# Copyright (C) 2026 Samuel Zenker
# SPDX-License-Identifier: GPL-3.0-or-later
"""
ltc_routes.py
HTTP fuer den LTC-Eingang (Einstellungen -> Timecode): GET /api/ltc (Zustand, mit ?devices=1 auch die Audio-Eingaenge), POST /api/ltc/config (Einstellung uebernehmen und den Eingang
neu starten). Die Einstellung steht in der App-Konfiguration (state.ltc_config, show-unabhaengig). numpy und PortAudio werden erst geladen, wenn LTC gebraucht wird.
Die Anbindung an die globale Uhr liegt im Server (`_ltc_event`); er setzt `hooks` und `loop` beim Start.
"""
from __future__ import annotations

import asyncio
from typing import Any, Callable, Dict, Optional

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter()
hooks: Dict[str, Optional[Callable[..., Any]]] = {"fix": None, "lost": None}       # vom Server gesetzt (Audio-Thread -> Ereignisschleife)
loop: Optional[asyncio.AbstractEventLoop] = None

CHANNELS = ("left", "right", "mix")
OUT_CHANNELS = ("left", "right", "both")
OUT_FPS = (24.0, 25.0, 29.97, 30.0)
DEFAULT_OUT = {"enabled": False, "device": "", "channel": "both", "fps": 25.0, "level": 0.5}


def _clean_out(raw: Any, base: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    out = dict(base or DEFAULT_OUT)
    if isinstance(raw, dict):
        if "enabled" in raw:
            out["enabled"] = raw["enabled"] is True
        if "device" in raw:
            out["device"] = str(raw["device"] or "")[:200]
        if raw.get("channel") in OUT_CHANNELS:
            out["channel"] = raw["channel"]
        if "fps" in raw:
            try:
                value = float(raw["fps"])
                out["fps"] = min(OUT_FPS, key=lambda candidate: abs(candidate - value))
            except (TypeError, ValueError):
                pass
        if "level" in raw:
            try:
                out["level"] = round(min(1.0, max(0.05, float(raw["level"]))), 2)
            except (TypeError, ValueError):
                pass
    return out


def clean(raw: Any, base: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """LTC-Einstellung bereinigen (ohne numpy zu laden): Eingang (enabled, device, channel) und Senden (out)."""
    out = dict(base or {"enabled": False, "device": "", "channel": "left", "out": dict(DEFAULT_OUT)})
    out["out"] = _clean_out(None, out.get("out"))
    if isinstance(raw, dict):
        if "enabled" in raw:
            out["enabled"] = raw["enabled"] is True
        if "device" in raw:
            out["device"] = str(raw["device"] or "")[:200]
        if raw.get("channel") in CHANNELS:
            out["channel"] = raw["channel"]
        if isinstance(raw.get("out"), dict):
            out["out"] = _clean_out(raw["out"], out["out"])
    return out


def _provider() -> tuple:
    from app.timecode import timecode
    return (timecode.running, timecode.direction, timecode.rate, timecode.position_ms())


def apply(config: Dict[str, Any]) -> Dict[str, Any]:
    """Eingang (LTC lesen) und Ausgang (LTC senden) nach der Einstellung starten / stoppen (blockierend: im Thread aufrufen)."""
    from app import ltc
    ltc.ltc_out.provider = _provider
    if config.get("out", {}).get("enabled") or ltc.ltc_out.running:
        ltc.ltc_out.configure(config.get("out", {}))
    ltc.ltc.on_frame = lambda frame: hooks["fix"](frame) if hooks["fix"] else None            # beim Aufruf nachschlagen: der Server setzt die Haken evtl. erst nach dem ersten Konfigurieren
    ltc.ltc.on_lost = lambda: hooks["lost"]() if hooks["lost"] else None
    return ltc.ltc.configure(config)


def _devices() -> list:
    from app.audio_engine import list_devices
    out = [{"id": "demo", "name": "Test signal (25 fps)", "kind": "demo", "channels": 1}]
    out += [{"id": d["id"], "name": d["name"], "kind": d["kind"], "channels": d["channels"], "default": bool(d.get("default"))} for d in list_devices() if d["kind"] in ("input", "loopback")]
    return out


def _outputs() -> list:
    from app.ltc import list_outputs
    return [{"id": d["id"], "name": d["name"], "channels": d["channels"], "default": bool(d.get("default"))} for d in list_outputs()]


def _status() -> Dict[str, Any]:
    from app.state_manager import state
    try:
        from app import ltc
        data = ltc.ltc.status()
    except Exception:                                                                # noqa: BLE001
        data = {"running": False, "locked": False, "error": "", "device": "", "fps": 0.0, "drop": False, "timecode": "", "level": 0.0}
    data["config"] = dict(state.ltc_config)
    try:
        from app import ltc as ltc_module
        data["out"] = ltc_module.ltc_out.status()
    except Exception:                                                                # noqa: BLE001
        data["out"] = {"running": False, "sending": False, "error": "", "device": ""}
    return data


@router.get("/api/ltc")
async def get_ltc(request: Request) -> JSONResponse:
    data = _status()
    if request.query_params.get("devices"):
        data["devices"] = await asyncio.to_thread(_devices)
        data["outputs"] = await asyncio.to_thread(_outputs)
    return JSONResponse(data)


@router.post("/api/ltc/config")
async def set_ltc(request: Request) -> JSONResponse:
    from app.state_manager import state
    try:
        body = await request.json()
    except ValueError:
        body = {}
    state.ltc_config = clean(body, state.ltc_config)
    state.save_app_config()
    await asyncio.to_thread(apply, state.ltc_config)
    return JSONResponse({"ok": True, **_status()})
