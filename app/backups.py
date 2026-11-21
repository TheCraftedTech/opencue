# Copyright (C) 2026 Samuel Zenker
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Sicherungen der Show im Hintergrund ("Backups") und Wiederherstellung nach einem Absturz.

Wer eine Show vor der Veranstaltung programmiert und sie waehrend der Veranstaltung mit Absicht NICHT speichert (nichts soll aus Versehen ueberschrieben werden), hat
trotzdem ungespeicherte Aenderungen im Arbeitsspeicher. Dieses Modul haelt sie fest, ohne dass man es sieht:

  * Alle `interval_min` Minuten (Standard 15) wird der aktuelle Stand der Show - auch der ungespeicherte - in den Ordner `backups/` des Datenordners geschrieben, aber nur
    wenn die Show Aenderungen hat und sich seit der letzten Sicherung etwas geaendert hat. Je Show bleiben die letzten `keep` (Standard 10), insgesamt hoechstens 100.
  * Beim Beenden ohne Speichern (oder wenn die Show gesperrt ist / nicht gespeichert werden kann) wird der Stand noch einmal gesichert.
  * Eine Sicherung ersetzt NIE die Show-Datei: sie wird mit "Datei -> Sicherung wiederherstellen" als ungespeicherter Stand geladen (die Show-Datei bleibt, wie sie ist).
  * Absturz-Erkennung: beim Start liegt eine Markierung `.session.json` im Ordner; beim sauberen Beenden wird sie geloescht. Ist sie beim naechsten Start noch da, bietet die
    Oberflaeche die letzte Sicherung dieser Sitzung zur Wiederherstellung an.

Dateien: `<Showname>__<JJJJMMTT-HHMMSS>.json` (eine ganz normale Show-Datei) und daneben `<...>.meta` (kleine JSON-Datei: Zeitpunkt, Grund, urspruenglicher Pfad).

  GET  /api/backups                  Liste, Einstellungen, Ordner, Angebot nach Absturz
  POST /api/backups/config           Einstellungen (von jedem angemeldeten Geraet)
  POST /api/backups/now              jetzt sichern
  POST /api/backups/restore          eine Sicherung als ungespeicherte Show laden
  POST /api/backups/delete           eine Sicherung loeschen
  POST /api/backups/dismiss-recovery das Angebot nach einem Absturz wegklicken (die Sicherungen bleiben)
  POST /api/backups/open-folder      den Ordner im Explorer oeffnen (nur lokal)
"""
from __future__ import annotations

import asyncio
import datetime
import hashlib
import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app import paths as _paths
from app import show_safety

logger = logging.getLogger("opencue.backups")

DEFAULTS: Dict[str, Any] = {"enabled": True, "interval_min": 15, "keep": 10}
MIN_INTERVAL, MAX_INTERVAL = 1, 240
MIN_KEEP, MAX_KEEP = 1, 50
MAX_TOTAL = 100                                              # Sicherungen insgesamt (alle Shows zusammen)
SESSION_FILE = ".session.json"
TICK_SECONDS = 20.0                                          # so oft schaut die Hintergrundaufgabe nach, ob eine Sicherung faellig ist
_NAME_FORBIDDEN = re.compile(r'[\\/:*?"<>|\x00-\x1f]')

router = APIRouter()


def normalize(raw: Any, base: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Einstellungen pruefen: Unbekanntes und Ungueltiges wird verworfen, Zahlen auf den erlaubten Bereich gebracht."""
    out = {key: (base or DEFAULTS).get(key, default) for key, default in DEFAULTS.items()}
    if not isinstance(raw, dict):
        return out
    if "enabled" in raw:
        out["enabled"] = raw["enabled"] is True or str(raw["enabled"]).lower() in ("1", "true", "on")
    for key, low, high in (("interval_min", MIN_INTERVAL, MAX_INTERVAL), ("keep", MIN_KEEP, MAX_KEEP)):
        if key in raw:
            try:
                value = int(float(raw[key]))
            except (TypeError, ValueError, OverflowError):
                continue
            out[key] = max(low, min(high, value))
    return out


def _stem(name: str) -> str:
    text = _NAME_FORBIDDEN.sub("_", str(name or "").strip()).strip(". ")[:60]
    return text or "Show"


def _folder() -> Path:
    directory = _paths.get_data_root() / "backups"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _now_iso() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


class BackupManager:
    def __init__(self) -> None:
        self._last_hash: Dict[str, str] = {}                 # Show -> Pruefsumme der letzten Sicherung (nichts doppelt sichern)
        self._last_try = time.monotonic()
        self.recovery: Optional[Dict[str, Any]] = None       # Angebot nach einem Absturz (Eintrag aus list_items()) oder None
        self.session_started = _now_iso()
        self.last_error = ""

    # ---------------------------------------------------------------- Sitzung / Absturz-Erkennung
    def start_session(self) -> None:
        """Beim Programmstart: war die letzte Sitzung nicht sauber beendet (Markierung noch da), die letzte Sicherung daraus als Angebot merken; dann neue Markierung."""
        marker = _folder() / SESSION_FILE
        previous_started = ""
        try:
            if marker.is_file():
                previous_started = str(json.loads(marker.read_text(encoding="utf-8")).get("started", ""))
                if previous_started:
                    candidates = [item for item in self.list_items() if item["taken_at"] >= previous_started]
                    self.recovery = candidates[0] if candidates else None
                    logger.warning("[BACKUP] OpenCue was not closed properly last time (session %s); %s",
                                   previous_started, "backup %s offered" % self.recovery["id"] if self.recovery else "no backup from that session")
        except (OSError, ValueError):
            logger.exception("[BACKUP] Session marker unreadable")
        try:
            marker.write_text(json.dumps({"started": self.session_started, "pid": os.getpid()}), encoding="utf-8")
        except OSError as exc:
            logger.warning("[BACKUP] Session marker not written: %s", exc)

    def end_session(self) -> None:
        """Sauberes Beenden: Markierung loeschen (dann gibt es beim naechsten Start kein Angebot)."""
        try:
            (_folder() / SESSION_FILE).unlink()
        except OSError:
            pass

    # ---------------------------------------------------------------- Liste
    def list_items(self) -> List[Dict[str, Any]]:
        """Alle Sicherungen, neueste zuerst: {id, name, taken_at, reason, size, original_path, original_exists, original_locked, dirty}."""
        items: List[Dict[str, Any]] = []
        for meta_path in _folder().glob("*.meta"):
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                data_path = meta_path.with_suffix(".json")
                if not isinstance(meta, dict) or not data_path.is_file():
                    continue
                original = str(meta.get("original_path") or "")
                items.append({
                    "id": data_path.name, "name": str(meta.get("name") or data_path.stem), "taken_at": str(meta.get("taken_at") or ""),
                    "reason": str(meta.get("reason") or "auto"), "size": data_path.stat().st_size, "original_path": original,
                    "original_exists": bool(original and Path(original).is_file()), "original_locked": show_safety.is_locked(original) if original else False,
                })
            except (OSError, ValueError):
                continue
        items.sort(key=lambda item: item["taken_at"], reverse=True)
        return items

    def path_of(self, backup_id: str) -> Optional[Path]:
        """Datei zu einer Sicherungs-Id (nur ein einfacher Name direkt im Sicherungsordner)."""
        if not backup_id or backup_id != Path(backup_id).name or not backup_id.endswith(".json"):
            return None
        path = _folder() / backup_id
        return path if path.is_file() else None

    # ---------------------------------------------------------------- sichern
    def build(self, reason: str = "auto", force: bool = False) -> Optional[Dict[str, Any]]:
        """Auf der Ereignisschleife: den Stand der geladenen Show als Text festhalten. None = nichts zu sichern (keine Aenderungen / seit der letzten Sicherung unveraendert)."""
        from app.state_manager import state
        if not (state.is_dirty or force):
            return None
        data = state._showfile_dict()
        digest = hashlib.sha1(json.dumps({k: v for k, v in data.items() if k != "saved_at"}, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")).hexdigest()
        key = state.showfile_path or state.showfile_name
        if not force and self._last_hash.get(key) == digest:
            return None
        return {"key": key, "digest": digest, "text": json.dumps(data, ensure_ascii=False), "name": state.showfile_name, "original_path": state.showfile_path or "",
                "reason": reason, "taken_at": _now_iso()}

    def write(self, job: Dict[str, Any]) -> Optional[Path]:
        """In einem Hintergrund-Thread: Datei und Beschreibung schreiben, aufraeumen. Gibt den Pfad zurueck oder None bei einem Fehler."""
        try:
            stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
            directory = _folder()
            path = directory / f"{_stem(job['name'])}__{stamp}.json"
            counter = 2
            while path.exists():                                              # zwei Sicherungen in derselben Sekunde
                path = directory / f"{_stem(job['name'])}__{stamp}-{counter}.json"
                counter += 1
            show_safety._atomic_write(path, job["text"])
            meta = {"name": job["name"], "taken_at": job["taken_at"], "reason": job["reason"], "original_path": job["original_path"], "digest": job["digest"]}
            show_safety._atomic_write(path.with_suffix(".meta"), json.dumps(meta, ensure_ascii=False))
            self._last_hash[job["key"]] = job["digest"]
            self.last_error = ""
            self.cleanup()
            logger.info("[BACKUP] %s saved (%s, %d KB)", path.name, job["reason"], path.stat().st_size // 1024)
            return path
        except Exception as exc:                                             # noqa: BLE001 - eine fehlgeschlagene Sicherung darf nie die Konsole stoeren
            self.last_error = str(exc)
            logger.warning("[BACKUP] OC-3701 Backup could not be written: %s", exc)
            return None

    async def take(self, reason: str = "auto", force: bool = False) -> Optional[Path]:
        job = self.build(reason, force)
        self._last_try = time.monotonic()
        if job is None:
            return None
        return await asyncio.to_thread(self.write, job)

    def take_now_blocking(self, reason: str) -> Optional[Path]:
        """Fuer das Beenden (kein Ereignisschleifen-Kontext noetig): bauen und gleich schreiben."""
        job = self.build(reason)
        return self.write(job) if job else None

    def cleanup(self) -> None:
        """Je Show die neuesten `keep` behalten, insgesamt hoechstens MAX_TOTAL."""
        from app.state_manager import state
        keep = int(state.backup_config.get("keep", DEFAULTS["keep"]))
        items = self.list_items()
        per_show: Dict[str, int] = {}
        survivors: List[Dict[str, Any]] = []
        for item in items:                                                    # neueste zuerst
            key = item["original_path"] or item["name"]
            per_show[key] = per_show.get(key, 0) + 1
            if per_show[key] > keep:
                self.delete(item["id"])
            else:
                survivors.append(item)
        for item in survivors[MAX_TOTAL:]:
            self.delete(item["id"])

    def delete(self, backup_id: str) -> bool:
        path = self.path_of(backup_id)
        if path is None:
            return False
        for target in (path, path.with_suffix(".meta")):
            try:
                target.unlink()
            except OSError:
                pass
        return True

    # ---------------------------------------------------------------- Hintergrundaufgabe
    async def run(self) -> None:
        """Laeuft fuer die ganze Programmzeit: schaut regelmaessig, ob eine Sicherung faellig ist (Einstellungen werden bei jedem Schritt neu gelesen)."""
        from app.state_manager import state
        while True:
            await asyncio.sleep(TICK_SECONDS)
            try:
                config = state.backup_config
                if not config.get("enabled", True):
                    self._last_try = time.monotonic()                          # aus: die Frist beginnt neu, wenn man es wieder einschaltet
                    continue
                if time.monotonic() - self._last_try >= int(config.get("interval_min", 15)) * 60:
                    await self.take("auto")
                    self._last_try = time.monotonic()
            except asyncio.CancelledError:
                raise
            except Exception:                                                  # noqa: BLE001
                logger.exception("[BACKUP] Background step failed")


manager = BackupManager()


# ---------------------------------------------------------------------------------------------------------------- HTTP
def _local(request: Request) -> bool:
    from app import remote                                                    # erst hier: remote kennt den Zustand (Zirkelimport vermeiden)
    return remote.is_local(request.client.host if request.client else None)


def _denied() -> JSONResponse:
    return JSONResponse({"ok": False, "error": "local_only"}, status_code=403)


def overview() -> Dict[str, Any]:
    from app.state_manager import state
    return {"ok": True, "config": dict(state.backup_config), "defaults": dict(DEFAULTS), "dir": str(_folder()), "items": manager.list_items(),
            "recovery": manager.recovery, "last_error": manager.last_error}


@router.get("/api/backups")
async def list_backups() -> JSONResponse:
    return JSONResponse(await asyncio.to_thread(overview))


@router.post("/api/backups/config")
async def set_config(request: Request) -> JSONResponse:
    from app.state_manager import state
    state.backup_config = normalize(await request.json(), state.backup_config)
    state.save_app_config()
    return JSONResponse({"ok": True, "config": dict(state.backup_config)})


@router.post("/api/backups/now")
async def backup_now(request: Request) -> JSONResponse:
    path = await manager.take("manual", force=True)
    return JSONResponse({"ok": path is not None, "id": path.name if path else None, "error": manager.last_error})


@router.post("/api/backups/delete")
async def delete_backup(request: Request) -> JSONResponse:
    body = await request.json()
    ok = manager.delete(str(body.get("id", "")))
    if manager.recovery and manager.recovery.get("id") == body.get("id"):
        manager.recovery = None
    return JSONResponse({"ok": ok}, status_code=200 if ok else 404)


@router.post("/api/backups/dismiss-recovery")
async def dismiss_recovery() -> JSONResponse:
    manager.recovery = None
    return JSONResponse({"ok": True})


@router.post("/api/backups/open-folder")
async def open_folder(request: Request) -> JSONResponse:
    if not _local(request):
        return _denied()
    try:
        os.startfile(str(_folder()))                                          # noqa: S606 - nur Windows (Explorer)
        return JSONResponse({"ok": True})
    except Exception as exc:                                                  # noqa: BLE001
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=500)


@router.post("/api/backups/restore")
async def restore_backup(request: Request) -> JSONResponse:
    body = await request.json()
    path = manager.path_of(str(body.get("id", "")))
    if path is None:
        return JSONResponse({"ok": False, "error": "not_found"}, status_code=404)
    from app import server as S
    try:
        await manager.take("before-restore")                                  # der jetzige ungespeicherte Stand geht nicht verloren
        info = await S.restore_backup_file(path)
    except Exception as exc:                                                  # noqa: BLE001
        logger.exception("[BACKUP] Restore failed")
        return JSONResponse({"ok": False, "error": "restore_failed", "message": str(exc)}, status_code=500)
    manager.recovery = None
    return JSONResponse({"ok": True, **info})
