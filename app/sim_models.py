# Copyright (C) 2026 Samuel Zenker
# SPDX-License-Identifier: GPL-3.0-or-later
"""
sim_models.py
Eigene 3D-Modelle fuer die 3D-Simulation (Bauen -> Hinzufuegen -> Modell): Buehnenteile, Traversen, Moebel, Deko als STL- oder OBJ-Datei.

- Bibliothek: <Datenordner>/models/<Name>.stl. Jede Datei wird beim Einlesen geprueft und EINHEITLICH als binaere STL gespeichert (nur Dreiecke; Normalen rechnet
  die Oberflaeche selbst). OBJ-Dateien werden dabei von "Y oben" (uebliche Export-Vorgabe, z. B. Blender) nach "Z oben" gedreht; STL bleibt, wie sie ist (CAD: Z oben).
- Ein Modell auf der Buehne ist ein Koerper wie Quader oder Zylinder (sim_stages.py, Typ "model", Feld "model" = Dateiname, "unit" = Einheit der Datei): seine Groesse
  ist der Rahmen, in den das Modell gestreckt wird; Position, Drehung, Farbe und Oberflaeche wie bei allen Koerpern. Die Datei selbst steckt NICHT in der Buehne oder
  Showfile - das Export-Paket einer Show nimmt die benutzten Modelle mit (models/<Datei>), fehlt eine Datei, zeigt die Simulation einen Platzhalter.
- Einlesen ueber den Dateimanager (Art "models", /api/files/models/upload) oder direkt aus der Seitenleiste des Baumodus (dieselbe Adresse). Regel wie ueberall:
  nie ueberschreiben (gleicher Name + gleicher Inhalt = uebersprungen, sonst "Name (2)").
Schnittstellen: GET /api/sim-models (Liste), GET /api/sim-models/file/<Datei> (die STL), POST /api/sim-models/rename|duplicate|delete.
Umbenennen und Loeschen eines Modells, das auf der geladenen Buehne steht, wird abgelehnt ("in_use") - sonst wuerde die Buehne ihr Modell verlieren.
"""
from __future__ import annotations

import os
import re
import struct
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response

from app import paths as _paths
from app import sim_stages

router = APIRouter()

EXTENSION = ".stl"
IMPORT_EXTENSIONS = (".stl", ".obj")
MAX_TRIANGLES = 2_000_000                     # ~100 MB binaere STL; ab einigen 100 000 Dreiecken werden schwache Grafikkarten (iPad, Laptop ohne eigene GPU) langsamer
MAX_BYTES = 400 * 1024 * 1024                 # wie die Upload-Grenze des Dateimanagers
UNITS = {"mm": 0.001, "cm": 0.01, "m": 1.0, "in": 0.0254}
_FORBIDDEN = re.compile(r'[\\/:*?"<>|\x00-\x1f]')
_RESERVED = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}
_STL_RECORD = np.dtype([("normal", "<f4", (3,)), ("v", "<f4", (3, 3)), ("attr", "<u2")])
_VERTEX_RE = re.compile(rb"vertex\s+(\S+)\s+(\S+)\s+(\S+)", re.IGNORECASE)
_meta_cache: Dict[str, Tuple[int, int, Dict[str, Any]]] = {}


class ModelError(ValueError):
    def __init__(self, code: str, message: str = "", status: int = 400) -> None:
        super().__init__(message or code)
        self.code, self.message, self.status = code, message or code, status

    def response(self) -> JSONResponse:
        return JSONResponse({"ok": False, "error": self.code, "message": self.message}, status_code=self.status)


# ------------------------------------------------------------------------------------------------ Ordner und Namen
def models_dir() -> Path:
    directory = _paths.get_data_root() / "models"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def clean_stem(name: Any, fallback: str = "Model") -> str:
    text = re.sub(r"\s+", " ", _FORBIDDEN.sub("_", str(name or ""))).strip(". ")[:60]
    if not text or text.split(".")[0].upper() in _RESERVED:
        return fallback
    return text


def valid_filename(filename: Any) -> bool:
    return (isinstance(filename, str) and filename.lower().endswith(EXTENSION) and filename == Path(filename).name and not filename.startswith(".")
            and "\x00" not in filename and len(filename) <= 80)


def path_of(filename: str) -> Path:
    if not valid_filename(filename):
        raise ModelError("invalid_name", "Ungueltiger Dateiname")
    path = models_dir() / filename
    if not path.is_file():
        raise ModelError("not_found", "Model not found", 404)
    return path


# ------------------------------------------------------------------------------------------------ Einlesen
def parse_stl(data: bytes) -> np.ndarray:
    """Dreiecke (n, 3, 3) aus einer STL - binaer oder ASCII (der Kopf einer binaeren Datei darf mit "solid" beginnen: die Laenge entscheidet)."""
    if len(data) >= 84:
        count = struct.unpack_from("<I", data, 80)[0]
        if count and 84 + 50 * count <= len(data) <= 84 + 50 * count + 4096:
            if count > MAX_TRIANGLES:
                raise ModelError("too_many_triangles", f"Mehr als {MAX_TRIANGLES} Dreiecke")
            return np.frombuffer(data, dtype=_STL_RECORD, count=count, offset=84)["v"].astype(np.float32)
    if b"vertex" not in data[:65536].lower():
        raise ModelError("invalid_file", "Not an STL file")
    found = _VERTEX_RE.findall(data)
    if len(found) < 3:
        raise ModelError("invalid_file", "The STL file contains no triangles")
    try:
        values = np.array(found, dtype=np.float64)
    except ValueError:
        raise ModelError("invalid_file", "Invalid numbers in the STL file") from None
    usable = (len(values) // 3) * 3
    triangles = values[:usable].reshape(-1, 3, 3).astype(np.float32)
    if len(triangles) > MAX_TRIANGLES:
        raise ModelError("too_many_triangles", f"Mehr als {MAX_TRIANGLES} Dreiecke")
    return triangles


def parse_obj(data: bytes) -> np.ndarray:
    """Dreiecke aus einer OBJ (nur Geometrie: v / f; Vielecke als Faecher; negative Indizes erlaubt), von Y oben nach Z oben gedreht."""
    vertices: List[Tuple[float, float, float]] = []
    faces: List[Tuple[int, int, int]] = []
    for raw_line in data.decode("utf-8", "replace").splitlines():
        line = raw_line.strip()
        if line.startswith("v "):
            parts = line.split()
            try:
                vertices.append((float(parts[1]), float(parts[2]), float(parts[3])))
            except (IndexError, ValueError):
                raise ModelError("invalid_file", "Invalid vertex in the OBJ file") from None
        elif line.startswith("f "):
            refs = []
            for token in line.split()[1:]:
                try:
                    index = int(token.split("/")[0])
                except ValueError:
                    raise ModelError("invalid_file", "Invalid face in the OBJ file") from None
                refs.append(index - 1 if index > 0 else len(vertices) + index)
            for k in range(1, len(refs) - 1):
                faces.append((refs[0], refs[k], refs[k + 1]))
            if len(faces) > MAX_TRIANGLES:
                raise ModelError("too_many_triangles", f"Mehr als {MAX_TRIANGLES} Dreiecke")
    if not vertices or not faces:
        raise ModelError("invalid_file", "The OBJ file contains no faces")
    points = np.asarray(vertices, dtype=np.float64)
    index = np.asarray(faces, dtype=np.int64)
    if index.min() < 0 or index.max() >= len(points):
        raise ModelError("invalid_file", "The OBJ file refers to missing vertices")
    triangles = points[index]
    triangles = np.stack([triangles[..., 0], -triangles[..., 2], triangles[..., 1]], axis=-1)       # Y oben -> Z oben
    return triangles.astype(np.float32)


def check_triangles(triangles: np.ndarray) -> np.ndarray:
    if triangles.ndim != 3 or triangles.shape[1:] != (3, 3) or not len(triangles):
        raise ModelError("invalid_file", "No triangles found")
    if not np.isfinite(triangles).all():
        raise ModelError("invalid_file", "The file contains invalid numbers")
    size = triangles.reshape(-1, 3).max(axis=0) - triangles.reshape(-1, 3).min(axis=0)
    if (size > 0).sum() < 2:
        raise ModelError("invalid_file", "The model has no extent")
    return triangles


def pack_colors(colors: np.ndarray) -> np.ndarray:
    """RGB (n, 3, uint8) -> 16-Bit-Attribut je Dreieck: Bit 15 = Farbe gueltig, Bits 10-14 R, 5-9 G, 0-4 B (je 5 Bit). Eigene Festlegung dieses Programms; STL-Dateien, die der Benutzer einliest,
    werden ohne Attribute abgelegt (siehe to_stl) - so deutet nie fremder Inhalt der Attribut-Bytes als Farbe."""
    c = np.asarray(colors, dtype=np.uint16) >> 3
    return (0x8000 | (c[:, 0] << 10) | (c[:, 1] << 5) | c[:, 2]).astype(np.uint16)


def to_stl(triangles: np.ndarray, colors: Any = None) -> bytes:
    """Binaere STL (Normalen 0: die Oberflaeche berechnet sie selbst). colors: optional (n, 3) uint8 - eine Farbe je Dreieck (z. B. aus einer MVR-Szene), siehe pack_colors."""
    records = np.zeros(len(triangles), dtype=_STL_RECORD)
    records["v"] = triangles
    if colors is not None and len(colors) == len(triangles):
        records["attr"] = pack_colors(colors)
    header = b"OpenCue 3D model".ljust(80, b" ")
    return header + struct.pack("<I", len(triangles)) + records.tobytes()


def read_any(filename: str, data: bytes) -> np.ndarray:
    if len(data) > MAX_BYTES:
        raise ModelError("too_large", "The file is too large", 413)
    lower = filename.lower()
    if lower.endswith(".obj"):
        return check_triangles(parse_obj(data))
    if lower.endswith(".stl"):
        return check_triangles(parse_stl(data))
    raise ModelError("invalid_name", "An STL or OBJ file is expected")


def import_bytes(filename: str, data: bytes) -> Dict[str, Any]:
    """Datei pruefen, als binaere STL ablegen. Rueckgabe wie beim Dateimanager: {ok, id, name, status (created|copy|identical), original}."""
    return store_stl(filename, to_stl(read_any(filename, data)))


def store_triangles(filename: str, triangles: np.ndarray, colors: Any = None) -> Dict[str, Any]:
    """Fertige Dreiecke (Meter, Z oben, optional Farben je Dreieck) in die Modell-Bibliothek legen (MVR-Import); gleiche Regeln wie import_bytes."""
    return store_stl(filename, to_stl(check_triangles(triangles), colors))


def store_stl(filename: str, stl: bytes) -> Dict[str, Any]:
    original = clean_stem(Path(filename).stem)
    directory = models_dir()
    n = 1
    while True:
        name = original if n == 1 else f"{original} ({n})"
        path = directory / (name + EXTENSION)
        if not path.exists():
            identical = False
            break
        if path.read_bytes() == stl:
            identical = True
            break
        n += 1
    if not identical:
        partial = path.with_name("." + path.name + ".part")
        partial.write_bytes(stl)
        os.replace(partial, path)
    status = "identical" if identical else ("created" if name == original else "copy")
    return {"ok": True, "id": path.name, "name": name, "status": status, "original": original if status == "copy" else None, "replaced": False}


# ------------------------------------------------------------------------------------------------ Liste
def meta(path: Path) -> Dict[str, Any]:
    """Dreiecke und Ausdehnung (Einheiten der Datei) - zwischengespeichert, bis sich die Datei aendert."""
    stat = path.stat()
    cached = _meta_cache.get(str(path))
    if cached and cached[0] == stat.st_mtime_ns and cached[1] == stat.st_size:
        return cached[2]
    try:
        triangles = parse_stl(path.read_bytes())
        points = triangles.reshape(-1, 3)
        low, high = points.min(axis=0), points.max(axis=0)
        info = {"triangles": int(len(triangles)), "size": [round(float(v), 4) for v in (high - low)], "ok": True}
    except ModelError as exc:
        info = {"triangles": 0, "size": [0, 0, 0], "ok": False, "message": exc.message}
    _meta_cache[str(path)] = (stat.st_mtime_ns, stat.st_size, info)
    return info


def list_models() -> List[Dict[str, Any]]:
    used = used_models()
    try:
        saved = used_by_saved_stages()
    except Exception:          # noqa: BLE001
        saved = set()
    out = []
    for path in sorted(models_dir().glob("*" + EXTENSION), key=lambda p: p.name.lower()):
        if path.name.startswith(".") or not path.is_file():
            continue
        stat = path.stat()
        out.append({"id": path.name, "name": path.stem, "bytes": stat.st_size, "modified": int(stat.st_mtime), **meta(path), "in_use": path.name in used, "in_saved_stage": path.name in saved})
    return out


def used_models() -> set:
    """Modelle, die auf der geladenen Buehne stehen."""
    try:
        return {o.get("model") for o in sim_stages.store.objects if o.get("type") == "model" and o.get("model")}
    except Exception:          # noqa: BLE001 - die Buehne ist noch nicht geladen
        return set()


def used_by_saved_stages() -> set:
    """Modelle, die auf irgendeiner GESPEICHERTEN Buehne (Buehnen-Bibliothek) stehen."""
    names: set = set()
    try:
        for entry in sim_stages.list_files():
            for obj in sim_stages.read_file(entry["filename"])["objects"]:
                if obj.get("type") == "model" and obj.get("model"):
                    names.add(obj["model"])
    except Exception:          # noqa: BLE001 - eine unlesbare Buehnen-Datei darf nichts loeschen lassen: im Zweifel gelten alle als benutzt (siehe unused())
        raise
    return names


def unused() -> List[Dict[str, Any]]:
    """Modelle, die weder auf der geladenen noch auf einer gespeicherten Buehne stehen (loeschbar). Ist eine Buehnen-Datei nicht lesbar: nichts gilt als unbenutzt."""
    try:
        keep = used_models() | used_by_saved_stages()
    except Exception:          # noqa: BLE001
        return []
    out = []
    for path in sorted(models_dir().glob("*" + EXTENSION)):
        if path.name.startswith(".") or not path.is_file() or path.name in keep:
            continue
        out.append({"id": path.name, "bytes": path.stat().st_size})
    return out


# ------------------------------------------------------------------------------------------------ Verwalten
def rename(filename: str, new_name: Any) -> Dict[str, Any]:
    path = path_of(filename)
    if filename in used_models():
        raise ModelError("in_use", "Das Modell steht auf der geladenen Buehne", 409)
    stem = clean_stem(new_name, "")
    if not stem:
        raise ModelError("invalid_name", "Ungueltiger Name")
    target = models_dir() / (stem + EXTENSION)
    if target.exists() and target.resolve() != path.resolve():
        raise ModelError("exists", "That name already exists", 409)
    os.replace(path, target)
    return {"ok": True, "id": target.name, "name": stem}


def duplicate(filename: str) -> Dict[str, Any]:
    path = path_of(filename)
    data = path.read_bytes()
    n = 2
    while (models_dir() / f"{path.stem} ({n}){EXTENSION}").exists():
        n += 1
    target = models_dir() / f"{path.stem} ({n}){EXTENSION}"
    target.write_bytes(data)
    return {"ok": True, "id": target.name, "name": target.stem}


def delete(filename: str) -> Dict[str, Any]:
    path = path_of(filename)
    if filename in used_models():
        raise ModelError("in_use", "Das Modell steht auf der geladenen Buehne", 409)
    path.unlink()
    _meta_cache.pop(str(path), None)
    return {"ok": True}


async def _announce() -> None:
    from app import server as S
    await S.event_bus.broadcast({"type": "sim_models_changed", "payload": {}})


@router.get("/api/sim-models")
async def api_list() -> JSONResponse:
    return JSONResponse({"models": list_models(), "max_triangles": MAX_TRIANGLES, "units": list(UNITS)})


@router.get("/api/sim-models/file/{filename}")
async def api_file(filename: str) -> Response:
    try:
        path = path_of(filename)
    except ModelError as exc:
        return exc.response()
    return Response(content=path.read_bytes(), media_type="model/stl", headers={"Cache-Control": "no-cache"})


@router.post("/api/sim-models/delete-unused")
async def api_delete_unused(request: Request) -> JSONResponse:
    """Alle Modelle loeschen, die auf keiner Buehne (geladen oder gespeichert) stehen. {"dry_run": true} zaehlt nur."""
    try:
        body = await request.json()
    except ValueError:
        body = {}
    items = unused()
    if not (isinstance(body, dict) and body.get("dry_run")):
        for item in items:
            try:
                (models_dir() / item["id"]).unlink()
                _meta_cache.pop(str(models_dir() / item["id"]), None)
            except OSError:
                pass
        if items:
            await _announce()
    return JSONResponse({"ok": True, "count": len(items), "bytes": sum(i["bytes"] for i in items), "ids": [i["id"] for i in items][:200]})


@router.post("/api/sim-models/{action}")
async def api_manage(action: str, request: Request) -> JSONResponse:
    try:
        body = await request.json()
    except ValueError:
        body = {}
    body = body if isinstance(body, dict) else {}
    try:
        if action == "rename":
            result = rename(str(body.get("filename", "")), body.get("new_name"))
        elif action == "duplicate":
            result = duplicate(str(body.get("filename", "")))
        elif action == "delete":
            result = delete(str(body.get("filename", "")))
        else:
            raise ModelError("not_found", "Unbekannte Aktion", 404)
    except ModelError as exc:
        return exc.response()
    await _announce()
    return JSONResponse(result)
