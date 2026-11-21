# Copyright (C) 2026 Samuel Zenker
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Hilfe-Menue "Log-Ordner oeffnen" / "Problem melden" und Fehlermeldungen der Oberflaeche (JavaScript) ins Protokoll.

  POST /api/diag/open-log-folder   den Ordner mit opencue.log im Explorer oeffnen (nur an der Konsole selbst)
  POST /api/diag/report            Diagnose-Text (Version, System, letzte Protokollzeilen - ohne Zugangsschluessel) + Adresse der Meldeseite; an der Konsole wird sie gleich im Browser geoeffnet
  POST /api/client-error           ein JavaScript-Fehler aus der Oberflaeche (static/js/error_report.js): kommt als Zeile `OC-3601` ins Protokoll und steht damit im Fehlerbericht
                                   (begrenzt: gleiche Fehler zaehlen nur einmal je Minute, insgesamt hoechstens 40 Zeilen je Minute, alles gekuerzt)
"""
from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Any, Dict, Tuple

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app import about, errors, logsetup, remote, version
from app.window_signals import file_dialog

logger = logging.getLogger("opencue.ui")
router = APIRouter()

ISSUES_URL = version.SOURCE_URL.rstrip("/") + "/issues/new"
MAX_PER_MINUTE = 40
_seen: Dict[Tuple[str, str, str], float] = {}
_window: list = []                                                # Zeitpunkte der zuletzt geschriebenen Zeilen


def _is_local(request: Request) -> bool:
    return remote.is_local(request.client.host if request.client else None)


@router.post("/api/diag/open-log-folder")
async def open_log_folder(request: Request) -> JSONResponse:
    if not _is_local(request):
        return JSONResponse({"ok": False, "error": "local_only"}, status_code=403)
    try:
        folder = logsetup.log_dir()
        folder.mkdir(parents=True, exist_ok=True)
        os.startfile(str(folder))                                  # noqa: S606 - nur Windows (Explorer)
        return JSONResponse({"ok": True})
    except Exception as exc:                                       # noqa: BLE001
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=500)


@router.post("/api/diag/report")
async def report_problem(request: Request) -> JSONResponse:
    text = await asyncio.to_thread(errors.diagnostics, "", "Problem report", "Sent from the Help menu: please describe what you did and what happened.", "", 60)
    opened = False
    if _is_local(request) and file_dialog.available:
        await asyncio.to_thread(about._open_browser, ISSUES_URL)    # im Programmfenster oeffnet window.open keinen Browser: der Server startet ihn
        opened = True
    return JSONResponse({"ok": True, "text": text, "url": ISSUES_URL, "opened": opened})


def _clip(value: Any, limit: int) -> str:
    text = " ".join(str(value if value is not None else "").split())
    return text if len(text) <= limit else text[: limit - 1] + "..."


@router.post("/api/client-error")
async def client_error(request: Request) -> JSONResponse:
    try:
        body = await request.json()
    except Exception:                                              # noqa: BLE001
        return JSONResponse({"ok": False}, status_code=400)
    if not isinstance(body, dict):
        return JSONResponse({"ok": False}, status_code=400)
    message, source, line = _clip(body.get("message"), 300), _clip(body.get("source"), 200), _clip(body.get("line"), 12)
    now = time.monotonic()
    key = (message, source, line)
    if now - _seen.get(key, -999.0) < 60.0:                        # derselbe Fehler noch einmal: nicht noch eine Zeile
        return JSONResponse({"ok": True, "logged": False})
    _window[:] = [stamp for stamp in _window if now - stamp < 60.0]
    if len(_window) >= MAX_PER_MINUTE:
        return JSONResponse({"ok": True, "logged": False})
    _window.append(now)
    _seen[key] = now
    if len(_seen) > 500:
        for old in sorted(_seen, key=_seen.get)[:250]:
            _seen.pop(old, None)
    device = "console" if _is_local(request) else "remote device"
    logger.warning("[UI] OC-3601 JavaScript error on the %s: %s (%s:%s:%s) %s | page %s | %s", device, message, source, line, _clip(body.get("col"), 12),
                   _clip(body.get("kind"), 20), _clip(body.get("page"), 120), _clip(body.get("stack"), 800))
    return JSONResponse({"ok": True, "logged": True})
