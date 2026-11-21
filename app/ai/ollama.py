# Copyright (C) 2026 Samuel Zenker
# SPDX-License-Identifier: GPL-3.0-or-later
"""Schmale Huelle um die HTTP-Schnittstelle von Ollama (synchron; wird aus Threads benutzt). Nur urllib, keine zusaetzliche Bibliothek."""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional, Tuple

from app.ai.config import clean_base_url
from app.ai.errors import AiError


class OllamaClient:
    def __init__(self, base_url: str, api_key: str = "", timeout: float = 180.0) -> None:
        self.base = clean_base_url(base_url)
        self.api_key = api_key
        self.timeout = timeout
        self._opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))      # ein lokaler / LAN-Server wird nie ueber einen Proxy gerufen

    def _request(self, method: str, path: str, body: Optional[Dict[str, Any]] = None, timeout: Optional[float] = None):
        headers = {"Accept": "application/json"}
        data = None
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        if self.api_key:
            headers["Authorization"] = "Bearer " + self.api_key
        request = urllib.request.Request(self.base + path, data=data, headers=headers, method=method)
        try:
            return self._opener.open(request, timeout=timeout or self.timeout)
        except urllib.error.HTTPError as exc:
            text = ""
            try:
                text = exc.read().decode("utf-8", "replace")
                text = json.loads(text).get("error", text)
            except Exception:
                pass
            if exc.code in (401, 403):
                raise AiError("unauthorized", "The server refused the key (HTTP %d). Check the key in the settings." % exc.code, 401)
            if exc.code == 404 and "model" in str(text).lower():
                raise AiError("model_missing", str(text), 404)
            raise AiError("http_error", str(text) or ("HTTP %d" % exc.code), exc.code)
        except urllib.error.URLError as exc:
            raise AiError("not_reachable", "Cannot reach %s (%s). Is Ollama running and the address right?" % (self.base, getattr(exc, "reason", exc)), 502)
        except (TimeoutError, OSError) as exc:
            raise AiError("timeout", "No answer from %s in time (%s)." % (self.base, exc), 504)

    def _json(self, method: str, path: str, body: Optional[Dict[str, Any]] = None, timeout: Optional[float] = None) -> Dict[str, Any]:
        with self._request(method, path, body, timeout) as response:
            try:
                return json.loads(response.read().decode("utf-8", "replace") or "{}")
            except ValueError:
                raise AiError("bad_answer", "The server did not answer like Ollama.", 502)

    def version(self) -> str:
        return str(self._json("GET", "/api/version", timeout=8).get("version", ""))

    def tags(self) -> List[Dict[str, Any]]:
        return list(self._json("GET", "/api/tags", timeout=15).get("models") or [])

    def show(self, model: str) -> Dict[str, Any]:
        return self._json("POST", "/api/show", {"model": model}, timeout=15)

    def chat_once(self, payload: Dict[str, Any], timeout: Optional[float] = None) -> Dict[str, Any]:
        """Eine Anfrage ohne Streaming (kleine Hilfsaufgaben wie der Chat-Titel)."""
        return self._json("POST", "/api/chat", {**payload, "stream": False}, timeout)

    def open_chat(self, payload: Dict[str, Any]):
        """Oeffnet eine gestreamte Chat-Anfrage; die Antwort besteht aus einer JSON-Zeile je Stueck."""
        return self._request("POST", "/api/chat", payload)


_can_chat_cache: Dict[Tuple[str, str, str], Tuple[float, Optional[bool]]] = {}


def can_chat(client: OllamaClient, name: str, digest: str = "") -> Optional[bool]:
    """Kann das Modell Text erzeugen? True / False nach Auskunft des Servers, None wenn er es nicht sagt (aeltere Ollama-Versionen).
    Reine Embedding-Modelle koennen es nicht und sind fuer den Chat unbrauchbar."""
    key = (client.base, name, digest)
    hit = _can_chat_cache.get(key)
    if hit and time.time() - hit[0] < 300:
        return hit[1]
    value: Optional[bool] = None
    try:
        caps = client.show(name).get("capabilities")
        if isinstance(caps, list):
            value = "completion" in caps
    except AiError:
        value = None
    _can_chat_cache[key] = (time.time(), value)
    return value


_caps_cache: Dict[Tuple[str, str], Tuple[float, Optional[List[str]]]] = {}


def model_caps(client: OllamaClient, name: str) -> Optional[List[str]]:
    """Die Faehigkeiten eines Modells laut Server ("completion", "tools", "thinking" ...); None, wenn er es nicht sagt (aeltere Ollama-Versionen) oder nicht antwortet."""
    key = (client.base, name)
    hit = _caps_cache.get(key)
    if hit and time.time() - hit[0] < 300:
        return hit[1]
    value: Optional[List[str]] = None
    try:
        caps = client.show(name).get("capabilities")
        if isinstance(caps, list):
            value = [str(c) for c in caps]
    except AiError:
        value = None
    _caps_cache[key] = (time.time(), value)
    return value


def list_models(client: OllamaClient) -> List[Dict[str, Any]]:
    """Die Modelle des Servers, die Text erzeugen koennen. Ob ein Modell Werkzeuge rufen kann, ist fuer den reinen Chat egal."""
    models = client.tags()
    with ThreadPoolExecutor(max_workers=6) as pool:
        chat = list(pool.map(lambda m: can_chat(client, str(m.get("name", "")), str(m.get("digest", ""))), models))
    out: List[Dict[str, Any]] = []
    for item, usable in zip(models, chat):
        if usable is False:
            continue
        details = item.get("details") or {}
        out.append({"name": item.get("name"), "size": item.get("size"), "parameters": details.get("parameter_size"),
                    "family": details.get("family"), "quantization": details.get("quantization_level")})
    return sorted(out, key=lambda m: str(m["name"]).lower())
