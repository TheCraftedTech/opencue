# Copyright (C) 2026 Samuel Zenker
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Schnittstelle des KI-Assistenten fuer die Oberflaeche (/api/ai): Einstellungen, Verbindungstest, Modelle, Modi, Chats. Das Senden einer Nachricht und die gestreamte
Antwort laufen ueber den WebSocket (Nachrichten ai_send / ai_stop -> Ereignis ai_event, siehe app/server.py).

Einstellungen und Verbindungstest sind nur an der Konsole selbst moeglich (nicht von Remote-Geraeten): sie legen fest, mit welchem Server das Programm spricht.
"""
from __future__ import annotations

import asyncio
from typing import Any, Dict

from fastapi import APIRouter, Body, Request
from fastapi.responses import JSONResponse

from app import remote
from app.ai import modes, tools
from app.ai.agent import assistant
from app.ai.config import clean_base_url, public_config
from app.ai.errors import AiError
from app.ai.ollama import list_models
from app.state_manager import state

router = APIRouter(prefix="/api/ai", tags=["ai"], include_in_schema=False)


def _srv():
    from app import server
    return server


def _error(exc: AiError) -> JSONResponse:
    return JSONResponse({"error": {"code": exc.code, "message": exc.message}}, status_code=exc.status)


def _local_only(request: Request) -> None:
    if not remote.is_local(request.client.host if request.client else None):
        raise AiError("local_only", "The assistant settings can only be changed at the console itself.", 403)


async def announce_chats() -> None:
    await _srv().event_bus.broadcast({"type": "ai_chats_changed", "payload": {"chats": assistant.store.list()}})


assistant.on_chats_changed = announce_chats                      # der Assistent meldet selbst, wenn er einen Chat benannt hat


@router.get("/state")
async def get_state() -> JSONResponse:
    return JSONResponse(assistant.state())


@router.get("/modes")
async def get_modes() -> JSONResponse:
    return JSONResponse({"modes": modes.public_modes(), "default": assistant.config["default_mode"]})


@router.get("/tools")
async def get_tools() -> JSONResponse:
    """Die Funktionen des Modus "Arbeiten", nach Sammlungen."""
    return JSONResponse({"collections": [{"name": c.name, "opener": c.opener, "description": c.description,
                                          "tools": [{"name": t.name, "description": t.description, "access": t.access, "parameters": t.parameters} for t in c.tools]}
                                         for c in tools.COLLECTIONS.values() if c.tools], "mode": assistant.config["tools_mode"]})


@router.get("/ui-targets")
async def get_ui_targets() -> JSONResponse:
    """Die Dialoge, die der Wegweiser als Schaltflaeche im Chat anbieten darf (Id, Beschriftung / Menuepfad, was die Schaltflaeche ausloest) - in der Sprache der Oberflaeche."""
    from app.ai.guide import targets as guide_targets
    lang = _srv().state.language
    return JSONResponse({"targets": [guide_targets.describe(t, lang) for t in guide_targets.targets()]})


@router.get("/config")
async def get_config(request: Request) -> JSONResponse:
    try:
        _local_only(request)
    except AiError as exc:
        return _error(exc)
    return JSONResponse(public_config(assistant.config))


@router.post("/config")
async def post_config(request: Request, patch: Dict[str, Any] = Body(default_factory=dict)) -> JSONResponse:
    """Einstellungen aendern (nur was gesendet wird). Eine ungueltige Adresse wird abgelehnt, nichts wird dann geaendert."""
    try:
        _local_only(request)
        assistant.update(patch)
    except AiError as exc:
        return _error(exc)
    state.ai_config = dict(assistant.config)
    state.save_app_config()
    await _srv().event_bus.broadcast({"type": "ai_state", "payload": assistant.state()})
    return JSONResponse(public_config(assistant.config))


@router.post("/test")
async def post_test(request: Request, body: Dict[str, Any] = Body(default_factory=dict)) -> JSONResponse:
    """Verbindung pruefen (mit den gespeicherten Einstellungen oder mit `base_url` / `api_key` aus der Anfrage, ohne zu speichern)."""
    try:
        _local_only(request)
        url = clean_base_url(body["base_url"]) if body.get("base_url") else None
        key = str(body["api_key"]) if "api_key" in body else None
        client = assistant.client(url, key)
        version = await asyncio.to_thread(client.version)
        found = await asyncio.to_thread(list_models, client)
    except AiError as exc:
        return JSONResponse({"ok": False, "error": {"code": exc.code, "message": exc.message}})
    return JSONResponse({"ok": True, "version": version, "models": found})


@router.get("/models")
async def get_models() -> JSONResponse:
    """Die Modelle des eingestellten Servers, die Text erzeugen koennen."""
    try:
        found = await asyncio.to_thread(list_models, assistant.client())
    except AiError as exc:
        return JSONResponse({"ok": False, "error": {"code": exc.code, "message": exc.message}, "models": []})
    return JSONResponse({"ok": True, "models": found})


@router.get("/chats")
async def get_chats() -> JSONResponse:
    return JSONResponse({"chats": assistant.store.list(), "running": list(assistant.runs)})


@router.post("/chats")
async def post_chat(body: Dict[str, Any] = Body(default_factory=dict)) -> JSONResponse:
    try:
        chat = assistant.store.create(str(body.get("model") or assistant.config["model"]), str(body.get("title") or ""), modes.clean_mode(body.get("mode") or assistant.config["default_mode"]))
    except AiError as exc:
        return _error(exc)
    await announce_chats()
    return JSONResponse(chat, status_code=201)


@router.get("/chats/{chat_id}")
async def get_chat(chat_id: str) -> JSONResponse:
    try:
        chat = assistant.store.load(chat_id)
    except AiError as exc:
        return _error(exc)
    chat["running"] = chat_id in assistant.runs
    chat["pending"] = assistant.pending_for(chat_id)                   # offene Rueckfragen "darf die KI das?" (ein neu geoeffnetes Panel zeigt sie sofort)
    return JSONResponse(chat)


@router.patch("/chats/{chat_id}")
async def patch_chat(chat_id: str, body: Dict[str, Any] = Body(default_factory=dict)) -> JSONResponse:
    """Titel, Modell und / oder Modus eines Chats aendern. Beides darf jederzeit gewechselt werden; der Verlauf bleibt."""
    try:
        chat = assistant.store.load(chat_id)
        if "title" in body:
            chat["title"] = " ".join(str(body["title"] or "").split())[:80]
            chat["auto_title"] = not chat["title"]
        if "model" in body:
            chat["model"] = str(body["model"] or "").strip()[:200]
        if "mode" in body:
            chat["mode"] = modes.clean_mode(body["mode"])
        assistant.store.save(chat)
    except AiError as exc:
        return _error(exc)
    await announce_chats()
    return JSONResponse({"id": chat_id, "title": chat["title"], "model": chat["model"], "mode": chat["mode"]})


@router.post("/chats/{chat_id}/duplicate")
async def duplicate_chat(chat_id: str, body: Dict[str, Any] = Body(default_factory=dict)) -> JSONResponse:
    try:
        chat = assistant.store.duplicate(chat_id, str(body.get("title") or ""))
    except AiError as exc:
        return _error(exc)
    await announce_chats()
    return JSONResponse({"id": chat["id"], "title": chat["title"], "model": chat.get("model", ""), "mode": chat["mode"]}, status_code=201)


@router.post("/chats/{chat_id}/seen")
async def seen_chat(chat_id: str) -> JSONResponse:
    """Der Benutzer hat die neue Antwort gesehen: die Markierung "ungelesen" (gelber Punkt in der Chat-Liste) entfaellt auf allen Geraeten. Laeuft im Chat gerade eine Antwort, ist nichts zu tun."""
    try:
        chat = assistant.store.load(chat_id)
        if chat_id not in assistant.runs and chat.get("unread"):
            chat["unread"] = False
            assistant.store.save(chat, touch=False)
            await announce_chats()
    except AiError as exc:
        return _error(exc)
    return JSONResponse({"ok": True})


@router.delete("/chats/{chat_id}")
async def delete_chat(chat_id: str) -> JSONResponse:
    try:
        if chat_id in assistant.runs:
            await assistant.stop(chat_id)
        assistant.store.delete(chat_id)
    except AiError as exc:
        return _error(exc)
    await announce_chats()
    return JSONResponse({"ok": True})
