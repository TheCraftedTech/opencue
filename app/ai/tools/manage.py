# Copyright (C) 2026 Samuel Zenker
# SPDX-License-Identifier: GPL-3.0-or-later
"""Die Show VERWALTEN: Patch (Scheinwerfer anlegen / aendern / loeschen), Showfiles (speichern / laden / neu / loeschen / umbenennen), Variablen, Effekte, Cue-Eigenschaften und Cue-Listen.

Jede Funktion ruft direkt die Funktion der REST-API auf (`api_v1_system` / `api_v1_manage`) - ohne HTTP und ohne Token: dieselbe Pruefung, dieselben Fehlermeldungen, dieselben Meldungen an alle Geraete.
Die Antworten der API werden fuer kleine Modelle gekuerzt. Was Daten unwiderruflich entfernt (Scheinwerfer, Variablen, Effekte, Cue-Listen, Showfiles loeschen; eine andere Show laden; eine neue Show) ist "critical":
der Benutzer wird gefragt (oder hat "Immer erlauben" gewaehlt). Zahlen und Namen werden geprueft; die KI kann nichts ausser dem tun, was die API erlaubt."""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from app.ai.tools.base import Collection, Tool, ToolContext, register, schema
from app.ai.tools.operate import FIXTURES_PARAM, NAME_TEXT, _cuelist, _flag, _number, find_name
from app.ai.tools.selection import fid_text, resolve
from app.ai.tools.show import LIST_LIMIT, _state

HEX = re.compile(r"^#?([0-9a-fA-F]{6}|[0-9a-fA-F]{3})$")
NAMED_RGB = {"red": (255, 0, 0), "green": (0, 255, 0), "blue": (0, 0, 255), "white": (255, 255, 255), "black": (0, 0, 0), "yellow": (255, 255, 0), "cyan": (0, 255, 255), "magenta": (255, 0, 255),
             "orange": (255, 128, 0), "pink": (255, 105, 180), "purple": (128, 0, 255), "amber": (255, 191, 0), "lime": (128, 255, 0), "teal": (0, 128, 128), "violet": (138, 43, 226),
             "lightblue": (135, 206, 250), "warm": (255, 180, 107), "cool": (201, 226, 255),
             "rot": (255, 0, 0), "gruen": (0, 255, 0), "grün": (0, 255, 0), "blau": (0, 0, 255), "weiss": (255, 255, 255), "weiß": (255, 255, 255), "schwarz": (0, 0, 0), "gelb": (255, 255, 0),
             "rosa": (255, 105, 180), "lila": (128, 0, 255)}
VARIABLE_TYPES = ("dimmer", "position", "color", "focus", "zoom", "gobo")
TRIGGERS = ("go", "follow", "timecode", "audio", "midi", "clock")


# ------------------------------------------------------------------------------------------------------------------ Aufruf der REST-Funktionen
def _sys():
    from app import api_v1_system
    return api_v1_system


def _man():
    from app import api_v1_manage
    return api_v1_manage


def _text_of(exc: Exception) -> str:
    """Eine lesbare Meldung zu einer Ausnahme der API (ApiError, Pruefung der Angaben ...)."""
    message = getattr(exc, "message", None)
    if message:
        return str(message)
    errors = getattr(exc, "errors", None)
    if callable(errors):
        try:
            first = errors()[0]
            where = ".".join(str(p) for p in first.get("loc", ()))
            return f"{where}: {first.get('msg', 'invalid value')}"
        except Exception:
            pass
    return str(exc) or exc.__class__.__name__


async def call(coro) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """(Antwort, Fehlertext) einer Funktion der API."""
    try:
        return await coro, None
    except Exception as exc:
        return None, _text_of(exc)


def _failed(error: str) -> Dict[str, Any]:
    return {"ok": False, "error": error}


def _clean(args: Dict[str, Any], *keys: str) -> Dict[str, Any]:
    """Nur die Angaben, die die KI wirklich gemacht hat (leer / None = nicht angegeben)."""
    return {k: args[k] for k in keys if args.get(k) not in (None, "")}


def _colour(value: Any) -> Tuple[Optional[Dict[str, int]], Optional[str]]:
    text = " ".join(str(value or "").split()).strip('"\'').lower()
    if text in NAMED_RGB:
        r, g, b = NAMED_RGB[text]
        return {"r": r, "g": g, "b": b}, None
    found = HEX.match(text)
    if found:
        digits = found.group(1)
        digits = "".join(c * 2 for c in digits) if len(digits) == 3 else digits
        return {"r": int(digits[0:2], 16), "g": int(digits[2:4], 16), "b": int(digits[4:6], 16)}, None
    parts = re.split(r"[,; ]+", text)
    if len(parts) == 3 and all(p.isdigit() and int(p) <= 255 for p in parts):
        return {"r": int(parts[0]), "g": int(parts[1]), "b": int(parts[2])}, None
    return None, f"Unknown colour '{value}'. Use a name ({', '.join(sorted(k for k in NAMED_RGB if k.isascii()))}), a hex colour such as #FF8000 or three numbers 0-255."


# ------------------------------------------------------------------------------------------------------------------ Patch
async def _list_fixture_types(args: Dict[str, Any], ctx: ToolContext) -> Any:
    data, error = await call(_sys().list_fixture_types(str(args.get("search", args.get("q", args.get("name", "")))) or None))
    if error:
        return _failed(error)
    rows = data["fixture_types"]
    shown = [{"name": t["name"], "manufacturer": t["manufacturer"], "id": t["id"], "modes": [f"{m['name']} ({m['channel_count']} ch)" for m in t["modes"][:6]]} for t in rows[:12]]
    result: Dict[str, Any] = {"ok": True, "total": len(rows), "fixture_types": shown}
    if len(rows) > len(shown):
        result["note"] = f"Only the first {len(shown)} of {len(rows)} are shown. Give a longer search text."
    if not rows:
        result["note"] = "Nothing matches. Try a part of the name or the manufacturer (the installed library is listed without a search)."
    return result


async def _add_fixtures(args: Dict[str, Any], ctx: ToolContext) -> Any:
    kind = str(args.get("type", args.get("fixture_type", "")) or "").strip()
    if not kind:
        return _failed("Say which fixture type. list_fixture_types shows what is installed.")
    values: Dict[str, Any] = {"type": kind}
    for key, label, low, high in (("quantity", "quantity", 1, 512), ("universe", "universe", 1, 63999), ("address", "address", 1, 512)):
        if args.get(key) not in (None, ""):
            number, error = _number(args[key], label, low, high)
            if error:
                return _failed(error)
            values[key] = int(number)
    for key in ("name", "mode", "group"):
        if args.get(key) not in (None, ""):
            values[key] = str(args[key]).strip()
    try:
        body = _sys().FixtureCreateBody(**values)
    except Exception as exc:
        return _failed(_text_of(exc))
    data, error = await call(_sys().post_fixtures(body))
    if error:
        return _failed(error)
    created = data["created"]
    return {"ok": True, "created": len(created), "fixtures": fid_text([int(f["fid"]) for f in created if f.get("fid")]), "names": [f["name"] for f in created[:8]],
            "dmx": f"universe {created[0]['universe']}, addresses {created[0]['start_channel']}-{created[-1]['end_channel']}" if created else "", "model": created[0]["type"] if created else ""}


async def _change_fixture(args: Dict[str, Any], ctx: ToolContext) -> Any:
    notes: List[str] = []
    fixtures, error = resolve(args.get("fixture", args.get("fixtures")), _state(), notes)
    if error:
        return _failed(error)
    if len(fixtures) != 1:
        return _failed("Name exactly ONE fixture (its number).")
    values: Dict[str, Any] = {}
    for key, low, high in (("universe", 1, 63999), ("address", 1, 512)):
        if args.get(key) not in (None, ""):
            number, error = _number(args[key], key, low, high)
            if error:
                return _failed(error)
            values[key] = int(number)
    if args.get("name") not in (None, ""):
        values["name"] = str(args["name"]).strip()
    if args.get("group") is not None:
        values["group"] = str(args["group"]).strip()
    if not values:
        return _failed("Nothing to change. Give a new name, address, universe or group.")
    try:
        body = _sys().FixtureUpdateBody(**values)
    except Exception as exc:
        return _failed(_text_of(exc))
    data, error = await call(_sys().put_fixture(fixtures[0].id, body))
    if error:
        return _failed(error)
    return {"ok": True, "fixture": data["fid"], "name": data["name"], "universe": data["universe"], "dmx_address": f"{data['start_channel']}-{data['end_channel']}", "group": data["group"]}


async def _delete_fixtures(args: Dict[str, Any], ctx: ToolContext) -> Any:
    notes: List[str] = []
    fixtures, error = resolve(next((args[k] for k in ("fixtures", "fixture", "ids") if args.get(k) not in (None, "")), None), _state(), notes)
    if error:
        return _failed(error)
    data, error = await call(_sys().post_fixtures_delete(_sys().FixturesDeleteBody(fixtures=[f.id for f in fixtures])))
    if error:
        return _failed(error)
    out = {"ok": True, "deleted": len(data["deleted"]), "fixtures": fid_text([int(d["fid"]) for d in data["deleted"] if d.get("fid")])}
    return {**out, "note": " ".join(notes)} if notes else out


async def _change_group(args: Dict[str, Any], ctx: ToolContext) -> Any:
    st = _state()
    name, error = find_name(args.get("group", args.get("name")), list(st.groups), "group")
    if error:
        return _failed(error)
    values: Dict[str, Any] = {}
    if args.get("new_name") not in (None, ""):
        label = " ".join(str(args["new_name"]).split())
        if not NAME_TEXT.match(label) or '"' in label:
            return _failed("Give a new name of 1-40 letters, digits or spaces.")
        values["name"] = label
    if args.get("fixtures") not in (None, ""):
        fixtures, error = resolve(args["fixtures"], st, [])
        if error:
            return _failed(error)
        values["fixtures"] = [f.id for f in fixtures]
    if not values:
        return _failed("Nothing to change. Give a new_name and / or the fixtures that belong to the group.")
    try:
        body = _sys().FixtureGroupBody(**values)
    except Exception as exc:
        return _failed(_text_of(exc))
    data, error = await call(_sys().put_group(name, body))
    if error:
        return _failed(error)
    return {"ok": True, "group": data["name"], "fixtures": fid_text([int(f) for f in data["fids"] if f]) or "none"}


# ------------------------------------------------------------------------------------------------------------------ Showfiles
def _show_state(data: Dict[str, Any]) -> Dict[str, Any]:
    return {"show": data["name"], "unsaved_changes": data["dirty"], "saved_as_file": data["saved"]}


async def _save_show(args: Dict[str, Any], ctx: ToolContext) -> Any:
    data, error = await call(_sys().post_showfile_save())
    return _failed(error + (" Use save_show_as to give it a name." if "no file" in error else "")) if error else {"ok": True, "message": "The show is saved.", **_show_state(data)}


async def _save_show_as(args: Dict[str, Any], ctx: ToolContext) -> Any:
    name = " ".join(str(args.get("name", "")).split())
    if not name:
        return _failed("Give the name for the showfile.")
    overwrite = _flag(args.get("overwrite")) is True
    data, error = await call(_sys().post_showfile_save_as(_sys().ShowfileSaveAsBody(name=name, overwrite=overwrite)))
    if error:
        return _failed(error + (" Ask the user whether to replace it; then call again with overwrite true." if "exists already" in error else ""))
    return {"ok": True, "message": f"The show is saved as '{data['name']}'.", **_show_state(data)}


async def _load_show(args: Dict[str, Any], ctx: ToolContext) -> Any:
    st = _state()
    name, error = find_name(args.get("name", args.get("showfile")), [p["name"] for p in await _list_names()], "showfile")
    if error:
        return _failed(error)
    force = _flag(args.get("discard_changes")) is True
    data, error = await call(_sys().post_showfile_load(_sys().ShowfileLoadBody(name=name, force=force)))
    if error:
        return _failed(error + (" Tell the user; only call again with discard_changes true if the user agrees to lose them." if "unsaved changes" in error else ""))
    return {"ok": True, "message": f"Loaded '{data['name']}'.", **_show_state(data), "fixtures": len(st.fixtures), "cuelists": len(st.cuelists)}


async def _list_names() -> List[Dict[str, Any]]:
    from app.ai.tools.show import _api
    data = await _api().list_showfiles()
    return [{"name": s["name"]} for s in data["showfiles"]]


async def _new_show(args: Dict[str, Any], ctx: ToolContext) -> Any:
    data, error = await call(_sys().post_showfile_new(_sys().ShowfileForceBody(force=_flag(args.get("discard_changes")) is True)))
    if error:
        return _failed(error + (" Tell the user; only call again with discard_changes true if the user agrees to lose them." if "unsaved changes" in error else ""))
    return {"ok": True, "message": "A new, empty show is open.", **_show_state(data)}


async def _delete_showfile(args: Dict[str, Any], ctx: ToolContext) -> Any:
    name, error = find_name(args.get("name", args.get("showfile")), [p["name"] for p in await _list_names()], "showfile")
    if error:
        return _failed(error)
    data, error = await call(_sys().delete_showfile(name, _flag(args.get("force")) is True))
    return _failed(error) if error else {"ok": True, "deleted_showfile": name}


async def _rename_showfile(args: Dict[str, Any], ctx: ToolContext) -> Any:
    name, error = find_name(args.get("name", args.get("showfile")), [p["name"] for p in await _list_names()], "showfile")
    if error:
        return _failed(error)
    new_name = " ".join(str(args.get("new_name", "")).split())
    if not new_name:
        return _failed("Give the new_name.")
    data, error = await call(_sys().post_showfile_rename(name, _sys().ShowfileRenameBody(new_name=new_name, overwrite=_flag(args.get("overwrite")) is True)))
    return _failed(error) if error else {"ok": True, "renamed": {"from": name, "to": new_name}}


# ------------------------------------------------------------------------------------------------------------------ Variablen
def _variable_values(kind: str, args: Dict[str, Any], need: bool) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Die Werte einer Variable aus den einfachen Angaben der KI (color / level / pan / tilt) - je nach Art."""
    if kind == "color":
        if args.get("color") in (None, ""):
            return None, "A colour variable needs 'color' (a name, #hex or three numbers 0-255)." if need else None
        rgb, error = _colour(args["color"])
        return rgb, error
    if kind == "position":
        out: Dict[str, Any] = {}
        for key in ("pan", "tilt"):
            if args.get(key) not in (None, ""):
                number, error = _number(args[key], key, 0, 100)
                if error:
                    return None, error
                out[key] = number
        if need and not out:
            return None, "A position variable needs 'pan' and / or 'tilt' (0-100 percent of the range)."
        return (out or None), None
    if args.get("level") in (None, ""):
        return None, f"A {kind} variable needs 'level' (0-100 percent)." if need else None
    number, error = _number(args["level"], "level", 0, 100)
    return ({"level": number} if not error else None), error


async def _create_variable(args: Dict[str, Any], ctx: ToolContext) -> Any:
    kind = str(args.get("type", "")).strip().lower()
    if kind not in VARIABLE_TYPES:
        return _failed(f"'type' must be one of: {', '.join(VARIABLE_TYPES)}.")
    values, error = _variable_values(kind, args, True)
    if error:
        return _failed(error)
    fields: Dict[str, Any] = {"type": kind, "values": values, **_clean(args, "name", "group")}
    try:
        body = _man().VariableBody(**fields)
    except Exception as exc:
        return _failed(_text_of(exc))
    data, error = await call(_man().post_variable(body))
    return _failed(error) if error else {"ok": True, "variable": data["name"], "type": data["type"], "values": data["values"], "group": data["group"] or None}


async def _change_variable(args: Dict[str, Any], ctx: ToolContext) -> Any:
    st = _state()
    name, error = find_name(args.get("variable", args.get("name")), [p.name for p in st.presets.values()], "variable")
    if error:
        return _failed(error)
    preset = next(p for p in st.presets.values() if p.name == name)
    values, error = _variable_values(preset.type, args, False)
    if error:
        return _failed(error)
    fields: Dict[str, Any] = {}
    if args.get("new_name") not in (None, ""):
        fields["name"] = str(args["new_name"]).strip()
    if args.get("group") is not None:
        fields["group"] = str(args["group"]).strip()
    if values:
        fields["values"] = values
    if not fields:
        return _failed(f"Nothing to change. Give new_name, group or the new value ({'color' if preset.type == 'color' else 'pan / tilt' if preset.type == 'position' else 'level'}).")
    try:
        body = _man().VariableBody(**fields)
    except Exception as exc:
        return _failed(_text_of(exc))
    data, error = await call(_man().put_variable(preset.id, body))
    return _failed(error) if error else {"ok": True, "variable": data["name"], "type": data["type"], "values": data["values"], "note": "Everything that uses the variable follows the new value."}


async def _delete_variable(args: Dict[str, Any], ctx: ToolContext) -> Any:
    st = _state()
    name, error = find_name(args.get("variable", args.get("name")), [p.name for p in st.presets.values()], "variable")
    if error:
        return _failed(error)
    data, error = await call(_man().delete_variable(next(p.id for p in st.presets.values() if p.name == name)))
    return _failed(error) if error else {"ok": True, "deleted_variable": name}


# ------------------------------------------------------------------------------------------------------------------ Effekte
async def _list_effect_types(args: Dict[str, Any], ctx: ToolContext) -> Any:
    data, error = await call(_man().list_effect_scripts())
    if error:
        return _failed(error)
    wanted = str(args.get("search", "")).strip().lower()
    rows = []
    for s in data["scripts"]:
        if not s.get("ok", True):
            continue
        text = f"{s.get('name', '')} {s.get('category', '')} {' '.join(s.get('tags', []) or [])}".lower()
        if wanted and wanted not in text:
            continue
        settings = [f"{v.get('name')} ({v.get('minimum', 0):g}-{v.get('maximum', 100):g})" if isinstance(v.get("minimum", 0), (int, float)) else str(v.get("name")) for v in (s.get("variables") or [])[:8]]
        rows.append({"type": s.get("name"), "controls": s.get("category"), "settings": settings})
    result: Dict[str, Any] = {"ok": True, "total": len(rows), "effect_types": rows[:LIST_LIMIT]}
    if len(rows) > LIST_LIMIT:
        result["note"] = f"Only the first {LIST_LIMIT} are shown. Use search."
    return result


def _effect_names() -> List[str]:
    return [str(fx.get("name") or key) for key, fx in _state().fx_effects.items()]


def _effect_id(name: str) -> str:
    return next(key for key, fx in _state().fx_effects.items() if str(fx.get("name") or key) == name)


async def _create_effect(args: Dict[str, Any], ctx: ToolContext) -> Any:
    kind = str(args.get("type", args.get("script", ""))).strip()
    if not kind:
        return _failed("Say the effect type. list_effect_types shows them.")
    settings = args.get("settings") or {}
    if not isinstance(settings, dict):
        return _failed("'settings' must be an object: {\"speed\": 50}.")
    fields: Dict[str, Any] = {"script": kind, "params": settings, **_clean(args, "name", "group")}
    try:
        body = _man().EffectBody(**fields)
    except Exception as exc:
        return _failed(_text_of(exc))
    data, error = await call(_man().post_effect(body))
    return _failed(error + " (list_effect_types shows the types and their settings)") if error else {"ok": True, "effect": data["name"], "type": data["script"], "controls": data["category"], "settings": data["params"]}


async def _change_effect(args: Dict[str, Any], ctx: ToolContext) -> Any:
    name, error = find_name(args.get("effect"), _effect_names(), "effect")
    if error:
        return _failed(error)
    settings = args.get("settings") or {}
    if not isinstance(settings, dict):
        return _failed("'settings' must be an object: {\"speed\": 50}.")
    fields: Dict[str, Any] = {}
    if settings:
        fields["params"] = settings
    if args.get("new_name") not in (None, ""):
        fields["name"] = str(args["new_name"]).strip()
    if args.get("group") is not None:
        fields["group"] = str(args["group"]).strip()
    if not fields:
        return _failed("Nothing to change. Give settings, new_name or group.")
    try:
        body = _man().EffectBody(**fields)
    except Exception as exc:
        return _failed(_text_of(exc))
    data, error = await call(_man().put_effect(_effect_id(name), body))
    return _failed(error) if error else {"ok": True, "effect": data["name"], "settings": data["params"]}


async def _delete_effect(args: Dict[str, Any], ctx: ToolContext) -> Any:
    name, error = find_name(args.get("effect"), _effect_names(), "effect")
    if error:
        return _failed(error)
    data, error = await call(_man().delete_effect_definition(_effect_id(name)))
    return _failed(error) if error else {"ok": True, "deleted_effect": name, "note": "It stopped everywhere."}


# ------------------------------------------------------------------------------------------------------------------ Cue-Eigenschaften, Cue-Listen
def _cue_ref(cl, value: Any) -> Tuple[Optional[Any], Optional[str]]:
    number, error = _number(value, "cue", 0, 99999)
    if error:
        return None, error
    cue = next((c for c in cl.cues if abs(c.number - number) < 1e-9), None)
    if cue is None:
        return None, f"The cue list '{cl.name}' has no cue {number:g}. It has: {', '.join(f'{c.number:g}' for c in sorted(cl.cues, key=lambda c: c.number)[:LIST_LIMIT]) or '(no cues)'}."
    return cue, None


def _cue_summary(data: Dict[str, Any]) -> Dict[str, Any]:
    c = data["cue"]
    return {"cuelist": data["cuelist"]["name"], "cue": c["number"], "name": c["name"], "trigger": c["trigger"], "fade_s": c["fade"], "delay_s": c["delay"], "timecode": c.get("timecode"), "command": c.get("command") or None}


async def _set_cue(args: Dict[str, Any], ctx: ToolContext) -> Any:
    cl, error = _cuelist(args.get("cuelist", args.get("list")))
    if error:
        return _failed(error)
    cue, error = _cue_ref(cl, args.get("cue"))
    if error:
        return _failed(error)
    values: Dict[str, Any] = {}
    for key in ("fade", "delay"):
        if args.get(key) not in (None, ""):
            number, error = _number(args[key], key, 0, 100000)
            if error:
                return _failed(error)
            values[key] = number
    if args.get("name") not in (None, ""):
        label = " ".join(str(args["name"]).split())
        if not NAME_TEXT.match(label) or '"' in label:
            return _failed("Give a cue name of 1-40 letters, digits or spaces.")
        values["name"] = label
    if args.get("trigger") not in (None, ""):
        trigger = str(args["trigger"]).strip().lower()
        if trigger not in TRIGGERS:
            return _failed(f"trigger must be one of: {', '.join(TRIGGERS)}.")
        values["trigger"] = trigger
        if trigger == "timecode":
            if args.get("timecode") in (None, ""):
                return _failed("A timecode trigger needs 'timecode' (seconds such as 90 or a time such as 1:30).")
            values["timecode"] = str(args["timecode"]).strip()
        if trigger == "audio":
            values["audio"] = {"source": str(args.get("audio_source", "beat")).strip().lower(), **({"value": args["audio_value"]} if args.get("audio_value") not in (None, "") else {})}
        if trigger == "midi":
            values["midi"] = {"type": str(args.get("midi_type", "note")).strip().lower(),
                              **{key: args[arg] for key, arg in (("number", "midi_number"), ("channel", "midi_channel"), ("value", "midi_value")) if args.get(arg) not in (None, "")}}
        if trigger == "clock":
            if args.get("clock_time") in (None, ""):
                return _failed("A clock trigger needs 'clock_time' (a time of day such as 19:30).")
            values["clock"] = {"time": str(args["clock_time"]).strip(), **({"days": args["clock_days"]} if args.get("clock_days") not in (None, "") else {})}
    elif args.get("timecode") not in (None, ""):
        values["timecode"] = str(args["timecode"]).strip()
    if args.get("command") is not None:
        values["command"] = str(args["command"]).strip()
    if args.get("mib") not in (None, ""):
        values["mib"] = str(args["mib"]).strip().capitalize()
    if args.get("new_number") not in (None, ""):
        number, error = _number(args["new_number"], "new_number", 0, 99999)
        if error:
            return _failed(error)
        values["number"] = number
    if not values:
        return _failed("Nothing to change. Give name, fade, delay, trigger, timecode, command, mib or new_number.")
    try:
        body = _man().CueUpdateBody(**values)
    except Exception as exc:
        return _failed(_text_of(exc))
    data, error = await call(_man().put_cue(cl.id, cue.id, body))
    return _failed(error) if error else {"ok": True, "status": data["status"], **_cue_summary(data)}


async def _duplicate_cue(args: Dict[str, Any], ctx: ToolContext) -> Any:
    cl, error = _cuelist(args.get("cuelist", args.get("list")))
    if error:
        return _failed(error)
    cue, error = _cue_ref(cl, args.get("cue"))
    if error:
        return _failed(error)
    values: Dict[str, Any] = {}
    if args.get("new_number") not in (None, ""):
        number, error = _number(args["new_number"], "new_number", 0, 99999)
        if error:
            return _failed(error)
        values["number"] = number
    if args.get("name") not in (None, ""):
        values["name"] = " ".join(str(args["name"]).split())
    data, error = await call(_man().post_cue_duplicate(cl.id, cue.id, _man().CueDuplicateBody(**values)))
    return _failed(error) if error else {"ok": True, **_cue_summary(data)}


async def _update_cue(args: Dict[str, Any], ctx: ToolContext) -> Any:
    cl, error = _cuelist(args.get("cuelist", args.get("list")))
    if error:
        return _failed(error)
    mode = "only" if _flag(args.get("only_this_cue")) is True else "normal"
    data, error = await call(_man().post_update_active(cl.id, _man().UpdateActiveBody(mode=mode)))
    return _failed(error) if error else {"ok": True, "updated": True, **_cue_summary(data)}


async def _create_cuelist(args: Dict[str, Any], ctx: ToolContext) -> Any:
    name = " ".join(str(args.get("name", "")).split())
    data, error = await call(_man().post_cuelist(_man().CuelistCreateBody(name=name)))
    return _failed(error) if error else {"ok": True, "cuelist": data["name"], "note": "The list is empty - store cues with store_cue."}


async def _rename_cuelist(args: Dict[str, Any], ctx: ToolContext) -> Any:
    cl, error = _cuelist(args.get("cuelist", args.get("list")))
    if error:
        return _failed(error)
    new_name = " ".join(str(args.get("new_name", args.get("name_new", ""))).split())
    if not new_name:
        return _failed("Give the new_name.")
    data, error = await call(_man().put_cuelist(cl.id, _man().CuelistUpdateBody(name=new_name)))
    return _failed(error) if error else {"ok": True, "cuelist": data["name"], "was": cl.name}


async def _duplicate_cuelist(args: Dict[str, Any], ctx: ToolContext) -> Any:
    cl, error = _cuelist(args.get("cuelist", args.get("list")))
    if error:
        return _failed(error)
    name = " ".join(str(args.get("new_name", "")).split())
    data, error = await call(_man().post_cuelist_duplicate(cl.id, _man().CuelistDuplicateBody(name=name)))
    return _failed(error) if error else {"ok": True, "copy": data["name"], "cues": data["cue_count"]}


async def _delete_cuelist(args: Dict[str, Any], ctx: ToolContext) -> Any:
    cl, error = _cuelist(args.get("cuelist", args.get("list")))
    if error:
        return _failed(error)
    data, error = await call(_man().delete_cuelist(cl.id))
    return _failed(error) if error else {"ok": True, "deleted_cuelist": data["deleted"]["name"], "cues_removed": data["deleted"]["cue_count"]}


# ------------------------------------------------------------------------------------------------------------------ Anmeldung
SHOWFILE_NAME = {"type": "string", "description": "Name of a saved showfile (list_showfiles shows them)."}
DISCARD = {"type": "boolean", "description": "true = throw away unsaved changes of the loaded show. Only with the user's agreement; default false."}
CUELIST_NAME = {"type": "string", "description": "Name of the cue list."}

register(Collection("patch", "patch_functions",
                    "Gives you more functions for PATCHING: look up fixture types, add fixtures to the show, change a fixture's name / address / group, delete fixtures and rename a group or change its members. "
                    "Call it ONLY when the user wants to add, change or remove fixtures or groups - never for greetings, thanks or small talk.", [
    Tool("list_fixture_types", "Looks up the installed FIXTURE TYPES (library) by a part of the name or manufacturer: name, manufacturer, id and modes with their channel count. Use it for \"which Par types are there?\", \"gibt es einen Eurolite Moving Head?\", before add_fixtures when you are not sure of the type.",
         schema({"search": {"type": "string", "description": "Part of the name or manufacturer (empty = the first types of the library)."}}), _list_fixture_types),
    Tool("add_fixtures", "PATCHES new fixtures into the show: a type, how many, the universe and the first DMX address (they are placed one after the other). Use it for \"patch 4 Par at address 1\", \"füge 6 Scheinwerfer Generic Dimmer ab Adresse 10 hinzu\". "
                         "Addresses that overlap other fixtures are refused. The fixture type must exist in the library (see list_fixture_types).",
         schema({"type": {"type": "string", "description": "Fixture type: its name (e.g. \"Generic RGBW LED Par\") or id from list_fixture_types."}, "quantity": {"type": "integer", "description": "How many (default 1)."},
                 "name": {"type": "string", "description": "Name; with several fixtures a number is appended (Par 1, Par 2 ...)."}, "universe": {"type": "integer", "description": "Universe (default 1)."},
                 "address": {"type": "integer", "description": "First DMX address, 1-512 (default 1)."}, "mode": {"type": "string", "description": "Mode of the type (default: its first mode)."},
                 "group": {"type": "string", "description": "Put them into this group (created if needed)."}}, ["type"]), _add_fixtures, access="write"),
    Tool("change_fixture", "CHANGES ONE fixture: its name, DMX address, universe or group. Use it for \"rename fixture 3 to Front left\", \"setze Scheinwerfer 2 auf Adresse 50\", \"put fixture 4 into group Wash\". Give only what changes.",
         schema({"fixture": {"type": "string", "description": "The fixture number."}, "name": {"type": "string", "description": "New name."}, "address": {"type": "integer", "description": "New first DMX address."},
                 "universe": {"type": "integer", "description": "New universe."}, "group": {"type": "string", "description": "Group name (empty text = take it out of its group)."}}, ["fixture"]), _change_fixture, access="write"),
    Tool("change_group", "RENAMES a fixture group and / or sets which fixtures belong to it (the list replaces the members). Use it for \"rename the group Wash to Front\", \"die Gruppe Wash soll aus den Scheinwerfern 1 bis 4 bestehen\".",
         schema({"group": {"type": "string", "description": "Name of the group."}, "new_name": {"type": "string", "description": "New name."}, "fixtures": FIXTURES_PARAM}, ["group"]), _change_group, access="write"),
    Tool("delete_fixtures", "DELETES fixtures from the show (CRITICAL: the user is asked first; cues keep no values for them). Use it for \"delete fixture 5\", \"lösche die Scheinwerfer 3 bis 6\".",
         schema({"fixtures": FIXTURES_PARAM}, ["fixtures"]), _delete_fixtures, access="critical"),
]))

register(Collection("showfiles", "showfile_functions",
                    "Gives you more functions for SHOWFILES: save the show, save it under a name, load another show, start a new show, rename and delete saved showfiles. "
                    "Call it ONLY when the user asks for that - never for greetings, thanks or small talk.", [
    Tool("save_show", "SAVES the loaded show under its current name. Use it for \"save the show\", \"speichere die Show\". A show that was never saved needs save_show_as.", schema(), _save_show, access="write"),
    Tool("save_show_as", "SAVES the show under a NAME (a new showfile). Use it for \"save the show as Concert\", \"speichere die Show unter dem Namen Konzert\". An existing name is refused unless overwrite is true (ask the user first).",
         schema({"name": {"type": "string", "description": "Name for the showfile."}, "overwrite": {"type": "boolean", "description": "true = replace a showfile of this name. Only with the user's agreement."}}, ["name"]), _save_show_as, access="write"),
    Tool("rename_showfile", "RENAMES a saved showfile. Use it for \"rename the showfile Test to Concert\".",
         schema({"name": SHOWFILE_NAME, "new_name": {"type": "string", "description": "The new name."}}, ["name", "new_name"]), _rename_showfile, access="write"),
    Tool("load_show", "LOADS a saved show and REPLACES the running one (CRITICAL: the user is asked first). Unsaved changes are refused - tell the user, save first, or only with the user's agreement use discard_changes. Use it for \"load the show Concert\", \"lade die Show Konzert\".",
         schema({"name": SHOWFILE_NAME, "discard_changes": DISCARD}, ["name"]), _load_show, access="critical"),
    Tool("new_show", "Starts a NEW, EMPTY show and closes the running one (CRITICAL: the user is asked first). Unsaved changes are refused unless discard_changes. Use it for \"start a new show\", \"neue Show\".",
         schema({"discard_changes": DISCARD}), _new_show, access="critical"),
    Tool("delete_showfile", "DELETES a saved showfile from the computer (CRITICAL: the user is asked first). The loaded show can only be deleted with force. Use it for \"delete the showfile Test\", \"lösche die Showfile Test\".",
         schema({"name": SHOWFILE_NAME, "force": {"type": "boolean", "description": "true = also delete the file of the loaded show (it stays in memory, unsaved)."}}, ["name"]), _delete_showfile, access="critical"),
]))

register(Collection("variables", "variable_functions",
                    "Gives you more functions to CREATE, CHANGE and DELETE variables (saved colours, brightness levels, positions, zoom, focus, gobo). "
                    "Call it ONLY when the user wants to create or change a variable - never for greetings, thanks or small talk.", [
    Tool("create_variable", "CREATES a variable. Types: color (give 'color'), dimmer / zoom / focus / gobo (give 'level' 0-100), position (give 'pan' and / or 'tilt' 0-100). Use it for \"make a colour variable Sunset with orange\", \"lege eine Variable Halb mit 50 Prozent Helligkeit an\".",
         schema({"name": {"type": "string", "description": "Name of the variable (unique)."}, "type": {"type": "string", "description": "color, dimmer, position, zoom, focus or gobo."},
                 "color": {"type": "string", "description": "For color: a name (red, orange, warm ...), #hex or \"255 128 0\"."}, "level": {"type": "number", "description": "For dimmer / zoom / focus / gobo: percent 0-100."},
                 "pan": {"type": "number", "description": "For position: percent 0-100."}, "tilt": {"type": "number", "description": "For position: percent 0-100."}, "group": {"type": "string", "description": "Optional variable group."}},
                ["name", "type"]), _create_variable, access="write"),
    Tool("change_variable", "CHANGES a variable: its value, name or group. Everything that uses it follows at once. Use it for \"change the variable Sunset to red\", \"setze die Variable Halb auf 70 Prozent\".",
         schema({"variable": {"type": "string", "description": "Name of the variable."}, "color": {"type": "string", "description": "New colour (color variables)."}, "level": {"type": "number", "description": "New percent (dimmer / zoom / focus / gobo)."},
                 "pan": {"type": "number", "description": "New pan percent (position)."}, "tilt": {"type": "number", "description": "New tilt percent (position)."}, "new_name": {"type": "string", "description": "New name."},
                 "group": {"type": "string", "description": "Variable group (empty = none)."}}, ["variable"]), _change_variable, access="write"),
    Tool("delete_variable", "DELETES a variable (CRITICAL: the user is asked first; cues that used it lose it). Use it for \"delete the variable Sunset\", \"lösche die Variable Halb\".",
         schema({"variable": {"type": "string", "description": "Name of the variable."}}, ["variable"]), _delete_variable, access="critical"),
]))

register(Collection("effects", "effect_functions",
                    "Gives you more functions to CREATE, CHANGE and DELETE effects and to look up the effect types and their settings. "
                    "Call it ONLY when the user wants to create or change an effect - never for greetings, thanks or small talk.", [
    Tool("list_effect_types", "Lists the EFFECT TYPES (what an effect can be: strobe, wave, rainbow ...) with what they control and their settings with limits. Use it for \"which effect types are there?\", \"welche Effekt-Arten gibt es?\", before create_effect. Optional search text.",
         schema({"search": {"type": "string", "description": "Part of a name, category or tag."}}), _list_effect_types),
    Tool("create_effect", "CREATES an effect from an effect type with its settings (a saved effect; start it with apply_effect). Use it for \"create a strobe effect Flash with speed 80\", \"erstelle einen Effekt Welle vom Typ ...\". Look up types and setting names with list_effect_types.",
         schema({"type": {"type": "string", "description": "The effect type (from list_effect_types)."}, "name": {"type": "string", "description": "Name of the effect."},
                 "settings": {"type": "object", "description": "Settings by name, e.g. {\"speed\": 80}. Colours as \"#rrggbb\"."}, "group": {"type": "string", "description": "Optional effect group."}}, ["type"]), _create_effect, access="write"),
    Tool("change_effect", "CHANGES an effect: some of its settings, its name or group. Use it for \"make the effect Flash faster: speed 100\", \"ändere die Geschwindigkeit des Effekts Welle auf 30\".",
         schema({"effect": {"type": "string", "description": "Name of the effect."}, "settings": {"type": "object", "description": "Settings to change by name, e.g. {\"speed\": 100}."},
                 "new_name": {"type": "string", "description": "New name."}, "group": {"type": "string", "description": "Effect group (empty = none)."}}, ["effect"]), _change_effect, access="write"),
    Tool("delete_effect", "DELETES an effect (CRITICAL: the user is asked first; it stops everywhere). Use it for \"delete the effect Flash\", \"lösche den Effekt Welle\".",
         schema({"effect": {"type": "string", "description": "Name of the effect."}}, ["effect"]), _delete_effect, access="critical"),
]))

register(Collection("cue_edit", "cue_edit_functions",
                    "Gives you more functions to change the PROPERTIES of cues (name, fade, delay, trigger, timecode, command, number), to copy a cue and to update the active cue from the programmer. "
                    "Call it ONLY when the user wants to change a cue - never for greetings, thanks or small talk.", [
    Tool("set_cue", "Changes the PROPERTIES of ONE cue: name, fade time, delay, trigger (go / follow / timecode / audio / midi / clock), timecode, a command, move-in-black, or a new number. Use it for \"set the fade of cue 3 in <list> to 2 seconds\", \"Cue 2 soll automatisch folgen\", \"nenne Cue 4 Finale\". Give only what changes.",
         schema({"cuelist": CUELIST_NAME, "cue": {"type": "number", "description": "The cue number."}, "name": {"type": "string", "description": "New name."}, "fade": {"type": "number", "description": "Fade time in seconds."},
                 "delay": {"type": "number", "description": "Delay in seconds."}, "trigger": {"type": "string", "description": "go (manual), follow (after the previous cue), timecode, audio, midi or clock (a time of day)."},
                 "timecode": {"type": "string", "description": "For trigger timecode: seconds or a time such as 1:30."}, "audio_source": {"type": "string", "description": "For trigger audio: beat, kick, snare, hat ..."},
                 "midi_type": {"type": "string", "description": "For trigger midi: note, cc or pc."}, "midi_number": {"type": "number", "description": "For trigger midi: note / controller / program number 0-127."},
                 "midi_channel": {"type": "number", "description": "For trigger midi: channel 1-16 (0 or empty = any)."},
                 "clock_time": {"type": "string", "description": "For trigger clock: time of day such as 19:30."}, "clock_days": {"type": "string", "description": "For trigger clock: days such as Mon-Fri, Sat,Sun or daily (empty = every day)."},
                 "command": {"type": "string", "description": "A console command that runs when the cue fires (empty text removes it)."}, "mib": {"type": "string", "description": "Move in black: Off, Auto or On."},
                 "new_number": {"type": "number", "description": "Renumber the cue."}}, ["cuelist", "cue"]), _set_cue, access="write"),
    Tool("duplicate_cue", "COPIES a cue into the same cue list (next free number, or new_number). Use it for \"copy cue 2\", \"dupliziere Cue 3 in <list> als Cue 3.5\".",
         schema({"cuelist": CUELIST_NAME, "cue": {"type": "number", "description": "The cue to copy."}, "new_number": {"type": "number", "description": "Number of the copy."}, "name": {"type": "string", "description": "Name of the copy."}}, ["cuelist", "cue"]), _duplicate_cue, access="write"),
    Tool("update_cue", "UPDATES the ACTIVE cue of a list with the values currently in the programmer (like the Update button). Use it for \"update the cue\", \"übernimm die Werte in den aktiven Cue von <list>\". Needs an active cue (go first) and programmer values.",
         schema({"cuelist": CUELIST_NAME, "only_this_cue": {"type": "boolean", "description": "true = following cues keep their old values (default false: they follow)."}}, ["cuelist"]), _update_cue, access="write"),
]))

register(Collection("cuelist_manage", "cuelist_manage_functions",
                    "Gives you more functions to CREATE, RENAME, COPY and DELETE whole cue lists. "
                    "Call it ONLY when the user wants that - never for greetings, thanks or small talk.", [
    Tool("create_cuelist", "CREATES a new, empty cue list. Use it for \"create a cue list Act 2\", \"lege eine Cue-Liste Akt 2 an\".",
         schema({"name": {"type": "string", "description": "Name of the new list (empty = Cue List 1 ...)."}}), _create_cuelist, access="write"),
    Tool("rename_cuelist", "RENAMES a cue list. Use it for \"rename the list Show to Act 1\".",
         schema({"cuelist": CUELIST_NAME, "new_name": {"type": "string", "description": "The new name."}}, ["cuelist", "new_name"]), _rename_cuelist, access="write"),
    Tool("duplicate_cuelist", "COPIES a cue list with all its cues. Use it for \"copy the list Show\", \"dupliziere die Liste Show als Show 2\".",
         schema({"cuelist": CUELIST_NAME, "new_name": {"type": "string", "description": "Name of the copy (default: '<name> (copy)')."}}, ["cuelist"]), _duplicate_cuelist, access="write"),
    Tool("delete_cuelist", "DELETES a cue list with all its cues (CRITICAL: the user is asked first). Use it for \"delete the cue list Test\", \"lösche die Cue-Liste Test\".",
         schema({"cuelist": CUELIST_NAME}, ["cuelist"]), _delete_cuelist, access="critical"),
]))
