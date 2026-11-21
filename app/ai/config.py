# Copyright (C) 2026 Samuel Zenker
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Einstellungen des KI-Assistenten (stehen in der app_config.json unter "ai", nicht in der Show).

Bewusst klein: Server, Modell und ein paar Zahlen. Unbekannte Schluessel (auch alte aus frueheren Staenden) werden beim Pruefen verworfen.
"""
from __future__ import annotations

import json
import re
import urllib.parse
from typing import Any, Dict, Optional

from app.ai.errors import AiError

DEFAULTS: Dict[str, Any] = {
    "enabled": False,                          # der Assistent ist standardmaessig aus
    "provider": "ollama",
    "base_url": "http://127.0.0.1:11434",
    "api_key": "",                             # optional: "Authorization: Bearer <Schluessel>" (z. B. hinter einem Proxy)
    "model": "",                               # Standardmodell neuer Chats
    "num_ctx": 16384,                          # Kontextfenster (Tokens), das dem Modell angefordert wird (die Funktionsliste des Arbeitsmodus braucht ~5000 davon; ein 3B-Modell braucht dafuer nur ~0,6 GB mehr Speicher)
    "temperature": 0.3,
    "num_predict": 1200,                       # laengste Antwort (Tokens): schuetzt davor, dass ein kleines Modell endlos weiterschreibt (bei ~17 Tokens/s sonst Minuten)
    "auto_title": True,                        # die KI benennt einen Chat nach der ersten Antwort selbst (solange der Benutzer ihn nicht umbenannt hat)
    "timeout_s": 180,                          # so lange wartet eine Anfrage auf Antwort (das erste Laden eines Modells dauert)
    "keep_alive": "10m",                       # so lange bleibt das Modell im Speicher
    "default_mode": "chat",                    # Modus neuer Chats: "chat" | "guide" | "work"
    "tools_mode": "core",                      # Modus "Arbeiten": "core" = die haeufigen Funktionen sofort, der Rest nach Bedarf | "collections" = alles nach Bedarf | "all" = alle sofort (grosser Prompt)
    "permissions": {"read": "allow", "write": "ask", "critical": "ask"},       # je Klasse von Funktionen: "allow" = immer erlauben | "ask" = fragen | "never" = nie
    "allowed_tools": [],                       # "Immer erlauben" im Chat: diese Funktionen laufen auch bei "fragen" ohne Rueckfrage (nie bei "critical")
}
PERMISSION_VALUES = ("allow", "ask", "never")
PERMISSION_CLASSES = ("read", "write", "critical")
MAX_ALLOWED_TOOLS = 100
TOOL_NAME = re.compile(r"^[A-Za-z0-9_]{1,60}$")
RECOMMENDED_KEYS = ("num_ctx", "temperature", "num_predict", "auto_title", "timeout_s", "keep_alive", "tools_mode")     # "Empfohlene Werte": nur die technischen; Adresse, Modell und Berechtigungen bleiben
LIMITS = {"num_ctx": (1024, 131072), "temperature": (0.0, 2.0), "num_predict": (64, 16384), "timeout_s": (10, 3600)}
KEEP_ALIVE = re.compile(r"^(-1|\d{1,4}[smh])$")


def clean_base_url(value: Any) -> str:
    """Normalisiert die Adresse des Servers ("localhost:11434" -> "http://localhost:11434"); nur http / https, keine Zugangsdaten in der Adresse."""
    text = str(value or "").strip()
    if not text:
        raise AiError("bad_url", "The address is empty.")
    if "://" not in text:
        text = "http://" + text
    parts = urllib.parse.urlsplit(text)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise AiError("bad_url", "The address must start with http:// or https:// and name a computer, e.g. http://127.0.0.1:11434")
    if parts.username or parts.password:
        raise AiError("bad_url", "Do not put a user name or password into the address; use the key field.")
    return urllib.parse.urlunsplit((parts.scheme, parts.netloc, parts.path.rstrip("/"), "", ""))[:200]


def clean_tool_names(value: Any) -> list:
    """Eine Liste von Funktionsnamen ("immer erlaubt"): nur gueltige Namen, ohne Doppelte, hoechstens MAX_ALLOWED_TOOLS."""
    out: list = []
    for item in value if isinstance(value, (list, tuple)) else []:
        name = str(item or "").strip()
        if TOOL_NAME.match(name) and name not in out:
            out.append(name)
    return out[:MAX_ALLOWED_TOOLS]


def clean_config(raw: Any, base: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """`base` (oder die Standardwerte) mit den Angaben aus `raw` ueberschrieben; Zahlen werden auf ihren Bereich begrenzt. Eine ungueltige Adresse: AiError."""
    result = {key: (base or DEFAULTS).get(key, default) for key, default in DEFAULTS.items()}
    result["permissions"] = {k: (result["permissions"].get(k) if result["permissions"].get(k) in PERMISSION_VALUES else DEFAULTS["permissions"][k]) for k in PERMISSION_CLASSES} if isinstance(result.get("permissions"), dict) else dict(DEFAULTS["permissions"])
    result["allowed_tools"] = clean_tool_names(result.get("allowed_tools"))
    if not isinstance(raw, dict):
        return result
    if "enabled" in raw:
        result["enabled"] = raw["enabled"] is True or str(raw["enabled"]).lower() in ("1", "true", "on")
    if "base_url" in raw:
        result["base_url"] = clean_base_url(raw["base_url"])
    if "api_key" in raw:
        result["api_key"] = str(raw["api_key"] or "").strip()[:300]
    if "model" in raw:
        result["model"] = str(raw["model"] or "").strip()[:200]
    if raw.get("default_mode") in ("chat", "guide", "work"):
        result["default_mode"] = raw["default_mode"]
    if "auto_title" in raw:
        result["auto_title"] = raw["auto_title"] is True or str(raw["auto_title"]).lower() in ("1", "true", "on")
    if raw.get("tools_mode") in ("core", "collections", "all"):
        result["tools_mode"] = raw["tools_mode"]
    if isinstance(raw.get("permissions"), dict):
        for key, value in raw["permissions"].items():
            if key in PERMISSION_CLASSES and value in PERMISSION_VALUES:
                result["permissions"][key] = value
    if "allowed_tools" in raw:
        result["allowed_tools"] = clean_tool_names(raw["allowed_tools"])
    if "keep_alive" in raw and KEEP_ALIVE.match(str(raw["keep_alive"]).strip()):
        result["keep_alive"] = str(raw["keep_alive"]).strip()
    for key, (low, high) in LIMITS.items():
        if key in raw:
            try:
                number = float(raw[key])
            except (TypeError, ValueError):
                continue
            if number == number and abs(number) != float("inf"):
                number = max(low, min(high, number))
                result[key] = round(number, 2) if key == "temperature" else int(round(number))
    return result


def public_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Die Einstellungen ohne den Schluessel (nur ob einer gesetzt ist)."""
    return {**{k: v for k, v in config.items() if k != "api_key"}, "has_key": bool(config.get("api_key")), "recommended": {k: DEFAULTS[k] for k in RECOMMENDED_KEYS},
            "defaults": {k: v for k, v in DEFAULTS.items() if k != "api_key"}}


def dump(config: Dict[str, Any]) -> str:
    return json.dumps(config, ensure_ascii=False)
