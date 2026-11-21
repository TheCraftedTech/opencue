# Copyright (C) 2026 Samuel Zenker
# SPDX-License-Identifier: GPL-3.0-or-later
"""
fx_engine.py
Echtzeit-Effekt-Engine (FX) von OpenCue.

FX-Definitionen (Name, Gruppe, Skript-Art, Parameter) liegen wie Presets in der
Show (state.fx_effects, state.fx_groups). Die Art ist der Name eines Skripts aus
app/fx_script.py (Registry). Im Programmer wird einer Fixture je Attribut-
Kategorie (Dimmer, Farbe, Position) eine FX-ID zugewiesen (state.fx_assignments).

Die Skripte selbst laufen im RECHENKERN (app/fx_runner.py): im Normalbetrieb im EIGENEN PROZESS der DMX-Ausgabe (app/dmx_output.py) - unabhaengig vom Server, auf
einem anderen Prozessorkern -, ohne diesen Prozess (Tests, Rueckfall) in einem Thread dieses Moduls. Diese Engine haelt die Definitionen und Zuweisungen (Show-Zustand),
schickt dem Rechenkern bei jeder Aenderung eine vollstaendige Konfiguration (`_snapshot`), spiegelt dessen Kanalwerte in den DMX-Puffer (der Puffer bleibt die Wahrheit fuer die
Anzeige) und nimmt die Ausgabewerte fuer die Vorschau entgegen.

Der FX-Thread laeuft im Takt der DMX-Ausgabe (40 Hz). Jedes Skript legt mit `#RATE`
fest, wie oft pro Sekunde sein loop() laeuft (1-40): jede Instanz hat einen eigenen
Fahrplan (`_next_due`), zwischen zwei Durchlaeufen bleibt der letzte Ausgabewert stehen
(`_held`; nur Ein-/Ausblendungen rechnen auch dazwischen weiter). `t` ist die Zeit seit
dem Start der Engine (fuer alle Effekte gleich), `elapsed` die Zeit seit dem Start des
Effekts auf dieser Fixture (= Durchlauf / Rate, exakt). Der Skript-Zustand (globale
Variablen) ist pro Fixture x Kategorie x Effekt; geschrieben werden nur die Kanaele der
Kategorie ueber dmx_engine.commit_batch(). Alle Zugriffe auf Definitionen, Zuweisungen und
Skript-Zustaende laufen unter self.lock - so kann der FX-Thread nie einen Wert
nach einem Cue-Start schreiben.
"""

from __future__ import annotations

import itertools
import json
import logging
import threading
import time
import uuid
from typing import Any, Dict, List, Optional, Set, Tuple

from app.audio_engine import audio_engine
from app.dmx_engine import OUTPUT_FPS, dmx_engine
from app.dmx_resolve import current_abstract_values, fixture_channel_offsets
from app.fx_categories import ATTR_CATEGORY, CATEGORIES, CATEGORY_ATTRS  # noqa: F401  (ATTR_CATEGORY/CATEGORY_ATTRS: auch fuer cue_engine)
from app.fx_runner import FXRunner, SLOW_RUN_SECONDS, _abstract, _blend, _mix, _neutral  # noqa: F401  (Hilfen des Rechenkerns, hier weiter erreichbar)
from app.fx_script import FxScript, registry
from app.state_manager import state

logger = logging.getLogger("opencue.fx")

# Gleicher Takt wie die DMX-Ausgabe, damit Effektberechnung und Versand nicht schweben.
FX_HZ = OUTPUT_FPS
# Ausblenden eines Effekts (Out-Rampe): so lange nach ihrem Ende bleibt die Zuweisung noch, damit der Rechenkern den Endwert (Neutralwert) sicher ausgegeben und gespiegelt hat.
RAMP_FINISH_GRACE = 0.08
RAMP_KEEP_AFTER_IN = 0.5
# UI-Vorschau und DMX-Monitor laufen mit 25 Hz, unabhaengig vom FX-Takt.
UI_UPDATE_INTERVAL = 0.04



def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _color_dict(value: Any, fallback: Dict[str, int]) -> Dict[str, int]:
    try:
        return {k: int(_clamp(round(float(value[k])), 0, 255)) for k in ("r", "g", "b")}
    except (KeyError, TypeError, ValueError, IndexError):
        return dict(fallback)


def normalize_fx(data: Dict[str, Any], current: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """Validiert eine FX-Definition gegen ihr Skript. Parameter, die fehlen, kommen
    aus `current` oder aus den Vorgaben des Skripts."""
    kind = data.get("kind", (current or {}).get("kind"))
    script = registry.get(kind) if kind else None
    if script is None:
        return None
    source = data.get("params") if isinstance(data.get("params"), dict) else (current or {}).get("params", {})
    params: Dict[str, Any] = {}
    for var in script.ui_variables:
        raw = source.get(var.name, var.default)
        if var.kind == "ColorPicker":
            params[var.name] = _color_dict(raw, var.default)
        else:
            try:
                params[var.name] = _clamp(float(raw), var.minimum, var.maximum)
            except (TypeError, ValueError):
                params[var.name] = float(var.default)
    name = data.get("name", (current or {}).get("name", ""))
    group = data.get("group", (current or {}).get("group", ""))
    return {
        "name": str(name).strip()[:80],               # leer = save_definition vergibt einen eindeutigen Namen
        "group": str(group or "")[:60],
        "kind": kind,
        "params": params,
    }


class FXEngine:
    def __init__(self, st, dmx) -> None:
        self._state = st
        self._dmx = dmx
        # Schuetzt Definitionen, Zuweisungen und Skript-Zustaende gegen den FX-Thread.
        self.lock = threading.RLock()
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._offsets: Dict[str, Tuple[tuple, Dict[str, int]]] = {}
        self._touched_universes: Set[int] = set()
        # (fixture_id, kategorie) -> letzter Ausgabewert (abstrakt) - vom Rechenkern gemeldet (Vorschau, Start-Wert eines Cue-Fades).
        self._live: Dict[Tuple[str, str], Dict[str, Any]] = {}
        self._slot_cache: Dict[str, Dict[str, List[float]]] = {}          # Geraetetyp -> Gobo-Slots beider Raeder in Prozent
        self._t0 = time.monotonic()
        # (fixture_id, kategorie) -> Ein-/Ausblend-Rampe der Effekt-Amplitude:
        # {"rid": Nummer, "kind": "in"|"out", "start": monotonic, "dur": s, "base": abstrakte Werte}
        self._ramps: Dict[Tuple[str, str], Dict[str, Any]] = {}
        self._ramp_ids = itertools.count(1)
        self._assignments_changed = False
        # Rechenkern: im eigenen Prozess (mode "process") oder hier im Hauptprogramm (mode "local")
        self.mode = "local"
        self._epoch = 0                                                    # wird bei Show-Wechsel erhoeht: der Rechenkern verwirft seinen Laufzeit-Zustand
        self._runner: Optional[FXRunner] = None
        self._sig: Optional[str] = None                                    # Konfiguration, die der Rechenkern gerade hat
        self._sig_id = 0                                                   # Nummer der zuletzt an den Prozess geschickten Konfiguration
        self._master_sent: Optional[float] = None
        self._sent_at = 0.0
        self._live_seq = -1
        self.stats = {"mode": "local", "configs": 0, "mirror_skips": 0}

    def start(self) -> None:
        if self._thread is None or not self._thread.is_alive():
            self._stop.clear()
            self._thread = threading.Thread(target=self._loop, name="opencue-fx", daemon=True)
            self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None

    # ---- Definitionen (Bibliothek) -----------------------------------------------

    def name_taken(self, name: str, exclude_id: Optional[str] = None) -> bool:
        """Gibt es schon einen Effekt dieses Namens (Gross-/Kleinschreibung egal)? Ein Effekt zaehlt nicht gegen sich selbst."""
        wanted = str(name).strip().lower()
        with self.lock:
            return any(i != exclude_id and str(d.get("name", "")).strip().lower() == wanted for i, d in self._state.fx_effects.items())

    def _generated_name(self, kind: str) -> str:
        """Vorgabename eines neuen Effekts ohne eigenen Namen: der Name des Effekttyps (#NAME des Skripts), bei Bedarf mit Zaehler: "Kick Flash", "Kick Flash 2" ...
        (Aufrufer haelt self.lock)."""
        script = registry.get(kind)
        base = (script.label if script is not None and script.label else kind or "Effect").strip()[:70]
        taken = {str(d.get("name", "")).strip().lower() for d in self._state.fx_effects.values()}
        if base.lower() not in taken:
            return base
        n = 2
        while f"{base} {n}".lower() in taken:
            n += 1
        return f"{base} {n}"

    def save_definition(self, fx_id: Optional[str], data: Dict[str, Any]) -> Optional[str]:
        """Legt einen Effekt an (fx_id None) oder aendert ihn. Namen sind eindeutig: ein vergebener Name wird abgelehnt (None), ein leerer bekommt
        den Namen des Effekttyps (mit Zaehler, wenn vergeben; beim Aendern bleibt der alte). Die Art eines vorhandenen Effekts laesst sich nicht aendern."""
        with self.lock:
            current = self._state.fx_effects.get(fx_id) if fx_id else None
            if fx_id and current is None:
                return None
            if current is not None:
                data = {**data, "kind": current["kind"]}
            normalized = normalize_fx(data, current)
            if normalized is None:
                return None
            if normalized["name"]:
                if self.name_taken(normalized["name"], fx_id):
                    return None
            elif current is not None:
                normalized["name"] = current["name"]
            else:
                normalized["name"] = self._generated_name(normalized["kind"])
            new_id = fx_id or str(uuid.uuid4())
            self._state.fx_effects[new_id] = normalized
            return new_id

    def delete_definition(self, fx_id: str) -> List[str]:
        """Loescht eine Definition und ihre laufenden Zuweisungen. Cue-Verweise bleiben
        bestehen: Ein Cue mit einem fehlenden Effekt aendert den Kanal nicht (siehe
        cue_engine._start). Gibt die freigegebenen Fixtures zurueck."""
        with self.lock:
            if self._state.fx_effects.pop(fx_id, None) is None:
                return []
            return self._drop_assignments(lambda a: a.get("fx_id") == fx_id)

    def add_group(self, name: str) -> None:
        name = str(name).strip()[:60]
        with self.lock:
            if name and name not in self._state.fx_groups:
                self._state.fx_groups.append(name)

    def delete_group(self, name: str) -> None:
        with self.lock:
            if name not in self._state.fx_groups:
                return
            self._state.fx_groups.remove(name)
            for definition in self._state.fx_effects.values():
                if definition.get("group") == name:
                    definition["group"] = ""

    # ---- Zuweisungen (Programmer, Cues) ------------------------------------------

    def _script_of(self, fx_id: str) -> Optional[FxScript]:
        definition = self._state.fx_effects.get(fx_id)
        return registry.get(definition["kind"]) if definition else None

    def _used_attrs(self, fx_id: str, category: str) -> Set[str]:
        """Attribute, die dieser Effekt steuert (Ausgaben, die sein Skript setzt); ohne Skript alle der Kategorie."""
        script = self._script_of(fx_id)
        return set(script.used_attrs) if script is not None else set(CATEGORY_ATTRS[category])

    def attrs_of_effects(self, categories_to_fx: Dict[str, str]) -> Set[str]:
        """Vereinigung der gesteuerten Attribute fuer {kategorie: fx_id} (Cue-Engine: diese Attribute setzt der Cue nicht zusaetzlich statisch)."""
        with self.lock:
            attrs: Set[str] = set()
            for cat, fx_id in categories_to_fx.items():
                attrs |= self._used_attrs(fx_id, cat)
            return attrs

    def _category_of(self, fx_id: str) -> Optional[str]:
        definition = self._state.fx_effects.get(fx_id)
        return registry.category(definition["kind"]) if definition else None

    def assign(self, fixture_ids: List[str], category: str, fx_id: Optional[str]) -> List[str]:
        """Weist den Fixtures eine FX-ID je Kategorie zu (fx_id=None entfernt die
        Zuweisung). Gibt die Fixtures zurueck, die dadurch freigegeben wurden."""
        with self.lock:
            assignments = self._state.fx_assignments
            if fx_id is None:
                released = []
                for fid in fixture_ids:
                    cats = assignments.get(fid)
                    if cats and cats.pop(category, None) is not None:
                        released.append(fid)
                        self._forget(fid, category)
                        if not cats:
                            assignments.pop(fid, None)
                return released
            if self._category_of(fx_id) != category:
                return []
            valid = [fid for fid in fixture_ids if fid in self._state.fixtures]
            for index, fid in enumerate(valid):
                assignments.setdefault(fid, {})[category] = {"fx_id": fx_id, "index": index, "count": len(valid)}
            return []

    def _drop_assignments(self, predicate) -> List[str]:
        assignments = self._state.fx_assignments
        released: List[str] = []
        for fid in list(assignments):
            cats = assignments[fid]
            for cat in [c for c, a in cats.items() if predicate(a)]:
                cats.pop(cat, None)
                self._forget(fid, cat)
                released.append(fid)
            if not cats:
                assignments.pop(fid, None)
        return list(dict.fromkeys(released))

    def count_active(self, script_name: str) -> int:
        """Anzahl laufender Zuweisungen, die dieses Skript verwenden."""
        with self.lock:
            kinds = {fid for fid, d in self._state.fx_effects.items() if d.get("kind") == script_name}
            return sum(1 for cats in self._state.fx_assignments.values()
                       for a in cats.values() if a.get("fx_id") in kinds)

    def drop_script_assignments(self, script_name: str) -> List[str]:
        """Entfernt die Zuweisungen aller Effekte, die dieses Skript verwenden (Skript geloescht)."""
        with self.lock:
            kinds = {fid for fid, d in self._state.fx_effects.items() if d.get("kind") == script_name}
            return self._drop_assignments(lambda a: a.get("fx_id") in kinds)

    def cue_effects(self) -> Dict[str, Dict[str, str]]:
        """Aktuelle Zuweisungen als Cue-Datensatz: fixture_id -> {kategorie: fx_id}."""
        with self.lock:
            return {fid: {cat: a["fx_id"] for cat, a in cats.items()}
                    for fid, cats in self._state.fx_assignments.items() if cats}

    def cue_effect_order(self) -> Dict[str, Dict[str, int]]:
        """Auswahl-Reihenfolge je Zuweisung: fixture_id -> {kategorie: index}. Wird im Cue
        gespeichert, damit Welleneffekte nach dem Laden exakt gleich verteilt sind."""
        with self.lock:
            return {fid: {cat: int(a.get("index", 0)) for cat, a in cats.items()}
                    for fid, cats in self._state.fx_assignments.items() if cats}

    def take_assignments_changed(self) -> bool:
        with self.lock:
            changed, self._assignments_changed = self._assignments_changed, False
            return changed

    def reset_runtime(self) -> None:
        """Verwirft Skript-Zustaende, Ausgabewerte und Ein-/Ausblendungen (Show gewechselt),
        ohne die Zuweisungen der geladenen Show anzutasten."""
        with self.lock:
            self._live.clear()
            self._ramps.clear()
            self._epoch += 1

    def clear_all(self) -> List[str]:
        """Entfernt alle Zuweisungen (Clear Clear). Gibt die betroffenen Fixtures zurueck."""
        with self.lock:
            fixture_ids = list(self._state.fx_assignments)
            self._state.fx_assignments.clear()
            self._live.clear()
            self._ramps.clear()
            self._epoch += 1
            return fixture_ids

    def release_categories(self, fixture_id: str, categories, fade_out: float = 0.0) -> bool:
        """Beendet laufende Effekte der genannten Kategorien auf einer Fixture. Mit
        fade_out > 0 wird die Amplitude auf 0 % ausgeblendet, danach endet der Effekt."""
        now = time.monotonic()
        with self.lock:
            assigned = self._state.fx_assignments.get(fixture_id, {})
            released = False
            for cat in set(categories) & set(assigned):
                if fade_out > 0:
                    ramp = self._ramps.get((fixture_id, cat))
                    if not (ramp and ramp["kind"] == "out"):
                        self._ramps[(fixture_id, cat)] = {"rid": next(self._ramp_ids), "kind": "out", "start": now, "dur": fade_out,
                                                          "base": _neutral(cat, self._script_of(assigned[cat]["fx_id"]))}
                    released = True
                    continue
                self._forget(fixture_id, cat)
                assigned.pop(cat, None)
                released = True
            if fixture_id in self._state.fx_assignments and not assigned:
                self._state.fx_assignments.pop(fixture_id, None)
            return released

    def apply_cue_effects(self, cue_effects: Dict[str, Dict[str, str]],
                          order: Optional[Dict[str, Dict[str, int]]] = None,
                          fade_in: float = 0.0) -> bool:
        """Startet die Effekte eines Cues. Fixtures mit gleichem Effekt je Kategorie
        bilden eine Gruppe; ihr Phasenversatz folgt der gespeicherten Auswahl-Reihenfolge
        (`order`), sonst der Reihenfolge im Cue. Mit fade_in > 0 wird die Amplitude von
        dem Wert, der vorher anlag, auf 100 % eingeblendet."""
        order = order or {}
        groups: Dict[Tuple[str, str], List[str]] = {}
        for fid, cats in cue_effects.items():
            for cat, fx_id in cats.items():
                groups.setdefault((cat, fx_id), []).append(fid)
        started = False
        now = time.monotonic()
        with self.lock:
            for (cat, fx_id), fixture_ids in groups.items():
                if self._category_of(fx_id) != cat:
                    continue  # Effekt existiert nicht (mehr): Kanal bleibt unveraendert
                fixture_ids.sort(key=lambda f: order.get(f, {}).get(cat, 10 ** 6))
                for fid in fixture_ids:
                    cur = self._state.fx_assignments.get(fid, {}).get(cat)
                    ramp = self._ramps.get((fid, cat))
                    if ramp is not None and ramp["kind"] == "out":
                        self._ramps.pop((fid, cat), None)  # Effekt bleibt: Ausblenden abbrechen
                    elif fade_in > 0 and not (cur and cur["fx_id"] == fx_id):
                        fx = self._state.fixtures.get(fid)
                        if fx is not None:
                            script = self._script_of(fx_id)
                            mine = set(script.used_attrs) if script is not None else set(CATEGORY_ATTRS[cat])
                            base = self._live.get((fid, cat)) or {
                                k: v for k, v in current_abstract_values(fx).items()
                                if k in mine}
                            base = {**_neutral(cat, script), **base}
                            self._ramps[(fid, cat)] = {"rid": next(self._ramp_ids), "kind": "in", "start": now, "dur": fade_in, "base": base}
                self.assign(fixture_ids, cat, fx_id)
                started = True
        return started

    def release_for_cue(self, fixture_id: str, attrs) -> Tuple[Dict[str, Any], bool]:
        """Ein Cue setzt Attribute von `fixture_id` statisch. Entfernt die Effekt-
        Zuweisungen der betroffenen Kategorien und gibt den zuletzt AUSGEGEBENEN Wert
        zurueck (inkl. laufender Ein-/Ausblendung) - der Cue blendet exakt von dort aus."""
        attrs = set(attrs)
        categories = {ATTR_CATEGORY[a] for a in attrs if a in ATTR_CATEGORY}
        with self.lock:
            assigned = self._state.fx_assignments.get(fixture_id, {})
            from_values: Dict[str, Any] = {}
            released = False
            for cat in categories & set(assigned):
                mine = self._used_attrs(assigned[cat]["fx_id"], cat)
                if not (mine & attrs):
                    continue                                # der Cue setzt nur Attribute, die dieser Effekt nicht steuert
                a = assigned.pop(cat)
                last = self._live.get((fixture_id, cat))
                if last:
                    from_values.update(last)                  # ohne Ausgabewert (Effekt eben erst zugewiesen) startet der Cue vom aktuellen DMX-Stand
                self._forget(fixture_id, cat)
                released = True
            if fixture_id in self._state.fx_assignments and not assigned:
                self._state.fx_assignments.pop(fixture_id, None)
            return from_values, released

    def live_values(self) -> Dict[str, Dict[str, Any]]:
        """Modulierte Werte je Fixture fuer die UI-Vorschau (abstrakt, ohne Grand Master)."""
        with self.lock:
            live: Dict[str, Dict[str, Any]] = {}
            for fid, cats in self._state.fx_assignments.items():
                for cat in cats:
                    output = self._live.get((fid, cat))
                    if output:
                        live.setdefault(fid, {}).update(output)
            return live

    def state_payload(self) -> Dict[str, Any]:
        with self.lock:
            return {
                "effects": {fid: dict(fx) for fid, fx in self._state.fx_effects.items()},
                "groups": list(self._state.fx_groups),
                "assignments": {fid: {c: dict(a) for c, a in cats.items()}
                                for fid, cats in self._state.fx_assignments.items()},
                "scripts": registry.describe(),
                "is_dirty": self._state.is_dirty,
            }

    def take_touched_universes(self) -> Set[int]:
        with self.lock:
            touched, self._touched_universes = self._touched_universes, set()
        return touched

    # ---- Skript-Ausfuehrung --------------------------------------------------------

    def _forget(self, fixture_id: str, category: str) -> None:
        self._live.pop((fixture_id, category), None)
        self._ramps.pop((fixture_id, category), None)

    def _gobo_info(self, fixture_id: str) -> Dict[str, List[float]]:
        """Die festen Gobo-Slots der beiden Gobo-Raeder eines Geraets als Wert in Prozent (Mitte des DMX-Bereichs): {"slots": Rad 1, "slots2": Rad 2}; leer ohne Angaben."""
        fx = self._state.fixtures.get(fixture_id)
        if fx is None:
            return {"slots": [], "slots2": []}
        cached = self._slot_cache.get(fx.fixture_type)
        if cached is None:
            cached = {"slots": [], "slots2": []}
            try:
                from app.fixture_manager import get_fixture_beamfx
                data = get_fixture_beamfx(fx.fixture_type) or {}
                for key, channel in (("slots", "Gobo1"), ("slots2", "Gobo2")):
                    wheel = data.get(channel) or {}
                    cached[key] = [round((r["from"] + r["to"]) / 2 / 255.0 * 100.0, 3) for r in wheel.get("ranges", []) if r.get("kind") == "slot"]
            except Exception:                                  # ohne Angaben bleibt es leer: slots = 0
                logger.exception("Gobo-Slots von '%s' konnten nicht gelesen werden", fx.fixture_type)
            self._slot_cache[fx.fixture_type] = cached
        return cached

    def _gobo_slots(self, fixture_id: str) -> List[float]:
        return self._gobo_info(fixture_id)["slots"]

    def _offsets_for(self, fx) -> Dict[str, int]:
        # fixture_channel_offsets() durchsucht bei jedem Aufruf den GDTF-Ordner -
        # die Offsets werden deshalb je Fixture gecacht.
        signature = (fx.fixture_type, fx.mode)
        cached = self._offsets.get(fx.id)
        if cached is not None and cached[0] == signature:
            return cached[1]
        offsets = fixture_channel_offsets(fx)
        self._offsets[fx.id] = (signature, offsets)
        return offsets

    # ---- Konfiguration fuer den Rechenkern -----------------------------------------------------------------------------
    def _snapshot(self) -> Dict[str, Any]:
        """Alles, was der Rechenkern zum Rechnen braucht, als reine Daten (JSON-faehig): Zuweisungen, Effekt-Definitionen, Geraete (Adresse, Kanaltabelle, Gobo-Slots), Ein-/Ausblendungen.
        Aendert sich der Inhalt, schickt `_tick` eine neue Konfiguration - sonst nichts. Aufrufer haelt self.lock."""
        assign: List[list] = []
        fixtures: Dict[str, list] = {}
        types: Dict[str, Dict[str, int]] = {}
        defs: Dict[str, Dict[str, Any]] = {}
        kinds: Dict[str, int] = {}
        audio = False
        for fid, cats in self._state.fx_assignments.items():
            fx = self._state.fixtures.get(fid)
            if fx is None:
                continue
            for cat, a in cats.items():
                definition = self._state.fx_effects.get(a["fx_id"])
                script = registry.get(definition["kind"]) if definition else None
                if script is None:
                    continue
                assign.append([fid, cat, a["fx_id"], int(a.get("index", 0)), int(a.get("count", 1))])
                defs[a["fx_id"]] = {"kind": definition["kind"], "params": definition.get("params", {})}
                kinds[definition["kind"]] = script.program.uid
                audio = audio or script.uses_audio
                entry = fixtures.get(fid)
                if entry is None:
                    key = f"{fx.fixture_type}|{fx.mode}"
                    types[key] = self._offsets_for(fx)
                    entry = fixtures[fid] = [fx.universe, fx.start_channel, key, [], []]
                if cat == "gobo":
                    info = self._gobo_info(fid)
                    entry[3], entry[4] = info["slots"], info["slots2"]
        ramps = [[fid, cat, r["rid"], r["kind"], r["start"], r["dur"], r["base"]] for (fid, cat), r in self._ramps.items()
                 if any(a[0] == fid and a[1] == cat for a in assign)]
        return {"epoch": self._epoch, "assign": assign, "defs": defs, "fixtures": fixtures, "types": types, "kinds": kinds, "ramps": ramps, "audio": audio}

    @staticmethod
    def _signature(snap: Dict[str, Any]) -> str:
        return json.dumps({k: v for k, v in snap.items() if k != "types"}, sort_keys=True, default=str)

    def _config(self, snap: Dict[str, Any], now: float) -> Dict[str, Any]:
        """Die Nachricht an den Rechenkern: der Schnappschuss, dazu die Quelltexte der benutzten Skripte; Rampen mit Alter statt absoluter Zeit (jeder Prozess hat seine eigene Uhr)."""
        cfg = {k: v for k, v in snap.items() if k not in ("kinds", "audio")}
        cfg["scripts"] = {kind: registry.get(kind).source for kind in snap["kinds"] if registry.get(kind) is not None}
        cfg["ramps"] = [[fid, cat, rid, kind, max(0.0, now - start), dur, base] for fid, cat, rid, kind, start, dur, base in snap["ramps"]]
        return cfg

    # ---- FX-Thread -----------------------------------------------------------------------------------------------------
    def _loop(self) -> None:
        period = 1.0 / FX_HZ
        next_tick = time.monotonic()
        while not self._stop.is_set():
            try:
                self._tick(time.monotonic())
            except Exception:
                logger.exception("FX-Tick fehlgeschlagen")
            next_tick += period
            delay = next_tick - time.monotonic()
            if delay < 0:
                next_tick = time.monotonic()
                delay = 0.0
            self._stop.wait(delay)

    def _tick(self, now: float) -> None:
        with self.lock:
            proc = self._dmx.fx_process()
            if proc is None:
                if self.mode != "local":                            # Rueckfall: der Ausgabe-Prozess ist weg, hier weiterrechnen (frisch begonnen)
                    self.mode = self.stats["mode"] = "local"
                    self._sig = None
                    self._runner = None
                    logger.warning("FX: Der Rechenkern laeuft jetzt im Hauptprogramm")
                self._tick_local(now)
            else:
                if self.mode != "process":
                    self.mode = self.stats["mode"] = "process"
                    self._sig = None
                    self._master_sent = None
                    self._runner = None
                    logger.info("FX: Der Rechenkern laeuft im Prozess der DMX-Ausgabe")
                self._tick_remote(now, proc)
            self._finish_ramps(now)

    def _tick_local(self, now: float) -> None:
        snap = self._snapshot()
        sig = self._signature(snap)
        runner = self._runner
        if runner is None:
            runner = self._runner = FXRunner()
            runner.t0 = self._t0
        if sig != self._sig:
            runner.apply_config(self._config(snap, now), now)
            self._sig = sig
            self.stats["configs"] += 1
        if not snap["assign"]:
            return
        runner.master = self._state.effective_master("")
        batches, live = runner.tick(now, audio_engine.values() if snap["audio"] else None)
        for universe, channels in batches.items():
            self._dmx.commit_batch(universe, channels)
        self._touched_universes.update(batches.keys())
        self._live.update(live)

    def _tick_remote(self, now: float, proc) -> None:
        snap = self._snapshot()
        sig = self._signature(snap)
        changed = sig != self._sig
        if changed:
            nxt = self._sig_id + 1
            if proc.send_fx(nxt, self._config(snap, now)):
                self._sig_id = nxt
                self._sig = sig
                self._sent_at = now
                self.stats["configs"] += 1
        master = self._state.effective_master("")
        if master != self._master_sent and proc.send({"cmd": "fxgm", "gm": master}):
            self._master_sent = master
        if snap["audio"]:
            proc.send({"cmd": "fxaudio", "a": audio_engine.values()})
        if not snap["assign"]:
            return
        if changed or sig != self._sig:
            self.stats["mirror_skips"] += 1                          # die Konfiguration ist noch unterwegs: der Rechenkern hat den alten Stand (nichts spiegeln, was veraltet ist)
            return
        applied, overlay = proc.read_overlay()
        if applied != self._sig_id:
            self.stats["mirror_skips"] += 1
            again = proc.fx_message_again() if now - self._sent_at > 1.5 else None
            if again is not None:                                            # nicht quittiert (Nachricht verloren / Prozess eben neu gestartet): noch einmal schicken
                proc.send(again)
                self._sent_at = now
            return
        for universe, (values, mask) in overlay.items():
            if self._dmx.mirror_overlay(universe, values, mask):
                self._touched_universes.add(universe)
        seq = proc.fx_live_seq
        if seq != self._live_seq:
            self._live_seq = seq
            for fid, cat, abstract in proc.fx_live:
                self._live[(fid, cat)] = abstract

    def _finish_ramps(self, now: float) -> None:
        """Ausblenden beendet: der Effekt endet auf dem Neutralwert (Zuweisung faellt weg). Eingeblendete Rampen werden nach kurzer Zeit vergessen."""
        for (fid, cat), ramp in list(self._ramps.items()):
            end = ramp["start"] + ramp["dur"]
            if ramp["kind"] == "out" and now >= end + RAMP_FINISH_GRACE:
                assigned = self._state.fx_assignments.get(fid, {})
                assigned.pop(cat, None)
                if not assigned:
                    self._state.fx_assignments.pop(fid, None)
                self._forget(fid, cat)
                self._assignments_changed = True
            elif ramp["kind"] == "in" and now >= end + RAMP_KEEP_AFTER_IN:
                self._ramps.pop((fid, cat), None)


fx_engine = FXEngine(state, dmx_engine)
