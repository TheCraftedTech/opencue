# Copyright (C) 2026 Samuel Zenker
# SPDX-License-Identifier: GPL-3.0-or-later
"""
net_diag.py
Warum erreicht OpenCue das Internet nicht? (Update-Pruefung bei GitHub, GDTF Share.) Der Browser eines Rechners kann im Netz sein, waehrend ein Programm blockiert wird
(Firewall / Virenscanner, ein Proxy, ein Firmennetz, das verschluesselte Verbindungen aufbricht). Dieses Modul
  - merkt sich das Ergebnis der letzten echten Verbindung je Dienst (`record`, `last`) - die Einstellungen zeigen es (Ein- & Ausgaenge),
  - ordnet einen Fehler einer kurzen Ursache zu (`classify`: dns | timeout | refused | reset | blocked | tls_cert | tls | proxy | http_<n> | network),
  - prueft auf Knopfdruck beide Dienste Schritt fuer Schritt (`run_check`: DNS -> TCP -> TLS -> HTTP) und nennt die Stufe, an der es scheitert.
Es werden nur die beiden Adressen von OpenCue selbst angefragt (kein Datenversand).
"""
from __future__ import annotations

import socket
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

_last: Dict[str, Dict[str, Any]] = {}
CHECK_TIMEOUT_S = 8.0


def classify(exc: BaseException) -> str:
    """Kurzer Ursachen-Code zu einer Ausnahme (die Oberflaeche uebersetzt ihn: NET_ERR_<CODE>)."""
    if isinstance(exc, urllib.error.HTTPError):
        return f"http_{exc.code}"
    if isinstance(exc, urllib.error.URLError):
        return classify(exc.reason) if isinstance(exc.reason, BaseException) else "network"
    if isinstance(exc, ssl.SSLCertVerificationError):
        return "tls_cert"
    if isinstance(exc, ssl.SSLError):
        return "tls"
    if isinstance(exc, socket.gaierror):
        return "dns"
    if isinstance(exc, (TimeoutError, socket.timeout)):
        return "timeout"
    if isinstance(exc, ConnectionRefusedError):
        return "refused"
    if isinstance(exc, ConnectionResetError):
        return "reset"
    if isinstance(exc, PermissionError):
        return "blocked"                                    # WinError 10013: der Zugriff auf den Socket ist verboten (Firewall / Sicherheitssoftware)
    if isinstance(exc, OSError) and getattr(exc, "winerror", None) in (10013, 10061):
        return "blocked" if exc.winerror == 10013 else "refused"
    return "network"


def record(service: str, ok: bool, exc: Optional[BaseException] = None) -> None:
    """Ergebnis einer echten Verbindung merken (von updater.py und fixture_library.py aufgerufen)."""
    _last[service] = {"ok": bool(ok), "at": int(time.time()), "code": "" if ok else (classify(exc) if exc is not None else "network"),
                      "detail": "" if ok or exc is None else str(getattr(exc, "reason", exc))[:200]}


def last(service: str) -> Optional[Dict[str, Any]]:
    return dict(_last[service]) if service in _last else None


def proxy_text() -> str:
    """Ein eingestellter System-Proxy (ohne Zugangsdaten) - er erklaert oft, warum ein Programm nicht durchkommt, der Browser aber schon."""
    out = []
    for scheme, address in sorted(urllib.request.getproxies().items()):
        if scheme in ("http", "https", "all"):
            parts = urllib.parse.urlsplit(address if "://" in address else "//" + address)
            out.append(f"{scheme}: {parts.hostname or address}:{parts.port}" if parts.port else f"{scheme}: {parts.hostname or address}")
    return ", ".join(out)


def _stages(host: str, port: int) -> Dict[str, Any]:
    """Direkt, ohne Proxy: wo bleibt die Verbindung haengen? Gibt {"stage", "code", "detail"} der ersten fehlgeschlagenen Stufe zurueck ({} = alles ging)."""
    try:
        addresses = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except OSError as exc:
        return {"stage": "dns", "code": "dns", "detail": str(exc)[:160]}
    family, _kind, _proto, _name, sockaddr = addresses[0]
    try:
        raw = socket.create_connection(sockaddr[:2], timeout=CHECK_TIMEOUT_S)
    except OSError as exc:
        return {"stage": "tcp", "code": classify(exc), "detail": str(exc)[:160]}
    try:
        context = ssl.create_default_context()
        with context.wrap_socket(raw, server_hostname=host):
            return {}
    except OSError as exc:
        return {"stage": "tls", "code": classify(exc), "detail": str(exc)[:200]}
    finally:
        try:
            raw.close()
        except OSError:
            pass


def check_target(service: str, url: str) -> Dict[str, Any]:
    """Eine Adresse so anfragen, wie OpenCue es selbst tut (urllib, Proxy-Einstellungen von Windows); bei einem Fehler zusaetzlich die Stufen einzeln pruefen."""
    parts = urllib.parse.urlsplit(url)
    host = parts.hostname or ""
    port = parts.port or (443 if parts.scheme == "https" else 80)
    started = time.monotonic()
    request = urllib.request.Request(url, headers={"User-Agent": "OpenCue-Verbindungstest"})
    result: Dict[str, Any] = {"service": service, "host": host}
    try:
        with urllib.request.urlopen(request, timeout=CHECK_TIMEOUT_S) as response:
            response.read(256)
            result.update(ok=True, status=response.status)
    except urllib.error.HTTPError as exc:                    # eine Antwort des Servers (auch 401 / 403 / 404) heisst: die Verbindung steht
        result.update(ok=True, status=exc.code)
    except Exception as exc:                                 # noqa: BLE001 - jede Art von Netzwerkfehler
        result.update(ok=False, code=classify(exc), detail=str(getattr(exc, "reason", exc))[:200])
        stage = _stages(host, port) if parts.scheme == "https" or parts.scheme == "http" else {}
        if stage:
            result.update(stage=stage["stage"], direct_code=stage["code"], direct_detail=stage["detail"])
        elif urllib.request.getproxies():
            result["code"] = "proxy" if result["code"] == "network" else result["code"]        # direkt geht es, ueber den Proxy nicht
    result["ms"] = int((time.monotonic() - started) * 1000)
    record(service, bool(result["ok"]), None if result["ok"] else Exception(result.get("detail", "")))
    if not result["ok"]:
        _last[service]["code"] = result["code"]
    return result


def run_check() -> Dict[str, Any]:
    """Update-Server (GitHub) und GDTF Share nacheinander pruefen. Laeuft in einem Thread (blockiert bis zu ein paar Sekunden je Adresse)."""
    from app import fixture_library, updater
    targets = [("update", updater.api_url()), ("gdtf", fixture_library.SHARE_BASE + "/")]
    return {"results": [check_target(service, url) for service, url in targets], "proxy": proxy_text()}
