# Copyright (C) 2026 Samuel Zenker
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Windows-Einstellungen im Programm: Administrator-Hinweis, Firewall-Regel, Start mit Windows (Einstellungen -> Fernzugriff / Allgemein). Auch von Fernzugriffs-Geraeten aenderbar (die Windows-Rueckfrage erscheint dabei am Hauptrechner).

  GET  /api/system            {admin, headless, firewall: {available, exists, admin, program}, autostart: {available, enabled, headless, command}}
  POST /api/system/firewall   {enabled: true|false}: Regel anlegen / loeschen (Windows fragt nach Administratorrechten, falls OpenCue nicht als Administrator laeuft)
  POST /api/system/autostart  {enabled, headless}: Start mit Windows ein-/ausschalten (Registry des Benutzers, keine Administratorrechte)
  POST /api/system/fileassoc  {enabled}: Doppelklick auf .ocshow-Dateien oeffnet sie in OpenCue (app/file_assoc.py; im Ergebnis von GET: fileassoc {available, enabled, command})
"""
from __future__ import annotations

import asyncio
import os

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app import autostart, file_assoc, firewall, remote, windows_env
from app.keep_awake import keep_awake

router = APIRouter()


def _local(request: Request) -> bool:
    return remote.is_local(request.client.host if request.client else None)


def info() -> dict:
    return {"ok": True, "admin": windows_env.is_admin(), "headless": os.environ.get("OPENCUE_HEADLESS") == "1", "firewall": firewall.status(), "autostart": autostart.get(), "fileassoc": file_assoc.get(), "keep_awake": keep_awake.status()}


@router.get("/api/system")
async def system_info() -> JSONResponse:
    return JSONResponse(await asyncio.to_thread(info))


@router.post("/api/system/firewall")
async def set_firewall(request: Request) -> JSONResponse:
    body = await request.json()
    want = bool(body.get("enabled")) if isinstance(body, dict) else False
    result = await asyncio.to_thread(firewall.add if want else firewall.remove)             # wartet auf die Windows-Rueckfrage (UAC) - nicht auf der Ereignisschleife
    return JSONResponse({**result, "firewall": await asyncio.to_thread(firewall.status)})


@router.post("/api/system/autostart")
async def set_autostart(request: Request) -> JSONResponse:
    body = await request.json()
    if not isinstance(body, dict):
        return JSONResponse({"ok": False, "error": "bad_request"}, status_code=400)
    if not autostart.available():
        return JSONResponse({"ok": False, "error": "unavailable", "autostart": autostart.get()}, status_code=409)
    state = await asyncio.to_thread(autostart.set, bool(body.get("enabled")), bool(body.get("headless")))
    return JSONResponse({"ok": True, "autostart": state})


@router.post("/api/system/fileassoc")
async def set_fileassoc(request: Request) -> JSONResponse:
    body = await request.json()
    if not isinstance(body, dict):
        return JSONResponse({"ok": False, "error": "bad_request"}, status_code=400)
    if not file_assoc.available():
        return JSONResponse({"ok": False, "error": "unavailable", "fileassoc": file_assoc.get()}, status_code=409)
    state = await asyncio.to_thread(file_assoc.set, bool(body.get("enabled")))
    return JSONResponse({"ok": True, "fileassoc": state})
