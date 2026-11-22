# Copyright (C) 2026 Samuel Zenker
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Chat und Notizen (Panel "Chat & Notizen", static/js/chat_panel.js): Unterhaltungen zwischen den Geraeten, die mit dem Programm verbunden sind (Konsole, iPad, Handy ...),
und Notizen / Checklisten im Markdown-Format. Alles liegt auf dem Server, jedes Panel auf jedem Geraet zeigt dieselben Eintraege.

Ein Eintrag ("thread") ist eine JSON-Datei `<id>.json` (id: 16 Hex-Zeichen) im Ordner "notebook" des Datenverzeichnisses, geschrieben wird atomar:
  kind "chat": messages = [{id, cid, author, text, ts}]       (cid = Kennung des sendenden Geraets, author = dessen frei gewaehlter Name)
  kind "note": body = Markdown-Text, rev = Zaehler (steigt bei jedem Speichern; wer gleichzeitig schreibt, ueberschreibt - der letzte Stand gewinnt)

Aenderungen gehen an alle Geraete als WebSocket-Nachricht `notebook_event` (payload.op: created | renamed | deleted | message | message_deleted | note).
Der Chatverlauf gehoert zum Programm, nicht zur Show: er bleibt beim Laden einer anderen Show erhalten.
"""
from __future__ import annotations

import json
import os
import re
import threading
import time
import urllib.parse
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body
from fastapi.responses import JSONResponse, Response

from app import paths as _paths

router = APIRouter(prefix="/api/notebook", tags=["notebook"], include_in_schema=False)

THREAD_ID = re.compile(r"^[0-9a-f]{16}$")
MAX_THREADS = 300
MAX_MESSAGES = 5000                 # je Chat; darueber fallen die aeltesten weg
MAX_TEXT = 4000                     # Zeichen je Nachricht
MAX_BODY = 100_000                  # Zeichen je Notiz
MAX_TITLE = 80
MAX_NAME = 40
KINDS = ("chat", "note")
_lock = threading.Lock()


class NotebookError(Exception):
    def __init__(self, code: str, message: str, status: int = 400):
        super().__init__(message)
        self.code, self.message, self.status = code, message, status


def _dir():
    directory = _paths.get_data_root() / "notebook"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _path(thread_id: str):
    if not THREAD_ID.match(str(thread_id)):
        raise NotebookError("not_found", "No such chat or note.", 404)
    return _dir() / f"{thread_id}.json"


def clean_name(value: Any) -> str:
    return " ".join(str(value or "").split())[:MAX_NAME]


def clean_title(value: Any) -> str:
    return " ".join(str(value or "").split())[:MAX_TITLE]


def clean_cid(value: Any) -> str:
    return re.sub(r"[^0-9A-Za-z_-]", "", str(value or ""))[:32]


def _load(thread_id: str) -> Dict[str, Any]:
    path = _path(thread_id)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise NotebookError("not_found", "No such chat or note.", 404)
    except (OSError, ValueError):
        raise NotebookError("bad_file", "This file could not be read.", 500)
    if not isinstance(data, dict) or data.get("kind") not in KINDS:
        raise NotebookError("bad_file", "This file could not be read.", 500)
    data.setdefault("messages", [])
    data.setdefault("body", "")
    data.setdefault("rev", 0)
    return data


def _save(thread: Dict[str, Any], touch: bool = True) -> None:
    path = _path(thread["id"])
    if touch:
        thread["updated"] = time.time()
    partial = path.with_suffix(".tmp")
    partial.write_text(json.dumps(thread, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(partial, path)


def _tasks(body: str) -> Dict[str, int]:
    """Anzahl der Aufgaben einer Notiz (`- [ ]` / `- [x]`), fuer die Anzeige "3 von 5 erledigt"."""
    done = len(re.findall(r"^\s*[-*+]\s+\[[xX]\]\s", body, re.M))
    open_ = len(re.findall(r"^\s*[-*+]\s+\[ \]\s", body, re.M))
    return {"done": done, "total": done + open_}


def summary(thread: Dict[str, Any]) -> Dict[str, Any]:
    """Der kurze Eintrag der Liste (ohne Verlauf / Text)."""
    out = {"id": thread["id"], "kind": thread["kind"], "title": thread.get("title") or "", "created": thread.get("created"), "updated": thread.get("updated"), "rev": thread.get("rev", 0)}
    if thread["kind"] == "chat":
        messages = thread.get("messages", [])
        last = messages[-1] if messages else None
        out["count"] = len(messages)
        out["last"] = {"author": last.get("author", ""), "cid": last.get("cid", ""), "text": str(last.get("text", ""))[:120], "ts": last.get("ts")} if last else None
    else:
        body = str(thread.get("body", ""))
        first = next((ln.strip() for ln in body.splitlines() if ln.strip()), "")
        out["snippet"] = re.sub(r"^[#>\-\*\+\s\[\]xX0-9.]+", "", first)[:100] if first else ""
        out["tasks"] = _tasks(body)
    return out


def list_threads() -> List[Dict[str, Any]]:
    out = []
    for path in _dir().glob("*.json"):
        if not THREAD_ID.match(path.stem):
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(data, dict) or data.get("kind") not in KINDS:
            continue
        data["id"] = path.stem
        out.append(summary(data))
    return sorted(out, key=lambda t: t.get("updated") or 0, reverse=True)


def create(kind: str, title: str = "", body: str = "") -> Dict[str, Any]:
    if kind not in KINDS:
        raise NotebookError("bad_kind", "Unknown kind.")
    with _lock:
        if len(list(_dir().glob("*.json"))) >= MAX_THREADS:
            raise NotebookError("limit", f"At most {MAX_THREADS} chats and notes - delete old ones first.")
        now = time.time()
        thread = {"id": uuid.uuid4().hex[:16], "kind": kind, "title": clean_title(title), "created": now, "updated": now, "rev": 0, "version": 1,
                  "messages": [], "body": str(body or "")[:MAX_BODY] if kind == "note" else ""}
        _save(thread)
        return thread


def rename(thread_id: str, title: str) -> Dict[str, Any]:
    with _lock:
        thread = _load(thread_id)
        thread["title"] = clean_title(title)
        _save(thread, touch=False)
        return thread


def delete(thread_id: str) -> None:
    with _lock:
        path = _path(thread_id)
        if not path.exists():
            raise NotebookError("not_found", "No such chat or note.", 404)
        path.unlink()


def add_message(thread_id: str, author: str, cid: str, text: str) -> Dict[str, Any]:
    text = str(text or "").replace("\r\n", "\n").strip("\n")
    if not text.strip():
        raise NotebookError("empty", "The message is empty.")
    if len(text) > MAX_TEXT:
        raise NotebookError("too_long", f"A message can have at most {MAX_TEXT} characters.")
    with _lock:
        thread = _load(thread_id)
        if thread["kind"] != "chat":
            raise NotebookError("not_a_chat", "This is a note, not a chat.")
        message = {"id": uuid.uuid4().hex[:12], "cid": clean_cid(cid), "author": clean_name(author) or "?", "text": text, "ts": time.time()}
        thread["messages"].append(message)
        if len(thread["messages"]) > MAX_MESSAGES:
            thread["messages"] = thread["messages"][-MAX_MESSAGES:]
        _save(thread)
        return {"message": message, "thread": thread}


def delete_message(thread_id: str, message_id: str) -> Dict[str, Any]:
    with _lock:
        thread = _load(thread_id)
        before = len(thread["messages"])
        thread["messages"] = [m for m in thread["messages"] if m.get("id") != message_id]
        if len(thread["messages"]) == before:
            raise NotebookError("not_found", "No such message.", 404)
        _save(thread)
        return thread


def save_body(thread_id: str, body: str, base_rev: Optional[int], strict: bool = False) -> Dict[str, Any]:
    """Notiz speichern. Oberflaeche: wer gleichzeitig schreibt, ueberschreibt (conflict=True meldet es). strict (REST-API): bei abweichendem base_rev wird NICHT gespeichert (Fehler 409)."""
    body = str(body or "").replace("\r\n", "\n")
    if len(body) > MAX_BODY:
        raise NotebookError("too_long", f"A note can have at most {MAX_BODY} characters.")
    with _lock:
        thread = _load(thread_id)
        if thread["kind"] != "note":
            raise NotebookError("not_a_note", "This is a chat, not a note.")
        conflict = base_rev is not None and int(base_rev) != int(thread.get("rev", 0))
        if conflict and strict:
            raise NotebookError("conflict", f"The note has changed since revision {int(base_rev)} (now {int(thread.get('rev', 0))}). Read it again and retry.", 409)
        if body == thread.get("body", ""):
            return {"thread": thread, "conflict": False, "changed": False}
        thread["body"] = body
        thread["rev"] = int(thread.get("rev", 0)) + 1
        _save(thread)
        return {"thread": thread, "conflict": conflict, "changed": True}


def append_body(thread_id: str, text: str) -> Dict[str, Any]:
    """Text ans Ende einer Notiz haengen (in einer eigenen Zeile) - fuer Skripte / Geraete, die nur etwas dazuschreiben (z. B. ein Protokoll)."""
    text = str(text or "").replace("\r\n", "\n").strip("\n")
    if not text.strip():
        raise NotebookError("empty", "There is nothing to add.")
    with _lock:
        thread = _load(thread_id)
        if thread["kind"] != "note":
            raise NotebookError("not_a_note", "This is a chat, not a note.")
        old = str(thread.get("body", ""))
        body = (old.rstrip("\n") + "\n" if old.strip() else "") + text + "\n"
        if len(body) > MAX_BODY:
            raise NotebookError("too_long", f"A note can have at most {MAX_BODY} characters.")
        thread["body"] = body
        thread["rev"] = int(thread.get("rev", 0)) + 1
        _save(thread)
        return thread


# ------------------------------------------------------------------------------------------------------------ Markdown-Export
def display_title(thread: Dict[str, Any]) -> str:
    title = thread.get("title") or ""
    if title:
        return title
    stamp = time.strftime("%Y-%m-%d", time.localtime(thread.get("created") or time.time()))
    return ("Note " if thread.get("kind") == "note" else "Chat ") + stamp


def export_filename(thread: Dict[str, Any]) -> str:
    stem = re.sub(r'[\\/:*?"<>|\x00-\x1f]', "_", display_title(thread)).strip(" .") or "notebook"
    return stem[:80] + ".md"


def export_markdown(thread: Dict[str, Any]) -> str:
    """Eine Notiz (ihr Markdown-Text) oder ein Chat (Verlauf, nach Tagen gegliedert) als Markdown-Datei."""
    title = display_title(thread)
    if thread.get("kind") == "note":
        body = str(thread.get("body", "")).strip("\n")
        first = next((ln for ln in body.splitlines() if ln.strip()), "")
        return (body if re.match(r"^#\s", first) else f"# {title}\n\n{body}").rstrip("\n") + "\n"
    lines = [f"# {title}", ""]
    day = ""
    for message in thread.get("messages", []):
        stamp = time.localtime(float(message.get("ts") or 0))
        key = time.strftime("%Y-%m-%d", stamp)
        if key != day:
            day = key
            lines += [f"## {key}", ""]
        text = str(message.get("text", "")).split("\n")
        lines.append(f"- **{time.strftime('%H:%M', stamp)} {message.get('author', '?')}:** {text[0]}")
        lines += ["  " + ln if ln.strip() else "" for ln in text[1:]]
    return "\n".join(lines).rstrip("\n") + "\n"


# ------------------------------------------------------------------------------------------------------------ Sicherung / Export-Paket
def thread_files() -> List[Any]:
    """Alle Eintrags-Dateien (fuer "Alles sichern")."""
    return sorted(p for p in _dir().glob("*.json") if THREAD_ID.match(p.stem) and p.is_file())


def package_info() -> List[Dict[str, Any]]:
    """Die Eintraege fuer den Export-Dialog der Show: id, Name, Art, Groesse."""
    out = []
    for path in thread_files():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(data, dict) or data.get("kind") not in KINDS:
            continue
        data["id"] = path.stem
        out.append({"id": path.stem, "name": display_title(data), "kind": data["kind"], "size": path.stat().st_size,
                    "count": len(data.get("messages", [])) if data["kind"] == "chat" else 0})
    return sorted(out, key=lambda x: x["name"].lower())


def import_thread(file_stem: str, raw: bytes) -> str:
    """Einen Eintrag aus einer Sicherung / einem Paket einlesen. Gibt "identical" (gibt es schon, gleicher Inhalt), "imported" oder "copy" zurueck.
    Regel wie bei allen Dateien: nie ueberschreiben - Abweichendes unter gleicher Kennung kommt als Kopie mit neuer Kennung dazu."""
    try:
        data = json.loads(raw.decode("utf-8-sig"))
    except (ValueError, UnicodeDecodeError):
        raise NotebookError("bad_file", "Not a valid chat or note file.")
    if not isinstance(data, dict) or data.get("kind") not in KINDS or not THREAD_ID.match(file_stem):
        raise NotebookError("bad_file", "Not a valid chat or note file.")
    now = time.time()
    kind = data["kind"]
    clean = {"id": file_stem, "kind": kind, "title": clean_title(data.get("title")), "created": float(data.get("created") or now), "updated": float(data.get("updated") or now),
             "rev": int(data.get("rev") or 0), "version": 1, "messages": [], "body": ""}
    if kind == "note":
        clean["body"] = str(data.get("body") or "").replace("\r\n", "\n")[:MAX_BODY]
    else:
        for m in (data.get("messages") or [])[-MAX_MESSAGES:]:
            if isinstance(m, dict) and str(m.get("text", "")).strip():
                clean["messages"].append({"id": re.sub(r"[^0-9a-f]", "", str(m.get("id", "")))[:12] or uuid.uuid4().hex[:12], "cid": clean_cid(m.get("cid")),
                                          "author": clean_name(m.get("author")) or "?", "text": str(m.get("text", ""))[:MAX_TEXT], "ts": float(m.get("ts") or now)})
    with _lock:
        path = _path(file_stem)
        status = "imported"
        if path.exists():
            try:
                same = json.loads(path.read_text(encoding="utf-8"))
                if same.get("kind") == kind and same.get("title", "") == clean["title"] and same.get("body", "") == clean["body"] and same.get("messages", []) == clean["messages"]:
                    return "identical"
            except (OSError, ValueError, AttributeError):
                pass
            clean["id"] = uuid.uuid4().hex[:16]
            status = "copy"
        if len(list(_dir().glob("*.json"))) >= MAX_THREADS:
            raise NotebookError("limit", f"At most {MAX_THREADS} chats and notes - delete old ones first.")
        _save(clean, touch=False)
        return status


# ------------------------------------------------------------------------------------------------------------ HTTP
def _srv():
    from app import server
    return server


def _error(exc: NotebookError) -> JSONResponse:
    return JSONResponse({"error": {"code": exc.code, "message": exc.message}}, status_code=exc.status)


async def _announce(op: str, thread: Dict[str, Any], **extra: Any) -> None:
    payload = {"op": op, "id": thread["id"], "thread": summary(thread)}
    payload.update(extra)
    await _srv().event_bus.broadcast({"type": "notebook_event", "payload": payload})


@router.get("")
async def get_list() -> JSONResponse:
    return JSONResponse({"threads": list_threads(), "limits": {"text": MAX_TEXT, "body": MAX_BODY, "title": MAX_TITLE, "name": MAX_NAME}})


@router.post("")
async def post_create(data: Dict[str, Any] = Body(default={})) -> JSONResponse:
    try:
        thread = create(str(data.get("kind", "chat")), str(data.get("title", "")), str(data.get("body", "")))
    except NotebookError as exc:
        return _error(exc)
    await _announce("created", thread, by=clean_cid(data.get("cid")))
    return JSONResponse(thread)


@router.get("/{thread_id}")
async def get_thread(thread_id: str) -> JSONResponse:
    try:
        return JSONResponse(_load(thread_id))
    except NotebookError as exc:
        return _error(exc)


@router.patch("/{thread_id}")
async def patch_thread(thread_id: str, data: Dict[str, Any] = Body(default={})) -> JSONResponse:
    try:
        thread = rename(thread_id, str(data.get("title", "")))
    except NotebookError as exc:
        return _error(exc)
    await _announce("renamed", thread, by=clean_cid(data.get("cid")))
    return JSONResponse(summary(thread))


@router.delete("/{thread_id}")
async def delete_thread(thread_id: str, cid: str = "") -> JSONResponse:
    try:
        delete(thread_id)
    except NotebookError as exc:
        return _error(exc)
    await _srv().event_bus.broadcast({"type": "notebook_event", "payload": {"op": "deleted", "id": thread_id, "by": clean_cid(cid)}})
    return JSONResponse({"ok": True})


@router.post("/{thread_id}/messages")
async def post_message(thread_id: str, data: Dict[str, Any] = Body(default={})) -> JSONResponse:
    try:
        result = add_message(thread_id, str(data.get("author", "")), str(data.get("cid", "")), str(data.get("text", "")))
    except NotebookError as exc:
        return _error(exc)
    await _announce("message", result["thread"], message=result["message"])
    return JSONResponse(result["message"])


@router.delete("/{thread_id}/messages/{message_id}")
async def remove_message(thread_id: str, message_id: str, cid: str = "") -> JSONResponse:
    try:
        thread = delete_message(thread_id, message_id)
    except NotebookError as exc:
        return _error(exc)
    await _announce("message_deleted", thread, message_id=message_id, by=clean_cid(cid))
    return JSONResponse({"ok": True})


@router.put("/{thread_id}/body")
async def put_body(thread_id: str, data: Dict[str, Any] = Body(default={})) -> JSONResponse:
    try:
        base = data.get("base_rev")
        result = save_body(thread_id, str(data.get("body", "")), int(base) if base is not None else None)
    except (NotebookError, ValueError, TypeError) as exc:
        return _error(exc if isinstance(exc, NotebookError) else NotebookError("bad_request", "Invalid request."))
    thread = result["thread"]
    if result["changed"]:
        await _announce("note", thread, body=thread["body"], rev=thread["rev"], by=clean_cid(data.get("cid")), author=clean_name(data.get("author")), conflict=result["conflict"])
    return JSONResponse({"rev": thread["rev"], "conflict": result["conflict"], "changed": result["changed"]})


@router.get("/{thread_id}/export")
async def get_export(thread_id: str) -> Response:
    """Die Notiz bzw. der Chat als Markdown-Datei zum Herunterladen."""
    try:
        thread = _load(thread_id)
    except NotebookError as exc:
        return _error(exc)
    return markdown_response(thread)


def markdown_response(thread: Dict[str, Any]) -> Response:
    name = export_filename(thread)
    fallback = re.sub(r"[^A-Za-z0-9._ -]", "_", name) or "notebook.md"
    return Response(content=export_markdown(thread).encode("utf-8"), media_type="text/markdown; charset=utf-8", headers={
        "Content-Disposition": f"attachment; filename=\"{fallback}\"; filename*=UTF-8''{urllib.parse.quote(name)}", "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})


async def announce_reload() -> None:
    """Nach dem Einlesen einer Sicherung / eines Pakets: alle Geraete laden die Liste neu."""
    await _srv().event_bus.broadcast({"type": "notebook_event", "payload": {"op": "reload"}})


@router.post("/{thread_id}/typing")
async def post_typing(thread_id: str, data: Dict[str, Any] = Body(default={})) -> JSONResponse:
    """"X schreibt gerade ...": wird nicht gespeichert, nur an alle Geraete weitergereicht (der Absender drosselt auf etwa alle 2,5 Sekunden)."""
    try:
        if not _path(thread_id).exists():
            raise NotebookError("not_found", "No such chat or note.", 404)
    except NotebookError as exc:
        return _error(exc)
    await _srv().event_bus.broadcast({"type": "notebook_event", "payload": {"op": "typing", "id": thread_id, "by": clean_cid(data.get("cid")), "author": clean_name(data.get("author")) or "?",
                                                                            "what": "note" if data.get("what") == "note" else "chat"}})
    return JSONResponse({"ok": True})
