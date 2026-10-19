"""
file_manager.py
Schnittstelle des Dateimanagers (Dialog "Dateimanager" in der Oberflaeche): ein gemeinsamer Blick auf alle Dateiarten des Datenordners
(Shows, Layouts, 3D-Buehnen, Effekte, Farbprofile, Scheinwerfer-Dateien), dazu Download, Upload, Import/Export als ZIP und das Export-Paket einer Show.

Aufgaben-Teilung: Oeffnen, Umbenennen, Duplizieren und Loeschen bleiben bei den bestehenden Schnittstellen der Dateiarten (/api/layouts*, /api/sim-stage*,
/api/showfiles*, /api/effects, /api/library/installed) - sie kennen die Besonderheiten (geladene Show, aktives Layout, aktive Buehne). Neu ist hier:
  GET  /api/files/{kind}                 Liste (einheitliche Zeilen: id = Dateiname, name, size, modified, detail, active)
  GET  /api/files/download               eine Datei oder mehrere/alle Dateien einer Art als ZIP (Browser-Download); ?kind=&id=...  oder  ?kinds=a,b (alles sichern)
  POST /api/files/open-download          oeffnet im Programmfenster den Standard-Browser mit der Download-Adresse (dort laeuft ein gewoehnlicher Download)
  POST /api/files/{kind}/upload          eine Datei (roher Body, ?filename=); eine ZIP-Datei wird wie /api/files/import behandelt. Nie ueberschreiben: gleicher Name + gleicher
                                         Inhalt = uebersprungen, gleicher Name + anderer Inhalt = Kopie unter freiem Namen "Name (2)"
  POST /api/files/import                 ZIP: Sicherung oder Export-Paket einer Show (siehe unten); gleiche Regel; die Show zeigt auf ihre Kopien
  GET  /api/files/export-show/info       was das Export-Paket der geladenen Show enthalten koennte (je Eintrag einzeln waehlbar)
  GET  /api/files/export-show            das Export-Paket als ZIP (?fixture=<id>&effect=<name>&media=<id>&layout=<datei>&stream=<id>&stage=1, je Eintrag wiederholbar)
  POST /api/files/effects/rename|duplicate|favorite
  POST /api/files/effects/restore-defaults   fehlende mitgelieferte Effekte wieder anlegen (nie ueberschreiben)
Export-Paket (ZIP): manifest.json, show.json (nur die Show selbst: Scheinwerfer, Cues, Presets, Effekt-Definitionen ...), fixtures/*.gdtf (benutzte Typen), effects/*.fx (benutzte
Skripte), stages/<Name>.json (die aktive Buehne), media/<sha256> (die Medien der Show), layouts/*.json, streams.json (Quellen OHNE Passwoerter). In der Show selbst steht nichts
davon; jeder Punkt ist im Export-Dialog abwaehlbar. Beim Import wird alles geprueft wie beim Einzel-Upload; vorhandene lokale Dateien bleiben (sie gewinnen).
Alle Download-Adressen sind gewoehnliche GET-Adressen: lokale Verbindungen brauchen keine Anmeldung, entfernte Geraete haben ihre Sitzung im Cookie.
"""
from __future__ import annotations

import asyncio
import hashlib
import io
import json
import os
import re
import tempfile
import time
import urllib.parse
import webbrowser
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response

from app import fixture_library, media_store, remote, sim_stages, stream_sources
from app import paths as _paths
from app.fx_script import FxScriptError, compile_script, registry, restore_default_effects, valid_script_name
from app.state_manager import state
from app.window_signals import file_dialog

router = APIRouter()

KINDS = ("shows", "layouts", "stages", "effects", "themes", "fixtures")
EXTENSIONS = {"shows": ".json", "layouts": ".json", "stages": ".json", "effects": ".fx", "themes": ".json", "fixtures": ".gdtf"}
MAX_UPLOAD_BYTES = 400 * 1024 * 1024         # eine Datei bzw. ein ZIP
MAX_ZIP_UNPACKED = 2 * 1024 * 1024 * 1024    # Summe aller Eintraege eines ZIP
MAX_ZIP_ENTRIES = 5000
_RESERVED = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}
_FORBIDDEN = re.compile(r'[\\/:*?"<>|\x00-\x1f]')

_open_browser = webbrowser.open               # Tests tauschen das aus


class FileError(Exception):
    def __init__(self, code: str, message: str = "", status: int = 400, **extra: Any) -> None:
        super().__init__(message or code)
        self.code, self.message, self.status, self.extra = code, message or code, status, extra

    def response(self) -> JSONResponse:
        return JSONResponse({"ok": False, "error": self.code, "message": self.message, **self.extra}, status_code=self.status)


# ------------------------------------------------------------------------------------------------ Namen und Ordner
def safe_stem(name: Any, fallback: str = "datei") -> str:
    """Dateiname ohne Endung aus einem Anzeigenamen (wie die Layout-/Show-Namen: verbotene Zeichen -> _, hoechstens 60 Zeichen)."""
    text = _FORBIDDEN.sub("_", str(name or "").strip()).strip(". ")[:60]
    if not text or text.split(".")[0].upper() in _RESERVED:
        return fallback
    return text


def kind_dir(kind: str) -> Path:
    if kind == "shows":
        return _paths.SHOWFILES_DIR
    if kind == "layouts":
        return _paths.LAYOUTS_DIR
    if kind == "stages":
        return sim_stages.library_dir()
    if kind == "effects":
        return _paths.effects_dir()
    if kind == "themes":
        return _paths.themes_dir()
    if kind == "fixtures":
        return _paths.FIXTURES_DIR
    raise FileError("unknown_kind", "Unbekannte Dateiart", 404)


def _check_kind(kind: str) -> str:
    if kind not in KINDS:
        raise FileError("unknown_kind", "Unbekannte Dateiart", 404)
    return kind


def resolve(kind: str, file_id: str) -> Path:
    """Datei zu einer Zeilen-Id (= Dateiname); nur einfache Dateinamen mit der Endung der Art, die direkt im Ordner der Art liegen."""
    _check_kind(kind)
    if not isinstance(file_id, str) or not file_id or file_id != Path(file_id).name or file_id.startswith(".") or "\x00" in file_id:
        raise FileError("invalid_name", "Ungueltiger Dateiname", 400)
    if not file_id.lower().endswith(EXTENSIONS[kind]):
        raise FileError("invalid_name", "Falsche Dateiendung", 400)
    path = kind_dir(kind) / file_id
    if not path.is_file():
        raise FileError("not_found", "Datei nicht gefunden", 404)
    return path


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name("." + path.name + ".part")
    try:
        partial.write_bytes(data)
        os.replace(partial, path)
    finally:
        if partial.exists():
            partial.unlink()


def _unique_name(base: str, taken) -> str:
    """Freier Name: 'X', sonst 'X (2)', 'X (3)' ..."""
    if not taken(base):
        return base
    n = 2
    while taken(f"{base} ({n})"):
        n += 1
    return f"{base} ({n})"


# ------------------------------------------------------------------------------------------------ Listen
_HEAD_KEYS = ("showfile_name", "saved_at")


def _show_head(path: Path) -> Dict[str, Any]:
    """Name und Speicherzeit stehen am Anfang der Showfile: grosse Dateien (Medien) muessen nicht komplett gelesen werden."""
    with open(path, "rb") as handle:
        head = handle.read(4096).decode("utf-8", "replace")
    out: Dict[str, Any] = {}
    for key in _HEAD_KEYS:
        match = re.search(r'"' + key + r'"\s*:\s*("(?:[^"\\]|\\.)*")', head)
        if match:
            try:
                out[key] = json.loads(match.group(1))
            except ValueError:
                pass
    return out


def _default_radius() -> int:
    from app.state_manager import DEFAULT_RADIUS
    return DEFAULT_RADIUS


def _same(a: Optional[str], b: Path) -> bool:
    try:
        return bool(a) and Path(a).resolve() == b.resolve()
    except (OSError, ValueError):
        return False


def rows(kind: str) -> List[Dict[str, Any]]:
    _check_kind(kind)
    out: List[Dict[str, Any]] = []
    directory = kind_dir(kind)
    if kind == "shows":
        for path in sorted(directory.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            head = _show_head(path)
            stat = path.stat()
            active = _same(state.showfile_path, path)
            out.append({"id": path.name, "name": head.get("showfile_name", path.stem), "size": stat.st_size, "modified": int(stat.st_mtime),
                        "detail": str(head.get("saved_at", "")).replace("T", " "), "active": active, "dirty": bool(active and state.is_dirty), "path": str(path)})
    elif kind == "layouts":
        for path in sorted(directory.glob("*.json"), key=lambda p: p.name.lower()):
            stat = path.stat()
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                name, panels, favorite = str(data.get("name", path.stem)), len(data.get("panels") or []), bool(data.get("is_favorite", False))
            except (OSError, ValueError, AttributeError):
                name, panels, favorite = path.stem, 0, False
            out.append({"id": path.name, "name": name, "size": stat.st_size, "modified": int(stat.st_mtime), "detail": str(panels), "favorite": favorite,
                        "active": name == state.last_active_layout})
    elif kind == "stages":
        sim_stages.store.ensure()
        for item in sim_stages.list_files():
            path = directory / item["filename"]
            out.append({"id": item["filename"], "name": item["name"], "size": path.stat().st_size if path.is_file() else 0, "modified": item["modified"],
                        "detail": str(item["objects"]), "active": item["filename"] == sim_stages.store.filename})
    elif kind == "effects":
        from app import server as S
        registry.load(S._effect_sources())
        used: Dict[str, int] = {}
        for definition in state.fx_effects.values():
            used[str(definition.get("kind", ""))] = used.get(str(definition.get("kind", "")), 0) + 1
        for entry in registry.files():
            if entry["origin"] != "user":
                continue
            path = Path(entry["path"])
            if not path.is_file():
                continue
            script = registry.get(entry["name"])
            stat = path.stat()
            out.append({"id": path.name, "name": script.label if script else entry["name"], "size": stat.st_size, "modified": int(stat.st_mtime),
                        "detail": entry.get("category") or "", "ok": bool(entry["ok"]), "message": "" if entry["ok"] else str(entry.get("message", "")),
                        "in_use": used.get(entry["name"], 0), "active": False,
                        "favorite": entry["name"] in state.fx_favorites, "default": bool(entry.get("default"))})
        out.sort(key=lambda r: r["name"].lower())
    elif kind == "themes":
        state.reload_theme_profiles()                                   # Dateien sind die Wahrheit (auch von Hand dazugelegte)
        current = state.theme_payload()
        for builtin_id, label, key, base in (("builtin:dark", "Dark", "THEME_BASE_DARK", "dark"), ("builtin:light", "Light", "THEME_BASE_LIGHT", "light")):
            out.append({"id": builtin_id, "name": label, "name_key": key, "size": 0, "modified": 0, "detail": base, "builtin": True,
                        "theme": {"base": base, "tokens": {}, "radius": _default_radius()}, "active": current == {"base": base, "tokens": {}, "radius": _default_radius()}})
        for name, theme in sorted(state.theme_profiles.items(), key=lambda kv: kv[0].lower()):
            filename = state._theme_files.get(name, "")
            path = directory / filename if filename else None
            stat = path.stat() if path is not None and path.is_file() else None
            out.append({"id": filename, "name": name, "size": stat.st_size if stat else 0, "modified": int(stat.st_mtime) if stat else 0, "detail": theme["base"],
                        "theme": theme, "active": current == theme})
    else:
        usage: Dict[str, int] = {}
        for fx in state.fixtures.values():
            usage[fx.fixture_type] = usage.get(fx.fixture_type, 0) + 1
        for item in fixture_library.installed_entries(usage):
            out.append({"id": item["file"], "name": f"{item['manufacturer']} – {item['name']}", "size": item["size"], "modified": item["installed_at"],
                        "detail": f"{item['category']} · {len(item['modes'])}", "in_use": item["in_use"], "active": bool(item["in_use"]), "error": item.get("error")})
    return out


@router.get("/api/files/export-show/info")
async def export_info() -> JSONResponse:
    return JSONResponse(await asyncio.to_thread(show_package_info))


@router.get("/api/files/export-show")
async def export_show(request: Request) -> Response:
    """Das Paket der geladenen Show. Was hinein soll, steht in wiederholten Abfrage-Parametern: fixture=<Typ-Id>, effect=<Skriptname>, media=<Id>, layout=<Dateiname>,
    stream=<Id>, stage=1. Nicht Genanntes kommt nicht ins Paket."""
    q = request.query_params
    options = {"fixtures": q.getlist("fixture"), "effects": q.getlist("effect"), "media": q.getlist("media"), "layouts": q.getlist("layout"), "streams": q.getlist("stream"),
               "stage": q.get("stage", "0") in ("1", "true")}
    data, name = await asyncio.to_thread(build_show_package, options)
    return _download(data, f"{name}.zip", "application/zip")


@router.get("/api/files/download")
async def download(request: Request) -> Response:
    q = request.query_params
    try:
        kind = q.get("kind", "")
        ids = q.getlist("id")
        if q.get("kinds"):                                           # alles sichern: alle Dateien der genannten Arten
            kinds = [k for k in q["kinds"].split(",") if k in KINDS]
            data = await asyncio.to_thread(_zip_files, [(k, p) for k in kinds for p in _all_files(k)])
            return _download(data, f"opencue-sicherung-{time.strftime('%Y%m%d-%H%M')}.zip", "application/zip")
        _check_kind(kind)
        files = [resolve(kind, i) for i in ids] if ids else _all_files(kind)
        if not files:
            raise FileError("not_found", "Nichts zum Herunterladen", 404)
        if len(files) == 1 and ids:
            media_type = {"shows": "application/json", "layouts": "application/json", "stages": "application/json", "themes": "application/json", "effects": "text/plain; charset=utf-8"}.get(kind, "application/octet-stream")
            return _download(await asyncio.to_thread(files[0].read_bytes), files[0].name, media_type)
        data = await asyncio.to_thread(_zip_files, [(kind, p) for p in files])
        return _download(data, f"opencue-{kind}.zip", "application/zip")
    except FileError as exc:
        return exc.response()


def _all_files(kind: str) -> List[Path]:
    directory = kind_dir(kind)
    if not directory.is_dir():
        return []
    return [p for p in sorted(directory.glob("*" + EXTENSIONS[kind])) if p.is_file() and not p.name.startswith(".")]


def _zip_files(entries: List[Tuple[str, Path]]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for kind, path in entries:
            archive.write(path, f"{kind}/{path.name}")
    return buffer.getvalue()


def _download(data: bytes, filename: str, media_type: str) -> Response:
    quoted = urllib.parse.quote(filename)
    fallback = re.sub(r"[^A-Za-z0-9._ -]", "_", filename) or "download"
    return Response(content=data, media_type=media_type, headers={
        "Content-Disposition": f"attachment; filename=\"{fallback}\"; filename*=UTF-8''{quoted}", "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})


@router.post("/api/files/open-download")
async def open_download(request: Request) -> JSONResponse:
    """Im Programmfenster (pywebview) gibt es keinen Browser-Download: stattdessen oeffnet der Server den Standard-Browser mit der Download-Adresse.
    Entfernte Geraete (und Tests) bekommen opened=false und laden die Adresse selbst herunter."""
    body = await request.json()
    url = str(body.get("url", ""))
    if not (url.startswith("/api/files/download?") or url.startswith("/api/files/export-show?")):
        return JSONResponse({"ok": False, "error": "invalid_url"}, status_code=400)
    host = request.client.host if request.client else None
    if not (remote.is_local(host) and file_dialog.available):
        return JSONResponse({"ok": True, "opened": False})
    await asyncio.to_thread(_open_browser, f"http://127.0.0.1:{state.server_port}{url}")
    return JSONResponse({"ok": True, "opened": True})


@router.get("/api/files/{kind}")
async def list_kind(kind: str) -> JSONResponse:
    try:
        return JSONResponse({"kind": kind, "path": str(kind_dir(_check_kind(kind))), "rows": await asyncio.to_thread(rows, kind)})
    except FileError as exc:
        return exc.response()


# ------------------------------------------------------------------------------------------------ Einzelne Datei einlesen (Upload und ZIP)
# Regel fuer jeden Import: nie zwei Dateien mit demselben Namen, nie etwas ueberschreiben.
#   - gleicher Name UND gleicher Inhalt  -> nichts wird geschrieben (status "identical")
#   - gleicher Name, anderer Inhalt      -> die neue Datei kommt unter einem freien Namen "<Name> (2)", "(3)" ... dazu (status "copy")
#   - Name frei                          -> neu angelegt (status "created")
def _bool(value: Any) -> bool:
    return str(value).lower() in ("1", "true", "yes")


def _norm_text(data: bytes) -> str:
    return data.decode("utf-8-sig", "replace").replace("\r\n", "\n").strip()


def _free_name(base: str, path_of, same) -> Tuple[str, bool]:
    """(Name, identisch): 'base', sonst 'base (2)' ...; stoesst der Name auf eine Datei mit gleichem Inhalt (same(path)), ist es dieselbe Datei (identisch=True)."""
    n = 1
    while True:
        name = base if n == 1 else f"{base} ({n})"
        path = path_of(name)
        if not path.exists():
            return name, False
        if same(path):
            return name, True
        n += 1


def _status(file_id: str, name: str, identical: bool, original: str) -> Dict[str, Any]:
    status = "identical" if identical else ("created" if name == original else "copy")
    return {"ok": True, "id": file_id, "name": name, "status": status, "original": original if status == "copy" else None, "replaced": False}


def _json_equal(a: Any, b: Any, ignore: Tuple[str, ...]) -> bool:
    if not isinstance(a, dict) or not isinstance(b, dict):
        return False
    return {k: v for k, v in a.items() if k not in ignore} == {k: v for k, v in b.items() if k not in ignore}


def import_one(kind: str, filename: str, data: bytes) -> Dict[str, Any]:
    """Prueft eine Datei der Art 'kind' und legt sie im Ordner der Art ab (Regel siehe oben). Rueckgabe: {ok, id, name, status, original}. Wirft FileError."""
    _check_kind(kind)
    if len(data) > MAX_UPLOAD_BYTES:
        raise FileError("too_large", "Die Datei ist zu gross", 413)
    stem = safe_stem(Path(filename).stem, "datei")
    if kind in ("shows", "layouts"):
        try:
            content = json.loads(data.decode("utf-8-sig"))
        except (UnicodeDecodeError, ValueError):
            raise FileError("invalid_file", "Keine gueltige JSON-Datei", 400) from None
        if not isinstance(content, dict):
            raise FileError("invalid_file", "Keine OpenCue-Datei", 400)
        directory = kind_dir(kind)
        if kind == "shows":
            if not (isinstance(content.get("fixtures"), dict) or isinstance(content.get("cuelists"), dict) or isinstance(content.get("cues"), list)):
                raise FileError("invalid_file", "Das ist keine OpenCue-Show", 400)
            original, key, ignore = str(content.get("showfile_name") or stem), "showfile_name", ("saved_at", "showfile_name")
        else:
            panels = content.get("panels")
            if not isinstance(panels, list) or not all(isinstance(p, dict) and p.get("type") for p in panels):
                raise FileError("invalid_file", "Das ist kein OpenCue-Layout", 400)
            original, key, ignore = str(content.get("name") or stem), "name", ("name", "created_at", "is_favorite")

        def same(path: Path) -> bool:
            try:
                return _json_equal(json.loads(path.read_text(encoding="utf-8")), content, ignore)
            except (OSError, ValueError):
                return False
        name, identical = _free_name(original, lambda n: directory / (safe_stem(n, stem) + ".json"), same)
        path = directory / (safe_stem(name, stem) + ".json")
        if not identical:
            if name != original:
                content[key] = name
            _atomic_write(path, json.dumps(content, indent=2, ensure_ascii=False).encode("utf-8") if name != original else data)
        return _status(path.name, name, identical, original)
    if kind == "stages":
        try:
            unit = sim_stages._read_text(data.decode("utf-8-sig"))
        except sim_stages.StageError as exc:
            raise FileError("invalid_file", "Das ist keine OpenCue-Buehne", 400, detail=str(exc)) from None
        except UnicodeDecodeError:
            raise FileError("invalid_file", "Keine gueltige Datei", 400) from None
        original = sim_stages.clean_name(unit.get("name"), stem)
        objects = sim_stages.normalize_objects(unit.get("objects"))
        digest = sim_stages.digest(objects)

        def same_stage(path: Path) -> bool:
            try:
                return sim_stages.digest(sim_stages.read_file(path.name)["objects"]) == digest
            except sim_stages.StageError:
                return False
        name, identical = _free_name(original, lambda n: sim_stages.library_dir() / sim_stages.filename_for(n), same_stage)
        filename = sim_stages.filename_for(name)
        if not identical:
            try:
                filename = sim_stages.write_file(name, objects, overwrite=False)
            except sim_stages.StageError as exc:
                raise FileError("invalid_file", "Die Buehne ist ungueltig", 400, detail=str(exc)) from None
        return _status(filename, name, identical, original)
    if kind == "themes":
        try:
            content = json.loads(data.decode("utf-8-sig"))
        except (UnicodeDecodeError, ValueError):
            raise FileError("invalid_file", "Keine gueltige JSON-Datei", 400) from None
        raw = content.get("theme") if isinstance(content, dict) and isinstance(content.get("theme"), dict) else content
        if not isinstance(raw, dict) or not ("tokens" in raw or "base" in raw):
            raise FileError("invalid_file", "Das ist kein OpenCue-Farbprofil", 400)
        name = (content.get("name") if isinstance(content, dict) else None) or stem
        try:
            result = state.import_theme_profile(str(name), raw)
        except ValueError:
            raise FileError("too_many", "Zu viele Farbprofile", 400) from None
        return {"ok": True, "id": result["file"], "name": result["name"], "status": result["status"], "original": result["original"], "replaced": False}
    if kind == "effects":
        original = filename[:-3] if filename.lower().endswith(".fx") else Path(filename).stem
        if not valid_script_name(original):
            raise FileError("invalid_name", "Ungueltiger Effektname", 400)
        try:
            text = data.decode("utf-8-sig")
            compile_script(original, text)
        except UnicodeDecodeError:
            raise FileError("invalid_file", "Keine Textdatei", 400) from None
        except FxScriptError as exc:
            raise FileError("invalid_file", f"Das Skript ist fehlerhaft: {exc.message}", 400, line=exc.line) from None
        directory = _paths.effects_dir()

        def same_script(path: Path) -> bool:
            try:
                return _norm_text(path.read_bytes()) == _norm_text(data)
            except OSError:
                return False
        name, identical = _free_name(original, lambda n: directory / f"{n}.fx", same_script)
        if not identical:
            _atomic_write(directory / f"{name}.fx", text.encode("utf-8"))
        return _status(f"{name}.fx", name, identical, original)
    usage: Dict[str, int] = {}
    for fx in state.fixtures.values():
        usage[fx.fixture_type] = usage.get(fx.fixture_type, 0) + 1
    try:
        result = fixture_library.install_bytes(data, filename, "", usage, on_conflict="copy")
    except fixture_library.LibraryError as exc:
        raise FileError("invalid_file", exc.message, exc.status) from None
    label = f"{result['manufacturer']} – {result['name']}"
    if result.get("identical"):
        status, original = "identical", None
    elif result.get("copied_from"):
        status, original = "copy", result["copied_from"]
    else:
        status, original = "created", None
    return {"ok": True, "id": result["id"] + ".gdtf", "name": label, "status": status, "original": original, "replaced": False}


@router.post("/api/files/import")
async def import_zip(request: Request) -> JSONResponse:
    body = await request.body()
    try:
        result = await asyncio.to_thread(import_package, body)
    except FileError as exc:
        return exc.response()
    for kind in KINDS:
        await _announce(kind)
    return JSONResponse(result)


@router.post("/api/files/{kind}/upload")
async def upload(kind: str, request: Request) -> JSONResponse:
    filename = Path(urllib.parse.unquote(request.query_params.get("filename", ""))).name
    body = await request.body()
    try:
        _check_kind(kind)
        if not filename:
            raise FileError("invalid_name", "Dateiname fehlt", 400)
        if filename.lower().endswith(".zip"):
            result = await asyncio.to_thread(import_package, body)
            for each in KINDS:
                await _announce(each)
            return JSONResponse(result)
        if not filename.lower().endswith(EXTENSIONS[kind]):
            raise FileError("invalid_name", f"Erwartet wird eine {EXTENSIONS[kind]}-Datei", 400)
        result = await asyncio.to_thread(import_one, kind, filename, body)
    except FileError as exc:
        return exc.response()
    await _announce(kind)
    return JSONResponse(result)


async def _announce(kind: str) -> None:
    """Andere Dialoge/Panels aktualisieren sich (Listen, Dropdowns)."""
    from app import server as S
    if kind == "shows":
        await S._announce_showfiles_changed()
    elif kind == "effects":
        registry.load(S._effect_sources())
        await S.event_bus.broadcast(S._fx_changed_message())
        await S.event_bus.broadcast(S._fx_script_list_message())
    elif kind == "fixtures":
        await S._broadcast_library_changed()
    elif kind == "themes":
        state.reload_theme_profiles()
        await S.event_bus.broadcast({"type": "theme_profiles_changed", "payload": {"profiles": state.theme_profiles_payload()}})
    elif kind == "layouts":
        await S.event_bus.broadcast({"type": "layout_status_changed", "payload": {}})
    elif kind == "stages":
        await S.event_bus.broadcast({"type": "sim_stage_library_changed", "payload": {}})


# ------------------------------------------------------------------------------------------------ Import eines ZIP (Sicherung / Export-Paket)
def _zip_entries(archive: zipfile.ZipFile) -> List[zipfile.ZipInfo]:
    infos = [i for i in archive.infolist() if not i.is_dir()]
    if len(infos) > MAX_ZIP_ENTRIES or sum(i.file_size for i in infos) > MAX_ZIP_UNPACKED:
        raise FileError("too_large", "Das ZIP ist zu gross", 413)
    return infos


def _entry_parts(name: str) -> Tuple[str, str]:
    """('ordner', 'datei') eines ZIP-Eintrags; nur eine Ebene tief, keine absoluten/aufwaertsfuehrenden Pfade."""
    parts = [p for p in name.replace("\\", "/").split("/") if p]
    if not parts or any(p in (".", "..") or ":" in p for p in parts) or len(parts) > 2:
        return "", ""
    return (parts[0], parts[1]) if len(parts) == 2 else ("", parts[0])


def _remap_show(content: Dict[str, Any], maps: Dict[str, Dict[str, str]]) -> None:
    """Hat eine Datei des Pakets unter neuem Namen (Kopie) angelegt werden muessen, zeigt die Show danach auf diese Kopie (sie behaelt so genau ihre Dateien)."""
    for fx in (content.get("fixtures") or {}).values():
        if isinstance(fx, dict) and fx.get("fixture_type") in maps["fixtures"]:
            fx["fixture_type"] = maps["fixtures"][fx["fixture_type"]]
    for definition in (content.get("fx_effects") or {}).values():
        if isinstance(definition, dict) and definition.get("kind") in maps["effects"]:
            definition["kind"] = maps["effects"][definition["kind"]]
    stage = content.get("sim_stage")
    if isinstance(stage, dict) and stage.get("filename") in maps["stages"]:
        stage["filename"] = maps["stages"][stage["filename"]]


def import_package(data: bytes) -> Dict[str, Any]:
    """ZIP einlesen (Export-Paket einer Show oder Sicherung). Regel: nie ueberschreiben, nie doppelte Namen (siehe import_one): Gleiches wird uebersprungen, Abweichendes kommt als
    Kopie "Name (2)" dazu, und die Show zeigt dann auf die Kopie. Rueckgabe: {ok, imported: {art: n}, skipped: {art: n}, copies: [{kind, from, to}], errors: [..], show: Dateiname | None}."""
    if len(data) > MAX_UPLOAD_BYTES * 5:
        raise FileError("too_large", "Das ZIP ist zu gross", 413)
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        raise FileError("invalid_file", "Kein gueltiges ZIP", 400) from None
    imported: Dict[str, int] = {}
    skipped: Dict[str, int] = {}
    copies: List[Dict[str, str]] = []
    errors: List[Dict[str, str]] = []
    maps: Dict[str, Dict[str, str]] = {"fixtures": {}, "effects": {}, "stages": {}}
    show_file: Optional[str] = None

    def count(bucket: Dict[str, int], kind: str) -> None:
        bucket[kind] = bucket.get(kind, 0) + 1

    def take(kind: str, result: Dict[str, Any], old_id: str) -> None:
        if result["status"] == "identical":
            count(skipped, kind)
            return
        count(imported, kind)
        if result["status"] == "copy":
            copies.append({"kind": kind, "from": result["original"], "to": result["name"]})
            if kind in maps:
                strip = {"fixtures": 5, "effects": 3, "stages": 0}[kind]
                maps[kind][old_id[:-strip] if strip else old_id] = result["id"][:-strip] if strip else result["id"]

    with archive:
        infos = _zip_entries(archive)
        show_info = None
        media_names: Dict[str, str] = {}
        for info in infos:
            if _entry_parts(info.filename) == ("", "show.json"):
                show_info = info
                try:
                    for mid, entry in (json.loads(archive.read(info).decode("utf-8-sig")).get("media") or {}).items():
                        media_names[str(mid)] = str((entry or {}).get("name", mid))
                except (ValueError, AttributeError, UnicodeDecodeError):
                    pass
        for info in infos:                                            # 1. alle Dateien ausser der Show (damit feststeht, ob Kopien angelegt wurden)
            folder, name = _entry_parts(info.filename)
            if not name or name.startswith(".") or name == "manifest.json" or (folder, name) == ("", "show.json"):
                continue
            try:
                raw = archive.read(info)
                if folder in KINDS and name.lower().endswith(EXTENSIONS[folder]):
                    take(folder, import_one(folder, name, raw), name)
                elif folder == "media" and media_store.ID_RE.match(name):
                    if hashlib.sha256(raw).hexdigest() != name:
                        raise FileError("invalid_file", "Pruefsumme stimmt nicht", 400)
                    target = media_store.path_for(name)
                    if target is not None and target.is_file():
                        count(skipped, "media")
                    else:
                        _ingest_media(raw, name, media_names.get(name, name))
                        count(imported, "media")
                elif (folder, name) == ("", "streams.json"):
                    added = _import_streams(raw)
                    if added:
                        imported["streams"] = added
            except FileError as exc:
                errors.append({"entry": info.filename, "message": exc.message})
            except Exception as exc:                                   # ein kaputter Eintrag stoppt den Rest nicht
                errors.append({"entry": info.filename, "message": f"{type(exc).__name__}: {exc}"})
        if show_info is not None:                                      # 2. die Show (mit umgeleiteten Verweisen)
            try:
                content = json.loads(archive.read(show_info).decode("utf-8-sig"))
                if not isinstance(content, dict):
                    raise FileError("invalid_file", "Keine OpenCue-Show", 400)
                _remap_show(content, maps)
                result = import_one("shows", safe_stem(content.get("showfile_name") or "Show", "show") + ".json", json.dumps(content, indent=2, ensure_ascii=False).encode("utf-8"))
                show_file = result["id"]
                take("shows", result, result["id"])
            except FileError as exc:
                errors.append({"entry": "show.json", "message": exc.message})
            except (ValueError, UnicodeDecodeError):
                errors.append({"entry": "show.json", "message": "Keine gueltige JSON-Datei"})
    return {"ok": True, "imported": imported, "skipped": skipped, "copies": copies, "errors": errors, "show": show_file}


def _ingest_media(raw: bytes, digest: str, display_name: str) -> None:
    store = media_store.store_dir()
    store.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=".import-", suffix=".part", dir=str(store))
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(raw)
        media_store.ingest(Path(tmp_name), display_name, len(raw), digest, None)
    except media_store.MediaError as exc:
        raise FileError(exc.code, exc.message, exc.status) from None
    finally:
        Path(tmp_name).unlink(missing_ok=True)


def _import_streams(raw: bytes) -> int:
    """Stream-Quellen aus einem Paket: nur neue Ids; Passwoerter gibt es im Paket nie."""
    try:
        sources = json.loads(raw.decode("utf-8-sig")).get("sources")
    except (ValueError, AttributeError, UnicodeDecodeError):
        raise FileError("invalid_file", "streams.json ist ungueltig", 400) from None
    existing = {r["id"] for r in stream_sources._load()}
    added = 0
    rows_now = stream_sources._load()
    for item in sources or []:
        if not isinstance(item, dict) or not re.fullmatch(r"[0-9a-f-]{36}", str(item.get("id", ""))) or item["id"] in existing:
            continue
        try:
            url, user, _password = stream_sources.clean_url(item.get("url", ""))
        except Exception:
            continue
        rows_now.append({"id": item["id"], "name": re.sub(r"\s+", " ", str(item.get("name", "")).strip())[:60] or "Stream", "url": url,
                         "type": item.get("type") if item.get("type") in stream_sources.TYPES else "auto", "user": str(item.get("user", "") or user)[:120],
                         "proxy": bool(item.get("proxy", False))})
        added += 1
    if added:
        stream_sources._save(rows_now)
    return added


# ------------------------------------------------------------------------------------------------ Export-Paket der geladenen Show
def _used_fixture_types() -> List[str]:
    return sorted({fx.fixture_type for fx in state.fixtures.values()})


def _used_effect_scripts() -> List[str]:
    return sorted({str(fx.get("kind", "")) for fx in state.fx_effects.values() if valid_script_name(str(fx.get("kind", "")))})


def _fixture_label(fixture_id: str) -> str:
    parts = fixture_id.split("@")
    return f"{parts[0]} – {parts[1].replace('_', ' ')}" + (f" ({parts[2].replace('_', ' ')})" if len(parts) > 2 else "") if len(parts) >= 2 else fixture_id


def show_package_info() -> Dict[str, Any]:
    """Was in das Paket der geladenen Show kommen koennte: die benutzten Scheinwerfertypen und Effekt-Skripte, die Medien der Show, alle Layouts und Stream-Quellen
    (je Eintrag einzeln waehlbar); present = die Datei gibt es auf diesem Computer."""
    fixtures = []
    for fixture_id in _used_fixture_types():
        path = _paths.FIXTURES_DIR / f"{fixture_id}.gdtf"
        fixtures.append({"id": fixture_id, "name": _fixture_label(fixture_id), "size": path.stat().st_size if path.is_file() else 0, "present": path.is_file(),
                         "count": sum(1 for fx in state.fixtures.values() if fx.fixture_type == fixture_id)})
    effects = [{"name": name, "present": (_paths.effects_dir() / f"{name}.fx").is_file()} for name in _used_effect_scripts()]
    media = []
    for meta in state.media.values():
        path = media_store.file_path(meta)
        media.append({"id": meta["id"], "name": meta.get("name", ""), "size": int(meta.get("size", 0)), "kind": meta.get("kind", ""), "present": bool(path and path.is_file())})
    layouts = []
    for path in _all_files("layouts"):
        try:
            layouts.append({"id": path.name, "name": str(json.loads(path.read_text(encoding="utf-8")).get("name", path.stem))})
        except (OSError, ValueError, AttributeError):
            layouts.append({"id": path.name, "name": path.stem})
    streams = [{"id": r["id"], "name": r["name"], "url": r["url"]} for r in stream_sources._load()]
    stage = {"name": sim_stages.store.name, "objects": len(sim_stages.store.objects)} if sim_stages.store.ready and sim_stages.store.objects else None
    return {"show": state.showfile_name, "fixtures": fixtures, "effects": effects, "stage": stage, "media": media, "layouts": layouts, "streams": streams, "dirty": bool(state.is_dirty)}


def build_show_package(options: Dict[str, Any]) -> Tuple[bytes, str]:
    """Das Paket der aktuell geladenen Show (so wie sie jetzt im Speicher steht, auch ungespeichert) als ZIP. options: fixtures/effects/media/layouts/streams = Listen der
    gewaehlten Eintraege (Typ-Ids, Skriptnamen, Medien-Ids, Layout-Dateinamen, Stream-Ids), stage = True/False. Es kommt nur hinein, was gewaehlt UND vorhanden ist
    (Scheinwerfertypen und Skripte nur, wenn die Show sie benutzt)."""
    data = state._showfile_dict()
    want = {k: set(options.get(k) or []) for k in ("fixtures", "effects", "media", "layouts", "streams")}
    stage_entry: Optional[Tuple[str, bytes]] = None
    if isinstance(data.get("sim_stage"), dict):
        stage_ref = data["sim_stage"]
        if options.get("stage") and sim_stages.store.objects:
            filename = stage_ref.get("filename") or sim_stages.filename_for(sim_stages.store.name)
            stage_ref["filename"] = filename
            stage_entry = (filename, sim_stages.file_text(sim_stages.store.name, sim_stages.store.objects).encode("utf-8"))
        else:
            stage_ref["filename"] = None
    buffer = io.BytesIO()
    contents: Dict[str, Any] = {}
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("show.json", json.dumps(data, indent=2, ensure_ascii=False))
        files = [_paths.FIXTURES_DIR / f"{fid}.gdtf" for fid in _used_fixture_types() if fid in want["fixtures"]]
        files = [p for p in files if p.is_file()]
        for path in files:
            archive.write(path, f"fixtures/{path.name}")
        contents["fixtures"] = len(files)
        files = [_paths.effects_dir() / f"{name}.fx" for name in _used_effect_scripts() if name in want["effects"]]
        files = [p for p in files if p.is_file()]
        for path in files:
            archive.write(path, f"effects/{path.name}")
        contents["effects"] = len(files)
        if stage_entry:
            archive.writestr(f"stages/{stage_entry[0]}", stage_entry[1])
        contents["stage"] = 1 if stage_entry else 0
        included = 0
        for media_id, meta in state.media.items():
            path = media_store.file_path(meta)
            if media_id in want["media"] and path and path.is_file():
                archive.write(path, f"media/{media_id}")
                included += 1
        contents["media"] = included
        layouts = [p for p in _all_files("layouts") if p.name in want["layouts"]]
        for path in layouts:
            archive.write(path, f"layouts/{path.name}")
        contents["layouts"] = len(layouts)
        streams = [{"id": r["id"], "name": r["name"], "url": r["url"], "type": r.get("type", "auto"), "user": r.get("user", ""), "proxy": bool(r.get("proxy", False))}
                   for r in stream_sources._load() if r["id"] in want["streams"]]            # nie Passwoerter (auch nicht verschluesselt: gelten nur fuer dieses Windows-Konto)
        if streams:
            archive.writestr("streams.json", json.dumps({"sources": streams}, indent=2, ensure_ascii=False))
        contents["streams"] = len(streams)
        archive.writestr("manifest.json", json.dumps({"format": "opencue-show-package", "version": 2, "show": state.showfile_name, "created": time.strftime("%Y-%m-%dT%H:%M:%S"),
                                                     "contents": contents}, indent=2, ensure_ascii=False))
    return buffer.getvalue(), safe_stem(state.showfile_name, "show")


# ------------------------------------------------------------------------------------------------ Effekte: Umbenennen und Duplizieren
def _effect_name(raw: Any) -> str:
    text = str(raw or "").strip()
    text = text[:-3] if text.lower().endswith(".fx") else text
    if not valid_script_name(text):
        raise FileError("invalid_name", "Ungueltiger Effektname", 400)
    return text


@router.post("/api/files/effects/duplicate")
async def effect_duplicate(request: Request) -> JSONResponse:
    body = await request.json()
    try:
        source = resolve("effects", str(body.get("id", "")))
        base = f"{source.stem} ({'Kopie' if state.language == 'de' else 'copy'})"
        name = _unique_name(base, lambda n: (_paths.effects_dir() / f"{n}.fx").exists())
        if not valid_script_name(name):
            raise FileError("invalid_name", "Ungueltiger Effektname", 400)
        await asyncio.to_thread(_atomic_write, _paths.effects_dir() / f"{name}.fx", source.read_bytes())
    except FileError as exc:
        return exc.response()
    await _announce("effects")
    return JSONResponse({"ok": True, "id": f"{name}.fx", "name": name})


@router.post("/api/files/effects/favorite")
async def effect_favorite(request: Request) -> JSONResponse:
    """Lieblings-Stern eines Effekt-Skripts umschalten (gleiche Einstellung wie im Effekt-Studio)."""
    body = await request.json()
    try:
        source = resolve("effects", str(body.get("id", "")))
    except FileError as exc:
        return exc.response()
    favorite = state.toggle_fx_favorite(source.stem)
    await _announce("effects")
    return JSONResponse({"ok": True, "favorite": favorite})


@router.post("/api/files/effects/restore-defaults")
async def effect_restore_defaults() -> JSONResponse:
    """Die mitgelieferten Effekte (defaults/effects), die im Effekte-Ordner fehlen, wieder anlegen. Vorhandene Dateien bleiben unveraendert."""
    try:
        result = await asyncio.to_thread(restore_default_effects, _paths.default_effects_dir(), _paths.effects_dir())
    except OSError as exc:
        return JSONResponse({"error": "write_failed", "message": f"Wiederherstellen fehlgeschlagen: {exc}"}, status_code=500)
    if result["restored"]:
        await _announce("effects")
    return JSONResponse({"ok": True, **result})


@router.post("/api/files/effects/rename")
async def effect_rename(request: Request) -> JSONResponse:
    """Skript umbenennen (nie auf einen vorhandenen Namen). Die Effekt-Definitionen der Show, die es benutzen, folgen; laeuft das Skript gerade, geht es nicht (erst freigeben)."""
    from app.fx_engine import fx_engine
    body = await request.json()
    try:
        source = resolve("effects", str(body.get("id", "")))
        new_name = _effect_name(body.get("new_name"))
        old_name = source.stem
        target = _paths.effects_dir() / f"{new_name}.fx"
        same_file = target.exists() and source.samefile(target)
        if new_name == old_name:
            return JSONResponse({"ok": True, "id": source.name, "name": old_name})
        if fx_engine.count_active(old_name):
            raise FileError("in_use", "Der Effekt laeuft gerade", 409, name=old_name)
        if target.exists() and not same_file:                            # nie derselbe Name zweimal
            raise FileError("exists", "Den Namen gibt es schon", 409, name=new_name)
        if same_file:                                                   # nur Gross-/Kleinschreibung: ueber einen Zwischennamen
            temp = source.with_name(f".{source.name}.rename")
            source.rename(temp)
            temp.rename(target)
        else:
            os.replace(source, target)
    except FileError as exc:
        return exc.response()
    state.forget_fx_favorite(old_name, new_name)                       # die Lieblingsmarke zieht mit um
    changed = 0
    for definition in state.fx_effects.values():
        if definition.get("kind") == old_name:
            definition["kind"] = new_name
            changed += 1
    if changed:
        state.is_dirty = True
    await _announce("effects")
    return JSONResponse({"ok": True, "id": f"{new_name}.fx", "name": new_name, "updated_definitions": changed})
