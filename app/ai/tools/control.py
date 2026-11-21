# Copyright (C) 2026 Samuel Zenker
# SPDX-License-Identifier: GPL-3.0-or-later
"""Sammlung "control": die Show VERAENDERN (Klasse "write": der Benutzer entscheidet in den Einstellungen, ob die KI fragen muss).

`set_fixtures` stellt Werte von Scheinwerfern - Helligkeit, Farbe, Pan / Tilt, Zoom, Fokus, Gobo, Prisma, Strobe und jeden anderen Kanal - genauso wie die Kommandozeile
(`Fixture 1 Thru 5 At 80 Color Red`): der Befehl wird gebaut und ueber `api_v1._run_command` ausgefuehrt, mit derselben Pruefung und denselben Fehlermeldungen. Alle Werte
werden VORHER streng geprueft - in den Befehl kommen nur Zahlen, Farbnamen und Kanalnamen aus erlaubten Zeichen, nie Text der KI."""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from app import command_line
from app.ai.tools import operate
from app.ai.tools.base import Collection, Tool, ToolContext, register, schema
from app.ai.tools.selection import command_clause, fid_text, resolve
from app.ai.tools.show import _output_note, _state, fail
from app.ai.tools import show as _show

MAX_CHANNELS = 12
COLORS = {"red", "green", "blue", "white", "black", "yellow", "cyan", "magenta", "orange", "pink", "purple", "amber", "lime", "teal", "violet", "lightblue", "warm", "cool"}
COLOR_ALIASES = {"rot": "red", "gruen": "green", "grün": "green", "blau": "blue", "weiss": "white", "weiß": "white", "schwarz": "black", "gelb": "yellow", "rosa": "pink",
                 "lila": "purple", "tuerkis": "teal", "türkis": "teal", "hellblau": "lightblue", "light blue": "lightblue", "kalt": "cool", "kaltweiss": "cool", "kaltweiß": "cool",
                 "warmweiss": "warm", "warmweiß": "warm", "warm white": "warm", "cold": "cool", "bernstein": "amber", "dunkelrot": "red"}
HEX = re.compile(r"^#?([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")
TRIPLE = re.compile(r"^\s*(\d{1,3})\s*[,; ]\s*(\d{1,3})\s*[,; ]\s*(\d{1,3})\s*$")
NUMBER = re.compile(r"^[+-]?\d+(?:\.\d+)?%?$")
CHANNEL_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 _.\-/]{0,38}$")
# Wert -> Klausel der Kommandozeile (alle in Prozent 0-100)
PERCENT_FIELDS = (("brightness", "At", ("dimmer", "intensity", "level", "helligkeit")), ("zoom", "Zoom", ()), ("focus", "Focus", ("fokus",)), ("gobo", "Gobo", ()),
                  ("prism", "Prism", ("prisma",)), ("strobe", "Strobe", ("shutter",)))


class ValueError_(Exception):
    pass


def _number(value: Any) -> Optional[float]:
    """Eine Zahl aus Zahl oder Text ('50', '50%', '50,5'); None: keine Zahl."""
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value) if value == value and abs(value) < 1e9 else None
    text = str(value).strip().replace(",", ".")
    if not NUMBER.match(text):
        return None
    return float(text.rstrip("%"))


def _shown(number: float) -> str:
    return f"{number:g}"


def _percent(value: Any, name: str) -> str:
    low = str(value).strip().lower()
    if name == "brightness" and low in ("full", "voll", "an", "on", "max"):
        return "100"
    if name == "brightness" and low in ("off", "aus", "dark", "dunkel", "min"):
        return "0"
    number = _number(value)
    if number is None:
        raise ValueError_(f"'{name}' must be a number from 0 to 100 (percent), not '{value}'.")
    if not 0 <= number <= 100:
        raise ValueError_(f"'{name}' must be between 0 and 100 (percent), not {_shown(number)}.")
    return _shown(number)


def _angle(value: Any, name: str) -> str:
    number = _number(value)
    text = str(value).strip()
    if number is None:
        raise ValueError_(f"'{name}' must be a number: degrees (e.g. 30 or -45) or a percent of the range (e.g. 50%), not '{value}'.")
    if text.endswith("%"):
        if not 0 <= number <= 100:
            raise ValueError_(f"'{name}' in percent must be between 0 and 100.")
        return _shown(number) + "%"
    if abs(number) > 1000:
        raise ValueError_(f"'{name}' in degrees is out of range.")
    return _shown(number)


def _color(value: Any) -> str:
    text = " ".join(str(value).split()).strip().strip('"\'')
    low = text.lower()
    if low in COLORS:
        return low
    if low in COLOR_ALIASES:
        return COLOR_ALIASES[low]
    if HEX.match(text):
        return "#" + HEX.match(text).group(1)
    triple = TRIPLE.match(text)
    if triple:
        parts = [int(g) for g in triple.groups()]
        if max(parts) > 255:
            raise ValueError_("Colour values must be 0-255 (red, green, blue).")
        return " ".join(str(p) for p in parts)
    raise ValueError_(f"Unknown colour '{value}'. Use a name ({', '.join(sorted(COLORS))}), a hex colour such as #FF8000, or three numbers 0-255 (red, green, blue).")


def _channels(value: Any) -> List[str]:
    """Weitere Kanaele: {"Frost": 50} (Name des Kanals -> Prozent) -> Klauseln 'Channel Frost 50'."""
    if value in (None, "", {}, []):
        return []
    items: List[tuple] = []
    if isinstance(value, dict):
        items = list(value.items())
    elif isinstance(value, list) and all(isinstance(v, dict) for v in value):
        items = [(v.get("name") or v.get("channel"), v.get("value", v.get("percent"))) for v in value]
    else:
        raise ValueError_("'channels' must be an object that maps a channel name to a percent, e.g. {\"Frost\": 50, \"Iris\": 20}.")
    if len(items) > MAX_CHANNELS:
        raise ValueError_(f"At most {MAX_CHANNELS} extra channels per call.")
    out = []
    for name, raw in items:
        name = str(name or "").strip()
        if not CHANNEL_NAME.match(name):
            raise ValueError_(f"'{name}' is not a usable channel name.")
        number = _number(raw)
        if number is None or not 0 <= number <= 100:
            raise ValueError_(f"The value of channel '{name}' must be a percent from 0 to 100.")
        out.append(f'Channel "{name}" {_shown(number)}' if " " in name else f"Channel {name} {_shown(number)}")
    return out


def build_command(fixtures: List[Any], args: Dict[str, Any]) -> tuple:
    """(Befehl der Kommandozeile, Liste der gesetzten Werte als Text). ValueError_ bei jedem ungueltigen Wert."""
    clauses: List[str] = []
    done: List[str] = []
    for key, word, aliases in PERCENT_FIELDS:
        raw = next((args[k] for k in (key,) + aliases if args.get(k) not in (None, "")), None)
        if raw is None:
            continue
        value = _percent(raw, key)
        clauses.append(f"{word} {value}")
        done.append(f"{key} {value} %")
    if args.get("color") not in (None, ""):
        value = _color(args["color"])
        clauses.append(f"Color {value}")
        done.append(f"colour {value}")
    for key, word in (("pan", "Pan"), ("tilt", "Tilt")):
        if args.get(key) not in (None, ""):
            value = _angle(args[key], key)
            clauses.append(f"{word} {value}")
            done.append(f"{key} {value}" + ("" if value.endswith("%") else " degrees"))
    for clause in _channels(args.get("channels")):
        clauses.append(clause)
        done.append(clause.replace("Channel ", "channel ").replace('"', ""))
    if not clauses:
        raise ValueError_("Nothing to set. Give at least one value: brightness (0-100), color, pan, tilt, zoom, focus, gobo, prism, strobe or channels.")
    return command_clause(fixtures) + " " + " ".join(clauses), done


async def _set_fixtures(args: Dict[str, Any], ctx: ToolContext) -> Any:
    spec = next((args[k] for k in ("fixtures", "fixture", "fids", "fid", "ids", "group", "name") if args.get(k) not in (None, "")), None)
    st = _state()
    notes: List[str] = []
    fixtures, error = resolve(spec, st, notes)
    if error:
        return {"ok": False, "error": error}
    try:
        command, done = build_command(fixtures, args)
    except ValueError_ as exc:
        return {"ok": False, "error": str(exc)}
    token = command_line.keep_selection.set(True)              # die Auswahl der Oberflaeche bleibt unberuehrt: der Benutzer arbeitet nebenher ungestoert weiter
    try:
        result = await _show._api()._run_command(command, log=True)
    except Exception as exc:
        return fail(exc)
    finally:
        command_line.keep_selection.reset(token)
    names = fid_text([int(f.fid) for f in fixtures if f.fid])
    if not result["success"]:
        return {"ok": False, "error": result["message"] or "The console rejected the command.", "command": command}
    out = {"ok": True, "message": result["message"], "fixtures": names or ", ".join(f.name for f in fixtures), "count": len(fixtures), "set": done, "command": command, **_output_note(st)}
    if notes:                                                          # der Hinweis steht VORNE: kleine Modelle lesen das Ende eines Ergebnisses nicht
        out = {"ok": True, "note": " ".join(notes) + (" " + out["note"] if out.get("note") else ""), **{k: v for k, v in out.items() if k not in ("ok", "note")}}
    return out


register(Collection("control", "control_functions",
                    "Gives you more functions for CHANGING the current OpenCue show: set the brightness, colour, position (pan / tilt), zoom ... of fixtures, blackout, the grand master and the timecode. "
                    "Call it ONLY when the user asks you to change something (e.g. \"set fixture 3 to 50 percent\") - never for questions, greetings, thanks or small talk.", [
    Tool("set_fixtures", "CHANGES values of fixtures (lights). Use it for \"set fixture 3 to 50 percent\", \"stelle Scheinwerfer 1 bis 5 auf 80 Prozent\", \"make all fixtures red\", \"mach Scheinwerfer 2 aus\", "
                         "\"Gruppe Front auf Blau\", \"turn the pan of fixture 4 to 90 degrees\". The values you give are set; everything else stays as it is. "
                         "Give the fixtures and at least one value. To only LOOK at values use read_fixtures.",
         schema({"fixtures": {"type": "string", "description": "Which fixtures: \"all\", a range like \"1-5\", numbers like \"1, 3, 7\" (or \"1-3, 7\"), or the name of a group."},
                 "brightness": {"type": "number", "description": "Brightness in percent, 0 (off) to 100 (full)."},
                 "color": {"type": "string", "description": "A name (red, blue, warm ...), #hex or \"255 128 0\"."},
                 "pan": {"type": "number", "description": "Degrees (30, -45) or percent (\"50%\")."},
                 "tilt": {"type": "number", "description": "Degrees (30, -45) or percent (\"50%\")."},
                 "zoom": {"type": "number", "description": "Zoom in percent, 0-100."},
                 "focus": {"type": "number", "description": "Focus in percent, 0-100."},
                 "gobo": {"type": "number", "description": "Gobo wheel, percent 0-100."},
                 "prism": {"type": "number", "description": "Prism in percent, 0-100."},
                 "strobe": {"type": "number", "description": "Shutter / strobe in percent, 0-100."},
                 "channels": {"type": "object", "description": "Any other channel by name, percent: {\"Frost\": 50}."}},
                ["fixtures"]), _set_fixtures, access="write"),
    Tool("set_blackout", "Switches BLACKOUT on or off: on = every light goes dark at once (the values are kept), off = the lights are back as programmed. Use it for \"blackout\", \"mach alles dunkel\", \"Blackout aus\", \"lights back on\".",
         schema({"enabled": {"type": "boolean", "description": "true = blackout on (dark), false = blackout off (lights back)."}}, ["enabled"]), operate._set_blackout, access="write"),
    Tool("set_master", "Sets the GRAND MASTER in percent: it scales the brightness of ALL fixtures (100 = as programmed, 0 = dark). Use it for \"master to 50\", \"Gesamthelligkeit auf 80 Prozent\", \"dim everything to half\".",
         schema({"value": {"type": "number", "description": "Percent, 0-100."}}, ["value"]), operate._set_master, access="write"),
    Tool("timecode_control", "Controls the global TIMECODE clock: play, pause, stop (back to 0), seek (jump to a position) or rate (speed 0.1-8). Use it for \"start the timecode\", \"Timecode anhalten\", \"jump to 1:30\".",
         schema({"action": {"type": "string", "description": "play, pause, stop, seek or rate."}, "position": {"type": "string", "description": "For seek (and optionally play): seconds such as 4.3 or a time such as 1:04.300."},
                 "rate": {"type": "number", "description": "For rate: the speed, 0.1-8 (1 = normal)."}}, ["action"]), operate._timecode, access="write"),
]))
