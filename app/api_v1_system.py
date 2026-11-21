# Copyright (C) 2026 Samuel Zenker
# SPDX-License-Identifier: GPL-3.0-or-later
"""
api_v1_system.py
REST-API (Teil 3): Programmer und Auswahl (write.programmer), Patch und Scheinwerfer-Gruppen (write.patch), Showfiles (write.showfile), Lesen von Medien und Layouts
sowie der Ereignis-Strom (Server-Sent Events, `GET /events`).

Wie in app/api_v1_manage.py: gleiche Anmeldung, gleiche Fehler, gleicher Weg wie die Oberflaeche (Aenderungen erscheinen sofort in allen Fenstern).
Showfile-Aktionen, die die laufende Show ersetzen (Neu, Laden), verlangen bei ungespeicherten Aenderungen ein ausdrueckliches `force`.
"""
from __future__ import annotations

import asyncio
import copy
import json
import re
import time
import types
from typing import Any, AsyncIterator, Dict, List, Optional, Set

from fastapi import Request
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import Field

from app import paths as _paths
from app.api_v1 import ApiError, _fixture_dict, _group_of, _message, _resolve_fixture, _route, _srv, _timecode_dict
from app.api_v1_manage import Strict, _clean_values, _resolve_variable, _targets

MAX_STREAMS = 20


class Targets(Strict):
    """Wie man Scheinwerfer nennt: `fixtures` (Liste: Nummer, Name oder id), `fixture` (einer), `group` (Gruppenname) und / oder `selection` (die aktuelle Auswahl der Konsole)."""
    fixtures: Optional[List[Any]] = Field(None, description="Fixtures by number, name or id.")
    fixture: Optional[Any] = Field(None, description="One fixture by number, name or id.")
    group: Optional[str] = Field(None, description="A fixture group by name.")
    selection: Optional[bool] = Field(None, description="true = the fixtures that are selected on the console right now.")


def _spec(body: Targets) -> Dict[str, Any]:
    return body.model_dump(exclude_none=True)


def _resolve_targets(body: Targets, default_selection: bool = True) -> List[Any]:
    """Scheinwerfer der Anfrage; ohne Angabe gilt (wie an der Konsole) die aktuelle Auswahl."""
    st = _srv().state
    spec = _spec(body)
    use_selection = bool(spec.pop("selection", False))
    named = any(key in spec for key in ("fixtures", "fixture", "group"))
    found = _targets(spec) if named else []
    if use_selection or (not named and default_selection):
        for fid in st.selected_fixture_ids:
            fx = st.fixtures.get(fid)
            if fx is not None and fx not in found:
                found.append(fx)
    if not found:
        raise ApiError(400, "bad_request", "No fixtures: name them ('fixtures', 'fixture', 'group') or select some on the console ('selection': true).")
    return found


# ------------------------------------------------------------------------------------------------------------------ Programmer und Auswahl
class SelectionBody(Targets):
    mode: str = Field("set", description="'set' (replace the selection), 'add', 'remove' or 'clear'.")


class ProgrammerValuesBody(Targets):
    values: Dict[str, Any] = Field(..., description="Attributes to set: dimmer, pan, tilt, strobe, gobo, gobo_spin, gobo2, gobo2_spin, prism, focus, zoom in percent (0-100), color as '#rrggbb' / [r, g, b] / {r,g,b}, raw channels as ch<N> (0-255). With mode 'relative' the numbers are CHANGES in percent points (e.g. {\"pan\": 2.5} = 2.5 % further right).")
    mode: str = Field("absolute", description="'absolute' (default: the values are the new values) or 'relative' (the values are added to each fixture's current value, limited to 0-100; colors and raw channels cannot be relative).")


class ProgrammerVariableBody(Targets):
    variable: str = Field(..., description="Name or id of the variable to apply (it stays linked: when the variable changes, the fixtures follow).")


class ProgrammerClearBody(Targets):
    all: bool = Field(False, description="true = 'Clear Clear': EVERY fixture goes back to its baseline (dark), all effects end, the selection is emptied. Without it only the programmer values of the named fixtures are forgotten (their output stays as it is).")


def current_value(fx, attr: str) -> float:
    """Aktueller Wert (Prozent) eines Attributs: der Programmer-Wert, sonst der Stand im DMX-Puffer (die Wahrheit), sonst die Mitte (Pan / Tilt) bzw. 0."""
    from app.dmx_resolve import abstract_from_dmx
    st = _srv().state
    value = (st.programmer_values.get(fx.id) or {}).get(attr)
    if isinstance(value, (int, float)):
        return float(value)
    live = abstract_from_dmx(fx, _srv().dmx_engine.get_universe_snapshot(fx.universe), st.effective_master(fx.id)).get(attr)
    if isinstance(live, (int, float)):
        return float(live)
    return 50.0 if attr in ("pan", "tilt") else 0.0


def relative_values(fx, deltas: Dict[str, Any]) -> Dict[str, Any]:
    """Aus Aenderungen (Prozentpunkte) die neuen Werte dieses Scheinwerfers machen; 0-100 begrenzt."""
    out: Dict[str, Any] = {}
    for attr, delta in deltas.items():
        if not isinstance(delta, (int, float)) or attr == "color" or attr.startswith("ch"):
            raise ApiError(400, "bad_request", f"'{attr}' cannot be relative: use numbers for dimmer, pan, tilt, strobe, gobo, prism, focus, zoom (colors and raw channels need absolute values).")
        out[attr] = round(max(0.0, min(100.0, current_value(fx, attr) + float(delta))), 4)
    return out


def _clean_deltas(values: Any) -> Dict[str, Any]:
    """Aenderungen fuer mode 'relative': Zahlen (Prozentpunkte, -100 bis 100) je Attribut."""
    from app.api_v1_manage import PCT_ATTRS
    if not isinstance(values, dict):
        raise ApiError(400, "bad_request", "values must be an object, e.g. {\"pan\": 2.5}.")
    out: Dict[str, Any] = {}
    for key, raw in values.items():
        name = str(key).strip().lower()
        if name not in PCT_ATTRS:
            raise ApiError(400, "bad_request", f"'{key}' cannot be relative (relative: {', '.join(PCT_ATTRS)}).")
        if isinstance(raw, bool) or not isinstance(raw, (int, float)) or not -100 <= raw <= 100:
            raise ApiError(400, "bad_request", f"{name}: a number between -100 and 100 (percent points).")
        out[name] = float(raw)
    return out


def _programmer_state() -> Dict[str, Any]:
    st = _srv().state
    fixtures = []
    for fid, values in st.programmer_values.items():
        fx = st.fixtures.get(fid)
        if fx is None or not values:
            continue
        refs = {kind: (st.presets[pid].name if pid in st.presets else None) for kind, pid in st.programmer_refs.get(fid, {}).items()}
        shown = {k: ({**v, "hex": "#%02x%02x%02x" % (int(v.get("r", 0)), int(v.get("g", 0)), int(v.get("b", 0)))} if k == "color" and isinstance(v, dict) else v) for k, v in values.items()}
        fixtures.append({"fixture_id": fid, "fid": fx.fid, "name": fx.name, "values": shown, "variables": refs})
    effects = [{"fid": st.fixtures[fid].fid, "name": st.fixtures[fid].name, "effects": {cat: (st.fx_effects.get(a.get("fx_id")) or {}).get("name") for cat, a in cats.items()}}
               for fid, cats in st.fx_assignments.items() if fid in st.fixtures and cats]
    return {"selection": [{"fid": st.fixtures[i].fid, "name": st.fixtures[i].name, "id": i} for i in st.selected_fixture_ids if i in st.fixtures],
            "fixtures": sorted(fixtures, key=lambda f: f["fid"]), "effects": sorted(effects, key=lambda e: e["fid"])}


@_route("/programmer", "read.status", "The programmer: selection, touched values, linked variables, running effects")
async def get_programmer() -> Dict[str, Any]:
    """What was set by hand since the last store / clear: per fixture the attributes (percent, color r/g/b + hex, raw channels `ch<N>`) and the variables they follow."""
    return _programmer_state()


@_route("/selection", "write.programmer", "Change the selection of the console", method="put")
async def put_selection(body: SelectionBody) -> Dict[str, Any]:
    srv = _srv()
    st = srv.state
    if body.mode not in ("set", "add", "remove", "clear"):
        raise ApiError(400, "bad_request", "mode must be set, add, remove or clear.")
    if body.mode == "clear":
        ids: List[str] = []
    else:
        chosen = [fx.id for fx in _resolve_targets(body, default_selection=False)]
        current = list(st.selected_fixture_ids)
        ids = chosen if body.mode == "set" else (current + [i for i in chosen if i not in current] if body.mode == "add" else [i for i in current if i not in chosen])
    ids = st.set_selection(ids)
    await srv.event_bus.broadcast({"type": "selection_changed", "payload": {"selected_ids": ids}})
    return {"fixtures": [{"fid": st.fixtures[i].fid, "name": st.fixtures[i].name} for i in ids if i in st.fixtures]}


@_route("/programmer/values", "write.programmer", "Set values in the programmer (live output)", method="put")
async def put_programmer_values(body: ProgrammerValuesBody) -> Dict[str, Any]:
    """Like moving the faders of the programmer: the output changes at once, the values count as touched (a cue stores them, 'Clear' forgets them) and they replace a variable or effect that controlled the same attribute."""
    from app.dmx_resolve import apply_abstract_values, fixture_channel_offsets
    srv = _srv()
    st = srv.state
    abstract = _clean_values(body.values) if body.mode != "relative" else {k: v for k, v in _clean_deltas(body.values).items()}
    if not abstract:
        raise ApiError(400, "bad_request", "values must name at least one attribute.")
    if body.mode not in ("absolute", "relative"):
        raise ApiError(400, "bad_request", "mode must be absolute or relative.")
    fixtures = _resolve_targets(body)
    batches: Dict[int, Dict[int, int]] = {}
    universes: Set[int] = set()
    changed: Dict[str, Any] = {}
    applied: List[int] = []
    skipped: List[int] = []
    await srv.release_effects_for_manual({fx.id: list(abstract) for fx in fixtures}, srv._broadcast_generic)       # der Wert gewinnt: Effekte auf diesen Attributen enden
    for fx in fixtures:
        st.release_layers(fx.id, list(abstract))
        mine = abstract if body.mode != "relative" else relative_values(fx, abstract)          # relativ: jeder Scheinwerfer von SEINEM Wert aus
        resolved = apply_abstract_values(fx, copy.deepcopy(mine), fixture_channel_offsets(fx), batches, pct_values=True, grand_master=st.effective_master(fx.id))
        if resolved:
            st.set_fixture_values(fx.id, resolved)
            st.set_programmer_values(fx.id, copy.deepcopy(mine))
            universes.add(fx.universe)
            changed[fx.id] = copy.deepcopy(mine)
            applied.append(fx.fid)
        else:
            skipped.append(fx.fid)
    for universe, channels in batches.items():
        srv.dmx_engine.commit_batch(universe, channels)
    for universe in universes:
        await srv.event_bus.broadcast({"type": "dmx_universe_changed", "payload": {"universe": universe, "values": srv.dmx_engine.get_universe_snapshot(universe)}})
    if changed:
        await srv.event_bus.broadcast({"type": "fixtures_changed", "payload": {"fixtures": st.fixtures_as_dicts(), "is_dirty": st.is_dirty}})
        await srv.event_bus.broadcast({"type": "programmer_command_update", "payload": {"values": changed}})
        await srv.event_bus.broadcast(srv._refs_message())
    return {"applied": applied, "skipped": skipped, "note": "skipped = fixtures that have none of these attributes" if skipped else None}


@_route("/programmer/variables", "write.programmer", "Apply a variable to fixtures", method="post")
async def post_programmer_variable(body: ProgrammerVariableBody) -> Dict[str, Any]:
    srv = _srv()
    variable = _resolve_variable(body.variable)
    fixtures = _resolve_targets(body)
    await srv._apply_preset_to_fixtures([fx.id for fx in fixtures], variable)
    return {"variable": {"id": variable.id, "name": variable.name, "type": variable.type}, "fixtures": [fx.fid for fx in fixtures]}


@_route("/programmer/clear", "write.programmer", "Clear the programmer", method="post")
async def post_programmer_clear(body: Optional[ProgrammerClearBody] = None) -> Dict[str, Any]:
    from app.command_line import apply_full_baseline_reset
    srv = _srv()
    st = srv.state
    body = body or ProgrammerClearBody()
    if body.all:
        result = await apply_full_baseline_reset(srv._broadcast_generic)
        return {"all": True, "message": result.get("message")}
    fixtures = _resolve_targets(body)
    affected = st.clear_programmer([fx.id for fx in fixtures])
    if affected:
        await srv.event_bus.broadcast({"type": "programmer_cleared", "payload": {"fixture_ids": affected}})
        await srv.event_bus.broadcast(srv._refs_message())
    return {"all": False, "cleared": [st.fixtures[i].fid for i in affected if i in st.fixtures]}


# ------------------------------------------------------------------------------------------------------------------ Patch
class FixtureCreateBody(Strict):
    type: str = Field(..., description="Fixture type: id or name from GET /fixture-types (e.g. 'Generic RGBW LED Par').")
    mode: Optional[str] = Field(None, description="Mode name of the type (leave out: the first mode).")
    name: Optional[str] = Field(None, max_length=60, description="Name; with quantity > 1 a number is appended ('Par 1', 'Par 2' ...). Default: the name of the type.")
    quantity: int = Field(1, ge=1, le=512, description="How many fixtures; they are patched one after the other.")
    universe: int = Field(1, ge=1, le=63999)
    address: int = Field(1, ge=1, le=512, description="First DMX address (1-512) of the first fixture.")
    name_start_index: int = Field(1, ge=1, description="First number appended to the name.")
    group: Optional[str] = Field(None, description="Put the new fixtures into this fixture group (created when needed).")
    allow_overlap: bool = Field(False, description="Allow addresses that overlap other fixtures (default: 409 address_conflict).")


class FixtureUpdateBody(Strict):
    name: Optional[str] = Field(None, min_length=1, max_length=60)
    universe: Optional[int] = Field(None, ge=1, le=63999)
    address: Optional[int] = Field(None, ge=1, le=512, description="New first DMX address.")
    sort_index: Optional[float] = Field(None, description="Free sort value for the fixture list (null = not set).")
    group: Optional[str] = Field(None, description="Fixture group ('' = remove from its group; the group is created when needed).")
    allow_overlap: bool = False


class FixturesDeleteBody(Strict):
    fixtures: List[Any] = Field(..., description="Fixtures by number, name or id.")


class FixtureGroupBody(Strict):
    name: Optional[str] = Field(None, min_length=1, max_length=40, description="Name of the group.")
    fixtures: Optional[List[Any]] = Field(None, description="The members of the group (replaces the list; a fixture belongs to at most one group).")


def _find_type(ref: str) -> Dict[str, Any]:
    from app.fixture_manager import get_fixture_types
    types_ = get_fixture_types()
    text = ref.strip().lower()
    exact = [t for t in types_ if t["id"] == ref or str(t.get("name", "")).strip().lower() == text]
    if len(exact) == 1:
        return exact[0]
    both = [t for t in types_ if f"{t.get('manufacturer', '')} {t.get('name', '')}".strip().lower() == text]
    if len(both) == 1:
        return both[0]
    if len(exact) > 1:
        raise ApiError(400, "ambiguous", f"'{ref}' fits {len(exact)} fixture types - use the id from GET /fixture-types.")
    raise ApiError(404, "not_found", f"No fixture type '{ref}' (GET /fixture-types lists them).")


def _overlap(universe: int, start: int, count: int, ignore: Optional[Set[str]] = None) -> Optional[Any]:
    for fx in _srv().state.fixtures.values():
        if fx.universe != universe or (ignore and fx.id in ignore):
            continue
        if start <= fx.start_channel + max(1, fx.channel_count) - 1 and fx.start_channel <= start + count - 1:
            return fx
    return None


async def _broadcast_patch(groups: bool = False) -> None:
    srv = _srv()
    st = srv.state
    await srv.event_bus.broadcast({"type": "fixtures_changed", "payload": {"fixtures": st.fixtures_as_dicts(), "is_dirty": st.is_dirty}})
    if groups:
        await srv._broadcast_fixture_groups()


def _group_by_name(name: str) -> str:
    st = _srv().state
    found = next((g for g in st.groups if g.lower() == name.strip().lower()), None)
    if found is None:
        raise ApiError(404, "not_found", f"No fixture group '{name}'.")
    return found


@_route("/fixture-types", "read.show", "Fixture types that can be patched")
async def list_fixture_types(q: Optional[str] = None) -> Dict[str, Any]:
    """The installed fixture library. `?q=` filters by manufacturer / name. Use `id` (or the name) as `type` in POST /fixtures."""
    from app.fixture_manager import get_fixture_types
    out = []
    wanted = (q or "").strip().lower()
    for t in get_fixture_types():
        text = f"{t.get('manufacturer', '')} {t.get('name', '')} {t.get('short_name', '')}".lower()
        if wanted and wanted not in text:
            continue
        out.append({"id": t["id"], "name": t.get("name"), "manufacturer": t.get("manufacturer"), "short_name": t.get("short_name"), "source": t.get("source"),
                    "modes": [{"name": m.get("name"), "channel_count": m.get("channel_count")} for m in t.get("modes", [])]})
    return {"fixture_types": out}


@_route("/fixtures", "write.patch", "Patch fixtures", method="post", status_code=201)
async def post_fixtures(body: FixtureCreateBody) -> Dict[str, Any]:
    """Creates one or more fixtures of a type, patched one after the other from `address`. Addresses are checked (must fit into 512, no overlap unless `allow_overlap`)."""
    srv = _srv()
    st = srv.state
    ftype = _find_type(body.type)
    modes = ftype.get("modes") or []
    if body.mode:
        mode = next((m for m in modes if str(m.get("name", "")).lower() == body.mode.strip().lower()), None)
        if mode is None:
            raise ApiError(400, "bad_request", f"Unknown mode '{body.mode}' (modes: {', '.join(str(m.get('name')) for m in modes) or 'none'}).")
    else:
        mode = modes[0] if modes else {"name": "default", "channel_count": ftype.get("channel_count", 1)}
    count = int(mode.get("channel_count") or ftype.get("channel_count") or 1)
    if body.address + count * body.quantity - 1 > 512:
        raise ApiError(400, "bad_request", f"{body.quantity} x {count} channels from address {body.address} do not fit into one universe (512).")
    if not body.allow_overlap:
        for index in range(body.quantity):
            clash = _overlap(body.universe, body.address + index * count, count)
            if clash is not None:
                raise ApiError(409, "address_conflict", f"The addresses {body.address + index * count}-{body.address + (index + 1) * count - 1} in universe {body.universe} overlap '{clash.name}' (fixture {clash.fid}). Send allow_overlap: true to patch anyway.")
    group = (body.group or "").strip()
    if group and not any(g.lower() == group.lower() for g in st.groups):
        st.add_fixture_group(group)
    created = st.add_fixtures_batch(fixture_type_id=ftype["id"], fixture_type_name=ftype.get("name", ""), channel_count=count, mode=str(mode.get("name", "default")),
                                    name_prefix=(body.name or ftype.get("name") or "Fixture").strip(), quantity=body.quantity, universe=body.universe,
                                    start_channel=body.address, name_start_index=body.name_start_index)
    if group and created:
        st.assign_fixture_group([fx.id for fx in created], _group_by_name(group))
    await _broadcast_patch(groups=bool(group))
    groups = _group_of()
    return {"created": [_fixture_dict(fx, groups) for fx in created]}


@_route("/fixtures/delete", "write.patch", "Delete several fixtures", method="post")
async def post_fixtures_delete(body: FixturesDeleteBody) -> Dict[str, Any]:
    st = _srv().state
    if not body.fixtures or len(body.fixtures) > 1000:
        raise ApiError(400, "bad_request", "Send 1 to 1000 fixtures.")
    fixtures = [_resolve_fixture(str(ref)) for ref in body.fixtures]
    removed = [{"id": fx.id, "fid": fx.fid, "name": fx.name} for fx in fixtures]
    st.delete_fixtures_bulk([fx.id for fx in fixtures])
    await _broadcast_patch(groups=True)
    return {"deleted": removed}


@_route("/fixtures/{ref}", "write.patch", "Change a fixture (name, address, group)", method="put")
async def put_fixture(ref: str, body: FixtureUpdateBody) -> Dict[str, Any]:
    st = _srv().state
    fx = _resolve_fixture(ref)
    universe = body.universe if body.universe is not None else fx.universe
    address = body.address if body.address is not None else fx.start_channel
    count = max(1, fx.channel_count)
    if body.universe is not None or body.address is not None:
        if address + count - 1 > 512:
            raise ApiError(400, "bad_request", f"The fixture needs {count} channels: the last possible address is {512 - count + 1}.")
        if not body.allow_overlap:
            clash = _overlap(universe, address, count, {fx.id})
            if clash is not None:
                raise ApiError(409, "address_conflict", f"Universe {universe}, addresses {address}-{address + count - 1} overlap '{clash.name}' (fixture {clash.fid}). Send allow_overlap: true to patch anyway.")
        st.update_fixture_patch(fx.id, universe, address)
    if body.name is not None:
        st.rename_fixture(fx.id, body.name)
    if "sort_index" in body.model_fields_set:
        st.set_fixture_sort_index(fx.id, body.sort_index)
    groups_changed = False
    if body.group is not None:
        group = body.group.strip()
        if group:
            if not any(g.lower() == group.lower() for g in st.groups):
                st.add_fixture_group(group)
            st.assign_fixture_group([fx.id], _group_by_name(group))
        else:
            st.assign_fixture_group([fx.id], "")
        groups_changed = True
    await _broadcast_patch(groups=groups_changed)
    return _fixture_dict(fx)


@_route("/fixtures/{ref}", "write.patch", "Delete a fixture", method="delete")
async def delete_fixture(ref: str) -> Dict[str, Any]:
    st = _srv().state
    fx = _resolve_fixture(ref)
    info = {"id": fx.id, "fid": fx.fid, "name": fx.name}
    st.delete_fixtures_bulk([fx.id])
    await _broadcast_patch(groups=True)
    return {"deleted": info}


@_route("/groups", "write.patch", "Create a fixture group", method="post", status_code=201)
async def post_group(body: FixtureGroupBody) -> Dict[str, Any]:
    st = _srv().state
    if not body.name:
        raise ApiError(400, "bad_request", "name is required.")
    name = st.add_fixture_group(body.name)
    if name is None:
        raise ApiError(409, "duplicate", f"A fixture group named '{body.name.strip()}' exists already (or the name is empty).")
    if body.fixtures:
        st.assign_fixture_group([_resolve_fixture(str(r)).id for r in body.fixtures], name)
    await _srv()._broadcast_fixture_groups()
    return {"name": name, "fids": [st.fixtures[i].fid for i in st.groups[name] if i in st.fixtures]}


@_route("/groups/{name}", "write.patch", "Rename a fixture group / set its members", method="put")
async def put_group(name: str, body: FixtureGroupBody) -> Dict[str, Any]:
    st = _srv().state
    current = _group_by_name(name)
    if body.name is not None and body.name.strip() != current:
        if not st.rename_fixture_group(current, body.name):
            raise ApiError(409, "duplicate", f"A fixture group named '{body.name.strip()}' exists already.")
        current = st.clean_group_name(body.name)
    if body.fixtures is not None:
        wanted = [_resolve_fixture(str(r)).id for r in body.fixtures]
        leaving = [i for i in st.groups[current] if i not in wanted]
        if leaving:
            st.assign_fixture_group(leaving, "")
        if wanted:
            st.assign_fixture_group(wanted, current)
    await _srv()._broadcast_fixture_groups()
    return {"name": current, "fids": [st.fixtures[i].fid for i in st.groups[current] if i in st.fixtures]}


@_route("/groups/{name}", "write.patch", "Delete a fixture group (its fixtures stay)", method="delete")
async def delete_group(name: str) -> Dict[str, Any]:
    st = _srv().state
    current = _group_by_name(name)
    st.delete_fixture_group(current)
    await _srv()._broadcast_fixture_groups()
    return {"deleted": current}


# ------------------------------------------------------------------------------------------------------------------ Showfiles
class ShowfileForceBody(Strict):
    force: bool = Field(False, description="Replace the show that is loaded even though it has unsaved changes.")


class ShowfileLoadBody(ShowfileForceBody):
    name: str = Field(..., min_length=1, max_length=120, description="Name of the saved showfile (GET /showfiles).")


class ShowfileSaveAsBody(Strict):
    name: str = Field(..., min_length=1, max_length=60, description="Name for the showfile (letters, digits, spaces, - _ . ( ) are kept; other characters are removed).")
    overwrite: bool = Field(False, description="Replace a showfile of this name that exists already.")


class ShowfileRenameBody(Strict):
    new_name: str = Field(..., min_length=1, max_length=60)
    overwrite: bool = False


_RESERVED = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}


def _clean_show_name(name: str) -> str:
    cleaned = re.sub(r'[\\/:*?"<>|\x00-\x1f]', "", str(name)).strip().strip(".")[:60].strip()
    if not cleaned or cleaned.split(".")[0].upper() in _RESERVED:
        raise ApiError(400, "bad_request", "That is not a usable showfile name.")
    return cleaned


def _showfile_path(name: str):
    """Pfad einer gespeicherten Showfile (nur direkt im Showfile-Ordner), sonst 404."""
    folder = _paths.SHOWFILES_DIR
    wanted = str(name).strip()
    if wanted.lower().endswith(".json"):
        wanted = wanted[:-5]
    candidate = folder / f"{wanted}.json"
    try:
        if candidate.is_file() and candidate.resolve().parent == folder.resolve():
            return candidate
        for path in folder.glob("*.json"):                                 # Gross-/Kleinschreibung egal
            if path.stem.lower() == wanted.lower():
                return path
    except OSError:
        pass
    raise ApiError(404, "not_found", f"No saved showfile '{name}' (GET /showfiles lists them).")


def _need_force(force: bool, what: str) -> None:
    st = _srv().state
    if st.is_dirty and not force:
        raise ApiError(409, "unsaved_changes", f"The show '{st.showfile_name}' has unsaved changes. Save it first (POST /showfile/save), or send force: true to {what} anyway.")


def _showfile_status() -> Dict[str, Any]:
    st = _srv().state
    path = st.showfile_path
    return {"name": st.showfile_name, "path": path, "dirty": bool(st.is_dirty), "saved": bool(path and _path_exists(path))}


def _path_exists(path: str) -> bool:
    try:
        return bool(__import__("pathlib").Path(path).is_file())
    except OSError:
        return False


class _JsonRequest:
    """Kleine Huelle, damit die vorhandenen Showfile-Routen des Servers (die eine Anfrage mit JSON-Koerper erwarten) aufgerufen werden koennen."""

    def __init__(self, body: Dict[str, Any]) -> None:
        self._body = body

    async def json(self) -> Dict[str, Any]:
        return self._body


def _unwrap(response) -> Dict[str, Any]:
    payload = json.loads(response.body.decode("utf-8")) if getattr(response, "body", None) else {}
    if response.status_code >= 400:
        code = payload.get("error") or "rejected"
        raise ApiError(response.status_code, str(code), payload.get("message") or {"in_use": "This showfile is the one that is loaded.", "exists": "A showfile of that name exists already (send overwrite: true)."}.get(code, str(code)))
    return payload


@_route("/showfile", "read.status", "Name and state of the loaded show")
async def get_showfile() -> Dict[str, Any]:
    return _showfile_status()


@_route("/showfile/new", "write.showfile", "Start a new, empty show", method="post")
async def post_showfile_new(body: Optional[ShowfileForceBody] = None) -> Dict[str, Any]:
    _need_force(bool(body and body.force), "discard it")
    await _message("new_show", {})
    return _showfile_status()


@_route("/showfile/save", "write.showfile", "Save the loaded show", method="post")
async def post_showfile_save() -> Dict[str, Any]:
    """Saves the show under its current name and place. A show that has never been saved needs POST /showfile/save-as."""
    st = _srv().state
    if not st.showfile_path:
        raise ApiError(409, "never_saved", "This show has no file yet: use POST /showfile/save-as with a name.")
    await _message("save_show", {})
    return _showfile_status()


@_route("/showfile/save-as", "write.showfile", "Save the show under a name", method="post")
async def post_showfile_save_as(body: ShowfileSaveAsBody) -> Dict[str, Any]:
    st = _srv().state
    name = _clean_show_name(body.name)
    target = _paths.SHOWFILES_DIR / f"{name}.json"
    if target.exists() and not body.overwrite and str(target) != str(st.showfile_path):
        raise ApiError(409, "exists", f"A showfile named '{name}' exists already - send overwrite: true to replace it.")
    await _message("save_show_as", {"name": name})
    return _showfile_status()


@_route("/showfile/load", "write.showfile", "Load a saved show (replaces the running one)", method="post")
async def post_showfile_load(body: ShowfileLoadBody) -> Dict[str, Any]:
    _need_force(body.force, "load another show")
    path = _showfile_path(body.name)
    await _message("load_show", {"path": str(path)})
    return _showfile_status()


@_route("/showfiles/{name}/rename", "write.showfile", "Rename a saved showfile", method="post")
async def post_showfile_rename(name: str, body: ShowfileRenameBody) -> Dict[str, Any]:
    srv = _srv()
    path = _showfile_path(name)
    return _unwrap(await srv.rename_showfile(_JsonRequest({"path": str(path), "new_name": _clean_show_name(body.new_name), "overwrite": body.overwrite})))


@_route("/showfiles/{name}/duplicate", "write.showfile", "Copy a saved showfile", method="post", status_code=201)
async def post_showfile_duplicate(name: str) -> Dict[str, Any]:
    srv = _srv()
    return _unwrap(await srv.duplicate_showfile(_JsonRequest({"path": str(_showfile_path(name))})))


@_route("/showfiles/{name}", "write.showfile", "Delete a saved showfile", method="delete")
async def delete_showfile(name: str, force: bool = False) -> Dict[str, Any]:
    """The show that is loaded can only be deleted with `?force=true` (it stays in memory but counts as unsaved)."""
    srv = _srv()
    path = _showfile_path(name)
    if srv._same_path(srv.state.showfile_path, path) and not force:
        raise ApiError(409, "in_use", "This showfile is the one that is loaded. Send ?force=true to delete it anyway (the show stays in memory, unsaved).")
    return _unwrap(await srv.delete_showfile(_JsonRequest({"path": str(path)})))


# ------------------------------------------------------------------------------------------------------------------ Medien und Layouts lesen
@_route("/media", "read.show", "Media (video / audio files) of the show")
async def list_media() -> Dict[str, Any]:
    """The media the show uses: id, name, type, duration, size, and `missing` when the file is gone."""
    payload = _srv().state.media_payload()
    return {"media": [{"id": mid, "name": m.get("name"), "kind": m.get("kind"), "mime": m.get("mime"), "size": m.get("size"), "duration_ms": m.get("duration_ms"), "missing": m.get("missing")}
                      for mid, m in payload.items()]}


class MediaRenameBody(Strict):
    name: str = Field(..., min_length=1, max_length=120)


def _media_or_404(media_id: str) -> Dict[str, Any]:
    meta = _srv().state.media.get(media_id)
    if meta is None:
        raise ApiError(404, "not_found", f"No medium '{media_id}' (GET /media lists them).")
    return meta


@_route("/media/{media_id}/file", "read.show", "Download a medium")
async def get_media_file(media_id: str) -> FileResponse:
    from app import media_store
    meta = _media_or_404(media_id)
    path = media_store.file_path(meta)
    if path is None or not path.is_file():
        raise ApiError(404, "missing", "The file of this medium is missing on this computer.")
    return FileResponse(path, media_type=meta.get("mime") or "application/octet-stream", filename=meta.get("name") or None)


@_route("/media", "write.media", "Upload a video / audio file", method="post", status_code=201,
        openapi_extra={"requestBody": {"required": True, "content": {"application/octet-stream": {"schema": {"type": "string", "format": "binary"}}}}})
async def post_media(request: Request) -> Dict[str, Any]:
    """Send the raw file as the request body (`Content-Type: application/octet-stream`) and its name in the header `X-Filename` (URL-encoded); optional `X-Duration-Ms`. Up to 1 GB; MP4 / WebM / OGG / WAV / MP3 / FLAC / AAC / M4A. The same file twice is one entry."""
    return _unwrap(await _srv().media_upload(request))


@_route("/media/{media_id}", "write.media", "Rename a medium", method="put")
async def put_media(media_id: str, body: MediaRenameBody) -> Dict[str, Any]:
    _media_or_404(media_id)
    return _unwrap(await _srv().media_update(media_id, _JsonRequest({"name": body.name})))


@_route("/media/{media_id}", "write.media", "Remove a medium from the show and delete its copy", method="delete")
async def delete_media(media_id: str) -> Dict[str, Any]:
    _media_or_404(media_id)
    return _unwrap(await _srv().media_delete(media_id))


@_route("/system", "read.status", "Program, outputs and network settings")
async def get_system() -> Dict[str, Any]:
    """Version, language, the DMX outputs (Art-Net, sACN, USB-DMX) with their addresses, the default universe, remote access and the data folder."""
    from app.version import APP_NAME, APP_VERSION
    srv = _srv()
    st = srv.state
    return {"app": {"name": APP_NAME, "version": APP_VERSION}, "language": st.language, "default_universe": st.default_universe,
            "outputs": {"artnet": {"enabled": st.artnet_enabled, "ip": st.artnet_ip, "bind_ip": st.artnet_bind_ip}, "sacn": {"enabled": st.sacn_enabled},
                        "enttec": {"enabled": st.enttec_enabled, "port": st.enttec_port, "universe": st.enttec_universe}},
            "universes": sorted(set(srv.dmx_engine.universe_numbers()) | {fx.universe for fx in st.fixtures.values()}),
            "remote": {"enabled": bool(st.remote_enabled), "clients": len(srv._remote_client_infos())}, "data_folder": str(_paths.get_data_root()),
            "blackout": bool(st.blackout), "grand_master": st.grand_master}


@_route("/layouts", "read.show", "Saved layouts of the console")
async def list_layouts() -> Dict[str, Any]:
    response = await _srv().list_layouts()
    return {"layouts": json.loads(response.body.decode("utf-8"))}


# ------------------------------------------------------------------------------------------------------------------ Ereignisse (Server-Sent Events)
class EventHub:
    """Verteilt Zustandsaenderungen der Show an alle offenen Ereignis-Stroeme. Eine Hintergrundaufgabe vergleicht ~10x pro Sekunde kleine Fingerabdruecke des
    Zustands (aktive Cues, Blackout, Master, Timecode, Auswahl, Effekte, ...) und laeuft nur, solange ein Strom offen ist. Befehle kommen ueber einen Abgriff am Ereignisbus."""

    INTERVAL = 0.1
    DEFAULT = ("cue", "cuelists", "blackout", "master", "timecode", "selection", "effects", "fixtures", "variables", "show", "command", "audio")
    ALL = DEFAULT + ("beat", "hit")             # beat / hit (jeder Schlag) nur auf ausdrueckliche Anfrage: mehrere Meldungen pro Sekunde
    LIVE = ("command", "beat", "hit")           # kommen als Ereignis, nicht aus dem Zustandsvergleich

    def __init__(self) -> None:
        self.queues: Dict[int, "asyncio.Queue"] = {}
        self._task: Optional["asyncio.Task"] = None
        self._seq = 0
        self._keys = 0
        self._last: Dict[str, Any] = {}
        self._tapped = False
        self._audio_tapped = False
        self._event_loop: Optional["asyncio.AbstractEventLoop"] = None

    # ---- Fingerabdruecke
    def _signatures(self) -> Dict[str, Any]:
        srv = _srv()
        st = srv.state
        tc = srv.timecode.state()
        active = {}
        for cl in st.cuelists.values():
            cue = next((c for c in cl.cues if c.id == st.active_cue_ids.get(cl.id)), None)
            active[cl.id] = (cl.name, cue.number if cue else None, cue.name if cue else None)
        return {
            "cue": active,
            "cuelists": [(cl.id, cl.name, len(cl.cues), tuple((c.number, c.name) for c in cl.cues)) for cl in st.cuelists.values()] + [st.active_cuelist_id],
            "blackout": bool(st.blackout), "master": round(float(st.grand_master), 2),
            "timecode": (bool(tc["running"]), tc["direction"], tc["rate"]),
            "selection": tuple(st.selected_fixture_ids),
            "effects": (tuple(sorted((fid, c, a.get("fx_id")) for fid, cats in st.fx_assignments.items() for c, a in cats.items())), tuple(sorted(st.fx_effects))),
            "fixtures": tuple((fx.id, fx.name, fx.universe, fx.start_channel) for fx in st.fixtures.values()) + (tuple((g, tuple(m)) for g, m in st.groups.items()),),
            "variables": tuple((p.id, p.name, json.dumps(p.values, sort_keys=True)) for p in st.presets.values()),
            "show": (st.showfile_name, bool(st.is_dirty), st.showfile_path),
            "audio": self._audio_signature(),
        }

    @staticmethod
    def _audio_signature() -> Any:
        from app.audio_engine import audio_engine
        values = audio_engine.values() if audio_engine.running else {}
        return (audio_engine.running, audio_engine.device_name, audio_engine.error, audio_engine.config.get("mode"),
                round(float(values.get("a_bpm", 0))) if values.get("a_active") else 0, bool(values.get("a_active")))

    def _payload(self, kind: str) -> Dict[str, Any]:
        srv = _srv()
        st = srv.state
        if kind == "cue":
            return {"cuelists": [{"id": cl.id, "name": cl.name, "active_cue": ({"id": c.id, "number": c.number, "name": c.name} if (c := next((x for x in cl.cues if x.id == st.active_cue_ids.get(cl.id)), None)) else None)}
                                 for cl in st.cuelists.values()]}
        if kind == "cuelists":
            return {"cuelists": [{"id": cl.id, "name": cl.name, "cue_count": len(cl.cues)} for cl in st.cuelists.values()], "active_cuelist": st.active_cuelist_id}
        if kind == "blackout":
            return {"enabled": bool(st.blackout)}
        if kind == "master":
            return {"value": st.grand_master}
        if kind == "timecode":
            return _timecode_dict()
        if kind == "selection":
            return {"fixtures": [{"fid": st.fixtures[i].fid, "name": st.fixtures[i].name} for i in st.selected_fixture_ids if i in st.fixtures]}
        if kind == "effects":
            return {"effects": len(st.fx_effects), "running": sum(len(c) for c in st.fx_assignments.values())}
        if kind == "fixtures":
            return {"fixtures": len(st.fixtures)}
        if kind == "variables":
            return {"variables": len(st.presets)}
        if kind == "show":
            return {"name": st.showfile_name, "dirty": bool(st.is_dirty), "saved": bool(st.showfile_path)}
        if kind == "audio":
            from app.audio_engine import audio_engine
            values = audio_engine.values() if audio_engine.running else {}
            return {"running": audio_engine.running, "device": audio_engine.device_name, "error": audio_engine.error or None, "mode": audio_engine.config.get("mode"),
                    "bpm": round(float(values.get("a_bpm", 0)), 1) if values.get("a_active") else None, "signal": bool(values.get("a_active"))}
        return {}

    def snapshot_events(self) -> List[Dict[str, Any]]:
        return [{"event": kind, "data": self._payload(kind)} for kind in self.ALL if kind not in self.LIVE]

    # ---- Verteilen
    def _publish(self, event: str, data: Dict[str, Any]) -> None:
        self._seq += 1
        item = {"id": self._seq, "event": event, "data": data}
        for queue in list(self.queues.values()):
            if queue.full():                                           # ein langsamer Empfaenger verliert die aeltesten Ereignisse, bremst aber nicht die anderen
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass
            queue.put_nowait(item)

    def _audio_tap(self, name: str, strength: float) -> None:
        """Aus dem Audio-Thread: ein Schlag / Einsatz -> in die Ereignis-Schleife uebergeben."""
        loop = self._event_loop
        if loop is None or not self.queues:
            return
        if name == "beat":
            from app.audio_engine import audio_engine
            values = audio_engine.values()
            loop.call_soon_threadsafe(self._publish, "beat", {"bpm": round(float(values.get("a_bpm", 0)), 1), "count": int(values.get("a_beat_count", 0))})
        else:
            loop.call_soon_threadsafe(self._publish, "hit", {"drum": name, "strength": round(float(strength), 2)})

    def _tap(self, message: Dict[str, Any]) -> None:
        if message.get("type") == "command_log" and self.queues:
            payload = message.get("payload") or {}
            self._publish("command", {"command": payload.get("command"), "success": payload.get("success"), "message": payload.get("message"), "time": payload.get("timestamp")})

    async def _loop(self) -> None:
        self._last = self._signatures()
        while self.queues:
            await asyncio.sleep(self.INTERVAL)
            try:
                now = self._signatures()
            except Exception:                                          # mitten in einer Aenderung gelesen: naechster Takt
                continue
            for kind, signature in now.items():
                if signature != self._last.get(kind):
                    self._publish(kind, self._payload(kind))
            self._last = now
        self._task = None

    def subscribe(self) -> int:
        srv = _srv()
        if not self._tapped:
            srv.event_bus.add_tap(self._tap)
            self._tapped = True
        self._keys += 1
        key = self._keys
        self._event_loop = asyncio.get_running_loop()
        if not self._audio_tapped:
            from app.audio_engine import audio_engine
            audio_engine.add_tap(self._audio_tap)
            self._audio_tapped = True
        self.queues[key] = asyncio.Queue(maxsize=200)
        if self._task is None or self._task.done():
            self._task = asyncio.get_running_loop().create_task(self._loop())
        return key

    def unsubscribe(self, key: int) -> None:
        self.queues.pop(key, None)


hub = EventHub()


def _sse(item: Dict[str, Any]) -> str:
    return f"id: {item['id']}\nevent: {item['event']}\ndata: {json.dumps(item['data'], ensure_ascii=False)}\n\n"


@_route("/events", "read.status", "Live events (Server-Sent Events stream)", query_token=True)
async def stream_events(request: Request, events: Optional[str] = None, access_token: Optional[str] = None) -> StreamingResponse:
    """A stream that stays open and reports changes as they happen: `cue` (active cue of a list changed), `cuelists`, `blackout`, `master`, `timecode`, `selection`, `effects`, `fixtures`,
    `variables`, `show`, `command` (a console command ran) and `audio` (source opened / closed, tempo, signal present); on request only (`?events=beat,hit`): `beat` (every beat) and `hit` (every bass drum / snare / hi-hat hit). The first messages (`event: hello`, then one event per kind) carry the current state.
    `?events=cue,blackout` limits the stream to those kinds. Browsers' EventSource cannot send headers: use `?access_token=<token>` there (the token then appears in URLs - prefer fetch with the header)."""
    wanted = {e.strip() for e in (events or "").split(",") if e.strip()} or set(hub.DEFAULT)
    unknown = wanted - set(hub.ALL)
    if unknown:
        raise ApiError(400, "bad_request", f"Unknown event '{sorted(unknown)[0]}' (events: {', '.join(hub.ALL)}).")
    if len(hub.queues) >= MAX_STREAMS:
        raise ApiError(429, "too_many_streams", f"At most {MAX_STREAMS} event streams at once.")
    key = hub.subscribe()
    queue = hub.queues[key]

    async def generate() -> AsyncIterator[str]:
        try:
            yield "retry: 3000\n\n"
            yield _sse({"id": 0, "event": "hello", "data": {"app": "OpenCue", "events": sorted(wanted)}})
            for item in hub.snapshot_events():
                if item["event"] in wanted:
                    yield _sse({"id": 0, **item})
            last_beat = time.monotonic()
            while True:
                try:
                    item = await asyncio.wait_for(queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    item = None
                if await request.is_disconnected():
                    break
                if item is not None:
                    if item["event"] in wanted:
                        yield _sse(item)
                    last_beat = time.monotonic()
                elif time.monotonic() - last_beat > 15:
                    yield ": keep-alive\n\n"
                    last_beat = time.monotonic()
        finally:
            hub.unsubscribe(key)

    return StreamingResponse(generate(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# ------------------------------------------------------------------------------------------------------------------ Eigene Panels (Button / Fader / Toggle) der Konsole
WIDGET_TYPES = ("button", "fader", "toggle")


class WidgetValueBody(Strict):
    value: float = Field(..., description="The value of the fader: between its minimum and maximum (default 0-100); it is rounded to a whole number like at the console.")


class WidgetStateBody(Strict):
    on: Optional[bool] = Field(None, description="true = on, false = off; leave out to flip the switch.")


def _command_key(template: Any) -> str:
    """Wie window.__commandKey im Browser: der Befehl als gemeinsamer Schluessel aller Panels mit demselben Befehl."""
    return " ".join(str(template or "").split()).lower()


def _toggle_key(mc: Dict[str, Any], panel_id: str) -> str:
    on, off = _command_key(mc.get("command_on")), _command_key(mc.get("command_off"))
    return "toggle|%s|%s" % (on, off) if (on or off) else "toggle#" + panel_id


def _widget_panel(widget_id: str, kind: Optional[str] = None):
    st = _srv().state
    panel = next((p for p in st.panels if p.id == str(widget_id) and p.type in WIDGET_TYPES), None)
    if panel is None:
        raise ApiError(404, "not_found", f"No button, fader or toggle panel '{widget_id}' on the console (GET /widgets lists them).")
    if kind and panel.type != kind:
        raise ApiError(409, "wrong_type", f"'{widget_id}' is a {panel.type}, not a {kind}.")
    return panel


def _widget_dict(panel) -> Dict[str, Any]:
    values = _srv()._command_values
    mc = panel.module_config or {}
    out: Dict[str, Any] = {"id": panel.id, "type": panel.type, "title": panel.title or None, "label": mc.get("label") or mc.get("label_on") or None,
                           "action": "write_to_command_line" if mc.get("action_mode") == "write" else "run_command"}
    if panel.type == "button":
        out["command"] = mc.get("command", "")
    elif panel.type == "fader":
        value = values.get(_command_key(mc.get("command")))
        high = mc.get("fader_max")
        out.update({"command": mc.get("command", ""), "min": float(mc.get("fader_min") or 0), "max": float(100 if high is None else high),
                    "value": value if value is not None else mc.get("fader_value")})
    else:
        value = values.get(_toggle_key(mc, panel.id))
        out.update({"command_on": mc.get("command_on", ""), "command_off": mc.get("command_off", ""), "on": (value >= 0.5) if value is not None else mc.get("initial_state") == "on"})
    return out


async def _widget_command(text: str, log: bool) -> Dict[str, Any]:
    if not str(text).strip():
        raise ApiError(409, "no_command", "This panel has no command set.")
    from app.api_v1 import _run_command
    return await _run_command(str(text), log)


@_route("/widgets", "read.show", "The console's own buttons, faders and toggles")
async def list_widgets() -> Dict[str, Any]:
    """The Button / Fader / Toggle panels of the console's layout with their commands and the current value of faders and toggles. Remote devices have layouts of their own; this is the console's."""
    return {"widgets": [_widget_dict(p) for p in _srv().state.panels if p.type in WIDGET_TYPES]}


@_route("/widgets/{widget_id}/press", "write.widgets", "Press a button panel", method="post")
async def post_widget_press(widget_id: str) -> Dict[str, Any]:
    """Runs the command of the button (also when the button is set to 'write into the command line': the API always runs it) and lets the button pulse on every device."""
    srv = _srv()
    panel = _widget_panel(widget_id, "button")
    mc = panel.module_config or {}
    result = await _widget_command(mc.get("command", ""), mc.get("log_to_history") is not False)
    await srv.event_bus.broadcast({"type": "command_value_updated", "payload": {"pattern": _command_key(mc.get("command")), "kind": "button"}})
    return {"widget": _widget_dict(panel), **result}


@_route("/widgets/{widget_id}/value", "write.widgets", "Move a fader panel", method="put")
async def put_widget_value(widget_id: str, body: WidgetValueBody) -> Dict[str, Any]:
    """Runs the command of the fader with `{value}` replaced and moves the faders of all devices that share the command."""
    srv = _srv()
    values = srv._command_values
    panel = _widget_panel(widget_id, "fader")
    mc = panel.module_config or {}
    low = float(mc.get("fader_min") or 0)
    high = float(100 if mc.get("fader_max") is None else mc.get("fader_max"))
    value = int(round(max(low, min(high, body.value))))
    template = str(mc.get("command", ""))
    result = await _widget_command(re.sub(r"\{value\}", str(value), template, flags=re.IGNORECASE), mc.get("log_to_history") is True)
    key = _command_key(template)
    if len(values) < srv.MAX_COMMAND_PATTERNS or key in values:
        values[key] = float(value)
    await srv.event_bus.broadcast({"type": "command_value_updated", "payload": {"pattern": key, "kind": "fader", "value": value}})
    return {"widget": _widget_dict(panel), "value": value, **result}


@_route("/widgets/{widget_id}/state", "write.widgets", "Switch a toggle panel", method="put")
async def put_widget_state(widget_id: str, body: Optional[WidgetStateBody] = None) -> Dict[str, Any]:
    """Runs the `on` or `off` command of the toggle (an empty command is fine: only the switch moves). Without `on` the switch flips."""
    srv = _srv()
    values = srv._command_values
    panel = _widget_panel(widget_id, "toggle")
    mc = panel.module_config or {}
    on = (not _widget_dict(panel)["on"]) if body is None or body.on is None else bool(body.on)
    command = str(mc.get("command_on" if on else "command_off", ""))
    result = await _widget_command(command, False) if command.strip() else {"command": "", "success": True, "message": "OK: switch set"}
    key = _toggle_key(mc, panel.id)
    if len(values) < srv.MAX_COMMAND_PATTERNS or key in values:
        values[key] = 1.0 if on else 0.0
    await srv.event_bus.broadcast({"type": "command_value_updated", "payload": {"pattern": key, "kind": "toggle", "value": 1 if on else 0}})
    return {"widget": _widget_dict(panel), "on": on, **result}


# ------------------------------------------------------------------------------------------------------------------ Layouts
@_route("/layouts/{filename}/load", "write.layout", "Show a saved layout on the console", method="post")
async def post_layout_load(filename: str) -> Dict[str, Any]:
    """Replaces the panel layout of the console window (unsaved layout changes there are lost). `filename` as in GET /layouts (`Name.json`)."""
    name = str(filename).strip()
    if "/" in name or "\\" in name or not name.lower().endswith(".json"):
        raise ApiError(400, "bad_request", "filename must be a layout file name as GET /layouts shows it (for example 'Concert.json').")
    request = types.SimpleNamespace(state=types.SimpleNamespace(cid=None), json=_JsonRequest({"filename": name}).json)
    return _unwrap(await _srv().load_layout(request))


# ------------------------------------------------------------------------------------------------------------------ Einstellungen (Ausgaenge)
class OutputArtnet(Strict):
    enabled: Optional[bool] = None
    ip: Optional[str] = Field(None, max_length=45, description="Target address (unicast or broadcast), for example 2.255.255.255.")
    bind_ip: Optional[str] = Field(None, max_length=45, description="Network card address to send from ('' = automatic).")


class OutputSacn(Strict):
    enabled: Optional[bool] = None


class OutputEnttec(Strict):
    enabled: Optional[bool] = None
    port: Optional[str] = Field(None, max_length=64, description="Serial port, for example COM3 (GET /system/usb-ports).")
    universe: Optional[int] = Field(None, ge=1, le=63999)


class SystemBody(Strict):
    artnet: Optional[OutputArtnet] = None
    sacn: Optional[OutputSacn] = None
    enttec: Optional[OutputEnttec] = None
    default_universe: Optional[int] = Field(None, ge=1, le=63999, description="Universe that new fixtures start in.")
    language: Optional[str] = Field(None, description="'en', 'de', 'fr', 'nl', 'it' or 'es' (the language of every window).")


def _check_ip(value: str, label: str, allow_empty: bool) -> str:
    import ipaddress
    text = str(value).strip()
    if not text and allow_empty:
        return ""
    try:
        return str(ipaddress.ip_address(text))
    except ValueError:
        raise ApiError(400, "bad_request", f"{label} must be an IP address such as 192.168.1.255{' (or empty)' if allow_empty else ''}.")


@_route("/system", "write.settings", "Change the DMX outputs, default universe and language", method="put")
async def put_system(body: SystemBody) -> Dict[str, Any]:
    """Only what you send changes. Art-Net, sACN and USB DMX are switched like in Settings -> DMX / Network; the answer is `GET /system`."""
    if body.language is not None and body.language not in ("en", "de", "fr", "nl", "it", "es"):
        raise ApiError(400, "bad_request", "language must be one of 'en', 'de', 'fr', 'nl', 'it', 'es'.")
    messages: List[Any] = []
    if body.artnet is not None:
        if body.artnet.ip is not None:
            messages.append(("set_artnet_ip", {"ip": _check_ip(body.artnet.ip, "artnet.ip", False)}))
        if body.artnet.bind_ip is not None:
            messages.append(("set_artnet_bind_ip", {"ip": _check_ip(body.artnet.bind_ip, "artnet.bind_ip", True)}))
        if body.artnet.enabled is not None:
            messages.append(("set_artnet_enabled", {"enabled": body.artnet.enabled}))
    if body.sacn is not None and body.sacn.enabled is not None:
        messages.append(("set_sacn_enabled", {"enabled": body.sacn.enabled}))
    if body.enttec is not None:
        if body.enttec.port is not None:
            messages.append(("set_enttec_port", {"port": body.enttec.port}))
        if body.enttec.universe is not None:
            messages.append(("set_enttec_universe", {"universe": body.enttec.universe}))
        if body.enttec.enabled is not None:
            messages.append(("set_enttec_enabled", {"enabled": body.enttec.enabled}))
    if body.default_universe is not None:
        messages.append(("set_default_universe", {"universe": body.default_universe}))
    if body.language is not None:
        messages.append(("set_language", {"language": body.language}))
    for message_type, payload in messages:
        await _message(message_type, payload)
    return await get_system()


@_route("/system/usb-ports", "read.status", "Serial ports for USB DMX")
async def get_usb_ports() -> Dict[str, Any]:
    return {"ports": await asyncio.to_thread(_srv().dmx_engine.scan_enttec_ports)}


@_route("/system/dmx/reinitialize", "write.settings", "Restart the DMX outputs", method="post")
async def post_dmx_reinitialize() -> Dict[str, Any]:
    """Rebuilds the Art-Net sockets and reconnects USB DMX without restarting the program (the output continues with the current values)."""
    await _message("reinitialize_dmx", {})
    return {"ok": True}


# ------------------------------------------------------------------------------------------------------------------ Fixture-Bibliothek (GDTF-Dateien)
@_route("/fixture-types", "write.patch", "Install a fixture type from a GDTF file", method="post", status_code=201,
        openapi_extra={"requestBody": {"required": True, "content": {"application/octet-stream": {"schema": {"type": "string", "format": "binary"}}}}})
async def post_fixture_type(request: Request) -> Dict[str, Any]:
    """Send the raw `.gdtf` file as the request body and its name in the header `X-Filename` (URL-encoded); up to 30 MB. The file is checked before it is installed. The new type shows up in `GET /fixture-types`."""
    return _unwrap(await _srv().library_import(request))


@_route("/fixture-types/{type_id}", "write.patch", "Remove an installed fixture type", method="delete")
async def delete_fixture_type(type_id: str) -> Dict[str, Any]:
    """Removes the file from the library. A type that the loaded show uses is refused (`409 in_use`): delete those fixtures first."""
    return _unwrap(await _srv().library_uninstall(type_id))


# ------------------------------------------------------------------------------------------------------------------ Befehlszeile: Vorschlaege
@_route("/command/suggest", "read.status", "Completions for a command (like Tab in the command line)")
async def get_command_suggest(text: str = "") -> Dict[str, Any]:
    """What can follow the text typed so far: `?text=Fixture 1 At`. Useful for tools that offer a command line of their own."""
    from app.command_line import get_suggestions
    return {"text": text[:500], "suggestions": get_suggestions(text[:500])}
