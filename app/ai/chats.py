# Copyright (C) 2026 Samuel Zenker
# SPDX-License-Identifier: GPL-3.0-or-later
"""Gespraeche ("Chats") als Dateien: ein Chat = eine JSON-Datei `<id>.json` (id: 16 Hex-Zeichen) im Ordner "chats" des Datenverzeichnisses. Geschrieben wird atomar."""
from __future__ import annotations

import json
import os
import re
import time
import uuid
from typing import Any, Dict, List

from app import paths as _paths
from app.ai.errors import AiError

MAX_CHATS = 500
CHAT_ID = re.compile(r"^[0-9a-f]{16}$")


def chats_dir():
    directory = _paths.get_data_root() / "chats"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


class ChatStore:
    @staticmethod
    def _path(chat_id: str):
        if not CHAT_ID.match(str(chat_id)):
            raise AiError("not_found", "No such chat.", 404)
        return chats_dir() / f"{chat_id}.json"

    def load(self, chat_id: str) -> Dict[str, Any]:
        path = self._path(chat_id)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            raise AiError("not_found", "No such chat.", 404)
        except (OSError, ValueError):
            raise AiError("bad_chat", "This chat file could not be read.", 500)
        if not isinstance(data, dict):
            raise AiError("bad_chat", "This chat file could not be read.", 500)
        data.setdefault("messages", [])
        data.setdefault("mode", "chat")
        return data

    def save(self, chat: Dict[str, Any], touch: bool = True) -> None:
        """`touch` False: die Zeit der letzten Aenderung bleibt (die Liste ist danach sortiert) - fuer reine Markierungen wie "gelesen"."""
        path = self._path(chat["id"])
        if touch:
            chat["updated"] = time.time()
        partial = path.with_suffix(".tmp")
        partial.write_text(json.dumps(chat, ensure_ascii=False, indent=1), encoding="utf-8")
        os.replace(partial, path)

    def create(self, model: str = "", title: str = "", mode: str = "chat") -> Dict[str, Any]:
        if len(self.list()) >= MAX_CHATS:
            raise AiError("limit", f"At most {MAX_CHATS} chats - delete old ones first.")
        now = time.time()
        chat = {"id": uuid.uuid4().hex[:16], "title": title.strip()[:80], "auto_title": not title.strip(), "created": now, "updated": now,
                "model": model, "mode": mode, "messages": [], "version": 2}
        self.save(chat)
        return chat

    def duplicate(self, chat_id: str, title: str = "") -> Dict[str, Any]:
        """Eine Kopie mit allen Nachrichten (neue Nummer, Titel `title` oder der alte mit Zusatz)."""
        if len(self.list()) >= MAX_CHATS:
            raise AiError("limit", f"At most {MAX_CHATS} chats - delete old ones first.")
        chat = self.load(chat_id)
        now = time.time()
        name = " ".join(str(title or "").split())[:80] or ((chat.get("title") or "Chat") + " (copy)")[:80]
        chat.update({"id": uuid.uuid4().hex[:16], "title": name, "auto_title": False, "created": now, "updated": now})
        self.save(chat)
        return chat

    def delete(self, chat_id: str) -> None:
        path = self._path(chat_id)
        if not path.exists():
            raise AiError("not_found", "No such chat.", 404)
        path.unlink()

    def list(self) -> List[Dict[str, Any]]:
        out = []
        for path in chats_dir().glob("*.json"):
            if not CHAT_ID.match(path.stem):
                continue
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if not isinstance(data, dict):
                continue
            out.append({"id": path.stem, "title": data.get("title") or "", "created": data.get("created"), "updated": data.get("updated"),
                        "model": data.get("model") or "", "mode": data.get("mode") or "chat", "unread": bool(data.get("unread")),
                        "messages": sum(1 for m in data.get("messages", []) if m.get("role") in ("user", "assistant") and m.get("content"))})
        return sorted(out, key=lambda c: c.get("updated") or 0, reverse=True)
