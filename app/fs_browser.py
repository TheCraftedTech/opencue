# Copyright (C) 2026 Samuel Zenker
# SPDX-License-Identifier: GPL-3.0-or-later
"""
OpenCue-Explorer: ein eigener Datei-Dialog, damit sich Fernzugriffs-Geraete (iPad, Handy) so bedienen lassen wie der Hauptrechner - ohne den Windows-Explorer.

Zwei Betriebsarten (Oberflaeche: static/js/fs_browser.js):
  * DATEN-ORDNER: durchsuchen, herunterladen (Ordner als ZIP), hochladen, neuer Ordner, umbenennen, duplizieren, loeschen - beschraenkt auf den Datenordner von OpenCue (Shows, Sicherungen,
    Protokolle, Scheinwerfer, Medien ...). Pfade sind immer RELATIV zum Datenordner; alles ausserhalb (auch ueber .. oder Verknuepfungen) wird abgelehnt.
  * ORDNER WAEHLEN: nur die Ordnerstruktur des Rechners (Laufwerke, Unterordner) zum Aussuchen eines Pfads (z. B. "Speicherort aendern"); es werden keine Dateien aufgelistet oder gelesen.

  GET  /api/fs/list?area=data|logs&path=<relativ>  Inhalt eines Ordners im Datenordner
  GET  /api/fs/dirs?path=<absolut>           Unterordner (leerer Pfad = Laufwerke) fuer "Ordner waehlen"
  POST /api/fs/op                            {op: mkdir|rename|duplicate|delete, path, name?}
  GET  /api/fs/download?path=<relativ>       Datei (oder Ordner als ZIP) herunterladen
  POST /api/fs/upload?path=<relativ>&name=   Datei hochladen (roher Body, hoechstens 400 MB; nie etwas ueberschreiben)
Zugriff: wie alle Adressen - Fernzugriffs-Geraete brauchen die Anmeldung.
"""
from __future__ import annotations

import asyncio
import logging
import os
import re
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, JSONResponse
from starlette.background import BackgroundTask

from app import paths as _paths

logger = logging.getLogger("opencue.fs")
router = APIRouter()

MAX_ROWS = 3000
MAX_UPLOAD = 400 * 1024 * 1024
MAX_ZIP = 400 * 1024 * 1024
_BAD_NAME = re.compile(r'[\\/:*?"<>|\x00-\x1f]')


class FsError(Exception):
    def __init__(self, code: str, status: int = 400, **extra: Any) -> None:
        super().__init__(code)
        self.code, self.status, self.extra = code, status, extra

    def response(self) -> JSONResponse:
        return JSONResponse({"ok": False, "error": self.code, **self.extra}, status_code=self.status)


AREAS = ("data", "logs")


def root(area: str = "data") -> Path:
    """Wurzel eines Bereichs: 'data' = Datenordner, 'logs' = Protokoll-Ordner (liegt beim Standard-Datenordner, auch wenn der Datenordner verlegt wurde)."""
    if area == "logs":
        from app import logsetup
        folder = logsetup.log_dir()
        folder.mkdir(parents=True, exist_ok=True)
        return folder.resolve()
    if area not in ("data", "", None):
        raise FsError("bad_area")
    return Path(_paths.get_data_root()).resolve()


def safe(rel: str, area: str = "data") -> Path:
    """Relativer Pfad -> absoluter Pfad INNERHALB des Datenordners (sonst FsError)."""
    base = root(area)
    parts = [p for p in str(rel or "").replace("\\", "/").split("/") if p not in ("", ".")]
    if any(p == ".." or ":" in p or _BAD_NAME.search(p) for p in parts):
        raise FsError("bad_path")
    path = (base.joinpath(*parts)).resolve()
    if path != base and base not in path.parents:
        raise FsError("outside", 403)
    return path


def rel_of(path: Path, area: str = "data") -> str:
    base = root(area)
    return "" if path == base else "/".join(path.relative_to(base).parts)


def clean_name(name: Any) -> str:
    text = str(name or "").strip().rstrip(". ")
    if not text or text in (".", "..") or _BAD_NAME.search(text) or len(text) > 120:
        raise FsError("bad_name")
    return text


def unique(path: Path) -> Path:
    if not path.exists():
        return path
    stem, suffix = (path.stem, path.suffix) if path.is_file() else (path.name, "")
    n = 2
    while True:
        candidate = path.with_name(f"{stem} ({n}){suffix}")
        if not candidate.exists():
            return candidate
        n += 1


def list_dir(rel: str, area: str = "data") -> Dict[str, Any]:
    path = safe(rel, area)
    if not path.is_dir():
        raise FsError("not_found", 404)
    rows: List[Dict[str, Any]] = []
    try:
        entries = list(os.scandir(path))
    except OSError as exc:
        raise FsError("unreadable", 403, detail=str(exc))
    for entry in entries[:MAX_ROWS]:
        try:
            info = entry.stat()
            is_dir = entry.is_dir()
        except OSError:
            continue
        rows.append({"name": entry.name, "dir": is_dir, "size": 0 if is_dir else info.st_size, "mtime": int(info.st_mtime)})
    rows.sort(key=lambda r: (not r["dir"], r["name"].lower()))
    crumbs, acc = [], []
    for part in rel_of(path, area).split("/") if rel_of(path, area) else []:
        acc.append(part)
        crumbs.append({"name": part, "path": "/".join(acc)})
    return {"ok": True, "area": area, "root": str(root(area)), "path": rel_of(path, area), "crumbs": crumbs, "rows": rows, "truncated": len(entries) > MAX_ROWS}


def list_dirs(absolute: str) -> Dict[str, Any]:
    """Ordner-Auswahl: leerer Pfad = Laufwerke (Windows) bzw. die Wurzel; sonst die Unterordner (nur Namen und Pfade, nie Dateien)."""
    text = str(absolute or "").strip()
    if not text:
        drives: List[Dict[str, str]] = []
        if hasattr(os, "listdrives"):
            drives = [{"name": d.rstrip("\\"), "path": d} for d in os.listdrives()]
        else:
            drives = [{"name": "/", "path": "/"}]
        home = str(Path.home())
        return {"ok": True, "path": "", "parent": None, "rows": drives, "home": home, "data": str(root())}
    path = Path(text)
    if not path.is_absolute():
        raise FsError("bad_path")
    try:
        path = path.resolve()
        names = sorted((e.name for e in os.scandir(path) if e.is_dir() and not e.name.startswith("$")), key=str.lower)
    except OSError as exc:
        raise FsError("unreadable", 403, detail=str(exc))
    parent = str(path.parent) if path.parent != path else ""
    return {"ok": True, "path": str(path), "parent": parent, "rows": [{"name": n, "path": str(path / n)} for n in names[:MAX_ROWS]], "home": str(Path.home()), "data": str(root())}


def operate(body: Dict[str, Any]) -> Dict[str, Any]:
    op = str(body.get("op", ""))
    area = str(body.get("area", "data"))
    target = safe(str(body.get("path", "")), area)
    if op == "mkdir":
        if not target.is_dir():
            raise FsError("not_found", 404)
        new = target / clean_name(body.get("name"))
        if new.exists():
            raise FsError("exists", 409)
        new.mkdir()
        return {"ok": True, "path": rel_of(new, area)}
    if target == root(area):
        raise FsError("root", 400)                                                    # den Datenordner selbst nie anfassen
    if not target.exists():
        raise FsError("not_found", 404)
    if op == "rename":
        new = target.with_name(clean_name(body.get("name")))
        if new.exists() and new != target:
            raise FsError("exists", 409)
        target.rename(new)
        return {"ok": True, "path": rel_of(new, area)}
    if op == "duplicate":
        new = unique(target.with_name(clean_name(body.get("name"))) if body.get("name") else target)
        if target.is_dir():
            shutil.copytree(target, new)
        else:
            shutil.copy2(target, new)
        return {"ok": True, "path": rel_of(new, area)}
    if op == "delete":
        if target.is_dir():
            shutil.rmtree(target)
        else:
            target.unlink()
        return {"ok": True}
    raise FsError("bad_op")


def zip_folder(folder: Path) -> Path:
    fd, tmp = tempfile.mkstemp(suffix=".zip", prefix="opencue-fs-")
    os.close(fd)
    total = 0
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as archive:
        for item in folder.rglob("*"):
            if item.is_file():
                total += item.stat().st_size
                if total > MAX_ZIP:
                    archive.close()
                    os.unlink(tmp)
                    raise FsError("too_large", 413)
                try:
                    archive.write(item, item.relative_to(folder).as_posix())
                except OSError:
                    continue                                                           # eine gerade benutzte Datei ueberspringen
    return Path(tmp)


@router.get("/api/fs/list")
async def api_list(path: str = "", area: str = "data") -> JSONResponse:
    try:
        return JSONResponse(await asyncio.to_thread(list_dir, path, area), headers={"Cache-Control": "no-store"})
    except FsError as exc:
        return exc.response()


@router.get("/api/fs/dirs")
async def api_dirs(path: str = "") -> JSONResponse:
    try:
        return JSONResponse(await asyncio.to_thread(list_dirs, path), headers={"Cache-Control": "no-store"})
    except FsError as exc:
        return exc.response()


@router.post("/api/fs/op")
async def api_op(request: Request) -> JSONResponse:
    try:
        body = await request.json()
        if not isinstance(body, dict):
            raise FsError("bad_request")
        return JSONResponse(await asyncio.to_thread(operate, body))
    except FsError as exc:
        return exc.response()
    except OSError as exc:
        return JSONResponse({"ok": False, "error": "os_error", "detail": str(exc)}, status_code=409)


@router.get("/api/fs/download")
async def api_download(path: str = "", area: str = "data"):
    try:
        target = safe(path, area)
        if not target.exists():
            raise FsError("not_found", 404)
        if target.is_dir():
            archive = await asyncio.to_thread(zip_folder, target)
            return FileResponse(str(archive), media_type="application/zip", filename=(target.name or "OpenCue") + ".zip", background=BackgroundTask(lambda: os.path.exists(archive) and os.unlink(archive)))
        return FileResponse(str(target), media_type="application/octet-stream", filename=target.name)
    except FsError as exc:
        return exc.response()


@router.post("/api/fs/upload")
async def api_upload(request: Request, path: str = "", name: str = "", area: str = "data") -> JSONResponse:
    try:
        folder = safe(path, area)
        if not folder.is_dir():
            raise FsError("not_found", 404)
        target = unique(folder / clean_name(name))
        declared = request.headers.get("content-length")
        if declared and declared.isdigit() and int(declared) > MAX_UPLOAD:
            raise FsError("too_large", 413)
        size = 0
        partial = target.with_name("." + target.name + ".part")
        with open(partial, "wb") as handle:
            async for chunk in request.stream():
                size += len(chunk)
                if size > MAX_UPLOAD:
                    handle.close()
                    partial.unlink(missing_ok=True)
                    raise FsError("too_large", 413)
                handle.write(chunk)
        os.replace(partial, target)
        return JSONResponse({"ok": True, "path": rel_of(target, area), "name": target.name})
    except FsError as exc:
        return exc.response()
    except OSError as exc:
        return JSONResponse({"ok": False, "error": "os_error", "detail": str(exc)}, status_code=409)
