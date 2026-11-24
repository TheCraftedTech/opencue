# Copyright (C) 2026 Samuel Zenker
# SPDX-License-Identifier: GPL-3.0-or-later
"""
mvr_export.py
MVR-Export (Menue Bibliothek -> "MVR-Szene exportieren"): Scheinwerfer (Patch + Lage) und die 3D-Buehne als .mvr-Datei fuer Vectorworks, Capture, Depence und andere Planungsprogramme.
Gegenstueck zu app/mvr_import.py; die Annahmen sind dieselben, nur umgekehrt (siehe dort):

  * MVR = ZIP mit GeneralSceneDescription.xml, den benutzten .gdtf-Dateien und den 3D-Dateien der Buehne (alles im Hauptordner der ZIP). Aufbau der XML nach der Spezifikation
    DIN SPEC 15801 (MVR 1.6) und nach der Datei, die Vectorworks schreibt: Layer -> ChildList -> Fixture / SceneObject.
  * Matrix = "{u}{v}{w}{o}": u, v, w sind die Bilder der X-, Y-, Z-Achse (Spalten der Drehmatrix), o die Verschiebung in MILLIMETERN, rechtshaendig, Z oben.
    OpenCue speichert Drehungen als Euler-Winkel XYZ in Grad (wie three.js: R = Rx * Ry * Rz) und Positionen in Metern.
  * Adresse: absolut = (Universum - 1) * 512 + Kanal (so liest sie auch der Import).
  * Buehnenobjekte: je ein .glb (glTF 2.0, Meter, Y oben - siehe glb_writer.py); die Groesse steckt in den Netzpunkten, Lage und Drehung in der Matrix. Gleiche Objekte teilen sich eine Datei.

HTTP (Auftrag im Hintergrund, die Oberflaeche zeigt eine Ladeanimation und danach den Download-Knopf):
  GET  /api/mvr/export/info       Zusammenfassung (Scheinwerfer, Typen, Buehne) fuer den Dialog
  POST /api/mvr/export/start      {fixtures, stage, unplaced, name} -> {job}
  GET  /api/mvr/export/status     ?job= -> {state: running|done|error, phase, done, total, result}
  GET  /api/mvr/export/download   ?job= -> die .mvr-Datei (Browser-Download; im Programmfenster oeffnet /api/files/open-download den Standard-Browser)
"""
from __future__ import annotations

import asyncio
import io
import logging
import math
import re
import threading
import time
import uuid
import zipfile
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.parse import quote
from xml.sax.saxutils import escape, quoteattr

import numpy as np
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response

from app import fixture_manager, sim_models, sim_stages
from app.glb_writer import write_glb
from app.version import APP_NAME, APP_VERSION

logger = logging.getLogger("opencue.mvr")
router = APIRouter()

NAMESPACE = uuid.UUID("6f1d2e34-5b7a-4c1e-9a55-0c3e8b7d4a11")           # feste Grundlage fuer abgeleitete Uuids (derselbe Inhalt ergibt immer dieselben Kennungen)
MM = 1000.0
MAX_JOBS_KEPT = 2
JOB_SECONDS = 15 * 60
_UUID_RE = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
# Oberflaechen der Simulation -> glTF-PBR (Metall, Rauheit)
MATERIAL_PBR = {"matt": (0.0, 0.92), "satin": (0.0, 0.55), "glossy": (0.0, 0.25), "metal": (1.0, 0.35), "mirror": (1.0, 0.05)}


# ------------------------------------------------------------------------------------------------ Hilfen
def uid(*parts: str) -> str:
    return str(uuid.uuid5(NAMESPACE, "|".join(parts))).upper()


def fixture_uuid(fixture_id: str) -> str:
    return fixture_id.upper() if _UUID_RE.match(fixture_id or "") else uid("fixture", str(fixture_id))


def rotation_matrix(euler_deg: Any) -> np.ndarray:
    """Euler XYZ in Grad (three.js: R = Rx * Ry * Rz) -> 3x3-Drehmatrix; die Spalten sind die Bilder der Achsen."""
    x, y, z = [math.radians(float(v)) for v in (list(euler_deg or [0, 0, 0]) + [0, 0, 0])[:3]]
    cx, sx, cy, sy, cz, sz = math.cos(x), math.sin(x), math.cos(y), math.sin(y), math.cos(z), math.sin(z)
    rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    return rx @ ry @ rz


def matrix_text(rotation: np.ndarray, position_m: Any) -> str:
    """"{u}{v}{w}{o}" - u, v, w = Spalten der Drehmatrix, o = Position in Millimetern (Zeilenvektor-Schreibweise der MVR-Spezifikation)."""
    p = [float(v) for v in (list(position_m or [0, 0, 0]) + [0, 0, 0])[:3]]
    cells = [tuple(float(rotation[r][c]) for r in range(3)) for c in range(3)] + [tuple(v * MM for v in p)]
    return "".join("{%s}" % ",".join("%.6f" % (v + 0.0) for v in cell) for cell in cells)


def safe_file_name(name: str, taken: Dict[str, str], extension: str) -> str:
    """Dateiname fuer die ZIP: nur A-Z a-z 0-9 _ @ -, ein Punkt vor der Endung, nie zwei Namen, die sich nur durch Gross-/Kleinschreibung unterscheiden."""
    stem = re.sub(r"[^A-Za-z0-9_@-]+", "_", name).strip("_") or "file"
    candidate, n = stem + extension, 1
    while candidate.lower() in taken:
        n += 1
        candidate = f"{stem}_{n}{extension}"
    taken[candidate.lower()] = candidate
    return candidate


def first_mode(gdtf_path: Path) -> str:
    try:
        import zipfile as _z
        from xml.etree import ElementTree
        with _z.ZipFile(gdtf_path) as archive:
            root = ElementTree.fromstring(archive.read("description.xml"))
        mode = root.find("./FixtureType/DMXModes/DMXMode")
        return (mode.get("Name") or "") if mode is not None else ""
    except Exception:                                                                    # noqa: BLE001 - nur ein Vorschlag fuer den Modus
        return ""


def modes_of(gdtf_path: Path) -> List[str]:
    try:
        from xml.etree import ElementTree
        with zipfile.ZipFile(gdtf_path) as archive:
            root = ElementTree.fromstring(archive.read("description.xml"))
        return [m.get("Name") or "" for m in root.findall("./FixtureType/DMXModes/DMXMode")]
    except Exception:                                                                    # noqa: BLE001
        return []


# ------------------------------------------------------------------------------------------------ Scheinwerfer
def collect_fixtures(state: Any, unplaced: bool) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Alle Scheinwerfer der Show, die in die Datei kommen, plus Zaehler fuer die Zusammenfassung. Nicht exportierbar: Geraete ohne GDTF-Datei (eingebaute Generic-Typen)."""
    sim_stages.store.ensure()
    layout = sim_stages.store.layout
    paths = {p.stem: p for p in fixture_manager.gdtf_paths()}
    out: List[Dict[str, Any]] = []
    stats: Dict[str, Any] = {"total": 0, "exportable": 0, "no_gdtf": 0, "unplaced": 0, "types": {}, "missing_types": {}}
    modes_cache: Dict[Path, List[str]] = {}
    for fx in sorted(state.fixtures.values(), key=lambda f: (f.fid or 0, f.universe, f.start_channel)):
        stats["total"] += 1
        path = paths.get(fx.fixture_type)
        if path is None:
            stats["no_gdtf"] += 1
            stats["missing_types"][fx.fixture_type] = stats["missing_types"].get(fx.fixture_type, 0) + 1
            continue
        item = layout.get(fx.id)
        if item is None:
            stats["unplaced"] += 1
            if not unplaced:
                continue
            item = {"position": [0.0, 0.0, 0.0], "rotation": [0.0, 0.0, 0.0]}
        modes = modes_cache.get(path)
        if modes is None:
            modes = modes_cache[path] = modes_of(path)
        mode = fx.mode if fx.mode in modes else (modes[0] if modes else (fx.mode or ""))
        out.append({"fx": fx, "path": path, "mode": mode, "position": item.get("position") or [0, 0, 0], "rotation": item.get("rotation") or [0, 0, 0]})
        stats["exportable"] += 1
        stats["types"][fx.fixture_type] = stats["types"].get(fx.fixture_type, 0) + 1
    return out, stats


# ------------------------------------------------------------------------------------------------ Buehne
def _unit_box() -> np.ndarray:
    lo, hi = np.array([-0.5, -0.5, 0.0]), np.array([0.5, 0.5, 1.0])
    c = np.array([[x, y, z] for z in (lo[2], hi[2]) for y in (lo[1], hi[1]) for x in (lo[0], hi[0])])      # Index = x + 2y + 4z
    quads = [(0, 2, 3, 1), (4, 5, 7, 6), (0, 1, 5, 4), (2, 6, 7, 3), (0, 4, 6, 2), (1, 3, 7, 5)]                # unten, oben, vorn (-Y), hinten (+Y), links (-X), rechts (+X)
    tris = []
    for a, b, c2, d in quads:
        tris += [(c[a], c[b], c[c2]), (c[a], c[c2], c[d])]
    return np.array(tris, dtype=np.float64)


def _unit_cylinder(segments: int = 48) -> np.ndarray:
    tris = []
    for i in range(segments):
        a0, a1 = 2 * math.pi * i / segments, 2 * math.pi * (i + 1) / segments
        p0, p1 = (0.5 * math.cos(a0), 0.5 * math.sin(a0)), (0.5 * math.cos(a1), 0.5 * math.sin(a1))
        tris += [((p0[0], p0[1], 0), (p1[0], p1[1], 0), (p1[0], p1[1], 1)), ((p0[0], p0[1], 0), (p1[0], p1[1], 1), (p0[0], p0[1], 1))]
        tris += [((0, 0, 1), (p0[0], p0[1], 1), (p1[0], p1[1], 1)), ((0, 0, 0), (p1[0], p1[1], 0), (p0[0], p0[1], 0))]
    return np.array(tris, dtype=np.float64)


def _unit_sphere(cols: int = 40, rows: int = 24) -> np.ndarray:
    def point(r: int, c: int) -> Tuple[float, float, float]:
        phi, theta = math.pi * r / rows, 2 * math.pi * c / cols
        return (0.5 * math.sin(phi) * math.cos(theta), 0.5 * math.sin(phi) * math.sin(theta), 0.5 + 0.5 * math.cos(phi))
    tris = []
    for r in range(rows):
        for c in range(cols):
            a, b, c2, d = point(r, c), point(r + 1, c), point(r + 1, c + 1), point(r, c + 1)
            if r > 0:
                tris.append((a, b, d))
            if r < rows - 1:
                tris.append((b, c2, d))
    return np.array(tris, dtype=np.float64)


def _unit_wedge() -> np.ndarray:
    A, B, C = (-0.5, -0.5, 0.0), (0.5, -0.5, 0.0), (-0.5, -0.5, 1.0)                    # wie buildGeometry("wedge") in sim3d_build.js: rechtwinkliges Dreieck, hoch bei -X, Tiefe entlang Y
    D, E, F = (-0.5, 0.5, 0.0), (0.5, 0.5, 0.0), (-0.5, 0.5, 1.0)
    order = [A, B, C, D, F, E, A, D, E, A, E, B, A, C, F, A, F, D, B, E, F, B, F, C]
    return np.array(order, dtype=np.float64).reshape(-1, 3, 3)


_UNIT = {"box": _unit_box, "screen": _unit_box, "cylinder": _unit_cylinder, "sphere": _unit_sphere, "wedge": _unit_wedge}


def _stl_with_colors(data: bytes) -> Tuple[np.ndarray, Optional[np.ndarray]]:
    """Dreiecke und - falls die Datei von OpenCue stammt (MVR-Import) - die Farbe je Dreieck (siehe sim_models.pack_colors)."""
    triangles = sim_models.parse_stl(data)
    colors = None
    try:
        count = len(triangles)
        if len(data) >= 84 + 50 * count and int.from_bytes(data[80:84], "little") == count:
            attr = np.frombuffer(data, dtype=sim_models._STL_RECORD, count=count, offset=84)["attr"].astype(np.uint32)       # noqa: SLF001
            valid = (attr & 0x8000) != 0
            if valid.any():
                colors = np.stack([((attr >> 10) & 31) << 3, ((attr >> 5) & 31) << 3, (attr & 31) << 3], axis=1).astype(np.uint8)
                colors[~valid] = (156, 156, 160)
    except Exception:                                                                    # noqa: BLE001 - dann eben ohne Farben
        colors = None
    return triangles.astype(np.float64), colors


def object_geometry(obj: Dict[str, Any], model_cache: Dict[str, Any]) -> Tuple[np.ndarray, Optional[np.ndarray]]:
    """Netz eines Buehnenobjekts in Metern, Z oben, im Mass der Buehne (Groesse eingerechnet), Ursprung = Mitte der Unterkante - genau wie die Simulation es zeichnet."""
    size = np.array([float(v) for v in obj["size"]], dtype=np.float64)
    if obj["type"] == "model":
        name = obj["model"]
        if name not in model_cache:
            model_cache[name] = _stl_with_colors(sim_models.path_of(name).read_bytes())
        tris, colors = model_cache[name]
        lo, hi = tris.reshape(-1, 3).min(axis=0), tris.reshape(-1, 3).max(axis=0)
        extent = np.where(hi - lo > 1e-9, hi - lo, 1.0)
        centre = np.array([(lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, lo[2]])
        return (tris - centre) / extent * size, colors
    return _UNIT[obj["type"]]() * size, None


def hex_rgb(text: str) -> Tuple[float, float, float]:
    try:
        return tuple(int(text[i:i + 2], 16) / 255.0 for i in (1, 3, 5))                 # type: ignore[return-value]
    except Exception:                                                                    # noqa: BLE001
        return (0.61, 0.61, 0.63)


# ------------------------------------------------------------------------------------------------ Datei bauen
def summarize(state: Any) -> Dict[str, Any]:
    items, stats = collect_fixtures(state, True)
    sim_stages.store.ensure()
    objects = sim_stages.store.objects
    by_type: Dict[str, int] = {}
    for obj in objects:
        by_type[obj["type"]] = by_type.get(obj["type"], 0) + 1
    models = {o["model"] for o in objects if o["type"] == "model"}
    types = [{"id": t, "name": t.replace("@", " ").replace("_", " ")[:70], "count": n} for t, n in sorted(stats["types"].items(), key=lambda kv: -kv[1])]
    placed = stats["exportable"] - stats["unplaced"]
    return {"fixtures": {"total": stats["total"], "exportable": stats["exportable"], "placed": placed, "unplaced": stats["unplaced"], "no_gdtf": stats["no_gdtf"], "types": types[:8], "type_count": len(types),
                         "missing_types": [{"id": k, "count": v} for k, v in stats["missing_types"].items()][:6]},
            "stage": {"name": sim_stages.store.name, "objects": len(objects), "by_type": by_type, "models": len(models), "dirty": bool(sim_stages.store.state_of() == "modified") if hasattr(sim_stages.store, "state_of") else False}}


def build(state: Any, opts: Dict[str, Any], progress: Optional[Callable[[str, int, int], None]] = None) -> Tuple[bytes, Dict[str, Any]]:
    """Die .mvr-Datei als Bytes und ein Bericht {fixtures, types, objects, files, warnings}."""
    note = progress or (lambda phase, done, total: None)
    want_fixtures, want_stage = bool(opts.get("fixtures", True)), bool(opts.get("stage", True))
    warnings: List[str] = []
    report: Dict[str, Any] = {"fixtures": 0, "types": 0, "objects": 0, "models": 0, "files": 0, "warnings": warnings, "skipped_no_gdtf": 0, "skipped_unplaced": 0}
    names: Dict[str, str] = {}                                                            # Kleinschreibung -> Dateiname (keine Doppelten)
    files: List[Tuple[str, bytes]] = []
    layers: List[str] = []

    # ---- Scheinwerfer
    if want_fixtures:
        items, stats = collect_fixtures(state, bool(opts.get("unplaced", False)))
        report["skipped_no_gdtf"], report["skipped_unplaced"] = stats["no_gdtf"], (stats["unplaced"] if not opts.get("unplaced") else 0)
        if stats["no_gdtf"]:
            warnings.append(f"{stats['no_gdtf']} fixtures use a built-in type without a GDTF file and were left out")
        if report["skipped_unplaced"]:
            warnings.append(f"{report['skipped_unplaced']} fixtures are not placed in the 3D stage and were left out")
        gdtf_names: Dict[Path, str] = {}
        for item in items:
            if item["path"] not in gdtf_names:
                gdtf_names[item["path"]] = safe_file_name(item["path"].stem, names, ".gdtf")
        total = len(gdtf_names)
        for i, (path, name) in enumerate(gdtf_names.items()):
            note("types", i, total)
            files.append((name, path.read_bytes()))
        lines: List[str] = []
        for i, item in enumerate(items):
            if i % 25 == 0:
                note("fixtures", i, len(items))
            fx = item["fx"]
            absolute = (int(fx.universe) - 1) * 512 + int(fx.start_channel)
            fid = int(fx.fid or 0)
            lines.append(f"          <Fixture name={quoteattr(str(fx.name)[:80])} uuid=\"{fixture_uuid(fx.id)}\">\n"
                         f"            <Matrix>{matrix_text(rotation_matrix(item['rotation']), item['position'])}</Matrix>\n"
                         f"            <GDTFSpec>{escape(gdtf_names[item['path']])}</GDTFSpec>\n"
                         f"            <GDTFMode>{escape(item['mode'])}</GDTFMode>\n"
                         f"            <Addresses><Address break=\"0\">{absolute}</Address></Addresses>\n"
                         f"            <FixtureID>{fid}</FixtureID>\n"
                         f"            <FixtureIDNumeric>{fid}</FixtureIDNumeric>\n"
                         f"            <UnitNumber>0</UnitNumber>\n"
                         f"          </Fixture>\n")
        if lines:
            layers.append(f"      <Layer name=\"Fixtures\" uuid=\"{uid('layer', 'fixtures')}\">\n        <ChildList>\n" + "".join(lines) + "        </ChildList>\n      </Layer>\n")
        report["fixtures"], report["types"] = len(items), len(gdtf_names)

    # ---- Buehne
    if want_stage:
        sim_stages.store.ensure()
        objects = list(sim_stages.store.objects)
        model_cache: Dict[str, Any] = {}
        meshes: Dict[Tuple, str] = {}                                                      # gleiche Form + Groesse + Farbe + Oberflaeche = eine Datei
        lines = []
        for i, obj in enumerate(objects):
            if i % 5 == 0:
                note("stage", i, len(objects))
            try:
                key = (obj["type"], obj.get("model", ""), tuple(round(float(v), 4) for v in obj["size"]), obj.get("color", ""), obj.get("material", "matt"))
                if key not in meshes:
                    tris, colors = object_geometry(obj, model_cache)
                    metallic, roughness = MATERIAL_PBR.get(obj.get("material", "matt"), (0.0, 0.9))
                    name = safe_file_name(f"{obj['type']}_{len(meshes) + 1:03d}", names, ".glb")
                    files.append((name, write_glb(tris, colors, hex_rgb(obj.get("color", "")), metallic, roughness, obj.get("name", obj["type"]))))
                    meshes[key] = name
                rotation = rotation_matrix(obj["rotation"])
                lines.append(f"          <SceneObject name={quoteattr(str(obj.get('name') or obj['type'])[:80])} uuid=\"{uid('object', str(obj.get('id', i)))}\">\n"
                             f"            <Matrix>{matrix_text(rotation, obj['position'])}</Matrix>\n"
                             f"            <Geometries>\n              <Geometry3D fileName=\"{escape(meshes[key])}\"/>\n            </Geometries>\n"
                             f"          </SceneObject>\n")
            except (OSError, sim_models.ModelError, ValueError, KeyError) as exc:
                warnings.append(f"Object '{obj.get('name', obj.get('type'))}' was left out ({type(exc).__name__})")
        if lines:
            layers.append(f"      <Layer name=\"Stage\" uuid=\"{uid('layer', 'stage')}\">\n        <ChildList>\n" + "".join(lines) + "        </ChildList>\n      </Layer>\n")
        report["objects"], report["models"] = len(lines), len({k[1] for k in meshes if k[0] == "model"})

    if not layers:
        raise ValueError("nothing to export")
    note("pack", 0, 0)
    xml = ("<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"no\" ?>\n"
           f"<GeneralSceneDescription verMajor=\"1\" verMinor=\"6\" provider={quoteattr(APP_NAME)} providerVersion={quoteattr(APP_VERSION)}>\n"
           f"  <UserData>\n    <Data provider={quoteattr(APP_NAME)} ver=\"1\"/>\n  </UserData>\n"
           "  <Scene>\n    <Layers>\n" + "".join(layers) + "    </Layers>\n  </Scene>\n</GeneralSceneDescription>\n")
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("GeneralSceneDescription.xml", xml.encode("utf-8"))
        for name, data in files:
            archive.writestr(name, data)
    report["files"] = len(files)
    return buffer.getvalue(), report


def clean_options(body: Any) -> Dict[str, Any]:
    body = body if isinstance(body, dict) else {}
    name = re.sub(r"[^\w .()-]+", "", str(body.get("name") or "")).strip(" .")[:60] or "OpenCue scene"      # Buchstaben (auch Umlaute), Ziffern, Leerzeichen, _ . ( ) -
    return {"fixtures": body.get("fixtures") is not False, "stage": body.get("stage") is not False, "unplaced": body.get("unplaced") is True, "name": name}


# ------------------------------------------------------------------------------------------------ HTTP
_jobs: Dict[str, Dict[str, Any]] = {}
_lock = threading.Lock()
_tasks: set = set()


def _srv():
    from app import server
    return server


async def _run(job: Dict[str, Any], opts: Dict[str, Any]) -> None:
    def progress(phase: str, done: int, total: int) -> None:
        job.update(phase=phase, done=done, total=total)

    try:
        state = _srv().state
        data, report = await asyncio.to_thread(build, state, opts, progress)
        job.update(state="done", phase="done", data=data, result=dict(report, size=len(data), filename=opts["name"] + ".mvr"))
    except ValueError as exc:
        job.update(state="error", phase="error", error={"code": "empty", "message": str(exc)})
    except Exception as exc:                                                              # noqa: BLE001
        logger.exception("MVR-Export fehlgeschlagen")
        job.update(state="error", phase="error", error={"code": "failed", "message": f"{type(exc).__name__}: {exc}"[:200]})


@router.get("/api/mvr/export/info")
async def export_info() -> JSONResponse:
    try:
        return JSONResponse({"ok": True, **await asyncio.to_thread(summarize, _srv().state)})
    except Exception as exc:                                                              # noqa: BLE001
        logger.exception("MVR-Export: Zusammenfassung fehlgeschlagen")
        return JSONResponse({"ok": False, "error": "failed", "message": f"{type(exc).__name__}: {exc}"[:200]}, status_code=500)


@router.post("/api/mvr/export/start")
async def export_start(request: Request) -> JSONResponse:
    body = await request.json()
    opts = clean_options(body)
    if not opts["fixtures"] and not opts["stage"]:
        return JSONResponse({"ok": False, "error": "nothing", "message": "Choose what to export."}, status_code=400)
    now = time.time()
    with _lock:
        for key in [k for k, j in _jobs.items() if j["state"] != "running" and now - j["started"] > JOB_SECONDS]:
            _jobs.pop(key, None)
        while len([j for j in _jobs.values() if j["state"] != "running"]) >= MAX_JOBS_KEPT:
            _jobs.pop(min((k for k, j in _jobs.items() if j["state"] != "running"), key=lambda k: _jobs[k]["started"]), None)
        job_id = uuid.uuid4().hex
        job = {"state": "running", "phase": "start", "done": 0, "total": 0, "result": None, "error": None, "data": None, "started": now}
        _jobs[job_id] = job
    task = asyncio.get_running_loop().create_task(_run(job, opts))
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)
    return JSONResponse({"ok": True, "job": job_id})


@router.get("/api/mvr/export/status")
async def export_status(job: str = "") -> JSONResponse:
    item = _jobs.get(job)
    if item is None:
        return JSONResponse({"ok": False, "error": "not_found", "message": "No such export."}, status_code=404)
    out: Dict[str, Any] = {"ok": True, "state": item["state"], "phase": item["phase"], "done": item["done"], "total": item["total"], "seconds": round(time.time() - item["started"], 1)}
    if item["state"] == "done":
        out["result"] = item["result"]
    if item["state"] == "error":
        out.update(ok=False, error=item["error"]["code"], message=item["error"]["message"])
    return JSONResponse(out)


@router.get("/api/mvr/export/download")
async def export_download(job: str = "") -> Response:
    item = _jobs.get(job)
    if item is None or item["state"] != "done" or not item.get("data"):
        return JSONResponse({"ok": False, "error": "not_found", "message": "The file is no longer available - export again."}, status_code=404)
    full = str(item["result"]["filename"]) or "scene.mvr"
    ascii_name = re.sub(r"[^A-Za-z0-9 _.()-]+", "_", full) or "scene.mvr"                  # Rueckfall fuer alte Browser; der echte Name (Umlaute) steht in filename*
    disposition = f'attachment; filename="{ascii_name}"; filename*=UTF-8\'\'{quote(full, safe="")}'
    return Response(item["data"], media_type="application/octet-stream", headers={"Content-Disposition": disposition, "Cache-Control": "no-store"})
