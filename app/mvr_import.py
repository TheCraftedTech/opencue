# Copyright (C) 2026 Samuel Zenker
# SPDX-License-Identifier: GPL-3.0-or-later
"""
mvr_import.py
MVR-Import (My Virtual Rig, DIN SPEC 15801): eine Vectorworks- / Capture- / Depence-... Szene als .mvr-Datei einlesen. Eine MVR-Datei ist ein ZIP mit
`GeneralSceneDescription.xml` (Ebenen -> Objekte, Scheinwerfer mit Position, Drehung, DMX-Adresse, GDTF-Typ und -Modus), den GDTF-Dateien der Scheinwerfer und den
3D-Dateien (3ds / glb) der Buehnenteile. Die Datei selbst bleibt NICHT erhalten: sie wird in OpenCues eigene Daten umgewandelt.

  * Scheinwerfer -> werden gepatcht (Typ, Modus, Universum, Adresse, Nummer, Name) und in der 3D-Simulation an ihre Stelle gesetzt (Position + Drehung, `fixture_layout`).
    Die GDTF-Dateien kommen in die Scheinwerfer-Bibliothek (nie ueberschreiben: gleicher Inhalt = vorhandene Datei, sonst Kopie "(2)").
  * Buehnenteile (SceneObject, Truss, Support, VideoScreen, Projector, auch in Gruppen und Symbolen) -> eigene 3D-Modelle (binaere STL in `models/`, Meter, Z oben) und
    Buehnen-Objekte (Typ "model": Position, Drehung, Groesse) - so lassen sie sich in der 3D-Simulation wie alles andere verschieben und drehen. Eine Datei, die mehrfach
    vorkommt (Symbol), ergibt EINE STL und mehrere Objekte. Wird die Grenze der Buehne (200 Objekte) ueberschritten, werden die Teile je Ebene (sonst alle) zu einem
    Koerper zusammengefasst.
  * Die Buehne wird auf Wunsch ERSETZT (Standard; die bisherige Buehnen-Datei bleibt unangetastet), ergaenzt oder gar nicht angefasst; Scheinwerfer lassen sich abwaehlen.

MVR-Regeln (Spezifikation 1.6): rechtshaendig, Z oben, 1 Einheit = 1 mm; `Matrix` = vier Vektoren {u}{v}{w}{o}: u, v, w sind die Bilder der X-, Y-, Z-Achse, o die Verschiebung
(Zeilenvektor-Schreibweise p' = p * M). Ein Kind liegt im Koordinatensystem seines Elterns: Welt = Kind * Eltern (Geometrie -> Symbol -> Objekt -> Gruppe -> Ebene).
3ds-Dateien sind in Millimetern, glb / glTF in Metern; Assimp liefert beide mit Y oben, sie werden nach Z oben gedreht. Adressen: ganze Zahl = absolute DMX-Adresse
((Universum - 1) * 512 + Kanal) oder "Universum.Kanal".

Farben: jedes Dreieck behaelt die Farbe seines Materials (in den Attribut-Bytes der STL, siehe app/sim_models.py pack_colors). Gespiegelte Teile (negative Determinante der Matrix)
werden als gespiegeltes Modell "(mirrored)" abgelegt und mit der drehungsrichtigen Matrix platziert.
Schnittstellen: POST /api/mvr/preview (roher Body = die .mvr, ?filename=) liest nur und liefert eine Zusammenfassung + Sitzung; POST /api/mvr/apply {session, stage, fixtures, up_axis}
startet den Import im Hintergrund ({job}); GET /api/mvr/status?job= liefert Phase, Fortschritt und am Ende das Ergebnis. Eine Sitzung (die Datei im Speicher) lebt 20 Minuten.
Geschwindigkeit: GDTF-Dateien werden nur einmal eingebaut und gelesen (pygdtf braucht bei grossen LED-Leisten bis zu 13 s; fixture_manager merkt sich jede Datei einzeln).
"""
from __future__ import annotations

import asyncio
import hashlib
import io
import logging
import math
import os
import re
import tempfile
import threading
import time
import urllib.parse
import uuid
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from xml.etree import ElementTree

import numpy as np
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app import fixture_library, fixture_manager, sim_models, sim_stages
from app import paths as _paths
from app.state_manager import MAX_UNIVERSE, MIN_UNIVERSE, Fixture, state

try:
    import assimp_py as _assimp
except Exception:                       # pragma: no cover - haengt von der Installation ab
    _assimp = None

router = APIRouter()
logger = logging.getLogger("opencue.mvr")

MM = 0.001
MAX_ARCHIVE_BYTES = 400 * 1024 * 1024
MAX_UNPACKED_BYTES = 1500 * 1024 * 1024
MAX_MEMBER_BYTES = 200 * 1024 * 1024
MAX_XML_BYTES = 80 * 1024 * 1024
MAX_LEAVES = 20000
MAX_FIXTURES_IMPORT = 3000
MAX_DEPTH = 12
MAX_WARNINGS = 30
SESSION_SECONDS = 20 * 60
GEOMETRY_NODES = ("SceneObject", "Truss", "Support", "VideoScreen", "Projector", "FocusPoint")
MESH_EXTENSIONS = (".3ds", ".glb", ".gltf", ".obj", ".stl")
_MATRIX_NUMBER = re.compile(r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")
_FORBIDDEN = re.compile(r'[\\/:*?"<>|\x00-\x1f]')


class MvrError(Exception):
    def __init__(self, code: str, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.code, self.message, self.status = code, message, status

    def response(self) -> JSONResponse:
        return JSONResponse({"ok": False, "error": self.code, "message": self.message}, status_code=self.status)


# ------------------------------------------------------------------------------------------------ Matrizen
def parse_matrix(text: Optional[str]) -> np.ndarray:
    """"{ux,uy,uz}{vx,vy,vz}{wx,wy,wz}{ox,oy,oz}" -> 4x4 (Zeilenvektor-Schreibweise, Verschiebung in METERN). Fehlt sie oder ist sie unlesbar: Einheitsmatrix."""
    m = np.eye(4)
    numbers = [float(x) for x in _MATRIX_NUMBER.findall(text or "")]
    if len(numbers) == 12 and all(math.isfinite(v) for v in numbers):
        m[0, :3], m[1, :3], m[2, :3] = numbers[0:3], numbers[3:6], numbers[6:9]
        m[3, :3] = np.array(numbers[9:12]) * MM
    return m


def euler_xyz(rotation: np.ndarray) -> List[float]:
    """Drehmatrix (Spalten = Bilder der Achsen) -> Euler-Winkel XYZ in Grad, genau wie three.js `Euler.setFromRotationMatrix(m, "XYZ")` (so dreht die 3D-Simulation)."""
    m11, m12, m13 = rotation[0]
    m22, m23 = rotation[1][1], rotation[1][2]
    m32, m33 = rotation[2][1], rotation[2][2]
    y = math.asin(max(-1.0, min(1.0, m13)))
    if abs(m13) < 0.9999999:
        x, z = math.atan2(-m23, m33), math.atan2(-m12, m11)
    else:
        x, z = math.atan2(m32, m22), 0.0
    return [round(math.degrees(v), 2) + 0.0 for v in (x, y, z)]


def decompose(m: np.ndarray) -> Optional[Tuple[np.ndarray, np.ndarray, np.ndarray, bool]]:
    """-> (Verschiebung, Massstaebe k je Achse, Drehmatrix R mit den Achsbildern als Spalten, gespiegelt?) oder None bei entarteter Matrix."""
    rows = m[:3, :3]
    k = np.linalg.norm(rows, axis=1)
    if not np.isfinite(k).all() or k.min() < 1e-9:
        return None
    e = rows / k[:, None]
    return m[3, :3].copy(), k, e.T.copy(), bool(np.linalg.det(e) < 0)


# ------------------------------------------------------------------------------------------------ Archiv und XML
def open_archive(data: bytes) -> Tuple[zipfile.ZipFile, Dict[str, zipfile.ZipInfo]]:
    if len(data) > MAX_ARCHIVE_BYTES:
        raise MvrError("too_large", "The file is too large", 413)
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        raise MvrError("invalid_file", "This is not an MVR file (no valid ZIP archive).") from None
    infos = [i for i in archive.infolist() if not i.is_dir()]
    if sum(i.file_size for i in infos) > MAX_UNPACKED_BYTES:
        raise MvrError("too_large", "The file is too large when unpacked", 413)
    names: Dict[str, zipfile.ZipInfo] = {}
    for info in infos:
        parts = [p for p in info.filename.replace("\\", "/").split("/") if p]
        if not parts or any(p in (".", "..") or ":" in p for p in parts):
            continue
        names.setdefault(parts[-1].lower(), info)                                # alles liegt laut Spezifikation im Hauptordner; tiefer Verschachteltes wird trotzdem gefunden
    return archive, names


def read_xml(archive: zipfile.ZipFile, names: Dict[str, zipfile.ZipInfo]) -> ElementTree.Element:
    info = names.get("generalscenedescription.xml")
    if info is None:
        raise MvrError("invalid_file", "This is not an MVR file (GeneralSceneDescription.xml is missing).")
    if info.file_size > MAX_XML_BYTES:
        raise MvrError("too_large", "The scene description is unusually large", 413)
    xml = archive.read(info)
    head = xml[:4096].lower()
    if b"<!entity" in xml[:200000].lower() or b"<!doctype" in head:
        raise MvrError("invalid_file", "The scene description contains forbidden declarations.")
    try:
        return ElementTree.fromstring(xml)
    except ElementTree.ParseError:
        raise MvrError("invalid_file", "GeneralSceneDescription.xml is not valid XML.") from None


def _matrix_of(node: ElementTree.Element) -> np.ndarray:
    return parse_matrix(node.findtext("Matrix"))


def _clean_label(text: Any, fallback: str, limit: int = 60) -> str:
    cleaned = re.sub(r"\s+", " ", _FORBIDDEN.sub("", str(text or ""))).strip()
    return cleaned[:limit] or fallback


# ------------------------------------------------------------------------------------------------ Szene lesen
class Scan:
    """Inhalt einer MVR-Datei, ohne die 3D-Dateien zu lesen: Teile (leaves), Scheinwerfer und alles, was auffaellt."""

    def __init__(self) -> None:
        self.leaves: List[Dict[str, Any]] = []
        self.fixtures: List[Dict[str, Any]] = []
        self.warnings: List[str] = []
        self.layers: List[str] = []
        self.skipped: Dict[str, int] = {}
        self.provider = ""
        self.version = ""
        self.truncated = False

    def warn(self, text: str) -> None:
        if text not in self.warnings and len(self.warnings) < MAX_WARNINGS:
            self.warnings.append(text)


def parse_address(node: ElementTree.Element) -> Optional[Tuple[int, int]]:
    """Erste Adresse des Scheinwerfers (kleinster Break) -> (Universum, Kanal) oder None."""
    best: Optional[Tuple[int, str]] = None
    for address in node.findall("Addresses/Address"):
        text = (address.text or "").strip()
        if not text:
            continue
        try:
            brk = int(address.get("break", "0") or 0)
        except ValueError:
            brk = 0
        if best is None or brk < best[0]:
            best = (brk, text)
    if best is None:
        return None
    text = best[1]
    try:
        if "." in text:
            universe, channel = text.split(".", 1)
            return int(universe), int(channel)
        absolute = int(text)
    except ValueError:
        return None
    if absolute < 1:
        return None
    return (absolute - 1) // 512 + 1, (absolute - 1) % 512 + 1


def _file_of(name: str, names: Dict[str, zipfile.ZipInfo]) -> Optional[str]:
    key = name.strip().replace("\\", "/").split("/")[-1].lower()
    if key and "." not in key:
        key += ".3ds"                                                             # ohne Endung gilt laut Spezifikation 3ds
    return key if key in names else None


def scan_scene(root: ElementTree.Element, names: Dict[str, zipfile.ZipInfo]) -> Scan:
    scan = Scan()
    scan.provider = " ".join(x for x in (root.get("provider"), root.get("providerVersion")) if x)
    scan.version = f"{root.get('verMajor', '?')}.{root.get('verMinor', '?')}"
    scene = root.find("Scene")
    if scene is None:
        raise MvrError("invalid_file", "The scene description has no <Scene>.")
    symdefs = {sd.get("uuid", ""): sd for sd in scene.findall("AUXData/Symdef")}

    def leaves_of(container: ElementTree.Element, base: np.ndarray, owner: Dict[str, Any], depth: int) -> None:
        for item in container:
            if len(scan.leaves) >= MAX_LEAVES:
                scan.truncated = True
                return
            matrix = _matrix_of(item) @ base
            if item.tag == "Geometry3D":
                file = _file_of(item.get("fileName", ""), names)
                if file is None:
                    scan.warn(f"3D file missing in the archive: {item.get('fileName', '?')}")
                elif not file.endswith(MESH_EXTENSIONS):
                    scan.skipped[file.rsplit(".", 1)[-1]] = scan.skipped.get(file.rsplit(".", 1)[-1], 0) + 1
                    scan.warn(f"3D format not supported: {file}")
                else:
                    scan.leaves.append({**owner, "file": file, "m": matrix})
            elif item.tag == "Symbol":
                definition = symdefs.get(item.get("symdef", ""))
                if definition is None:
                    scan.warn("A symbol refers to a missing definition.")
                elif depth >= MAX_DEPTH:
                    scan.warn("Symbols are nested too deeply.")
                else:
                    child_list = definition.find("ChildList")
                    if child_list is not None:
                        leaves_of(child_list, matrix, owner, depth + 1)

    def walk(children: ElementTree.Element, base: np.ndarray, layer: str, depth: int) -> None:
        for node in children:
            if node.tag not in GEOMETRY_NODES and node.tag not in ("GroupObject", "Fixture"):
                continue
            if depth > MAX_DEPTH:
                scan.warn("Groups are nested too deeply.")
                return
            world = _matrix_of(node) @ base
            name = _clean_label(node.get("name"), node.tag)
            if node.tag == "Fixture":
                if len(scan.fixtures) < MAX_FIXTURES_IMPORT:
                    scan.fixtures.append(_fixture_of(node, world, name, layer))
                else:
                    scan.truncated = True
            elif node.tag == "FocusPoint":
                scan.skipped["FocusPoint"] = scan.skipped.get("FocusPoint", 0) + 1
            elif node.tag != "GroupObject":
                geometries = node.find("Geometries")
                if geometries is not None:
                    leaves_of(geometries, world, {"name": name, "layer": layer, "uuid": node.get("uuid", ""), "kind": node.tag}, 0)
            child_list = node.find("ChildList")
            if child_list is not None:
                walk(child_list, world, layer, depth + 1)

    for layer in scene.findall("Layers/Layer"):
        layer_name = _clean_label(layer.get("name"), "Layer")
        scan.layers.append(layer_name)
        base = np.eye(4)
        layer_matrix = layer.find("Matrix")
        if layer_matrix is not None:
            base = parse_matrix(layer_matrix.text)
            base[:3, :3] = np.eye(3)                                              # laut Spezifikation nur eine Hoehe (Drehung und Massstab bleiben Einheit)
        child_list = layer.find("ChildList")
        if child_list is not None:
            walk(child_list, base, layer_name, 0)
    return scan


def _fixture_of(node: ElementTree.Element, world: np.ndarray, name: str, layer: str) -> Dict[str, Any]:
    address = parse_address(node)
    fid = None
    for tag in ("FixtureIDNumeric", "FixtureID"):
        text = (node.findtext(tag) or "").strip()
        if text.isdigit() and int(text) > 0:
            fid = int(text)
            break
    parts = decompose(world)
    position = [round(float(v), 4) for v in world[3, :3]]
    rotation = euler_xyz(parts[2]) if parts else [0.0, 0.0, 0.0]
    return {"name": name, "uuid": node.get("uuid", ""), "gdtf": (node.findtext("GDTFSpec") or "").strip(), "mode": (node.findtext("GDTFMode") or "").strip(),
            "universe": address[0] if address else None, "channel": address[1] if address else None, "fid": fid, "position": position, "rotation": rotation, "layer": layer}


# ------------------------------------------------------------------------------------------------ 3D-Dateien
def _gdtf_file(name: str, names: Dict[str, zipfile.ZipInfo]) -> Optional[str]:
    """Die GDTF-Datei zu einem GDTFSpec: genau der Name, mit ".gdtf" ergaenzt oder (Vectorworks schreibt manchmal nur "Cluster S2") der Teil nach dem "@" - nur wenn es eindeutig ist."""
    key = name.strip().replace("\\", "/").split("/")[-1].lower()
    if not key:
        return None
    for candidate in (key, key + ".gdtf"):
        if candidate in names and candidate.endswith(".gdtf"):
            return candidate
    stem = key[:-5] if key.endswith(".gdtf") else key
    hits = [n for n in names if n.endswith(".gdtf") and (n[:-5] == stem or n[:-5].split("@")[-1] == stem)]
    return hits[0] if len(hits) == 1 else None


def load_mesh(data: bytes, extension: str, up_axis: str) -> Dict[str, Any]:
    """Eine 3D-Datei -> {"tris": (n,3,3) float32 in METERN, Z oben; "colors": (n,3) uint8 (Farbe je Dreieck aus dem Material); "lo", "hi"; "color": Mittelfarbe}. Wirft MvrError."""
    if _assimp is None:
        raise MvrError("no_assimp", "3D files cannot be read here (assimp-py is not installed).", 501)
    flags = _assimp.Process_Triangulate | _assimp.Process_JoinIdenticalVertices | _assimp.Process_PreTransformVertices
    fd, name = tempfile.mkstemp(suffix=extension, prefix="opencue-mvr-")
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
        try:
            scene = _assimp.import_file(name, flags)
        except Exception as exc:                                                  # noqa: BLE001 - Assimp wirft beliebige Fehler
            raise MvrError("bad_mesh", f"3D file unreadable ({type(exc).__name__})") from exc
    finally:
        try:
            os.unlink(name)
        except OSError:
            pass
    parts: List[np.ndarray] = []
    colors: List[np.ndarray] = []
    for mesh in scene.meshes:
        if not mesh.num_vertices or not mesh.num_faces:
            continue
        vertices = np.frombuffer(bytes(mesh.vertices), dtype=np.float32).reshape(-1, 3)
        index = np.frombuffer(bytes(mesh.indices), dtype=np.uint32).reshape(-1, 3)
        if len(vertices) != mesh.num_vertices or not len(index) or int(index.max()) >= len(vertices):
            continue
        parts.append(vertices[index])
        rgb = [0.62, 0.62, 0.63]
        try:
            diffuse = scene.materials[mesh.material_index].get("COLOR_DIFFUSE")
            if diffuse:
                rgb = [max(0.0, min(1.0, float(c))) for c in diffuse[:3]]
                if min(rgb) > 0.93:                                               # reines Weiss = "keine Farbe angegeben" (Vectorworks): ein neutrales Grau, sonst wirkt jede Flaeche im Licht ausgebrannt
                    rgb = [0.62, 0.62, 0.63]
        except Exception:                                                         # noqa: BLE001
            pass
        colors.append(np.tile(np.array([int(round(c * 255)) for c in rgb], dtype=np.uint8), (len(index), 1)))
    if not parts:
        raise MvrError("bad_mesh", "The 3D file contains no faces")
    tris = np.concatenate(parts).astype(np.float64)
    ext = extension.lower()
    y_up = up_axis == "y" or (up_axis == "auto" and ext in (".3ds", ".glb", ".gltf", ".obj"))        # Assimp liefert diese Formate mit Y oben (auch 3ds, das in der Datei Z oben ist)
    if y_up:
        tris = np.stack([tris[..., 0], -tris[..., 2], tris[..., 1]], axis=-1)    # Y oben -> Z oben
    tris = (tris * (MM if ext == ".3ds" else 1.0)).astype(np.float32)             # 3ds ist laut MVR in Millimetern, glTF in Metern
    if not np.isfinite(tris).all():
        raise MvrError("bad_mesh", "The 3D file contains invalid numbers")
    all_colors = np.concatenate(colors)
    mean = all_colors.mean(axis=0) / 255.0
    points = tris.reshape(-1, 3)
    return {"tris": tris, "colors": all_colors, "lo": points.min(axis=0).astype(np.float64), "hi": points.max(axis=0).astype(np.float64),
            "color": "#%02x%02x%02x" % tuple(int(round(float(v) * 255)) for v in mean)}


def mirrored(mesh: Dict[str, Any]) -> Dict[str, Any]:
    """Das an der lokalen X-Achse gespiegelte Netz (Umlaufsinn der Dreiecke wird mitgedreht, damit Vorder- und Rueckseite stimmen)."""
    tris = mesh["tris"].copy()
    tris[..., 0] *= -1
    tris = tris[:, [0, 2, 1], :]
    lo, hi = mesh["lo"], mesh["hi"]
    return {**mesh, "tris": tris, "lo": np.array([-hi[0], lo[1], lo[2]]), "hi": np.array([-lo[0], hi[1], hi[2]])}


FLIP_X = np.diag([-1.0, 1.0, 1.0, 1.0])


# ------------------------------------------------------------------------------------------------ Vorschau
def _quick_gdtf_name(data: bytes) -> str:
    """Hersteller + Name aus der description.xml, ohne pygdtf (das bei grossen Dateien bis zu 13 s braucht): nur das erste <FixtureType> wird gelesen."""
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            with archive.open("description.xml") as handle:
                if b"<!ENTITY" in handle.peek(65536)[:65536] or b"<!DOCTYPE" in handle.peek(65536)[:65536]:
                    return ""
                for _event, node in ElementTree.iterparse(handle, events=("start",)):
                    if node.tag == "FixtureType":
                        return f"{node.get('Manufacturer', '')} {node.get('Name', '')}".strip()
    except Exception:                                                             # noqa: BLE001
        pass
    return ""


def summarize(data: bytes, filename: str) -> Dict[str, Any]:
    archive, names = open_archive(data)
    with archive:
        root = read_xml(archive, names)
        scan = scan_scene(root, names)
        types: Dict[str, Dict[str, Any]] = {}
        for fx in scan.fixtures:
            file = _gdtf_file(fx["gdtf"], names) if fx["gdtf"] else None
            entry = types.setdefault(file or fx["gdtf"] or "?", {"file": file or fx["gdtf"], "count": 0, "modes": set(), "name": "", "present": file is not None})
            entry["count"] += 1
            if fx["mode"]:
                entry["modes"].add(fx["mode"])
        for entry in types.values():
            if entry["present"]:
                entry["name"] = _quick_gdtf_name(archive.read(names[entry["file"]])) or entry["file"]
            entry["modes"] = sorted(entry["modes"])[:6]
        files = sorted({leaf["file"] for leaf in scan.leaves})
        stats: Dict[str, Dict[str, Any]] = {name: {"name": name, "parts": 0, "fixtures": 0} for name in scan.layers}
        for leaf in scan.leaves:
            stats.setdefault(leaf["layer"], {"name": leaf["layer"], "parts": 0, "fixtures": 0})["parts"] += 1
        for fx in scan.fixtures:
            stats.setdefault(fx["layer"], {"name": fx["layer"], "parts": 0, "fixtures": 0})["fixtures"] += 1
        layer_stats = [s for s in stats.values() if s["parts"] or s["fixtures"]]
        unaddressed = sum(1 for fx in scan.fixtures if fx["universe"] is None)
        out_of_range = sum(1 for fx in scan.fixtures if fx["universe"] is not None and not MIN_UNIVERSE <= fx["universe"] <= MAX_UNIVERSE)
        universes = sorted({fx["universe"] for fx in scan.fixtures if fx["universe"] is not None and MIN_UNIVERSE <= fx["universe"] <= MAX_UNIVERSE})
        missing = [t["file"] or "(none)" for t in types.values() if not t["present"]]
        warnings = list(scan.warnings)
        if missing:
            warnings.append("GDTF file missing in the archive: " + ", ".join(missing[:4]))
        if out_of_range:
            warnings.append(f"{out_of_range} fixtures have a universe above {MAX_UNIVERSE} and get a new address")
        if scan.truncated:
            warnings.append("The scene is very large - only the first part is read")
        return {"name": Path(filename).stem or "MVR", "version": scan.version, "provider": scan.provider, "layers": scan.layers[:30], "layer_count": len(scan.layers),
                "parts": len(scan.leaves), "files": [{"name": f, "bytes": names[f].file_size} for f in files[:40]], "file_count": len(files),
                "fixtures": len(scan.fixtures), "unaddressed": unaddressed, "types": sorted(types.values(), key=lambda t: -t["count"])[:30], "type_count": len(types),
                "universes": universes[:200], "universe_count": len(universes), "layer_stats": layer_stats[:60], "focus_points": scan.skipped.get("FocusPoint", 0), "warnings": warnings[:MAX_WARNINGS],
                "can_read_3d": _assimp is not None, "stage_objects": len(sim_stages.store.objects) if sim_stages.store.ready else 0, "fixtures_now": len(state.fixtures),
                "max_objects": sim_stages.MAX_OBJECTS}


# ------------------------------------------------------------------------------------------------ Uebernehmen (Dateien, in einem Thread)
DEFAULT_OPTIONS: Dict[str, Any] = {
    "layers": None,                  # None = alle; sonst Liste von Ebenen-Namen
    "addressing": "file",            # "file": Adressen aus der Datei (mit Versatz) | "auto": neu vergeben ab start_universe
    "universe_offset": 0,            # wird auf jedes Universum der Datei addiert ("alle vier Universen hoeher")
    "start_universe": 1,
    "place_fixtures": True,          # Scheinwerfer auch in der 3D-Buehne an ihre Stelle setzen
    "colors": "keep",                # "keep": Farben der Materialien | "neutral": ein einheitliches Grau
    "up_axis": "auto",
}


def clean_options(raw: Any) -> Dict[str, Any]:
    """Einstellungen aus der Anfrage pruefen: Unbekanntes faellt weg, Zahlen kommen in ihren Bereich."""
    raw = raw if isinstance(raw, dict) else {}
    opts = dict(DEFAULT_OPTIONS)
    layers = raw.get("layers")
    if isinstance(layers, list):
        opts["layers"] = [str(x)[:80] for x in layers[:200]]
    if raw.get("addressing") in ("file", "auto"):
        opts["addressing"] = raw["addressing"]
    for key, low, high in (("universe_offset", -MAX_UNIVERSE, MAX_UNIVERSE), ("start_universe", MIN_UNIVERSE, MAX_UNIVERSE)):
        try:
            opts[key] = max(low, min(high, int(raw.get(key, opts[key]))))
        except (TypeError, ValueError):
            pass
    opts["place_fixtures"] = raw.get("place_fixtures") is not False
    if raw.get("colors") in ("keep", "neutral"):
        opts["colors"] = raw["colors"]
    if raw.get("up_axis") in ("auto", "y", "z"):
        opts["up_axis"] = raw["up_axis"]
    return opts


def _stl_name(prefix: str, label: str, suffix: str = "") -> str:
    """"<MVR-Name> - <Teil>[ (mirrored)].stl", hoechstens 60 Zeichen im Namen (die Endung (mirrored) geht nie verloren)."""
    clean = lambda text: re.sub(r"\s+", " ", _FORBIDDEN.sub("_", text)).strip(". ")
    return (clean(f"{prefix[:20]} - {label}")[:60 - len(suffix)] + suffix) + ".stl"


def _label_of(leaf: Dict[str, Any]) -> str:
    """Name des Modells: der Objektname aus der Datei (die Dateinamen in MVR sind meist nur eine Kennung)."""
    stem = Path(leaf["file"]).stem
    return stem if len(stem) <= 24 and leaf["name"] in ("", "SceneObject") else (leaf["name"] or stem)


def _world_tris(mesh: Dict[str, Any], matrix: np.ndarray) -> np.ndarray:
    return (mesh["tris"].astype(np.float64) @ matrix[:3, :3] + matrix[3, :3]).astype(np.float32)


def build(data: bytes, filename: str, stage_capacity: int, up_axis: str, want_stage: bool, want_fixtures: bool, progress: Optional[Any] = None, opts: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Alles, was nur Dateien betrifft: GDTF-Typen einbauen, 3D-Dateien lesen und als STL (mit Farben) ablegen, Buehnen-Objekte und Scheinwerfer-Eintraege berechnen.
    progress(phase, done, total) meldet den Fortschritt ("types" | "models")."""
    def tick(phase: str, done: int, total: int) -> None:
        if progress is not None:
            progress(phase, done, total)

    opts = {**DEFAULT_OPTIONS, **(opts or {})}
    archive, names = open_archive(data)
    report: Dict[str, Any] = {"warnings": [], "models": 0, "triangles": 0, "merged": "none", "types_installed": 0, "recentered": [0.0, 0.0], "mirrored": 0, "model_ids": []}
    warnings: List[str] = report["warnings"]
    with archive:
        scan = scan_scene(read_xml(archive, names), names)
        warnings.extend(scan.warnings)
        if opts["layers"] is not None:                                            # nur die gewaehlten Ebenen
            chosen = set(opts["layers"])
            scan.leaves = [leaf for leaf in scan.leaves if leaf["layer"] in chosen]
            scan.fixtures = [fx for fx in scan.fixtures if fx["layer"] in chosen]
        prefix = _clean_label(Path(filename).stem, "MVR", 40)

        # ---- Scheinwerfer-Typen: jede Datei wird nur einmal eingebaut und nur einmal gelesen (pygdtf braucht bei grossen Dateien bis zu 13 s)
        type_of: Dict[str, Optional[Dict[str, Any]]] = {}
        if want_fixtures:
            keys = sorted({fx["gdtf"] for fx in scan.fixtures})
            files = {key: (_gdtf_file(key, names) if key else None) for key in keys}
            todo = sorted({f for f in files.values() if f})
            by_file: Dict[str, Optional[Dict[str, Any]]] = {}
            for number, file in enumerate(todo):
                tick("types", number, len(todo))
                try:
                    installed = fixture_library.install_bytes(archive.read(names[file]), stem_hint=file, on_conflict="copy", deep_check=False)
                    fixture_manager._parse_gdtf_cached(_paths.FIXTURES_DIR / f"{installed['id']}.gdtf")          # noqa: SLF001 - hier wird gelesen und gemerkt
                    fixture_manager.flush_parse_cache()
                    ft = fixture_manager.get_fixture_type_by_id(installed["id"])
                    if ft is None or ft.get("error"):
                        raise ValueError((ft or {}).get("error") or "not readable")
                    by_file[file] = ft
                    report["types_installed"] += 0 if installed.get("identical") else 1
                except Exception as exc:                                                              # noqa: BLE001
                    warnings.append(f"GDTF file {file} could not be used ({type(exc).__name__}: {str(exc)[:80]}) - its fixtures were skipped")
                    by_file[file] = None
            tick("types", len(todo), len(todo))
            for key, file in files.items():
                if file is None:
                    warnings.append(f"GDTF file missing: {key or '(none)'} - its fixtures were skipped")
                type_of[key] = by_file.get(file) if file else None

        # ---- Buehne
        objects: List[Dict[str, Any]] = []
        if want_stage and scan.leaves:
            meshes: Dict[Tuple[str, bool], Optional[Dict[str, Any]]] = {}
            raw: Dict[str, Optional[Dict[str, Any]]] = {}

            def mesh_of(file: str, flip: bool) -> Optional[Dict[str, Any]]:
                if file not in raw:
                    info = names[file]
                    if info.file_size > MAX_MEMBER_BYTES:
                        warnings.append(f"3D file too large: {file}")
                        raw[file] = None
                    else:
                        try:
                            raw[file] = load_mesh(archive.read(info), "." + file.rsplit(".", 1)[-1], up_axis)
                            if opts["colors"] == "neutral":
                                raw[file]["colors"] = np.tile(np.array([158, 158, 161], dtype=np.uint8), (len(raw[file]["tris"]), 1))
                        except MvrError as exc:
                            warnings.append(f"{file}: {exc.message}")
                            raw[file] = None
                if raw[file] is None:
                    return None
                if (file, flip) not in meshes:
                    meshes[(file, flip)] = mirrored(raw[file]) if flip else raw[file]
                return meshes[(file, flip)]

            instanced: List[Tuple[Dict[str, Any], Dict[str, Any], Any, np.ndarray, bool]] = []
            total_files = len({leaf["file"] for leaf in scan.leaves})
            loaded = 0
            for leaf in scan.leaves:
                parts = decompose(leaf["m"])
                if parts is None:
                    continue
                flip = parts[3]
                matrix = FLIP_X @ leaf["m"] if flip else leaf["m"]                    # gespiegelt: erst das Netz spiegeln, dann mit der (jetzt drehungsrichtigen) Matrix platzieren
                if flip:
                    parts = decompose(matrix)
                    report["mirrored"] += 1
                if leaf["file"] not in raw:
                    tick("models", loaded, total_files)
                    loaded += 1
                mesh = mesh_of(leaf["file"], flip)
                if mesh is not None and parts is not None:
                    instanced.append((leaf, mesh, parts, matrix, flip))
            tick("models", total_files, total_files)
            level = 0 if len(instanced) <= stage_capacity else (1 if len({leaf["layer"] for leaf, _, _, _, _ in instanced}) <= stage_capacity else 2)
            report["merged"] = ("none", "layers", "all")[level]
            stored: Dict[Tuple[str, bool], str] = {}
            if level == 0:
                by_content: Dict[str, str] = {}
                for leaf, mesh, (origin, k, rotation, _flip), matrix, flip in instanced:
                    key = (leaf["file"], flip)
                    if key not in stored:
                        digest = hashlib.sha1(mesh["tris"].tobytes() + mesh["colors"].tobytes()).hexdigest()           # gleiche Form + Farben unter anderem Dateinamen = ein Modell
                        if digest not in by_content:
                            by_content[digest] = sim_models.store_triangles(_stl_name(prefix, _label_of(leaf), " (mirrored)" if flip else ""), mesh["tris"], mesh["colors"])["id"]
                            report["models"] += 1
                            report["triangles"] += len(mesh["tris"])
                            report["model_ids"].append(by_content[digest])
                        stored[key] = by_content[digest]
                    lo, hi = mesh["lo"], mesh["hi"]
                    base = np.array([(lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, lo[2], 1.0]) @ matrix
                    objects.append({"type": "model", "name": leaf["name"], "color": "#ffffff", "position": [round(float(v), 4) for v in base[:3]], "rotation": euler_xyz(rotation),
                                    "size": [round(float(max(sim_stages.MIN_SIZE, v)), 4) for v in (hi - lo) * k], "material": "matt", "model": stored[key], "unit": "m"})
            else:
                groups: Dict[str, List[Tuple[Dict[str, Any], Dict[str, Any], Any, np.ndarray, bool]]] = {}
                for item in instanced:
                    groups.setdefault(item[0]["layer"] if level == 1 else prefix, []).append(item)
                for label, items in groups.items():
                    tris = np.concatenate([_world_tris(mesh, matrix) for _leaf, mesh, _p, matrix, _f in items])
                    colors = np.concatenate([mesh["colors"] for _leaf, mesh, _p, _m, _f in items])
                    try:
                        model = sim_models.store_triangles(_stl_name(prefix, label), tris, colors)["id"]
                    except sim_models.ModelError as exc:
                        warnings.append(f"{label}: {exc.message}")
                        continue
                    report["models"] += 1
                    report["triangles"] += len(tris)
                    report["model_ids"].append(model)
                    points = tris.reshape(-1, 3)
                    lo, hi = points.min(axis=0).astype(np.float64), points.max(axis=0).astype(np.float64)
                    objects.append({"type": "model", "name": label, "color": "#ffffff", "position": [round(float((lo[0] + hi[0]) / 2), 4), round(float((lo[1] + hi[1]) / 2), 4), round(float(lo[2]), 4)],
                                    "rotation": [0.0, 0.0, 0.0], "size": [round(float(max(sim_stages.MIN_SIZE, v)), 4) for v in (hi - lo)], "material": "matt", "model": model, "unit": "m"})

        # ---- Scheinwerfer
        items: List[Dict[str, Any]] = []
        if want_fixtures:
            for fx in scan.fixtures:
                ft = type_of.get(fx["gdtf"])
                if ft is None:
                    continue
                modes = ft.get("modes") or [{"name": "default", "channel_count": ft.get("channel_count", 1)}]
                wanted = fx["mode"].lower()
                mode = next((m for m in modes if str(m.get("name", "")).lower() == wanted), None)
                if mode is None:
                    mode = next((m for m in modes if str(m.get("name", "")).lower() == "default"), modes[0])
                    if wanted:
                        warnings.append(f"Mode '{fx['mode']}' not found in {ft.get('name', fx['gdtf'])} - '{mode.get('name')}' used")
                items.append({**fx, "type_id": ft["id"], "mode_name": str(mode.get("name", "default")), "channels": int(mode.get("channel_count", 1))})

        # ---- grosse Koordinaten (Szenen in Landeskoordinaten) auf den Ursprung schieben
        xs = [o["position"][0] for o in objects] + [i["position"][0] for i in items]
        ys = [o["position"][1] for o in objects] + [i["position"][1] for i in items]
        if xs and (abs(min(xs) + max(xs)) / 2 > 150 or abs(min(ys) + max(ys)) / 2 > 150):
            dx, dy = -round((min(xs) + max(xs)) / 2), -round((min(ys) + max(ys)) / 2)
            for entry in objects + items:
                entry["position"][0] = round(entry["position"][0] + dx, 4)
                entry["position"][1] = round(entry["position"][1] + dy, 4)
            report["recentered"] = [float(dx), float(dy)]
            warnings.append(f"The scene was far from the origin and was moved by {dx:g} m / {dy:g} m")
    report.update({"objects": objects, "fixture_items": items, "stage_name": _clean_label(Path(filename).stem, "MVR", 60), "fixtures_in_file": len(scan.fixtures), "parts": len(scan.leaves)})
    report["warnings"] = list(dict.fromkeys(warnings))[:MAX_WARNINGS]
    return report


# ------------------------------------------------------------------------------------------------ Uebernehmen (Zustand, im Ereignis-Thread)
def patch_fixtures(items: List[Dict[str, Any]], warnings: List[str], opts: Optional[Dict[str, Any]] = None) -> Tuple[List[Fixture], Dict[str, Dict[str, Any]], int]:
    """Scheinwerfer anlegen. Rueckgabe: (angelegt, Layout {id: {position, rotation}}, Anzahl mit automatischer Adresse). Nummern (FID) der Datei gelten, wo sie frei sind.
    opts: addressing "file" (Adresse der Datei, plus universe_offset) oder "auto" (alles neu ab start_universe); place_fixtures False = nur patchen, nicht in der 3D-Buehne platzieren."""
    opts = {**DEFAULT_OPTIONS, **(opts or {})}
    used_fids = {fx.fid for fx in state.fixtures.values()}
    next_free: Dict[int, int] = {}
    for fx in state.fixtures.values():
        next_free[fx.universe] = max(next_free.get(fx.universe, 1), fx.start_channel + max(1, fx.channel_count))
    created: List[Fixture] = []
    layout: Dict[str, Dict[str, Any]] = {}
    automatic = 0
    renumbered = 0
    for item in items:
        channels = max(1, item["channels"])
        universe, channel = item["universe"], item["channel"]
        if opts["addressing"] == "auto":
            universe, channel = None, None                                        # alles neu: der Reihe nach ab dem Start-Universum
        elif universe is not None and opts["universe_offset"]:
            universe += opts["universe_offset"]
        valid = universe is not None and MIN_UNIVERSE <= universe <= MAX_UNIVERSE and channel is not None and 1 <= channel and channel + channels - 1 <= 512
        if not valid:
            universe = None
            start = max(MIN_UNIVERSE, min(MAX_UNIVERSE, int(opts["start_universe"] if opts["addressing"] == "auto" else (getattr(state, "default_universe", 1) or 1))))
            for candidate in range(start, MAX_UNIVERSE + 1):
                at = next_free.get(candidate, 1)
                if at + channels - 1 <= 512:
                    universe, channel = candidate, at
                    break
            if universe is None:
                warnings.append(f"No free DMX address left for {item['name']}")
                continue
            automatic += 1 if opts["addressing"] != "auto" else 0
        next_free[universe] = max(next_free.get(universe, 1), channel + channels)
        fid = item["fid"] if item["fid"] and item["fid"] not in used_fids else None
        if item["fid"] and fid is None:
            renumbered += 1
        if fid is None:
            fid = (max(used_fids) + 1) if used_fids else 1
        used_fids.add(fid)
        fx = Fixture(id=str(uuid.uuid4()), fid=fid, name=item["name"][:80], fixture_type=item["type_id"], universe=universe, start_channel=channel, channel_count=channels, mode=item["mode_name"])
        state.fixtures[fx.id] = fx
        created.append(fx)
        if opts["place_fixtures"]:
            layout[fx.id] = {"position": item["position"], "rotation": item["rotation"]}
    if renumbered:
        warnings.append(f"{renumbered} fixture numbers were already in use and got new ones")
    if created:
        state.mark_dirty()
    return created, layout, automatic


# ------------------------------------------------------------------------------------------------ Sitzungen, Auftrag und HTTP
_sessions: Dict[str, Dict[str, Any]] = {}
_session_lock = threading.Lock()
_jobs: Dict[str, Dict[str, Any]] = {}
_tasks: set = set()


def _remember(data: bytes, filename: str) -> str:
    now = time.time()
    with _session_lock:
        for key in [k for k, v in _sessions.items() if now - v["time"] > SESSION_SECONDS]:
            _sessions.pop(key, None)
        while len(_sessions) >= 2:                                                # hoechstens zwei Dateien im Speicher
            _sessions.pop(min(_sessions, key=lambda k: _sessions[k]["time"]), None)
        token = uuid.uuid4().hex
        _sessions[token] = {"data": data, "filename": filename, "time": now}
        return token


def _srv():
    from app import server
    return server


@router.post("/api/mvr/preview")
async def preview(request: Request) -> JSONResponse:
    """Roher Body = die .mvr-Datei (?filename=). Liest nur; Antwort: Zusammenfassung + Sitzung fuer /apply."""
    filename = urllib.parse.unquote(request.query_params.get("filename", "")) or "scene.mvr"
    length = int(request.headers.get("content-length") or 0)
    if length > MAX_ARCHIVE_BYTES:
        return MvrError("too_large", "The file is too large", 413).response()
    data = await request.body()
    try:
        summary = await asyncio.to_thread(summarize, data, filename)
    except MvrError as exc:
        return exc.response()
    return JSONResponse({"ok": True, "session": _remember(data, filename), "summary": summary})


async def _run_job(job: Dict[str, Any], session: Dict[str, Any], stage_mode: str, want_fixtures: bool, opts: Dict[str, Any]) -> None:
    def progress(phase: str, done: int, total: int) -> None:
        job.update(phase=phase, done=done, total=total)

    try:
        srv = _srv()
        sim_stages.store.ensure()
        capacity = sim_stages.MAX_OBJECTS - (len(sim_stages.store.objects) if stage_mode == "add" else 0)
        result = await asyncio.to_thread(build, session["data"], session["filename"], max(1, capacity), opts["up_axis"], stage_mode != "none", want_fixtures, progress, opts)
        job.update(phase="apply", done=0, total=0)
        warnings: List[str] = result["warnings"]
        report: Dict[str, Any] = {"ok": True, "warnings": warnings, "models": result["models"], "triangles": result["triangles"], "merged": result["merged"], "recentered": result["recentered"],
                                  "mirrored": result["mirrored"]}
        store = sim_stages.store
        created: List[Fixture] = []
        layout: Dict[str, Dict[str, Any]] = {}
        automatic = 0
        if want_fixtures and result["fixture_items"]:
            created, layout, automatic = patch_fixtures(result["fixture_items"], warnings, opts)
        if stage_mode != "none" and not result["objects"]:
            warnings.append("The file contains no 3D parts - the stage was not changed")
        if stage_mode != "none" and result["objects"]:
            objects = sim_stages.normalize_objects(result["objects"])
            if stage_mode == "replace":
                store.set_objects(objects)
                store.filename, store.saved_objects = None, []                    # die bisherige Buehnen-Datei bleibt unangetastet; die neue bekommt beim Speichern der Show eine eigene
                store.name = sim_stages.clean_name(result["stage_name"], sim_stages.suggest_name())
                if (sim_stages.library_dir() / sim_stages.filename_for(store.name)).exists():
                    store.name = sim_stages.suggest_name([store.name])
            else:
                store.set_objects(list(store.objects) + objects)
            report["objects"] = len(objects)
        if layout:
            store.set_layout({**store.layout, **layout})
        universes = sorted({fx.universe for fx in created})
        report.update({"fixtures": len(created), "automatic_addresses": automatic, "types_installed": result["types_installed"], "fixtures_in_file": result["fixtures_in_file"],
                       "universes": universes})
        if created:
            await srv.event_bus.broadcast({"type": "fixtures_changed", "payload": {"fixtures": state.fixtures_as_dicts(), "is_dirty": state.is_dirty}})
            await srv._broadcast_library_changed()
        if result["models"]:
            await sim_models._announce()                                          # noqa: SLF001
        if stage_mode != "none" or layout:
            await sim_stages._broadcast(source="mvr")                              # noqa: SLF001
        report["stage_name"] = store.name
        job.update(state="done", result=report, phase="done")
    except MvrError as exc:
        job.update(state="error", error={"code": exc.code, "message": exc.message}, phase="error")
    except Exception as exc:                                                      # noqa: BLE001 - dem Benutzer eine Meldung statt eines stillen Abbruchs
        logger.exception("MVR-Import fehlgeschlagen")
        job.update(state="error", error={"code": "failed", "message": f"{type(exc).__name__}: {exc}"[:200]}, phase="error")


@router.post("/api/mvr/apply")
async def apply(request: Request) -> JSONResponse:
    """Startet den Import im Hintergrund und antwortet sofort mit {job}; den Fortschritt liefert GET /api/mvr/status?job=...
    Einstellungen im Body: session, stage ("replace" | "add" | "none"), fixtures (bool) und optional layers [Namen], addressing ("file" | "auto"), universe_offset, start_universe, place_fixtures, colors ("keep" | "neutral"), up_axis."""
    body = await request.json()
    session = _sessions.get(str(body.get("session", "")))
    if session is None:
        return MvrError("expired", "The file is no longer in memory - choose it again.", 410).response()
    if any(j["state"] == "running" for j in _jobs.values()):
        return MvrError("busy", "Another import is running.", 409).response()
    stage_mode = body.get("stage") if body.get("stage") in ("replace", "add", "none") else "replace"
    want_fixtures = body.get("fixtures") is not False
    opts = clean_options(body)
    for old in [k for k, j in _jobs.items() if j["state"] != "running" and time.time() - j["started"] > 3600]:
        _jobs.pop(old, None)
    job_id = uuid.uuid4().hex
    job = {"state": "running", "phase": "start", "done": 0, "total": 0, "result": None, "error": None, "started": time.time()}
    _jobs[job_id] = job
    task = asyncio.get_running_loop().create_task(_run_job(job, session, stage_mode, want_fixtures, opts))
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)
    return JSONResponse({"ok": True, "job": job_id})


@router.get("/api/mvr/status")
async def status(job: str = "") -> JSONResponse:
    item = _jobs.get(job)
    if item is None:
        return MvrError("not_found", "No such import.", 404).response()
    out = {"ok": True, "state": item["state"], "phase": item["phase"], "done": item["done"], "total": item["total"], "seconds": round(time.time() - item["started"], 1)}
    if item["state"] == "done":
        out["result"] = item["result"]
    if item["state"] == "error":
        out["ok"] = False
        out["error"] = item["error"]["code"]
        out["message"] = item["error"]["message"]
    return JSONResponse(out)
