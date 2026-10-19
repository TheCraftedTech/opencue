"""
command_line.py
dot2-/MA-Lighting-Stil Befehlszeilen-Parser fuer OpenCue.

Syntax-Philosophie (vollstaendige Referenz: documentation/commands.md):
    [Aktion/Objekt] [ID/Bereich] [Eigenschaft/Ziel]
z.B. "Fixture 1 Thru 10", "At 80", "Store Cue 1.5", "Go Cue 3".

execute_command() ist die einzige oeffentliche Schnittstelle. Sie nimmt
einen rohen Befehlsstring entgegen (ggf. mehrere, durch Komma getrennte
Befehle, sequenziell abgearbeitet), parst ihn, fuehrt ihn auf
state_manager.state (Selektion/Programmer) bzw. der globalen
cue_engine.cue_engine (Cue-Trigger) aus und gibt ein JSON-faehiges
Ergebnis-Dict zurueck: {"success": bool, "message": str}.

`broadcast` ist ein async callable(message_type: str, payload: dict), das
der Aufrufer (server.py ODER cue_engine.py's automatische CMD-Ausfuehrung,
siehe dort) uebergibt - die Handler rufen es auf, wann immer sich State
aendert, der andere Panels betrifft (Selektion, Programmer, Fixtures,
CueLists, DMX-Output). Dieses Modul kennt den WebSocket-EventBus selbst
NICHT (gleiches Prinzip wie cue_engine.py - vermeidet einen Zirkelimport).

SELEKTION IST SERVER-AUTORITATIV: state.selected_fixture_ids ist die
gemeinsame, fuer alle verbundenen Clients sichtbare Selektion (siehe
state_manager.py). Maus-Klicks im Frontend synchronisieren sich ueber
"set_selection" (server.py) ebenfalls dorthin.

DIREKTE KOMBI-BEFEHLE: Nach einer Fixture-/Group-ID-Spezifikation koennen
beliebig viele Attribut-Klauseln direkt angehaengt werden, z.B.
"Fixture 1 Thru 5 At 80 Color Red" - siehe _consume_clause()/
_apply_attr_spec(). Dieselben Klausel-Parser bedienen auch die
eigenstaendigen Top-Level-Befehle "At"/"Color"/"RGB"/"Pan"/"Tilt", die auf
die AKTUELLE Selektion wirken.
"""

from __future__ import annotations

import math
import re
import time
from contextvars import ContextVar
from typing import Any, Awaitable, Callable, Dict, List, Optional, Set, Tuple

from app.dmx_engine import DMX_UNIVERSE_SIZE, dmx_engine
from app.fx_engine import fx_engine
from app.dmx_resolve import (
    apply_abstract_values, beam_attr_by_channel, beam_channels, byte_to_pct, current_abstract_values,
    fixture_channel_offsets, pct_to_byte, preset_to_abstract, raw_offset,
)
from app.state_manager import Cue, CueList, state

Broadcast = Callable[[str, Dict[str, Any]], Awaitable[None]]


class _CommandError(Exception):
    """Fuer den Benutzer bestimmte Fehlermeldung (ohne Traceback im Log)."""


# ---------------------------------------------------------------------------
# Tokenizer & Hilfsfunktionen
# ---------------------------------------------------------------------------

class _Tok(str):
    """Ein Wort der Eingabe. `quoted` = stand in Anfuehrungszeichen (ein Name, nie ein Schluesselwort)."""

    quoted: bool = False


def _scan(raw: str) -> List[Tuple[_Tok, int, int, bool]]:
    """Zerlegt einen Befehl in (Token, Start, Ende, Anfuehrungszeichen_offen)-Eintraege. Woerter in doppelten Anfuehrungszeichen bleiben ein Token
    (z.B. Label Cue 1 "Szene Intro"); ein nicht geschlossenes Anfuehrungszeichen reicht bis zum Ende (wichtig fuer die Vorschlaege beim Tippen)."""
    out: List[Tuple[_Tok, int, int, bool]] = []
    i, n = 0, len(raw)
    while i < n:
        if raw[i].isspace():
            i += 1
            continue
        start = i
        buf: List[str] = []
        quoted = False
        is_open = False
        while i < n and not raw[i].isspace():
            if raw[i] == '"':
                quoted = True
                i += 1
                while i < n and raw[i] != '"':
                    if raw[i] == "\\" and i + 1 < n and raw[i + 1] in ('"', "\\"):
                        i += 1
                    buf.append(raw[i])
                    i += 1
                if i >= n:
                    is_open = True
                i += 1
            else:
                buf.append(raw[i])
                i += 1
        tok = _Tok("".join(buf))
        tok.quoted = quoted
        out.append((tok, start, min(i, n), is_open))
    return out


def _tokenize(raw: str) -> List[_Tok]:
    return [item[0] for item in _scan(raw)]


def _split_commands(raw: str) -> List[str]:
    """Teilt einen Eingabe-String bei Kommas oder Semikolons in mehrere sequenziell zu
    verarbeitende Befehle - respektiert dabei Trennzeichen INNERHALB doppelter
    Anfuehrungszeichen (z.B. Label Cue 1 "Akt 1, Szene 2" darf nicht am
    Komma im Namen auseinandergerissen werden)."""
    parts: List[str] = []
    current: List[str] = []
    in_quotes = False
    for ch in raw:
        if ch == '"':
            in_quotes = not in_quotes
            current.append(ch)
        elif ch in ",;" and not in_quotes:
            parts.append("".join(current).strip())
            current = []
        else:
            current.append(ch)
    parts.append("".join(current).strip())
    return [p for p in parts if p]


def _parse_float(tok: str) -> float:
    try:
        value = float(tok)
    except (TypeError, ValueError):
        raise _CommandError(f"Invalid number: {tok}")
    if not math.isfinite(value):                    # 'nan' / 'inf' sind keine Eingabewerte
        raise _CommandError(f"Invalid number: {tok}")
    return value


def _parse_int(tok: str) -> int:
    return int(_parse_float(tok))


def _fmt_fixture_count(n: int) -> str:
    return f"{n} fixture" if n == 1 else f"{n} fixtures"


def _fmt_num(n: float) -> str:
    return f"{n:g}"


def _split_on_plus(tokens: List[str]) -> List[List[str]]:
    groups: List[List[str]] = [[]]
    for tok in tokens:
        if tok == "+":
            groups.append([])
        else:
            groups[-1].append(tok)
    return [g for g in groups if g]


def _parse_id_spec(tokens: List[str]) -> List[int]:
    """Parst z.B. ["1","Thru","10","+","15"] -> sortierte, deduplizierte
    Nummern-Liste. Jeder durch "+" getrennte Teilausdruck ist entweder "N"
    oder "N Thru M" (Reihenfolge von Start/Ende wird toleriert)."""
    numbers: List[int] = []
    for grp in _split_on_plus(tokens):
        if len(grp) == 1:
            numbers.append(_parse_int(grp[0]))
        elif len(grp) == 3 and grp[1].lower() == "thru":
            start, end = _parse_int(grp[0]), _parse_int(grp[2])
            lo, hi = (start, end) if start <= end else (end, start)
            numbers.extend(range(lo, hi + 1))
        else:
            raise _CommandError(f"Invalid range: {' '.join(grp)}")
    return sorted(set(numbers))


# Zielliste fuer 'Cuelist <name> <Befehl>': gilt nur waehrend dieses einen Befehls (Task-lokal), die aktive Liste bleibt unveraendert.
_target_list: ContextVar[Optional[str]] = ContextVar("opencue_command_target_list", default=None)


def _active_cuelist() -> CueList:
    target = _target_list.get()
    if target is not None:
        cl = state.cuelists.get(target)
        if cl is None:
            raise _CommandError("Cue list not found")
        return cl
    cl = state.cuelists.get(state.active_cuelist_id) if state.active_cuelist_id else None
    if cl is None:
        raise _CommandError("No active Cue List selected")
    return cl


def _find_cue_by_number(cl: CueList, number: float) -> Optional[Cue]:
    for cue in cl.cues:
        if abs(cue.number - number) < 1e-6:
            return cue
    return None


def _cuelists_payload() -> Dict[str, Any]:
    from app.cue_engine import cue_engine  # deferred: vermeidet Zirkelimport beim Modul-Laden
    return {
        "cuelists": state.cuelists_as_dicts(),
        "active_cuelist_id": state.active_cuelist_id,
        "active_cue_ids": dict(state.active_cue_ids),
        "cue_playback": cue_engine.playback_snapshot(),       # der Fortschrittsbalken passt zum neuen aktiven Cue (wie der Broadcast des Servers)
        "is_dirty": state.is_dirty,
    }


async def _broadcast_fixtures(broadcast: Broadcast) -> None:
    await broadcast("fixtures_changed", {"fixtures": state.fixtures_as_dicts(), "is_dirty": state.is_dirty})


# ---------------------------------------------------------------------------
# Benannte Farben (fuer "Color <name>")
# ---------------------------------------------------------------------------

_NAMED_COLORS: Dict[str, Tuple[int, int, int]] = {
    "red": (255, 0, 0), "green": (0, 255, 0), "blue": (0, 0, 255),
    "white": (255, 255, 255), "black": (0, 0, 0), "yellow": (255, 255, 0),
    "cyan": (0, 255, 255), "magenta": (255, 0, 255), "orange": (255, 128, 0),
    "pink": (255, 105, 180), "purple": (128, 0, 255), "amber": (255, 191, 0),
    "lime": (128, 255, 0), "teal": (0, 160, 160), "violet": (148, 0, 211), "lightblue": (100, 180, 255),
    "warm": (255, 197, 143), "cool": (201, 226, 255),
}

# Fallback-Gradbereich fuer Pan/Tilt, falls das GDTF-Profil der Fixture
# keinen eigenen physical_from/physical_to-Bereich definiert - identisch
# zum Frontend-Fallback (siehe _panTiltPhysicalRange() in app.js).
_PAN_TILT_DEFAULTS: Dict[str, Tuple[float, float]] = {"pan": (-270.0, 270.0), "tilt": (-135.0, 135.0)}


def _degrees_to_pct(fx, axis: str, degrees: float) -> float:
    """Wandelt eine Gradangabe (Pan/Tilt-Befehl) in den 0-100%-Wert um, den
    das abstrakte Werteformat erwartet - anhand des physical_from/
    physical_to-Bereichs des GDTF-Kanals dieser Fixture, mit Fallback auf
    _PAN_TILT_DEFAULTS falls das Profil keinen eigenen Bereich angibt."""
    from app.fixture_manager import get_fixture_type_by_id
    lo, hi = _PAN_TILT_DEFAULTS[axis]
    fixture_type = get_fixture_type_by_id(fx.fixture_type)
    if fixture_type:
        modes = fixture_type.get("modes", [])
        mode_def = next((m for m in modes if m.get("name") == fx.mode), modes[0] if modes else None)
        if mode_def:
            ch_name = "Pan" if axis == "pan" else "Tilt"
            ch = next((c for c in mode_def.get("channels", []) if c.get("name") == ch_name), None)
            if ch and isinstance(ch.get("physical_from"), (int, float)) and isinstance(ch.get("physical_to"), (int, float)):
                lo, hi = float(ch["physical_from"]), float(ch["physical_to"])
    if hi == lo:
        return 50.0
    return max(0.0, min(100.0, (degrees - lo) / (hi - lo) * 100.0))


# ---------------------------------------------------------------------------
# Attribut-Klauseln: At/Full/Color/RGB/Pan/Tilt, Beam-Attribute, Kanaele
# ---------------------------------------------------------------------------
# Jeder Parser gibt (spec_fragment, verbrauchte_tokens, anzeige_label)
# zurueck. spec_fragment-Schluessel (mehrere Klauseln werden mit _merge_spec() zusammengefuehrt):
#   "dimmer": ("abs"|"rel", float)         - At <value> / At +N / At -N / Full
#   "color":  {"r","g","b"}               - Color <name|#hex|r g b> / RGB <r> <g> <b>
#   "axis":   {"pan"|"tilt": (kind, mode, wert)}
#                                         - Pan/Tilt: kind "deg" (Grad, je Fixture in Prozent umgerechnet, da der Gradbereich
#                                           variiert) oder "pct" (0-100 %); mode "abs"|"rel"
#   "beam":   {attr: (mode, pct)}         - Zoom/Focus/Gobo/Gobo2/Prism/Strobe/... in Prozent
#   "chan":   [(ref, mode, wert, einheit)] - ein Kanal des Geraets: ref = Nummer (1 = erster Kanal des Geraets) oder GDTF-Kanalname,
#                                           einheit "byte" (0-255, DMX direkt) oder "pct" (0-100 %)

# Beam-Attribute der Befehlszeile (normalisiert: klein, ohne Leerzeichen/Unterstrich) -> abstraktes Attribut
_BEAM_KEYWORDS: Dict[str, str] = {
    "zoom": "zoom", "focus": "focus", "gobo": "gobo", "gobo1": "gobo", "gobo2": "gobo2",
    "gobospin": "gobo_spin", "gobo1spin": "gobo_spin", "gobo2spin": "gobo2_spin",
    "prism": "prism", "strobe": "strobe", "shutter": "strobe",
}
_BEAM_LABELS: Dict[str, str] = {
    "zoom": "Zoom", "focus": "Focus", "gobo": "Gobo", "gobo2": "Gobo2", "gobo_spin": "GoboSpin",
    "gobo2_spin": "Gobo2Spin", "prism": "Prism", "strobe": "Strobe",
}
_ATTR_KEYWORDS = {"at", "full", "color", "colour", "rgb", "pan", "tilt", "channel", "ch", "variable", "var", "preset", "effect", "fx", "manual", "release"} | set(_BEAM_KEYWORDS)
_CHANNEL_TOKEN = re.compile(r"^(?:ch|channel)(\d+)$", re.IGNORECASE)
_LEVEL_WORDS: Dict[str, float] = {"full": 100.0, "max": 100.0, "half": 50.0, "min": 0.0, "zero": 0.0}

# Kanalnamen (GDTF-Attribute) -> gaengige Kurzschreibweisen der Befehlszeile ("Frost 50", "Cyan 80")
_CHANNEL_ALIASES: Dict[str, str] = {
    "intensity": "dimmer", "dim": "dimmer", "shutter": "shutter1", "colorwheel": "color1", "wheel": "color1",
    "cyan": "colorsubc", "magenta": "colorsubm", "yellow": "colorsuby",
    "red": "coloraddr", "green": "coloraddg", "blue": "coloraddb", "white": "coloraddw", "amber": "coloraddra",
    "speed": "positionmspeed",
}


class _Incomplete(_CommandError):
    """Eine Klausel ist noch nicht fertig getippt (es fehlt ein Wert) - fuer die Vorschlaege (Tab) ein Hinweis auf den erwarteten Wert."""


def _norm(text: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", str(text).lower())


def _is_clause_keyword(tok: Any) -> bool:
    return _norm(tok) in _ATTR_KEYWORDS or bool(_CHANNEL_TOKEN.match(str(tok)))


def _parse_level(tok: Any) -> Tuple[str, float, bool]:
    """Wert einer Klausel: '50', '50%', '+10', '-10', 'Full', 'Half', 'Min' -> (mode "abs"|"rel", Zahl, in_prozent).
    Ohne %-Zeichen ist 'in_prozent' False - Kanaele per Nummer lesen das dann als DMX-Wert (0-255)."""
    raw = str(tok).strip()
    low = raw.lower()
    if low in _LEVEL_WORDS:
        return "abs", _LEVEL_WORDS[low], True
    percent = low.endswith("%")
    body = low[:-1] if percent else low
    if not re.fullmatch(r"[+-]?(\d+(\.\d*)?|\.\d+)", body):
        raise _CommandError(f"Invalid number: {raw}")
    return ("rel" if body[0] in "+-" else "abs"), float(body), percent


def _pct(value: float) -> float:
    return max(0.0, min(100.0, value))


def _parse_at_clause(tokens: List[str], idx: int) -> Tuple[Dict[str, Any], int, str]:
    if tokens[idx].lower() == "full":
        return {"dimmer": ("abs", 100.0)}, 1, "Full"
    if idx + 1 >= len(tokens):
        raise _Incomplete("At: missing value (e.g. 'At 80', 'At Full', 'At +10')")
    raw = tokens[idx + 1]
    token = raw.lower()
    if token == "at":  # "At At" == "At Full"
        return {"dimmer": ("abs", 100.0)}, 2, "At Full"
    mode, value, _percent = _parse_level(raw)
    return {"dimmer": (mode, value if mode == "rel" else _pct(value))}, 2, f"At {raw}"


# Benannte Farben (fuer "Color <name>")
def _parse_color_clause(tokens: List[str], idx: int) -> Tuple[Dict[str, Any], int, str]:
    if idx + 1 >= len(tokens):
        raise _Incomplete("Color: missing name (e.g. 'Color Red', 'Color #FF8800' or 'Color 255 128 0')")
    name = tokens[idx + 1]
    text = str(name)
    hex_match = re.fullmatch(r"#?([0-9a-fA-F]{6}|[0-9a-fA-F]{3})", text) if text.startswith("#") else None
    if hex_match:
        digits = hex_match.group(1)
        if len(digits) == 3:
            digits = "".join(ch * 2 for ch in digits)
        r, g, b = (int(digits[i:i + 2], 16) for i in (0, 2, 4))
        return {"color": {"r": r, "g": g, "b": b}}, 2, f"Color #{digits.upper()}"
    if re.fullmatch(r"\d+", text):                                    # Color 255 128 0
        if idx + 3 >= len(tokens):
            raise _Incomplete("Color: expected 'Color <r> <g> <b>' (each 0-255)")
        r, g, b = (max(0, min(255, _parse_int(tokens[idx + 1 + k]))) for k in range(3))
        return {"color": {"r": r, "g": g, "b": b}}, 4, f"Color {r} {g} {b}"
    rgb = _NAMED_COLORS.get(_norm(text))
    if rgb is None:
        raise _CommandError(f"Unknown color: {name}")
    return {"color": {"r": rgb[0], "g": rgb[1], "b": rgb[2]}}, 2, f"Color {text.capitalize()}"


def _parse_rgb_clause(tokens: List[str], idx: int) -> Tuple[Dict[str, Any], int, str]:
    if idx + 3 >= len(tokens):
        raise _Incomplete("RGB: expected 'RGB <r> <g> <b>' (each 0-255)")
    r, g, b = (max(0, min(255, _parse_int(tokens[idx + 1 + k]))) for k in range(3))
    return {"color": {"r": r, "g": g, "b": b}}, 4, f"RGB {r} {g} {b}"


def _parse_pantilt_clause(tokens: List[str], idx: int) -> Tuple[Dict[str, Any], int, str]:
    axis = tokens[idx].lower()
    if idx + 1 >= len(tokens):
        raise _Incomplete(f"{axis.capitalize()}: missing value (degrees, or a percentage like 50%)")
    raw = tokens[idx + 1]
    mode, value, percent = _parse_level(raw)
    if percent:
        return {"axis": {axis: ("pct", mode, value if mode == "rel" else _pct(value))}}, 2, f"{axis.capitalize()} {raw}"
    return {"axis": {axis: ("deg", mode, value)}}, 2, f"{axis.capitalize()} {raw}°"


def _parse_beam_clause(tokens: List[str], idx: int) -> Tuple[Dict[str, Any], int, str]:
    attr = _BEAM_KEYWORDS[_norm(tokens[idx])]
    label = _BEAM_LABELS[attr]
    if idx + 1 >= len(tokens):
        raise _Incomplete(f"{label}: missing value (0-100, e.g. '{label} 50', '{label} Full', '{label} +10')")
    raw = tokens[idx + 1]
    mode, value, _percent = _parse_level(raw)
    return {"beam": {attr: (mode, value if mode == "rel" else _pct(value))}}, 2, f"{label} {raw}"


def _parse_channel_clause(tokens: List[str], idx: int) -> Tuple[Dict[str, Any], int, str]:
    """'CH3 128' / 'Channel 3 128' / 'Channel Frost1 50' / 'CH3 50%'. Nummer = Kanal des Geraets (1 = erster), Wert 0-255 wie im DMX Direkt;
    mit % oder per Namen 0-100 %."""
    head = str(tokens[idx])
    match = _CHANNEL_TOKEN.match(head)
    if match:
        ref: Any = int(match.group(1))
        pos = idx + 1
    else:
        if idx + 1 >= len(tokens):
            raise _Incomplete("Channel: expected 'Channel <number|name> <value>' (e.g. 'CH3 128', 'Channel Frost 50')")
        ref_tok = str(tokens[idx + 1])
        ref = int(ref_tok) if re.fullmatch(r"\d+", ref_tok) else ref_tok
        pos = idx + 2
    if isinstance(ref, int) and ref < 1:
        raise _CommandError("Channel numbers start at 1")
    if pos >= len(tokens):
        raise _Incomplete(f"Channel {ref}: missing value (0-255, or 0-100% with %)")
    raw = tokens[pos]
    mode, value, percent = _parse_level(raw)
    unit = "pct" if (percent or isinstance(ref, str)) else "byte"
    return {"chan": [(ref, mode, value, unit)]}, pos + 1 - idx, f"Channel {ref} {raw}"


def _parse_named_channel_clause(tokens: List[str], idx: int) -> Tuple[Dict[str, Any], int, str]:
    """Jeder GDTF-Kanalname direkt als Klausel: 'Frost 50', 'Iris 30', 'Cyan 80' (Prozent). Ob das Geraet den Kanal hat, zeigt sich beim Anwenden."""
    name = str(tokens[idx])
    if idx + 1 >= len(tokens):
        raise _Incomplete(f"{name}: missing value (0-100)")
    try:
        mode, value, _percent = _parse_level(tokens[idx + 1])
    except _CommandError:
        raise _CommandError(f"Unknown attribute: {name}")
    return {"chan": [(name, mode, value, "pct")]}, 2, f"{name} {tokens[idx + 1]}"


def _consume_clause(tokens: List[str], idx: int) -> Tuple[Dict[str, Any], int, str]:
    tok = str(tokens[idx])
    kw = _norm(tok)
    if kw == "at" or kw == "full":
        return _parse_at_clause(tokens, idx)
    if kw in ("color", "colour"):
        return _parse_color_clause(tokens, idx)
    if kw == "rgb":
        return _parse_rgb_clause(tokens, idx)
    if kw in ("pan", "tilt"):
        return _parse_pantilt_clause(tokens, idx)
    if kw in _BEAM_KEYWORDS:
        return _parse_beam_clause(tokens, idx)
    if kw in ("channel", "ch") or _CHANNEL_TOKEN.match(tok):
        return _parse_channel_clause(tokens, idx)
    if kw in _VARIABLE_KEYWORDS:
        return _parse_variable_clause(tokens, idx)
    if kw in _EFFECT_KEYWORDS:
        return _parse_effect_clause(tokens, idx)
    if kw in _MANUAL_KEYWORDS:
        return _parse_manual_clause(tokens, idx)
    return _parse_named_channel_clause(tokens, idx)


def _merge_spec(spec: Dict[str, Any], fragment: Dict[str, Any]) -> None:
    for key, value in fragment.items():
        if key in ("axis", "beam"):
            spec.setdefault(key, {}).update(value)
        elif key in ("chan", "ops"):
            spec.setdefault(key, []).extend(value)
        else:
            spec[key] = value


def _parse_clauses(tokens: List[str]) -> Tuple[Dict[str, Any], List[str]]:
    spec: Dict[str, Any] = {}
    labels: List[str] = []
    idx = 0
    while idx < len(tokens):
        fragment, consumed, label = _consume_clause(tokens, idx)
        _merge_spec(spec, fragment)
        labels.append(label)
        idx += consumed
    return spec, labels


def _find_channel(offsets: Dict[str, int], ref: Any) -> Optional[Tuple[str, int]]:
    """Kanal eines Geraets: per Nummer (1 = Offset 0) oder per Name - exakt, per Kurzform ('Frost' fuer 'Frost1'), per Alias ('Cyan') oder eindeutigem Anfang.
    Gibt (GDTF-Kanalname, Offset) zurueck oder None."""
    if isinstance(ref, int):
        return next(((name, off) for name, off in offsets.items() if off == ref - 1), None)
    want = _norm(ref)
    if not want:
        return None
    by_norm = {_norm(name): name for name in offsets}
    want = _CHANNEL_ALIASES.get(want, want) if want not in by_norm else want
    if want in by_norm:
        return by_norm[want], offsets[by_norm[want]]
    for matcher in (lambda n: re.sub(r"\d+$", "", n) == want, lambda n: n.startswith(want)):
        hits = [name for n, name in by_norm.items() if matcher(n)]
        if len(hits) == 1:
            return hits[0], offsets[hits[0]]
    return None


def _current_pct(fx, attr: str) -> float:
    """Aktueller Wert (0-100 %) eines abstrakten Attributs: Programmer-Wert, sonst der zuletzt ausgegebene."""
    current = state.programmer_values.get(fx.id, {}).get(attr)
    if current is None:
        current = current_abstract_values(fx).get(attr, 50.0 if attr in ("pan", "tilt") else 0.0)
    return float(current)


def _degrees_range(fx, axis: str) -> Tuple[float, float]:
    from app.fixture_manager import get_fixture_type_by_id
    lo, hi = _PAN_TILT_DEFAULTS[axis]
    fixture_type = get_fixture_type_by_id(fx.fixture_type)
    if fixture_type:
        modes = fixture_type.get("modes", [])
        mode_def = next((m for m in modes if m.get("name") == fx.mode), modes[0] if modes else None)
        if mode_def:
            ch = next((c for c in mode_def.get("channels", []) if c.get("name") == ("Pan" if axis == "pan" else "Tilt")), None)
            if ch and isinstance(ch.get("physical_from"), (int, float)) and isinstance(ch.get("physical_to"), (int, float)):
                lo, hi = float(ch["physical_from"]), float(ch["physical_to"])
    return lo, hi


def _build_fixture_values(fx, spec: Dict[str, Any], missing: Dict[str, int]) -> Dict[str, Any]:
    """Abstrakte Werte (Programmer-Format) fuer EIN Geraet; was es nicht hat, zaehlt in `missing` (Anzeigename -> Anzahl Geraete)."""
    abstract: Dict[str, Any] = {}
    offsets = fixture_channel_offsets(fx)
    if "dimmer" in spec:
        mode, val = spec["dimmer"]
        abstract["dimmer"] = _pct(_current_pct(fx, "dimmer") + val) if mode == "rel" else val
    if "color" in spec:
        abstract["color"] = spec["color"]
    for axis, (kind, mode, num) in spec.get("axis", {}).items():
        if kind == "deg":
            if mode == "rel":
                lo, hi = _degrees_range(fx, axis)
                abstract[axis] = _pct(_current_pct(fx, axis) + (num / (hi - lo) * 100.0 if hi != lo else 0.0))
            else:
                abstract[axis] = _degrees_to_pct(fx, axis, num)
        else:
            abstract[axis] = _pct(_current_pct(fx, axis) + num) if mode == "rel" else num
    beam = beam_channels(offsets)
    for attr, (mode, num) in spec.get("beam", {}).items():
        if attr not in beam:
            missing[_BEAM_LABELS[attr]] = missing.get(_BEAM_LABELS[attr], 0) + 1
            continue
        abstract[attr] = _pct(_current_pct(fx, attr) + num) if mode == "rel" else num
    if spec.get("chan"):
        attr_by_channel = {"Dimmer": "dimmer", "Pan": "pan", "Tilt": "tilt", **beam_attr_by_channel(offsets)}
        for ref, mode, num, unit in spec["chan"]:
            found = _find_channel(offsets, ref)
            if found is None:
                shown = f"Channel {ref}" if isinstance(ref, int) else str(ref)
                missing[shown] = missing.get(shown, 0) + 1
                continue
            name, offset = found
            attr = attr_by_channel.get(name)
            step = num * 255.0 / 100.0 if unit == "pct" else num
            if mode == "rel":
                if attr:
                    base = pct_to_byte(_current_pct(fx, attr))
                else:
                    base = state.programmer_values.get(fx.id, {}).get(f"ch{offset}")
                    base = float(base) if base is not None else float(fx.values.get(name, 0))
                byte = base + step
            else:
                byte = step
            byte = int(max(0, min(255, round(byte))))
            if attr:
                abstract[attr] = byte_to_pct(byte)
            else:
                abstract[f"ch{offset}"] = byte
    return abstract


def _plan_spec(fixtures: List[Any], spec: Dict[str, Any]) -> Tuple[List[Tuple[Any, Dict[str, Any]]], List[str]]:
    """Berechnet fuer jedes Geraet die abstrakten Werte (ohne etwas zu schreiben). Ein Attribut, das KEIN Geraet hat, ist ein Fehler;
    fehlt es nur einzelnen, kommt ein Hinweis zurueck."""
    missing: Dict[str, int] = {}
    planned: List[Tuple[Any, Dict[str, Any]]] = []
    for fx in fixtures:
        abstract = _build_fixture_values(fx, spec, missing)
        if abstract:
            planned.append((fx, abstract))
    unknown = [name for name, count in missing.items() if count >= len(fixtures)]
    if unknown:
        raise _CommandError(f"Unknown attribute: {', '.join(unknown)} (the selected {'fixture has' if len(fixtures) == 1 else 'fixtures have'} no such channel)")
    return planned, [f"{name} not available on {count} of {len(fixtures)} fixtures" for name, count in missing.items()]


async def _apply_attr_spec(spec: Dict[str, Any], broadcast: Broadcast) -> List[str]:
    """Wendet ein per _parse_clauses() gebautes Spec auf ALLE aktuell selektierten Fixtures an - schreibt DMX, aktualisiert
    state.programmer_values (fuer "Store Cue") und broadcastet Live-Werte. Gibt Hinweise zurueck (Attribute, die einzelne Geraete
    nicht haben); ein Attribut, das KEIN selektiertes Geraet hat, ist ein Fehler (dann wird nichts angewendet)."""
    if not state.selected_fixture_ids:
        raise _CommandError("No fixtures selected")
    fixtures_sel = [state.fixtures[i] for i in state.selected_fixture_ids if i in state.fixtures]
    planned, notes = _plan_spec(fixtures_sel, spec)

    universe_batches: Dict[int, Dict[int, int]] = {}
    affected_universes: Set[int] = set()
    live_values: Dict[str, Any] = {}

    for fx, abstract in planned:
        state.set_programmer_values(fx.id, abstract)
        state.release_layers(fx.id, list(abstract))      # der Programmer uebernimmt: Cue-Listen mischen diese Attribute nicht mehr
        offsets = fixture_channel_offsets(fx)
        resolved = apply_abstract_values(
            fx, abstract, offsets, universe_batches,
            pct_values=True, grand_master=state.effective_master(fx.id),
        )
        if resolved:
            state.set_fixture_values(fx.id, resolved)
            affected_universes.add(fx.universe)
        live_values[fx.id] = abstract

    for universe, ch_map in universe_batches.items():
        dmx_engine.commit_batch(universe, ch_map)
    for universe in affected_universes:
        await broadcast("dmx_universe_changed", {
            "universe": universe, "values": dmx_engine.get_universe_snapshot(universe),
        })
    await _broadcast_fixtures(broadcast)
    # programmer_command_update: aktualisiert Fader/Regler UND markiert sie
    # als "touched" (rote Markierung) - anders als das gleich geformte
    # programmer_live_update der CueEngine, das bewusst NICHT touched
    # markiert (Cue-Playback ist keine manuelle Bedienung).
    if live_values:
        await broadcast("programmer_command_update", {"values": live_values})
    await broadcast("programmer_refs", {"refs": state.programmer_refs_payload()})          # ein fester Wert loest eine Variable ab
    if spec.get("ops"):                                                                    # Variablen / Effekte / Manuell: nach den Werten, der Reihe nach
        await _run_ops([fx.id for fx in fixtures_sel], spec["ops"], broadcast)
    return notes


# ---------------------------------------------------------------------------
# Selektion: Fixture / Group (inkl. direkter Kombi-Befehle)
# ---------------------------------------------------------------------------

def _is_number(tok: Any) -> bool:
    return bool(re.fullmatch(r"[+-]?(\d+(\.\d*)?|\.\d+)", str(tok)))


def _parse_selection(tokens: List[str]) -> Tuple[List[int], List[str]]:
    """'1 Thru 10 + 15 + "Front"' -> (sortierte Nummern, Namen). Ein Teil ist 'N', 'N Thru M' oder ein Name (in Anfuehrungszeichen oder ein einzelnes Wort)."""
    numbers: List[int] = []
    names: List[str] = []
    for grp in _split_on_plus(tokens):
        if len(grp) == 1 and not (_is_number(grp[0]) and not getattr(grp[0], "quoted", False)):
            names.append(str(grp[0]))
        else:
            numbers.extend(_parse_id_spec(grp))
    return sorted(set(numbers)), names


def _split_spec(rest: List[str], known_names: Set[str]) -> int:
    """Index, ab dem die Attribut-Klauseln beginnen: die ID-Angabe besteht aus Nummern, Thru, +, Namen in Anfuehrungszeichen und
    unquotierten Namen, die es gibt. Ein Schluesselwort (At, Color, Zoom, CH3 ...) beendet sie; ein sonst unbekanntes Wort
    nach der ID-Angabe ist ein Kanalname ('Fixture 1 Frost 50')."""
    for i, tok in enumerate(rest):
        low = str(tok).lower()
        if low in ("+", "thru") or _is_number(tok) or getattr(tok, "quoted", False):
            continue
        if _is_clause_keyword(tok):
            return i
        if low in known_names:
            continue
        return i
    return len(rest)


async def _select_and_apply(
    rest: List[str], broadcast: Broadcast, *, resolve_ids, noun: str, known_names: Set[str],
) -> Dict[str, Any]:
    """Gemeinsame Logik fuer 'Fixture <spec> [Attribut-Klauseln...]' und
    'Group <spec> [Attribut-Klauseln...]'. resolve_ids(numbers, names) -> (ids, missing)."""
    if not rest:
        raise _CommandError(f"{noun}: missing ID (e.g. '{noun} 1' or '{noun} 1 Thru 10')")
    split_idx = _split_spec(rest, known_names)
    spec_tokens, attr_tokens = rest[:split_idx], rest[split_idx:]
    if not spec_tokens:
        if not _is_clause_keyword(rest[0]):                 # ein unbekannter Name (oder Tippfehler) statt einer ID
            raise _CommandError(f"No matching {noun.lower()}s for: {rest[0]}")
        raise _CommandError(f"{noun}: missing ID (e.g. '{noun} 1' or '{noun} 1 Thru 10')")

    numbers, names = _parse_selection(spec_tokens)
    ids, missing = resolve_ids(numbers, names)
    if not ids:
        raise _CommandError(f"No matching {noun.lower()}s for: {' '.join(spec_tokens)}")
    clauses: Tuple[Dict[str, Any], List[str]] = ({}, [])
    if attr_tokens:
        clauses = _parse_clauses(attr_tokens)              # zuerst pruefen: bei einem Tippfehler aendert sich die Auswahl nicht
        _plan_spec([state.fixtures[i] for i in ids if i in state.fixtures], clauses[0])
    state.set_selection(ids)
    await broadcast("selection_changed", {"selected_ids": state.selected_fixture_ids})
    msg = f"OK: {_fmt_fixture_count(len(state.selected_fixture_ids))} selected"
    if missing:
        msg += f" ({noun} not found: {', '.join(map(str, missing))})"

    if attr_tokens:
        spec, labels = clauses
        notes = await _apply_attr_spec(spec, broadcast)
        msg += f"; {' '.join(labels)} applied"
        if notes:
            msg += f" ({'; '.join(notes)})"
    return {"success": True, "message": msg}


async def _cmd_fixture(rest: List[str], broadcast: Broadcast) -> Dict[str, Any]:
    fid_to_id = {fx.fid: fx.id for fx in state.fixtures.values()}

    def resolve(numbers: List[int], names: List[str]) -> Tuple[List[str], List[str]]:
        ids = [fid_to_id[n] for n in numbers if n in fid_to_id]
        missing = [str(n) for n in numbers if n not in fid_to_id]
        for name in names:
            hits = [fx.id for fx in state.fixtures.values() if fx.name.strip().lower() == name.strip().lower()]
            if hits:
                ids.extend(h for h in hits if h not in ids)
            else:
                missing.append(f'"{name}"')
        return ids, missing

    known = {fx.name.strip().lower() for fx in state.fixtures.values()}
    return await _select_and_apply(rest, broadcast, resolve_ids=resolve, noun="Fixture", known_names=known)


async def _cmd_group(rest: List[str], broadcast: Broadcast) -> Dict[str, Any]:
    group_names = list(state.groups.keys())

    def resolve(numbers: List[int], names: List[str]) -> Tuple[List[str], List[str]]:
        ids: Set[str] = set()
        missing: List[str] = []
        for n in numbers:
            if 1 <= n <= len(group_names):
                ids.update(state.groups[group_names[n - 1]])
            else:
                missing.append(str(n))
        for name in names:
            key = next((g for g in group_names if g.strip().lower() == name.strip().lower()), None)
            if key is None:
                missing.append(f'"{name}"')
            else:
                ids.update(state.groups[key])
        return sorted(ids), missing

    return await _select_and_apply(rest, broadcast, resolve_ids=resolve, noun="Group", known_names={g.strip().lower() for g in group_names})


# ---------------------------------------------------------------------------
# Top-Level Attribut-Befehle (wirken auf die AKTUELLE Selektion)
# ---------------------------------------------------------------------------

async def _cmd_attr(tokens: List[str], broadcast: Broadcast) -> Dict[str, Any]:
    """'At 50', 'Color Red', 'Zoom 30', 'CH3 128', 'Frost 50' ... - eine oder mehrere Klauseln hintereinander auf die Selektion."""
    if not state.selected_fixture_ids:
        raise _CommandError(f"{str(tokens[0]).capitalize()}: no fixtures selected")
    spec, labels = _parse_clauses(tokens)
    notes = await _apply_attr_spec(spec, broadcast)
    msg = f"OK: {' '.join(labels)} applied to {_fmt_fixture_count(len(state.selected_fixture_ids))}"
    if notes:
        msg += f" ({'; '.join(notes)})"
    return {"success": True, "message": msg}


# ---------------------------------------------------------------------------
# Variablen, Effekte und "Manuell" (als Klauseln: 'Fixture 1 Variable "Warm" Effect Regenbogen')
# ---------------------------------------------------------------------------
# spec["ops"]: Liste von Vorgaengen, die NACH den Werten der Reihe nach ausgefuehrt werden:
#   ("variable", Preset)          - Variable anwenden UND verknuepfen (Platzhalter)
#   ("effect", fx_id, kategorie)  - Effekt zuweisen
#   ("manual", kategorien)        - Variable-Verknuepfung und Effekt dieser Kategorien loesen; die Werte bleiben
#   ("release_fx", kategorien)    - nur Effekte dieser Kategorien beenden

_VARIABLE_KEYWORDS = {"variable", "var", "preset"}
_EFFECT_KEYWORDS = {"effect", "fx"}
_MANUAL_KEYWORDS = {"manual", "release"}
_FX_CATEGORY_WORDS = {"dimmer": "dimmer", "intensity": "dimmer", "color": "color", "colour": "color", "position": "position", "pos": "position",
                      "zoom": "zoom", "focus": "focus", "gobo": "gobo"}
_OFF_WORDS = {"off", "stop", "none", "manual", "release"}


def _norm_name(text: Any) -> str:
    return " ".join(str(text).split()).lower()


def _take_name(tokens: List[str], idx: int) -> Tuple[str, int]:
    """Name ab tokens[idx]: ein Wort in Anfuehrungszeichen, sonst alle Woerter bis zum naechsten Schluesselwort ('Warm White' ohne Anfuehrungszeichen geht)."""
    first = tokens[idx]
    if getattr(first, "quoted", False):
        return str(first), 1
    words = [str(first)]
    j = idx + 1
    while j < len(tokens) and not getattr(tokens[j], "quoted", False) and not _is_clause_keyword(tokens[j]):
        words.append(str(tokens[j]))
        j += 1
    return " ".join(words), j - idx


def _find_variable(name: str):
    hits = [p for p in state.presets.values() if _norm_name(p.name) == _norm_name(name)]
    if not hits:
        names = ", ".join(f'"{p.name}"' for p in state.presets.values()) or "none"
        raise _CommandError(f'Unknown variable: {name} (available: {names})')
    return hits[0]


def _find_effect(name: str) -> Tuple[str, str, str]:
    """(fx_id, Kategorie, Name) des Effekts mit diesem Namen."""
    for fx_id, definition in state.fx_effects.items():
        if _norm_name(definition.get("name", "")) == _norm_name(name):
            category = fx_engine._category_of(fx_id)
            if category is None:
                raise _CommandError(f'Effect "{definition.get("name")}" has no valid script')
            return fx_id, category, str(definition.get("name", ""))
    names = ", ".join(f'"{d.get("name")}"' for d in state.fx_effects.values()) or "none"
    raise _CommandError(f'Unknown effect: {name} (available: {names})')


def _take_categories(tokens: List[str], idx: int) -> Tuple[List[str], int]:
    cats: List[str] = []
    j = idx
    while j < len(tokens) and not getattr(tokens[j], "quoted", False):
        word = str(tokens[j]).lower()
        if word == "all":
            return [], j + 1 - idx            # leer = alle Kategorien
        if word not in _FX_CATEGORY_WORDS:
            break
        cats.append(_FX_CATEGORY_WORDS[word])
        j += 1
    return list(dict.fromkeys(cats)), j - idx


def _parse_variable_clause(tokens: List[str], idx: int) -> Tuple[Dict[str, Any], int, str]:
    if idx + 1 >= len(tokens):
        raise _Incomplete('Variable: missing name (e.g. Variable "Warm White")')
    name, used = _take_name(tokens, idx + 1)
    preset = _find_variable(name)
    return {"ops": [("variable", preset)]}, 1 + used, f"Variable {preset.name}"


def _parse_effect_clause(tokens: List[str], idx: int) -> Tuple[Dict[str, Any], int, str]:
    if idx + 1 >= len(tokens):
        raise _Incomplete('Effect: missing name (e.g. Effect "Regenbogen") or Effect Off [color|position|...]')
    nxt = tokens[idx + 1]
    if not getattr(nxt, "quoted", False) and str(nxt).lower() in _OFF_WORDS:
        cats, used = _take_categories(tokens, idx + 2)
        return {"ops": [("release_fx", cats)]}, 2 + used, "Effect Off" + (f" {' '.join(cats)}" if cats else "")
    name, used = _take_name(tokens, idx + 1)
    fx_id, category, real_name = _find_effect(name)
    return {"ops": [("effect", fx_id, category)]}, 1 + used, f"Effect {real_name}"


def _parse_manual_clause(tokens: List[str], idx: int) -> Tuple[Dict[str, Any], int, str]:
    cats, used = _take_categories(tokens, idx + 1)
    return {"ops": [("manual", cats)]}, 1 + used, "Manual" + (f" {' '.join(cats)}" if cats else "")


async def release_fixtures(fixture_ids: List[str], broadcast: Broadcast) -> None:
    """Gibt Fixtures frei (Effekt-Zuweisung entfernt) und zeigt sofort den gespeicherten Stand."""
    ids = list(dict.fromkeys(fixture_ids))
    if not ids:
        return
    restore_fixture_outputs(ids)
    values = {fid: current_abstract_values(state.fixtures[fid]) for fid in ids if fid in state.fixtures and state.fixtures[fid].values}
    values = {fid: v for fid, v in values.items() if v}
    if values:
        await broadcast("programmer_live_update", {"values": values})


async def apply_preset_to_fixtures(fixture_ids: List[str], preset, broadcast: Broadcast, *, live: bool = False) -> None:
    """Wendet eine Variable auf Fixtures an UND verknuepft sie: die Fixture folgt der Variable, bis ein manueller Wert, ein Effekt oder ein Cue das Attribut
    uebernimmt. live=True (die Variable wurde geaendert): gleiche Ausgabe, aber ohne die Werte als "angefasst" zu markieren."""
    import copy
    ids = [fid for fid in dict.fromkeys(fixture_ids) if fid in state.fixtures]
    abstract = preset_to_abstract(preset)
    if not ids or not abstract:
        return
    if not live:
        await release_fixtures(fx_engine.assign(ids, preset.type, None), broadcast)         # ein Effekt dieser Kategorie endet: die Variable gibt jetzt vor
    batches: Dict[int, Dict[int, int]] = {}
    changed: Dict[str, Dict[str, Any]] = {}
    universes: Set[int] = set()
    for fid in ids:
        fx = state.fixtures[fid]
        state.release_layers(fid, list(abstract))                                           # der Programmer uebernimmt: Cue-Listen mischen diese Attribute nicht mehr
        resolved = apply_abstract_values(fx, copy.deepcopy(abstract), fixture_channel_offsets(fx), batches,
                                         pct_values=True, grand_master=state.effective_master(fid))
        if resolved:
            state.set_fixture_values(fid, resolved)
            universes.add(fx.universe)
        state.set_programmer_values(fid, copy.deepcopy(abstract))
        state.set_programmer_ref(fid, preset.type, preset.id)                               # nach dem Setzen: set_programmer_values loest alte Verknuepfungen
        changed[fid] = copy.deepcopy(abstract)
    for universe, ch_map in batches.items():
        dmx_engine.commit_batch(universe, ch_map)
    for universe in universes:
        await broadcast("dmx_universe_changed", {"universe": universe, "values": dmx_engine.get_universe_snapshot(universe)})
    await broadcast("programmer_values_quiet" if live else "programmer_command_update", {"values": changed})
    await broadcast("programmer_refs", {"refs": state.programmer_refs_payload()})


async def _run_ops(ids: List[str], ops: List[Tuple[Any, ...]], broadcast: Broadcast) -> None:
    """Variablen/Effekte/Manuell der Klauseln der Reihe nach auf die Fixtures `ids` anwenden."""
    for op in ops:
        kind = op[0]
        if kind == "variable":
            await apply_preset_to_fixtures(ids, op[1], broadcast)
        elif kind == "effect":
            _kind, fx_id, category = op
            released = fx_engine.assign(ids, category, fx_id)
            for fid in ids:
                state.drop_programmer_refs(fid, types=[category])                # der Effekt gibt diese Kategorie jetzt vor, nicht mehr eine Variable
            await release_fixtures(released, broadcast)
            state.mark_dirty()
            await broadcast("fx_changed", fx_engine.state_payload())
            await broadcast("programmer_refs", {"refs": state.programmer_refs_payload()})
        else:                                                                       # manual / release_fx
            from app.state_manager import PRESET_TYPES
            cats = list(op[1]) or list(PRESET_TYPES)
            released: List[str] = []
            for category in cats:
                released += fx_engine.assign(ids, category, None)
                if kind == "manual":
                    for fid in ids:
                        state.drop_programmer_refs(fid, types=[category])
            await release_fixtures(released, broadcast)
            if released:
                state.mark_dirty()
            await broadcast("fx_changed", fx_engine.state_payload())
            await broadcast("programmer_refs", {"refs": state.programmer_refs_payload()})


# ---------------------------------------------------------------------------
# Cue-Listen anlegen / umbenennen / duplizieren / loeschen
# ---------------------------------------------------------------------------

async def delete_cuelist(cuelist_id: str, broadcast: Broadcast) -> bool:
    """Loescht eine Cue-Liste samt Aufraeumen (laufende Ueberblendung endet, Executor mit dieser Liste fallen auf 'Aktive Liste' zurueck)."""
    from app.cue_engine import cue_engine  # deferred
    if cuelist_id not in state.cuelists:
        return False
    cue_engine.forget(cuelist_id)                         # laufende Ueberblendung/Follow der Liste enden, die DMX-Werte bleiben stehen
    state.delete_cuelist(cuelist_id)
    rebound = [p for p in state.panels if p.type == "executor" and p.module_config.get("cuelist_id") == cuelist_id]
    for panel in rebound:
        panel.module_config = {**panel.module_config, "cuelist_id": ""}
    if rebound:
        state.save_app_config()
        await broadcast("panels_changed", {"panels": state.panels_as_dicts()})
    await broadcast("cuelists_changed", _cuelists_payload())
    return True


async def _cmd_cuelist_object(head: str, rest: List[str], broadcast: Broadcast) -> Dict[str, Any]:
    """Cuelist New ["Name"] | Cuelist <Name> Rename "<neu>" | Duplicate ["<Name>"] | Delete."""
    if head in ("new", "create", "add"):
        name = " ".join(str(t) for t in rest).strip()
        cl = state.add_cuelist(name)
        if cl is None:
            raise _CommandError(f'Cue list "{name}" already exists (names are unique)')
        await broadcast("cuelists_changed", _cuelists_payload())
        return {"success": True, "message": f'OK: Cue list "{cl.name}" created'}
    cl = _active_cuelist()                                 # die Liste steht ueber _target_list fest (Cuelist <Name> <Befehl>)
    if head == "rename":
        new = " ".join(str(t) for t in rest).strip()
        if not new:
            raise _Incomplete('Rename: missing name (e.g. Cuelist Show Rename "Akt 1")')
        if state.cuelist_name_taken(new, cl.id):
            raise _CommandError(f'Cue list "{new}" already exists (names are unique)')
        old = cl.name
        state.rename_cuelist(cl.id, new)
        await broadcast("cuelists_changed", _cuelists_payload())
        return {"success": True, "message": f'OK: Cue list "{old}" renamed to "{state.cuelists[cl.id].name}"'}
    if head == "duplicate":
        name = " ".join(str(t) for t in rest).strip()
        copy_ = state.duplicate_cuelist(cl.id, name or None)
        if copy_ is None:
            raise _CommandError(f'Cue list "{name}" already exists (names are unique)')
        await broadcast("cuelists_changed", _cuelists_payload())
        return {"success": True, "message": f'OK: Cue list "{cl.name}" duplicated as "{copy_.name}"'}
    name = cl.name                                         # delete
    await delete_cuelist(cl.id, broadcast)
    return {"success": True, "message": f'OK: Cue list "{name}" deleted'}


# ---------------------------------------------------------------------------
# Gruppen: Store Group / Delete Group / Label Group
# ---------------------------------------------------------------------------

def _find_group(tokens: List[str]) -> str:
    """Gruppenname (Gross-/Kleinschreibung egal, auch mehrere Woerter) oder Nummer (N-te Gruppe) -> der Gruppenname."""
    if not tokens:
        raise _Incomplete("Group: missing name or number")
    text = _norm_name(" ".join(str(t) for t in tokens))
    for name in state.groups:
        if _norm_name(name) == text:
            return name
    if re.fullmatch(r"\d+", text):
        names = list(state.groups)
        if 1 <= int(text) <= len(names):
            return names[int(text) - 1]
    avail = ", ".join(f'"{g}"' for g in state.groups) or "none"
    raise _CommandError(f"Group not found: {' '.join(str(t) for t in tokens)} (available: {avail})")


async def _broadcast_groups(broadcast: Broadcast) -> None:
    await broadcast("fixture_groups_changed", {"groups": state.groups, "is_dirty": state.is_dirty})


async def _cmd_store_group(rest: List[str], broadcast: Broadcast) -> Dict[str, Any]:
    """Store Group "<Name>" [Merge|Overwrite]: legt eine Gruppe aus der aktuellen Auswahl an (bei vorhandenem Namen: Merge = Auswahl hinzufuegen,
    Overwrite = Mitglieder ersetzen). Wie im Gruppen-Dialog gehoert ein Geraet hoechstens einer Gruppe an."""
    option: Optional[str] = None
    words = list(rest)
    if words and not getattr(words[-1], "quoted", False) and str(words[-1]).lower() in ("merge", "overwrite"):
        option = str(words.pop()).lower()
    name = state.clean_group_name(" ".join(str(t) for t in words))
    if not name:
        raise _Incomplete('Store Group: missing name (e.g. Store Group "Front")')
    ids = [i for i in state.selected_fixture_ids if i in state.fixtures]
    if not ids:
        raise _CommandError("Store Group: no fixtures selected")
    existing = next((g for g in state.groups if _norm_name(g) == _norm_name(name)), None)
    if existing is not None and option is None:
        raise _CommandError(f'Group "{existing}" already exists - use \'Store Group "{existing}" Merge\' or \'... Overwrite\'')
    if existing is None:
        existing = state.add_fixture_group(name)
        verb = "created"
    else:
        verb = "merged" if option == "merge" else "overwritten"
        if option == "overwrite":
            state.groups[existing] = []
            state.mark_dirty()
    state.assign_fixture_group(ids, existing)
    await _broadcast_groups(broadcast)
    return {"success": True, "message": f'OK: Group "{existing}" {verb} ({_fmt_fixture_count(len(state.groups[existing]))})'}


async def _cmd_delete_group(rest: List[str], broadcast: Broadcast) -> Dict[str, Any]:
    name = _find_group(rest)
    state.delete_fixture_group(name)
    await _broadcast_groups(broadcast)
    return {"success": True, "message": f'OK: Group "{name}" deleted (the fixtures stay)'}


async def _cmd_rename_group(rest: List[str], broadcast: Broadcast) -> Dict[str, Any]:
    """Label Group <Name|Nr> "<neu>"  /  Set Group <Name|Nr> Name "<neu>"."""
    if len(rest) < 2:
        raise _Incomplete('Label Group: expected \'Label Group <name|number> "<new name>"\'')
    # Alt-Name: alles bis auf das letzte Token (nur dieses ist der neue Name, in Anfuehrungszeichen); 'Name' (Set) wird uebersprungen
    words = [t for t in rest]
    new = str(words.pop())
    if words and str(words[-1]).lower() == "name" and not getattr(words[-1], "quoted", False):
        words.pop()
    old = _find_group(words)
    if not state.rename_fixture_group(old, new):
        raise _CommandError(f'Group "{new}" already exists or the name is empty')
    await _broadcast_groups(broadcast)
    return {"success": True, "message": f'OK: Group "{old}" renamed to "{state.clean_group_name(new)}"'}


# ---------------------------------------------------------------------------
# Clear / Clear Clear (mit 1s-Doppel-Clear-Fenster)
# ---------------------------------------------------------------------------

_last_clear_at: Optional[float] = None
_CLEAR_CLEAR_WINDOW = 1.0  # Sekunden


# Kanaele, die schon ueber Dimmer/Farbe/Pan/Tilt/Beam-Attribute zurueckgesetzt werden (alles andere kommt als roher Kanal dazu)
_RESET_COVERED_CHANNELS = ("Dimmer", "Pan", "Tilt", "PanFine", "TiltFine",
                           "ColorAdd_R", "ColorAdd_G", "ColorAdd_B", "ColorSub_C", "ColorSub_M", "ColorSub_Y")


def _full_reset_abstract(fx) -> Dict[str, Any]:
    """Baseline-Neutralwerte fuer EINE Fixture - der 'kein Programmer-
    Override, keine Cue aktiv'-Ruhezustand: Dimmer/Beam auf 0 (aus/
    geschlossen), Farbe geloescht (schwarz), Pan/Tilt auf 0 Grad. Pan/Tilt
    werden ueber denselben physical_from/physical_to-Bereich wie ein
    'Pan 0'/'Tilt 0'-Befehl aufgeloest (siehe _degrees_to_pct) - ein fest
    verdrahteter 50%-Mittelwert waere bei einem asymmetrischen GDTF-Profil
    (0 Grad != Kanalmitte) falsch."""
    abstract: Dict[str, Any] = {
        "dimmer": 0.0,
        "color": {"r": 0, "g": 0, "b": 0},
        "pan": _degrees_to_pct(fx, "pan", 0.0),
        "tilt": _degrees_to_pct(fx, "tilt", 0.0),
        "strobe": 0.0,
        "gobo": 0.0,
        "gobo_spin": 0.0,
        "gobo2": 0.0,
        "gobo2_spin": 0.0,
        "prism": 0.0,
        "focus": 0.0,
        "zoom": 0.0,
    }
    # Alles andere, was das Geraet hat (Frost, Iris, Farbrad, Drehungen, Fein-Kanaele, Geschwindigkeit ...), steht als roher Kanal auf 0 -
    # "Clear Clear" heisst wirklich alles zurueck, damit danach jedes Attribut frisch eingestellt werden kann.
    offsets = fixture_channel_offsets(fx)
    covered = set(_RESET_COVERED_CHANNELS) | set(beam_channels(offsets).values())
    for name, offset in offsets.items():
        if name not in covered:
            abstract[f"ch{offset}"] = 0
    return abstract


async def apply_full_baseline_reset(broadcast: Broadcast) -> Dict[str, Any]:
    """Vollstaendiger Baseline-Reset ueber ALLE gepatchten Fixtures -
    ausgeloest von "Clear Clear" (siehe _cmd_clear) UND einmalig beim
    Programmstart/Engine-Init (siehe server.py's lifespan()). Setzt
    AUSNAHMSLOS jede gepatchte Fixture auf ihre Baseline-Standardwerte
    zurueck (nicht nur die aktuell im Programmer befindlichen) - schreibt
    das tatsaechlich als DMX aus (nicht nur kosmetisch in der Anzeige),
    entfernt alle Programmer-Overrides (touched-Status) und hebt die
    Selektion vollstaendig auf. Bewusst ohne Ausnahme fuer gerade per Cue
    angesteuerte Fixtures - "Clear Clear" ist ein expliziter Full-Blackout,
    kein selektiver Programmer-Release."""
    # Effekte zuerst beenden, sonst wuerde der FX-Thread den Baseline-Wert wieder ueberschreiben.
    fx_engine.clear_all()
    affected = list(state.fixtures.keys())
    universe_batches: Dict[int, Dict[int, int]] = {}
    affected_universes: Set[int] = set()
    reset_values: Dict[str, Any] = {}

    for fx_id in affected:
        fx = state.fixtures.get(fx_id)
        if fx is None:
            continue
        abstract = _full_reset_abstract(fx)
        state.release_layers(fx_id)
        offsets = fixture_channel_offsets(fx)
        resolved = apply_abstract_values(
            fx, abstract, offsets, universe_batches,
            pct_values=True, grand_master=state.effective_master(fx_id),
        )
        if resolved:
            state.set_fixture_values(fx_id, resolved)
            affected_universes.add(fx.universe)
        reset_values[fx_id] = {k: v for k, v in abstract.items() if raw_offset(k) is None}      # die Oberflaeche kennt nur abstrakte Attribute

    for universe, ch_map in universe_batches.items():
        dmx_engine.commit_batch(universe, ch_map)
    for universe in affected_universes:
        await broadcast("dmx_universe_changed", {
            "universe": universe, "values": dmx_engine.get_universe_snapshot(universe),
        })

    # "ausnahmslos": clear_programmer() ohne fixture_ids-Filter leert ALLE
    # Overrides, nicht nur die der oben zurueckgesetzten Fixtures.
    state.clear_programmer()
    state.set_selection([])

    if affected_universes:
        await _broadcast_fixtures(broadcast)
    await broadcast("selection_changed", {"selected_ids": []})
    if affected:
        # reset_values traegt die tatsaechlichen Neutralwerte JEDER gepatchten
        # Fixture - das Frontend synct damit Scheinwerfer-Karten/Farbfelder/
        # 2D-Positionierungs-Raster auf den neuen (dunklen/neutralen) Zustand,
        # zusaetzlich zum reinen Aufraeumen der touched-Markierung (siehe
        # ProgrammerState.syncFromEngine()/clearTouchedByIds() in app.js).
        await broadcast("programmer_cleared", {
            "fixture_ids": affected, "reset_values": reset_values, "reset_dropdowns": True,
        })
    await broadcast("programmer_refs", {"refs": state.programmer_refs_payload()})
    await broadcast("fx_changed", fx_engine.state_payload())
    return {"success": True, "message": "OK: All fixtures reset to baseline (dimmer, color, position, beam, wheels and every other channel at 0)"}


async def write_stored_outputs(broadcast: Broadcast) -> None:
    """Fallback fuer Showfiles ohne gespeicherten DMX-Block: berechnet die
    Ausgabe aller Fixtures aus Fixture.values neu (mit Grand Master)."""
    universe_batches: Dict[int, Dict[int, int]] = {}
    affected_universes: Set[int] = set()
    for fx in state.fixtures.values():
        abstract = current_abstract_values(fx) if fx.values else {}
        if not abstract:
            continue
        apply_abstract_values(
            fx, abstract, fixture_channel_offsets(fx), universe_batches,
            pct_values=True, grand_master=state.effective_master(fx.id),
        )
        affected_universes.add(fx.universe)

    for universe, ch_map in universe_batches.items():
        dmx_engine.commit_batch(universe, ch_map)
    for universe in affected_universes:
        await broadcast("dmx_universe_changed", {
            "universe": universe, "values": dmx_engine.get_universe_snapshot(universe),
        })


def restore_fixture_outputs(fixture_ids: List[str]) -> None:
    """Gibt Fixtures nach einem Effekt frei: zurueck auf die gespeicherten Werte
    bzw. auf die Baseline, falls noch nichts gespeichert ist. Synchron, wird vom
    FX-Thread aufgerufen."""
    batches: Dict[int, Dict[int, int]] = {}
    with fx_engine.lock:
        for fid in fixture_ids:
            fx = state.fixtures.get(fid)
            if fx is None:
                continue
            abstract = current_abstract_values(fx) if fx.values else {}
            if not abstract:
                abstract = _full_reset_abstract(fx)
            apply_abstract_values(
                fx, abstract, fixture_channel_offsets(fx), batches,
                pct_values=True, grand_master=state.effective_master(fx.id),
            )
        for universe, ch_map in batches.items():
            dmx_engine.commit_batch(universe, ch_map)


def restore_dmx_universes(universes: Dict[int, Dict[int, int]]) -> None:
    """Setzt jedes Universum exakt auf den gespeicherten Stand - Kanaele ohne
    Eintrag werden 0. Universen, die in der Datei fehlen, werden ebenfalls auf 0
    gesetzt, damit ein Showfile-Load keine Reste der vorherigen Show stehen laesst."""
    for universe in set(universes) | set(dmx_engine.universe_numbers()):
        saved = universes.get(universe, {})
        dmx_engine.commit_batch(
            universe, {ch: saved.get(ch, 0) for ch in range(1, DMX_UNIVERSE_SIZE + 1)},
        )


async def _rescale_dimmers(broadcast: Broadcast) -> None:
    """Berechnet die Dimmer-Kanaele aus dem unskalierten Wert in Fixture.values mit dem Grand Master (bzw. Blackout) neu.
    Pan/Tilt und Beam bleiben unberuehrt; Geraete OHNE Dimmer-Kanal (reine RGB-Geraete) dunkeln ueber ihre Farbe ab (nur bei Master 0 / Blackout)."""
    universe_batches: Dict[int, Dict[int, int]] = {}
    affected_universes: Set[int] = set()
    for fx in state.fixtures.values():
        raw = fx.values.get("Dimmer")
        offsets = fixture_channel_offsets(fx)
        offset = offsets.get("Dimmer")
        if offset is None:
            if all(k in fx.values for k in ("Red", "Green", "Blue")):
                apply_abstract_values(fx, {"color": {"r": fx.values["Red"], "g": fx.values["Green"], "b": fx.values["Blue"]}}, offsets, universe_batches,
                                      pct_values=True, grand_master=state.effective_master(fx.id))
                affected_universes.add(fx.universe)
            continue
        if raw is None:
            continue
        universe_batches.setdefault(fx.universe, {})[fx.start_channel + offset] = max(
            0, min(255, int(round(raw * state.effective_master(fx.id) / 100.0))),
        )
        affected_universes.add(fx.universe)

    for universe, ch_map in universe_batches.items():
        dmx_engine.commit_batch(universe, ch_map)
    for universe in affected_universes:
        await broadcast("dmx_universe_changed", {
            "universe": universe, "values": dmx_engine.get_universe_snapshot(universe),
        })


def _remember_unscaled_output() -> None:
    """Vor dem Blackout: Helligkeit/Farbe jedes Geraets, die noch nicht in Fixture.values stehen (z. B. von einem Effekt geschrieben), aus dem DMX-Puffer
    uebernehmen (mit herausgerechnetem Master) - sonst gaebe es nach dem Blackout nichts wiederherzustellen."""
    master = state.effective_master("")
    if master <= 0:
        return
    for fx in state.fixtures.values():
        offsets = fixture_channel_offsets(fx)
        buf = dmx_engine.get_universe_snapshot(fx.universe)
        base = fx.start_channel - 1
        off = offsets.get("Dimmer")
        if off is not None and "Dimmer" not in fx.values and 0 <= base + off < len(buf):
            fx.values["Dimmer"] = max(0, min(255, int(round(buf[base + off] * 100.0 / master))))
        elif off is None and not all(k in fx.values for k in ("Red", "Green", "Blue")):
            for key, name in (("Red", "ColorAdd_R"), ("Green", "ColorAdd_G"), ("Blue", "ColorAdd_B")):
                o = offsets.get(name)
                if o is not None and 0 <= base + o < len(buf):
                    fx.values[key] = buf[base + o]


async def set_blackout(enabled: Optional[bool], broadcast: Broadcast) -> bool:
    """Blackout: alle Helligkeiten auf 0 und wieder zurueck auf den Stand davor (enabled=None schaltet um). Die Werte bleiben unveraendert: waehrend
    des Blackouts lassen sich Helligkeiten weiter einstellen, sichtbar werden sie erst wieder nach 'Blackout Off'."""
    target = (not state.blackout) if enabled is None else bool(enabled)
    if target and not state.blackout:
        _remember_unscaled_output()                         # was nur im DMX-Puffer steht, bleibt fuer das Wiederherstellen erhalten
    state.blackout = target
    await _rescale_dimmers(broadcast)
    await broadcast("blackout_changed", {"enabled": state.blackout})
    return state.blackout


async def _cmd_blackout(rest: List[str], broadcast: Broadcast) -> Dict[str, Any]:
    """Blackout [On|Off|Toggle]: ohne Zusatz umschalten."""
    word = str(rest[0]).lower() if rest else "toggle"
    if len(rest) > 1 or word not in ("on", "off", "toggle", "1", "0", "true", "false"):
        raise _CommandError("Blackout: expected 'Blackout', 'Blackout On' or 'Blackout Off'")
    enabled = None if word == "toggle" else word in ("on", "1", "true")
    now = await set_blackout(enabled, broadcast)
    return {"success": True, "message": "OK: Blackout " + ("on" if now else "off")}


async def set_grand_master(value: float, broadcast: Broadcast) -> None:
    """Skaliert nur die Dimmer-Kanaele neu - aus dem unskalierten Dimmer-Wert
    in Fixture.values. Farben, Pan/Tilt und Beam bleiben unberuehrt."""
    state.grand_master = max(0.0, min(100.0, float(value)))
    await _rescale_dimmers(broadcast)
    await broadcast("grand_master_changed", {"value": state.grand_master})


async def set_cuelist_master(cuelist_id: str, value: float, broadcast: Broadcast) -> bool:
    """Executor-Fader einer Cue-Liste: MISCHT je Fixture und Attribut zwischen dem manuellen Wert (0 %) und dem Cue-Wert
    (100 %), fuer alle Kanaltypen. Mit dem Grand Master hat er nichts zu tun; die gespeicherten Cue-Werte bleiben
    unveraendert."""
    from app.cue_engine import cue_engine
    level = state.set_cuelist_master(cuelist_id, value)
    if level is None:
        return False
    await cue_engine.remix(cuelist_id)
    await broadcast("cuelist_master_changed", {"cuelist_id": cuelist_id, "value": level})
    return True


async def _cmd_master(rest: List[str], broadcast: Broadcast) -> Dict[str, Any]:
    tokens = list(rest)
    if tokens and tokens[0].lower() == "at":
        tokens = tokens[1:]
    if not tokens:
        raise _CommandError("Master: missing value (e.g. 'Master At 80', 'Master 80', 'Master Full')")
    tok = tokens[0].lower()
    if tok == "full":
        value = 100.0
    elif tok[0] in "+-":
        value = state.grand_master + _parse_float(tok)
    else:
        value = _parse_float(tok)
    await set_grand_master(value, broadcast)
    return {"success": True, "message": f"OK: Master {state.grand_master:g}%"}


async def _cmd_clear(rest: List[str], broadcast: Broadcast) -> Dict[str, Any]:
    global _last_clear_at
    now = time.monotonic()
    explicit_double = bool(rest and rest[0].lower() == "clear")
    rapid_double = _last_clear_at is not None and (now - _last_clear_at) <= _CLEAR_CLEAR_WINDOW
    _last_clear_at = None if (explicit_double or rapid_double) else now

    if explicit_double or rapid_double:
        return await apply_full_baseline_reset(broadcast)

    state.set_selection([])
    await broadcast("selection_changed", {"selected_ids": []})
    return {"success": True, "message": "OK: Selection cleared"}


# ---------------------------------------------------------------------------
# Cue-Listen: Auswahl per Name, Zielliste, Go/Back/Pause/Stop/Fader
# ---------------------------------------------------------------------------

def _list_suffix() -> str:
    """Bei 'Cuelist <name> ...' haengt die Rueckmeldung den Listennamen an (sonst ist es die aktive Liste)."""
    target = _target_list.get()
    cl = state.cuelists.get(target) if target else None
    return f' [{cl.name}]' if cl else ""


def _match_cuelist(tokens: List[str]) -> Optional[Tuple[CueList, int]]:
    """Cue-Liste anhand des NAMENS am Anfang der Tokens (Gross-/Kleinschreibung egal, auch mit mehreren Woertern: der laengste Treffer gewinnt)."""
    for k in range(len(tokens), 0, -1):
        candidate = " ".join(str(t) for t in tokens[:k]).strip().lower()
        for cl in state.cuelists.values():
            if cl.name.strip().lower() == candidate:
                return cl, k
    return None


def _find_cuelist(tokens: List[str]) -> Tuple[CueList, int]:
    """Cue-Liste am Anfang der Tokens: per Name ('Show', '"Cue List 1"') oder per Nummer (1 = erste Liste in der Reihenfolge des Dropdowns,
    wie 'Exec 1'). Gibt (Liste, verbrauchte Tokens) zurueck."""
    if not tokens:
        raise _Incomplete("Cuelist: expected 'Cuelist <name|number> [Go|Back|Pause|Stop|Fader <value>|Cue ...]'")
    found = _match_cuelist(tokens)
    if found is not None:
        return found
    if re.fullmatch(r"\d+", str(tokens[0])):
        lists = list(state.cuelists.values())
        n = int(str(tokens[0]))
        if 1 <= n <= len(lists):
            return lists[n - 1], 1
        raise _CommandError(f"Exec {n} not found")
    names = ", ".join(f'"{cl.name}"' for cl in state.cuelists.values()) or "none"
    raise _CommandError(f"Cue list not found: {tokens[0]} (available: {names})")


async def _cmd_cuelist(rest: List[str], broadcast: Broadcast) -> Dict[str, Any]:
    """Cuelist <name|number> [Befehl]: ohne Befehl wird die Liste aktiv; mit Befehl gilt dieser fuer genau diese Liste
    (Go, Back, Pause, Resume, Stop, Fader <wert>, Goto Cue n, Store Cue n, Cue n Fade ..., Off ...), ohne die aktive Liste zu wechseln."""
    if rest and not getattr(rest[0], "quoted", False) and str(rest[0]).lower() in ("new", "create", "add"):
        return await _cmd_cuelist_object(str(rest[0]).lower(), rest[1:], broadcast)
    cl, used = _find_cuelist(rest)
    sub = rest[used:]
    if sub and not getattr(sub[0], "quoted", False) and (str(sub[0]).lower() in ("rename", "duplicate") or (str(sub[0]).lower() == "delete" and len(sub) == 1)):
        token = _target_list.set(cl.id)
        try:
            return await _cmd_cuelist_object(str(sub[0]).lower(), sub[1:], broadcast)
        finally:
            _target_list.reset(token)
    if not sub:
        state.set_active_cuelist(cl.id)
        await broadcast("cuelists_changed", _cuelists_payload())
        return {"success": True, "message": f'OK: Cue list "{cl.name}" is now active'}
    token = _target_list.set(cl.id)
    try:
        return await _dispatch(sub, broadcast)
    finally:
        _target_list.reset(token)


async def _cmd_playback(keyword: str, broadcast: Broadcast) -> Dict[str, Any]:
    """Pause / Resume / Stop der laufenden Ueberblendung der Liste (wie die Tasten des Executors)."""
    from app.cue_engine import cue_engine  # deferred: vermeidet Zirkelimport beim Modul-Laden
    cl = _active_cuelist()
    if keyword == "pause":
        if not cue_engine.pause(cl.id):
            raise _CommandError("Pause: nothing is fading in this cue list")
        return {"success": True, "message": "OK: Paused" + _list_suffix()}
    if keyword in ("resume", "continue"):
        if not cue_engine.resume(cl.id):
            raise _CommandError("Resume: this cue list is not paused")
        return {"success": True, "message": "OK: Resumed" + _list_suffix()}
    stopped = cue_engine.stop(cl.id)
    if fx_engine.clear_all():                       # Stopp beendet auch alle laufenden Effekte (wie die Stopp-Taste)
        await broadcast("fx_changed", fx_engine.state_payload())
    return {"success": True, "message": ("OK: Stopped" if stopped else "OK: Nothing was running") + _list_suffix()}


async def _cmd_fader(rest: List[str], broadcast: Broadcast) -> Dict[str, Any]:
    """Fader <0-100 | Full | +n | -n>: der Executor-Fader der Liste (Mix zwischen manuellem Wert und Cue)."""
    cl = _active_cuelist()
    tokens = list(rest)
    if tokens and str(tokens[0]).lower() == "at":
        tokens = tokens[1:]
    if not tokens:
        raise _Incomplete("Fader: missing value (e.g. 'Fader 50', 'Fader Full', 'Fader +10')")
    mode, value, _percent = _parse_level(tokens[0])
    value = _pct(state.cuelist_masters.get(cl.id, 100.0) + value if mode == "rel" else value)
    await set_cuelist_master(cl.id, value, broadcast)
    return {"success": True, "message": f"OK: Fader {value:g}%" + _list_suffix()}


# ---------------------------------------------------------------------------
# Cue-Verwaltung: Store / Delete / Move / Label / Set / Cue-Eigenschaften / Go / Off
# ---------------------------------------------------------------------------

def _parse_cue_span(tokens: List[str], start: int = 0) -> Tuple[float, float, int]:
    """'3' oder '3 Thru 5' ab tokens[start] -> (von, bis, naechster Index)."""
    if start >= len(tokens):
        raise _Incomplete("Cue: missing number")
    low = _parse_float(tokens[start])
    high, i = low, start + 1
    if i < len(tokens) and str(tokens[i]).lower() == "thru":
        if i + 1 >= len(tokens):
            raise _Incomplete("Thru: missing number")
        high, i = _parse_float(tokens[i + 1]), i + 2
    return (low, high, i) if low <= high else (high, low, i)


def _cues_in_span(cl: CueList, low: float, high: float) -> List[Cue]:
    cues = [c for c in cl.cues if low - 1e-6 <= c.number <= high + 1e-6]
    if not cues:
        raise _CommandError(f"Cue {_fmt_num(low)} not found" if low == high else f"No cues between {_fmt_num(low)} and {_fmt_num(high)}")
    return cues


def _span_label(low: float, high: float, count: int) -> str:
    return f"Cue {_fmt_num(low)}" if low == high else f"{count} cues ({_fmt_num(low)}-{_fmt_num(high)})"


async def _cmd_store(rest: List[str], broadcast: Broadcast) -> Dict[str, Any]:
    """Store Cue <number> ["<Name>"] [Merge|Overwrite]  |  Store Group "<Name>" [Merge|Overwrite]"""
    if rest and str(rest[0]).lower() == "group":
        return await _cmd_store_group(rest[1:], broadcast)
    if not rest or rest[0].lower() != "cue" or len(rest) < 2:
        raise _CommandError("Store: expected 'Store Cue <number> [\"<name>\"] [Merge|Overwrite]'")
    number = _parse_float(rest[1])
    option: Optional[str] = None
    name: Optional[str] = None
    for tok in rest[2:]:
        low = str(tok).lower()
        if getattr(tok, "quoted", False) and name is None:
            name = str(tok)
        elif low in ("merge", "overwrite") and option is None:
            option = low
        else:
            raise _CommandError("Store Cue: expected 'Store Cue <number> [\"<name>\"] [Merge|Overwrite]'")
    cl = _active_cuelist()
    fixture_values = state.get_programmer_snapshot()
    fx_map = fx_engine.cue_effects()
    if not fixture_values and not fx_map:
        raise _CommandError("Store Cue: programmer is empty - set values or an effect first")
    status, _cue = state.store_cue(cl.id, fixture_values, number=number, mode=option, fx=fx_map,
                                   fx_order=fx_engine.cue_effect_order(), name=name)
    if status == "conflict":
        raise _CommandError(f"Cue {_fmt_num(number)} already exists - use 'Store Cue {_fmt_num(number)} Merge' "
                            f"or 'Store Cue {_fmt_num(number)} Overwrite'")
    if status not in ("created", "merged", "overwritten"):
        raise _CommandError("Store Cue: failed")
    affected = state.clear_programmer(list(fixture_values.keys()))
    await broadcast("cuelists_changed", _cuelists_payload())
    if affected:
        await broadcast("programmer_cleared", {"fixture_ids": affected})
        await broadcast("programmer_refs", {"refs": state.programmer_refs_payload()})
    verb = {"created": "stored", "merged": "merged", "overwritten": "overwritten"}[status]
    return {"success": True, "message": f"OK: Cue {_fmt_num(number)} {verb}" + _list_suffix()}


async def _cmd_delete(rest: List[str], broadcast: Broadcast) -> Dict[str, Any]:
    """Delete Cue <number> [Thru <number>]  |  Delete Group <name|number>  |  Delete Cuelist <name|number>"""
    head = str(rest[0]).lower() if rest else ""
    if head == "group":
        return await _cmd_delete_group(rest[1:], broadcast)
    if head in _CUELIST_KEYWORDS:
        cl, _used = _find_cuelist(rest[1:])
        token = _target_list.set(cl.id)
        try:
            return await _cmd_cuelist_object("delete", [], broadcast)
        finally:
            _target_list.reset(token)
    if not rest or rest[0].lower() != "cue" or len(rest) < 2:
        raise _CommandError("Delete: expected 'Delete Cue <number> [Thru <number>]'")
    low, high, _end = _parse_cue_span(rest, 1)
    cl = _active_cuelist()
    cues = _cues_in_span(cl, low, high)
    for cue in cues:
        if not state.delete_cue(cl.id, cue.id):
            raise _CommandError("Delete Cue: failed")
    await broadcast("cuelists_changed", _cuelists_payload())
    label = f"Cue {_fmt_num(low)}" if low == high else f"{len(cues)} cues ({_fmt_num(low)}-{_fmt_num(high)})"
    return {"success": True, "message": f"OK: {label} deleted" + _list_suffix()}


# Eigenschaften eines Cues fuer 'Cue <n> <Eigenschaft> <wert>' (normalisiert, ohne Leerzeichen): update_cue-Feld, Wertart, Anzeigename.
_CUE_PROPS: Dict[str, Tuple[str, str, str]] = {
    "fade": ("fade", "time", "fade"), "delay": ("delay", "time", "delay"),
    "colorfade": ("fade_color", "opt", "color fade"), "colordelay": ("delay_color", "opt", "color delay"),
    "colourfade": ("fade_color", "opt", "color fade"), "colourdelay": ("delay_color", "opt", "color delay"),
    "posfade": ("fade_pos", "opt", "position fade"), "positionfade": ("fade_pos", "opt", "position fade"),
    "posdelay": ("delay_pos", "opt", "position delay"), "positiondelay": ("delay_pos", "opt", "position delay"),
    "beamfade": ("fade_beam", "opt", "beam fade"), "beamdelay": ("delay_beam", "opt", "beam delay"),
    "zoomfade": ("fade_zoom", "opt", "zoom fade"), "zoomdelay": ("delay_zoom", "opt", "zoom delay"),
    "fxin": ("fx_fade_in", "time", "effect fade-in"), "fxfadein": ("fx_fade_in", "time", "effect fade-in"), "effectin": ("fx_fade_in", "time", "effect fade-in"),
    "fxout": ("fx_fade_out", "time", "effect fade-out"), "fxfadeout": ("fx_fade_out", "time", "effect fade-out"), "effectout": ("fx_fade_out", "time", "effect fade-out"),
    "trigger": ("trigger", "trigger", "trigger"), "mib": ("mib", "mib", "MIB"), "cmd": ("cmd", "text", "CMD"), "name": ("name", "text", "name"),
}
_CUE_PROP_FIRST_WORDS = {"color", "colour", "pos", "position", "beam", "zoom", "fx", "effect"}


def _match_cue_prop(tokens: List[str], i: int) -> Tuple[Tuple[str, str, str], int]:
    """Eigenschaft ab tokens[i]: ein Wort ('Fade') oder zwei ('Color Fade', 'FX In')."""
    if i >= len(tokens):
        raise _Incomplete("Cue: missing property (Fade, Delay, Color Fade, Name, Trigger ...)")
    if i + 1 < len(tokens):
        two = _norm(str(tokens[i]) + str(tokens[i + 1]))
        if two in _CUE_PROPS:
            return _CUE_PROPS[two], i + 2
    one = _norm(tokens[i])
    if one in _CUE_PROPS:
        return _CUE_PROPS[one], i + 1
    if one in _CUE_PROP_FIRST_WORDS:
        raise _Incomplete(f"Cue: expected '{str(tokens[i]).capitalize()} Fade|Delay'" if one != "fx" and one != "effect" else "Cue: expected 'FX In|Out'")
    raise _CommandError(f"Cue: unknown property '{tokens[i]}' (Fade, Delay, Color/Pos/Beam/Zoom Fade|Delay, FX In|Out, Trigger, MIB, Cmd, Name)")


def _cue_prop_value(kind: str, tokens: List[str], label: str) -> Tuple[Dict[str, Any], str]:
    """Wert einer Cue-Eigenschaft -> (Felder fuer update_cue, Anzeige)."""
    if not tokens:
        raise _Incomplete(f"Cue {label}: missing value")
    first = str(tokens[0])
    low = first.lower()
    if kind in ("time", "opt"):
        if kind == "opt" and low in ("-", "default", "none", "clear", "reset", "off"):
            return {"__field__": None}, "default"
        value = _parse_float(first)
        if value < 0:
            raise _CommandError(f"Cue {label}: time must not be negative")
        return {"__field__": value}, f"{_fmt_num(value)}s"
    if kind == "trigger":
        if low in ("go", "follow"):
            return {"trigger": low}, low.capitalize()
        if low in ("timecode", "tc", "time"):
            from app.timecode import format_timecode, parse_timecode_ms  # deferred
            if len(tokens) < 2:
                raise _Incomplete("Cue Trigger Timecode: missing time (e.g. 'Cue 3 Trigger Timecode 00:01:30.000' or '90')")
            parsed = parse_timecode_ms(str(tokens[1]))
            if parsed is None:
                raise _CommandError(f"Invalid time: {tokens[1]}")
            return {"trigger": "timecode", "timecode_ms": parsed}, f"Timecode {format_timecode(parsed)}"
        raise _CommandError("Cue Trigger: expected Go, Follow or Timecode <time>")
    if kind == "mib":
        mapping = {"off": "Off", "0": "Off", "auto": "Auto", "on": "On"}
        if low not in mapping:
            raise _CommandError("Cue MIB: expected Off, Auto or On")
        return {"mib": mapping[low]}, mapping[low]
    text = " ".join(str(t) for t in tokens)
    if label == "name" and not text.strip():
        raise _CommandError("Cue name must not be empty")
    return {"__field__": text}, f'"{text}"'


async def _cmd_cue_timing(rest: List[str], broadcast: Broadcast) -> Dict[str, Any]:
    """Cue <number> [Thru <number>] <Eigenschaft> <Wert>: Fade, Delay, Color/Pos/Beam/Zoom Fade|Delay ('-' = allgemeine Zeit), FX In|Out,
    Trigger Go|Follow|Timecode <zeit>, MIB Off|Auto|On, Cmd "<befehle>", Name "<text>"."""
    if not rest:
        raise _Incomplete("Cue: expected 'Cue <number> Fade|Delay|... <value>'")
    low, high, i = _parse_cue_span(rest)
    (field_name, kind, label), j = _match_cue_prop(rest, i)
    fields, display = _cue_prop_value(kind, rest[j:], label)
    if "__field__" in fields:
        fields = {field_name: fields["__field__"]}
    cl = _active_cuelist()
    cues = _cues_in_span(cl, low, high)
    for cue in cues:
        if state.update_cue(cl.id, cue.id, **fields) is None:
            raise _CommandError("Cue: update failed")
    await broadcast("cuelists_changed", _cuelists_payload())
    return {"success": True, "message": f"OK: {_span_label(low, high, len(cues))} {label} set to {display}" + _list_suffix()}


async def _cmd_go(rest: List[str], broadcast: Broadcast, keyword: str = "go") -> Dict[str, Any]:
    """Go (naechster Cue) | Go Cue <n> / Go <n> / Goto Cue <n> (zu diesem Cue springen) | Back / Go Back (voriger Cue)."""
    from app.cue_engine import cue_engine  # deferred: vermeidet Zirkelimport beim Modul-Laden
    cl = _active_cuelist()
    words = [str(w).lower() for w in rest]
    if keyword == "back" or (words and words[0] == "back"):
        cue = await cue_engine.trigger(cl.id, -1)
        if cue is None:
            raise _CommandError("Back: this cue list has no cues")
        await broadcast("cuelists_changed", _cuelists_payload())
        return {"success": True, "message": f"OK: Back to Cue {_fmt_num(cue.number)}" + _list_suffix()}
    if not rest and keyword == "go":
        cue = await cue_engine.trigger(cl.id, 1)
        if cue is None:
            raise _CommandError("Go: this cue list has no cues")
        await broadcast("cuelists_changed", _cuelists_payload())
        return {"success": True, "message": f"OK: Go Cue {_fmt_num(cue.number)}" + _list_suffix()}
    args = rest[1:] if words and words[0] == "cue" else rest
    verb = keyword.capitalize()
    if not args:
        raise _Incomplete(f"{verb}: expected '{verb} Cue <number>'")
    number = _parse_float(args[0])
    cue = _find_cue_by_number(cl, number)
    if cue is None:
        raise _CommandError(f"Cue {_fmt_num(number)} not found")
    new_cue = await cue_engine.jump_to(cl.id, cue.id)
    if new_cue is None:
        raise _CommandError(f"{verb} Cue: failed")
    await broadcast("cuelists_changed", _cuelists_payload())
    return {"success": True, "message": f"OK: Go Cue {_fmt_num(number)}" + _list_suffix()}


async def _cmd_update(rest: List[str], broadcast: Broadcast) -> Dict[str, Any]:
    """Update [CueOnly]: uebernimmt die Programmer-Werte in den aktiven Cue. Ohne Zusatz laufen Aenderungen in
    Folge-Cues weiter (Tracking), mit CueOnly bleibt die Aenderung auf diesen Cue beschraenkt."""
    option = rest[0].lower() if rest else ""
    if option not in ("", "cueonly"):
        raise _CommandError("Update: expected 'Update' or 'Update CueOnly'")
    cl = _active_cuelist()
    status, cue = state.update_active_cue(cl.id, state.get_programmer_snapshot(), fx=fx_engine.cue_effects(),
                                          fx_order=fx_engine.cue_effect_order(), mode="only" if option else "normal")
    if status == "no_active_cue":
        raise _CommandError("Update: no active cue in this cue list - run Go first")
    if status == "empty":
        raise _CommandError("Update: programmer is empty - set values or an effect first")
    if status != "updated":
        raise _CommandError("Update: failed")
    affected = state.clear_programmer(None)
    await broadcast("cuelists_changed", _cuelists_payload())
    if affected:
        await broadcast("programmer_cleared", {"fixture_ids": affected})
        await broadcast("programmer_refs", {"refs": state.programmer_refs_payload()})
    return {"success": True, "message": f"OK: Cue {_fmt_num(cue.number)} updated" + (" (CueOnly)" if option else "")}


async def _cmd_move(rest: List[str], broadcast: Broadcast) -> Dict[str, Any]:
    if len(rest) < 4 or rest[0].lower() != "cue" or rest[2].lower() != "at":
        raise _CommandError("Move: expected 'Move Cue <number> At <newNumber>'")
    number = _parse_float(rest[1])
    new_number = _parse_float(rest[3])
    cl = _active_cuelist()
    cue = _find_cue_by_number(cl, number)
    if cue is None:
        raise _CommandError(f"Cue {_fmt_num(number)} not found")
    status, _data = state.renumber_cue(cl.id, cue.id, new_number)
    if status == "conflict":
        raise _CommandError(f"Cue {_fmt_num(new_number)} already exists")
    if status != "ok":
        raise _CommandError("Move Cue: failed")
    await broadcast("cuelists_changed", _cuelists_payload())
    return {"success": True, "message": f"OK: Cue {_fmt_num(number)} moved to {_fmt_num(new_number)}"}


async def _cmd_label_or_set(keyword: str, rest: List[str], broadcast: Broadcast) -> Dict[str, Any]:
    """Label Cue <number> "<name>"  ODER  Set Cue <number> Name "<name>"  (auch fuer Group: Label Group <Name|Nr> "<neu>")."""
    verb = keyword.capitalize()
    if rest and str(rest[0]).lower() == "group":
        return await _cmd_rename_group(rest[1:], broadcast)
    if not rest or rest[0].lower() != "cue" or len(rest) < 2:
        raise _CommandError(f"{verb}: expected '{verb} Cue <number> ...'")
    number = _parse_float(rest[1])
    name_tokens = rest[2:]
    if keyword == "set":
        if not name_tokens or name_tokens[0].lower() != "name":
            raise _CommandError("Set Cue: expected 'Set Cue <number> Name \"<text>\"'")
        name_tokens = name_tokens[1:]
    if not name_tokens:
        raise _CommandError(f"{verb} Cue: missing name")
    name = " ".join(name_tokens)
    cl = _active_cuelist()
    cue = _find_cue_by_number(cl, number)
    if cue is None:
        raise _CommandError(f"Cue {_fmt_num(number)} not found")
    if state.update_cue(cl.id, cue.id, name=name) is None:
        raise _CommandError(f"{verb} Cue: failed")
    await broadcast("cuelists_changed", _cuelists_payload())
    return {"success": True, "message": f'OK: Cue {_fmt_num(number)} renamed to "{name}"'}


async def _cmd_timecode(rest: List[str], broadcast: Broadcast) -> Dict[str, Any]:
    """Globaler Timecode ueber die Befehlszeile (siehe app/timecode.py):
        Timecode                      Stand anzeigen
        Timecode At <zeit>            springen (z. B. 'Timecode At 4.3', 'Timecode At 00:00:04.300'); '+5' / '-2' = relativ in Sekunden
        Timecode Play | Reverse       vorwaerts / rueckwaerts laufen lassen ('At <zeit> Play' springt und startet gleich)
        Timecode Pause | Stop         anhalten / anhalten und auf 0 zuruecksetzen ('Reset' wie Stop)
        Timecode Rate <faktor>        Geschwindigkeit (0.1 ... 8, z. B. 2 oder 0.5x)"""
    from app.timecode import MAX_MS, format_timecode, parse_timecode_ms, timecode  # deferred
    words = [w.lower() for w in rest]

    async def done(snapshot: Dict[str, Any], text: str) -> Dict[str, Any]:
        await broadcast("timecode_state", snapshot)
        return {"success": True, "message": f"OK: {text}"}

    def describe(snapshot: Dict[str, Any]) -> str:
        state_text = ("playing backwards" if snapshot["direction"] < 0 else "playing") if snapshot["running"] else "stopped"
        return f"Timecode {format_timecode(snapshot['position_ms'])} ({state_text}, {snapshot['rate']:g}x)"

    if not words:
        return {"success": True, "message": f"OK: {describe(timecode.state())}"}
    head = words[0]
    if head in ("play", "go", "start", "run"):
        return await done(timecode.play(1), "Timecode playing")
    if head in ("reverse", "back", "rewind", "backwards"):
        return await done(timecode.play(-1), "Timecode playing backwards")
    if head == "pause":
        return await done(timecode.pause(), f"Timecode paused at {format_timecode(timecode.position_ms())}")
    if head in ("stop", "reset"):
        return await done(timecode.stop(), "Timecode stopped at 00:00:00.000")
    if head in ("rate", "speed"):
        if len(rest) < 2:
            raise _CommandError("Timecode Rate: expected 'Timecode Rate <factor>' (0.1 - 8)")
        try:
            factor = float(rest[1].lower().rstrip("x").replace(",", "."))
        except ValueError:
            raise _CommandError(f"Invalid number: {rest[1]}")
        snapshot = timecode.set_rate(factor)
        return await done(snapshot, f"Timecode speed {snapshot['rate']:g}x")
    # 'At <zeit>', '<zeit>', '+5' / '-2'
    args = rest[1:] if head == "at" else rest
    if not args:
        raise _CommandError("Timecode At: expected a time, e.g. 'Timecode At 4.3' or 'Timecode At 00:00:04.300'")
    token = args[0]
    if token[0] in "+-" and len(token) > 1:
        try:
            delta = float(token.replace(",", "."))
        except ValueError:
            raise _CommandError(f"Invalid time: {token}")
        target = min(MAX_MS, max(0, timecode.position_ms() + delta * 1000))
    else:
        parsed = parse_timecode_ms(token)
        if parsed is None:
            raise _CommandError(f"Invalid time: {token} (e.g. 4.3 or 00:00:04.300, max. 100 hours)")
        target = parsed
    tail = [w.lower() for w in args[1:]]
    if tail and tail[0] not in ("play", "go", "start", "reverse", "back"):
        raise _CommandError(f"Timecode At: unexpected '{args[1]}' (expected Play or Reverse)")
    snapshot = timecode.seek(target)
    if tail and tail[0] in ("play", "go", "start"):
        snapshot = timecode.play(1)
    elif tail and tail[0] in ("reverse", "back"):
        snapshot = timecode.play(-1)
    return await done(snapshot, f"Timecode at {format_timecode(target)}" + (" (playing)" if snapshot["running"] else ""))


async def _cmd_off(rest: List[str], broadcast: Broadcast) -> Dict[str, Any]:
    """Off Exec <N> | Off Cuelist <name> | Off (aktive Liste): "Exec N" ist die N-te Cue-Liste in der Reihenfolge des Dropdowns.
    "Off" loescht aktuell nur den aktiven-Cue-Status der Liste (kein Blackout-Fade der zuletzt ausgegebenen DMX-Werte) -
    siehe documentation/commands.md fuer diese bewusste Einschraenkung."""
    head = str(rest[0]).lower() if rest else ""
    if head in _CUELIST_KEYWORDS:
        cl, _used = _find_cuelist(rest[1:])
        label = f"Exec {list(state.cuelists.values()).index(cl) + 1}" if head in ("exec", "executor") else f'Cue list "{cl.name}"'
    elif not rest:
        cl = _active_cuelist()
        label = f'Cue list "{cl.name}"'
    else:
        raise _CommandError("Off: expected 'Off Exec <number>', 'Off Cuelist <name>' or just 'Off'")
    if state.active_cue_ids.pop(cl.id, None) is None:
        return {"success": True, "message": f"OK: {label} already off"}
    await broadcast("cuelists_changed", _cuelists_payload())
    return {"success": True, "message": f"OK: {label} off"}


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

# Kategorie-Woerter fuer Cue-Listen: erst die Kategorie, dann der Name ('Cuelist Show Go'). 'QList' / 'Q-List' sind dieselbe Kategorie.
_CUELIST_KEYWORDS = ("cuelist", "qlist", "q-list", "list", "cl", "exec", "executor")


async def _dispatch(tokens: List[str], broadcast: Broadcast) -> Dict[str, Any]:
    """Fuehrt einen bereits zerlegten Befehl aus (wirft _CommandError bei Fehlern - _execute_single faengt sie ab)."""
    keyword = str(tokens[0]).lower()
    rest = tokens[1:]

    if keyword == "fixture":
        return await _cmd_fixture(rest, broadcast)
    if keyword == "group":
        return await _cmd_group(rest, broadcast)
    if _is_clause_keyword(tokens[0]):                      # At, Full, Color, RGB, Pan, Tilt, Zoom, Gobo ..., CH3, Channel ...
        return await _cmd_attr(tokens, broadcast)
    if keyword == "clear":
        return await _cmd_clear(rest, broadcast)
    if keyword in ("master", "grandmaster"):
        return await _cmd_master(rest, broadcast)
    if keyword == "blackout":
        return await _cmd_blackout(rest, broadcast)
    if keyword == "store":
        return await _cmd_store(rest, broadcast)
    if keyword == "update":
        return await _cmd_update(rest, broadcast)
    if keyword == "delete":
        return await _cmd_delete(rest, broadcast)
    if keyword == "move":
        return await _cmd_move(rest, broadcast)
    if keyword in ("label", "set"):
        return await _cmd_label_or_set(keyword, rest, broadcast)
    if keyword == "cue":
        return await _cmd_cue_timing(rest, broadcast)
    if keyword in ("go", "goto", "back"):
        return await _cmd_go(rest, broadcast, keyword)
    if keyword in ("pause", "resume", "continue", "stop"):
        return await _cmd_playback(keyword, broadcast)
    if keyword in ("fader", "mix"):
        return await _cmd_fader(rest, broadcast)
    if keyword in _CUELIST_KEYWORDS:
        return await _cmd_cuelist(rest, broadcast)
    if keyword == "off":
        return await _cmd_off(rest, broadcast)
    if keyword in ("timecode", "tc"):
        return await _cmd_timecode(rest, broadcast)
    if state.selected_fixture_ids and any(
            _find_channel(fixture_channel_offsets(fx), tokens[0]) for fx in (state.fixtures.get(i) for i in state.selected_fixture_ids) if fx):
        return await _cmd_attr(tokens, broadcast)           # Frost 50 (Kanalname der selektierten Geraete)
    if _match_cuelist(tokens) is not None:                  # ein Listenname allein ist kein Befehl: erst die Kategorie nennen
        return {"success": False, "message": f"Unknown command: {tokens[0]} (a cue list needs its category first: 'Cuelist {tokens[0]} Go')"}
    return {"success": False, "message": f"Unknown command: {tokens[0]}"}


async def _execute_single(raw: str, broadcast: Broadcast) -> Dict[str, Any]:
    tokens = _tokenize(raw)
    if not tokens:
        return {"success": False, "message": "Empty command"}
    try:
        return await _dispatch(tokens, broadcast)
    except _CommandError as exc:
        return {"success": False, "message": str(exc)}
    except Exception as exc:  # pragma: no cover - Sicherheitsnetz, Server darf nie abstuerzen
        return {"success": False, "message": f"Internal error: {exc}"}


async def execute_command(raw: str, broadcast: Broadcast) -> Dict[str, Any]:
    """Parst und fuehrt einen Befehlszeilen-Eintrag aus - ggf. MEHRERE,
    durch Komma oder Semikolon getrennte Befehle sequenziell nacheinander (siehe
    _split_commands()). Gibt IMMER {"success": bool, "message": str}
    zurueck - wirft keine Exceptions nach aussen."""
    raw = (raw or "").strip()
    if not raw:
        return {"success": False, "message": "Empty command"}

    parts = _split_commands(raw)
    if not parts:
        return {"success": False, "message": "Empty command"}
    if len(parts) == 1:
        return await _execute_single(parts[0], broadcast)

    messages: List[str] = []
    overall_success = True
    for part in parts:
        result = await _execute_single(part, broadcast)
        messages.append(result.get("message", ""))
        overall_success = overall_success and result.get("success", False)
    return {"success": overall_success, "message": " | ".join(messages)}


# ---------------------------------------------------------------------------
# Autocomplete / Vorschlags-Engine (Tab-Taste, siehe app.js)
# ---------------------------------------------------------------------------
# EIN Ort fuer die komplette Grammatik - das Frontend kennt KEINE eigenen
# Keyword-Listen, es rendert nur, was get_suggestions() zurueckgibt. Die
# Vorschlaege folgen dem echten Parser (_consume_clause() & Co.), und sie
# kennen den Zustand: Fixture-Namen/-Kanaele, Gruppen, Cue-Listen und Cues.
#
# Jeder Vorschlag: {"label": Anzeige, "insert": einzufuegender Text (inkl. Leerzeichen/Anfuehrungszeichen), "hint": Erlaeuterung,
#                   "start": Index im GESAMTEN Eingabetext, ab dem `insert` das gerade getippte Wort ersetzt, "info": True = nur Hinweis
#                   auf den erwarteten Wert (nicht einfuegbar)}.

Suggestion = Dict[str, Any]

# (Keyword, Syntax-Hinweis-Anzeigetext oder None) - die Top-Level-Schluesselwoerter, die _dispatch() tatsaechlich kennt.
_TOP_LEVEL_KEYWORDS: List[Tuple[str, Optional[str]]] = [
    ("Fixture", "<id | name> [Thru <id>] [+ <id>] [At ...]"),
    ("Group", "<id | name> [Thru <id>]"),
    ("At", "<0-100> | Full | +<n> | -<n>"),
    ("Full", None),
    ("Color", "<name> | #RRGGBB | <r> <g> <b>"),
    ("RGB", "<r> <g> <b>"),
    ("Pan", "<degrees | n%>"),
    ("Tilt", "<degrees | n%>"),
    ("Zoom", "<0-100>"),
    ("Focus", "<0-100>"),
    ("Gobo", "<0-100>"),
    ("Prism", "<0-100>"),
    ("Strobe", "<0-100>"),
    ("Channel", "<number | name> <value>"),
    ("Clear", None),
    ("Master", "[At] <0-100> | Full | +<n> | -<n>"),
    ("Blackout", "[On | Off]  (without: toggle)"),
    ("Variable", '"<name>"  (applies a variable to the selection)'),
    ("Effect", '"<name>" | Off [color|position|...]'),
    ("Manual", "[dimmer|color|position|zoom|focus|gobo]  (back to manual: releases variable + effect)"),
    ("Go", "[Cue <number>]"),
    ("Back", None),
    ("Goto", "Cue <number>"),
    ("Pause", None),
    ("Resume", None),
    ("Stop", None),
    ("Fader", "<0-100> | Full | +<n> | -<n>"),
    ("Cuelist", "New [\"<name>\"] | <name | number> [Go | Back | Fader ... | Rename | Duplicate | Delete]   (also QList)"),
    ("Store", 'Cue <number> ["<name>"] [Merge|Overwrite]  |  Group "<name>"'),
    ("Update", "[CueOnly]"),
    ("Delete", "Cue <number> [Thru <number>] | Group <name> | Cuelist <name>"),
    ("Move", "Cue <number> At <number>"),
    ("Label", 'Cue <number> "<text>"  |  Group <name> "<new name>"'),
    ("Set", 'Cue <number> Name "<text>"'),
    ("Cue", "<number> Fade|Delay|... <value>"),
    ("Off", "[Exec <number> | Cuelist <name>]"),
    ("Timecode", "At <time> | Play | Reverse | Pause | Stop | Rate <factor>"),
]
_LIST_SUBCOMMANDS: List[Tuple[str, Optional[str]]] = [
    ("Go", "[Cue <number>]"), ("Back", None), ("Goto", "Cue <number>"), ("Pause", None), ("Resume", None), ("Stop", None),
    ("Fader", "<0-100> | Full | +<n> | -<n>"), ("Off", None), ("Store", "Cue <number>"), ("Update", "[CueOnly]"),
    ("Delete", "Cue <number>   (alone: deletes the list)"), ("Move", "Cue <number> At <number>"), ("Label", 'Cue <number> "<text>"'),
    ("Set", 'Cue <number> Name "<text>"'), ("Cue", "<number> Fade|Delay|... <value>"),
    ("Rename", '"<new name>"'), ("Duplicate", '["<name>"]'),
]
_MAX_ITEMS = 80


def _kw(label: str, hint: Optional[str] = None) -> Suggestion:
    return {"insert": label + " ", "label": label, "hint": hint}


def _info(text: str) -> Suggestion:
    """Nur ein Hinweis auf den erwarteten Wert (wird nicht eingefuegt)."""
    return {"insert": "", "label": text, "hint": None, "info": True}


def _name_item(name: str, hint: Optional[str] = None) -> Suggestion:
    """Ein Name als Vorschlag: mit Anfuehrungszeichen, wenn er Leerzeichen/Trennzeichen enthaelt oder wie ein Schluesselwort/eine Zahl aussieht."""
    needs_quotes = bool(re.search(r'[\s,;"+]', name)) or _is_clause_keyword(name) or _is_number(name) or not name
    return {"insert": (f'"{name}" ' if needs_quotes else name + " "), "label": name, "hint": hint}


def _all_fids() -> List[str]:
    return [str(f) for f in sorted(fx.fid for fx in state.fixtures.values())]


def _all_group_numbers() -> List[str]:
    return [str(i) for i in range(1, len(state.groups) + 1)]


def _active_cuelist_numbers() -> List[str]:
    cl = _suggest_cuelist()
    return [_fmt_num(c.number) for c in cl.cues] if cl else []


def _suggest_cuelist() -> Optional[CueList]:
    target = _target_list.get()
    if target is not None:
        return state.cuelists.get(target)
    return state.cuelists.get(state.active_cuelist_id) if state.active_cuelist_id else None


def _looks_like_number(tok: Any) -> bool:
    return _is_number(tok)


def _cue_items() -> List[Suggestion]:
    cl = _suggest_cuelist()
    return [_kw(_fmt_num(c.number), c.name) for c in cl.cues] if cl else []


def _cuelist_items() -> List[Suggestion]:
    items = [_name_item(cl.name, "Cue list") for cl in state.cuelists.values()]
    items += [_kw(str(i + 1), cl.name) for i, cl in enumerate(state.cuelists.values())]
    return items


def _fixtures_for_names(spec_tokens: Optional[List[str]] = None, kind: str = "fixture") -> List[Any]:
    """Die Geraete, auf die sich die Kanalnamen-Vorschlaege beziehen: die angegebene ID-Angabe, sonst die Selektion, sonst alle Geraete."""
    fixtures: List[Any] = []
    if spec_tokens:
        try:
            numbers, names = _parse_selection(spec_tokens)
        except _CommandError:
            numbers, names = [], []
        if kind == "fixture":
            by_fid = {fx.fid: fx for fx in state.fixtures.values()}
            fixtures = [by_fid[n] for n in numbers if n in by_fid]
            fixtures += [fx for fx in state.fixtures.values() if fx.name.strip().lower() in {n.lower() for n in names}]
        else:
            group_names = list(state.groups.keys())
            ids: List[str] = []
            for n in numbers:
                if 1 <= n <= len(group_names):
                    ids.extend(state.groups[group_names[n - 1]])
            for name in names:
                ids.extend(next((v for g, v in state.groups.items() if g.strip().lower() == name.lower()), []))
            fixtures = [state.fixtures[i] for i in dict.fromkeys(ids) if i in state.fixtures]
    elif state.selected_fixture_ids:
        fixtures = [state.fixtures[i] for i in state.selected_fixture_ids if i in state.fixtures]
    return fixtures or list(state.fixtures.values())


_COVERED_CHANNELS = {"Dimmer", "Pan", "Tilt", "PanFine", "TiltFine"}


def _channel_items(fixtures: List[Any], *, numbers: bool) -> List[Suggestion]:
    """Kanalnummern (1 ... Anzahl der Kanaele) bzw. Kanalnamen der Geraete, die nicht schon ein eigenes Schluesselwort haben."""
    if numbers:
        first = fixtures[0] if fixtures else None
        names = {off: name for name, off in fixture_channel_offsets(first).items()} if first else {}
        count = max((fx.channel_count for fx in fixtures[:50]), default=0)
        return [_kw(str(n), names.get(n - 1)) for n in range(1, count + 1)]
    seen: Dict[str, int] = {}
    for fx in fixtures[:50]:
        offsets = fixture_channel_offsets(fx)
        covered = set(beam_channels(offsets).values()) | _COVERED_CHANNELS
        for name, off in sorted(offsets.items(), key=lambda kv: kv[1]):
            if name not in covered and not name.endswith("Fine"):
                seen.setdefault(name, off)
    return [_name_item(name, f"CH{off + 1}") for name, off in sorted(seen.items(), key=lambda kv: kv[1])]


def _clause_keyword_items(fixtures: List[Any]) -> List[Suggestion]:
    items = [_kw("At", "<0-100> | Full | +n"), _kw("Color", "<name | #hex | r g b>"), _kw("RGB", "<r> <g> <b>"),
             _kw("Pan", "<degrees | n%>"), _kw("Tilt", "<degrees | n%>"), _kw("Full")]
    items += [_kw("Zoom", "<0-100>"), _kw("Focus", "<0-100>"), _kw("Gobo", "<0-100>"), _kw("Prism", "<0-100>"), _kw("Strobe", "<0-100>"),
              _kw("Channel", "<number | name> <value>")]
    items += [_kw("Variable", '"<name>"'), _kw("Effect", '"<name>" | Off'), _kw("Manual", "[color|position|...]")]
    items += _channel_items(fixtures, numbers=False)
    return items


def _variable_items() -> List[Suggestion]:
    return [_name_item(p.name, p.type) for p in state.presets.values()]


def _effect_items() -> List[Suggestion]:
    items: List[Suggestion] = []
    for fx_id, definition in state.fx_effects.items():
        category = fx_engine._category_of(fx_id)
        items.append(_name_item(str(definition.get("name", "")), category or "?"))
    return items


def _category_items() -> List[Suggestion]:
    return [_kw(c) for c in ("dimmer", "color", "position", "zoom", "focus", "gobo")] + [_kw("all")]


def _level_items(extra: Tuple[str, ...] = ("Full", "Half", "Min")) -> List[Suggestion]:
    return [_kw(word) for word in extra]


def _clause_value_hints(tokens: List[str], i: int, fixtures: List[Any]) -> List[Suggestion]:
    """Eine Klausel ab tokens[i] ist noch nicht fertig: was kommt als Naechstes?"""
    kw = _norm(tokens[i])
    args = tokens[i + 1:]
    if kw in ("at", "full"):
        return _level_items(("Full",)) + [_info("<0-100> | +<n> | -<n>  (%)")]
    if kw in ("color", "colour"):
        if not args:
            return [_kw(name.capitalize()) for name in _NAMED_COLORS] + [_info("#RRGGBB | <r> <g> <b>")]
        return [_info(f"<{'g' if len(args) == 1 else 'b'}> (0-255)")]
    if kw == "rgb":
        return [_info(("<r> <g> <b>", "<g> <b>", "<b>")[min(len(args), 2)] + " (0-255)")]
    if kw in ("pan", "tilt"):
        return [_info("<degrees> | <0-100>% | +<n>")]
    if kw in _BEAM_KEYWORDS:
        return _level_items() + [_info("<0-100> | +<n> | -<n>  (%)")]
    if kw in _VARIABLE_KEYWORDS:
        return (_variable_items() if not args else []) + [_info('"<variable name>"')]
    if kw in _EFFECT_KEYWORDS:
        return ([_kw("Off", "release effects")] + _effect_items() if not args else []) + [_info('"<effect name>" | Off [color|position|...]')]
    if kw in _MANUAL_KEYWORDS:
        return _category_items() + [_info("[dimmer|color|position|zoom|focus|gobo|all]")]
    if kw in ("channel", "ch"):
        if not args:
            return _channel_items(fixtures, numbers=True) + _channel_items(fixtures, numbers=False)
        return [_info("<0-255> (DMX) | <0-100>%" if _is_number(args[0]) else "<0-100>  (%)")]
    if _CHANNEL_TOKEN.match(str(tokens[i])):
        return [_info("<0-255> (DMX) | <0-100>%")]
    return [_info("<0-100>  (%)")]


def _suggest_clause_stream(tokens: List[str], fixtures: List[Any]) -> List[Suggestion]:
    """Attribut-Klauseln hintereinander (nach einer ID-Angabe oder als Top-Level-Befehl): am Ende der letzten fertigen Klausel kommt die naechste."""
    i = 0
    last_head = ""
    while i < len(tokens):
        try:
            _fragment, used, _label = _consume_clause(tokens, i)
        except _Incomplete:
            return _clause_value_hints(tokens, i, fixtures)
        except _CommandError:
            return []
        last_head = _norm(tokens[i])
        i += used
    if last_head in _MANUAL_KEYWORDS:                         # 'Manual' (oder 'Manual color'): weitere Kategorien oder die naechste Klausel
        return _category_items() + _clause_keyword_items(fixtures)
    return _clause_keyword_items(fixtures)


def _suggest_fixture_or_group_context(keyword: str, rest: List[str]) -> List[Suggestion]:
    if keyword == "fixture":
        known = {fx.name.strip().lower() for fx in state.fixtures.values()}
        id_items = [_kw(str(fx.fid), fx.name) for fx in sorted(state.fixtures.values(), key=lambda f: f.fid)]
        id_items += [_name_item(n, "Name") for n in dict.fromkeys(fx.name for fx in state.fixtures.values())]
    else:
        known = {g.strip().lower() for g in state.groups}
        id_items = [_kw(str(i + 1), g) for i, g in enumerate(state.groups)] + [_name_item(g, "Name") for g in state.groups]
    split = _split_spec(rest, known)
    spec_tokens, clause_tokens = rest[:split], rest[split:]
    if clause_tokens:
        return _suggest_clause_stream(clause_tokens, _fixtures_for_names(spec_tokens, keyword))
    if not spec_tokens or str(spec_tokens[-1]).lower() in ("thru", "+"):
        return id_items
    return [_kw("Thru", "<id>"), _kw("+", "<id>")] + _clause_keyword_items(_fixtures_for_names(spec_tokens, keyword))


def _suggest_cue_subcommand(keyword: str, rest: List[str]) -> List[Suggestion]:
    """Store/Delete/Move/Label/Set - alle erwarten 'Cue <number> ...'."""
    if not rest:
        return {"store": [_kw("Cue", "<number>"), _kw("Group", '"<name>"')], "delete": [_kw("Cue", "<number>"), _kw("Group", "<name>"), _kw("Cuelist", "<name>")],
                "label": [_kw("Cue", "<number>"), _kw("Group", "<name>")], "set": [_kw("Cue", "<number>"), _kw("Group", "<name>")]}.get(keyword, [_kw("Cue")])
    head = str(rest[0]).lower()
    if head == "group" and keyword in ("store", "delete", "label", "set"):
        if keyword == "store":
            return [_kw("Merge"), _kw("Overwrite")] if len(rest) >= 2 else [_name_item(g, "overwrite/merge") for g in state.groups] + [_info('"<new group name>" (from the selection)')]
        if len(rest) == 1:
            return [_name_item(g, f"Group {i + 1}") for i, g in enumerate(state.groups)]
        return [_kw("Name", '"<new name>"'), _info('"<new name>"')] if keyword == "set" and len(rest) == 2 else ([_info('"<new name>"')] if keyword == "label" and len(rest) == 2 else [])
    if keyword == "delete" and head in _CUELIST_KEYWORDS:
        return _cuelist_items() if len(rest) == 1 else []
    if head != "cue":
        return []
    if len(rest) == 1:
        return _cue_items()
    if keyword == "delete":
        return [_kw("Thru", "<number>")] if len(rest) == 2 else (_cue_items() if str(rest[-1]).lower() == "thru" else [])
    if len(rest) == 2:
        return {"move": [_kw("At", "<number>")], "set": [_kw("Name", '"<text>"')], "label": [_info('"<text>"')],
                "store": [_kw("Merge"), _kw("Overwrite"), _info('"<name>"')]}.get(keyword, [])
    if keyword == "store" and len(rest) == 3:
        return [_kw("Merge"), _kw("Overwrite")]
    return []


def _suggest_cue_properties(rest: List[str]) -> List[Suggestion]:
    """Top-Level 'Cue <number> [Thru <number>] <Eigenschaft> <Wert>'."""
    if not rest or (len(rest) >= 2 and str(rest[-1]).lower() == "thru"):
        return _cue_items()
    try:
        _low, _high, i = _parse_cue_span(rest)
    except _CommandError:
        return []
    if i >= len(rest):
        return [_kw("Thru", "<number>"), _kw("Fade", "<seconds>"), _kw("Delay", "<seconds>"), _kw("Color", "Fade|Delay"), _kw("Pos", "Fade|Delay"),
                _kw("Beam", "Fade|Delay"), _kw("Zoom", "Fade|Delay"), _kw("FX", "In|Out"), _kw("Trigger", "Go|Follow|Timecode"),
                _kw("MIB", "Off|Auto|On"), _kw("Cmd", '"<commands>"'), _kw("Name", '"<text>"')]
    try:
        (_field, kind, label), j = _match_cue_prop(rest, i)
    except _Incomplete:
        first = _norm(rest[i])
        return [_kw("In"), _kw("Out")] if first in ("fx", "effect") else [_kw("Fade", "<seconds>"), _kw("Delay", "<seconds>")]
    except _CommandError:
        return []
    values = rest[j:]
    if kind == "trigger":
        if not values:
            return [_kw("Go"), _kw("Follow"), _kw("Timecode", "<time>")]
        return [_info("<time>, e.g. 00:01:30.000")] if len(values) == 1 and str(values[0]).lower() in ("timecode", "tc", "time") else []
    if kind == "mib":
        return [_kw("Off"), _kw("Auto"), _kw("On")] if not values else []
    if values:
        return []
    if kind == "opt":
        return [_kw("-", "= general time"), _info("<seconds>")]
    if kind == "time":
        return [_info("<seconds>")]
    return [_info('"<text>"')]


def _suggest_after_list(remaining: List[str], cl: CueList) -> List[Suggestion]:
    """Nach 'Cuelist <name>': der Befehl fuer genau diese Liste (die Cue-Nummern der Vorschlaege gehoeren zu ihr)."""
    token = _target_list.set(cl.id)
    try:
        if not remaining:
            return [_kw(k, h) for k, h in _LIST_SUBCOMMANDS]
        return _suggest_for_context(remaining)
    finally:
        _target_list.reset(token)


def _suggest_cuelist_context(rest: List[str]) -> List[Suggestion]:
    if not rest:
        return [_kw("New", '"<name>"  (creates a cue list)')] + _cuelist_items()
    if str(rest[0]).lower() in ("new", "create", "add") and not getattr(rest[0], "quoted", False):
        return [_info('"<name>"  (empty: Cue List 1, 2 ...)')]
    found = _match_cuelist(rest)
    if found is not None:
        tail = rest[found[1]:]
        if tail and str(tail[0]).lower() in ("rename", "duplicate"):
            return [_info('"<new name>"')]
        return _suggest_after_list(tail, found[0])
    if re.fullmatch(r"\d+", str(rest[0])):
        lists = list(state.cuelists.values())
        n = int(str(rest[0]))
        if 1 <= n <= len(lists):
            return _suggest_after_list(rest[1:], lists[n - 1])
    return []


def _suggest_for_context(ctx_tokens: List[str]) -> List[Suggestion]:
    if not ctx_tokens:
        return [_kw(k, h) for k, h in _TOP_LEVEL_KEYWORDS]          # zuerst die Kategorie; Namen kommen erst danach (Cuelist <Name>, Fixture <Name> ...)

    keyword = str(ctx_tokens[0]).lower()
    rest = ctx_tokens[1:]

    if keyword in ("fixture", "group"):
        return _suggest_fixture_or_group_context(keyword, rest)
    if _is_clause_keyword(ctx_tokens[0]):
        return _suggest_clause_stream(ctx_tokens, _fixtures_for_names())
    if keyword in ("store", "delete", "move", "label", "set"):
        return _suggest_cue_subcommand(keyword, rest)
    if keyword == "cue":
        return _suggest_cue_properties(rest)
    if keyword in ("go", "goto"):
        if not rest:
            return [_kw("Cue", "<number>")] + ([_kw("Back")] if keyword == "go" else []) + _cue_items()
        if len(rest) == 1 and str(rest[0]).lower() == "cue":
            return _cue_items()
        return []
    if keyword == "blackout":
        return [_kw("On"), _kw("Off")] if not rest else []
    if keyword in ("fader", "mix", "master", "grandmaster"):
        args = rest[1:] if rest and str(rest[0]).lower() == "at" else rest
        if args:
            return []
        return ([] if rest else [_kw("At")]) + _level_items(("Full",)) + [_info("<0-100> | +<n> | -<n>  (%)")]
    if keyword in _CUELIST_KEYWORDS:
        return _suggest_cuelist_context(rest)
    if keyword == "off":
        if not rest:
            return [_kw("Exec", "<number>"), _kw("Cuelist", "<name>")]
        if str(rest[0]).lower() in _CUELIST_KEYWORDS and len(rest) == 1:
            return _cuelist_items()
        return []
    if keyword in ("timecode", "tc"):
        if not rest:
            return [_kw("At", "<time>"), _kw("Play"), _kw("Reverse"), _kw("Pause"), _kw("Stop"), _kw("Rate", "<factor>")]
        if len(rest) == 2 and str(rest[0]).lower() == "at":
            return [_kw("Play"), _kw("Reverse")]
        return []
    if keyword == "clear":
        return [_kw("Clear", "full reset")] if not rest else []
    return []


def _split_segment(text: str) -> int:
    """Index, ab dem der aktuelle (letzte) Teilbefehl beginnt: nach dem letzten Komma/Semikolon ausserhalb von Anfuehrungszeichen."""
    in_quotes = False
    last = -1
    for i, ch in enumerate(text):
        if ch == '"':
            in_quotes = not in_quotes
        elif ch in ",;" and not in_quotes:
            last = i
    return last + 1


def get_suggestions(text: str) -> List[Suggestion]:
    """Kontextsensitive Vorschlaege fuer die aktuelle Command-Line-Eingabe (Tab-Autocomplete, siehe app.js). `text` ist der VOLLSTAENDIGE
    Inhalt des Eingabefelds; nur der Teil nach dem letzten Komma/Semikolon wird betrachtet (verkettete Befehle). Das letzte, noch nicht
    abgeschlossene Wort ist nicht Teil des Kontexts, sondern der Praefix-Filter auf die Kandidaten (Namen in einem offenen
    Anfuehrungszeichen eingeschlossen). Jeder Vorschlag traegt `start`: ab dort ersetzt sein `insert` den Text."""
    raw = text or ""
    seg_start = _split_segment(raw)
    segment = raw[seg_start:]
    scanned = _scan(segment)
    if scanned and scanned[-1][3]:                                    # offenes Anfuehrungszeichen: der Name wird noch getippt
        ctx_tokens = [t[0] for t in scanned[:-1]]
        partial, start = str(scanned[-1][0]), seg_start + scanned[-1][1]
    elif not segment or segment[-1].isspace() or not scanned:
        ctx_tokens, partial, start = [t[0] for t in scanned], "", len(raw)
    else:
        ctx_tokens = [t[0] for t in scanned[:-1]]
        partial, start = str(scanned[-1][0]), seg_start + scanned[-1][1]

    candidates = _suggest_for_context(ctx_tokens)
    infos = [c for c in candidates if c.get("info")]
    real = [c for c in candidates if not c.get("info")]
    if partial:
        low = partial.lower()
        exact_or_prefix = [c for c in real if str(c["label"]).lower().startswith(low)]
        real = exact_or_prefix or [c for c in real if len(low) >= 2 and low in str(c["label"]).lower()]
    out = real[:_MAX_ITEMS] + infos
    for c in out:
        c["start"] = start
    return out
