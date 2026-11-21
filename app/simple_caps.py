# Copyright (C) 2026 Samuel Zenker
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Faehigkeiten ausgewaehlter Scheinwerfer fuer das Einfach-Panel ("Einfache Steuerung", static/js/simple_panel.js): welche Bedienelemente braucht die Auswahl?

  GET /api/simple/caps?ids=<id>,<id>,...
      {"pan": bool, "tilt": bool, "dimmer": bool, "color": "rgb" | "cmy" | "wheel" | "none", "zoom": bool, "focus": bool, "strobe": bool,
       "gobo": null | {"ids": [...], "channel_offset": n, "slots": [{"name", "image", "value"}]}}

Die Angaben sind die Vereinigung ueber die Auswahl (ein Regler erscheint, sobald EIN Scheinwerfer ihn hat; die Server-Aufloesung ignoriert Scheinwerfer ohne den Kanal).
Gobos gelten nur fuer die Scheinwerfer, die denselben Typ UND denselben Kanal-Platz wie der erste mit Gobo-Rad haben (ein Befehl "Rad auf Mitte des Slots" ist ein rohes Kanal-Byte).
"""
from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app import fixture_manager
from app.dmx_resolve import beam_channels
from app.state_manager import state

router = APIRouter()
MAX_IDS = 400

# Looks des Einfach-Panels: Id -> (Skriptname = Dateiname in defaults/effects ohne .fx, Kategorie). Es sind die mitgelieferten Standard-Effekte, ohne jede Einstellung.
LOOKS = {"rainbow": ("rainbow", "color"), "circle": ("circle", "position"), "pulse": ("pulse", "dimmer"), "strobe": ("strobe", "dimmer")}


def ensure_look(look_id: str) -> Dict[str, Any]:
    """Der Effekt zu diesem Look steht in der Show (sonst wird er aus den Standard-Effekten angelegt; fehlt auch die Skriptdatei im Benutzerordner, wird sie von dort kopiert).
    Rueckgabe {"fx_id", "name", "category", "created"} oder {} (unbekannter Look / Skript nicht vorhanden)."""
    entry = LOOKS.get(look_id)
    if entry is None:
        return {}
    stem, category = entry
    from app import paths
    from app.fx_engine import fx_engine
    from app.fx_script import registry
    if not registry.has(stem):                                                    # das Skript fehlt im Benutzerordner (z. B. geloescht oder neuer Datenordner): aus den Standard-Effekten holen
        source = paths.default_effects_dir() / (stem + ".fx")
        target = paths.effects_dir() / (stem + ".fx")
        if not source.is_file():
            return {}
        if not target.exists():
            target.write_bytes(source.read_bytes())
        registry.reload()
        if not registry.has(stem):
            return {}
    for fx_id, definition in state.fx_effects.items():
        if definition.get("kind") == stem:
            return {"fx_id": fx_id, "name": definition.get("name", ""), "category": category, "created": False}
    fx_id = fx_engine.save_definition(None, {"kind": stem})
    if fx_id is None:
        return {}
    state.mark_dirty()
    return {"fx_id": fx_id, "name": state.fx_effects[fx_id].get("name", ""), "category": category, "created": True}


async def run_look(look_id: str, on: bool, broadcast: Any) -> Dict[str, Any]:
    """Look einschalten (Effekt auf die gewaehlten Scheinwerfer) oder ausschalten (Effekt dieser Kategorie von der Auswahl nehmen). Rueckgabe: {"ok", "created", "message"}."""
    from app.command_line import execute_command
    info = ensure_look(look_id)
    if not info:
        return {"ok": False, "created": False, "message": "Look not available"}
    command = f'Effect "{info["name"]}"' if on else f"Effect Off {info['category']}"
    result = await execute_command(command, broadcast)
    return {"ok": bool(result.get("success")), "created": info["created"], "message": str(result.get("message", ""))}

def _channels(fixture: Any) -> List[Dict[str, Any]]:
    ft = fixture_manager.get_fixture_type_by_id(fixture.fixture_type)
    if not ft:
        return []
    modes = ft.get("modes") or []
    mode = next((m for m in modes if m.get("name") == fixture.mode), None) or (modes[0] if modes else None)
    return list(mode.get("channels") or []) if mode else []


def _color_kind(names: List[str]) -> str:
    low = [n.lower() for n in names]
    if any(n.startswith("coloradd_") or n in ("red", "green", "blue", "colorrgb_red") or n.startswith("colorrgb") for n in low):
        return "rgb"
    if any(n.startswith("colorsub_") for n in low):
        return "cmy"
    if any(n.startswith("color1") or n.startswith("colorwheel") for n in low):
        return "wheel"
    return "none"


def caps_for(ids: List[str]) -> Dict[str, Any]:
    out: Dict[str, Any] = {"pan": False, "tilt": False, "dimmer": False, "color": "none", "zoom": False, "focus": False, "strobe": False, "gobo": None}
    rank = {"none": 0, "wheel": 1, "cmy": 2, "rgb": 3}
    gobo_key = None
    for fid in ids[:MAX_IDS]:
        fixture = state.fixtures.get(fid)
        if fixture is None:
            continue
        channels = _channels(fixture)
        names = [c.get("name", "") for c in channels]
        out["pan"] = out["pan"] or "Pan" in names
        out["tilt"] = out["tilt"] or "Tilt" in names
        out["dimmer"] = out["dimmer"] or "Dimmer" in names
        kind = _color_kind(names)
        if rank[kind] > rank[out["color"]]:
            out["color"] = kind
        beam = beam_channels(names)
        out["zoom"] = out["zoom"] or "zoom" in beam
        out["focus"] = out["focus"] or "focus" in beam
        out["strobe"] = out["strobe"] or "strobe" in beam
        gobo_channel = beam.get("gobo")
        if not gobo_channel:
            continue
        offset = next((c.get("offset") for c in channels if c.get("name") == gobo_channel), None)
        if offset is None:
            continue
        key = (fixture.fixture_type, offset)
        if out["gobo"] is None:
            wheels = [w for w in fixture_manager.get_fixture_wheels(fixture.fixture_type) if w.get("attribute_name") == gobo_channel and w.get("type") == "gobo"]
            if not wheels:
                continue
            gobo_key = key
            out["gobo"] = {"ids": [fid], "channel_offset": offset, "slots": [{"name": s.get("name", ""), "image": s.get("image"), "value": s.get("dmx_center", s.get("dmx_from", 0))}
                                                                         for s in wheels[0].get("slots", [])]}
        elif key == gobo_key:
            out["gobo"]["ids"].append(fid)
    return out


@router.get("/api/simple/caps")
async def simple_caps(request: Request, ids: str = "") -> JSONResponse:
    import asyncio
    wanted = [i for i in ids.split(",") if i][:MAX_IDS]
    caps = await asyncio.to_thread(caps_for, wanted)                              # das erste Einlesen der Gobo-Raeder dauert: nicht im Event-Loop
    return JSONResponse({"ok": True, **caps}, headers={"Cache-Control": "no-store"})
