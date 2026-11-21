# Copyright (C) 2026 Samuel Zenker
# SPDX-License-Identifier: GPL-3.0-or-later
"""
cue_fade.py
Der RECHENKERN der Cue-Ueberblendungen: aus den Start- und Zielwerten eines Cues und der verstrichenen Zeit die abstrakten Werte (und daraus DMX-Kanalwerte) - ohne Zugriff auf Show,
Server oder Oberflaeche (nur die Kanal-Aufloesung aus dmx_resolve).

Zwei Benutzer teilen sich genau diese Formeln (so laufen beide nie auseinander):
  * app/cue_engine.py (Server): rechnet jeden Takt seinen Stand (Fixture-Werte, Cue-Schicht, Live-Anzeige) und schreibt ihn in den DMX-Puffer;
  * der Ausgabe-Prozess (app/dmx_output.py): bekommt jede laufende Ueberblendung als reine Daten (`fade_to_dict`) und rechnet sie mit seiner eigenen Uhr als "Ueberlagerung" ueber das Bild des
    Servers (`FadePlayer`). Haengt der Server oder rechnet er gerade Schweres, laeuft die Ueberblendung in der Ausgabe trotzdem gleichmaessig weiter.
"""

from __future__ import annotations

import copy
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from app.dmx_resolve import DISCRETE_ATTRS, apply_abstract_values, raw_offset

SCALAR_ATTRS = ("dimmer", "pan", "tilt", "strobe", "gobo", "gobo_spin", "gobo2", "gobo2_spin", "prism", "focus", "zoom")

# Abstraktes Attribut -> Attributgruppe (bestimmt, welche Cue-Fade/Delay-Zeit gilt). "color" wird separat behandelt, gehoert aber ebenfalls zur "color"-Gruppe.
ATTR_GROUPS: Dict[str, str] = {
    "dimmer": "dimmer",
    "pan": "pos",
    "tilt": "pos",
    "strobe": "beam",
    "gobo": "beam",
    "gobo_spin": "beam",
    "gobo2": "beam",
    "gobo2_spin": "beam",
    "prism": "beam",
    "focus": "beam",
    "zoom": "zoom",
}


def neutral_value(attr: str) -> Any:
    if attr == "color":
        return {"r": 0, "g": 0, "b": 0}
    return 50.0 if attr in ("pan", "tilt") else 0.0


def mix_abstract(base: Dict[str, Any], layer: Dict[str, Any], f: float) -> Dict[str, Any]:
    """Mischt die Cue-Werte (layer) linear mit den manuellen Werten (base): f = 1 -> Cue, f = 0 -> manuell. Gilt fuer
    jedes Attribut (Skalare und Farbe je Kanal); fehlt ein manueller Wert, gilt der Neutralwert."""
    out: Dict[str, Any] = {}
    for attr, cue_value in layer.items():
        if f >= 1.0:
            out[attr] = copy.deepcopy(cue_value)
            continue
        manual = base.get(attr)
        if manual is None:
            manual = neutral_value(attr)
        if attr in DISCRETE_ATTRS or raw_offset(attr) is not None:
            out[attr] = copy.deepcopy(cue_value if f >= 0.5 else manual)           # Raeder/rohe Kanaele: umschalten statt ueberblenden
        elif attr == "color":
            out[attr] = {k: float(manual.get(k, 0)) + (float(cue_value.get(k, 0)) - float(manual.get(k, 0))) * f
                         for k in ("r", "g", "b")}
        else:
            out[attr] = float(manual) + (float(cue_value) - float(manual)) * f
    return out


@dataclass
class FixtureFade:
    """Start- und Zielwerte EINER Fixture fuer die laufende Ueberblendung."""

    scalars_from: Dict[str, float] = field(default_factory=dict)
    scalars_to: Dict[str, float] = field(default_factory=dict)
    color_from: Optional[Dict[str, float]] = None
    color_to: Optional[Dict[str, float]] = None
    # Rohe Kanaele ("ch<Offset>", Byte): werden nie ueberblendet, sondern mit dem Beginn der Beam-Zeit (nach dem Delay) umgeschaltet
    raw_from: Dict[str, float] = field(default_factory=dict)
    raw_to: Dict[str, float] = field(default_factory=dict)
    # MIB-Snap: Position/Farbe/Beam dieser Fixture werden sofort (t=1.0) angewandt statt ueber die Gruppen-Fade-Zeit zu interpolieren - der Dimmer selbst ist davon NICHT betroffen.
    mib_snap: bool = False
    # MIB-Vorlauf: Werte des FOLGENDEN Cues, die ab `premove_after` Sekunden (nach Start dieses Cues) sofort angefahren werden, weil die Fixture dann dunkel ist.
    premove_to: Dict[str, Any] = field(default_factory=dict)
    premove_after: float = 0.0


def group_progress(elapsed: float, timing: Dict[str, Tuple[float, float]], group: str) -> float:
    delay, duration = timing.get(group, (0.0, 0.0))
    if elapsed < delay:
        return 0.0
    if duration <= 0.0:
        return 1.0
    return min(1.0, (elapsed - delay) / duration)


def fade_abstract(fade: FixtureFade, elapsed: float, timing: Dict[str, Tuple[float, float]]) -> Dict[str, Any]:
    """Die abstrakten Werte EINER Fixture nach `elapsed` Sekunden (vor dem Mix mit dem manuellen Wert)."""
    abstract_now: Dict[str, Any] = {}
    for attr, to_v in fade.scalars_to.items():
        from_v = fade.scalars_from.get(attr, to_v)
        group = ATTR_GROUPS.get(attr, "dimmer")
        t_attr = 1.0 if (fade.mib_snap and group != "dimmer") else group_progress(elapsed, timing, group)
        if attr in DISCRETE_ATTRS:                       # Gobo-/Prismenrad, Strobe-Bereich: umschalten, nicht durch die Slots fahren
            abstract_now[attr] = to_v if t_attr > 0.0 else from_v
        else:
            abstract_now[attr] = from_v + (to_v - from_v) * t_attr
    for attr, to_v in fade.raw_to.items():               # rohe Kanaele: Umschalten am Beginn der Beam-Zeit
        abstract_now[attr] = to_v if (fade.mib_snap or group_progress(elapsed, timing, "beam") > 0.0) else fade.raw_from.get(attr, to_v)
    if fade.color_to is not None:
        from_c = fade.color_from or {"r": 0, "g": 0, "b": 0}
        t_color = 1.0 if fade.mib_snap else group_progress(elapsed, timing, "color")
        abstract_now["color"] = {
            k: from_c.get(k, 0) + (fade.color_to.get(k, 0) - from_c.get(k, 0)) * t_color
            for k in ("r", "g", "b")
        }
    if fade.premove_to and elapsed >= fade.premove_after:       # MIB-Vorlauf: die Fixture ist dunkel, jetzt auf die Position des Folge-Cues
        for attr, value in fade.premove_to.items():
            abstract_now[attr] = copy.deepcopy(value)
    return abstract_now


# ---- Uebertragung an den Ausgabe-Prozess -------------------------------------------------------------------------------
def fade_to_dict(fade: FixtureFade) -> Dict[str, Any]:
    return {
        "sf": fade.scalars_from, "st": fade.scalars_to, "cf": fade.color_from, "ct": fade.color_to,
        "rf": fade.raw_from, "rt": fade.raw_to, "mib": fade.mib_snap, "pm": fade.premove_to, "pa": fade.premove_after,
    }


def fade_from_dict(d: Dict[str, Any]) -> FixtureFade:
    return FixtureFade(scalars_from=d.get("sf") or {}, scalars_to=d.get("st") or {}, color_from=d.get("cf"), color_to=d.get("ct"),
                       raw_from=d.get("rf") or {}, raw_to=d.get("rt") or {}, mib_snap=bool(d.get("mib")), premove_to=d.get("pm") or {},
                       premove_after=float(d.get("pa") or 0.0))


class _Fx:
    __slots__ = ("universe", "start_channel")

    def __init__(self, universe: int, start_channel: int) -> None:
        self.universe, self.start_channel = universe, start_channel


class FadePlayer:
    """Spielt die ihm uebergebenen Ueberblendungen mit der eigenen Uhr ab (Ausgabe-Prozess). `set_jobs` ersetzt die ganze Menge; ein Job lebt, bis der Server ihn nicht mehr schickt - nach seinem Ende
    haelt er den Endwert (bis das Bild des Servers ihn ebenfalls hat)."""

    def __init__(self) -> None:
        self.jobs: Dict[str, Dict[str, Any]] = {}
        self.levels: Dict[str, float] = {}

    def set_jobs(self, jobs: List[Dict[str, Any]], now: Optional[float] = None) -> None:
        now = time.monotonic() if now is None else now
        wanted: Dict[str, Dict[str, Any]] = {}
        for spec in jobs:
            fixtures = []
            for fid, (universe, start, key, fade, base) in (spec.get("fixtures") or {}).items():
                fixtures.append((_Fx(int(universe), int(start)), (spec.get("types") or {}).get(key, {}), fade_from_dict(fade), base or {}))
            wanted[spec["id"]] = {
                "timing": {g: (float(v[0]), float(v[1])) for g, v in (spec.get("timing") or {}).items()},
                "e0": float(spec.get("elapsed", 0.0)), "t_recv": now, "running": bool(spec.get("running", True)),
                "fixtures": fixtures,
            }
        self.jobs = wanted

    def set_levels(self, levels: Dict[str, float]) -> None:
        self.levels = {k: float(v) for k, v in (levels or {}).items()}

    def tick(self, now: float, master: float) -> Dict[int, Dict[int, int]]:
        """Die Kanalwerte aller laufenden Ueberblendungen jetzt: Universum -> {Kanal (1-512): Wert}."""
        out: Dict[int, Dict[int, int]] = {}
        for cuelist_id, job in self.jobs.items():
            elapsed = job["e0"] + ((now - job["t_recv"]) if job["running"] else 0.0)
            level = self.levels.get(cuelist_id, 1.0)
            for fx, offsets, fade, base in job["fixtures"]:
                abstract_now = fade_abstract(fade, elapsed, job["timing"])
                mixed = mix_abstract(base, abstract_now, level)
                batches: Dict[int, Dict[int, int]] = {}
                apply_abstract_values(fx, mixed, offsets, batches, pct_values=True, grand_master=master)
                for universe, channels in batches.items():
                    out.setdefault(universe, {}).update(channels)
        return out
