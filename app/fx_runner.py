# Copyright (C) 2026 Samuel Zenker
# SPDX-License-Identifier: GPL-3.0-or-later
"""
fx_runner.py
Der RECHENKERN der Effekte: fuehrt die Effekt-Skripte aus und liefert DMX-Kanalwerte - ohne jeden Zugriff auf Show, Server oder Oberflaeche.

Warum ein eigenes Modul: Effekte sind der rechenintensivste Teil von OpenCue (jedes Skript laeuft bis zu 40-mal pro Sekunde je Scheinwerfer). Dieser Kern bekommt alles, was er
braucht, als reine Daten (`apply_config`: Zuweisungen, Effekt-Definitionen, Skript-Quelltexte, Geraete-Kanaltabellen, Ein-/Ausblendungen) und kann deshalb in jedem Prozess laufen:
  * im EIGENEN PROZESS der DMX-Ausgabe (app/dmx_output.py, Normalbetrieb): Effekte laufen dann auf einem anderen Prozessorkern mit eigenem Interpreter, unabhaengig vom Server;
  * im Hauptprogramm (app/fx_engine.py, Rueckfall und Tests), wenn die Ausgabe nicht in einem eigenen Prozess laeuft.
Dieses Modul importiert nichts aus dem Programm ausser Skript-Sprache, Kategorien und der reinen Kanal-Aufloesung - es ist im Ausgabe-Prozess billig zu laden.

Zeit: `tick(now, audio)` bekommt die Zeit von aussen (monotone Sekunden des aufrufenden Prozesses); `t` im Skript ist die Zeit seit dem Start dieses Rechenkerns.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional, Set, Tuple

from app.dmx_resolve import apply_abstract_values
from app.fx_categories import CATEGORIES
from app.fx_script import FxScript, compile_script, run_script

logger = logging.getLogger("opencue.fx")

# Ein Durchlauf, der laenger dauert, haelt den Rechenkern fuer alle anderen Effekte auf: so ein Effekt wird abgeschaltet.
SLOW_RUN_SECONDS = 0.05


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


class _Fixture:
    """Das Wenige, was die Kanal-Aufloesung von einem Geraet braucht (apply_abstract_values liest universe und start_channel)."""
    __slots__ = ("id", "universe", "start_channel")

    def __init__(self, fid: str, universe: int, start_channel: int) -> None:
        self.id, self.universe, self.start_channel = fid, universe, start_channel


Key = Tuple[str, str, str, str]            # (Scheinwerfer, Kategorie, Effekt-ID, Skript-Art)


class FXRunner:
    def __init__(self) -> None:
        self.epoch = -1
        self.t0 = time.monotonic()
        self.master = 100.0                                              # Grand Master (0-100 %), bei Blackout 0 (vom Aufrufer gesetzt)
        self.scripts: Dict[str, FxScript] = {}
        self._sources: Dict[str, str] = {}
        self.assign: List[Tuple[str, str, str, int, int]] = []           # (Scheinwerfer, Kategorie, Effekt-ID, Index, Anzahl)
        self.defs: Dict[str, Dict[str, Any]] = {}
        self.fixtures: Dict[str, _Fixture] = {}
        self.offsets: Dict[str, Dict[str, int]] = {}                      # Scheinwerfer -> Kanalname -> Offset
        self.gobo: Dict[str, Dict[str, List[float]]] = {}                 # Scheinwerfer -> {"slots": [...], "slots2": [...]}
        # Laufzeit (je Scheinwerfer x Kategorie x Effekt)
        self._instances: Dict[Key, Dict[str, Any]] = {}
        self._runs: Dict[Key, int] = {}
        self._next_due: Dict[Key, float] = {}
        self._held: Dict[Key, Dict[str, float]] = {}
        self._failed: Dict[Key, int] = {}
        self._ramps: Dict[Tuple[str, str], Dict[str, Any]] = {}            # (Scheinwerfer, Kategorie) -> {"rid", "kind": "in"|"out", "start", "dur", "base"}
        # Zuletzt geschriebene Kanaele je Zuweisung: (Universum, Kanal) -> Wert. Daraus entsteht die Ueberlagerung der Ausgabe (solange die Zuweisung besteht, gehoert ihr der Kanal).
        self.owned: Dict[Tuple[str, str], Dict[Tuple[int, int], int]] = {}

    # ---- Konfiguration --------------------------------------------------------------------------
    def apply_config(self, cfg: Dict[str, Any], now: Optional[float] = None) -> None:
        now = time.monotonic() if now is None else now
        if cfg.get("epoch") != self.epoch:                                # Show gewechselt / alles zuruecksetzen
            self.epoch = cfg.get("epoch")
            self._reset_runtime()
        for name, text in (cfg.get("scripts") or {}).items():
            if self._sources.get(name) == text and name in self.scripts:
                continue
            try:
                self.scripts[name] = compile_script(name, text)
                self._sources[name] = text
            except Exception as exc:                                       # ein fehlerhaftes Skript ersetzt die zuletzt funktionierende Version nicht
                logger.error("FX-Skript '%s' laesst sich nicht uebersetzen: %s", name, exc)
        types = cfg.get("types") or {}
        self.fixtures = {}
        self.offsets = {}
        self.gobo = {}
        for fid, (universe, start, key, slots, slots2) in (cfg.get("fixtures") or {}).items():
            self.fixtures[fid] = _Fixture(fid, int(universe), int(start))
            self.offsets[fid] = types.get(key, {})
            if slots or slots2:
                self.gobo[fid] = {"slots": list(slots), "slots2": list(slots2)}
        self.assign = [tuple(a) for a in (cfg.get("assign") or [])]
        self.defs = cfg.get("defs") or {}
        wanted: Dict[Tuple[str, str], Dict[str, Any]] = {}
        for fid, cat, rid, kind, age, dur, base in (cfg.get("ramps") or []):
            current = self._ramps.get((fid, cat))
            if current is not None and current["rid"] == rid:
                wanted[(fid, cat)] = current                               # diese Ein-/Ausblendung laeuft schon: ihr Start bleibt
            else:
                wanted[(fid, cat)] = {"rid": rid, "kind": kind, "start": now - float(age), "dur": float(dur), "base": base}
        self._ramps = wanted
        active = {(fid, cat) for fid, cat, *_ in self.assign}
        for key in [k for k in self.owned if k not in active]:             # Zuweisung beendet: die Kanaele gehoeren ihr nicht mehr
            self.owned.pop(key, None)

    def _reset_runtime(self) -> None:
        self._instances.clear()
        self._runs.clear()
        self._next_due.clear()
        self._held.clear()
        self._failed.clear()
        self._ramps.clear()
        self.owned.clear()

    # ---- Ausfuehrung ----------------------------------------------------------------------------
    def _execute(self, fid: str, cat: str, index: int, count: int, fx_id: str, script: FxScript, definition: Dict[str, Any], now: float,
                 audio: Optional[Dict[str, float]]) -> Dict[str, float]:
        key = (fid, cat, fx_id, definition["kind"])
        if self._failed.get(key) == script.program.uid:
            return {}                                       # ruht (Fehler/zu langsam), bis das Skript neu gespeichert wird
        instance = self._instances.setdefault(key, {})
        runs = self._runs.get(key, 0)
        self._runs[key] = runs + 1
        started = time.perf_counter()
        try:
            info = self.gobo.get(fid, {"slots": [], "slots2": []}) if cat == "gobo" else None
            out = run_script(script, instance, definition.get("params", {}), index, count, now - self.t0, runs, info, audio if script.uses_audio else None)
        except Exception:  # Ein Laufzeitfehler stoppt nur diesen Effekt, nie den Rechenkern
            logger.exception("FX-Skript '%s' fehlgeschlagen - der Effekt ruht bis zum naechsten Speichern", script.name)
            self._failed[key] = script.program.uid
            return {}
        if time.perf_counter() - started > SLOW_RUN_SECONDS:
            logger.warning("FX-Skript '%s' braucht zu lange pro Durchlauf (mehr als %.0f ms) - der Effekt ruht bis zum naechsten Speichern", script.name, SLOW_RUN_SECONDS * 1000)
            self._failed[key] = script.program.uid
        return out

    def uses_audio(self) -> bool:
        for _fid, _cat, fx_id, _i, _n in self.assign:
            definition = self.defs.get(fx_id)
            script = self.scripts.get(definition["kind"]) if definition else None
            if script is not None and script.uses_audio:
                return True
        return False

    def tick(self, now: float, audio: Optional[Dict[str, float]] = None) -> Tuple[Dict[int, Dict[int, int]], Dict[Tuple[str, str], Dict[str, Any]]]:
        """Ein Durchlauf: gibt (Kanalwerte dieses Takts je Universum, abstrakte Ausgabewerte je (Scheinwerfer, Kategorie)) zurueck."""
        jobs = []
        active: Set[Key] = set()
        for fid, cat, fx_id, index, count in self.assign:
            fx = self.fixtures.get(fid)
            if fx is None:
                continue
            definition = self.defs.get(fx_id)
            script = self.scripts.get(definition["kind"]) if definition else None
            if script is not None:
                active.add((fid, cat, fx_id, definition["kind"]))
                jobs.append((fx, cat, index, count, fx_id, script, definition))
        for key in [k for k in self._instances if k not in active]:
            self._instances.pop(key, None)
            self._runs.pop(key, None)
            self._next_due.pop(key, None)
            self._held.pop(key, None)
            self._failed.pop(key, None)
        batches: Dict[int, Dict[int, int]] = {}
        live: Dict[Tuple[str, str], Dict[str, Any]] = {}
        for fx, cat, index, count, fx_id, script, definition in jobs:
            key = (fx.id, cat, fx_id, definition["kind"])
            ramp = self._ramps.get((fx.id, cat))
            due = self._next_due.get(key)
            if due is None or now >= due - 0.002:            # loop() ist dran (#RATE-mal pro Sekunde)
                period = 1.0 / script.rate
                nxt = (due if due is not None else now) + period
                self._next_due[key] = nxt if nxt > now - 3 * period else now + period      # weit im Rueckstand: neu aufsetzen statt aufholen
                out = self._execute(fx.id, cat, index, count, fx_id, script, definition, now, audio)
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
                else:
                    abstract = _blend(abstract, ramp["base"], f)
            live[(fx.id, cat)] = abstract
            local: Dict[int, Dict[int, int]] = {}
            apply_abstract_values(fx, abstract, self.offsets.get(fx.id, {}), local, pct_values=True, grand_master=self.master)
            if local:
                owned = self.owned.setdefault((fx.id, cat), {})
                for universe, channels in local.items():
                    batches.setdefault(universe, {}).update(channels)
                    for channel, value in channels.items():
                        owned[(universe, channel)] = value
        return batches, live

    def overlay(self) -> Dict[int, Dict[int, int]]:
        """Alle Kanaele, die gerade einer Zuweisung gehoeren, mit ihrem letzten Wert: Universum -> {Kanal (1-512): Wert}."""
        out: Dict[int, Dict[int, int]] = {}
        for channels in self.owned.values():
            for (universe, channel), value in channels.items():
                out.setdefault(universe, {})[channel] = value
        return out
