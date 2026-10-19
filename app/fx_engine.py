"""
fx_engine.py
Echtzeit-Effekt-Engine (FX) von OpenCue.

FX-Definitionen (Name, Gruppe, Skript-Art, Parameter) liegen wie Presets in der
Show (state.fx_effects, state.fx_groups). Die Art ist der Name eines Skripts aus
app/fx_script.py (Registry). Im Programmer wird einer Fixture je Attribut-
Kategorie (Dimmer, Farbe, Position) eine FX-ID zugewiesen (state.fx_assignments).

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

import logging
import threading
import time
import uuid
from typing import Any, Dict, List, Optional, Set, Tuple

from app.dmx_engine import OUTPUT_FPS, dmx_engine
from app.dmx_resolve import apply_abstract_values, current_abstract_values, fixture_channel_offsets
from app.fx_categories import ATTR_CATEGORY, CATEGORIES, CATEGORY_ATTRS  # noqa: F401  (ATTR_CATEGORY/CATEGORY_ATTRS: auch fuer cue_engine)
from app.fx_script import FxScript, registry, run_script
from app.state_manager import state

logger = logging.getLogger("opencue.fx")

# Gleicher Takt wie die DMX-Ausgabe, damit Effektberechnung und Versand nicht schweben.
FX_HZ = OUTPUT_FPS
# Ein Durchlauf, der laenger dauert, haelt den FX-Thread (und die Sperre) fuer alle anderen Effekte auf: so ein Effekt wird abgeschaltet.
SLOW_RUN_SECONDS = 0.05
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


def _abstract(category: str, out: Dict[str, float], script: Optional[Any] = None) -> Dict[str, Any]:
    """Ausgabe des Skripts -> abstrakte Werte fuer apply_abstract_values (pct_values=True); Tabelle: app/fx_categories.py.
    Mit `script` nur die Ausgaben, die es wirklich setzt: ein Effekt, der nur `pan` schreibt, laesst `tilt` in Ruhe."""
    return CATEGORIES[category].to_abstract(out, script.used_outputs if script is not None else None)


def _neutral(category: str, script: Optional[Any] = None) -> Dict[str, Any]:
    return CATEGORIES[category].neutral(script.used_outputs if script is not None else None)


def _mix(a: Any, b: Any, f: float) -> Any:
    """Linearer Mix zweier abstrakter Werte (Zahl oder {r,g,b}-Dict)."""
    if isinstance(a, dict) and isinstance(b, dict):
        return {k: float(a.get(k, 0.0)) + (float(b.get(k, 0.0)) - float(a.get(k, 0.0))) * f for k in b}
    return float(a) + (float(b) - float(a)) * f


def _blend(frm: Dict[str, Any], to: Dict[str, Any], f: float) -> Dict[str, Any]:
    return {k: _mix(frm.get(k, v), v, f) for k, v in to.items()}


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
        # (fixture_id, kategorie) -> letzter Ausgabewert (abstrakt).
        self._last_output: Dict[Tuple[str, str], Dict[str, Any]] = {}
        # (fixture_id, kategorie, fx_id) -> persistenter Speicher des Skripts.
        self._instances: Dict[Tuple[str, str, str, str], Dict[str, Any]] = {}
        self._runs: Dict[Tuple[str, str, str, str], int] = {}
        # Fahrplan je Instanz: Zeitpunkt des naechsten loop()-Aufrufs und der zuletzt gelieferte Ausgabewert (Skript-Ausgabe, nicht abstrakt)
        self._next_due: Dict[Tuple[str, str, str, str], float] = {}
        self._held: Dict[Tuple[str, str, str, str], Dict[str, float]] = {}
        # Instanzen, die mit einem Fehler oder zu langsam waren: ruhen, bis das Skript neu gespeichert wird (Wert = Programm-Nummer, die versagt hat)
        self._failed: Dict[Tuple[str, str, str, str], int] = {}
        self._slot_cache: Dict[str, Dict[str, List[float]]] = {}          # Geraetetyp -> Gobo-Slots beider Raeder in Prozent
        self._t0 = time.monotonic()
        # (fixture_id, kategorie) -> Ein-/Ausblend-Rampe der Effekt-Amplitude:
        # {"kind": "in"|"out", "start": monotonic, "dur": s, "base": abstrakte Werte}
        self._ramps: Dict[Tuple[str, str], Dict[str, Any]] = {}
        self._assignments_changed = False

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

    def _generated_name(self, category: str) -> str:
        """Eindeutiger Vorgabename je Kategorie: Position_1, Position_2 ... (Aufrufer haelt self.lock)."""
        base = (category or "Effekt").capitalize()
        taken = {str(d.get("name", "")).strip().lower() for d in self._state.fx_effects.values()}
        n = 1
        while f"{base}_{n}".lower() in taken:
            n += 1
        return f"{base}_{n}"

    def save_definition(self, fx_id: Optional[str], data: Dict[str, Any]) -> Optional[str]:
        """Legt einen Effekt an (fx_id None) oder aendert ihn. Namen sind eindeutig: ein vergebener Name wird abgelehnt (None), ein leerer bekommt
        einen erzeugten (Kategorie_1 ...; beim Aendern bleibt der alte). Die Art eines vorhandenen Effekts laesst sich nicht aendern."""
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
                normalized["name"] = self._generated_name(registry.category(normalized["kind"]) or "")
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
            self._last_output.clear()
            self._instances.clear()
            self._runs.clear()
            self._next_due.clear()
            self._held.clear()
            self._failed.clear()
            self._ramps.clear()

    def clear_all(self) -> List[str]:
        """Entfernt alle Zuweisungen (Clear Clear). Gibt die betroffenen Fixtures zurueck."""
        with self.lock:
            fixture_ids = list(self._state.fx_assignments)
            self._state.fx_assignments.clear()
            self._last_output.clear()
            self._instances.clear()
            self._runs.clear()
            self._next_due.clear()
            self._held.clear()
            self._failed.clear()
            self._ramps.clear()
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
                        self._ramps[(fixture_id, cat)] = {"kind": "out", "start": now, "dur": fade_out,
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
                            base = self._last_output.get((fid, cat)) or {
                                k: v for k, v in current_abstract_values(fx).items()
                                if k in mine}
                            base = {**_neutral(cat, script), **base}
                            self._ramps[(fid, cat)] = {"kind": "in", "start": now, "dur": fade_in, "base": base}
                self.assign(fixture_ids, cat, fx_id)
                started = True
        return started

    def release_for_cue(self, fixture_id: str, attrs) -> Tuple[Dict[str, Any], bool]:
        """Ein Cue setzt Attribute von `fixture_id` statisch. Entfernt die Effekt-
        Zuweisungen der betroffenen Kategorien und gibt den zuletzt AUSGEGEBENEN Wert
        zurueck (inkl. laufender Ein-/Ausblendung) - der Cue blendet exakt von dort aus."""
        attrs = set(attrs)
        categories = {ATTR_CATEGORY[a] for a in attrs if a in ATTR_CATEGORY}
        now = time.monotonic()
        with self.lock:
            assigned = self._state.fx_assignments.get(fixture_id, {})
            from_values: Dict[str, Any] = {}
            released = False
            for cat in categories & set(assigned):
                mine = self._used_attrs(assigned[cat]["fx_id"], cat)
                if not (mine & attrs):
                    continue                                # der Cue setzt nur Attribute, die dieser Effekt nicht steuert
                a = assigned.pop(cat)
                last = self._last_output.get((fixture_id, cat))
                if last:
                    from_values.update(last)
                else:
                    definition = self._state.fx_effects.get(a["fx_id"])
                    script = registry.get(definition["kind"]) if definition else None
                    if script is not None and fixture_id in self._state.fixtures:
                        out = self._execute(fixture_id, cat, a, script, definition, now)
                        if out:
                            from_values.update(_abstract(cat, out, script))
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
                    output = self._last_output.get((fid, cat))
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
        self._last_output.pop((fixture_id, category), None)
        self._ramps.pop((fixture_id, category), None)
        for key in [k for k in self._instances if k[0] == fixture_id and k[1] == category]:
            self._instances.pop(key, None)
            self._runs.pop(key, None)
            self._next_due.pop(key, None)
            self._held.pop(key, None)
            self._failed.pop(key, None)

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

    def _execute(self, fid: str, cat: str, a: Dict[str, Any], script: FxScript,
                 definition: Dict[str, Any], now: float) -> Dict[str, float]:
        key = (fid, cat, a["fx_id"], definition["kind"])
        if self._failed.get(key) == script.program.uid:
            return {}                                       # ruht (Fehler/zu langsam), bis das Skript neu gespeichert wird
        instance = self._instances.setdefault(key, {})
        runs = self._runs.get(key, 0)
        self._runs[key] = runs + 1
        started = time.perf_counter()
        try:
            info = self._gobo_info(fid) if cat == "gobo" else None
            out = run_script(script, instance, definition.get("params", {}),
                             a["index"], a["count"], now - self._t0, runs, info)
        except Exception:  # Ein Laufzeitfehler stoppt nur diesen Effekt, nie den Thread
            logger.exception("FX-Skript '%s' fehlgeschlagen - der Effekt ruht bis zum naechsten Speichern", script.name)
            self._failed[key] = script.program.uid
            return {}
        if time.perf_counter() - started > SLOW_RUN_SECONDS:
            logger.warning("FX-Skript '%s' braucht zu lange pro Durchlauf (mehr als %.0f ms) - der Effekt ruht bis zum naechsten Speichern",
                           script.name, SLOW_RUN_SECONDS * 1000)
            self._failed[key] = script.program.uid
        return out

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

    # ---- FX-Thread -----------------------------------------------------------------

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
            self._tick_locked(now)

    def _tick_locked(self, now: float) -> None:
        jobs = []
        active: Set[Tuple[str, str, str, str]] = set()
        for fid, cats in self._state.fx_assignments.items():
            fx = self._state.fixtures.get(fid)
            if fx is None:
                continue
            for cat, a in cats.items():
                definition = self._state.fx_effects.get(a["fx_id"])
                script = registry.get(definition["kind"]) if definition else None
                if script is not None:
                    active.add((fid, cat, a["fx_id"], definition["kind"]))
                    jobs.append((fx, cat, a, script, definition))
        for key in [k for k in self._instances if k not in active]:
            self._instances.pop(key, None)
            self._runs.pop(key, None)
            self._next_due.pop(key, None)
            self._held.pop(key, None)
            self._failed.pop(key, None)
        if not jobs:
            return

        batches: Dict[int, Dict[int, int]] = {}
        finished: List[Tuple[str, str]] = []
        for fx, cat, a, script, definition in jobs:
            key = (fx.id, cat, a["fx_id"], definition["kind"])
            ramp = self._ramps.get((fx.id, cat))
            due = self._next_due.get(key)
            if due is None or now >= due - 0.002:            # loop() ist dran (#RATE-mal pro Sekunde)
                period = 1.0 / script.rate
                nxt = (due if due is not None else now) + period
                self._next_due[key] = nxt if nxt > now - 3 * period else now + period      # weit im Rueckstand: neu aufsetzen statt aufholen
                out = self._execute(fx.id, cat, a, script, definition, now)
                if out:
                    self._held[key] = out
            else:
                out = self._held.get(key)
                if ramp is None:
                    continue                                 # nichts Neues: der Kanal behaelt den letzten Wert
            if not out:
                continue
            abstract = _abstract(cat, out, script)
            if ramp is not None:
                f = min(1.0, (now - ramp["start"]) / ramp["dur"]) if ramp["dur"] > 0 else 1.0
                if ramp["kind"] == "in":
                    abstract = _blend(ramp["base"], abstract, f)
                    if f >= 1.0:
                        self._ramps.pop((fx.id, cat), None)
                else:
                    abstract = _blend(abstract, ramp["base"], f)
                    if f >= 1.0:
                        finished.append((fx.id, cat))
            self._last_output[(fx.id, cat)] = abstract
            apply_abstract_values(
                fx, abstract, self._offsets_for(fx), batches,
                pct_values=True, grand_master=self._state.effective_master(fx.id),
            )
        for universe, channels in batches.items():
            self._dmx.commit_batch(universe, channels)
        self._touched_universes.update(batches.keys())
        for fid, cat in finished:  # Ausblenden beendet: Effekt endet auf dem Neutralwert
            assigned = self._state.fx_assignments.get(fid, {})
            assigned.pop(cat, None)
            if not assigned:
                self._state.fx_assignments.pop(fid, None)
            self._forget(fid, cat)
            self._assignments_changed = True


fx_engine = FXEngine(state, dmx_engine)
