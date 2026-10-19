"""
about.py
"Ueber OpenCue" (Hilfe-Menue): Version, Lizenz (GPL-3.0-or-later), Quellcode-Link und die Lizenzen der mitgelieferten Bibliotheken.

  GET  /api/about                      Version/Metadaten (app/version.py) + Liste der Drittanbieter-Komponenten + Datenordner
  GET  /api/about/license              Text der LICENSE (GPL-3)
  GET  /api/about/component?name=...   Lizenztext einer Komponente aus der Liste (nur Namen aus components.json, nie ein freier Pfad)
  GET  /api/update/status              letztes Pruefergebnis (ohne Netzwerkzugriff) + Einstellungen; POST /api/update/check prueft jetzt (Netz); skip / enabled / download / progress / arm / disarm:
                                       siehe app/updater.py (Download, Beenden und Setup starten gehen nur am Hauptgeraet)
  POST /api/about/open                 {target: "source" | "website" | "releases"}: oeffnet die Adresse im Standard-Browser (nur am Hauptgeraet, nur diese festen Adressen)

Die Lizenztexte der Bibliotheken erzeugt packaging/collect_licenses.py nach packaging/third_party/ (im Build: <Programmordner>/third_party/) samt components.json.
"""
from __future__ import annotations

import asyncio
import json
import logging
import platform
import sys
import webbrowser
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, PlainTextResponse

from app import paths as _paths
from app import remote, updater, version
from app.state_manager import state
from app.window_signals import file_dialog

logger = logging.getLogger("opencue.about")
router = APIRouter()
_open_browser = webbrowser.open                       # Tests tauschen das aus
_MAX_TEXT = 400_000


def third_party_dir() -> Optional[Path]:
    """Ordner mit components.json und licenses/: im Build <Programmordner>/third_party, in der Entwicklung packaging/third_party."""
    root = _paths.project_root()
    for candidate in (root / "third_party", root / "packaging" / "third_party"):
        if (candidate / "components.json").is_file():
            return candidate
    return None


def components() -> List[Dict[str, Any]]:
    folder = third_party_dir()
    if folder is None:
        return []
    try:
        data = json.loads((folder / "components.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return [c for c in data if isinstance(c, dict) and c.get("name")]


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")[:_MAX_TEXT]
    except OSError:
        return ""


@router.get("/api/about")
async def about() -> JSONResponse:
    info = version.info()
    info["components"] = [{"name": c["name"], "version": c.get("version", ""), "license": c.get("license", ""), "purpose": c.get("purpose", ""), "url": c.get("url", ""), "has_text": bool(c.get("files"))} for c in components()]
    info["data_dir"] = str(_paths.get_data_root())
    info["python"] = platform.python_version()
    info["frozen"] = bool(getattr(sys, "frozen", False))
    return JSONResponse(info, headers={"Cache-Control": "no-store"})


@router.get("/api/about/license")
async def license_text() -> PlainTextResponse:
    text = _read_text(_paths.project_root() / "LICENSE")
    return PlainTextResponse(text or "LICENSE file not found.", headers={"Cache-Control": "no-store"})


@router.get("/api/about/component")
async def component_text(name: str = "") -> PlainTextResponse:
    folder = third_party_dir()
    entry = next((c for c in components() if c["name"] == name), None)
    if folder is None or entry is None:
        return PlainTextResponse("Unknown component.", status_code=404)
    parts: List[str] = []
    for relative in entry.get("files") or []:
        path = (folder / "licenses" / relative).resolve()
        if folder.resolve() in path.parents:                      # nur Dateien aus dem Lizenzordner
            text = _read_text(path)
            if text:
                parts.append(text.strip())
    return PlainTextResponse(("\n\n" + "-" * 72 + "\n\n").join(parts) or "No licence text bundled for this component.", headers={"Cache-Control": "no-store"})


@router.post("/api/about/open")
async def open_link(request: Request) -> JSONResponse:
    """Im Programmfenster (pywebview) oeffnet window.open keinen Browser: der Server startet den Standard-Browser. Entfernte Geraete bekommen opened=false und oeffnen den Link selbst."""
    body = await request.json()
    target = body.get("target") if isinstance(body, dict) else None
    url = {"source": version.SOURCE_URL, "website": version.WEBSITE_URL, "releases": version.RELEASES_URL}.get(str(target))
    if not url:
        return JSONResponse({"ok": False, "error": "invalid_target"}, status_code=400)
    host = request.client.host if request.client else None
    if not (remote.is_local(host) and file_dialog.available):
        return JSONResponse({"ok": True, "opened": False, "url": url})
    await asyncio.to_thread(_open_browser, url)
    return JSONResponse({"ok": True, "opened": True, "url": url})


# ------------------------------------------------------------------------------------------------ Updates
def _is_main_device(request: Request) -> bool:
    host = request.client.host if request.client else None
    return remote.is_local(host) and file_dialog.available


def _update_payload(request: Request, info: Dict[str, Any]) -> Dict[str, Any]:
    latest = str(info.get("latest") or "")
    return {**info, "enabled": state.update_check_enabled, "skipped": bool(latest) and state.update_skipped_version == latest,
            "can_install": _is_main_device(request) and sys.platform == "win32" and bool(info.get("installer")), "version": version.APP_VERSION_LABEL}


@router.get("/api/update/status")
async def update_status(request: Request) -> JSONResponse:
    return JSONResponse(_update_payload(request, updater.cached()), headers={"Cache-Control": "no-store"})


@router.post("/api/update/check")
async def update_check(request: Request) -> JSONResponse:
    """Prueft jetzt (Netzwerk, hoechstens ein paar Sekunden; ohne Netz state "error")."""
    return JSONResponse(_update_payload(request, await updater.check(force=True)), headers={"Cache-Control": "no-store"})


@router.post("/api/update/skip")
async def update_skip(request: Request) -> JSONResponse:
    """'Diese Version nicht mehr anzeigen': fuer genau diese Version; eine neuere meldet sich wieder."""
    body = await request.json()
    tag = str(body.get("version") or "") if isinstance(body, dict) else ""
    if updater.parse_version(tag) is None:
        return JSONResponse({"ok": False, "error": "invalid_version"}, status_code=400)
    state.update_skipped_version = tag
    state.save_app_config()
    return JSONResponse({"ok": True})


@router.post("/api/update/enabled")
async def update_enabled(request: Request) -> JSONResponse:
    body = await request.json()
    state.update_check_enabled = bool(body.get("enabled")) if isinstance(body, dict) else True
    state.save_app_config()
    return JSONResponse({"ok": True, "enabled": state.update_check_enabled})


@router.post("/api/update/download")
async def update_download(request: Request) -> JSONResponse:
    if not _is_main_device(request):
        return JSONResponse({"ok": False, "error": "main_device_only"}, status_code=403)
    info = updater.cached()
    installer = info.get("installer") if info.get("state") == "available" else None
    if not installer:
        return JSONResponse({"ok": False, "error": "no_installer"}, status_code=409)
    started = updater.start_download(installer)
    return JSONResponse({"ok": True, "started": started})


@router.get("/api/update/progress")
async def update_progress() -> JSONResponse:
    info = updater.progress()
    return JSONResponse({k: v for k, v in info.items() if k != "path"}, headers={"Cache-Control": "no-store"})


@router.post("/api/update/arm")
async def update_arm(request: Request) -> JSONResponse:
    """Setup fuer das Programmende vormerken; danach beendet der Benutzer OpenCue wie immer (Speichern-Dialog), und main.py startet das Setup."""
    if not _is_main_device(request):
        return JSONResponse({"ok": False, "error": "main_device_only"}, status_code=403)
    return JSONResponse({"ok": updater.arm()})


@router.post("/api/update/disarm")
async def update_disarm() -> JSONResponse:
    updater.disarm()
    return JSONResponse({"ok": True})
