# Copyright (C) 2026 Samuel Zenker
# SPDX-License-Identifier: GPL-3.0-or-later
"""
audio_routes.py
Schnittstelle des Audio-Panels (/api/audio): Geraeteliste, Quelle oeffnen/schliessen, Einstellungen, Tempo antippen. Die eigentliche Arbeit macht app/audio_engine.py;
jede Aenderung wird in app_config.json gespeichert und als `audio_state` an alle Geraete gemeldet. Die Messwerte selbst (25 Hz) kommen als `audio_frame` ueber den
WebSocket an die Geraete mit offenem Audio-Panel (siehe server.py `_audio_pump`).
"""
from __future__ import annotations

import asyncio
from typing import Any, Dict

from fastapi import APIRouter, Body
from fastapi.responses import JSONResponse

from app.audio_engine import audio_engine, list_devices
from app.state_manager import state

router = APIRouter(prefix="/api/audio", tags=["audio"], include_in_schema=False)


def _srv():
    from app import server                                       # erst zur Laufzeit: server.py bindet dieses Modul ein
    return server


async def _announce() -> Dict[str, Any]:
    state.audio_config = dict(audio_engine.config)
    state.save_app_config()
    status = audio_engine.status()
    await _srv().event_bus.broadcast({"type": "audio_state", "payload": status})
    return status


@router.get("")
async def get_audio() -> JSONResponse:
    """Alle Eingaenge, die Windows kennt, und der Stand der Analyse."""
    devices = await asyncio.to_thread(list_devices)
    return JSONResponse({"devices": devices, "state": audio_engine.status()})


@router.post("/config")
async def post_config(patch: Dict[str, Any] = Body(default_factory=dict)) -> JSONResponse:
    """Einstellungen aendern (Verstaerkung, Empfindlichkeit, Tempo-Modus, Verzoegerung ...); unbekannte Schluessel werden verworfen."""
    audio_engine.configure(patch)
    return JSONResponse(await _announce())


@router.post("/start")
async def post_start(body: Dict[str, Any] = Body(default_factory=dict)) -> JSONResponse:
    """Quelle oeffnen: `device` = Kennung aus der Liste (ohne Angabe die gewaehlte), `demo` fuer den Demo-Beat."""
    device = body.get("device")
    ok = await asyncio.to_thread(audio_engine.start, str(device) if device is not None else None)
    if ok:
        audio_engine.configure({"autostart": True})
    status = await _announce()
    return JSONResponse({**status, "ok": ok})


@router.post("/stop")
async def post_stop() -> JSONResponse:
    await asyncio.to_thread(audio_engine.stop)
    audio_engine.configure({"autostart": False})
    return JSONResponse(await _announce())


@router.post("/tap")
async def post_tap() -> JSONResponse:
    bpm = audio_engine.tap()
    status = await _announce()
    return JSONResponse({**status, "bpm": bpm})
