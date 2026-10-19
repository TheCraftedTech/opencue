"""
updater.py
Update-Pruefung ueber GitHub-Releases und Installation der neuen Version.

Ablauf
  1. check(): fragt https://api.github.com/repos/<Repo>/releases/latest (nur oeffentliche, endgueltige Releases) nach dem neuesten Stand und vergleicht mit app/version.py.
     Das Programm bleibt voll offline nutzbar: ohne Netz endet die Pruefung still mit state "error". Ergebnis wird 6 Stunden zwischengespeichert (force=True ueberspringt das).
  2. download(): laedt das Setup (Anhang "OpenCue-Setup-v<Version>.exe" des Releases) in einen Temp-Ordner und prueft die SHA-256-Summe, wenn GitHub sie mitliefert (Feld "digest").
     Nur Adressen unter https://github.com/<Repo>/releases/download/ werden geladen (GitHub leitet auf seinen eigenen Download-Server um).
  3. arm()/disarm(): der Benutzer beendet OpenCue ueber den normalen Beenden-Dialog (Speichern!); main.py ruft danach launch_pending_installer(): das Setup startet erst NACH dem
     Beenden (keine gesperrten Dateien) und startet OpenCue am Ende wieder (OpenCue.iss, stiller Modus). Bricht der Benutzer den Dialog ab, wird disarm() aufgerufen; ein
     scharf geschaltetes Setup verfaellt ausserdem nach 15 Minuten.

Test/Entwicklung: Umgebungsvariable OPENCUE_UPDATE_URL ersetzt die API-Adresse (z. B. lokaler Testserver oder Datei); app/updater._fetch_json und _open lassen sich in Tests austauschen.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import re
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from app import version

logger = logging.getLogger("opencue.updater")

CACHE_SECONDS = 6 * 3600
ARM_SECONDS = 15 * 60
FETCH_TIMEOUT = 8.0
MAX_INSTALLER_BYTES = 600 * 1024 * 1024
NOTES_LIMIT = 4000
_UA = {"User-Agent": f"{version.APP_NAME}/{version.APP_VERSION}", "Accept": "application/vnd.github+json"}
_INSTALLER_NAME = re.compile(r"^OpenCue-Setup-v[0-9A-Za-z.+-]+\.exe$")
_VERSION = re.compile(r"^[vV]?(\d+)\.(\d+)\.(\d+)(?:[-+.]?([0-9A-Za-z.-]+))?$")

_lock = threading.Lock()
_cache: Dict[str, Any] = {}                 # letztes Ergebnis von check()
_progress: Dict[str, Any] = {"state": "idle"}
_armed: Dict[str, Any] = {}                 # {"path": ..., "at": ...}


# ------------------------------------------------------------------------------------------------ Versionen
def parse_version(text: Any) -> Optional[Tuple[Tuple[int, int, int], str]]:
    """'v1.2.3' / '1.2.3-beta.1' -> ((1, 2, 3), 'beta.1'); sonst None."""
    match = _VERSION.match(str(text or "").strip())
    if not match:
        return None
    return (int(match.group(1)), int(match.group(2)), int(match.group(3))), (match.group(4) or "")


def is_newer(latest: Any, current: Any) -> bool:
    """Ist `latest` neuer als `current`? Eine Vorabversion (1.1.0-beta) ist aelter als die Endfassung 1.1.0 und neuer als 1.0.9."""
    a, b = parse_version(latest), parse_version(current)
    if a is None or b is None:
        return False
    if a[0] != b[0]:
        return a[0] > b[0]
    if a[1] == b[1]:
        return False
    return a[1] == "" and b[1] != ""            # gleiche Zahlen: Endfassung schlaegt Vorabversion


# ------------------------------------------------------------------------------------------------ Netzwerk
def api_url() -> str:
    return os.environ.get("OPENCUE_UPDATE_URL", "").strip() or version.UPDATE_API_URL


def _fetch_json(url: str) -> Tuple[int, Any]:
    """(HTTP-Status, JSON) - 404 (noch kein Release) ist ein normales Ergebnis. Andere Fehler: Ausnahme."""
    request = urllib.request.Request(url, headers=_UA)
    try:
        with urllib.request.urlopen(request, timeout=FETCH_TIMEOUT) as response:
            return response.status, json.loads(response.read(2_000_000).decode("utf-8"))
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return 404, None
        raise


def _open(url: str):
    return urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": _UA["User-Agent"]}), timeout=FETCH_TIMEOUT)


def _installer_from(release: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    prefix = version.SOURCE_URL.rstrip("/") + "/releases/download/"
    for asset in release.get("assets") or []:
        name = str(asset.get("name") or "")
        url = str(asset.get("browser_download_url") or "")
        if _INSTALLER_NAME.match(name) and url.startswith(prefix):
            digest = str(asset.get("digest") or "")
            return {"name": name, "url": url, "size": int(asset.get("size") or 0), "sha256": digest[7:].lower() if digest.lower().startswith("sha256:") else ""}
    return None


def _evaluate(status: int, release: Any) -> Dict[str, Any]:
    base = {"current": version.APP_VERSION_LABEL, "checked_at": int(time.time())}
    if status == 404 or not isinstance(release, dict):
        return {**base, "state": "none", "latest": ""}                          # noch kein Release veroeffentlicht
    tag = str(release.get("tag_name") or "")
    if parse_version(tag) is None:
        return {**base, "state": "error", "error": "bad_version", "latest": tag}
    available = is_newer(tag, version.APP_VERSION)
    return {**base, "state": "available" if available else "current", "latest": tag if tag.lower().startswith("v") else "v" + tag, "notes": str(release.get("body") or "")[:NOTES_LIMIT],
            "url": str(release.get("html_url") or version.SOURCE_URL + "/releases/latest"), "installer": _installer_from(release) if available else None,
            "published_at": str(release.get("published_at") or "")}


async def check(force: bool = False) -> Dict[str, Any]:
    """Pruefung (zwischengespeichert). Gibt immer ein Dict mit state: available | current | none | error zurueck."""
    now = time.time()
    with _lock:
        cached = dict(_cache)
    if cached and not force and now - cached.get("_at", 0) < CACHE_SECONDS:
        return {k: v for k, v in cached.items() if k != "_at"}
    try:
        status, release = await asyncio.to_thread(_fetch_json, api_url())
        result = _evaluate(status, release)
    except Exception as exc:                                                    # offline, Zeitueberschreitung, Rate-Limit ...
        code = getattr(exc, "code", None)
        logger.info("[Update] Pruefung nicht moeglich: %s", exc)
        result = {"state": "error", "error": "rate_limit" if code in (403, 429) else "network", "current": version.APP_VERSION_LABEL, "latest": "", "checked_at": int(now)}
    with _lock:
        _cache.clear()
        _cache.update(result, _at=now)
    return result


def cached() -> Dict[str, Any]:
    """Letztes Ergebnis ohne Netzwerkzugriff; {"state": "unknown"}, solange noch keine Pruefung lief."""
    with _lock:
        return {k: v for k, v in _cache.items() if k != "_at"} or {"state": "unknown", "current": version.APP_VERSION_LABEL}


def reset_cache() -> None:
    with _lock:
        _cache.clear()


# ------------------------------------------------------------------------------------------------ Download
def progress() -> Dict[str, Any]:
    with _lock:
        return dict(_progress)


def _set_progress(**values: Any) -> None:
    with _lock:
        _progress.clear()
        _progress.update(values)


def download_blocking(installer: Dict[str, Any]) -> Path:
    """Laedt das Setup (Thread). Gibt den Pfad zurueck oder wirft eine Ausnahme; Fortschritt in progress()."""
    url = str(installer.get("url") or "")
    if not url.startswith(version.SOURCE_URL.rstrip("/") + "/releases/download/") or not _INSTALLER_NAME.match(str(installer.get("name") or "")):
        raise ValueError("invalid_installer")
    folder = Path(tempfile.mkdtemp(prefix="opencue-update-"))
    target = folder / installer["name"]
    total = int(installer.get("size") or 0)
    digest = hashlib.sha256()
    done = 0
    _set_progress(state="downloading", done=0, total=total)
    with _open(url) as response, open(target, "wb") as out:
        total = int(response.headers.get("Content-Length") or total or 0)
        while True:
            block = response.read(256 * 1024)
            if not block:
                break
            done += len(block)
            if done > MAX_INSTALLER_BYTES:
                raise ValueError("too_big")
            out.write(block)
            digest.update(block)
            _set_progress(state="downloading", done=done, total=total)
    expected = str(installer.get("sha256") or "").lower()
    if expected and digest.hexdigest() != expected:
        target.unlink(missing_ok=True)
        raise ValueError("checksum")
    _set_progress(state="ready", done=done, total=done, path=str(target), verified=bool(expected), name=installer["name"])
    return target


def start_download(installer: Dict[str, Any]) -> bool:
    """Startet den Download im Hintergrund; False, wenn schon einer laeuft."""
    if progress().get("state") == "downloading":
        return False
    _set_progress(state="downloading", done=0, total=int(installer.get("size") or 0))

    def run() -> None:
        try:
            download_blocking(installer)
        except Exception as exc:
            logger.warning("[Update] Download fehlgeschlagen: %s", exc)
            _set_progress(state="error", error=str(exc) if str(exc) in ("checksum", "too_big", "invalid_installer") else "network")

    threading.Thread(target=run, name="opencue-update-download", daemon=True).start()
    return True


# ------------------------------------------------------------------------------------------------ Setup starten
def arm() -> bool:
    """Heruntergeladenes Setup fuer das Programmende vormerken (nur wenn der Download fertig ist)."""
    info = progress()
    path = info.get("path")
    if info.get("state") != "ready" or not path or not Path(path).is_file():
        return False
    with _lock:
        _armed.clear()
        _armed.update(path=str(path), at=time.time())
    return True


def disarm() -> None:
    with _lock:
        _armed.clear()


def is_armed() -> bool:
    with _lock:
        return bool(_armed) and time.time() - _armed.get("at", 0) < ARM_SECONDS


def launch_pending_installer() -> bool:
    """Von main.py nach dem Beenden aufgerufen: startet das vorgemerkte Setup (stiller Modus, startet OpenCue danach wieder). True, wenn gestartet."""
    with _lock:
        path = _armed.get("path") if _armed and time.time() - _armed.get("at", 0) < ARM_SECONDS else None
        _armed.clear()
    if not path or not Path(path).is_file() or sys.platform != "win32":
        return False
    flags = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    try:
        subprocess.Popen([path, "/SILENT", "/NORESTART", "/CLOSEAPPLICATIONS"], close_fds=True, creationflags=flags)
        return True
    except OSError as exc:
        logger.error("[Update] Setup konnte nicht gestartet werden: %s", exc)
        return False
