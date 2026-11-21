# Copyright (C) 2026 Samuel Zenker
# SPDX-License-Identifier: GPL-3.0-or-later
"""
ui_store.py
Gemerkter Oberflaechenzustand der KONSOLE in der app_config.json (Schluessel "ui_store"): alles, was die Oberflaeche unter "opencue.*" in den localStorage legt - zuletzt
benutzte Unteransichten, Umschalter, Filter, Sortierung, Scrollpositionen, Spaltenbreiten, GUI-Skalierung, Kamera der 3D-Simulation ...

Der localStorage des Fensters bleibt der schnelle Speicher; dazu spiegelt static/js/ui_store.js jede Aenderung hierher und laedt beim Start den Stand von hier zurueck.
So geht nichts verloren, wenn der WebView-Speicher geleert wird oder der Datenordner wechselt. Externe Geraete (iPad ...) behalten ihren Zustand im eigenen Browser:
jedes Geraet darf anders eingestellt sein.

  POST /api/uistore   {"set": {schluessel: text}, "remove": [schluessel]}   (nur lokal)
"""
from __future__ import annotations

import threading
from typing import Any, Dict, Optional

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

PREFIX = "opencue."
MAX_KEYS = 400
MAX_VALUE = 60000          # Zeichen je Eintrag
router = APIRouter()
_timer: Optional[threading.Timer] = None


def clean(raw: Any) -> Dict[str, str]:
    """Nur gueltige Eintraege: Schluessel mit Vorsatz "opencue.", Werte als Text, nicht zu gross."""
    out: Dict[str, str] = {}
    if isinstance(raw, dict):
        for key, value in raw.items():
            if isinstance(key, str) and key.startswith(PREFIX) and len(key) <= 120 and isinstance(value, str) and len(value) <= MAX_VALUE:
                out[key] = value
    return dict(list(out.items())[:MAX_KEYS])


def _schedule_save(state) -> None:
    """Die Datei gesammelt schreiben (Scrollen und Ziehen erzeugen viele Aenderungen)."""
    global _timer
    if _timer is not None:
        _timer.cancel()
    _timer = threading.Timer(2.0, state.save_app_config)
    _timer.daemon = True
    _timer.start()


@router.post("/api/uistore")
async def api_set(request: Request) -> JSONResponse:
    from app import remote
    from app.state_manager import state
    if not remote.is_local(request.client.host if request.client else None):
        return JSONResponse({"ok": False, "error": "local_only"}, status_code=403)
    try:
        body = await request.json()
    except ValueError:
        body = {}
    body = body if isinstance(body, dict) else {}
    changed = False
    for key, value in clean(body.get("set")).items():
        if state.ui_store.get(key) != value and (key in state.ui_store or len(state.ui_store) < MAX_KEYS):
            state.ui_store[key] = value
            changed = True
    for key in body.get("remove") or []:
        if isinstance(key, str) and state.ui_store.pop(key, None) is not None:
            changed = True
    if changed:
        _schedule_save(state)
    return JSONResponse({"ok": True})
