"""
fx_categories.py
Die Kategorien der Effekte: WAS ein Effekt steuert. Jede Kategorie nennt ihre Ausgabe-Variablen im Skript (z. B. r, g, b), deren Wertebereich und Neutralwert und
die abstrakten Attribute, die sie ansteuert (dieselben Schluessel wie in Cues und Presets: dimmer, color, pan, tilt ...; siehe dmx_resolve.apply_abstract_values).

Alles andere (Skript-Sprache, Engine, Cues, Studio) liest nur diese Tabelle. Eine neue Kategorie (Beam, Gobo, Rohwerte ...) ist ein weiterer Eintrag in CATEGORIES:
Ausgabenamen duerfen in keiner anderen Kategorie vorkommen, jedes Attribut gehoert genau einer Kategorie.
Dieses Modul importiert nichts aus dem Programm und kann deshalb von allen anderen Modulen benutzt werden.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple


@dataclass(frozen=True)
class Output:
    """Eine Ausgabe-Variable des Skripts, z. B. `pan` (0-100, Neutralwert 50)."""
    name: str                       # Variablenname im Skript
    low: float
    high: float
    neutral: Optional[float]        # Wert bei Effekt-Amplitude 0 / wenn das Skript nichts zuweist; None = optional: ohne Zuweisung im Skript bleibt der Kanal unberuehrt
    attr: str                       # abstraktes Attribut, in das der Wert geschrieben wird
    component: Optional[str] = None  # Teilwert eines zusammengesetzten Attributs (color -> r, g, b)


@dataclass(frozen=True)
class FxCategory:
    name: str
    outputs: Tuple[Output, ...]

    @property
    def output_names(self) -> Tuple[str, ...]:
        return tuple(o.name for o in self.outputs)

    @property
    def attrs(self) -> Tuple[str, ...]:
        return tuple(dict.fromkeys(o.attr for o in self.outputs))

    def used(self, assigned: Optional[Any]) -> Tuple[str, ...]:
        """Ausgaben, die ein Skript wirklich steuert: die zugewiesenen (Farbe nur als Ganzes r, g, b). Ohne Angabe oder ohne Zuweisung: alle Ausgaben."""
        names = set(assigned or ()) & set(self.output_names)
        if not names:
            return self.output_names
        if self.name == "color":
            return self.output_names
        return tuple(n for n in self.output_names if n in names)

    def attrs_of(self, used: Optional[Any] = None) -> Tuple[str, ...]:
        """Abstrakte Attribute der genannten Ausgaben (alle, wenn used None ist)."""
        if used is None:
            return self.attrs
        return tuple(dict.fromkeys(o.attr for o in self.outputs if o.name in set(used)))

    def _build(self, values: Dict[str, float], only: Optional[Any] = None) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        for o in self.outputs:
            if only is not None and o.name not in only:
                continue                                    # diese Ausgabe steuert der Effekt nicht: der Kanal bleibt frei
            raw = values.get(o.name, o.neutral)
            if raw is None:
                continue                                    # optionale Ausgabe, die das Skript nicht gesetzt hat
            value = max(o.low, min(o.high, float(raw)))
            if o.component:
                result.setdefault(o.attr, {})[o.component] = value
            else:
                result[o.attr] = value
        return result

    def to_abstract(self, out: Dict[str, float], only: Optional[Any] = None) -> Dict[str, Any]:
        """Ausgaben des Skripts -> abstrakte Werte (auf den Bereich begrenzt; Fehlendes = Neutralwert). only = nur diese Ausgaben (die das Skript steuert)."""
        return self._build(out, only)

    def neutral(self, only: Optional[Any] = None) -> Dict[str, Any]:
        """Abstrakte Werte bei Effekt-Amplitude 0 (Ziel des Ausblendens)."""
        return self._build({}, only)

    def describe(self) -> Dict[str, Any]:
        return {"name": self.name, "outputs": [{"name": o.name, "low": o.low, "high": o.high, "neutral": o.neutral, "optional": o.neutral is None} for o in self.outputs]}


CATEGORIES: Dict[str, FxCategory] = {c.name: c for c in (
    FxCategory("dimmer", (Output("dimmer", 0.0, 100.0, 0.0, "dimmer"),)),
    FxCategory("color", (Output("r", 0.0, 255.0, 0.0, "color", "r"), Output("g", 0.0, 255.0, 0.0, "color", "g"), Output("b", 0.0, 255.0, 0.0, "color", "b"))),
    FxCategory("position", (Output("pan", 0.0, 100.0, 50.0, "pan"), Output("tilt", 0.0, 100.0, 50.0, "tilt"))),
    FxCategory("zoom", (Output("zoom", 0.0, 100.0, 50.0, "zoom"),)),
    FxCategory("focus", (Output("focus", 0.0, 100.0, 50.0, "focus"),)),
    # Gobo: jede Ausgabe ist ein Wert 0-100 % (Stellung im DMX-Bereich des Kanals); das Skript setzt nur die, die es braucht. Hilfen: slots / slot(n) (Rad 1), slots2 / slot(n, 2) (Rad 2)
    FxCategory("gobo", (Output("gobo", 0.0, 100.0, 0.0, "gobo"), Output("gobo_spin", 0.0, 100.0, None, "gobo_spin"),
                        Output("gobo2", 0.0, 100.0, None, "gobo2"), Output("gobo2_spin", 0.0, 100.0, None, "gobo2_spin"))),
)}

# Abgeleitete Nachschlagetabellen
ATTR_CATEGORY: Dict[str, str] = {attr: c.name for c in CATEGORIES.values() for attr in c.attrs}
CATEGORY_ATTRS: Dict[str, Tuple[str, ...]] = {c.name: c.attrs for c in CATEGORIES.values()}
OUTPUTS_BY_CATEGORY: Dict[str, Tuple[str, ...]] = {c.name: c.output_names for c in CATEGORIES.values()}
OUTPUT_NAMES: Tuple[str, ...] = tuple(name for c in CATEGORIES.values() for name in c.output_names)

assert len(set(OUTPUT_NAMES)) == len(OUTPUT_NAMES), "Ausgabenamen muessen ueber alle Kategorien eindeutig sein"


def get(name: Any) -> Optional[FxCategory]:
    return CATEGORIES.get(name) if isinstance(name, str) else None


def describe() -> list:
    return [c.describe() for c in CATEGORIES.values()]
