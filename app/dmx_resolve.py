"""
dmx_resolve.py
Abstrakte Werte (dimmer/pan/tilt/color/beam-Attribute) <-> DMX-Byte-Werte.

Gemeinsam genutzt von server.py (Live-Programmer-Pfad, set_fixture_values)
und cue_engine.py (Cue-Firing samt Fade-Interpolation) - GENAU EINE Stelle
fuer die GDTF-Kanalaufloesung, damit Live-Programmer, Presets und Cues
niemals auseinanderlaufen (z.B. bei CMY- vs. RGB-Farbmischern).

"Abstrakte Werte" = GDTF-Profil-unabhaengiges Format:
  dimmer/pan/tilt/beam-Attribute (strobe/gobo/prism/focus/zoom): 0-100 (%)
  color: {"r": 0-255, "g": 0-255, "b": 0-255}
Dieses Format speichern sowohl Preset.values als auch
Cue.fixture_values[...]["values"].
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional

# Kanaele, deren rohes DMX-Byte die 3D-Simulation braucht (Slot des Farbrads nachschlagen); sie gehen als "wheels" im Live-Strom (fixtures_live) mit
WHEEL_CHANNELS = ("Color1", "Color2", "Shutter1", "Shutter1Strobe")      # Shutter/Strobe: Bereiche nachschlagen (/api/fixture-types/<Typ>/shutter)
WHEEL_PREFIXES = ("Gobo", "Prism")        # alle Gobo-/Prismen-Kanaele (Rad, Drehung, Position): Bereiche nachschlagen (/api/fixture-types/<Typ>/beamfx)

# Rohe Kanaele im Cue: jeder DMX-Kanal ohne eigenes abstraktes Attribut (Gobo-Rad 2, Drehung, Frost, Iris, Fein-Kanaele, Farbrad ...) steht als "ch<Offset>" (Byte 0-255) in den
# Werten des Programmers und der Cues - neben den abstrakten Attributen (dimmer, color, pan, tilt, strobe, gobo, prism, focus, zoom).
RAW_KEY = re.compile(r"^ch(\d{1,3})$")
DISCRETE_ATTRS = ("strobe", "gobo", "gobo_spin", "gobo2", "gobo2_spin", "prism")          # Raeder/Bereiche: nie ueberblenden (Zwischenwerte waeren andere Slots), sondern am Beginn der Gruppenzeit umschalten


def raw_offset(attr: Any) -> Optional[int]:
    """Kanal-Offset eines rohen Cue-Werts ("ch12" -> 12), sonst None."""
    match = RAW_KEY.match(attr) if isinstance(attr, str) else None
    return int(match.group(1)) if match else None


BEAM_ATTRS: Dict[str, str] = {
    "strobe": "Shutter1",
    "gobo": "Gobo1",                  # Gobo-Rad 1: Auswahl
    "gobo_spin": "Gobo1SelectSpin",   # Gobo-Rad 1: Drehung / Position (je nach Geraet ein anderer Kanalname, siehe BEAM_CANDIDATES)
    "gobo2": "Gobo2",                 # Gobo-Rad 2: Auswahl
    "gobo2_spin": "Gobo2SelectSpin",
    "prism": "Prism1",
    "focus": "Focus1",
    "zoom": "Zoom",
}
# Kanalnamen (GDTF-Attribute), die ein abstraktes Attribut bedeuten koennen - der erste, den das Geraet hat, gilt. Ohne Eintrag gilt BEAM_ATTRS.
BEAM_CANDIDATES: Dict[str, tuple] = {
    "gobo_spin": ("Gobo1PosRotate", "Gobo1Pos", "Gobo1SelectSpin"),
    "gobo2_spin": ("Gobo2PosRotate", "Gobo2Pos", "Gobo2SelectSpin"),
}


def beam_channels(names) -> Dict[str, str]:
    """abstraktes Beam-Attribut -> Kanalname fuer ein Geraet mit diesen Kanalnamen (nur vorhandene)."""
    present = set(names)
    out: Dict[str, str] = {}
    for attr, primary in BEAM_ATTRS.items():
        channel = next((c for c in BEAM_CANDIDATES.get(attr, (primary,)) if c in present), None)
        if channel is not None:
            out[attr] = channel
    return out


def beam_attr_by_channel(names) -> Dict[str, str]:
    """Kanalname -> abstraktes Beam-Attribut (Umkehrung von beam_channels fuer dieses Geraet)."""
    return {channel: attr for attr, channel in beam_channels(names).items()}


def pct_to_byte(pct: Any) -> float:
    """Wandelt einen 0-100%-Wert (Cue-/Preset-Speicherformat) in 0-255 um."""
    try:
        return max(0.0, min(255.0, float(pct) / 100.0 * 255.0))
    except (TypeError, ValueError):
        return 0.0


def byte_to_pct(byte: Any) -> float:
    """Kehrfunktion zu pct_to_byte() - ermittelt den Fade-Startpunkt aus dem
    zuletzt geschriebenen Fixture.values-Byte-Wert (siehe current_abstract_values)."""
    try:
        return max(0.0, min(100.0, float(byte) / 255.0 * 100.0))
    except (TypeError, ValueError):
        return 0.0


def fixture_channel_offsets(fx) -> Dict[str, int]:
    """GDTF-Kanalname -> Byte-Offset fuer den aktuell gepatchten Modus einer Fixture."""
    from app.fixture_manager import get_fixture_type_by_id
    fixture_type = get_fixture_type_by_id(fx.fixture_type)
    channels = []
    if fixture_type:
        modes = fixture_type.get("modes", [])
        mode_def = next((m for m in modes if m.get("name") == fx.mode), modes[0] if modes else None)
        if mode_def:
            channels = mode_def.get("channels", [])
    return {c["name"]: c["offset"] for c in channels}


def apply_abstract_values(
    fx,
    abstract: Dict[str, Any],
    offsets: Dict[str, int],
    universe_batches: Dict[int, Dict[int, int]],
    *,
    pct_values: bool,
    grand_master: float,
) -> Dict[str, int]:
    """Loest abstrakte Werte (dimmer/pan/tilt/color/beam-Attribute) in rohe
    DMX-Kanalschreibvorgaenge auf und traegt sie in universe_batches ein.
    Gibt die aufgeloesten Werte zurueck (fuer Fixture.values).

    pct_values=False: dimmer/pan/tilt/beam-Attribute liegen bereits als
    0-255-Byte vor (Live-Programmer-Pfad - das Frontend konvertiert bereits
    vor dem Senden). pct_values=True: sie liegen als 0-100%-Werte vor
    (Cue-/Preset-Speicherformat, auch waehrend Fade-Interpolation) und
    werden hier zu Byte konvertiert. color liegt in beiden Faellen immer
    als 0-255-RGB vor.

    grand_master (0-100%) skaliert ausschliesslich den Dimmer-Kanal, der
    Rueckgabewert (Fixture.values) bleibt unskaliert - so laesst sich die
    Ausgabe bei einer Master-Aenderung aus den gespeicherten Werten neu
    berechnen.
    """

    def _write(ch_name: str, val: float) -> bool:
        offset = offsets.get(ch_name)
        if offset is None:
            return False
        if ch_name == "Dimmer":
            val = val * grand_master / 100.0
        channel = fx.start_channel + offset
        universe_batches.setdefault(fx.universe, {})[channel] = max(0, min(255, int(round(val))))
        return True

    def _conv(v: Any) -> float:
        return pct_to_byte(v) if pct_values else float(v)

    def _axis(attr: str, coarse: str, fine: str) -> None:
        """Pan/Tilt. Hat das Profil einen Fein-Kanal (16 Bit), liegt der Wert als 16-Bit-Zahl vor:
        Grob-Byte = hohes, Fein-Byte = niedriges Byte. Sonst wie bisher nur das Grob-Byte."""
        value = abstract.get(attr)
        if value is None:
            return
        if offsets.get(fine) is not None:
            v16 = abstract.get(attr + "16")           # Live-Pfad: das Frontend schickt den 16-Bit-Wert mit
            if v16 is None:
                v16 = float(value) * 655.35 if pct_values else float(value) * 256.0
            v16 = max(0, min(65535, int(round(float(v16)))))
            if _write(coarse, v16 >> 8):
                resolved[coarse] = v16 >> 8
                if _write(fine, v16 & 0xFF):
                    resolved[fine] = v16 & 0xFF
            return
        bv = _conv(value)
        if _write(coarse, bv):
            resolved[coarse] = int(bv)

    resolved: Dict[str, int] = {}
    dimmer = abstract.get("dimmer")
    if dimmer is not None:
        bv = _conv(dimmer)
        if _write("Dimmer", bv):
            resolved["Dimmer"] = int(bv)
    _axis("pan", "Pan", "PanFine")
    _axis("tilt", "Tilt", "TiltFine")
    color = abstract.get("color")
    if color is not None:
        r, g, b = float(color.get("r", 0)), float(color.get("g", 0)), float(color.get("b", 0))
        out_r, out_g, out_b = (0.0, 0.0, 0.0) if (grand_master <= 0 and "Dimmer" not in offsets) else (r, g, b)      # ohne Dimmer-Kanal dunkelt nur die Farbe ab (Master 0 / Blackout)
        wrote_rgb = _write("ColorAdd_R", out_r) and _write("ColorAdd_G", out_g) and _write("ColorAdd_B", out_b)
        if not wrote_rgb:
            # Fallback fuer subtraktive CMY-Farbmischer (z.B. TMH-S400)
            _write("ColorSub_C", 255 - r)
            _write("ColorSub_M", 255 - g)
            _write("ColorSub_Y", 255 - b)
        resolved["Red"], resolved["Green"], resolved["Blue"] = int(r), int(g), int(b)
    for attr, ch_name in beam_channels(offsets).items():
        val = abstract.get(attr)
        if val is not None:
            bv = _conv(val)
            if _write(ch_name, bv):
                resolved[ch_name] = int(bv)
    top = max(offsets.values()) if offsets else -1
    for attr, val in abstract.items():                       # rohe Kanaele zuletzt: sie gewinnen (z. B. Fein-Byte nach der 16-Bit-Position)
        offset = raw_offset(attr)
        if offset is None or val is None or offset > top:
            continue
        byte = max(0, min(255, int(round(float(val)))))      # immer Byte, auch bei pct_values
        universe_batches.setdefault(fx.universe, {})[fx.start_channel + offset] = byte
        resolved[attr] = byte
    return resolved


def preset_to_abstract(preset) -> Dict[str, Any]:
    """Wandelt ein Preset in das abstrakte Werte-Format um (0-100% fuer
    dimmer/pan/tilt, 0-255 RGB fuer color) - identisch zum Cue-Speicherformat."""
    v = preset.values or {}
    if preset.type == "dimmer":
        return {"dimmer": v.get("level", 0)}
    if preset.type == "position":
        return {"pan": v.get("pan", 50), "tilt": v.get("tilt", 50)}
    if preset.type == "color":
        return {"color": {"r": v.get("r", 0), "g": v.get("g", 0), "b": v.get("b", 0)}}
    if preset.type in ("focus", "zoom"):
        return {preset.type: v.get("level", 0)}
    if preset.type == "gobo":                       # Gobo-Rad 1 (level) und optional Drehung, Rad 2, Drehung Rad 2: nur was im Preset steht
        out = {"gobo": v.get("level", 0)}
        for key, attr in (("spin", "gobo_spin"), ("gobo2", "gobo2"), ("gobo2_spin", "gobo2_spin")):
            if v.get(key) is not None:
                out[attr] = v[key]
        if v.get("level") is None and any(k in v for k in ("spin", "gobo2", "gobo2_spin")):
            out.pop("gobo")                         # Auswahl von Rad 1 ausdruecklich nicht gesetzt
        return out
    return {}


def current_abstract_values(fx) -> Dict[str, Any]:
    """Extrahiert den aktuellen Live-Zustand einer Fixture im abstrakten
    Format (0-100% / 0-255-RGB) aus ihrem Fixture.values-Byte-Cache - der
    Ausgangspunkt fuer eine neue Fade-Transition (siehe cue_engine.py).
    Attribute, die noch nie gesetzt wurden, fehlen im Ergebnis-Dict."""
    v = fx.values
    abstract: Dict[str, Any] = {}
    if "Dimmer" in v:
        abstract["dimmer"] = byte_to_pct(v["Dimmer"])
    for attr, coarse, fine in (("pan", "Pan", "PanFine"), ("tilt", "Tilt", "TiltFine")):
        if coarse in v:
            if fine in v:   # 16 Bit: Grob- und Fein-Byte zusammen
                abstract[attr] = max(0.0, min(100.0, (int(v[coarse]) * 256 + int(v[fine])) / 65535.0 * 100.0))
            else:
                abstract[attr] = byte_to_pct(v[coarse])
    if "Red" in v or "Green" in v or "Blue" in v:
        abstract["color"] = {"r": v.get("Red", 0), "g": v.get("Green", 0), "b": v.get("Blue", 0)}
    for attr, ch_name in beam_channels(v).items():
        abstract[attr] = byte_to_pct(v[ch_name])
    return abstract


_OFFSET_CACHE: Dict[Any, Dict[str, int]] = {}


def clear_offset_cache() -> None:
    _OFFSET_CACHE.clear()


def _offsets_cached(fx) -> Dict[str, int]:
    key = (fx.fixture_type, getattr(fx, "mode", ""))
    offsets = _OFFSET_CACHE.get(key)
    if offsets is None:
        offsets = fixture_channel_offsets(fx)
        _OFFSET_CACHE[key] = offsets
    return offsets


def abstract_from_dmx(fx, buf, grand_master: float) -> Dict[str, Any]:
    """Umkehrung von apply_abstract_values: liest die Werte einer Fixture aus dem DMX-Puffer (die Wahrheit - das, was der
    DMX-Monitor zeigt und ausgegeben wird) und liefert sie im abstrakten Format (0-100 % / RGB 0-255). Der Grand Master
    wird herausgerechnet (die Bedienelemente zeigen den Wert VOR dem Master); bei Master 0 ist der Dimmer nicht
    rekonstruierbar und fehlt dann."""
    offsets = _offsets_cached(fx)
    base = fx.start_channel - 1

    def byte(name: str):
        off = offsets.get(name)
        if off is None:
            return None
        idx = base + off
        return buf[idx] if 0 <= idx < len(buf) else None

    out: Dict[str, Any] = {}
    dim = byte("Dimmer")
    if dim is not None and grand_master > 0:
        out["dimmer"] = round(min(100.0, dim / 255.0 * 100.0 / (grand_master / 100.0)), 2)
    for attr, coarse, fine in (("pan", "Pan", "PanFine"), ("tilt", "Tilt", "TiltFine")):
        c = byte(coarse)
        if c is None:
            continue
        f = byte(fine)
        out[attr] = round(((c * 256 + f) / 65535.0 if f is not None else c / 255.0) * 100.0, 4)       # 16 Bit = 0,0015 % Aufloesung: vier Stellen, sonst geht beim Speichern Genauigkeit verloren
    r, g, b = byte("ColorAdd_R"), byte("ColorAdd_G"), byte("ColorAdd_B")
    if r is not None and g is not None and b is not None:
        if grand_master > 0 or dim is not None:             # ohne Dimmer-Kanal dunkelt der Master 0 / Blackout ueber die Farbe ab: dann nicht rekonstruierbar
            out["color"] = {"r": r, "g": g, "b": b}
    else:
        cy, ma, ye = byte("ColorSub_C"), byte("ColorSub_M"), byte("ColorSub_Y")
        if cy is not None and ma is not None and ye is not None:
            out["color"] = {"r": 255 - cy, "g": 255 - ma, "b": 255 - ye}
    for attr, ch_name in beam_channels(offsets).items():
        v = byte(ch_name)
        if v is not None:
            out[attr] = round(v / 255.0 * 100.0, 2)
    wheels = {name: byte(name) for name in offsets if (name in WHEEL_CHANNELS or name.startswith(WHEEL_PREFIXES)) and byte(name) is not None}
    if wheels:
        out["wheels"] = wheels
    return out
