"""
stream_sources.py
Quellen fuer das Livestream-Panel (Kamera-Streams per URL) und die Weiterleitung (Proxy) durch den Server.

- Eine Quelle ist Ausstattung dieses Computers (wie eine DMX-Schnittstelle), nicht Teil einer Show: sie liegt in
  <Datenordner>/stream_sources.json. Das Panel verweist nur ueber die ID darauf.
- Zugangsdaten gehoeren NIE in eine URL, die zum Browser geht: Chrome blockiert 'http://user:pass@host' fuer Bilder/Videos, und
  Panel-/Layout-Dateien waeren Klartext. Benutzername/Passwort stehen deshalb getrennt in der Quelle; das Passwort wird unter Windows
  mit DPAPI verschluesselt gespeichert (an den Windows-Benutzer gebunden) und verlaesst den Server nie - die Clients bekommen nur
  'hat Passwort'. Eine URL mit eingebetteten Zugangsdaten wird beim Speichern zerlegt.
- Der Proxy holt den Stream mit diesen Zugangsdaten (Basic oder Digest) und reicht ihn weiter: ein Bild-/Videostrom (MJPEG,
  progressives Video), HLS (Playlisten werden umgeschrieben, Segmente nur vom selben Server), und das Signalisieren von WebRTC (WHEP).
  Er holt nur von dem Server der Quelle (gleicher Host und Port, auch nach Weiterleitungen), nur http/https und nie von diesem Programm selbst.
"""
from __future__ import annotations

import base64
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app import paths as _paths

TYPES = ("auto", "mjpeg", "video", "hls", "webrtc")
MAX_SOURCES = 40
CONNECT_TIMEOUT = 10.0
MAX_PLAYLIST_BYTES = 2 * 1024 * 1024
USER_AGENT = "OpenCue-StreamProxy/1.0"


class StreamError(Exception):
    def __init__(self, code: str, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.code, self.message, self.status = code, message, status


def store_path() -> Path:
    return _paths.FIXTURES_DIR.parent / "stream_sources.json"


# ------------------------------------------------------------------------------------------------ Passwort-Schutz
def _protect(text: str) -> str:
    """Passwort verschluesselt (DPAPI) als Base64; ohne Windows: leer (dann wird nichts gespeichert)."""
    if not text:
        return ""
    try:
        from app import fixture_library
        if not fixture_library.remember_available():
            return ""
        return base64.b64encode(fixture_library._dpapi(text.encode("utf-8"), True)).decode("ascii")
    except Exception:
        return ""


def _unprotect(blob: str) -> str:
    if not blob:
        return ""
    try:
        from app import fixture_library
        return fixture_library._dpapi(base64.b64decode(blob), False).decode("utf-8")
    except Exception:
        return ""


def password_storage_available() -> bool:
    try:
        from app import fixture_library
        return fixture_library.remember_available()
    except Exception:
        return False


# ------------------------------------------------------------------------------------------------ Ablage
def _load() -> List[Dict[str, Any]]:
    try:
        data = json.loads(store_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    rows = data.get("sources") if isinstance(data, dict) else None
    return [r for r in (rows or []) if isinstance(r, dict) and re.fullmatch(r"[0-9a-f-]{36}", str(r.get("id", "")))]


def _save(rows: List[Dict[str, Any]]) -> None:
    target = store_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_suffix(".part")
    partial.write_text(json.dumps({"sources": rows}, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(partial, target)


def guess_type(url: str) -> str:
    """Typ aus der Adresse erraten (fuer 'automatisch')."""
    low = url.lower()
    path = urllib.parse.urlsplit(low).path
    if path.endswith(".m3u8") or "m3u8" in low:
        return "hls"
    if "whep" in low:
        return "webrtc"
    if re.search(r"mjpe?g|motion|video\.cgi|videostream|axis-cgi/mjpg|/stream\.mjpg|action=stream", low):
        return "mjpeg"
    return "video"


def effective_type(row: Dict[str, Any]) -> str:
    return guess_type(row["url"]) if row.get("type", "auto") == "auto" else row["type"]


def public(row: Dict[str, Any]) -> Dict[str, Any]:
    """Was die Clients sehen duerfen: nie das Passwort."""
    return {"id": row["id"], "name": row["name"], "url": row["url"], "type": row.get("type", "auto"), "resolved_type": effective_type(row),
            "user": row.get("user", ""), "has_password": bool(row.get("password_enc")) or bool(row.get("_session_password")), "proxy": bool(row.get("proxy", False))}


def public_list() -> List[Dict[str, Any]]:
    return [public(r) for r in _load()]


_session_passwords: Dict[str, str] = {}      # ohne Windows: Passwort nur fuer diese Sitzung im Speicher


def get(source_id: str) -> Optional[Dict[str, Any]]:
    for row in _load():
        if row["id"] == source_id:
            row = dict(row)
            row["password"] = _unprotect(row.get("password_enc", "")) or _session_passwords.get(source_id, "")
            return row
    return None


# ------------------------------------------------------------------------------------------------ URL pruefen
def clean_url(raw: str) -> Tuple[str, str, str]:
    """Pruefen und zerlegen: (url_ohne_zugangsdaten, benutzer_aus_url, passwort_aus_url). Wirft StreamError."""
    text = str(raw or "").strip()
    if not text or len(text) > 2000 or any(ord(c) < 32 for c in text):
        raise StreamError("invalid_url", "Bitte eine Adresse angeben")
    parts = urllib.parse.urlsplit(text)
    scheme = parts.scheme.lower()
    if scheme in ("rtsp", "rtsps", "rtmp", "rtmps"):
        raise StreamError("unsupported_scheme", "RTSP/RTMP kann der Browser nicht abspielen - ein Wandler (z. B. MediaMTX oder go2rtc) macht daraus WebRTC, HLS oder MJPEG")
    if scheme not in ("http", "https") or not parts.hostname:
        raise StreamError("invalid_url", "Die Adresse muss mit http:// oder https:// beginnen")
    user, password = urllib.parse.unquote(parts.username or ""), urllib.parse.unquote(parts.password or "")
    host = parts.hostname if ":" not in parts.hostname else f"[{parts.hostname}]"
    netloc = host + (f":{parts.port}" if parts.port else "")
    return urllib.parse.urlunsplit((scheme, netloc, parts.path, parts.query, "")), user, password


def save(data: Dict[str, Any], own_ports: Tuple[int, ...] = ()) -> Dict[str, Any]:
    """Quelle anlegen oder aendern. password: None/fehlt = unveraendert, '' = entfernen, Text = setzen."""
    name = re.sub(r"\s+", " ", str(data.get("name", "")).strip())[:60]
    if not name:
        raise StreamError("invalid_name", "Bitte einen Namen angeben")
    url, url_user, url_password = clean_url(data.get("url", ""))
    parts = urllib.parse.urlsplit(url)
    if (parts.hostname or "").lower() in ("localhost", "127.0.0.1", "::1") and (parts.port or (443 if parts.scheme == "https" else 80)) in own_ports:
        raise StreamError("self", "Das ist die Adresse dieses Programms selbst")
    kind = str(data.get("type", "auto"))
    if kind not in TYPES:
        raise StreamError("invalid_type", "Unbekannter Typ")
    rows = _load()
    source_id = str(data.get("id") or "")
    existing = next((r for r in rows if r["id"] == source_id), None)
    if existing is None:
        if len(rows) >= MAX_SOURCES:
            raise StreamError("too_many", f"Hoechstens {MAX_SOURCES} Quellen")
        source_id = str(uuid.uuid4())
        existing = {"id": source_id}
        rows.append(existing)
    user = str(data.get("user", "") if data.get("user") is not None else existing.get("user", "")).strip()[:120] or url_user[:120]
    existing.update({"name": name, "url": url, "type": kind, "user": user, "proxy": bool(data.get("proxy", False))})
    password = data.get("password")
    if url_password and password in (None, ""):
        password = url_password
    if password is not None:
        existing["password_enc"] = _protect(str(password)) if password else ""
        if password and not existing["password_enc"]:
            _session_passwords[source_id] = str(password)          # nur Speicher (kein Windows)
        elif not password:
            _session_passwords.pop(source_id, None)
    if (existing.get("password_enc") or _session_passwords.get(source_id)) and not existing.get("proxy"):
        existing["proxy"] = True        # mit Passwort immer ueber den Server: das Passwort darf nie zum Browser
    _save(rows)
    return public(existing)


def delete(source_id: str) -> bool:
    rows = _load()
    kept = [r for r in rows if r["id"] != source_id]
    if len(kept) == len(rows):
        return False
    _session_passwords.pop(source_id, None)
    _save(kept)
    return True


# ------------------------------------------------------------------------------------------------ Verbindung (Proxy)
def same_origin(a: str, b: str) -> bool:
    pa, pb = urllib.parse.urlsplit(a), urllib.parse.urlsplit(b)

    def port(p):
        return p.port or (443 if p.scheme == "https" else 80)
    return pa.scheme == pb.scheme and (pa.hostname or "").lower() == (pb.hostname or "").lower() and port(pa) == port(pb)


class _SameHostRedirect(urllib.request.HTTPRedirectHandler):
    def __init__(self, origin: str) -> None:
        self._origin = origin

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not same_origin(self._origin, newurl):
            raise urllib.error.HTTPError(newurl, 403, "Weiterleitung auf einen anderen Server blockiert", headers, fp)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def open_upstream(row: Dict[str, Any], url: Optional[str] = None, method: str = "GET", body: Optional[bytes] = None,
                  headers: Optional[Dict[str, str]] = None, timeout: float = CONNECT_TIMEOUT):
    """Verbindung zur Kamera mit den gespeicherten Zugangsdaten. url (z. B. ein HLS-Segment) muss vom selben Server wie die Quelle sein."""
    target = url or row["url"]
    if not same_origin(row["url"], target):
        raise StreamError("foreign_host", "Nur Adressen vom Server der Quelle sind erlaubt", 403)
    handlers: List[Any] = [_SameHostRedirect(row["url"])]
    if row.get("user"):
        manager = urllib.request.HTTPPasswordMgrWithDefaultRealm()
        manager.add_password(None, row["url"], row["user"], row.get("password", ""))
        handlers += [urllib.request.HTTPBasicAuthHandler(manager), urllib.request.HTTPDigestAuthHandler(manager)]
    opener = urllib.request.build_opener(*handlers)
    request = urllib.request.Request(target, data=body, method=method, headers={"User-Agent": USER_AGENT, **(headers or {})})
    try:
        return opener.open(request, timeout=timeout)
    except urllib.error.HTTPError as err:
        if err.code in (401, 403):
            raise StreamError("auth", "Die Kamera lehnt die Zugangsdaten ab (Benutzername/Passwort pruefen)", 502)
        if err.code == 404:
            raise StreamError("not_found", "Die Kamera kennt diese Adresse nicht (404)", 502)
        raise StreamError("upstream", f"Die Kamera antwortete mit Status {err.code}", 502)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise StreamError("network", f"Die Kamera ist nicht erreichbar ({getattr(exc, 'reason', exc)})", 502)


def rewrite_playlist(text: str, base_url: str, proxy_prefix: str) -> str:
    """HLS-Playlist: jede Adresse (Zeilen und URI="...") wird absolut gemacht und ueber den Proxy geleitet."""
    def via(address: str) -> str:
        return f"{proxy_prefix}?u={urllib.parse.quote(urllib.parse.urljoin(base_url, address), safe='')}"

    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            lines.append(line)
        elif stripped.startswith("#"):
            lines.append(re.sub(r'URI="([^"]+)"', lambda m: f'URI="{via(m.group(1))}"', line))
        else:
            lines.append(via(stripped))
    return "\n".join(lines) + "\n"


def looks_like_playlist(url: str, content_type: str) -> bool:
    return urllib.parse.urlsplit(url).path.lower().endswith(".m3u8") or "mpegurl" in (content_type or "").lower()
