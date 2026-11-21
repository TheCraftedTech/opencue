# Copyright (C) 2026 Samuel Zenker
# SPDX-License-Identifier: GPL-3.0-or-later
"""Die Show BEDIENEN (Klasse "write", `run_command` "critical"): Blackout, Master, Timecode, Cue-Listen, Variablen und Effekte, zurueck auf Manuell, und ein freier Befehl der Befehlszeile.

Alles laeuft ueber die Befehlszeile (`api_v1._run_command`): dieselbe Pruefung, dieselben Meldungen, der Befehl steht dort im Verlauf. Namen (Cue-Listen, Variablen, Effekte) werden VORHER gegen die
Show geprueft und in ihrer echten Schreibweise eingesetzt; Zahlen werden geprueft - in den Befehl kommt nie freier Text der KI (ausser bei `run_command`, der deshalb "critical" ist: jedes Mal fragen).
Funktionen, die Scheinwerfer meinen, lassen die Auswahl der Oberflaeche unberuehrt (`command_line.keep_selection`)."""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from app import command_line
from app.ai.tools.base import Collection, Tool, ToolContext, register, schema
from app.ai.tools.selection import command_clause, fid_text, resolve
from app.ai.tools.show import LIST_LIMIT, _api, _output_note, _state, fail

CATEGORIES = ("dimmer", "color", "position", "zoom", "focus", "gobo")
TIME_TEXT = re.compile(r"^[0-9][0-9:.]{0,14}$")
ON_WORDS = ("on", "an", "ein", "true", "1", "yes", "ja", "aktiv", "active")
OFF_WORDS = ("off", "aus", "false", "0", "no", "nein")
MAX_COMMAND = 200


async def run(command: str, keep: bool = False) -> Dict[str, Any]:
    """Einen Befehl ausfuehren: {"ok", "message", "command"}. `keep`: die Auswahl der Oberflaeche bleibt unberuehrt."""
    token = command_line.keep_selection.set(True) if keep else None
    try:
        result = await _api()._run_command(command, log=True)
    except Exception as exc:
        return fail(exc)
    finally:
        if token is not None:
            command_line.keep_selection.reset(token)
    if not result["success"]:
        return {"ok": False, "error": result["message"] or "The console rejected the command.", "command": command}
    return {"ok": True, "message": result["message"], "command": command}


def _number(value: Any, name: str, low: float = 0, high: float = 100) -> Tuple[Optional[float], Optional[str]]:
    if isinstance(value, bool) or value is None or value == "":
        return None, f"'{name}' is missing."
    try:
        number = float(str(value).strip().rstrip("%").replace(",", "."))
    except ValueError:
        return None, f"'{name}' must be a number from {low:g} to {high:g}, not '{value}'."
    if number != number or not low <= number <= high:
        return None, f"'{name}' must be between {low:g} and {high:g}, not {number:g}."
    return number, None


def _flag(value: Any) -> Optional[bool]:
    text = str(value).strip().lower()
    return True if text in ON_WORDS else False if text in OFF_WORDS else None


def find_name(wanted: Any, names: List[str], what: str) -> Tuple[Optional[str], Optional[str]]:
    """Der echte Name zu dem, was die KI geschrieben hat: genau (Gross-/Kleinschreibung egal), sonst EIN eindeutiger Treffer als Teilwort. Fehler nennt, was es gibt."""
    text = " ".join(str(wanted or "").split()).strip('"\'')
    if not text:
        return None, f"Say which {what}. There are: {', '.join(names[:LIST_LIMIT]) or '(none)'}."
    low = text.lower()
    exact = [n for n in names if n.lower() == low]
    part = [n for n in names if low in n.lower()]
    found = exact or (part if len(part) == 1 else [])
    if len(found) == 1 and '"' not in found[0]:
        return found[0], None
    return None, f"There is no {what} '{text}'. There are: {', '.join(names[:LIST_LIMIT]) or '(none)'}."


def _cuelist(ref: Any) -> Tuple[Optional[Any], Optional[str]]:
    st = _state()
    name, error = find_name(ref, [cl.name for cl in st.cuelists.values()], "cue list")
    if error:
        return None, error
    return next(cl for cl in st.cuelists.values() if cl.name == name), None


def _fixtures(args: Dict[str, Any], notes: List[str], default_all: bool = False) -> Tuple[List[Any], Optional[str]]:
    """Die genannten Scheinwerfer; `default_all`: ohne Angabe alle ("stoppe alle Effekte" nennt keine Nummer)."""
    spec = next((args[k] for k in ("fixtures", "fixture", "fids", "fid", "ids", "group", "name") if args.get(k) not in (None, "")), None)
    return resolve("all" if spec is None and default_all else spec, _state(), notes)


def _with_notes(result: Dict[str, Any], notes: List[str]) -> Dict[str, Any]:
    if result.get("ok") and notes:
        return {"ok": True, "note": " ".join(notes), **{k: v for k, v in result.items() if k != "ok"}}
    return result


# ------------------------------------------------------------------------------------------------------------------ Blackout, Master, Timecode
async def _set_blackout(args: Dict[str, Any], ctx: ToolContext) -> Any:
    raw = next((args[k] for k in ("enabled", "state", "on", "blackout", "value") if args.get(k) not in (None, "")), None)
    wanted = _flag(raw) if raw is not None else None
    if wanted is None:
        return {"ok": False, "error": "Say whether blackout should be on or off: enabled = true (all lights dark) or false (lights back)."}
    result = await run("Blackout On" if wanted else "Blackout Off")
    if result["ok"]:
        result = {**result, "blackout": bool(_state().blackout), "note": "Blackout is ON: all lights are dark." if _state().blackout else "Blackout is off: the lights are back as programmed."}
    return result


async def _set_master(args: Dict[str, Any], ctx: ToolContext) -> Any:
    number, error = _number(args.get("value", args.get("percent", args.get("master", args.get("level")))), "value")
    if error:
        return {"ok": False, "error": error}
    result = await run(f"Master {number:g}")
    if result["ok"]:
        result["grand_master_percent"] = _state().grand_master
    return result


async def _timecode(args: Dict[str, Any], ctx: ToolContext) -> Any:
    action = str(args.get("action", "")).strip().lower()
    position = str(args.get("position", "")).strip()
    if action in ("start", "run", "resume"):
        action = "play"
    if action in ("pause", "stop", "reset"):
        return await run("Timecode Pause" if action == "pause" else "Timecode Stop")
    if action == "play":
        if position:
            if not TIME_TEXT.match(position):
                return {"ok": False, "error": "position must be a time such as 4.3 (seconds) or 1:04.300."}
            return await run(f"Timecode At {position} Play")
        return await run("Timecode Play")
    if action == "seek":
        if not TIME_TEXT.match(position):
            return {"ok": False, "error": "seek needs a position such as 4.3 (seconds) or 1:04.300."}
        return await run(f"Timecode At {position}")
    if action == "rate":
        number, error = _number(args.get("rate"), "rate", 0.1, 8)
        return {"ok": False, "error": error} if error else await run(f"Timecode Rate {number:g}")
    return {"ok": False, "error": "action must be play, pause, stop, seek (with position) or rate (with rate)."}


# ------------------------------------------------------------------------------------------------------------------ Cue-Listen
def _cue_row(c: Dict[str, Any]) -> Dict[str, Any]:
    return {"number": c["number"], "name": c["name"], "active": c["active"], "trigger": c["trigger"], "fade_s": c["fade"], "delay_s": c["delay"], "fixtures": c["fixture_count"], "command": c.get("command") or None}


async def _read_cuelist(args: Dict[str, Any], ctx: ToolContext) -> Any:
    cl, error = _cuelist(args.get("cuelist", args.get("name", args.get("list"))))
    if error:
        return {"ok": False, "error": error}
    try:
        data = await _api().get_cuelist(cl.id)
    except Exception as exc:
        return fail(exc)
    cues = [_cue_row(c) for c in data["cues"][:LIST_LIMIT]]
    result = {"ok": True, "cuelist": data["name"], "total_cues": data["cue_count"], "active_cue": (data["active_cue"] or {}).get("number"), "fader_percent": data["fader"],
              "state": (data.get("playback") or {}).get("state"), "cues": cues}
    if data["cue_count"] > len(cues):
        result["note"] = f"Only the first {len(cues)} cues are shown."
    return result


_CUE_ACTIONS = {"go": "Go", "next": "Go", "play": "Go", "start": "Go", "back": "Back", "previous": "Back", "pause": "Pause", "resume": "Resume", "continue": "Resume", "stop": "Stop"}


async def _control_cuelist(args: Dict[str, Any], ctx: ToolContext) -> Any:
    cl, error = _cuelist(args.get("cuelist", args.get("name", args.get("list"))))
    if error:
        return {"ok": False, "error": error}
    action = _CUE_ACTIONS.get(str(args.get("action", "go")).strip().lower())
    if action is None:
        return {"ok": False, "error": "action must be go (next cue, or jump to 'cue'), back, pause, resume or stop."}
    command = f'Cuelist "{cl.name}" {action}'
    cue = args.get("cue", args.get("cue_number"))
    if cue not in (None, ""):
        number, error = _number(cue, "cue", 0, 99999)
        if error:
            return {"ok": False, "error": error}
        if action != "Go":
            return {"ok": False, "error": "A cue number only goes with action go (jump to that cue)."}
        if not any(abs(c.number - number) < 1e-9 for c in cl.cues):
            return {"ok": False, "error": f"The cue list '{cl.name}' has no cue {number:g}. It has: {', '.join(f'{c.number:g}' for c in sorted(cl.cues, key=lambda c: c.number)[:LIST_LIMIT]) or '(no cues)'}."}
        command += f" Cue {number:g}"
    result = await run(command)
    return {**result, "cuelist": cl.name} if result["ok"] else result


async def _cuelist_fader(args: Dict[str, Any], ctx: ToolContext) -> Any:
    cl, error = _cuelist(args.get("cuelist", args.get("name", args.get("list"))))
    if error:
        return {"ok": False, "error": error}
    number, error = _number(args.get("value", args.get("percent", args.get("level"))), "value")
    if error:
        return {"ok": False, "error": error}
    result = await run(f'Cuelist "{cl.name}" Fader {number:g}')
    return {**result, "cuelist": cl.name, "fader_percent": _state().cuelist_masters.get(cl.id, 100.0)} if result["ok"] else result


# ------------------------------------------------------------------------------------------------------------------ Variablen und Effekte auf Scheinwerfer
async def _apply_variable(args: Dict[str, Any], ctx: ToolContext) -> Any:
    st = _state()
    notes: List[str] = []
    fixtures, error = _fixtures(args, notes)
    if error:
        return {"ok": False, "error": error}
    name, error = find_name(args.get("variable", args.get("preset", args.get("name_of_variable"))), [p.name for p in st.presets.values()], "variable")
    if error:
        return {"ok": False, "error": error}
    result = await run(f'{command_clause(fixtures)} Variable "{name}"', keep=True)
    return _with_notes({**result, "variable": name, "fixtures": fid_text([int(f.fid) for f in fixtures if f.fid]) or "named"} if result["ok"] else result, notes)


def _effect_names() -> List[str]:
    return [str(fx.get("name") or key) for key, fx in _state().fx_effects.items()]


async def _apply_effect(args: Dict[str, Any], ctx: ToolContext) -> Any:
    notes: List[str] = []
    fixtures, error = _fixtures(args, notes)
    if error:
        return {"ok": False, "error": error}
    name, error = find_name(args.get("effect"), _effect_names(), "effect")
    if error:
        return {"ok": False, "error": error}
    result = await run(f'{command_clause(fixtures)} Effect "{name}"', keep=True)
    return _with_notes({**result, "effect": name, "fixtures": fid_text([int(f.fid) for f in fixtures if f.fid]) or "named"} if result["ok"] else result, notes)


async def _stop_effects(args: Dict[str, Any], ctx: ToolContext) -> Any:
    notes: List[str] = []
    fixtures, error = _fixtures(args, notes, default_all=True)
    if error:
        return {"ok": False, "error": error}
    result = await run(f"{command_clause(fixtures)} Effect Off", keep=True)
    return _with_notes({**result, "fixtures": fid_text([int(f.fid) for f in fixtures if f.fid]) or "named"} if result["ok"] else result, notes)


async def _release(args: Dict[str, Any], ctx: ToolContext) -> Any:
    notes: List[str] = []
    fixtures, error = _fixtures(args, notes, default_all=True)
    if error:
        return {"ok": False, "error": error}
    raw = args.get("what", args.get("categories", ""))
    wanted = [w.lower() for w in re.split(r"[,\s;]+", " ".join(str(x) for x in raw) if isinstance(raw, list) else str(raw or "")) if w]
    bad = [w for w in wanted if w not in CATEGORIES and w != "all"]
    if bad:
        return {"ok": False, "error": f"Unknown kind '{bad[0]}'. Use all or any of: {', '.join(CATEGORIES)}."}
    result = await run(f"{command_clause(fixtures)} Manual {' '.join(wanted)}".strip(), keep=True)
    return _with_notes({**result, "fixtures": fid_text([int(f.fid) for f in fixtures if f.fid]) or "named"} if result["ok"] else result, notes)


# ------------------------------------------------------------------------------------------------------------------ freier Befehl
async def _run_command(args: Dict[str, Any], ctx: ToolContext) -> Any:
    command = " ".join(str(args.get("command", args.get("text", ""))).split())
    if not command:
        return {"ok": False, "error": "Give the command, e.g. \"Fixture 1 Thru 4 At 80\" or \"Cuelist Show Go\"."}
    if len(command) > MAX_COMMAND:
        return {"ok": False, "error": f"The command is too long (at most {MAX_COMMAND} characters)."}
    result = await run(command)
    return {**result, **_output_note(_state())} if result["ok"] else result


# ------------------------------------------------------------------------------------------------------------------ Auswahl, Gruppen, Cues speichern / loeschen
NAME_TEXT = re.compile(r"^[\w][\w .,!?+&()/-]{0,39}$")


def _clean_name(value: Any, what: str) -> Tuple[Optional[str], Optional[str]]:
    text = " ".join(str(value or "").split())
    if not NAME_TEXT.match(text) or '"' in text:
        return None, f"Give a {what} of 1-40 letters, digits or spaces (no quotation marks)."
    return text, None


async def _read_selection(args: Dict[str, Any], ctx: ToolContext) -> Any:
    st = _state()
    chosen = [st.fixtures[i] for i in st.selected_fixture_ids if i in st.fixtures]
    return {"ok": True, "count": len(chosen), "fixtures": [{"fid": f.fid, "name": f.name} for f in chosen[:LIST_LIMIT]], "note": None if chosen else "No fixture is selected in the interface."}


async def _select_fixtures(args: Dict[str, Any], ctx: ToolContext) -> Any:
    notes: List[str] = []
    spec = next((args[k] for k in ("fixtures", "fixture", "fids", "ids", "group") if args.get(k) not in (None, "")), None)
    if str(spec).strip().lower() in ("none", "nothing", "keine", "nichts", "clear"):
        result = await run("Clear")
        return {**result, "selected": 0} if result["ok"] else result
    fixtures, error = resolve(spec, _state(), notes)
    if error:
        return {"ok": False, "error": error}
    result = await run(command_clause(fixtures))
    return _with_notes({**result, "selected": len(fixtures), "fixtures": fid_text([int(f.fid) for f in fixtures if f.fid]) or "named"} if result["ok"] else result, notes)


async def _create_group(args: Dict[str, Any], ctx: ToolContext) -> Any:
    name, error = _clean_name(args.get("name", args.get("group")), "group name")
    if error:
        return {"ok": False, "error": error}
    st = _state()
    if any(g.strip().lower() == name.lower() for g in st.groups):
        return {"ok": False, "error": f"A group '{name}' already exists. Choose another name. Groups: {', '.join(st.groups) or '(none)'}."}
    notes: List[str] = []
    fixtures, error = resolve(next((args[k] for k in ("fixtures", "fixture", "fids", "ids") if args.get(k) not in (None, "")), None), st, notes)
    if error:
        return {"ok": False, "error": error}
    before = list(st.selected_fixture_ids)                           # "Store Group" speichert die AUSWAHL: kurz auswaehlen, speichern, die Auswahl des Benutzers zurueck
    try:
        selected = await run(command_clause(fixtures))
        result = await run(f'Store Group "{name}"') if selected["ok"] else selected
    finally:
        st.set_selection(before)
        await _api()._srv().event_bus.broadcast({"type": "selection_changed", "payload": {"selected_ids": st.selected_fixture_ids}})
    return _with_notes({**result, "group": name, "fixtures": fid_text([int(f.fid) for f in fixtures if f.fid]) or "named"} if result["ok"] else result, notes)


async def _delete_group(args: Dict[str, Any], ctx: ToolContext) -> Any:
    name, error = find_name(args.get("name", args.get("group")), list(_state().groups), "group")
    if error:
        return {"ok": False, "error": error}
    result = await run(f'Delete Group "{name}"')
    return {**result, "deleted_group": name} if result["ok"] else result


async def _store_cue(args: Dict[str, Any], ctx: ToolContext) -> Any:
    cl, error = _cuelist(args.get("cuelist", args.get("list")))
    if error:
        return {"ok": False, "error": error}
    number, error = _number(args.get("cue", args.get("number")), "cue", 0, 99999)
    if error:
        return {"ok": False, "error": error}
    command = f'Cuelist "{cl.name}" Store Cue {number:g}'
    if args.get("name") not in (None, ""):
        label, error = _clean_name(args.get("name"), "cue name")
        if error:
            return {"ok": False, "error": error}
        command += f' "{label}"'
    mode = str(args.get("if_exists", "")).strip().lower()
    if mode in ("merge", "overwrite"):
        command += " " + mode.capitalize()
    elif mode:
        return {"ok": False, "error": "if_exists must be merge or overwrite (or left out)."}
    result = await run(command)
    if result["ok"]:
        result["note"] = "The cue stores the values currently set in the programmer (the red / touched values)."
    return {**result, "cuelist": cl.name, "cue": number} if result["ok"] else result


async def _delete_cue(args: Dict[str, Any], ctx: ToolContext) -> Any:
    cl, error = _cuelist(args.get("cuelist", args.get("list")))
    if error:
        return {"ok": False, "error": error}
    number, error = _number(args.get("cue", args.get("number")), "cue", 0, 99999)
    if error:
        return {"ok": False, "error": error}
    if not any(abs(c.number - number) < 1e-9 for c in cl.cues):
        return {"ok": False, "error": f"The cue list '{cl.name}' has no cue {number:g}. It has: {', '.join(f'{c.number:g}' for c in sorted(cl.cues, key=lambda c: c.number)[:LIST_LIMIT]) or '(no cues)'}."}
    result = await run(f'Cuelist "{cl.name}" Delete Cue {number:g}')
    return {**result, "cuelist": cl.name, "deleted_cue": number} if result["ok"] else result


# ------------------------------------------------------------------------------------------------------------------ Syntax der Befehlszeile (aus der mitgelieferten Anleitung)
HELP_TOPICS = {"overview": 15, "quick": 15, "selection": 2, "select": 2, "groups": 2, "values": 3, "brightness": 3, "master": 3, "blackout": 3, "timecode": 3, "color": 4, "colour": 4, "position": 4,
               "pan": 4, "tilt": 4, "channels": 5, "beam": 5, "zoom": 5, "effects": 6, "variables": 6, "manual": 6, "combine": 7, "chain": 8, "clear": 9, "cuelists": 10, "cuelist": 10,
               "playback": 10, "cues": 11, "cue": 11, "store": 11}
HELP_LIMIT = 3600


def _help_sections(language: str) -> Dict[int, str]:
    from app import paths
    folder = paths.project_root() / "static" / "help"
    path = folder / f"commands.{'de' if language == 'de' else 'en'}.md"
    if not path.exists():
        path = folder / "commands.en.md"
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    parts = re.split(r"(?m)^## (\d+)\. ", text)
    return {int(parts[i]): parts[i + 1] for i in range(1, len(parts) - 1, 2)}


async def _command_help(args: Dict[str, Any], ctx: ToolContext) -> Any:
    topic = str(args.get("topic", "") or "overview").strip().lower()
    number = HELP_TOPICS.get(topic)
    if number is None:
        return {"ok": False, "error": f"No such topic '{topic}'. Topics: {', '.join(sorted(set(HELP_TOPICS) - {'quick'}))}."}
    try:
        text = _help_sections(ctx.language).get(number, "")
    except OSError as exc:
        return fail(exc)
    if not text:
        return {"ok": False, "error": "The command reference is not available."}
    text = text.strip()
    result = {"ok": True, "topic": topic, "reference": text[:HELP_LIMIT]}
    if len(text) > HELP_LIMIT:
        result["note"] = "Shortened. Ask for a narrower topic for the rest."
    if topic in ("overview", "quick"):
        result["more_topics"] = "selection, values, color, channels, effects, combine, clear, cuelists, cues"
    return result


FIXTURES_PARAM = {"type": "string", "description": "Which fixtures: \"all\", a range like \"1-5\", numbers like \"1, 3, 7\" (or \"1-3, 7\"), or the name of a group."}

register(Collection("cuelists", "cuelist_functions",
                    "Gives you more functions for CUE LISTS: read the cues of one list, play it (go / back / pause / stop, jump to a cue) and set its fader. "
                    "Call it ONLY when the user asks about the cues of a list or wants to play or stop one - never for greetings, thanks or small talk.", [
    Tool("read_cuelist", "Reads ONE cue list with all its cues: number, name, trigger, fade and delay times, how many fixtures each cue sets, which cue is active and whether it plays. Use it for \"which cues does the cue list <name> have?\", \"welche Cues hat die Liste <Name>?\", \"what is in the list?\", \"which cue is active in <name>?\". Give the name of the list.",
         schema({"cuelist": {"type": "string", "description": "Name of the cue list."}}, ["cuelist"]), _read_cuelist),
    Tool("control_cuelist", "PLAYS a cue list: go = the next cue (or jump to a cue with 'cue'), back = the previous cue, pause, resume, stop. Use it for \"go in cue list Show\", \"starte die Cue-Liste Show\", \"nächster Cue\", \"gehe zu Cue 3 in Show\", \"stop the cue list\". The values you give are used; to only LOOK use read_cuelist.",
         schema({"cuelist": {"type": "string", "description": "Name of the cue list."}, "action": {"type": "string", "description": "go (default), back, pause, resume or stop."},
                 "cue": {"type": "number", "description": "Only with go: the cue number to jump to (e.g. 3 or 1.5)."}}, ["cuelist"]), _control_cuelist, access="write"),
    Tool("store_cue", "STORES the values currently set in the programmer (the changed fixtures) as a NEW CUE of a cue list. Use it for \"store this as cue 4 in <list>\", \"speichere das als Cue 5 in der Liste <Name>\". "
                      "First set the values (for example with set_fixtures), then store. If the cue number exists you get an error - then use if_exists merge or overwrite.",
         schema({"cuelist": {"type": "string", "description": "Name of the cue list."}, "cue": {"type": "number", "description": "Cue number, e.g. 4 or 1.5."}, "name": {"type": "string", "description": "Optional name of the cue."},
                 "if_exists": {"type": "string", "description": "Only if the cue number exists: merge (add the new values) or overwrite (replace the content)."}}, ["cuelist", "cue"]), _store_cue, access="write"),
    Tool("delete_cue", "DELETES one cue of a cue list (CRITICAL: the user is asked first). Use it for \"delete cue 3 in <list>\", \"lösche Cue 3 aus der Liste <Name>\".",
         schema({"cuelist": {"type": "string", "description": "Name of the cue list."}, "cue": {"type": "number", "description": "The cue number."}}, ["cuelist", "cue"]), _delete_cue, access="critical"),
    Tool("set_cuelist_fader", "Sets the FADER (mix level) of a cue list in percent: 0 = nothing of the list is output, 100 = full. Use it for \"set the fader of Show to 50\", \"Fader von Show auf 80 Prozent\".",
         schema({"cuelist": {"type": "string", "description": "Name of the cue list."}, "value": {"type": "number", "description": "Percent, 0-100."}}, ["cuelist", "value"]), _cuelist_fader, access="write"),
]))

register(Collection("looks", "look_functions",
                    "Gives you more functions to put VARIABLES (saved colours, positions ...) and EFFECTS on fixtures, to stop effects and to hand fixtures back to manual control. "
                    "Call it ONLY when the user asks for that - never for greetings, thanks or small talk.", [
    Tool("apply_variable", "Puts a saved VARIABLE (e.g. a colour or position preset of the show) on fixtures. Use it for \"put the variable <name> on fixtures 1 to 4\", \"wende die Variable <Name> auf die Gruppe Front an\". Use ONLY a name that list_variables shows.",
         schema({"fixtures": FIXTURES_PARAM, "variable": {"type": "string", "description": "Name of the variable."}}, ["fixtures", "variable"]), _apply_variable, access="write"),
    Tool("apply_effect", "STARTS an EFFECT on fixtures. Use it for \"start the effect <name> on all fixtures\", \"starte den Effekt <Name> auf Scheinwerfer 1 bis 3\". Use ONLY the name the user said or one that list_effects shows.",
         schema({"fixtures": FIXTURES_PARAM, "effect": {"type": "string", "description": "Name of the effect."}}, ["fixtures", "effect"]), _apply_effect, access="write"),
    Tool("stop_effects", "STOPS all effects on fixtures (the values stay as they are). Use it for \"stop the effects\", \"stoppe alle Effekte\", \"beende die Effekte auf Scheinwerfer 2\". Without 'fixtures' it stops them on ALL fixtures.",
         schema({"fixtures": FIXTURES_PARAM}), _stop_effects, access="write"),
    Tool("release_fixtures", "Hands fixtures back to MANUAL: releases the variables and effects on them (the last values stay). Optional 'what': all (default) or kinds such as dimmer, color, position, zoom, focus, gobo. Use it for \"release fixture 1\", \"gib Scheinwerfer 1 bis 4 frei\". Without 'fixtures' it releases ALL fixtures.",
         schema({"fixtures": FIXTURES_PARAM, "what": {"type": "string", "description": "all (default) or a list of: dimmer, color, position, zoom, focus, gobo."}}), _release, access="write"),
]))

register(Collection("groups", "group_functions",
                    "Gives you more functions for the SELECTION in the interface and for fixture GROUPS: what is selected, select fixtures, create a group, delete a group. "
                    "Call it ONLY when the user asks about the selection or about groups - never for greetings, thanks or small talk.", [
    Tool("read_selection", "Reads which fixtures are SELECTED in the interface right now. Use it for \"which fixtures are selected?\", \"was ist ausgewählt?\".", schema(), _read_selection),
    Tool("select_fixtures", "SELECTS fixtures in the interface (the user sees them selected). Use it for \"select fixtures 1 to 4\", \"wähle die Gruppe <Name> aus\", \"select nothing\". Give 'none' to clear the selection. "
                            "(set_fixtures does NOT need a selection - only use this when the user wants the selection itself.)",
         schema({"fixtures": FIXTURES_PARAM}, ["fixtures"]), _select_fixtures, access="write"),
    Tool("create_group", "CREATES a new fixture GROUP from fixtures. Use it for \"make a group <name> from fixtures 1 to 4\", \"lege die Gruppe <Name> aus Scheinwerfer 5 und 6 an\". The selection in the interface stays as it is. An existing name is an error.",
         schema({"name": {"type": "string", "description": "Name of the new group."}, "fixtures": FIXTURES_PARAM}, ["name", "fixtures"]), _create_group, access="write"),
    Tool("delete_group", "DELETES a fixture group (the fixtures stay) (CRITICAL: the user is asked first). Use it for \"delete the group <name>\", \"lösche die Gruppe <Name>\".",
         schema({"name": {"type": "string", "description": "Name of the group."}}, ["name"]), _delete_group, access="critical"),
]))

register(Collection("commands", "command_functions",
                    "Gives you the function that runs ANY command of the OpenCue command line - only for things no other function can do. "
                    "Call it ONLY when no other function fits and the user asks for it - never for greetings, thanks or small talk.", [
    Tool("command_help", "Gives the SYNTAX of the OpenCue command line from the user guide (examples for every command). Use it for \"how do I write ... in the command line?\", \"wie schreibe ich in der Befehlszeile ...?\", \"wie geht der Befehl ...?\" (the user wants an EXPLANATION, nothing is changed) and BEFORE run_command whenever you are not sure how a command is written. "
                         "Without a topic you get the quick reference; topics: selection, values, color, channels, effects, combine, clear, cuelists, cues.",
         schema({"topic": {"type": "string", "description": "Optional: selection, values, color, channels, effects, combine, clear, cuelists or cues. Default: the quick reference."}}), _command_help, access="free"),
    Tool("run_command", "Runs ONE command of the OpenCue command line exactly as if the user typed it (CRITICAL: the user is always asked first). Grammar: select with Fixture 1 Thru 5 + 8 / Group Front, then values: At 80, Color Red, Pan 30, Zoom 40, Frost 50; "
                        "Cuelist \"Show\" Go / Back / Stop / Fader 50; Master 80; Blackout On / Off; Timecode Play / Pause / Stop; Store Cue 3 \"Name\"; Delete Cue 3; Clear. Combine: Fixture 1 Thru 4 At 80 Color Blue; chain with ';'. Use the other functions when one fits - they are checked more strictly. If unsure how a command is written, call command_help first.",
         schema({"command": {"type": "string", "description": "The command, e.g. \"Fixture 1 Thru 4 At 80 Color Blue\"."}}, ["command"]), _run_command, access="critical"),
]))
