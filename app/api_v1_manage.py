# Copyright (C) 2026 Samuel Zenker
# SPDX-License-Identifier: GPL-3.0-or-later
"""
api_v1_manage.py
REST-API (Teil 2): die Show BEARBEITEN - Cue-Listen und Cues anlegen/aendern/loeschen, Variablen, Effekte (Definitionen, Zuweisungen, Skripte).
Die Routen haengen am Router von app/api_v1.py (gleiche Anmeldung, gleiche Fehler, gleiches OpenAPI-Schema); jede verlangt genau eine Berechtigung:
write.show (Cue-Listen, Cues), write.variables, write.effects (Definitionen, Zuweisungen), write.scripts (Effekt-Skripte als Dateien).

Alles laeuft ueber dieselben Funktionen wie die Oberflaeche (state_manager, fx_engine, Broadcasts): jede Aenderung erscheint sofort in allen offenen Fenstern
und macht die Show "ungespeichert". Eingaben werden streng geprueft (unbekannte Felder = 422, unbekannte Attribute/Namen = 400, doppelte Namen = 409).
"""
from __future__ import annotations

import asyncio
import copy
import re
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field

from app.api_v1 import ApiError, _cue_by_ref, _cue_detail, _message, _resolve_cuelist, _resolve_fixture, _route, _srv
from app.timecode import parse_timecode_ms

PCT_ATTRS = ("dimmer", "pan", "tilt", "strobe", "gobo", "gobo_spin", "gobo2", "gobo2_spin", "prism", "focus", "zoom")
COLOR_KEYS = ("r", "g", "b")
MAX_FIXTURES_PER_CALL = 1000
MAX_ENTRIES = 2000
TIME_GROUPS = {"color": ("fade_color", "delay_color"), "position": ("fade_pos", "delay_pos"), "beam": ("fade_beam", "delay_beam"), "zoom": ("fade_zoom", "delay_zoom")}


class Strict(BaseModel):
    """Basis der Anfragekoerper: unbekannte Felder werden abgelehnt (ein Tippfehler soll nicht stillschweigend ignoriert werden)."""
    model_config = ConfigDict(extra="forbid")


# ------------------------------------------------------------------------------------------------------------------ Hilfen: Eingaben pruefen
def _number(value: Any, label: str, low: float, high: float) -> float:
    if isinstance(value, bool) or value is None:
        raise ApiError(400, "bad_request", f"{label} must be a number {low:g} - {high:g}.")
    try:
        number = float(str(value).strip().rstrip("%").replace(",", ".")) if isinstance(value, str) else float(value)
    except (TypeError, ValueError):
        raise ApiError(400, "bad_request", f"{label} must be a number {low:g} - {high:g}.")
    if number != number or number < low or number > high:
        raise ApiError(400, "bad_request", f"{label} must be a number {low:g} - {high:g}.")
    return number


def _clean_color(raw: Any, label: str = "color") -> Dict[str, int]:
    """Farbe als {"r","g","b"} (0-255), "#rrggbb" / "rrggbb", [r, g, b] oder {"hex": "#rrggbb"}."""
    if isinstance(raw, dict) and "hex" in raw:
        raw = raw["hex"]
    if isinstance(raw, str):
        text = raw.strip().lstrip("#")
        if not re.fullmatch(r"[0-9a-fA-F]{6}", text):
            raise ApiError(400, "bad_request", f"{label}: expected '#rrggbb', [r, g, b] or {{\"r\":..,\"g\":..,\"b\":..}}.")
        return {"r": int(text[0:2], 16), "g": int(text[2:4], 16), "b": int(text[4:6], 16)}
    if isinstance(raw, (list, tuple)) and len(raw) == 3:
        raw = dict(zip(COLOR_KEYS, raw))
    if isinstance(raw, dict) and set(raw) <= set(COLOR_KEYS) and raw:
        return {k: int(round(_number(raw.get(k, 0), f"{label}.{k}", 0, 255))) for k in COLOR_KEYS}
    raise ApiError(400, "bad_request", f"{label}: expected '#rrggbb', [r, g, b] or {{\"r\":..,\"g\":..,\"b\":..}}.")


def _clean_values(values: Any) -> Dict[str, Any]:
    """Attribute eines Cues / des Programmers: dimmer, pan, tilt, strobe, gobo ... in Prozent (0-100), color als r/g/b (0-255), roh: ch<N> (0-255)."""
    from app.dmx_resolve import raw_offset
    if not isinstance(values, dict):
        raise ApiError(400, "bad_request", "values must be an object, e.g. {\"dimmer\": 80, \"color\": \"#ff0000\"}.")
    out: Dict[str, Any] = {}
    for key, raw in values.items():
        name = str(key).strip().lower()
        if name in ("color", "colour"):
            out["color"] = _clean_color(raw)
        elif name in PCT_ATTRS:
            out[name] = _number(raw, name, 0, 100)
        elif raw_offset(name) is not None:
            out[name] = int(round(_number(raw, name, 0, 255)))
        else:
            raise ApiError(400, "bad_request", f"Unknown attribute '{key}' (dimmer, color, pan, tilt, strobe, gobo, gobo_spin, gobo2, gobo2_spin, prism, focus, zoom, or ch<N> for a raw channel).")
    return out


def _targets(spec: Dict[str, Any], what: str = "fixtures") -> List[Any]:
    """Scheinwerfer eines Eintrags: `fixture` (eine Nummer / ein Name / eine ID), `fixtures` (Liste) und / oder `group` (Gruppenname)."""
    st = _srv().state
    refs: List[Any] = []
    if spec.get("fixture") not in (None, ""):
        refs.append(spec["fixture"])
    if isinstance(spec.get("fixtures"), (list, tuple)):
        refs.extend(spec["fixtures"])
    elif spec.get("fixtures") is not None:
        raise ApiError(400, "bad_request", "fixtures must be a list, e.g. [1, 2, \"Front\"].")
    found: List[Any] = []
    for ref in refs[:MAX_FIXTURES_PER_CALL]:
        fx = _resolve_fixture(str(ref))
        if fx not in found:
            found.append(fx)
    if spec.get("group") not in (None, ""):
        wanted = str(spec["group"]).strip().lower()
        name = next((g for g in st.groups if g.lower() == wanted), None)
        if name is None:
            raise ApiError(404, "not_found", f"No fixture group '{spec['group']}'.")
        for fid in st.groups[name]:
            fx = st.fixtures.get(fid)
            if fx is not None and fx not in found:
                found.append(fx)
    if not found:
        raise ApiError(400, "bad_request", f"Name the {what}: 'fixture', 'fixtures' (list) or 'group'.")
    return found


def _resolve_variable(ref: Any):
    st = _srv().state
    text = str(ref).strip()
    if text in st.presets:
        return st.presets[text]
    matches = [p for p in st.presets.values() if p.name.strip().lower() == text.lower()]
    if len(matches) == 1:
        return matches[0]
    raise ApiError(404, "not_found", f"No variable '{text}' (use its name or id).")


def _resolve_effect(ref: Any) -> Tuple[str, Dict[str, Any]]:
    st = _srv().state
    text = str(ref).strip()
    if text in st.fx_effects:
        return text, st.fx_effects[text]
    matches = [(key, d) for key, d in st.fx_effects.items() if str(d.get("name", "")).strip().lower() == text.lower()]
    if len(matches) == 1:
        return matches[0]
    raise ApiError(404, "not_found", f"No effect '{text}' (use its name or id).")


def _fx_category(definition: Dict[str, Any]) -> Optional[str]:
    return _srv().registry.category(definition.get("kind"))


def _position_ms(value: Any, label: str = "timecode") -> int:
    if isinstance(value, bool) or value is None or value == "":
        raise ApiError(400, "bad_request", f"{label} must be seconds or a time such as '1:04.300'.")
    if isinstance(value, (int, float)):
        ms = int(round(float(value) * 1000))
    else:
        parsed = parse_timecode_ms(value)
        ms = -1 if parsed is None else int(parsed)
    if ms < 0:
        raise ApiError(400, "bad_request", f"{label} must be seconds or a time such as '1:04.300' (at most 100 hours).")
    return ms


async def _broadcast_cues() -> None:
    await _srv()._broadcast_cuelists_changed()


async def _broadcast_fx() -> None:
    srv = _srv()
    await srv.event_bus.broadcast(srv._fx_changed_message())


async def _broadcast_presets() -> None:
    from dataclasses import asdict
    srv = _srv()
    st = srv.state
    await srv.event_bus.broadcast({"type": "presets_changed", "payload": {"presets": {pid: asdict(p) for pid, p in st.presets.items()},
                                                                           "preset_groups": list(st.preset_groups), "is_dirty": st.is_dirty}})


# ------------------------------------------------------------------------------------------------------------------ Cue-Inhalt aus der Anfrage
def _build_content(changes: Optional[List[Any]], effects: Optional[List[Any]]) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Dict[str, str]], Dict[str, Dict[str, int]]]:
    """`changes` und `effects` einer Anfrage -> (fixture_values, fx, fx_order) im Speicherformat des Cues."""
    from app.state_manager import PRESET_TYPE_ATTRS, PRESET_TYPES
    st = _srv().state
    if len(changes or []) > MAX_ENTRIES or len(effects or []) > MAX_ENTRIES:
        raise ApiError(400, "bad_request", f"At most {MAX_ENTRIES} entries in changes / effects per call.")
    fixture_values: Dict[str, Dict[str, Any]] = {}
    for index, item in enumerate(changes or []):
        label = f"changes[{index}]"
        if not isinstance(item, dict):
            raise ApiError(400, "bad_request", f"{label} must be an object: {{\"fixtures\": [1, 2], \"values\": {{\"dimmer\": 80}}, \"variables\": {{\"color\": \"Red\"}}}}.")
        extra = set(item) - {"fixture", "fixtures", "group", "values", "variables"}
        if extra:
            raise ApiError(400, "bad_request", f"{label}: unknown field '{sorted(extra)[0]}' (fixture, fixtures, group, values, variables).")
        values = _clean_values(item.get("values") or {})
        refs: Dict[str, str] = {}
        if item.get("variables"):
            if not isinstance(item["variables"], dict):
                raise ApiError(400, "bad_request", f"{label}.variables must be an object: {{\"color\": \"Red\"}} (type -> variable name).")
            for kind, ref in item["variables"].items():
                kind = str(kind).strip().lower()
                if kind not in PRESET_TYPES:
                    raise ApiError(400, "bad_request", f"{label}.variables: unknown type '{kind}' ({', '.join(PRESET_TYPES)}).")
                variable = _resolve_variable(ref)
                if variable.type != kind:
                    raise ApiError(400, "bad_request", f"{label}.variables: '{variable.name}' is a {variable.type} variable, not {kind}.")
                refs[kind] = variable.id
        for kind in refs:                                                    # eine Variable gibt ihre Attribute vor: feste Werte derselben Attribute entfallen
            for attr in PRESET_TYPE_ATTRS.get(kind, ()):
                values.pop(attr, None)
        if not values and not refs:
            raise ApiError(400, "bad_request", f"{label}: give 'values' and / or 'variables'.")
        for fx in _targets(item):
            step = fixture_values.setdefault(fx.id, {"values": {}})
            step["values"].update(copy.deepcopy(values))
            if refs:
                step.setdefault("refs", {}).update(refs)
                for kind in refs:
                    for attr in PRESET_TYPE_ATTRS.get(kind, ()):
                        step["values"].pop(attr, None)
    fx_map: Dict[str, Dict[str, str]] = {}
    fx_order: Dict[str, Dict[str, int]] = {}
    for index, item in enumerate(effects or []):
        label = f"effects[{index}]"
        if not isinstance(item, dict) or not isinstance(item.get("effects"), dict) or not item["effects"]:
            raise ApiError(400, "bad_request", f"{label} must be an object: {{\"fixtures\": [1, 2], \"effects\": {{\"dimmer\": \"Strobe\"}}}} (category -> effect name).")
        extra = set(item) - {"fixture", "fixtures", "group", "effects"}
        if extra:
            raise ApiError(400, "bad_request", f"{label}: unknown field '{sorted(extra)[0]}' (fixture, fixtures, group, effects).")
        fixtures = _targets(item)
        for category, ref in item["effects"].items():
            fx_id, definition = _resolve_effect(ref)
            if _fx_category(definition) != str(category).strip().lower():
                raise ApiError(400, "bad_request", f"{label}: effect '{definition.get('name')}' is a {_fx_category(definition)} effect, not {category}.")
            for position, fx in enumerate(fixtures):
                fx_map.setdefault(fx.id, {})[str(category).strip().lower()] = fx_id
                fx_order.setdefault(fx.id, {})[str(category).strip().lower()] = position
    return fixture_values, fx_map, fx_order


# ------------------------------------------------------------------------------------------------------------------ Cue-Eigenschaften
class CueProps(Strict):
    name: Optional[str] = Field(None, max_length=80, description="Name of the cue (empty = 'Cue <number>').")
    fade: Optional[float] = Field(None, ge=0, description="Fade time in seconds.")
    delay: Optional[float] = Field(None, ge=0, description="Delay in seconds.")
    trigger: Optional[str] = Field(None, description="go | follow | timecode | audio | midi | clock")
    timecode: Optional[Any] = Field(None, description="For trigger 'timecode': seconds or a time such as '1:04.300'.")
    audio: Optional[Dict[str, Any]] = Field(None, description="For trigger 'audio': {\"source\": \"beat\" | \"kick\" | \"snare\" | \"hat\" | \"level\" | \"bass\" | \"mid\" | \"high\" | \"b1\"..\"b8\", \"value\": n} (every n-th hit, or a threshold in %).")
    clock: Optional[Dict[str, Any]] = Field(None, description="For trigger 'clock': {\"time\": \"19:30\" (or \"19:30:15\"), \"days\": [0-6, Monday = 0] or a text such as \"Mon-Fri\" (empty = every day)}. The cue waits as the NEXT cue of a running list for this time of the wall clock.")
    midi: Optional[Dict[str, Any]] = Field(None, description="For trigger 'midi': {\"type\": \"note\" | \"cc\" | \"pc\", \"number\": 0-127, \"channel\": 0-16 (0 = any), \"value\": 1-127} - value is the threshold of a cc (fires when the controller rises to it). The cue fires when it is the NEXT cue of a running list and the signal arrives.")
    mib: Optional[str] = Field(None, description="Move in black: Off | Auto | On.")
    command: Optional[str] = Field(None, max_length=200, description="Console command(s) that run when the cue fires.")
    times: Optional[Dict[str, Any]] = Field(None, description="Own times per attribute group: {\"color\": {\"fade\": 2, \"delay\": 0}, \"position\": {...}, \"beam\": {...}, \"zoom\": {...}}; null = use the general time again.")
    effect_fade: Optional[Dict[str, Any]] = Field(None, description="Effect fade in / out in seconds: {\"in\": 1, \"out\": 2}.")
    play_mode: Optional[str] = Field(None, description="How the cue plays: 'tracking' (only the stored changes) or 'absolute' (the exact stored state of all fixtures). The state is always stored with the cue.")


def _prop_fields(body: CueProps) -> Dict[str, Any]:
    """Eigenschaften -> Felder fuer state.update_cue / save_cue (nur, was gesendet wurde; null setzt gezielt zurueck)."""
    from app.audio_vars import CUE_AUDIO_SOURCES, clean_audio_trigger
    from app.state_manager import CUE_TRIGGERS
    sent = body.model_fields_set
    fields: Dict[str, Any] = {}
    for key in ("name", "fade", "delay", "mib"):
        if key in sent and getattr(body, key) is not None:
            fields[key] = getattr(body, key)
    if "command" in sent and body.command is not None:
        fields["cmd"] = body.command
    if body.play_mode is not None:
        if body.play_mode not in ("tracking", "absolute"):
            raise ApiError(400, "bad_request", "play_mode must be 'tracking' or 'absolute'.")
        fields["play_mode"] = body.play_mode
    if body.mib is not None and body.mib not in ("Off", "Auto", "On"):
        raise ApiError(400, "bad_request", "mib must be Off, Auto or On.")
    if body.trigger is not None:
        trigger = body.trigger.strip().lower()
        if trigger not in CUE_TRIGGERS:
            raise ApiError(400, "bad_request", f"trigger must be one of: {', '.join(CUE_TRIGGERS)}.")
        fields["trigger"] = trigger
    if body.timecode is not None:
        fields["timecode_ms"] = _position_ms(body.timecode)
    if body.audio is not None:
        extra = set(body.audio) - {"source", "value"}
        source = str(body.audio.get("source", "")).strip().lower()
        if extra or source not in CUE_AUDIO_SOURCES:
            raise ApiError(400, "bad_request", f"audio must be {{\"source\": one of {', '.join(CUE_AUDIO_SOURCES)}, \"value\": n}}.")
        value = body.audio.get("value")
        if value is not None:
            value = _number(value, "audio.value", 0, 100000)
        fields["audio_source"], fields["audio_value"] = clean_audio_trigger(source, value)
    if body.midi is not None:
        from app.midi_vars import clean_midi_trigger
        extra = set(body.midi) - {"type", "number", "channel", "value"}
        if extra or str(body.midi.get("type", "")).strip().lower() not in ("note", "cc", "pc"):
            raise ApiError(400, "bad_request", "midi must be {\"type\": \"note\" | \"cc\" | \"pc\", \"number\": 0-127, \"channel\": 0-16, \"value\": 1-127}.")
        for key, low, high in (("number", 0, 127), ("channel", 0, 16), ("value", 1, 127)):
            if body.midi.get(key) is not None:
                _number(body.midi[key], f"midi.{key}", low, high)
        fields["midi_type"], fields["midi_number"], fields["midi_channel"], fields["midi_value"] = clean_midi_trigger(
            body.midi.get("type"), body.midi.get("number"), body.midi.get("channel"), body.midi.get("value"))
    if body.clock is not None:
        from app import timeofday
        extra = set(body.clock) - {"time", "days"}
        time_text = timeofday.clean_time(body.clock.get("time"))
        if extra or time_text is None:
            raise ApiError(400, "bad_request", "clock must be {\"time\": \"HH:MM\" or \"HH:MM:SS\", \"days\": [0-6] or \"Mon-Fri\"} (days optional, empty = every day).")
        fields["clock_time"], fields["clock_days"] = time_text, timeofday.clean_days(body.clock.get("days"))
    if body.times is not None:
        for group, spec in body.times.items():
            if group not in TIME_GROUPS or not isinstance(spec, dict) or set(spec) - {"fade", "delay"}:
                raise ApiError(400, "bad_request", "times must look like {\"color\": {\"fade\": 2, \"delay\": 0}} with the groups color, position, beam, zoom.")
            for part, field in zip(("fade", "delay"), TIME_GROUPS[group]):
                if part in spec:
                    fields[field] = None if spec[part] is None else _number(spec[part], f"times.{group}.{part}", 0, 100000)
    if body.effect_fade is not None:
        if set(body.effect_fade) - {"in", "out"}:
            raise ApiError(400, "bad_request", "effect_fade must look like {\"in\": 1, \"out\": 2}.")
        for part, field in (("in", "fx_fade_in"), ("out", "fx_fade_out")):
            if part in body.effect_fade:
                fields[field] = _number(body.effect_fade[part], f"effect_fade.{part}", 0, 100000)
    return fields


def _cue_result(cl, cue, status: str) -> Dict[str, Any]:
    st = _srv().state
    return {"status": status, "cuelist": {"id": cl.id, "name": cl.name}, "cue": _cue_detail(cue, st.active_cue_ids.get(cl.id) == cue.id)}


# ------------------------------------------------------------------------------------------------------------------ Cue-Listen
class CuelistCreateBody(Strict):
    name: str = Field("", max_length=80, description="Name (empty = 'Cue List 1', 'Cue List 2' ...). Names are unique.")


class CuelistUpdateBody(Strict):
    name: Optional[str] = Field(None, min_length=1, max_length=80, description="New name.")
    active: Optional[bool] = Field(None, description="true makes it the list that cue list panels show.")


class CuelistDuplicateBody(Strict):
    name: str = Field("", max_length=80, description="Name of the copy (empty = '<name> (copy)').")


class CuelistOrderBody(Strict):
    order: List[str] = Field(..., description="Names or ids of the cue lists in the new order (lists not named follow at the end).")


def _list_summary(cl) -> Dict[str, Any]:
    from app.api_v1 import _cuelist_summary
    srv = _srv()
    return _cuelist_summary(cl, srv.state.active_cuelist_id, srv.cue_engine.playback_snapshot())


@_route("/cuelists/order", "write.show", "Reorder the cue lists", method="put")
async def put_cuelist_order(body: CuelistOrderBody) -> Dict[str, Any]:
    st = _srv().state
    ids = [_resolve_cuelist(ref).id for ref in body.order]
    if st.reorder_cuelists(ids):
        await _broadcast_cues()
    return {"order": [{"id": cl.id, "name": cl.name} for cl in st.cuelists.values()]}


@_route("/cuelists", "write.show", "Create a cue list", method="post", status_code=201)
async def post_cuelist(body: CuelistCreateBody) -> Dict[str, Any]:
    st = _srv().state
    cl = st.add_cuelist(body.name)
    if cl is None:
        raise ApiError(409, "duplicate", f"A cue list named '{body.name.strip()}' exists already.")
    await _broadcast_cues()
    return _list_summary(cl)


@_route("/cuelists/{ref}", "write.show", "Rename a cue list / make it the shown list", method="put")
async def put_cuelist(ref: str, body: CuelistUpdateBody) -> Dict[str, Any]:
    st = _srv().state
    cl = _resolve_cuelist(ref)
    if body.name is not None and body.name.strip() != cl.name:
        if st.cuelist_name_taken(body.name, cl.id):
            raise ApiError(409, "duplicate", f"A cue list named '{body.name.strip()}' exists already.")
        st.rename_cuelist(cl.id, body.name)
    if body.active:
        st.set_active_cuelist(cl.id)
    await _broadcast_cues()
    return _list_summary(cl)


@_route("/cuelists/{ref}/duplicate", "write.show", "Copy a cue list with all its cues", method="post", status_code=201)
async def post_cuelist_duplicate(ref: str, body: Optional[CuelistDuplicateBody] = None) -> Dict[str, Any]:
    st = _srv().state
    cl = _resolve_cuelist(ref)
    name = body.name if body else ""
    copy_ = st.duplicate_cuelist(cl.id, name or None)
    if copy_ is None:
        raise ApiError(409, "duplicate", f"A cue list named '{name.strip()}' exists already.")
    await _broadcast_cues()
    return _list_summary(copy_)


@_route("/cuelists/{ref}", "write.show", "Delete a cue list", method="delete")
async def delete_cuelist(ref: str) -> Dict[str, Any]:
    cl = _resolve_cuelist(ref)
    await _message("delete_cuelist", {"id": cl.id})
    return {"deleted": {"id": cl.id, "name": cl.name, "cue_count": len(cl.cues)}}


# ------------------------------------------------------------------------------------------------------------------ Cues
class CueCreateBody(CueProps):
    number: Optional[Any] = Field(None, description="Cue number, decimals allowed (e.g. 2.5). Leave out: the next free number after the last cue.")
    changes: Optional[List[Dict[str, Any]]] = Field(None, description="What the cue changes: [{\"fixtures\": [1, 2] (or \"fixture\" / \"group\"), \"values\": {\"dimmer\": 80, \"color\": \"#ff0000\", \"pan\": 40}, \"variables\": {\"color\": \"Red\"}}]. Values in percent (color r/g/b 0-255, raw channel ch<N> 0-255); a variable stays a live placeholder.")
    effects: Optional[List[Dict[str, Any]]] = Field(None, description="Effects the cue starts: [{\"fixtures\": [1, 2], \"effects\": {\"dimmer\": \"Strobe 1\"}}] (category -> effect name).")
    from_programmer: bool = Field(False, description="Add the current programmer values and running effects of the console to the cue (like 'Store Cue').")
    clear_programmer: bool = Field(False, description="With from_programmer: empty the programmer afterwards (as 'Store Cue' does).")
    on_conflict: Optional[str] = Field(None, description="The number exists already: 'merge' (only the sent attributes go into the existing cue) or 'overwrite' (its content is replaced). Without it the answer is 409.")


class CueUpdateBody(CueProps):
    number: Optional[Any] = Field(None, description="New cue number.")
    changes: Optional[List[Dict[str, Any]]] = Field(None, description="Content as when creating a cue.")
    effects: Optional[List[Dict[str, Any]]] = Field(None, description="Effects as when creating a cue.")
    content: str = Field("merge", description="With changes / effects: 'merge' (the sent attributes join or replace the same attributes) or 'replace' (the content of the cue is exactly what is sent).")
    on_conflict: Optional[str] = Field(None, description="With a new number that exists already: 'merge' | 'overwrite'. Without it the answer is 409.")


class CueDeleteBody(Strict):
    cues: List[str] = Field(..., description="Numbers or ids of the cues to delete.")


class CueDuplicateBody(Strict):
    number: Optional[Any] = Field(None, description="Number of the copy (leave out: the next free number after the last cue).")
    name: Optional[str] = Field(None, max_length=80, description="Name of the copy (leave out: the same name).")


class UpdateActiveBody(Strict):
    mode: str = Field("normal", description="'normal' = only this cue changes (following cues take over the new values by tracking); 'only' = following cues keep the old values.")


def _check_conflict_mode(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    if value not in ("merge", "overwrite"):
        raise ApiError(400, "bad_request", "on_conflict must be 'merge' or 'overwrite'.")
    return value


@_route("/cuelists/{ref}/cues", "write.show", "Create a cue", method="post", status_code=201)
async def post_cue(ref: str, body: CueCreateBody) -> Dict[str, Any]:
    """Creates a cue with its content, times and trigger in one call. The content comes from `changes` / `effects` and / or the current programmer (`from_programmer`)."""
    srv = _srv()
    st, fx_engine = srv.state, srv.fx_engine
    cl = _resolve_cuelist(ref)
    mode = _check_conflict_mode(body.on_conflict)
    fields = _prop_fields(body)
    fixture_values, fx_map, fx_order = _build_content(body.changes, body.effects)
    if body.from_programmer:
        for fid, step in st.get_programmer_snapshot().items():
            if fid not in fixture_values:
                fixture_values[fid] = step
        for fid, cats in fx_engine.cue_effects().items():
            for cat, fx_id in cats.items():
                fx_map.setdefault(fid, {}).setdefault(cat, fx_id)
        for fid, cats in fx_engine.cue_effect_order().items():
            for cat, index in cats.items():
                fx_order.setdefault(fid, {}).setdefault(cat, index)
    number = body.number
    if number is not None and str(number).strip() != "" and st.parse_cue_number(number) is None:
        raise ApiError(400, "bad_request", "number must be a number >= 0 (decimals allowed).")
    store_fields = {"fade": fields.get("fade"), "delay": fields.get("delay"), "trigger": fields.get("trigger"), "timecode_ms": fields.get("timecode_ms"),
                    "audio_source": fields.get("audio_source"), "audio_value": fields.get("audio_value"),
                    "midi_type": fields.get("midi_type"), "midi_number": fields.get("midi_number"), "midi_channel": fields.get("midi_channel"), "midi_value": fields.get("midi_value"), "clock_time": fields.get("clock_time"), "clock_days": fields.get("clock_days"), "mib": fields.get("mib"), "cmd": fields.get("cmd", ""),
                    "fx_fade_in": fields.get("fx_fade_in"), "fx_fade_out": fields.get("fx_fade_out"), "play_mode": fields.get("play_mode")}   # nicht Angegebenes: Einstellungen -> Standardwerte
    for field in ("fade_color", "delay_color", "fade_pos", "delay_pos", "fade_beam", "delay_beam", "fade_zoom", "delay_zoom"):
        store_fields[field] = fields.get(field)
    status, data = st.store_cue(cl.id, fixture_values, number=number, mode=mode, fx=fx_map, fx_order=fx_order, name=fields.get("name"),
                                live=bool(body.from_programmer), **store_fields)          # aus dem Programmer: jede Aenderung gegenueber dem Cue davor; mit `changes`: genau diese Angaben
    if status == "empty":
        raise ApiError(409, "nothing_changed", "Nothing has changed compared with the cue before - change something first.")
    if status == "conflict":
        raise ApiError(409, "cue_exists", f"Cue {data.number:g} exists already in '{cl.name}'. Send on_conflict 'merge' or 'overwrite', or change it with PUT.")
    if status == "invalid":
        raise ApiError(400, "bad_request", "number must be a number >= 0 (decimals allowed).")
    if status not in ("created", "merged", "overwritten"):
        raise ApiError(400, "bad_request", "The cue could not be stored.")
    if status != "created" and fields:                         # eine vorhandene Nummer: Eigenschaften zusaetzlich setzen (store_cue ruehrt sie dort nicht an)
        st.update_cue(cl.id, data.id, **fields)
    if body.from_programmer and body.clear_programmer and fixture_values:
        affected = st.clear_programmer(list(fixture_values))
        if affected:
            await srv.event_bus.broadcast({"type": "programmer_cleared", "payload": {"fixture_ids": affected}})
            await srv.event_bus.broadcast(srv._refs_message())
    await _broadcast_cues()
    return _cue_result(cl, data, status)


@_route("/cuelists/{ref}/cues/delete", "write.show", "Delete several cues", method="post")
async def post_cues_delete(ref: str, body: CueDeleteBody) -> Dict[str, Any]:
    st = _srv().state
    cl = _resolve_cuelist(ref)
    if not body.cues or len(body.cues) > 500:
        raise ApiError(400, "bad_request", "Send 1 to 500 cues.")
    cues = [_cue_by_ref(cl, c) for c in body.cues]                       # unbekannter Cue: 404, bevor etwas geloescht wird
    removed = [{"id": cue.id, "number": cue.number, "name": cue.name} for cue in cues if st.delete_cue(cl.id, cue.id)]
    if removed:
        await _broadcast_cues()
    return {"deleted": removed}


@_route("/cuelists/{ref}/update-active", "write.show", "Take the programmer values into the active cue", method="post")
async def post_update_active(ref: str, body: Optional[UpdateActiveBody] = None) -> Dict[str, Any]:
    """Like the 'Update' button: the touched programmer values and running effects go into the cue that is active in this list."""
    srv = _srv()
    st, fx_engine = srv.state, srv.fx_engine
    cl = _resolve_cuelist(ref)
    mode = body.mode if body else "normal"
    if mode not in ("normal", "only"):
        raise ApiError(400, "bad_request", "mode must be 'normal' or 'only'.")
    status, cue = st.update_active_cue(cl.id, st.get_programmer_snapshot(), fx=fx_engine.cue_effects(), fx_order=fx_engine.cue_effect_order(), mode=mode, live=True)
    if status == "no_active_cue":
        raise ApiError(409, "no_active_cue", "This cue list has no active cue yet (run Go first).")
    if status == "empty":
        raise ApiError(409, "programmer_empty", "Nothing has changed compared with this cue - change something first.")
    if status != "updated":
        raise ApiError(400, "bad_request", "The cue could not be updated.")
    await _broadcast_cues()
    return _cue_result(cl, cue, "updated")


@_route("/cuelists/{ref}/cues/{cue}", "write.show", "Change a cue (properties and / or content)", method="put")
async def put_cue(ref: str, cue: str, body: CueUpdateBody) -> Dict[str, Any]:
    """Change what you send, leave the rest as it is. Properties: name, fade, delay, trigger, times ... Content: `changes` / `effects` (merge into the cue, or replace it with `content: "replace"`). A new `number` renumbers the cue."""
    st = _srv().state
    cl = _resolve_cuelist(ref)
    target = _cue_by_ref(cl, cue)
    mode = _check_conflict_mode(body.on_conflict)
    if body.content not in ("merge", "replace"):
        raise ApiError(400, "bad_request", "content must be 'merge' or 'replace'.")
    fields = _prop_fields(body)
    fixture_values, fx_map, fx_order = _build_content(body.changes, body.effects)
    status = "updated"
    if body.number is not None:
        number = st.parse_cue_number(body.number)
        if number is None:
            raise ApiError(400, "bad_request", "number must be a number >= 0 (decimals allowed).")
        if abs(number - target.number) >= 1e-6:
            result, data = st.renumber_cue(cl.id, target.id, number, mode)
            if result == "conflict":
                raise ApiError(409, "cue_exists", f"Cue {data.number:g} exists already in '{cl.name}'. Send on_conflict 'merge' or 'overwrite'.")
            if result not in ("ok", "merged", "overwritten"):
                raise ApiError(400, "bad_request", "The cue could not be renumbered.")
            target = data
            status = {"ok": "updated", "merged": "merged", "overwritten": "overwritten"}[result]
    if fields:
        st.update_cue(cl.id, target.id, **fields)
    if body.changes is not None or body.effects is not None:
        if body.content == "replace":
            if body.changes is not None:
                target.fixture_values = fixture_values
            if body.effects is not None:
                target.fx, target.fx_order = fx_map, fx_order
        else:
            st._merge_content(target, fixture_values, fx_map, fx_order)
        st.mark_dirty()
    await _broadcast_cues()
    return _cue_result(cl, target, status)


@_route("/cuelists/{ref}/cues/{cue}", "write.show", "Delete a cue", method="delete")
async def delete_cue(ref: str, cue: str) -> Dict[str, Any]:
    st = _srv().state
    cl = _resolve_cuelist(ref)
    target = _cue_by_ref(cl, cue)
    st.delete_cue(cl.id, target.id)
    await _broadcast_cues()
    return {"deleted": {"id": target.id, "number": target.number, "name": target.name}}


@_route("/cuelists/{ref}/cues/{cue}/duplicate", "write.show", "Copy a cue", method="post", status_code=201)
async def post_cue_duplicate(ref: str, cue: str, body: Optional[CueDuplicateBody] = None) -> Dict[str, Any]:
    st = _srv().state
    cl = _resolve_cuelist(ref)
    source = _cue_by_ref(cl, cue)
    wanted = body.number if body else None
    if wanted is None or str(wanted).strip() == "":
        number = round(max((c.number for c in cl.cues), default=0.0) + 1.0, 3)
    else:
        number = st.parse_cue_number(wanted)
        if number is None:
            raise ApiError(400, "bad_request", "number must be a number >= 0 (decimals allowed).")
        if st.find_cue_by_number(cl, number) is not None:
            raise ApiError(409, "cue_exists", f"Cue {number:g} exists already in '{cl.name}'.")
    import uuid
    copy_ = copy.deepcopy(source)
    copy_.id = str(uuid.uuid4())
    copy_.number = number
    if body and body.name is not None and body.name.strip():
        copy_.name = body.name.strip()[:80]
    cl.cues.append(copy_)
    cl.cues.sort(key=lambda c: c.number)
    st.mark_dirty()
    await _broadcast_cues()
    return _cue_result(cl, copy_, "created")


# ------------------------------------------------------------------------------------------------------------------ Variablen
class VariableBody(Strict):
    name: Optional[str] = Field(None, max_length=80, description="Name (unique in the whole show; empty = '<Type>_1' ...).")
    type: Optional[str] = Field(None, description="dimmer | position | color | focus | zoom | gobo (cannot be changed afterwards).")
    group: Optional[str] = Field(None, max_length=60, description="Name of a variable group ('' = none). The group is created when needed.")
    values: Optional[Dict[str, Any]] = Field(None, description="dimmer / focus / zoom: {\"level\": 0-100}; position: {\"pan\": 0-100, \"tilt\": 0-100}; color: {\"r\": 0-255, \"g\": .., \"b\": ..} or {\"hex\": \"#ff8000\"}; gobo: {\"level\": 0-100, \"spin\": .., \"gobo2\": .., \"gobo2_spin\": ..}.")


class GroupBody(Strict):
    name: str = Field(..., min_length=1, max_length=60)


def _clean_variable_values(kind: str, raw: Any) -> Dict[str, Any]:
    if not isinstance(raw, dict):
        raise ApiError(400, "bad_request", "values must be an object (see the description of this route).")
    if kind == "color":
        return _clean_color(raw, "values")
    allowed = {"dimmer": ("level",), "focus": ("level",), "zoom": ("level",), "position": ("pan", "tilt"), "gobo": ("level", "spin", "gobo2", "gobo2_spin")}[kind]
    extra = set(raw) - set(allowed)
    if extra or not raw:
        raise ApiError(400, "bad_request", f"values of a {kind} variable: {', '.join(allowed)} (each 0-100).")
    return {key: _number(value, f"values.{key}", 0, 100) for key, value in raw.items()}


def _variable_dict(p) -> Dict[str, Any]:
    return {"id": p.id, "name": p.name, "type": p.type, "group": p.group, "values": p.values}


@_route("/variables/{ref}", "read.show", "One variable")
async def get_variable(ref: str) -> Dict[str, Any]:
    p = _resolve_variable(ref)
    st = _srv().state
    users = sum(1 for cl in st.cuelists.values() for cue in cl.cues for step in cue.fixture_values.values() if p.id in st.step_refs(step).values())
    return {**_variable_dict(p), "used_in_cues": users}


@_route("/variables", "write.variables", "Create a variable", method="post", status_code=201)
async def post_variable(body: VariableBody) -> Dict[str, Any]:
    from app.state_manager import PRESET_TYPES
    st = _srv().state
    if body.type not in PRESET_TYPES:
        raise ApiError(400, "bad_request", f"type must be one of: {', '.join(PRESET_TYPES)}.")
    values = _clean_variable_values(body.type, body.values) if body.values is not None else None
    if values is None:
        raise ApiError(400, "bad_request", "values are required.")
    group = (body.group or "").strip()
    if group and group not in st.preset_groups:
        st.add_preset_group(group)
    preset = st.add_preset(name=body.name or "", preset_type=body.type, group=group, values=values)
    if preset is None:
        raise ApiError(409, "duplicate", f"A variable named '{(body.name or '').strip()}' exists already.")
    await _broadcast_presets()
    return _variable_dict(preset)


@_route("/variables/{ref}", "write.variables", "Change a variable", method="put")
async def put_variable(ref: str, body: VariableBody) -> Dict[str, Any]:
    """Changes follow immediately: everything that uses the variable (programmer fixtures, running cues, all cues that refer to it) shows the new value."""
    srv = _srv()
    st = srv.state
    p = _resolve_variable(ref)
    if body.type is not None and body.type != p.type:
        raise ApiError(400, "bad_request", "The type of a variable cannot be changed.")
    fields: Dict[str, Any] = {}
    if body.name is not None:
        if not body.name.strip():
            raise ApiError(400, "bad_request", "name must not be empty.")
        fields["name"] = body.name
    if body.group is not None:
        group = body.group.strip()
        if group and group not in st.preset_groups:
            st.add_preset_group(group)
        fields["group"] = group
    if body.values is not None:
        fields["values"] = _clean_variable_values(p.type, body.values)
    if st.update_preset(p.id, **fields) is None:
        raise ApiError(409, "duplicate", f"A variable named '{(body.name or '').strip()}' exists already.")
    await _broadcast_presets()
    if "values" in fields:
        await srv._reapply_preset(p.id)
    return _variable_dict(p)


@_route("/variables/{ref}", "write.variables", "Delete a variable", method="delete")
async def delete_variable(ref: str) -> Dict[str, Any]:
    p = _resolve_variable(ref)
    await _message("delete_preset", {"id": p.id})
    return {"deleted": _variable_dict(p)}


@_route("/variable-groups", "read.show", "List variable groups")
async def list_variable_groups() -> Dict[str, Any]:
    return {"groups": list(_srv().state.preset_groups)}


@_route("/variable-groups", "write.variables", "Create a variable group", method="post", status_code=201)
async def post_variable_group(body: GroupBody) -> Dict[str, Any]:
    st = _srv().state
    name = st.add_preset_group(body.name)
    await _broadcast_presets()
    return {"name": name, "groups": list(st.preset_groups)}


@_route("/variable-groups/{name}", "write.variables", "Delete a variable group (its variables stay, ungrouped)", method="delete")
async def delete_variable_group(name: str) -> Dict[str, Any]:
    st = _srv().state
    if not st.delete_preset_group(name):
        raise ApiError(404, "not_found", f"No variable group '{name}'.")
    await _broadcast_presets()
    return {"deleted": name, "groups": list(st.preset_groups)}


# ------------------------------------------------------------------------------------------------------------------ Effekte (Definitionen, Zuweisungen)
class EffectBody(Strict):
    script: Optional[str] = Field(None, description="The effect type = name of a script file from GET /effect-scripts (e.g. 'strobe'). Cannot be changed afterwards.")
    name: Optional[str] = Field(None, max_length=80, description="Name (unique; empty = the name of the effect type).")
    group: Optional[str] = Field(None, max_length=60, description="Effect group ('' = none; created when needed).")
    params: Optional[Dict[str, Any]] = Field(None, description="Values of the effect's settings by variable name (see 'variables' of the script): numbers within their limits, colours as '#rrggbb' or {r,g,b}.")


class AssignBody(Strict):
    fixtures: Optional[List[Any]] = Field(None, description="Fixtures (number, name or id).")
    fixture: Optional[Any] = None
    group: Optional[str] = Field(None, description="A fixture group instead of / in addition to the list.")


class ReleaseBody(AssignBody):
    categories: Optional[List[str]] = Field(None, description="Only these categories (dimmer, color, position, zoom, focus, gobo); leave out = every effect on these fixtures.")


def _clean_effect_params(kind: str, params: Dict[str, Any]) -> Dict[str, Any]:
    script = _srv().registry.get(kind)
    known = {v.name: v for v in script.ui_variables}
    out: Dict[str, Any] = {}
    for key, raw in params.items():
        var = known.get(key)
        if var is None:
            raise ApiError(400, "bad_request", f"Unknown setting '{key}' of effect type '{kind}' (settings: {', '.join(known) or 'none'}).")
        if var.kind == "ColorPicker":
            out[key] = _clean_color(raw, f"params.{key}")
        else:
            out[key] = _number(raw, f"params.{key}", float(var.minimum), float(var.maximum))
    return out


def _effect_dict(fx_id: str, definition: Dict[str, Any]) -> Dict[str, Any]:
    st = _srv().state
    running = [{"fid": st.fixtures[fid].fid, "name": st.fixtures[fid].name, "fixture_id": fid}
               for fid, cats in st.fx_assignments.items() if fid in st.fixtures for a in cats.values() if a.get("fx_id") == fx_id]
    return {"id": fx_id, "name": definition.get("name", fx_id), "group": definition.get("group", ""), "script": definition.get("kind", ""),
            "category": _fx_category(definition), "params": definition.get("params", {}), "running_on": running}


@_route("/effects/assignments", "read.show", "Which effect runs on which fixture")
async def get_effect_assignments() -> Dict[str, Any]:
    st = _srv().state
    out = []
    for fid, cats in st.fx_assignments.items():
        fx = st.fixtures.get(fid)
        if fx is None:
            continue
        for category, a in cats.items():
            definition = st.fx_effects.get(a.get("fx_id"), {})
            out.append({"fid": fx.fid, "fixture": fx.name, "fixture_id": fid, "category": category, "effect": definition.get("name"), "effect_id": a.get("fx_id"),
                        "index": a.get("index"), "count": a.get("count")})
    return {"assignments": sorted(out, key=lambda e: (e["fid"], e["category"]))}


@_route("/effects/release", "write.effects", "Stop effects on fixtures", method="post")
async def post_effects_release(body: ReleaseBody) -> Dict[str, Any]:
    """Takes the effects off the given fixtures (the values stay where they are, like 'Clear'). Without `categories` every effect on them ends."""
    from app.fx_categories import CATEGORIES
    srv = _srv()
    st = srv.state
    fixtures = _targets(body.model_dump(exclude_none=True))
    categories = [c.strip().lower() for c in body.categories] if body.categories else list(CATEGORIES)
    bad = [c for c in categories if c not in CATEGORIES]
    if bad:
        raise ApiError(400, "bad_request", f"Unknown category '{bad[0]}' ({', '.join(CATEGORIES)}).")
    ids = [fx.id for fx in fixtures]
    released: List[str] = []
    for category in categories:
        released += srv.fx_engine.assign(ids, category, None)
    if released:
        await srv._release_fixtures(released)
        st.mark_dirty()
    await _broadcast_fx()
    return {"released": len(set(released)), "fixtures": sorted({st.fixtures[i].fid for i in released if i in st.fixtures})}


@_route("/effects", "write.effects", "Create an effect", method="post", status_code=201)
async def post_effect(body: EffectBody) -> Dict[str, Any]:
    """An effect is a saved setting of an effect type (script): create it here, start it with POST /effects/{effect}/assign, store it in cues with POST /cuelists/{list}/cues."""
    srv = _srv()
    st = srv.state
    if not body.script or srv.registry.get(body.script) is None:
        raise ApiError(400, "bad_request", "script must be the name of an effect type (see GET /effect-scripts).")
    name = (body.name or "").strip()
    if name and srv.fx_engine.name_taken(name):
        raise ApiError(409, "duplicate", f"An effect named '{name}' exists already.")
    group = (body.group or "").strip()
    if group and group not in st.fx_groups:
        srv.fx_engine.add_group(group)
    data = {"kind": body.script, "name": name, "group": group, "params": _clean_effect_params(body.script, body.params or {})}
    fx_id = srv.fx_engine.save_definition(None, data)
    if fx_id is None:
        raise ApiError(400, "bad_request", "The effect could not be created.")
    st.mark_dirty()
    await _broadcast_fx()
    return _effect_dict(fx_id, st.fx_effects[fx_id])


@_route("/effects/{ref}", "read.show", "One effect")
async def get_effect(ref: str) -> Dict[str, Any]:
    srv = _srv()
    fx_id, definition = _resolve_effect(ref)
    script = next((s for s in srv.registry.describe() if s.get("name") == definition.get("kind")), {})
    st = srv.state
    used = sum(1 for cl in st.cuelists.values() for cue in cl.cues for cats in (cue.fx or {}).values() if fx_id in cats.values())
    return {**_effect_dict(fx_id, definition), "used_in_cues": used, "script_info": {"label": script.get("label"), "description": script.get("descriptions"), "variables": script.get("variables")}}


@_route("/effects/{ref}", "write.effects", "Change an effect", method="put")
async def put_effect(ref: str, body: EffectBody) -> Dict[str, Any]:
    srv = _srv()
    st = srv.state
    fx_id, definition = _resolve_effect(ref)
    if body.script is not None and body.script != definition.get("kind"):
        raise ApiError(400, "bad_request", "The effect type of an effect cannot be changed - create a new effect.")
    data: Dict[str, Any] = {}
    if body.name is not None:
        name = body.name.strip()
        if not name:
            raise ApiError(400, "bad_request", "name must not be empty.")
        if srv.fx_engine.name_taken(name, fx_id):
            raise ApiError(409, "duplicate", f"An effect named '{name}' exists already.")
        data["name"] = name
    if body.group is not None:
        group = body.group.strip()
        if group and group not in st.fx_groups:
            srv.fx_engine.add_group(group)
        data["group"] = group
    if body.params is not None:
        data["params"] = {**definition.get("params", {}), **_clean_effect_params(definition["kind"], body.params)}
    if srv.fx_engine.save_definition(fx_id, data) is None:
        raise ApiError(400, "bad_request", "The effect could not be changed.")
    st.mark_dirty()
    await _broadcast_fx()
    return _effect_dict(fx_id, st.fx_effects[fx_id])


@_route("/effects/{ref}", "write.effects", "Delete an effect (it stops everywhere)", method="delete")
async def delete_effect_definition(ref: str) -> Dict[str, Any]:
    fx_id, definition = _resolve_effect(ref)
    await _message("delete_fx", {"id": fx_id})
    return {"deleted": {"id": fx_id, "name": definition.get("name")}}


@_route("/effects/{ref}/assign", "write.effects", "Start an effect on fixtures", method="post")
async def post_effect_assign(ref: str, body: AssignBody) -> Dict[str, Any]:
    """Starts the effect on the fixtures (the order of the list decides how waves are spread). It replaces an effect of the same category on them."""
    srv = _srv()
    st = srv.state
    fx_id, definition = _resolve_effect(ref)
    category = _fx_category(definition)
    fixtures = _targets(body.model_dump(exclude_none=True))
    await _message("fx_assign", {"fixture_ids": [fx.id for fx in fixtures], "category": category, "fx_id": fx_id})
    return {"effect": {"id": fx_id, "name": definition.get("name"), "category": category}, "fixtures": [fx.fid for fx in fixtures],
            "running": sum(1 for fx in fixtures if st.fx_assignments.get(fx.id, {}).get(category, {}).get("fx_id") == fx_id)}


@_route("/effect-groups", "read.show", "List effect groups")
async def list_effect_groups() -> Dict[str, Any]:
    return {"groups": list(_srv().state.fx_groups)}


@_route("/effect-groups", "write.effects", "Create an effect group", method="post", status_code=201)
async def post_effect_group(body: GroupBody) -> Dict[str, Any]:
    await _message("add_fx_group", {"name": body.name})
    return {"groups": list(_srv().state.fx_groups)}


@_route("/effect-groups/{name}", "write.effects", "Delete an effect group", method="delete")
async def delete_effect_group(name: str) -> Dict[str, Any]:
    st = _srv().state
    if name not in st.fx_groups:
        raise ApiError(404, "not_found", f"No effect group '{name}'.")
    await _message("delete_fx_group", {"name": name})
    return {"deleted": name, "groups": list(st.fx_groups)}


# ------------------------------------------------------------------------------------------------------------------ Effekt-Skripte (Dateien)
class ScriptBody(Strict):
    text: str = Field(..., max_length=200_000, description="The script (see the Effect Studio guide).")
    overwrite: bool = Field(False, description="Replace a script of this name that exists already.")


class ScriptCheckBody(Strict):
    text: str = Field(..., max_length=200_000)
    name: str = Field("check", max_length=80)


class ScriptPreviewBody(Strict):
    text: str = Field(..., max_length=200_000)
    name: str = Field("preview", max_length=80)
    params: Optional[Dict[str, Any]] = Field(None, description="Settings of the script by variable name (default: the script's own defaults).")
    count: int = Field(3, ge=1, le=24, description="Number of fixtures (for waves).")
    duration: float = Field(4.0, gt=0, le=30, description="Seconds to simulate.")
    bpm: float = Field(120.0, ge=30, le=300, description="Tempo for audio scripts (the preview uses a sample beat).")


def _script_files() -> List[Dict[str, Any]]:
    srv = _srv()
    srv.registry.load(srv._effect_sources())
    described = {s.get("name"): s for s in srv.registry.describe()}
    out = []
    for f in srv.registry.files():
        info = described.get(f["name"], {})
        out.append({"name": f["name"], "label": f.get("label", f["name"]), "origin": f["origin"], "category": f["category"], "description": info.get("descriptions") or f.get("description", ""),
                    "tags": info.get("tags", []), "audio": bool(info.get("audio")), "ok": f["ok"], "line": f["line"], "message": f["message"],
                    "variables": info.get("variables", []), "default": bool(f.get("default")), "modified_default": bool(f.get("default_modified"))})
    return sorted(out, key=lambda e: e["name"].lower())


@_route("/effect-scripts", "read.show", "List effect types (script files)")
async def list_effect_scripts() -> Dict[str, Any]:
    """Every effect type with its category, tags, description and settings (name, kind, limits, default, labels)."""
    return {"scripts": _script_files()}


@_route("/effect-scripts/check", "write.scripts", "Check a script without saving it", method="post")
async def post_script_check(body: ScriptCheckBody) -> Dict[str, Any]:
    """Compiles the script and runs it three times as a test. Returns {ok, line, message}."""
    srv = _srv()
    name = srv._script_file_name(body.name) or "check"
    return await asyncio.to_thread(srv._compile_result, name, body.text, True)


@_route("/effect-scripts/preview", "write.scripts", "Simulate a script (curves) without fixtures", method="post")
async def post_script_preview(body: ScriptPreviewBody) -> Dict[str, Any]:
    from app.fx_script import FxScriptError, FxScriptRuntimeError, preview_script
    srv = _srv()
    name = srv._script_file_name(body.name) or "preview"
    try:
        result = await asyncio.to_thread(preview_script, name, body.text, body.params, body.count, body.duration, body.bpm)
    except FxScriptError as exc:
        raise ApiError(422, "invalid_script", f"Line {exc.line}: {exc.message}" if exc.line else exc.message)
    except (FxScriptRuntimeError, ValueError, TypeError) as exc:
        raise ApiError(422, "invalid_script", str(exc))
    return {"ok": True, **result}


@_route("/effect-scripts/{name}", "read.show", "Source text of an effect type")
async def get_effect_script(name: str) -> Dict[str, Any]:
    from pathlib import Path
    srv = _srv()
    clean = srv._script_file_name(name)
    srv.registry.load(srv._effect_sources())
    known = next((f for f in srv.registry.files() if f["name"] == clean), None)
    if known is None:
        raise ApiError(404, "not_found", f"No effect type '{name}'.")
    info = next(f for f in _script_files() if f["name"] == clean)
    return {**info, "text": Path(known["path"]).read_text(encoding="utf-8")}


@_route("/effect-scripts/{name}", "write.scripts", "Save an effect type (script file)", method="put")
async def put_effect_script(name: str, body: ScriptBody) -> Dict[str, Any]:
    """Saves the script as a file in the user's effect folder - only if it compiles and runs. A script of the same name is replaced only with `overwrite: true`."""
    from app import paths as _paths
    srv = _srv()
    st = srv.state
    clean = srv._script_file_name(name)
    if not clean:
        raise ApiError(400, "bad_request", "That is not a usable file name.")
    check = await asyncio.to_thread(srv._compile_result, clean, body.text, True)
    if not check["ok"]:
        raise ApiError(422, "invalid_script", (f"Line {check['line']}: " if check.get("line") else "") + str(check["message"]))
    target = _paths.effects_dir() / f"{clean}.fx"
    if target.exists() and not body.overwrite:
        raise ApiError(409, "exists", f"The effect type '{clean}' exists already - send overwrite: true to replace it.")
    try:
        _paths.effects_dir().mkdir(parents=True, exist_ok=True)
        from app import show_safety
        show_safety._atomic_write(target, body.text)
    except OSError as exc:
        raise ApiError(500, "write_failed", f"The file could not be written: {exc}")
    srv.registry.load(srv._effect_sources())
    if any(d.get("kind") == clean for d in st.fx_effects.values()):
        st.is_dirty = True
    await srv.event_bus.broadcast(srv._fx_script_list_message())
    await _broadcast_fx()
    return {"saved": True, "name": clean, "active": srv.fx_engine.count_active(clean), **next(f for f in _script_files() if f["name"] == clean)}


@_route("/effect-scripts/{name}", "write.scripts", "Delete an effect type (script file)", method="delete")
async def delete_effect_script(name: str) -> Dict[str, Any]:
    """Only scripts in the user's folder; effects that use it stop, their definitions stay."""
    import json
    srv = _srv()
    response = await srv.delete_effect(name)
    payload = json.loads(response.body.decode("utf-8"))
    if response.status_code == 404:
        raise ApiError(404, "not_found", f"No effect type '{name}'.")
    if response.status_code >= 400:
        raise ApiError(response.status_code, "rejected", str(payload.get("error", "Not possible.")))
    return {"deleted": srv._script_file_name(name), "released": payload.get("released", 0)}
