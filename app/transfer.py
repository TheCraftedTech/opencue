# Copyright (C) 2026 Samuel Zenker
# SPDX-License-Identifier: GPL-3.0-or-later
"""
transfer.py
Dateien, die der Browser selbst zusammenstellt (Einstellungen, eigene Tastenbelegung, MIDI-Belegung), zum Speichern anbieten.

Im Programmfenster (pywebview) gibt es keinen Browser-Download; der Server oeffnet dafuer den Standard-Browser mit einer Download-Adresse (siehe app/file_manager.py,
POST /api/files/open-download). Damit das auch fuer Inhalte geht, die nur der Browser kennt, legt er sie hier kurz ab:

  POST /api/transfer/stash   {"name": "datei.json", "data": {...}}  ->  {"url": "/api/transfer/get?token=..."}   (der Inhalt liegt 2 Minuten im Speicher)
  GET  /api/transfer/get?token=...                                  ->  die JSON-Datei als Download (gleiche Zugangsregeln wie jede andere Adresse)
Es wird nichts auf die Platte geschrieben; hoechstens 8 Eintraege, jeder bis 2 MB.
"""
from __future__ import annotations

import json
import re
import secrets
import time
from typing import Dict, Tuple

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response

router = APIRouter()

TTL_S = 120.0
MAX_ENTRIES = 8
MAX_BYTES = 2 * 1024 * 1024
_stash: Dict[str, Tuple[float, str, bytes]] = {}


def _purge(now: float) -> None:
    for token in [t for t, (at, _n, _b) in _stash.items() if now - at > TTL_S]:
        _stash.pop(token, None)
    while len(_stash) >= MAX_ENTRIES:
        _stash.pop(min(_stash, key=lambda t: _stash[t][0]), None)


def put(name: str, data: object) -> str:
    """Inhalt ablegen, gibt die Download-Adresse zurueck."""
    body = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
    if len(body) > MAX_BYTES:
        raise ValueError("too large")
    safe = re.sub(r"[^A-Za-z0-9._ -]", "_", str(name or "opencue.json"))[:80] or "opencue.json"
    if not safe.lower().endswith(".json"):
        safe += ".json"
    now = time.monotonic()
    _purge(now)
    token = secrets.token_urlsafe(18)
    _stash[token] = (now, safe, body)
    return f"/api/transfer/get?token={token}"


@router.post("/api/transfer/stash")
async def stash(request: Request) -> JSONResponse:
    try:
        payload = await request.json()
        url = put(str(payload.get("name", "")), payload.get("data"))
    except ValueError:
        return JSONResponse({"ok": False, "error": "too_large"}, status_code=413)
    except Exception:
        return JSONResponse({"ok": False, "error": "invalid"}, status_code=400)
    return JSONResponse({"ok": True, "url": url})


@router.get("/api/transfer/get")
async def get(token: str = "") -> Response:
    entry = _stash.get(token)
    if entry is None or time.monotonic() - entry[0] > TTL_S:
        _stash.pop(token, None)
        return JSONResponse({"ok": False, "error": "gone"}, status_code=404)
    _at, name, body = entry
    return Response(content=body, media_type="application/json; charset=utf-8", headers={
        "Content-Disposition": f'attachment; filename="{name}"', "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})
