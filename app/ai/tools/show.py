# Copyright (C) 2026 Samuel Zenker
# SPDX-License-Identifier: GPL-3.0-or-later
"""Sammlungen "read" und "library": die Show LESEN. Die Funktionen rufen direkt dieselben Python-Funktionen auf wie die REST-API (`app/api_v1.py`) - ohne HTTP und ohne Token.
Ergebnisse bleiben klein (kleiner Kontext des Modells): Listen sind begrenzt und sagen, wie viele es insgesamt gibt. Es wird nichts veraendert."""
from __future__ import annotations

from typing import Any, Dict, List

from app.ai.tools.base import Collection, Tool, ToolContext, register, schema
from app.ai.tools.selection import resolve

LIST_LIMIT = 30
MAX_PARAMS_SHOWN = 8
READ_LIMIT = 12                 # so viele Scheinwerfer zeigt read_fixtures auf einmal
READ_CHANNELS_UP_TO = 6         # bis zu so vielen Scheinwerfern steht jeder Kanal mit seinem DMX-Wert dabei (sonst wird die Antwort fuer kleine Modelle zu lang)


def _api():
    from app import api_v1                     # erst beim Aufruf: api_v1 holt sich den Server selbst
    return api_v1


def _state():
    return _api()._srv().state


def fail(exc: Exception) -> Dict[str, Any]:
    return {"ok": False, "error": str(getattr(exc, "message", None) or exc)}


def _short(value: Any, limit: int = 80) -> str:
    text = " ".join(str(value if value is not None else "").split())
    return text if len(text) <= limit else text[:limit - 3] + "..."


def _output_note(st) -> Dict[str, Any]:
    """Master und Blackout bestimmen, was die Scheinwerfer wirklich ausgeben (angezeigt wird der programmierte Wert)."""
    info: Dict[str, Any] = {"grand_master_percent": st.grand_master, "blackout": bool(st.blackout)}
    notes = []
    if st.blackout:
        notes.append("Blackout is ON: all lights are dark whatever their value.")
    if st.grand_master < 99.5:
        notes.append(f"The grand master is at {st.grand_master:g} %: the lights output only that share of the programmed brightness.")
    if notes:
        info["note"] = " ".join(notes) + " Tell the user this."
    return info


async def _show_overview(args: Dict[str, Any], ctx: ToolContext) -> Any:
    try:
        data = await _api().status()
    except Exception as exc:
        return fail(exc)
    return {"ok": True, "show": data["show"]["name"], "unsaved_changes": data["show"]["unsaved_changes"], "blackout": data["blackout"], "grand_master_percent": data["grand_master"],
            "counts": data["counts"], "active_cuelist": (data["active_cuelist"] or {}).get("name"), "selected_fixtures": data["selection"]["fids"][:LIST_LIMIT],
            "timecode_running": bool((data.get("timecode") or {}).get("running"))}


async def _list_fixtures(args: Dict[str, Any], ctx: ToolContext) -> Any:
    group = str(args.get("group") or "").strip() or None
    needle = str(args.get("name_contains") or args.get("name") or "").strip().lower()
    try:
        data = await _api().list_fixtures(group=group, include_state=True)
    except Exception as exc:
        return fail(exc)
    rows = [f for f in data["fixtures"] if not needle or needle in str(f["name"]).lower() or needle in str(f["type"]).lower()]
    shown = []
    for f in rows[:LIST_LIMIT]:
        item = {"fid": f["fid"], "name": f["name"], "type": f["type"], "universe": f["universe"], "address": f["start_channel"], "group": f["group"]}
        dim = (f.get("state") or {}).get("dimmer")
        item["brightness_percent"] = round(dim, 1) if isinstance(dim, (int, float)) else None           # None = der Scheinwerfer hat keinen Dimmer-Kanal
        shown.append(item)
    result = {"ok": True, "total": len(rows), "fixtures": shown, **_output_note(_state())}
    if len(rows) > LIST_LIMIT:
        result["note"] = f"Only the first {LIST_LIMIT} are shown. Use group or name_contains to narrow it down."
    return result


async def _list_groups(args: Dict[str, Any], ctx: ToolContext) -> Any:
    try:
        data = await _api().list_groups()
    except Exception as exc:
        return fail(exc)
    return {"ok": True, "total": len(data["groups"]), "groups": [{"name": g["name"], "fixture_numbers": g["fids"][:LIST_LIMIT], "count": len(g["fids"])} for g in data["groups"][:LIST_LIMIT]]}


async def _list_cuelists(args: Dict[str, Any], ctx: ToolContext) -> Any:
    try:
        data = await _api().list_cuelists()
    except Exception as exc:
        return fail(exc)
    st = _state()
    rows = []
    for c in data["cuelists"][:LIST_LIMIT]:
        cues = sorted(st.cuelists[c["id"]].cues, key=lambda q: q.number) if c["id"] in st.cuelists else []
        rows.append({"name": c["name"], "cues": c["cue_count"], "cue_names": [(q.name or f"{q.number:g}") for q in cues[:12]],          # die Namen gleich mit: "welche Cues hat die Liste?" ist so auch mit dieser Funktion beantwortbar
                     "active_cue": (c["active_cue"] or {}).get("name") or (c["active_cue"] or {}).get("number"), "fader_percent": c["fader"], "state": (c.get("playback") or {}).get("state")})
    return {"ok": True, "total": len(data["cuelists"]), "cuelists": rows}


def _round(value: Any) -> Any:
    """Zahlen auf eine Nachkommastelle (Werte aus dem DMX-Puffer haben viele Stellen); Verschachtelungen bleiben erhalten."""
    if isinstance(value, float):
        return round(value, 1)
    if isinstance(value, dict):
        return {k: _round(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_round(v) for v in value]
    return value


async def _read_fixtures(args: Dict[str, Any], ctx: ToolContext) -> Any:
    spec = next((args[k] for k in ("fixtures", "fixture", "fids", "fid", "ids", "group", "name") if args.get(k) not in (None, "")), None)
    st = _state()
    notes: List[str] = []
    fixtures, error = resolve(spec, st, notes)
    if error:
        return {"ok": False, "error": error}
    shown = fixtures[:READ_LIMIT]
    with_channels = len(shown) <= READ_CHANNELS_UP_TO
    rows = []
    try:
        for fx in shown:
            data = await _api().get_fixture(str(fx.id))
            row = {"fid": data["fid"], "name": data["name"], "manufacturer": data.get("manufacturer") or None, "model": data["type"], "mode": data.get("mode") or None,
                   "universe": data["universe"], "dmx_address": f"{data['start_channel']}-{data['end_channel']}", "channel_count": data["channel_count"], "group": data["group"],
                   "values": _round(data.get("state") or {})}
            if with_channels:
                row["channels_dmx_0_255"] = {c["name"]: c["value"] for c in data.get("channels", [])}
            rows.append(row)
    except Exception as exc:
        return fail(exc)
    result: Dict[str, Any] = {"ok": True, "total": len(fixtures), "fixtures": rows, **_output_note(st)}
    if len(fixtures) > len(shown):
        notes.append(f"Only the first {len(shown)} of {len(fixtures)} fixtures are shown. Ask for fewer fixtures to see the rest.")
    if not with_channels:
        notes.append(f"The channel list (channels_dmx_0_255) is only included for up to {READ_CHANNELS_UP_TO} fixtures.")
    if notes:                                                          # der Hinweis steht VORNE: kleine Modelle lesen das Ende eines Ergebnisses nicht
        result = {"ok": True, "note": " ".join(notes), **{k: v for k, v in result.items() if k != "ok"}}
    return result


async def _list_showfiles(args: Dict[str, Any], ctx: ToolContext) -> Any:
    try:
        data = await _api().list_showfiles()
    except Exception as exc:
        return fail(exc)
    rows = [s["name"] for s in data["showfiles"][:LIST_LIMIT]]
    return {"ok": True, "loaded": data["loaded"], "total": len(data["showfiles"]), "showfiles": rows}


async def _list_variables(args: Dict[str, Any], ctx: ToolContext) -> Any:
    try:
        data = await _api().list_variables()
    except Exception as exc:
        return fail(exc)
    rows = [{"name": v["name"], "type": v["type"], "group": v.get("group") or None, "value": _short(v.get("values"))} for v in data["variables"][:LIST_LIMIT]]
    return {"ok": True, "total": len(data["variables"]), "variables": rows}


async def _list_effects(args: Dict[str, Any], ctx: ToolContext) -> Any:
    try:
        from app import api_v1_manage
        st = _state()
        rows = []
        for fx_id, definition in list(st.fx_effects.items())[:LIST_LIMIT]:
            item = api_v1_manage._effect_dict(fx_id, definition)
            running = [r["fid"] for r in item["running_on"]]
            rows.append({"name": item["name"], "type": item["script"], "controls": item["category"], "group": item["group"] or None,
                         "settings": dict(list((item.get("params") or {}).items())[:MAX_PARAMS_SHOWN]), "running": bool(running),
                         "status": ("running on fixtures " + ", ".join(str(f) for f in running)) if running else "NOT running (saved only)"})
        active = [r["name"] for r in rows if r["running"]]
        return {"ok": True, "summary": ("Running right now: " + ", ".join(active) + ".") if active else "NO effect is running right now (the effects listed are only saved).",
                "total": len(st.fx_effects), "effects": rows}
    except Exception as exc:
        return fail(exc)


def _whole(value: Any, name: str, low: int, high: int, default: int):
    if value in (None, ""):
        return default, None
    try:
        number = int(float(str(value).replace(",", ".")))
    except ValueError:
        return None, f"'{name}' must be a whole number from {low} to {high}, not '{value}'."
    return (number, None) if low <= number <= high else (None, f"'{name}' must be between {low} and {high}, not {number}.")


async def _read_dmx(args: Dict[str, Any], ctx: ToolContext) -> Any:
    universe, e0 = _whole(args.get("universe"), "universe", 1, 63999, 1)
    first, e1 = _whole(args.get("first"), "first", 1, 512, 1)
    last, e2 = _whole(args.get("last"), "last", 1, 512, 512)
    if e0 or e1 or e2 or first > last:
        return {"ok": False, "error": e0 or e1 or e2 or "first must not be greater than last."}
    try:
        data = await _api().get_universe(universe, first, last, True)
    except Exception as exc:
        return fail(exc)
    channels = data["channels"]
    shown = dict(list(channels.items())[:60])
    result: Dict[str, Any] = {"ok": True, "universe": universe, "first": first, "last": last, "channels_not_zero": len(channels), "values_0_255": shown, **_output_note(_state())}
    if len(channels) > len(shown):
        result["note"] = f"Only the first {len(shown)} of {len(channels)} channels are listed. Ask for a smaller range."
    if not channels:
        result["note"] = "All channels in this range are 0."
    return result


register(Collection("read", "read_functions",
                    "Gives you more functions for LOOKING AT the current OpenCue show: overview, fixtures and all their values, groups, cue lists. "
                    "Call it ONLY when the user asks about the current show (e.g. how many fixtures there are) - never for greetings, thanks, small talk or general questions.", [
    Tool("show_overview", "Overview of the loaded show: name, blackout, grand master and only the COUNTS of fixtures / groups / cue lists / cues / effects / variables, and the active cue list. "
         "Use it for \"give me an overview\", \"wie ist der Stand der Show?\", \"wie heißt die Show?\", \"how many cue lists / effects are there?\". It does not list names - use list_fixtures, list_groups, list_cuelists, list_effects or list_variables for those.",
         schema(), _show_overview),
    Tool("list_fixtures", "Lists the fixtures (lights) of the show: number, name, type, DMX address, group and the current brightness in percent. Use it for \"which fixtures are there?\", \"welche Scheinwerfer gibt es?\", \"how many fixtures?\", \"what is on?\". "
                          "Optional filters: group name, or a part of the name / type.",
         schema({"group": {"type": "string", "description": "Only fixtures of this group."}, "name_contains": {"type": "string", "description": "Only fixtures whose name or type contains this text."}}), _list_fixtures),
    Tool("read_fixtures", "Reads the DETAILS of fixtures: model, manufacturer, mode, DMX address, group and ALL current values (brightness in percent, colour, pan / tilt, zoom ... and every channel as DMX value). "
                          "Use it for \"how bright is fixture 3?\", \"wie hell ist Scheinwerfer 3?\", \"which model is fixture 2?\", \"welche Farbe haben die Scheinwerfer 1 bis 5?\", \"show me everything about fixture 4\". "
                          "Give the fixtures: \"all\", a range like \"1-5\", or numbers like \"1, 3, 7\". It only reads - to change values use set_fixtures.",
         schema({"fixtures": {"type": "string", "description": "Which fixtures: \"all\", a range like \"1-5\", numbers like \"1, 3, 7\" (or \"1-3, 7\"), or the name of a group."}}, ["fixtures"]), _read_fixtures),
    Tool("list_groups", "Lists the fixture groups with the numbers of their fixtures. Use it for \"which groups are there?\", \"welche Gruppen gibt es?\".", schema(), _list_groups),
    Tool("read_dmx", "Reads the DMX OUTPUT values (0-255) of a universe: only the channels that are not zero. Use it for \"what is the DMX output?\", \"welche DMX-Kanäle sind an?\", \"show channels 1 to 50 of universe 1\". Optional: universe (default 1), first and last channel.",
         schema({"universe": {"type": "integer", "description": "Universe number (default 1)."}, "first": {"type": "integer", "description": "First channel (default 1)."}, "last": {"type": "integer", "description": "Last channel (default 512)."}}), _read_dmx),
    Tool("list_cuelists", "Lists the cue lists with their number of cues, the active cue and the fader - NOT the cues themselves (use read_cuelist for the cues of one list). Use it for \"which cue lists are there?\", \"welche Cue-Listen gibt es?\", \"what is playing?\".", schema(), _list_cuelists),
]))

register(Collection("library", "library_functions",
                    "Gives you more functions for LOOKING AT the effects and the variables (saved colours, positions ...) of the show. "
                    "Call it ONLY when the user asks about effects or variables - never for greetings, thanks, small talk or general questions.", [
    Tool("list_effects", "Lists the effects of the show with their type, settings and whether they are running right now and on which fixtures. Use it for \"which effects are there?\", \"läuft ein Effekt?\", \"is an effect running?\".", schema(), _list_effects),
    Tool("list_showfiles", "Lists the saved SHOWFILES on this computer and which one is loaded. Use it for \"which shows are saved?\", \"welche Showfiles gibt es?\", \"which show is loaded?\". (Loading and saving shows is not possible yet.)", schema(), _list_showfiles),
    Tool("list_variables", "Lists the variables of the show (name, type such as colour or position, group and value). Use it for \"which variables are there?\", \"welche Variablen gibt es?\", \"which saved colours / positions?\".", schema(), _list_variables),
]))
