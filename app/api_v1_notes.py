# Copyright (C) 2026 Samuel Zenker
# SPDX-License-Identifier: GPL-3.0-or-later
"""
api_v1_notes.py
REST-API (Teil 4): Chat und Notizen des Panels "Chat & Notizen" (app/notebook.py) unter /api/v1/notebook. Gleicher Router, gleiche Anmeldung, gleiche Fehler wie der Rest der API.
Zwei Berechtigungen: read.notes (Liste, Verlauf / Text lesen, als Markdown laden) und write.notes (anlegen, umbenennen, loeschen, Nachrichten, Notiz aendern / ergaenzen).

Alles laeuft ueber dieselben Funktionen wie die Oberflaeche: jede Aenderung erscheint sofort in allen offenen Panels (WebSocket `notebook_event`). Nachrichten von der API
tragen als Absender den Namen des Tokens (oder `author` aus der Anfrage) und die Geraetekennung "api". Eine Notiz laesst sich mit `base_rev` gegen gleichzeitiges Schreiben
schuetzen: stimmt die Version nicht mehr, kommt 409 und nichts wird gespeichert (in der Oberflaeche gewinnt dagegen der letzte Stand).
Der Chatverlauf gehoert zum Programm, nicht zur Show.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import Request
from pydantic import Field

from app import notebook
from app.api_v1 import ApiError, _route
from app.api_v1_manage import Strict

API_DEVICE = "api"
MAX_PAGE = 500


def _fail(exc: "notebook.NotebookError") -> ApiError:
    return ApiError(exc.status, exc.code, exc.message)


def _author(request: Request, given: Optional[str]) -> str:
    name = notebook.clean_name(given) or notebook.clean_name((getattr(request.state, "api_token", None) or {}).get("name"))
    return name or "API"


def _public(thread: Dict[str, Any], messages: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    out = notebook.summary(thread)
    if thread["kind"] == "chat":
        out["messages"] = [{"id": m.get("id"), "author": m.get("author"), "text": m.get("text"), "ts": m.get("ts"), "device": m.get("cid", "")}
                           for m in (thread["messages"] if messages is None else messages)]
    else:
        out["body"] = thread.get("body", "")
    return out


class ThreadCreate(Strict):
    kind: str = Field("chat", description='"chat" or "note".')
    title: str = Field("", max_length=notebook.MAX_TITLE)
    body: str = Field("", max_length=notebook.MAX_BODY, description="Start text of a note (Markdown).")


class ThreadRename(Strict):
    title: str = Field(..., max_length=notebook.MAX_TITLE)


class MessageBody(Strict):
    text: str = Field(..., min_length=1, max_length=notebook.MAX_TEXT)
    author: Optional[str] = Field(None, max_length=notebook.MAX_NAME, description="Name shown next to the message. Default: the name of the token.")


class BodyPut(Strict):
    body: str = Field(..., max_length=notebook.MAX_BODY, description="The complete Markdown text of the note.")
    base_rev: Optional[int] = Field(None, ge=0, description="Revision you read. When the note has changed since, nothing is saved and the answer is 409.")


class AppendBody(Strict):
    text: str = Field(..., min_length=1, max_length=notebook.MAX_BODY, description="Text that is added at the end of the note, on its own line.")


@_route("/notebook", "read.notes", "List the chats and notes")
async def list_notebook(kind: Optional[str] = None) -> Dict[str, Any]:
    """Newest change first. Each entry has `id`, `kind` (chat | note), `title`, `updated`, `rev`; chats also `count` and `last`, notes `snippet` and `tasks` (done / total checklist items). `?kind=chat` or `?kind=note` filters."""
    if kind is not None and kind not in notebook.KINDS:
        raise ApiError(400, "bad_request", 'kind must be "chat" or "note".')
    items = [t for t in notebook.list_threads() if kind is None or t["kind"] == kind]
    return {"threads": items, "limits": {"message": notebook.MAX_TEXT, "note": notebook.MAX_BODY, "title": notebook.MAX_TITLE}}


@_route("/notebook", "write.notes", "Create a chat or a note", method="post", status_code=201)
async def create_notebook(body: ThreadCreate) -> Dict[str, Any]:
    try:
        thread = notebook.create(body.kind, body.title, body.body)
    except notebook.NotebookError as exc:
        raise _fail(exc)
    await notebook._announce("created", thread, by=API_DEVICE)
    return _public(thread)


@_route("/notebook/{thread_id}", "read.notes", "Read a chat (messages) or a note (text)")
async def get_notebook(thread_id: str, after: Optional[str] = None, limit: int = 100) -> Dict[str, Any]:
    """A chat returns its newest `limit` messages (default 100, at most 500), oldest first; `?after=<message id>` returns only the messages after that one (to poll for new ones).
    A note returns `body` (Markdown) and `rev` (changes with every save; send it back as `base_rev`)."""
    try:
        thread = notebook._load(thread_id)
    except notebook.NotebookError as exc:
        raise _fail(exc)
    if thread["kind"] != "chat":
        return _public(thread)
    messages = thread["messages"]
    if after:
        index = next((i for i, m in enumerate(messages) if m.get("id") == after), None)
        if index is None:
            raise ApiError(404, "not_found", f"No message '{after}' in this chat (it may have been deleted).")
        messages = messages[index + 1:]
    messages = messages[-max(1, min(int(limit), MAX_PAGE)):]
    return _public(thread, messages)


@_route("/notebook/{thread_id}/export", "read.notes", "Download a chat or note as a Markdown file")
async def export_notebook(thread_id: str):
    try:
        return notebook.markdown_response(notebook._load(thread_id))
    except notebook.NotebookError as exc:
        raise _fail(exc)


@_route("/notebook/{thread_id}", "write.notes", "Rename a chat or note", method="put")
async def rename_notebook(thread_id: str, body: ThreadRename) -> Dict[str, Any]:
    try:
        thread = notebook.rename(thread_id, body.title)
    except notebook.NotebookError as exc:
        raise _fail(exc)
    await notebook._announce("renamed", thread, by=API_DEVICE)
    return notebook.summary(thread)


@_route("/notebook/{thread_id}", "write.notes", "Delete a chat or note", method="delete")
async def delete_notebook(thread_id: str) -> Dict[str, Any]:
    try:
        notebook.delete(thread_id)
    except notebook.NotebookError as exc:
        raise _fail(exc)
    await notebook._srv().event_bus.broadcast({"type": "notebook_event", "payload": {"op": "deleted", "id": thread_id, "by": API_DEVICE}})
    return {"ok": True}


@_route("/notebook/{thread_id}/messages", "write.notes", "Send a chat message", method="post", status_code=201)
async def post_notebook_message(request: Request, thread_id: str, body: MessageBody) -> Dict[str, Any]:
    """Appears in every open Chat & Notes panel at once (with a notice when the chat is not in view)."""
    try:
        result = notebook.add_message(thread_id, _author(request, body.author), API_DEVICE, body.text)
    except notebook.NotebookError as exc:
        raise _fail(exc)
    await notebook._announce("message", result["thread"], message=result["message"])
    m = result["message"]
    return {"id": m["id"], "author": m["author"], "text": m["text"], "ts": m["ts"], "device": m["cid"]}


@_route("/notebook/{thread_id}/messages/{message_id}", "write.notes", "Delete a chat message", method="delete")
async def delete_notebook_message(thread_id: str, message_id: str) -> Dict[str, Any]:
    try:
        thread = notebook.delete_message(thread_id, message_id)
    except notebook.NotebookError as exc:
        raise _fail(exc)
    await notebook._announce("message_deleted", thread, message_id=message_id, by=API_DEVICE)
    return {"ok": True}


@_route("/notebook/{thread_id}/body", "write.notes", "Replace the text of a note", method="put")
async def put_notebook_body(request: Request, thread_id: str, body: BodyPut) -> Dict[str, Any]:
    """Saves the complete text. With `base_rev` the save only happens when nobody changed the note since you read it (otherwise 409)."""
    try:
        result = notebook.save_body(thread_id, body.body, body.base_rev, strict=True)
    except notebook.NotebookError as exc:
        raise _fail(exc)
    thread = result["thread"]
    if result["changed"]:
        await notebook._announce("note", thread, body=thread["body"], rev=thread["rev"], by=API_DEVICE, author=_author(request, None), conflict=False)
    return {"rev": thread["rev"], "changed": result["changed"]}


@_route("/notebook/{thread_id}/append", "write.notes", "Add a line to the end of a note", method="post")
async def append_notebook(request: Request, thread_id: str, body: AppendBody) -> Dict[str, Any]:
    """For logs and scripts: no need to read the note first, nothing else is overwritten."""
    try:
        thread = notebook.append_body(thread_id, body.text)
    except notebook.NotebookError as exc:
        raise _fail(exc)
    await notebook._announce("note", thread, body=thread["body"], rev=thread["rev"], by=API_DEVICE, author=_author(request, None), conflict=False)
    return {"rev": thread["rev"], "changed": True}
