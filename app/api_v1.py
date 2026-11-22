# Copyright (C) 2026 Samuel Zenker
# SPDX-License-Identifier: GPL-3.0-or-later
"""
api_v1.py
REST-API von OpenCue (Version 1) unter /api/v1: Daten lesen (Zustand, Show, DMX-Ausgabe, Cues, Timecode) und steuern (Befehle,
Cue-Listen, Blackout/Master, Timecode, Audio, einzelne DMX-/Fixture-Kanaele). Antworten sind JSON. Die Show BEARBEITEN (Cues, Variablen, Effekte, Patch,
Showfiles, Medien) und der Ereignis-Strom stehen in app/api_v1_manage.py und app/api_v1_system.py, Chat und Notizen in app/api_v1_notes.py (gleicher Router, gleiche Anmeldung).

Anmeldung: Token im Kopf "Authorization: Bearer <Token>" (oder "X-API-Key: <Token>"). Tokens werden in den Einstellungen (Kategorie "API", nur an
der Konsole) angelegt, gespeichert wird nur ihr SHA-256-Hash (der Klartext erscheint einmal bei der Erstellung). Jedes Token hat Berechtigungen
(siehe CAPABILITIES); jede Route verlangt genau eine. Von anderen Geraeten ist die API nur erreichbar, wenn "Zugriff aus dem Netzwerk erlauben"
(Remote) an ist - das Token ersetzt dann die Anmeldung per Passwort/Sitzung (siehe Middleware in app/server.py). Es gibt keine neue Bibliothek:
FastAPI liefert Routen, Pruefung und das OpenAPI-Schema; die Dokumentationsseite (/api/v1/docs) kommt ohne Internet aus.

Die Einstellungs-Routen (/api/apikeys*) sind nur an der Konsole selbst erlaubt (nicht von Remote-Geraeten).

Browser-Seiten auf anderen Adressen (CORS): Antworten unter /api/v1 tragen "Access-Control-Allow-Origin: *" und Vorab-Anfragen (OPTIONS) werden beantwortet, solange
der Schalter "Browser-Seiten anderer Adressen erlauben" an ist (Standard). Das ist ungefaehrlich, weil nichts ohne Token geht und keine Cookies im Spiel sind
(die Berechtigung steckt im Kopf "Authorization", den fremde Seiten nicht kennen).
"""
from __future__ import annotations

import asyncio
import collections
import hashlib
import hmac
import json
import logging
import os
import secrets
import threading
import time
import types
import uuid
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional

from fastapi import APIRouter, Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from app import paths as _paths
from app import remote
from app.timecode import format_timecode, parse_timecode_ms
from app.version import APP_NAME, APP_VERSION

logger = logging.getLogger("opencue.api")

API_PREFIX = "/api/v1"
TOKEN_PREFIX = "oc_"
MAX_TOKENS = 50
MAX_NAME = 60
MAX_COMMAND = 500
MAX_BATCH = 100
FAIL_LIMIT = 20                      # fehlgeschlagene Anmeldungen je Adresse ...
FAIL_WINDOW = 60.0                   # ... innerhalb dieser Sekunden fuehren zu einer Sperre fuer den Rest des Fensters (HTTP 429)

# Berechtigungen: (id, Standard fuer neue Tokens). Texte in den Sprachdateien (API_CAP_<ID mit _>, API_CAP_<ID>_DESC).
CAPABILITIES: List[Dict[str, Any]] = [
    {"id": "read.status", "default": True, "group": "read"},       # Zustand, Blackout, Master, Timecode, Auswahl, Version
    {"id": "read.show", "default": True, "group": "read"},         # Scheinwerfer, Gruppen, Variablen, Effekte, Cue-Listen, Cues, Showfiles
    {"id": "read.dmx", "default": True, "group": "read"},          # DMX-Ausgabe (Universen) und Live-Werte der Scheinwerfer
    {"id": "write.command", "default": True, "group": "write"},    # Konsolenbefehle ausfuehren
    {"id": "write.cue", "default": True, "group": "write"},        # Cue-Listen steuern (Go, Back, Cue ausloesen, Fader)
    {"id": "write.timecode", "default": True, "group": "write"},   # Timecode steuern
    {"id": "write.blackout", "default": True, "group": "write"},   # Blackout und Grand Master
    {"id": "write.audio", "default": True, "group": "write"},      # Audio-Quelle und -Einstellungen aendern, Tempo antippen
    {"id": "write.programmer", "default": True, "group": "write"}, # Programmer: Auswahl, Werte, Variablen anwenden, Programmer leeren
    {"id": "write.widgets", "default": True, "group": "write"},    # Buttons, Fader und Toggles der Konsole bedienen (fuehren ihre eingestellten Befehle aus)
    {"id": "read.notes", "default": True, "group": "read"},         # Chats und Notizen lesen (Panel "Chat & Notizen")
    {"id": "write.notes", "default": False, "group": "write"},     # Chats und Notizen schreiben: anlegen, Nachrichten, Notiz aendern / ergaenzen, loeschen
    {"id": "write.dmx", "default": False, "group": "write"},       # einzelne DMX-/Fixture-Kanaele setzen (kritisch: ueberschreibt die Show)
    {"id": "write.show", "default": False, "group": "edit"},       # Cue-Listen und Cues anlegen, aendern, loeschen (Show-Daten)
    {"id": "write.variables", "default": False, "group": "edit"},  # Variablen (Presets) und Variablengruppen
    {"id": "write.effects", "default": False, "group": "edit"},    # Effekte anlegen / aendern / loeschen, auf Scheinwerfern starten und beenden
    {"id": "write.scripts", "default": False, "group": "edit"},    # Effekt-Skripte (Dateien) speichern, pruefen, loeschen
    {"id": "write.patch", "default": False, "group": "edit"},      # Scheinwerfer patchen (anlegen, Adresse, loeschen), Scheinwerfer-Gruppen
    {"id": "write.showfile", "default": False, "group": "edit"},   # Showfiles: neu, laden, speichern, umbenennen, kopieren, loeschen (kritisch: ersetzt die laufende Show)
    {"id": "write.media", "default": False, "group": "edit"},      # Medien (Video / Audio): hochladen, umbenennen, loeschen
    {"id": "write.layout", "default": False, "group": "edit"},     # ein gespeichertes Panel-Layout im Konsolenfenster anzeigen
    {"id": "write.settings", "default": False, "group": "edit"},   # DMX-Ausgaenge (Art-Net, sACN, USB), Standard-Universum, Sprache (kritisch: Netzwerk und Ausgabe)
]
CAPABILITY_IDS = [c["id"] for c in CAPABILITIES]
_OPERATE = ["read.status", "read.show", "read.dmx", "read.notes", "write.notes", "write.cue", "write.timecode", "write.blackout", "write.audio", "write.programmer", "write.widgets"]
PRESETS = {
    "read": ["read.status", "read.show", "read.dmx", "read.notes"],
    "operate": list(_OPERATE),
    "edit": _OPERATE + ["write.show", "write.variables", "write.effects"],
    "full": list(CAPABILITY_IDS),
}


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str, headers: Optional[Dict[str, str]] = None) -> None:
        super().__init__(message)
        self.status, self.code, self.message, self.headers = status, code, message, headers or {}


def _error_response(status: int, code: str, message: str, headers: Optional[Dict[str, str]] = None) -> JSONResponse:
    return JSONResponse({"error": {"code": code, "message": message}}, status_code=status, headers=headers)


# ------------------------------------------------------------------------------------------------------------------ Tokens
STORE_PATH: Optional[Path] = None          # Tests setzen einen eigenen Pfad


def _store_path() -> Path:
    return STORE_PATH if STORE_PATH is not None else _paths.APP_CONFIG_PATH.parent / "api_tokens.json"


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _now() -> float:
    return time.time()


class TokenStore:
    """Tokens und Hauptschalter der API (Datei config/api_tokens.json). Gespeichert wird nur der Hash."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self.enabled = True
        self.cors = True                       # Browser-Seiten anderer Adressen duerfen die API aufrufen (siehe ApiCorsMiddleware)
        self.views = True                      # Status-Ansichten (Bilder / Web-Seiten fuer einfache Geraete, app/api_v1_views.py)
        self.network = False                   # Reichweite: False = nur dieser PC (Standard), True = auch aus dem Netzwerk (braucht zusaetzlich den Fernzugriff)
        self.tokens: List[Dict[str, Any]] = []
        self._loaded_from: Optional[Path] = None
        self._last_touch_save = 0.0

    # ---- Datei
    def _ensure_loaded(self) -> None:
        path = _store_path()
        if self._loaded_from == path:
            return
        self._loaded_from = path
        self.enabled, self.cors, self.network, self.views, self.tokens = True, True, False, True, []
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
        except FileNotFoundError:
            return
        except Exception as exc:
            logger.warning("API-Tokens konnten nicht gelesen werden (%s): %s", path, exc)
            return
        self.enabled = bool(data.get("enabled", True))
        self.cors = bool(data.get("cors", True))
        self.network = bool(data.get("network", False))
        self.views = bool(data.get("views", True))
        for item in data.get("tokens", []):
            if isinstance(item, dict) and isinstance(item.get("hash"), str) and isinstance(item.get("id"), str):
                item["capabilities"] = [c for c in item.get("capabilities", []) if c in CAPABILITY_IDS]
                self.tokens.append(item)

    def _save(self) -> None:
        path = _store_path()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            partial = path.with_suffix(".tmp")
            partial.write_text(json.dumps({"version": 1, "enabled": self.enabled, "cors": self.cors, "network": self.network, "views": self.views, "tokens": self.tokens}, ensure_ascii=False, indent=2), encoding="utf-8")
            os.replace(partial, path)
        except Exception as exc:
            logger.warning("API-Tokens konnten nicht gespeichert werden: %s", exc)

    # ---- Verwaltung
    @staticmethod
    def public(item: Dict[str, Any]) -> Dict[str, Any]:
        """Sicht ohne Hash (fuer die Oberflaeche)."""
        return {"id": item["id"], "name": item.get("name", ""), "hint": item.get("hint", ""), "capabilities": list(item.get("capabilities", [])),
                "enabled": bool(item.get("enabled", True)), "created": item.get("created"), "last_used": item.get("last_used")}

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            self._ensure_loaded()
            return {"enabled": self.enabled, "cors": self.cors, "network": self.network, "views": self.views, "tokens": [self.public(t) for t in self.tokens]}

    def is_enabled(self) -> bool:
        with self._lock:
            self._ensure_loaded()
            return self.enabled

    def set_enabled(self, enabled: bool) -> None:
        with self._lock:
            self._ensure_loaded()
            self.enabled = bool(enabled)
            self._save()

    def is_views(self) -> bool:
        with self._lock:
            self._ensure_loaded()
            return self.views

    def set_views(self, enabled: bool) -> None:
        with self._lock:
            self._ensure_loaded()
            self.views = bool(enabled)
            self._save()

    def is_network(self) -> bool:
        with self._lock:
            self._ensure_loaded()
            return self.network

    def set_network(self, enabled: bool) -> None:
        with self._lock:
            self._ensure_loaded()
            self.network = bool(enabled)
            self._save()

    def is_cors(self) -> bool:
        with self._lock:
            self._ensure_loaded()
            return self.cors

    def set_cors(self, enabled: bool) -> None:
        with self._lock:
            self._ensure_loaded()
            self.cors = bool(enabled)
            self._save()

    @staticmethod
    def _clean_name(name: Any) -> str:
        return " ".join(str(name or "").split())[:MAX_NAME]

    @staticmethod
    def _clean_caps(caps: Any) -> List[str]:
        wanted = {str(c) for c in (caps or [])} if isinstance(caps, (list, tuple, set)) else set()
        return [c for c in CAPABILITY_IDS if c in wanted]

    def create(self, name: Any, capabilities: Any) -> Dict[str, Any]:
        """Legt ein Token an. Gibt {"token": Klartext (nur jetzt), "record": oeffentliche Sicht} zurueck."""
        with self._lock:
            self._ensure_loaded()
            if len(self.tokens) >= MAX_TOKENS:
                raise ApiError(400, "limit", f"At most {MAX_TOKENS} tokens")
            secret = TOKEN_PREFIX + secrets.token_urlsafe(32)
            item = {"id": uuid.uuid4().hex[:12], "name": self._clean_name(name) or "Token", "hash": _hash(secret), "hint": secret[:len(TOKEN_PREFIX) + 4],
                    "capabilities": self._clean_caps(capabilities if capabilities is not None else [c["id"] for c in CAPABILITIES if c["default"]]),
                    "enabled": True, "created": _now(), "last_used": None}
            self.tokens.append(item)
            self._save()
            return {"token": secret, "record": self.public(item)}

    def update(self, token_id: str, name: Any = None, capabilities: Any = None, enabled: Optional[bool] = None) -> Optional[Dict[str, Any]]:
        with self._lock:
            self._ensure_loaded()
            item = next((t for t in self.tokens if t["id"] == token_id), None)
            if item is None:
                return None
            if name is not None:
                item["name"] = self._clean_name(name) or item.get("name", "Token")
            if capabilities is not None:
                item["capabilities"] = self._clean_caps(capabilities)
            if enabled is not None:
                item["enabled"] = bool(enabled)
            self._save()
            return self.public(item)

    def regenerate(self, token_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            self._ensure_loaded()
            item = next((t for t in self.tokens if t["id"] == token_id), None)
            if item is None:
                return None
            secret = TOKEN_PREFIX + secrets.token_urlsafe(32)
            item["hash"], item["hint"], item["last_used"] = _hash(secret), secret[:len(TOKEN_PREFIX) + 4], None
            self._save()
            return {"token": secret, "record": self.public(item)}

    def delete(self, token_id: str) -> bool:
        with self._lock:
            self._ensure_loaded()
            before = len(self.tokens)
            self.tokens = [t for t in self.tokens if t["id"] != token_id]
            if len(self.tokens) != before:
                self._save()
                return True
            return False

    # ---- Pruefung
    def find(self, secret: str) -> Optional[Dict[str, Any]]:
        digest = _hash(secret)
        with self._lock:
            self._ensure_loaded()
            for item in self.tokens:
                if hmac.compare_digest(item["hash"], digest):
                    return item
        return None

    def touch(self, item: Dict[str, Any]) -> None:
        """Merkt sich die letzte Benutzung (hoechstens alle 30 s auf die Platte schreiben)."""
        now = _now()
        item["last_used"] = now
        if now - self._last_touch_save > 30:
            self._last_touch_save = now
            with self._lock:
                self._save()


store = TokenStore()
_failures: Dict[str, Deque[float]] = {}


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "?"


def _check_rate_limit(ip: str) -> None:
    now = time.monotonic()
    window = _failures.get(ip)
    if window:
        while window and now - window[0] > FAIL_WINDOW:
            window.popleft()
        if len(window) >= FAIL_LIMIT:
            retry = max(1, int(FAIL_WINDOW - (now - window[0])))
            raise ApiError(429, "rate_limited", f"Too many failed attempts. Try again in {retry} s.", {"Retry-After": str(retry)})


def _note_failure(ip: str) -> None:
    window = _failures.setdefault(ip, collections.deque())
    window.append(time.monotonic())
    if len(_failures) > 500:                                   # keine unbegrenzte Liste fremder Adressen
        for key in list(_failures)[:100]:
            _failures.pop(key, None)


bearer_scheme = HTTPBearer(auto_error=False, description="OpenCue API token: Authorization: Bearer oc_...")
key_scheme = APIKeyHeader(name="X-API-Key", auto_error=False, description="Alternative to the Bearer header")


def authenticate(ip: str, host: Optional[str], secret: Optional[str]) -> Dict[str, Any]:
    """Prueft Schalter, Reichweite, Sperre und Token (ohne Berechtigung) - fuer HTTP-Routen UND den WebSocket-Strom. Gibt den Token-Eintrag zurueck oder wirft ApiError."""
    _check_rate_limit(ip)
    if not store.is_enabled():
        raise ApiError(403, "api_disabled", "The API is switched off in the OpenCue settings.")
    if not store.is_network() and not remote.is_local(host):
        raise ApiError(403, "api_local_only", "The API only answers on the console computer itself (OpenCue settings -> REST API -> Reach).")
    if not secret:
        _note_failure(ip)
        logger.info("[API] Anmeldung abgelehnt (%s): kein Token mitgeschickt", ip)
        raise ApiError(401, "unauthorized", "Missing token. Send 'Authorization: Bearer <token>'.", {"WWW-Authenticate": "Bearer"})
    secret = secret.strip().strip("\"'")                                  # beim Kopieren mitgenommene Leerzeichen / Anfuehrungszeichen stoeren nicht
    item = store.find(secret)
    if item is None:
        _note_failure(ip)
        logger.info("[API] Anmeldung abgelehnt (%s): Token unbekannt (%d Zeichen, beginnt mit %s...)", ip, len(secret), secret[:7])
        raise ApiError(401, "unauthorized", "Invalid token.", {"WWW-Authenticate": "Bearer"})
    if not item.get("enabled", True):
        raise ApiError(403, "token_disabled", "This token is switched off.")
    return item


def require(capability: str, query_token: bool = False):
    """Abhaengigkeit einer Route: gueltiges, aktives Token mit dieser Berechtigung (sonst 401/403). query_token: das Token darf auch als ?access_token=... kommen
    (nur fuer den Ereignis-Strom: der EventSource des Browsers kann keinen Kopf senden)."""

    async def dependency(request: Request,
                         credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
                         api_key: Optional[str] = Depends(key_scheme)) -> Dict[str, Any]:
        ip = _client_ip(request)
        secret = (credentials.credentials if credentials and credentials.scheme.lower() == "bearer" else None) or api_key
        if not secret and query_token:
            secret = request.query_params.get("access_token") or request.query_params.get("token")
        item = authenticate(ip, request.client.host if request.client else None, secret)
        if capability not in item.get("capabilities", []):
            raise ApiError(403, "forbidden", f"This token does not have the permission '{capability}'.")
        store.touch(item)
        request.state.api_token = item
        return item

    return dependency


# ------------------------------------------------------------------------------------------------------------------ Zugriff auf den Server
def _srv():
    from app import server                                      # erst zur Laufzeit: server.py bindet dieses Modul ein
    return server


def _dummy_socket():
    return types.SimpleNamespace(state=types.SimpleNamespace(cam_group="", is_local=True, cid=None))


async def _message(message_type: str, payload: Dict[str, Any]) -> None:
    """Fuehrt eine Nachricht so aus, als haette sie ein Bedienfenster gesendet (gleicher Weg, gleiche Meldungen an alle Geraete)."""
    await _srv()._process_client_message(_dummy_socket(), message_type, payload)


def _to_hex(color: Dict[str, Any]) -> str:
    return "#%02x%02x%02x" % tuple(max(0, min(255, int(color.get(k, 0)))) for k in ("r", "g", "b"))


def _fixture_type(fx) -> Dict[str, Any]:
    from app import fixture_manager
    try:
        return fixture_manager.get_fixture_type_by_id(fx.fixture_type) or {}
    except Exception:
        return {}


def _group_of() -> Dict[str, str]:
    st = _srv().state
    return {fid: name for name, ids in st.groups.items() for fid in ids}


def _fixture_dict(fx, groups: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    info = _fixture_type(fx)
    groups = groups if groups is not None else _group_of()
    return {
        "id": fx.id, "fid": fx.fid, "name": fx.name, "type": info.get("name") or fx.fixture_type, "manufacturer": info.get("manufacturer", ""),
        "type_id": fx.fixture_type, "mode": fx.mode, "universe": fx.universe, "start_channel": fx.start_channel,
        "end_channel": fx.start_channel + max(1, fx.channel_count) - 1, "channel_count": fx.channel_count,
        "group": groups.get(fx.id), "sort_index": fx.sort_index,
    }


def _live_state(fx, snapshots: Dict[int, List[int]]) -> Dict[str, Any]:
    """Aktueller Zustand (aus dem DMX-Puffer): dimmer/pan/tilt/Strahl-Attribute in %, color als r/g/b (0-255) und hex."""
    from app.dmx_resolve import abstract_from_dmx
    srv = _srv()
    if fx.universe not in snapshots:
        snapshots[fx.universe] = srv.dmx_engine.get_universe_snapshot(fx.universe)
    values = abstract_from_dmx(fx, snapshots[fx.universe], srv.state.effective_master(fx.id)) or {}
    if isinstance(values.get("color"), dict):
        values["color"] = {**values["color"], "hex": _to_hex(values["color"])}
    return values


def _resolve_fixture(ref: str):
    st = _srv().state
    text = str(ref).strip()
    if text in st.fixtures:
        return st.fixtures[text]
    if text.isdigit():
        for fx in st.fixtures.values():
            if fx.fid == int(text):
                return fx
    matches = [fx for fx in st.fixtures.values() if fx.name.strip().lower() == text.lower()]
    if len(matches) == 1:
        return matches[0]
    raise ApiError(404, "not_found", f"No fixture '{text}' (use the fixture number, id or an unambiguous name).")


def _resolve_cuelist(ref: str):
    st = _srv().state
    text = str(ref).strip()
    if text in st.cuelists:
        return st.cuelists[text]
    for cl in st.cuelists.values():
        if cl.name.strip().lower() == text.lower():
            return cl
    raise ApiError(404, "not_found", f"No cue list '{text}' (use its id or name).")


def _cue_by_ref(cuelist, ref: str):
    text = str(ref).strip()
    for cue in cuelist.cues:
        if cue.id == text:
            return cue
    try:
        number = float(text)
    except ValueError:
        raise ApiError(404, "not_found", f"No cue '{text}' in this list (use the cue number or id).")
    for cue in cuelist.cues:
        if abs(cue.number - number) < 1e-9:
            return cue
    raise ApiError(404, "not_found", f"No cue '{text}' in this list.")


def _num(value: float) -> float:
    return int(value) if float(value).is_integer() else value


def _cue_summary(cue, active: bool = False) -> Dict[str, Any]:
    return {
        "id": cue.id, "number": _num(cue.number), "name": cue.name, "active": active,
        "trigger": cue.trigger, "audio": {"source": cue.audio_source, "value": cue.audio_value} if cue.trigger == "audio" else None,
        "midi": {"type": cue.midi_type, "number": cue.midi_number, "channel": cue.midi_channel, "value": cue.midi_value} if cue.trigger == "midi" else None,
        "clock": {"time": cue.clock_time, "days": list(cue.clock_days)} if cue.trigger == "clock" else None, "timecode_ms": cue.timecode_ms, "timecode": format_timecode(cue.timecode_ms) if cue.timecode_ms is not None else None,
        "fade": cue.fade, "delay": cue.delay,
        "times": {"color": {"fade": cue.fade_color, "delay": cue.delay_color}, "position": {"fade": cue.fade_pos, "delay": cue.delay_pos},
                  "beam": {"fade": cue.fade_beam, "delay": cue.delay_beam}, "zoom": {"fade": cue.fade_zoom, "delay": cue.delay_zoom}},
        "effect_fade": {"in": cue.fx_fade_in, "out": cue.fx_fade_out},
        "play_mode": cue.play_mode, "has_absolute": bool(cue.absolute),
        "mib": cue.mib, "command": cue.cmd, "fixture_count": len(cue.fixture_values),
    }


def _cue_detail(cue, active: bool = False) -> Dict[str, Any]:
    """Was der Cue aendert: je Scheinwerfer feste Werte, Verweise auf Variablen (Platzhalter) und Effekte."""
    st = _srv().state
    changes: List[Dict[str, Any]] = []
    for fixture_id, spec in cue.fixture_values.items():
        fx = st.fixtures.get(fixture_id)
        if fx is None:
            continue
        spec = spec or {}
        refs = dict(spec.get("refs") or {})
        if spec.get("preset_uuid"):                              # aelteres Format: ein Verweis auf eine Variable
            preset = st.presets.get(spec["preset_uuid"])
            if preset is not None:
                refs.setdefault(preset.type, spec["preset_uuid"])
        variables = {kind: (st.presets[pid].name if pid in st.presets else None) for kind, pid in refs.items()}
        values = dict(spec.get("values") or {})
        if isinstance(values.get("color"), dict):
            values["color"] = {**values["color"], "hex": _to_hex(values["color"])}
        changes.append({"fixture_id": fixture_id, "fid": fx.fid, "name": fx.name, "values": values, "variables": variables})
    effects = []
    for fixture_id, by_category in (cue.fx or {}).items():
        fx = st.fixtures.get(fixture_id)
        if fx is None:
            continue
        effects.append({"fixture_id": fixture_id, "fid": fx.fid, "name": fx.name,
                        "effects": {cat: (st.fx_effects.get(fx_id) or {}).get("name", fx_id) for cat, fx_id in by_category.items()}})
    detail = _cue_summary(cue, active)
    detail["changes"] = sorted(changes, key=lambda c: c["fid"])
    detail["effects"] = sorted(effects, key=lambda c: c["fid"])
    return detail


def _universes() -> List[int]:
    """Universen mit Ausgabe: die schon angelegten Puffer und alle, in denen Scheinwerfer gepatcht sind."""
    srv = _srv()
    return sorted(set(srv.dmx_engine.universe_numbers()) | {fx.universe for fx in srv.state.fixtures.values()})


def _dmx_universe(universe: int) -> List[int]:
    return list(_srv().dmx_engine.get_universe_snapshot(universe))


def _timecode_dict() -> Dict[str, Any]:
    state = _srv().timecode.state()
    return {"running": state["running"], "direction": state["direction"], "rate": state["rate"], "position_ms": state["position_ms"],
            "position": format_timecode(state["position_ms"])}


async def _run_command(text: str, log: bool = True) -> Dict[str, Any]:
    srv = _srv()
    text = str(text or "").strip()
    if not text or len(text) > MAX_COMMAND or any(ord(c) < 32 for c in text):
        raise ApiError(400, "bad_request", f"The command must be 1 to {MAX_COMMAND} characters of text.")
    result = await srv.execute_command(text, srv._broadcast_generic)
    if log:
        await srv._broadcast_command_log(text, result)
    return {"command": text, "success": bool(result.get("success")), "message": str(result.get("message", ""))}


def _quoted(name: str) -> str:
    if '"' in name:
        raise ApiError(400, "bad_request", "The cue list name contains a quotation mark; use the active list or rename it.")
    return f'"{name}"'


# ------------------------------------------------------------------------------------------------------------------ Anfragen (Koerper)
class CommandBody(BaseModel):
    command: str = Field(..., description="Console command, e.g. 'Fixture 1 Thru 4 At 80' (see the command reference).", examples=["Fixture 1 At Full"])
    log: bool = Field(True, description="Show the command in the command history of the console.")


class CommandsBody(BaseModel):
    commands: List[str] = Field(..., description=f"Up to {MAX_BATCH} commands, executed one after the other.")
    stop_on_error: bool = Field(False, description="Stop after the first command that fails.")
    log: bool = True


class BlackoutBody(BaseModel):
    enabled: Optional[bool] = Field(None, description="true / false; leave out to toggle.")


class MasterBody(BaseModel):
    value: float = Field(..., ge=0, le=100, description="Grand master in percent.")


class CueGoBody(BaseModel):
    cue: Optional[str] = Field(None, description="Cue number (or id) to jump to; leave out for the next cue.")


class FaderBody(BaseModel):
    value: float = Field(..., ge=0, le=100, description="Fader of the cue list (mix between manual values and the cue) in percent.")


class TimecodeBody(BaseModel):
    action: str = Field(..., description="play | pause | stop | seek | rate")
    position: Optional[Any] = Field(None, description="Seconds (number) or text such as '1:04.300' / '00:00:04.300' (for seek, or to start play from there).")
    direction: Optional[int] = Field(None, description="1 forward (default), -1 backward (play).")
    rate: Optional[float] = Field(None, description="Speed 0.1 ... 8 (action rate).")


class AudioBody(BaseModel):
    running: Optional[bool] = Field(None, description="true opens the source, false closes it. Leave out to keep it as it is (unless `device` is sent).")
    device: Optional[str] = Field(None, description="Input id from GET /audio/devices (or 'demo' for the demo beat). Opens that source, unless `running` is false.")
    settings: Optional[Dict[str, Any]] = Field(None, description="Settings to change: gain, auto_gain, sensitivity, smoothing, latency_ms, mode ('auto' | 'manual'), bpm (manual tempo 30-300), phase_follow, demo_bpm, autostart. Unknown keys are ignored, numbers are limited to their range.")


class ChannelBody(BaseModel):
    value: Optional[int] = Field(None, ge=0, le=255, description="DMX value 0-255.")
    percent: Optional[float] = Field(None, ge=0, le=100, description="Alternative: percent of the channel (0-100).")


class DmxBatchBody(BaseModel):
    channels: Dict[str, int] = Field(..., description="Channel number (1-512) -> value 0-255, e.g. {\"1\": 255, \"2\": 0}.")


# ------------------------------------------------------------------------------------------------------------------ Routen
router = APIRouter(prefix=API_PREFIX, tags=["OpenCue API v1"])


def _route(path: str, capability: str, summary: str, method: str = "get", query_token: bool = False, **kw):
    """Route mit genau einer Berechtigung; die Berechtigung steht im OpenAPI-Schema (x-capability)."""
    decorator = getattr(router, method)
    extra = {"x-capability": capability, **kw.pop("openapi_extra", {})}
    return decorator(path, dependencies=[Depends(require(capability, query_token))], summary=summary,
                     openapi_extra=extra, response_model=None, **kw)


@router.get("", summary="API index", response_model=None, openapi_extra={"x-capability": "read.status"})
async def index(token: Dict[str, Any] = Depends(require("read.status"))) -> Dict[str, Any]:
    """Names the API, the OpenCue version, the documentation and what this token may do."""
    return {"name": f"{APP_NAME} REST API", "api_version": 1, "app_version": APP_VERSION, "documentation": f"{API_PREFIX}/docs", "openapi": f"{API_PREFIX}/openapi.json",
            "websocket": f"{API_PREFIX}/ws", "token": {"name": token.get("name"), "capabilities": token.get("capabilities", [])},
            "capabilities": {c["id"]: c["id"] in token.get("capabilities", []) for c in CAPABILITIES}}


# ---- Zustand
@_route("/status", "read.status", "Overall state")
async def status() -> Dict[str, Any]:
    """Show name, blackout, grand master, timecode, selection, active cue list and the DMX outputs."""
    srv = _srv()
    st = srv.state
    active = st.cuelists.get(st.active_cuelist_id) if st.active_cuelist_id else None
    return {
        "app": {"name": APP_NAME, "version": APP_VERSION},
        "show": {"name": st.showfile_name, "unsaved_changes": bool(st.is_dirty)},
        "blackout": bool(st.blackout), "grand_master": st.grand_master,
        "timecode": _timecode_dict(),
        "selection": {"fixture_ids": list(st.selected_fixture_ids), "fids": [st.fixtures[i].fid for i in st.selected_fixture_ids if i in st.fixtures]},
        "active_cuelist": {"id": active.id, "name": active.name} if active else None,
        "dmx": {"universes": _universes(), "artnet": bool(st.artnet_enabled), "sacn": bool(st.sacn_enabled), "usb": bool(st.enttec_enabled)},
        "counts": {"fixtures": len(st.fixtures), "groups": len(st.groups), "variables": len(st.presets), "effects": len(st.fx_effects),
                   "cuelists": len(st.cuelists), "cues": sum(len(cl.cues) for cl in st.cuelists.values())},
    }


@_route("/blackout", "read.status", "Blackout state")
async def get_blackout() -> Dict[str, Any]:
    return {"enabled": bool(_srv().state.blackout)}


@_route("/master", "read.status", "Grand master")
async def get_master() -> Dict[str, Any]:
    st = _srv().state
    return {"value": st.grand_master, "effective": st.effective_master("")}


@_route("/timecode", "read.status", "Timecode state")
async def get_timecode() -> Dict[str, Any]:
    """Running, direction, speed and position of the global timecode."""
    return _timecode_dict()


def _audio_payload() -> Dict[str, Any]:
    from app.audio_engine import audio_engine
    values = audio_engine.values()
    return {
        "running": audio_engine.running, "device": audio_engine.device_name, "error": audio_engine.error, "mode": audio_engine.config.get("mode"),
        "active": bool(values["a_active"]), "level": values["a_level"], "bass": values["a_bass"], "mid": values["a_mid"], "high": values["a_high"],
        "bands": [values[f"a_b{i}"] for i in range(1, 9)],
        "kick": values["a_kick"], "snare": values["a_snare"], "hat": values["a_hat"], "beat": values["a_beat"],
        "beat_phase": values["a_beat_phase"], "beat_count": int(values["a_beat_count"]), "bpm": values["a_bpm"], "confidence": values["a_conf"],
        "settings": dict(audio_engine.config),
    }


@_route("/audio", "read.status", "Audio analysis")
async def get_audio() -> Dict[str, Any]:
    """The live audio analysis: is a source running, level, the eight frequency bands, kick / snare / hi-hat impulses, tempo (BPM), beat position and the settings.
    All values 0-1 except `bpm` and `beat_count`; without a running source everything is 0."""
    return _audio_payload()


@_route("/audio/devices", "read.status", "Audio inputs")
async def get_audio_devices() -> Dict[str, Any]:
    """Every input Windows knows (system sound = loopback, microphones / line in) plus the built-in demo beat. Use an `id` as `device` in PUT /audio."""
    from app.audio_engine import list_devices
    return {"devices": await asyncio.to_thread(list_devices)}


@_route("/selection", "read.status", "Selected fixtures")
async def get_selection() -> Dict[str, Any]:
    st = _srv().state
    return {"fixtures": [{"id": i, "fid": st.fixtures[i].fid, "name": st.fixtures[i].name} for i in st.selected_fixture_ids if i in st.fixtures]}


# ---- Show
@_route("/fixtures", "read.show", "List fixtures")
async def list_fixtures(universe: Optional[int] = None, group: Optional[str] = None, include_state: bool = False) -> Dict[str, Any]:
    """All fixtures of the show (sorted by number). `include_state=true` adds the current values (dimmer %, colour, pan/tilt ...)."""
    st = _srv().state
    groups = _group_of()
    snapshots: Dict[int, List[int]] = {}
    items = []
    for fx in sorted(st.fixtures.values(), key=lambda f: (f.fid if f.fid else 1e9, f.start_channel)):
        if universe is not None and fx.universe != universe:
            continue
        if group is not None and (groups.get(fx.id) or "").lower() != group.lower():
            continue
        item = _fixture_dict(fx, groups)
        if include_state:
            item["state"] = _live_state(fx, snapshots)
        items.append(item)
    return {"count": len(items), "fixtures": items}


@_route("/fixtures/state", "read.dmx", "Current state of all fixtures")
async def fixtures_state() -> Dict[str, Any]:
    """Per fixture the values the console currently outputs (read from the DMX buffer): dimmer/pan/tilt/zoom ... in %, colour as r/g/b (0-255) and hex."""
    st = _srv().state
    snapshots: Dict[int, List[int]] = {}
    return {"fixtures": [{"id": fx.id, "fid": fx.fid, "name": fx.name, "state": _live_state(fx, snapshots)}
                         for fx in sorted(st.fixtures.values(), key=lambda f: (f.fid if f.fid else 1e9, f.start_channel))]}


@_route("/fixtures/{ref}", "read.show", "One fixture with its channels")
async def get_fixture(ref: str) -> Dict[str, Any]:
    """`ref` is the fixture number (FID), its id or an unambiguous name. Includes every channel with address and current DMX value, and the current state."""
    from app.dmx_resolve import fixture_channel_offsets
    srv = _srv()
    fx = _resolve_fixture(ref)
    snapshots: Dict[int, List[int]] = {}
    item = _fixture_dict(fx)
    buf = srv.dmx_engine.get_universe_snapshot(fx.universe)
    snapshots[fx.universe] = buf
    channels = []
    for name, offset in sorted(fixture_channel_offsets(fx).items(), key=lambda kv: kv[1]):
        index = fx.start_channel - 1 + offset
        channels.append({"channel": offset + 1, "name": name, "address": fx.start_channel + offset, "value": buf[index] if 0 <= index < len(buf) else None})
    item["channels"] = channels
    item["state"] = _live_state(fx, snapshots)
    return item


@_route("/groups", "read.show", "List fixture groups")
async def list_groups() -> Dict[str, Any]:
    st = _srv().state
    return {"groups": [{"name": name, "fixture_ids": list(ids), "fids": [st.fixtures[i].fid for i in ids if i in st.fixtures]} for name, ids in st.groups.items()]}


@_route("/variables", "read.show", "List variables (presets)")
async def list_variables() -> Dict[str, Any]:
    st = _srv().state
    return {"variables": [{"id": p.id, "name": p.name, "type": p.type, "group": p.group, "values": p.values} for p in st.presets.values()]}


@_route("/effects", "read.show", "List effects")
async def list_effects() -> Dict[str, Any]:
    st = _srv().state
    return {"effects": [{"id": key, "name": fx.get("name", key), "group": fx.get("group", ""), "script": fx.get("kind", ""), "params": fx.get("params", {})}
                        for key, fx in st.fx_effects.items()]}


@_route("/showfiles", "read.show", "Saved showfiles")
async def list_showfiles() -> Dict[str, Any]:
    """Names of the showfiles on this computer and the one that is loaded (loading shows is not part of the API)."""
    srv = _srv()
    folder = _paths.SHOWFILES_DIR
    items = []
    try:
        for path in sorted(folder.glob("*.json"), key=lambda p: p.stem.lower()):
            items.append({"name": path.stem, "modified": int(path.stat().st_mtime), "size": path.stat().st_size})
    except OSError:
        pass
    return {"loaded": srv.state.showfile_name, "showfiles": items}


def _cuelist_summary(cl, active_id: Optional[str], playback: Dict[str, Any]) -> Dict[str, Any]:
    st = _srv().state
    cue_id = st.active_cue_ids.get(cl.id)
    cue = next((c for c in cl.cues if c.id == cue_id), None)
    pb = playback.get(cl.id) or {}
    return {"id": cl.id, "name": cl.name, "cue_count": len(cl.cues), "is_active_list": cl.id == active_id,
            "active_cue": {"id": cue.id, "number": _num(cue.number), "name": cue.name} if cue else None,
            "fader": st.cuelist_master(cl.id), "playback": {"state": pb.get("state"), "progress": pb.get("progress")} if pb else None}


@_route("/cuelists", "read.show", "List cue lists")
async def list_cuelists() -> Dict[str, Any]:
    srv = _srv()
    st = srv.state
    playback = srv.cue_engine.playback_snapshot()
    return {"active": st.active_cuelist_id, "cuelists": [_cuelist_summary(cl, st.active_cuelist_id, playback) for cl in st.cuelists.values()]}


@_route("/cuelists/{ref}", "read.show", "One cue list with all its cues")
async def get_cuelist(ref: str) -> Dict[str, Any]:
    """`ref` is the cue list id or name. The cues are sorted by number (timing, trigger, command, number of fixtures)."""
    srv = _srv()
    st = srv.state
    cl = _resolve_cuelist(ref)
    active_cue = st.active_cue_ids.get(cl.id)
    item = _cuelist_summary(cl, st.active_cuelist_id, srv.cue_engine.playback_snapshot())
    item["cues"] = [_cue_summary(c, c.id == active_cue) for c in sorted(cl.cues, key=lambda c: c.number)]
    return item


@_route("/cuelists/{ref}/cues", "read.show", "Cues of a list")
async def list_cues(ref: str, detail: bool = False) -> Dict[str, Any]:
    """`detail=true` includes for every cue what it changes (values, variables, effects per fixture)."""
    st = _srv().state
    cl = _resolve_cuelist(ref)
    active_cue = st.active_cue_ids.get(cl.id)
    build = _cue_detail if detail else _cue_summary
    return {"cuelist": {"id": cl.id, "name": cl.name}, "cues": [build(c, c.id == active_cue) for c in sorted(cl.cues, key=lambda c: c.number)]}


@_route("/cuelists/{ref}/cues/{cue}", "read.show", "One cue in detail")
async def get_cue(ref: str, cue: str) -> Dict[str, Any]:
    """`cue` is the cue number (e.g. 1.5) or id. Shows the timing, trigger, command and for each fixture the values, variables and effects the cue sets."""
    st = _srv().state
    cl = _resolve_cuelist(ref)
    found = _cue_by_ref(cl, cue)
    result = _cue_detail(found, st.active_cue_ids.get(cl.id) == found.id)
    result["cuelist"] = {"id": cl.id, "name": cl.name}
    return result


# ---- DMX
@_route("/dmx", "read.dmx", "DMX universes")
async def list_universes() -> Dict[str, Any]:
    """The universes the console outputs and how many channels of each are not zero."""
    return {"universes": [{"universe": u, "nonzero_channels": sum(1 for v in _dmx_universe(u) if v)} for u in _universes()]}


@_route("/dmx/{universe}", "read.dmx", "DMX values of a universe")
async def get_universe(universe: int, first: int = 1, last: int = 512, nonzero: bool = False) -> Dict[str, Any]:
    """The current DMX output of the universe: `values` is the list for the channels `first` ... `last` (default 1-512). `nonzero=true` returns only channels that are not zero as a map."""
    if not (1 <= first <= last <= 512):
        raise ApiError(400, "bad_request", "first and last must satisfy 1 <= first <= last <= 512.")
    values = _dmx_universe(universe)
    window = values[first - 1:last]
    if nonzero:
        return {"universe": universe, "first": first, "last": last, "channels": {str(first + i): v for i, v in enumerate(window) if v}}
    return {"universe": universe, "first": first, "last": last, "values": window}


@_route("/midi", "read.status", "MIDI devices and state")
async def get_midi() -> Dict[str, Any]:
    """MIDI: the devices that are connected (and whether OpenCue reads them), the outputs, how many mappings are active and the measured MIDI Timecode / MIDI clock tempo. Send MIDI with the command `Midi Note 60` etc. (POST /command)."""
    from app.midi_engine import midi
    return await asyncio.to_thread(midi.refresh_ports)


# ---- Steuern
@_route("/command", "write.command", "Run a console command", method="post")
async def post_command(body: CommandBody) -> Dict[str, Any]:
    """Runs one command exactly like the command line (also `a; b` chains). The result says whether it worked; a rejected command changes nothing."""
    return await _run_command(body.command, body.log)


@_route("/commands", "write.command", "Run several console commands", method="post")
async def post_commands(body: CommandsBody) -> Dict[str, Any]:
    if not body.commands or len(body.commands) > MAX_BATCH:
        raise ApiError(400, "bad_request", f"Send 1 to {MAX_BATCH} commands.")
    results = []
    for text in body.commands:
        result = await _run_command(text, body.log)
        results.append(result)
        if body.stop_on_error and not result["success"]:
            break
    return {"success": all(r["success"] for r in results), "executed": len(results), "results": results}


@_route("/blackout", "write.blackout", "Switch blackout", method="put")
async def put_blackout(body: BlackoutBody) -> Dict[str, Any]:
    srv = _srv()
    await srv.set_blackout(body.enabled, srv._broadcast_generic)
    return {"enabled": bool(srv.state.blackout)}


@_route("/master", "write.blackout", "Set the grand master", method="put")
async def put_master(body: MasterBody) -> Dict[str, Any]:
    result = await _run_command(f"Master {body.value:g}", log=False)
    if not result["success"]:
        raise ApiError(400, "rejected", result["message"])
    return {"value": _srv().state.grand_master}


async def _cue_command(ref: str, suffix: str) -> Dict[str, Any]:
    cl = _resolve_cuelist(ref)
    result = await _run_command(f"Cuelist {_quoted(cl.name)} {suffix}")
    return {"cuelist": {"id": cl.id, "name": cl.name}, **result}


@_route("/cuelists/{ref}/go", "write.cue", "Go (next cue or jump to a cue)", method="post")
async def cuelist_go(ref: str, body: Optional[CueGoBody] = None) -> Dict[str, Any]:
    """Without a body: the next cue (wraps around at the end). With `cue`: jump to that cue with its own fade time."""
    if body and body.cue not in (None, ""):
        cl = _resolve_cuelist(ref)
        cue = _cue_by_ref(cl, str(body.cue))
        return await _cue_command(ref, f"Go Cue {_num(cue.number)}")
    return await _cue_command(ref, "Go")


@_route("/cuelists/{ref}/back", "write.cue", "Back (previous cue)", method="post")
async def cuelist_back(ref: str) -> Dict[str, Any]:
    return await _cue_command(ref, "Back")


@_route("/cuelists/{ref}/pause", "write.cue", "Pause the running fade", method="post")
async def cuelist_pause(ref: str) -> Dict[str, Any]:
    return await _cue_command(ref, "Pause")


@_route("/cuelists/{ref}/resume", "write.cue", "Resume a paused fade", method="post")
async def cuelist_resume(ref: str) -> Dict[str, Any]:
    return await _cue_command(ref, "Resume")


@_route("/cuelists/{ref}/stop", "write.cue", "Stop (abort the fade, end effects)", method="post")
async def cuelist_stop(ref: str) -> Dict[str, Any]:
    return await _cue_command(ref, "Stop")


@_route("/cuelists/{ref}/fader", "write.cue", "Set the fader of a cue list", method="put")
async def cuelist_fader(ref: str, body: FaderBody) -> Dict[str, Any]:
    return await _cue_command(ref, f"Fader {body.value:g}")


@_route("/timecode", "write.timecode", "Control the timecode", method="put")
async def put_timecode(body: TimecodeBody) -> Dict[str, Any]:
    """`action`: play (optionally from `position`, with `direction`), pause, stop (back to 0), seek (`position`), rate (`rate` 0.1-8). Seeking does not fire timecode cues."""
    action = body.action.strip().lower()
    position_ms: Optional[int] = None
    if body.position is not None and body.position != "":
        if isinstance(body.position, (int, float)) and not isinstance(body.position, bool):
            position_ms = int(round(float(body.position) * 1000))
        else:
            position_ms = parse_timecode_ms(body.position)
        if position_ms is None or position_ms < 0:
            raise ApiError(400, "bad_request", "position must be seconds or a time such as '1:04.300' (at most 100 hours).")
    if action == "play":
        payload: Dict[str, Any] = {"direction": -1 if (body.direction or 1) < 0 else 1}
        if position_ms is not None:
            payload["position_ms"] = position_ms
        await _message("timecode_play", payload)
    elif action == "pause":
        await _message("timecode_pause", {})
    elif action == "stop":
        await _message("timecode_stop", {})
    elif action == "seek":
        if position_ms is None:
            raise ApiError(400, "bad_request", "seek needs a position.")
        await _message("timecode_seek", {"position_ms": position_ms})
    elif action == "rate":
        if body.rate is None:
            raise ApiError(400, "bad_request", "rate needs a rate.")
        await _message("timecode_rate", {"rate": body.rate})
    else:
        raise ApiError(400, "bad_request", "action must be play, pause, stop, seek or rate.")
    return _timecode_dict()


@_route("/audio", "write.audio", "Open / close the audio source, change its settings", method="put")
async def put_audio(body: AudioBody) -> Dict[str, Any]:
    """Settings are applied first, then the source is opened (`running` true, or a `device`) or closed (`running` false). Returns the same as GET /audio.
    If the source cannot be opened the answer is 409 with the reason."""
    from app import audio_routes
    from app.audio_engine import audio_engine
    if body.settings:
        audio_engine.configure(body.settings)
    if body.running is False:
        await asyncio.to_thread(audio_engine.stop)
        audio_engine.configure({"autostart": False})
    elif body.running is True or body.device is not None:
        device = body.device.strip() if body.device is not None else None
        if device is not None and not device:
            raise ApiError(400, "bad_request", "device must not be empty.")
        ok = await asyncio.to_thread(audio_engine.start, device)
        if not ok:
            await audio_routes._announce()
            raise ApiError(409, "audio_failed", audio_engine.error or "The audio source could not be opened.")
        audio_engine.configure({"autostart": True})
    await audio_routes._announce()
    return _audio_payload()


@_route("/audio/tap", "write.audio", "Tap the tempo", method="post")
async def post_audio_tap() -> Dict[str, Any]:
    """One tap of the tempo button: after a few taps the tempo (BPM) is taken from them and the audio tempo switches to manual. Returns the audio state with the tapped `tap_bpm` (null until there are enough taps)."""
    from app import audio_routes
    from app.audio_engine import audio_engine
    bpm = audio_engine.tap()
    await audio_routes._announce()
    return {**_audio_payload(), "tap_bpm": bpm}


async def _set_raw(universe: int, channel: int, value: int) -> Dict[str, Any]:
    """Ein DMX-Kanal: gehoert er einem Scheinwerfer, geht er den Weg des "DMX direkt"-Faders (Programmer), sonst direkt in den Puffer."""
    srv = _srv()
    owner = next((fx for fx in srv.state.fixtures.values() if fx.universe == universe and fx.start_channel <= channel < fx.start_channel + max(1, fx.channel_count)), None)
    if owner is not None:
        await _message("set_fixture_raw_channel", {"ids": [owner.id], "channel_offset": channel - owner.start_channel, "value": value})
    else:
        srv.dmx_engine.commit_batch(universe, {channel: value})
        await srv.event_bus.broadcast({"type": "dmx_universe_changed", "payload": {"universe": universe, "values": srv.dmx_engine.get_universe_snapshot(universe)}})
    return {"universe": universe, "channel": channel, "value": value, "fixture": {"fid": owner.fid, "name": owner.name} if owner else None}


def _check_address(universe: int, channel: int) -> None:
    if not (1 <= universe <= 63999) or not (1 <= channel <= 512):
        raise ApiError(400, "bad_request", "Universe must be 1-63999 and channel 1-512.")


@_route("/dmx/{universe}/{channel}", "write.dmx", "Set one DMX channel", method="put")
async def put_dmx_channel(universe: int, channel: int, body: ChannelBody) -> Dict[str, Any]:
    """Sets one DMX channel (0-255 or percent). A channel that belongs to a fixture is set like the 'DMX direct' fader of the programmer (a manual value that cues no longer mix); other channels are written straight to the output."""
    _check_address(universe, channel)
    value = body.value if body.value is not None else (int(round(body.percent * 255 / 100)) if body.percent is not None else None)
    if value is None:
        raise ApiError(400, "bad_request", "Send 'value' (0-255) or 'percent' (0-100).")
    return await _set_raw(universe, channel, value)


@_route("/dmx/{universe}", "write.dmx", "Set several DMX channels", method="put")
async def put_dmx_batch(universe: int, body: DmxBatchBody) -> Dict[str, Any]:
    if not body.channels or len(body.channels) > 512:
        raise ApiError(400, "bad_request", "Send 1 to 512 channels.")
    parsed = {}
    for key, value in body.channels.items():
        try:
            channel = int(key)
        except ValueError:
            raise ApiError(400, "bad_request", f"'{key}' is not a channel number.")
        _check_address(universe, channel)
        if not (0 <= int(value) <= 255):
            raise ApiError(400, "bad_request", "Values must be 0-255.")
        parsed[channel] = int(value)
    results = [await _set_raw(universe, channel, value) for channel, value in sorted(parsed.items())]
    return {"universe": universe, "set": len(results), "results": results}


@_route("/fixtures/{ref}/channels/{channel}", "write.dmx", "Set one channel of a fixture", method="put")
async def put_fixture_channel(ref: str, channel: str, body: ChannelBody) -> Dict[str, Any]:
    """`channel` is the channel number of the fixture (1 = first channel, as in 'CH6') or its channel name (e.g. 'Dimmer'). Same effect as the 'DMX direct' fader."""
    from app.dmx_resolve import fixture_channel_offsets
    fx = _resolve_fixture(ref)
    offsets = fixture_channel_offsets(fx)
    if channel.strip().isdigit():
        offset = int(channel) - 1
        if offset < 0 or offset >= max(1, fx.channel_count):
            raise ApiError(404, "not_found", f"The fixture has the channels 1 to {fx.channel_count}.")
    else:
        found = [off for name, off in offsets.items() if name.lower() == channel.strip().lower()]
        if len(found) != 1:
            raise ApiError(404, "not_found", f"No channel '{channel}' (names: {', '.join(sorted(offsets, key=offsets.get))}).")
        offset = found[0]
    value = body.value if body.value is not None else (int(round(body.percent * 255 / 100)) if body.percent is not None else None)
    if value is None:
        raise ApiError(400, "bad_request", "Send 'value' (0-255) or 'percent' (0-100).")
    result = await _set_raw(fx.universe, fx.start_channel + offset, value)
    result["channel_of_fixture"] = offset + 1
    return result


# ------------------------------------------------------------------------------------------------------------------ Browser-Seiten anderer Adressen (CORS)
CORS_METHODS = "GET, POST, PUT, DELETE, OPTIONS"
CORS_HEADERS = "Authorization, Content-Type, X-API-Key"


class ApiCorsMiddleware:
    """Erlaubt Browser-Seiten auf anderen Adressen den Zugriff auf /api/v1 (Schalter im Token-Store). Reiner ASGI-Baustein, ganz aussen (vor der
    Anmeldepruefung des Servers), damit auch Fehlerantworten (401, 403, 429) fuer die Seite lesbar sind und die Vorab-Anfrage (OPTIONS, ohne Token) durchkommt.
    Es gibt nie "Allow-Credentials": Cookies sind nicht im Spiel, die Berechtigung ist allein das Token im Kopf."""

    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        path = scope.get("path", "") if scope.get("type") == "http" else ""
        if not (path == API_PREFIX or path.startswith(API_PREFIX + "/")):
            await self.app(scope, receive, send)
            return
        headers = {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope.get("headers", [])}
        if "origin" not in headers or not store.is_cors():
            await self.app(scope, receive, send)
            return
        extra = [(b"access-control-allow-origin", b"*"), (b"access-control-expose-headers", b"Retry-After, WWW-Authenticate"), (b"vary", b"Origin")]
        if scope.get("method") == "OPTIONS" and "access-control-request-method" in headers:
            wanted = headers.get("access-control-request-headers", "")
            allow = [(b"access-control-allow-methods", CORS_METHODS.encode()), (b"access-control-allow-headers", (wanted or CORS_HEADERS).encode("latin-1", "ignore")),
                     (b"access-control-max-age", b"600")]
            if headers.get("access-control-request-private-network", "").lower() == "true":
                allow.append((b"access-control-allow-private-network", b"true"))
            await send({"type": "http.response.start", "status": 204, "headers": extra + allow + [(b"content-length", b"0")]})
            await send({"type": "http.response.body", "body": b""})
            return

        async def send_with_cors(message) -> None:
            if message["type"] == "http.response.start":
                message = {**message, "headers": list(message.get("headers", [])) + extra}
            await send(message)

        await self.app(scope, receive, send_with_cors)


# ------------------------------------------------------------------------------------------------------------------ Dokumentation (ohne Internet)
_schema_cache: Dict[str, Any] = {}


def build_openapi() -> Dict[str, Any]:
    """OpenAPI-Beschreibung nur der API-Routen (aus einer eigenen kleinen App, damit nichts anderes aus dem Server darin auftaucht)."""
    if not _schema_cache:
        sub = FastAPI(title=f"{APP_NAME} REST API", version=str(APP_VERSION), docs_url=None, redoc_url=None, openapi_url=None,
                      description=("Read the state of the console, control it and edit the show (cue lists, cues, variables, effects, patch, showfiles, media). JSON in, JSON out. Live changes: GET /events (Server-Sent Events); hardware and fast control: the WebSocket /api/v1/ws (see the page /api/v1/docs). Create a token under Settings -> API (on the console) and send it as "
                                   "`Authorization: Bearer <token>`. Every route needs one permission (shown as `x-capability`); a token without it gets HTTP 403. "
                                   "Errors look like `{\"error\": {\"code\": ..., \"message\": ...}}`."))
        sub.include_router(router)
        _schema_cache.update(sub.openapi())
    return _schema_cache


DOCS_HTML = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>OpenCue REST API</title>
<style>
:root{--bg:#101012;--panel:#18181b;--line:#2c2c31;--text:#e7e7ea;--dim:#9a9aa3;--accent:#ffb000;--get:#3fa7ff;--post:#3ecf8e;--put:#ffb000;--del:#ff6b6b}
@media (prefers-color-scheme:light){:root{--bg:#f6f6f7;--panel:#fff;--line:#d9d9de;--text:#1a1a1d;--dim:#5c5c66;--accent:#a86a00}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:15px/1.5 system-ui,Segoe UI,Roboto,sans-serif}
main{max-width:60rem;margin:0 auto;padding:1.5rem 1rem 4rem}h1{margin:.2rem 0}h2{margin:2rem 0 .6rem;font-size:1.05rem;border-bottom:1px solid var(--line);padding-bottom:.3rem}
p,li{color:var(--dim)}code,pre{font-family:ui-monospace,Consolas,monospace;font-size:.88em}pre{background:var(--panel);border:1px solid var(--line);border-radius:6px;padding:.7rem;overflow:auto;color:var(--text)}
.ep{background:var(--panel);border:1px solid var(--line);border-radius:6px;margin:.5rem 0}.ep summary{cursor:pointer;padding:.55rem .7rem;display:flex;gap:.6rem;align-items:baseline;flex-wrap:wrap}
.m{font-weight:700;min-width:3.4rem}.GET{color:var(--get)}.POST{color:var(--post)}.PUT{color:var(--put)}.DELETE{color:var(--del)}
.cap{margin-left:auto;font-size:.78rem;color:var(--dim);border:1px solid var(--line);border-radius:1rem;padding:0 .5rem}.body{padding:0 .8rem .8rem;color:var(--text)}
table{border-collapse:collapse;width:100%;margin:.4rem 0}td,th{border-top:1px solid var(--line);padding:.25rem .4rem;text-align:left;font-size:.88rem;vertical-align:top}th{color:var(--dim);font-weight:600}
</style></head><body><main><h1>OpenCue REST API</h1><p id="intro">Loading ...</p>
<h2>Authentication</h2><p>Create a token in OpenCue under <b>Settings &rarr; API</b> (on the console). Send it with every request:</p>
<pre>curl -H "Authorization: Bearer oc_xxxxxxxx" http://127.0.0.1:8000/api/v1/status</pre>
<p>From another device the API is reachable when <i>Allow access from the network</i> (Remote) is switched on; then use the console's address. Each token has permissions; a request without the needed one gets <code>403</code>, a missing or wrong token <code>401</code>.</p>
<h2>WebSocket <code>/api/v1/ws</code> (hardware, fast control)</h2>
<p>One open connection, JSON text frames, the same token and permissions. Log in with <code>?access_token=&lt;token&gt;</code>, the <code>Authorization</code> header or a first message <code>{"op":"auth","token":"oc_..."}</code> (within 5 s). An optional <code>"id"</code> in a message comes back in the <code>ack</code> / <code>error</code> answer. Targets: <code>fixtures</code> (list), <code>fixture</code>, <code>group</code>, <code>selection: true</code>.</p>
<table><tr><th>op</th><th>Permission</th><th>Fields</th></tr>
<tr><td><code>joystick</code></td><td>write.programmer</td><td><code>x</code>, <code>y</code> (-1..1), targets, <code>mode</code> rate (default: deflection = speed, exponential, integrated by the server at 40 Hz) | position (absolute), <code>axes</code> {"x":"pan","y":"tilt"}, <code>stick</code>, <code>speed</code>, <code>deadzone</code>, <code>timeout_ms</code> (dead-man, default 500), <code>release</code></td></tr>
<tr><td><code>set</code></td><td>write.programmer</td><td>targets, <code>values</code> {dimmer, pan, tilt, color, ... (percent)}, <code>mode</code> absolute | relative (percent points added)</td></tr>
<tr><td><code>select</code></td><td>write.programmer</td><td>targets, <code>mode</code> set | add | remove | clear</td></tr>
<tr><td><code>cmd</code></td><td>write.command</td><td><code>line</code></td></tr>
<tr><td><code>cue</code></td><td>write.cue</td><td><code>list</code>, <code>action</code> go | back | pause | resume | stop | fader, <code>cue</code>, <code>value</code></td></tr>
<tr><td><code>master</code> / <code>blackout</code></td><td>write.blackout</td><td><code>value</code> / <code>on</code></td></tr>
<tr><td><code>dmx</code></td><td>write.dmx</td><td><code>universe</code>, <code>channels</code> {"1":255}</td></tr>
<tr><td><code>tap</code></td><td>write.audio</td><td>tap the tempo</td></tr>
<tr><td><code>timecode</code></td><td>write.timecode</td><td><code>action</code> play | pause | stop | seek | rate | <b>sync</b> (follow an outside clock: <code>position</code> ms or "0:12.345", <code>running</code>)</td></tr>
<tr><td><code>audio_in</code></td><td>write.audio</td><td><code>rate</code> 8000-48000, <code>open</code>; then binary frames: PCM s16le mono, analysed as audio source "network"</td></tr>
<tr><td><code>subscribe</code> / <code>unsubscribe</code></td><td>read.status (audio, events), read.dmx (dmx, fixtures)</td><td><code>topic</code> audio | dmx | fixtures | events | timecode, <code>hz</code> (1-60), audio: <code>keys</code>; dmx: <code>universes</code>; events: <code>events</code></td></tr>
<tr><td><code>ping</code></td><td>-</td><td><code>t</code> is echoed in <code>pong</code> with <code>server_ms</code></td></tr></table>
<p>Answers: <code>hello</code>, <code>ack</code>, <code>error</code> (<code>code</code>, <code>message</code>), <code>pong</code>, <code>joystick</code> (<code>state: timeout</code>), and the pushed <code>audio</code>, <code>dmx</code> (<code>full</code> / <code>changes</code>), <code>fixtures</code>, <code>event</code>. Limits: 300 messages/s, 10 connections. Full guide with an ESP32 sketch: the help page "REST API", section 10.</p>
<h2>Status views (read-only images and pages for simple devices)</h2>
<p><code>GET /api/v1/views</code> lists them; <code>/api/v1/views/{status|timecode|dmx|cue|audio}</code> is a self-updating web page, <code>.png</code> / <code>.bmp</code> / <code>.rgb565</code> (raw 16 bit pixels for a TFT) / <code>.json</code> the same content as an image or model. Parameters: <code>w</code>, <code>h</code> (pixels), <code>theme</code> dark | light, <code>refresh</code> (seconds), <code>universe</code> (dmx), <code>list</code> (cue). Browsers: <code>?access_token=&lt;token&gt;</code>. Permission Status (dmx view: DMX). Help page "REST API", section 11.</p>
<div id="list"></div></main>
<script>
fetch('openapi.json').then(r=>r.json()).then(spec=>{
 document.getElementById('intro').textContent=(spec.info&&spec.info.description)||'';
 const rows=[];for(const [path,ops] of Object.entries(spec.paths||{}))for(const [method,op] of Object.entries(ops))rows.push({path,method,op});
 const groups={};const order=['status','showfile','system','programmer','selection','fixtures','fixture-types','groups','variables','variable-groups','effects','effect-groups','effect-scripts','cuelists','showfiles','media','layouts','dmx','blackout','master','timecode','audio','events','command','commands'];
 rows.forEach(r=>{const key=(r.path.split('/')[3]||'index');(groups[key]=groups[key]||[]).push(r)});
 const keys=Object.keys(groups).sort((a,b)=>(order.indexOf(a)<0?99:order.indexOf(a))-(order.indexOf(b)<0?99:order.indexOf(b)));
 const root=document.getElementById('list');
 const esc=s=>String(s==null?'':s).replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
 keys.forEach(k=>{const h=document.createElement('h2');h.textContent='/'+k;root.appendChild(h);
  groups[k].sort((a,b)=>a.path.localeCompare(b.path)).forEach(({path,method,op})=>{
   const d=document.createElement('details');d.className='ep';
   const params=(op.parameters||[]).filter(p=>p.in==='query'||p.in==='path');
   let body='';if(op.description)body+='<p>'+esc(op.description)+'</p>';
   if(params.length)body+='<table><tr><th>Parameter</th><th>In</th><th>Type</th><th></th></tr>'+params.map(p=>'<tr><td><code>'+esc(p.name)+'</code></td><td>'+esc(p.in)+'</td><td>'+esc((p.schema&&(p.schema.type||'')))+'</td><td>'+esc(p.description||'')+'</td></tr>').join('')+'</table>';
   const rb=op.requestBody&&op.requestBody.content&&op.requestBody.content['application/json'];
   if(rb){const ref=(rb.schema&&rb.schema.$ref||'').split('/').pop();const sc=(spec.components&&spec.components.schemas||{})[ref]||rb.schema||{};
    body+='<p>JSON body:</p><table><tr><th>Field</th><th>Type</th><th></th></tr>'+Object.entries(sc.properties||{}).map(([n,p])=>'<tr><td><code>'+esc(n)+((sc.required||[]).includes(n)?'*':'')+'</code></td><td>'+esc(p.type||(p.anyOf?p.anyOf.map(x=>x.type).filter(Boolean).join(' | '):''))+'</td><td>'+esc(p.description||'')+'</td></tr>').join('')+'</table>';}
   d.innerHTML='<summary><span class="m '+method.toUpperCase()+'">'+method.toUpperCase()+'</span><code>'+esc(path)+'</code><span>'+esc(op.summary||'')+'</span><span class="cap">'+esc(op['x-capability']||'')+'</span></summary><div class="body">'+body+'</div>';
   root.appendChild(d)});});
}).catch(e=>{document.getElementById('intro').textContent='Could not load the description: '+e});
</script></body></html>"""


@router.get("/docs", include_in_schema=False)
async def docs_page() -> HTMLResponse:
    """Documentation page (works offline, no token needed: it contains no show data)."""
    return HTMLResponse(DOCS_HTML)


@router.get("/openapi.json", include_in_schema=False)
async def openapi_json() -> JSONResponse:
    return JSONResponse(build_openapi())


# ------------------------------------------------------------------------------------------------------------------ Einstellungen (nur Konsole)
admin = APIRouter(prefix="/api/apikeys", tags=["settings"], include_in_schema=False)


def _local_only(request: Request) -> None:
    """Frueher nur am Hauptrechner; jetzt darf jedes angemeldete Geraet die Zugangsschluessel verwalten (Server-Betrieb ohne Fenster). Der Name bleibt, damit die Aufrufe unveraendert sind."""
    return None


class TokenCreateBody(BaseModel):
    name: str = ""
    capabilities: Optional[List[str]] = None


class TokenUpdateBody(BaseModel):
    name: Optional[str] = None
    capabilities: Optional[List[str]] = None
    enabled: Optional[bool] = None


class EnabledBody(BaseModel):
    enabled: bool


@admin.get("")
async def admin_list(request: Request) -> Dict[str, Any]:
    _local_only(request)
    data = store.snapshot()
    data["capabilities"] = CAPABILITIES
    data["presets"] = PRESETS
    return data


@admin.post("/enabled")
async def admin_enabled(request: Request, body: EnabledBody) -> Dict[str, Any]:
    _local_only(request)
    store.set_enabled(body.enabled)
    return store.snapshot()


@admin.post("/network")
async def admin_network(request: Request, body: EnabledBody) -> Dict[str, Any]:
    _local_only(request)
    store.set_network(body.enabled)
    return store.snapshot()


@admin.post("/views")
async def admin_views(request: Request, body: EnabledBody) -> Dict[str, Any]:
    _local_only(request)
    store.set_views(body.enabled)
    return store.snapshot()


@admin.get("/connections")
async def admin_connections(request: Request) -> Dict[str, Any]:
    """Wer ist gerade ueber den WebSocket verbunden (Einstellungen -> REST-API, "Verbunden")? Nur an der Konsole."""
    _local_only(request)
    from app import api_v1_stream
    return api_v1_stream.connections_info()


@admin.post("/connections/{conn_id}/close")
async def admin_connection_close(request: Request, conn_id: str) -> Dict[str, Any]:
    _local_only(request)
    from app import api_v1_stream
    return {"closed": await api_v1_stream.close_connection(conn_id)}


@admin.post("/cors")
async def admin_cors(request: Request, body: EnabledBody) -> Dict[str, Any]:
    _local_only(request)
    store.set_cors(body.enabled)
    return store.snapshot()


class ApplyBody(BaseModel):
    """Alles, was in den Einstellungen als Entwurf gesammelt wurde - wird mit "Speichern" auf einmal uebernommen."""
    enabled: Optional[bool] = None
    cors: Optional[bool] = None
    network: Optional[bool] = None
    views: Optional[bool] = None
    create: List[Dict[str, Any]] = []              # [{"temp_id", "name", "capabilities", "enabled"}]
    update: List[Dict[str, Any]] = []              # [{"id", "name"?, "capabilities"?, "enabled"?}]
    regenerate: List[str] = []
    delete: List[str] = []


@admin.post("/apply")
async def admin_apply(request: Request, body: ApplyBody) -> Dict[str, Any]:
    """Uebernimmt die gesammelten Aenderungen: Schalter, neue / geaenderte / neu erzeugte / geloeschte Tokens. Die Klartext-Tokens neuer und neu erzeugter Tokens
    stehen NUR in dieser Antwort (`secrets`)."""
    _local_only(request)
    secrets_out: List[Dict[str, Any]] = []
    if body.enabled is not None:
        store.set_enabled(body.enabled)
    if body.cors is not None:
        store.set_cors(body.cors)
    if body.network is not None:
        store.set_network(body.network)
    if body.views is not None:
        store.set_views(body.views)
    for token_id in body.delete:
        store.delete(str(token_id))
    for item in body.update:
        if isinstance(item, dict) and item.get("id"):
            store.update(str(item["id"]), item.get("name"), item.get("capabilities"), item.get("enabled"))
    for token_id in body.regenerate:
        made = store.regenerate(str(token_id))
        if made is not None:
            secrets_out.append({"id": made["record"]["id"], "name": made["record"]["name"], "token": made["token"], "kind": "regenerated"})
    for item in body.create:
        made = store.create(item.get("name"), item.get("capabilities"))
        if item.get("enabled") is False:
            store.update(made["record"]["id"], enabled=False)
        secrets_out.append({"temp_id": item.get("temp_id"), "id": made["record"]["id"], "name": made["record"]["name"], "token": made["token"], "kind": "created"})
    return {"snapshot": store.snapshot(), "secrets": secrets_out}


@admin.post("")
async def admin_create(request: Request, body: TokenCreateBody) -> Dict[str, Any]:
    _local_only(request)
    return store.create(body.name, body.capabilities)


@admin.put("/{token_id}")
async def admin_update(request: Request, token_id: str, body: TokenUpdateBody) -> Dict[str, Any]:
    _local_only(request)
    record = store.update(token_id, body.name, body.capabilities, body.enabled)
    if record is None:
        raise ApiError(404, "not_found", "No such token.")
    return {"record": record}


@admin.post("/{token_id}/regenerate")
async def admin_regenerate(request: Request, token_id: str) -> Dict[str, Any]:
    _local_only(request)
    result = store.regenerate(token_id)
    if result is None:
        raise ApiError(404, "not_found", "No such token.")
    return result


@admin.delete("/{token_id}")
async def admin_delete(request: Request, token_id: str) -> Dict[str, Any]:
    _local_only(request)
    if not store.delete(token_id):
        raise ApiError(404, "not_found", "No such token.")
    return {"ok": True}


# ------------------------------------------------------------------------------------------------------------------ Weitere Routen (eigene Module, gleicher Router)
from app import api_v1_manage  # noqa: E402,F401  (Show bearbeiten: Cue-Listen, Cues, Variablen, Effekte, Skripte)
from app import api_v1_system  # noqa: E402,F401  (Programmer, Patch, Showfiles, Ereignis-Strom)
from app import api_v1_views  # noqa: E402,F401  (Status-Ansichten fuer einfache Geraete: Bild / Web-Seite)
from app import api_v1_notes  # noqa: E402,F401  (Chat und Notizen: /notebook)
from app import api_v1_stream  # noqa: E402,F401  (WebSocket-Strom /ws: Joystick, schnelle Werte, Audio rein / raus, DMX- und Live-Werte)


# ------------------------------------------------------------------------------------------------------------------ Einbinden
def install(app: FastAPI) -> None:
    """Routen und Fehlerbehandlung am FastAPI-Objekt anmelden (von server.py aufgerufen)."""
    app.include_router(router)
    app.include_router(admin)

    @app.exception_handler(ApiError)
    async def _api_error(request: Request, exc: ApiError):
        if request.url.path.startswith(API_PREFIX + "/views/"):                               # Ansichten: Fehler als Bild / Seite (siehe api_v1_views.error_response)
            shown = api_v1_views.error_response(request, exc.status, exc.code, exc.message, exc.headers)
            if shown is not None:
                return shown
        return _error_response(exc.status, exc.code, exc.message, exc.headers)

    previous = app.exception_handlers.get(RequestValidationError)

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError):
        if request.url.path.startswith(API_PREFIX) or request.url.path.startswith("/api/apikeys"):
            errors = exc.errors()
            first = errors[0] if errors else {}
            where = ".".join(str(p) for p in first.get("loc", []) if p not in ("body", "query", "path"))
            message = (where + ": " if where else "") + str(first.get("msg", "Invalid request"))
            return _error_response(422, "invalid", message)
        if previous is not None:
            return await previous(request, exc)
        from fastapi.exception_handlers import request_validation_exception_handler
        return await request_validation_exception_handler(request, exc)
