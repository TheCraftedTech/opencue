"""
gdtf_model.py
3D-Modelle, Geometrie-Baum und Raeder (Gobos, Farben, Prismen) aus GDTF-Dateien - als Ergaenzung zu pygdtf.

pygdtf bleibt fuer DMX-Modi/Kanaele zustaendig und wird wie bisher benutzt. Es liest aber weder die 3D-Dateien noch Bilder noch den
Geometrie-Baum vollstaendig. Das macht dieses Modul:
- description.xml wird hier selbst gelesen (ElementTree, streng: keine DOCTYPE/ENTITY), daraus: Geometrie-Baum (Position als 4x4-Matrix, Achsen,
  Strahlen), Modell-Tabelle (Datei, Groesse, Grundform), Raeder mit Slots (Farbe, Gobo-Bild).
- die 3D-Dateien in der GDTF (models/gltf/*.glb und models/3ds/*.3ds) liest die Bibliothek "assimp-py" (Assimp: 3DS, GLB, OBJ, FBX ...), die in der
  requirements.txt steht. Ohne sie (oder bei kaputten Dateien) zeigt die Vorschau die Grundformen aus der GDTF (Base, Yoke, Head, Zylinder ...).
- Koordinaten wie in GDTF: rechtshaendig, Z nach oben, Meter. Der Scheinwerfer haengt (Strahl zeigt nach -Z). 3DS und glTF kommen bei Assimp in Y-oben
  heraus und werden hier nach Z-oben gedreht; jedes Modell wird auf die in der GDTF angegebene Groesse (Length=X, Width=Y, Height=Z) gebracht.
"""
from __future__ import annotations

import base64
import math
import os
import re
import tempfile
import zipfile
from array import array
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from xml.etree import ElementTree

try:                                    # die Bibliothek fuer 3D-Dateien (requirements.txt); ohne sie gibt es nur Grundformen
    import assimp_py as _assimp
except Exception:                       # pragma: no cover - hangt von der Installation ab
    _assimp = None

MAX_XML_BYTES = 40 * 1024 * 1024
MAX_MODEL_BYTES = 30 * 1024 * 1024
MAX_ASSET_BYTES = 4 * 1024 * 1024
MAX_TOTAL_INDICES = 900_000            # darueber zeigt die Vorschau Grundformen statt der (zu schweren) Dateien
MAX_REFERENCES = 64                    # GeometryReference (z. B. Pixel einer LED-Leiste) werden hoechstens so oft eingesetzt
MAX_NODES = 600
IDENTITY = [1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0]
GEOMETRY_TAGS = {"Geometry", "Axis", "Beam", "FilterBeam", "FilterColor", "FilterGobo", "FilterShaper", "MediaServerLayer", "MediaServerCamera",
                 "MediaServerMaster", "Display", "Laser", "WiringObject", "Inventory", "Structure", "Support", "Magnet", "GeometryReference"}


def available() -> bool:
    """Kann diese Installation 3D-Dateien lesen (assimp-py vorhanden)?"""
    return _assimp is not None


class ModelError(Exception):
    pass


# ------------------------------------------------------------------------------------------------ XML
def _read_zip(path: Path) -> Tuple[zipfile.ZipFile, Dict[str, str]]:
    archive = zipfile.ZipFile(path)
    return archive, {n.lower(): n for n in archive.namelist()}


def _read_description(archive: zipfile.ZipFile, names: Dict[str, str]) -> ElementTree.Element:
    real = names.get("description.xml")
    if real is None:
        raise ModelError("In der Datei fehlt die description.xml")
    if archive.getinfo(real).file_size > MAX_XML_BYTES:
        raise ModelError("Die description.xml ist ungewoehnlich gross")
    xml = archive.read(real)
    if b"<!ENTITY" in xml or b"<!DOCTYPE" in xml:
        raise ModelError("Die description.xml enthaelt unzulaessige Deklarationen")
    try:
        return ElementTree.fromstring(xml)
    except ElementTree.ParseError as exc:
        raise ModelError("Die description.xml ist kein gueltiges XML") from exc


def _num(text: Any, default: float = 0.0) -> float:
    try:
        value = float(str(text).strip().replace(",", "."))
        return value if math.isfinite(value) else default
    except (TypeError, ValueError):
        return default


def parse_matrix(text: Optional[str]) -> List[float]:
    """GDTF-Position '{a,b,c,d}{e,f,g,h}{i,j,k,l}{0,0,0,1}' -> 16 Zahlen (zeilenweise, Verschiebung in der letzten Spalte)."""
    rows = re.findall(r"\{([^{}]*)\}", text or "")
    values: List[float] = []
    for row in rows[:4]:
        cells = [_num(c) for c in row.split(",")]
        if len(cells) != 4:
            return list(IDENTITY)
        values.extend(cells)
    return values if len(values) == 16 else list(IDENTITY)


def _mul(a: List[float], b: List[float]) -> List[float]:
    return [sum(a[r * 4 + k] * b[k * 4 + c] for k in range(4)) for r in range(4) for c in range(4)]


def _apply(m: List[float], p: Tuple[float, float, float]) -> Tuple[float, float, float]:
    x, y, z = p
    return (m[0] * x + m[1] * y + m[2] * z + m[3], m[4] * x + m[5] * y + m[6] * z + m[7], m[8] * x + m[9] * y + m[10] * z + m[11])


# ------------------------------------------------------------------------------------------------ Modelle und Geometrie
def _models_table(root: ElementTree.Element) -> Dict[str, Dict[str, Any]]:
    table: Dict[str, Dict[str, Any]] = {}
    for m in root.findall("./FixtureType/Models/Model"):
        name = m.get("Name", "")
        if name:
            table[name] = {"name": name, "file": (m.get("File") or "").strip(), "length": _num(m.get("Length")), "width": _num(m.get("Width")),
                           "height": _num(m.get("Height")), "primitive": m.get("PrimitiveType", "Undefined")}
    return table


def _parse_geometry(elem: ElementTree.Element, counter: List[int], depth: int = 0) -> Dict[str, Any]:
    counter[0] += 1
    tag = elem.tag
    node: Dict[str, Any] = {"id": counter[0], "type": tag, "name": elem.get("Name", ""), "model": elem.get("Model", ""), "matrix": parse_matrix(elem.get("Position")),
                            "children": []}
    if tag == "Beam":
        node["beam"] = {"type": elem.get("BeamType", ""), "lamp": elem.get("LampType", ""), "angle": _num(elem.get("BeamAngle")), "field": _num(elem.get("FieldAngle")),
                        "radius": _num(elem.get("BeamRadius")), "power": _num(elem.get("PowerConsumption")), "flux": _num(elem.get("LuminousFlux")),
                        "temperature": _num(elem.get("ColorTemperature")), "throw_ratio": _num(elem.get("ThrowRatio")), "rectangle_ratio": _num(elem.get("RectangleRatio"))}
    if tag == "GeometryReference":
        node["ref"] = elem.get("Geometry", "")
    if depth > 24 or counter[0] > MAX_NODES:
        return node
    for child in elem:
        if child.tag in GEOMETRY_TAGS and counter[0] <= MAX_NODES:
            node["children"].append(_parse_geometry(child, counter, depth + 1))
    return node


def _expand_references(node: Dict[str, Any], tops: Dict[str, Dict[str, Any]], budget: List[int], depth: int = 0) -> None:
    """GeometryReference durch eine Kopie der referenzierten Geometrie ersetzen (an der Position der Referenz)."""
    for i, child in enumerate(node["children"]):
        if child["type"] == "GeometryReference":
            target = tops.get(child.get("ref", ""))
            if target is None or budget[0] <= 0 or depth > 6:
                node["children"][i] = {**child, "type": "Geometry", "model": "", "children": []}
                continue
            budget[0] -= 1
            copy = _clone(target)
            node["children"][i] = {**copy, "name": child["name"] or copy["name"], "matrix": child["matrix"], "type": "Geometry"}
            _expand_references(node["children"][i], tops, budget, depth + 1)
        else:
            _expand_references(child, tops, budget, depth)


_next_id = [100000]


def _clone(node: Dict[str, Any]) -> Dict[str, Any]:
    _next_id[0] += 1
    copy = {k: v for k, v in node.items() if k != "children"}
    copy["id"] = _next_id[0]
    copy["children"] = [_clone(c) for c in node["children"]]
    return copy


def _walk(node: Dict[str, Any]):
    yield node
    for child in node["children"]:
        yield from _walk(child)


def _roots(root: ElementTree.Element) -> Tuple[List[Dict[str, Any]], Optional[Dict[str, Any]], int]:
    counter = [0]
    tops = [_parse_geometry(e, counter) for e in root.findall("./FixtureType/Geometries/*") if e.tag in GEOMETRY_TAGS]
    by_name = {t["name"]: t for t in tops if t["type"] != "GeometryReference"}
    budget = [MAX_REFERENCES]
    for top in tops:
        _expand_references(top, by_name, budget)
    wanted = ""
    first_mode = root.find("./FixtureType/DMXModes/DMXMode")
    if first_mode is not None:
        wanted = first_mode.get("Geometry", "")
    main = by_name.get(wanted) or next((t for t in tops if t["type"] != "GeometryReference"), None)
    return tops, main, counter[0]


# ------------------------------------------------------------------------------------------------ Grundformen
def _mesh_from_lists(pos: List[float], nrm: List[float], idx: List[int]) -> Dict[str, Any]:
    return {"pos": array("f", pos), "nrm": array("f", nrm), "idx": array("I", idx), "color": None, "opacity": 1.0}


def _box(lx: float, ly: float, lz: float, cx: float = 0.0, cy: float = 0.0, cz: float = 0.0) -> Tuple[List[float], List[float], List[int]]:
    hx, hy, hz = lx / 2, ly / 2, lz / 2
    faces = [((1, 0, 0), [(1, -1, -1), (1, 1, -1), (1, 1, 1), (1, -1, 1)]), ((-1, 0, 0), [(-1, 1, -1), (-1, -1, -1), (-1, -1, 1), (-1, 1, 1)]),
             ((0, 1, 0), [(1, 1, -1), (-1, 1, -1), (-1, 1, 1), (1, 1, 1)]), ((0, -1, 0), [(-1, -1, -1), (1, -1, -1), (1, -1, 1), (-1, -1, 1)]),
             ((0, 0, 1), [(-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1)]), ((0, 0, -1), [(-1, 1, -1), (1, 1, -1), (1, -1, -1), (-1, -1, -1)])]
    pos: List[float] = []
    nrm: List[float] = []
    idx: List[int] = []
    for normal, corners in faces:
        base = len(pos) // 3
        for sx, sy, sz in corners:
            pos += [cx + sx * hx, cy + sy * hy, cz + sz * hz]
            nrm += list(normal)
        idx += [base, base + 1, base + 2, base, base + 2, base + 3]
    return pos, nrm, idx


def _ellipsoid(rx: float, ry: float, rz: float, cols: int = 24, rows: int = 14) -> Tuple[List[float], List[float], List[int]]:
    pos: List[float] = []
    nrm: List[float] = []
    idx: List[int] = []
    for r in range(rows + 1):
        phi = math.pi * r / rows
        for c in range(cols + 1):
            theta = 2 * math.pi * c / cols
            x, y, z = math.sin(phi) * math.cos(theta), math.sin(phi) * math.sin(theta), math.cos(phi)
            pos += [x * rx, y * ry, z * rz]
            nx, ny, nz = x / max(rx, 1e-9), y / max(ry, 1e-9), z / max(rz, 1e-9)
            length = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
            nrm += [nx / length, ny / length, nz / length]
    for r in range(rows):
        for c in range(cols):
            a = r * (cols + 1) + c
            b = a + cols + 1
            idx += [a, b, a + 1, a + 1, b, b + 1]
    return pos, nrm, idx


def _cylinder(rx: float, ry: float, h: float, segments: int = 32) -> Tuple[List[float], List[float], List[int]]:
    pos: List[float] = []
    nrm: List[float] = []
    idx: List[int] = []
    for i in range(segments + 1):
        a = 2 * math.pi * i / segments
        ca, sa = math.cos(a), math.sin(a)
        nx, ny = ca / max(rx, 1e-9), sa / max(ry, 1e-9)
        length = math.sqrt(nx * nx + ny * ny) or 1.0
        for z in (-h / 2, h / 2):
            pos += [rx * ca, ry * sa, z]
            nrm += [nx / length, ny / length, 0.0]
    for i in range(segments):
        a = i * 2
        idx += [a, a + 2, a + 1, a + 1, a + 2, a + 3]
    for z, nz in ((h / 2, 1.0), (-h / 2, -1.0)):                    # Deckel
        centre = len(pos) // 3
        pos += [0.0, 0.0, z]
        nrm += [0.0, 0.0, nz]
        for i in range(segments + 1):
            a = 2 * math.pi * i / segments
            pos += [rx * math.cos(a), ry * math.sin(a), z]
            nrm += [0.0, 0.0, nz]
        for i in range(segments):
            idx += [centre, centre + 1 + i, centre + 2 + i] if nz > 0 else [centre, centre + 2 + i, centre + 1 + i]
    return pos, nrm, idx


def _merge(*parts: Tuple[List[float], List[float], List[int]]) -> Tuple[List[float], List[float], List[int]]:
    pos: List[float] = []
    nrm: List[float] = []
    idx: List[int] = []
    for p, n, i in parts:
        base = len(pos) // 3
        pos += p
        nrm += n
        idx += [base + k for k in i]
    return pos, nrm, idx


def primitive_mesh(kind: str, length: float, width: float, height: float) -> Optional[Dict[str, Any]]:
    """Grundform aus der GDTF (PrimitiveType) mit den Massen des Modells: Length=X, Width=Y, Height=Z, Mittelpunkt im Ursprung."""
    lx, ly, lz = (max(length, 0.001), max(width, 0.001), max(height, 0.001))
    if kind in ("Cube", "Scanner", "Scanner1_1", "Base", "Base1_1"):
        parts = _box(lx, ly, lz)
    elif kind == "Sphere":
        parts = _ellipsoid(lx / 2, ly / 2, lz / 2)
    elif kind in ("Cylinder", "Conventional", "Conventional1_1", "Head", "Pigtail"):
        parts = _cylinder(lx / 2, ly / 2, lz)
    elif kind == "Yoke":                                              # U-Buegel: Quersteg oben, zwei Arme nach unten
        arm = max(lx * 0.12, 0.004)
        bar = max(lz * 0.16, 0.004)
        parts = _merge(_box(lx, ly, bar, 0, 0, lz / 2 - bar / 2), _box(arm, ly, lz, -lx / 2 + arm / 2, 0, 0), _box(arm, ly, lz, lx / 2 - arm / 2, 0, 0))
    else:
        return None
    mesh = _mesh_from_lists(*parts)
    mesh["color"] = {"Yoke": [0.46, 0.47, 0.52], "Head": [0.34, 0.35, 0.39]}.get(kind, [0.3, 0.31, 0.35])
    return mesh


# ------------------------------------------------------------------------------------------------ Dateien (assimp-py)
def _y_up_to_z_up(values: array) -> None:
    for i in range(0, len(values) - 2, 3):
        y, z = values[i + 1], values[i + 2]
        values[i + 1] = -z
        values[i + 2] = y


def _load_file(data: bytes, extension: str) -> List[Dict[str, Any]]:
    """3D-Datei (3ds/glb) lesen -> Teile je Material (Z oben, Meter). Wirft ModelError."""
    if _assimp is None:
        raise ModelError("assimp-py ist nicht installiert")
    flags = _assimp.Process_Triangulate | _assimp.Process_JoinIdenticalVertices | _assimp.Process_GenSmoothNormals | _assimp.Process_PreTransformVertices
    fd, name = tempfile.mkstemp(suffix=extension, prefix="opencue-model-")
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
        try:
            scene = _assimp.import_file(name, flags)
        except Exception as exc:
            raise ModelError(f"Die 3D-Datei konnte nicht gelesen werden ({type(exc).__name__})") from exc
    finally:
        try:
            os.unlink(name)
        except OSError:
            pass
    parts: List[Dict[str, Any]] = []
    for mesh in scene.meshes:
        if not mesh.num_vertices or not mesh.num_faces:
            continue
        pos = array("f")
        pos.frombytes(bytes(mesh.vertices))
        nrm = array("f")
        nrm.frombytes(bytes(mesh.normals)) if len(mesh.normals) else nrm.extend([0.0, 1.0, 0.0] * mesh.num_vertices)
        idx = array("I")
        idx.frombytes(bytes(mesh.indices))
        if len(pos) != mesh.num_vertices * 3 or len(nrm) != len(pos) or not idx or max(idx) >= mesh.num_vertices:
            continue
        _y_up_to_z_up(pos)
        _y_up_to_z_up(nrm)
        color, opacity = [0.5, 0.5, 0.5], 1.0
        try:
            material = scene.materials[mesh.material_index]
            diffuse = material.get("COLOR_DIFFUSE")
            if diffuse:
                color = [float(c) for c in diffuse[:3]]
                if min(color) > 0.92:                                 # reines Weiss = "keine Farbe angegeben": Scheinwerfer sind meist dunkel
                    color = [0.36, 0.37, 0.41]
            opacity = float(material.get("OPACITY", 1.0))
        except Exception:
            pass
        parts.append({"pos": pos, "nrm": nrm, "idx": idx, "color": color, "opacity": opacity})
    if not parts:
        raise ModelError("Die 3D-Datei enthaelt keine Flaechen")
    return parts


def _bounds(parts: List[Dict[str, Any]]) -> Optional[List[float]]:
    lo = [math.inf] * 3
    hi = [-math.inf] * 3
    for part in parts:
        pos = part["pos"]
        for axis in range(3):
            column = pos[axis::3]
            if column:
                lo[axis] = min(lo[axis], min(column))
                hi[axis] = max(hi[axis], max(column))
    return None if lo[0] == math.inf else lo + hi


def _fit(parts: List[Dict[str, Any]], info: Dict[str, Any]) -> None:
    """Das Modell auf die Groesse aus der GDTF bringen (gleichmaessig; faengt Millimeter- statt Meter-Dateien ab)."""
    box = _bounds(parts)
    target = max(info["length"], info["width"], info["height"])
    if not box or target <= 0:
        return
    extent = max(box[3] - box[0], box[4] - box[1], box[5] - box[2])
    if extent <= 0:
        return
    factor = target / extent
    if 0.97 <= factor <= 1.03:
        return
    for part in parts:
        pos = part["pos"]
        for i in range(len(pos)):
            pos[i] *= factor


def _pack(part: Dict[str, Any]) -> Dict[str, Any]:
    idx = part["idx"]
    vertices = len(part["pos"]) // 3
    small = vertices < 65536
    packed = array("H", idx) if small else idx
    return {"vertices": vertices, "indices": len(idx), "index_bits": 16 if small else 32, "color": [round(c, 3) for c in (part["color"] or [0.2, 0.2, 0.2])],
            "opacity": round(part["opacity"], 3), "pos": base64.b64encode(part["pos"].tobytes()).decode("ascii"),
            "nrm": base64.b64encode(part["nrm"].tobytes()).decode("ascii"), "idx": base64.b64encode(packed.tobytes()).decode("ascii")}


def _find_file(names: Dict[str, str], stem: str) -> Optional[Tuple[str, str]]:
    stem = re.sub(r"\.(3ds|glb|gltf)$", "", stem, flags=re.IGNORECASE)
    for folder, ext in (("models/gltf", ".glb"), ("models/3ds", ".3ds")):
        real = names.get(f"{folder}/{stem}{ext}".lower())
        if real:
            return real, ext
    return None


# ------------------------------------------------------------------------------------------------ Raeder
def _xyy_to_rgb(text: str) -> Optional[List[int]]:
    parts = [_num(p, -1) for p in (text or "").split(",")]
    if len(parts) != 3 or parts[1] <= 0:
        return None
    x, y, big_y = parts[0], parts[1], max(parts[2], 0.0) / 100.0
    X, Y, Z = x * big_y / y, big_y, (1 - x - y) * big_y / y
    r, g, b = (3.2406 * X - 1.5372 * Y - 0.4986 * Z, -0.9689 * X + 1.8758 * Y + 0.0415 * Z, 0.0557 * X - 0.2040 * Y + 1.0570 * Z)
    top = max(r, g, b, 1e-6)
    scale = 1.0 / top * max(0.35, min(1.0, big_y))              # Farbton voll zeigen, dunkle Filter etwas dunkler
    out = []
    for c in (r, g, b):
        c = max(0.0, c * scale)
        c = 12.92 * c if c <= 0.0031308 else 1.055 * (c ** (1 / 2.4)) - 0.055
        out.append(int(round(max(0.0, min(1.0, c)) * 255)))
    return out


def _asset_for(names: Dict[str, str], media: str) -> str:
    if not media:
        return ""
    base = media.replace("\\", "/").strip("/")
    for candidate in (base, f"wheels/{base}"):
        for ext in ("", ".png", ".svg"):
            real = names.get(f"{candidate}{ext}".lower())
            if real and real.lower().startswith("wheels/") and real.lower().endswith((".png", ".svg")):
                return real
    return ""


def wheels(root: ElementTree.Element, names: Dict[str, str]) -> List[Dict[str, Any]]:
    result = []
    for wheel in root.findall("./FixtureType/Wheels/Wheel")[:40]:
        slots = []
        for slot in wheel.findall("Slot")[:128]:
            media = slot.get("MediaFileName", "")
            facets = slot.findall("Facet")
            slots.append({"name": slot.get("Name", ""), "color": _xyy_to_rgb(slot.get("Color", "")), "image": _asset_for(names, media), "media": media,
                          "filter": slot.get("Filter", ""), "facets": len(facets)})
        images = sum(1 for s in slots if s["image"])
        has_facets = any(s["facets"] for s in slots)
        name = wheel.get("Name", "")
        if has_facets:
            kind = "prism"
        elif re.search(r"gobo|pattern|muster", name, re.IGNORECASE) or (images * 2 > len(slots) and not re.search(r"colou?r|farb", name, re.IGNORECASE)):
            kind = "gobo"
        else:
            kind = "color"
        result.append({"name": name, "kind": kind, "slots": slots})
    return result


# ------------------------------------------------------------------------------------------------ Oeffentliche Funktionen
def structure(path: Path) -> Dict[str, Any]:
    """Raeder, Strahlen/Optik, Anschluesse und eine Uebersicht der Modelle fuer den Detail-Dialog (immer, ohne 3D-Daten zu laden)."""
    archive, names = _read_zip(path)
    try:
        root = _read_description(archive, names)
        models = _models_table(root)
        _tops, main, _count = _roots(root)
        beams = [n["beam"] | {"name": n["name"]} for n in (_walk(main) if main else []) if n.get("beam")]
        connectors = [{"name": c.get("Name", ""), "type": c.get("Type", "")} for c in root.findall("./FixtureType/PhysicalDescriptions/Connectors/Connector")[:20]]
        emitters = [{"name": e.get("Name", ""), "wavelength": _num(e.get("DominantWaveLength")), "color": _xyy_to_rgb(e.get("Color", ""))}
                    for e in root.findall("./FixtureType/PhysicalDescriptions/Emitters/Emitter")[:40]]
        files = sum(1 for m in models.values() if m["file"] and _find_file(names, m["file"]))
        return {"wheels": wheels(root, names), "beams": beams[:12], "connectors": connectors, "emitters": emitters,
                "models": {"count": len(models), "files": files, "primitives": sum(1 for m in models.values() if not (m["file"] and _find_file(names, m["file"])) and m["primitive"] not in ("Undefined", "")),
                           "reader": available()}}
    finally:
        archive.close()


def asset(path: Path, relative: str) -> Tuple[bytes, str]:
    """Bild aus dem Ordner wheels/ der GDTF (png/svg): (Bytes, Inhaltstyp)."""
    archive, names = _read_zip(path)
    try:
        clean = relative.replace("\\", "/").strip("/")
        real = names.get(clean.lower())
        if real is None or not real.lower().startswith("wheels/") or not real.lower().endswith((".png", ".svg")) or ".." in clean:
            raise ModelError("Unbekannte Datei")
        if archive.getinfo(real).file_size > MAX_ASSET_BYTES:
            raise ModelError("Die Datei ist zu gross")
        return archive.read(real), "image/svg+xml" if real.lower().endswith(".svg") else "image/png"
    finally:
        archive.close()


def _axes(main: Dict[str, Any], root: ElementTree.Element) -> Dict[str, Any]:
    """Pan-/Tilt-Achse: die erste und zweite Axis von oben nach unten (Pan dreht um Z, Tilt um X); Bereiche aus den Kanaelen des ersten Modus."""
    axes = [n for n in _walk(main) if n["type"] == "Axis"]
    ranges: Dict[str, Tuple[float, float]] = {}
    raw: Dict[str, Tuple[float, float]] = {}                      # (Wert bei DMX 0, Wert bei DMX max) in der Richtung der Datei
    mode = root.find("./FixtureType/DMXModes/DMXMode")
    if mode is not None:
        for logical in mode.iter("LogicalChannel"):
            attr = logical.get("Attribute", "")
            if attr in ("Pan", "Tilt", "Zoom", "Focus1") and attr not in ranges:
                function = logical.find("ChannelFunction")
                if function is not None:
                    a, b = _num(function.get("PhysicalFrom"), -90.0), _num(function.get("PhysicalTo"), 90.0)
                    ranges[attr] = (min(a, b), max(a, b))               # sortiert (fuer die Schieberegler der Details-Ansicht)
                    raw[attr] = (a, b)                                  # manche Dateien geben den Bereich umgekehrt an (270 ... -270): die Simulation folgt der Richtung der Datei
    out: Dict[str, Any] = {}
    if "Zoom" in ranges:                                         # Oeffnungswinkel in Grad bei Zoom-Wert 0 % ... 100 % (die Simulation stellt den Lichtkegel danach ein)
        segments = _zoom_segments(root)
        if segments:
            out["zoom"] = {"from": segments[0][2], "to": segments[-1][3], "segments": segments}
    if "Pan" in ranges and axes:
        out["pan"] = {"node": axes[0]["id"], "min": ranges["Pan"][0], "max": ranges["Pan"][1], "from": raw["Pan"][0], "to": raw["Pan"][1]}
    if "Tilt" in ranges:
        tilt_axis = axes[1] if len(axes) > 1 else (axes[0] if "Pan" not in ranges and axes else None)
        if tilt_axis is not None:
            out["tilt"] = {"node": tilt_axis["id"], "min": ranges["Tilt"][0], "max": ranges["Tilt"][1], "from": raw["Tilt"][0], "to": raw["Tilt"][1]}
    if "Focus1" in raw:                                          # Fokus: Bereich der Funktion (Einheit meist 0..1 ohne Bedeutung; echte Meterangaben werden von der Simulation erkannt)
        out["focus"] = {"from": raw["Focus1"][0], "to": raw["Focus1"][1]}
    return out


def _dmx_fraction(text: str, default: float = 0.0) -> float:
    """DMX-Wert der GDTF ("128/1" = 8 Bit, "32896/2" = 16 Bit) als Anteil 0..1 des Kanalbereichs."""
    try:
        value, _, size = str(text or "").partition("/")
        bytes_ = max(1, int(size or 1))
        return max(0.0, min(1.0, float(value) / (256 ** bytes_ - 1)))
    except (TypeError, ValueError):
        return default


def _zoom_segments(root: ElementTree.Element) -> List[List[float]]:
    """Zoom-Funktionen des ersten Modus als Abschnitte [von, bis, Winkel bei von, Winkel bei bis] (von/bis als Anteil 0..1 des Kanals, Winkel in Grad - in der Richtung der
    Datei, nicht sortiert: viele Geraete zoomen mit steigendem DMX-Wert enger). Jede Funktion gilt bis zum Anfang der naechsten."""
    mode = root.find("./FixtureType/DMXModes/DMXMode")
    if mode is None:
        return []
    for logical in mode.iter("LogicalChannel"):
        if logical.get("Attribute", "") != "Zoom":
            continue
        functions = logical.findall("ChannelFunction")
        segments: List[List[float]] = []
        for index, function in enumerate(functions):
            a, b = _num(function.get("PhysicalFrom"), 0.0), _num(function.get("PhysicalTo"), 0.0)
            if a <= 0 or b <= 0:
                continue
            start = _dmx_fraction(function.get("DMXFrom", "0/1"))
            end = _dmx_fraction(functions[index + 1].get("DMXFrom", "")) if index + 1 < len(functions) else 1.0
            if end < start:
                continue
            segments.append([round(start, 5), round(end, 5), a, b])
        if segments:
            return segments
    return []


def scene(path: Path) -> Dict[str, Any]:
    """Alles fuer die 3D-Vorschau: Geometrie-Baum, Netze der benutzten Modelle (Dateien, sonst Grundformen), Achsen, Strahlen, Ausdehnung."""
    archive, names = _read_zip(path)
    notes: List[str] = []
    try:
        root = _read_description(archive, names)
        models = _models_table(root)
        _tops, main, _count = _roots(root)
        if main is None:
            return {"available": False, "reason": "no_geometry"}
        used = []
        for node in _walk(main):
            if node["model"] and node["model"] in models and node["model"] not in used:
                used.append(node["model"])
        meshes: Dict[str, List[Dict[str, Any]]] = {}
        from_files = from_primitives = 0
        total = 0
        for key in used:
            info = models[key]
            parts: Optional[List[Dict[str, Any]]] = None
            found = _find_file(names, info["file"]) if info["file"] else None
            if found and total < MAX_TOTAL_INDICES:
                real, ext = found
                try:
                    if archive.getinfo(real).file_size > MAX_MODEL_BYTES:
                        raise ModelError("zu gross")
                    parts = _load_file(archive.read(real), ext)
                    _fit(parts, info)
                    from_files += 1
                    total += sum(len(p["idx"]) for p in parts)
                except ModelError as exc:
                    notes.append(f"{info['file']}: {exc}")
                    parts = None
            elif found:
                notes.append(f"{info['file']}: zu detailreich")
            if parts is None:
                primitive = primitive_mesh(info["primitive"], info["length"], info["width"], info["height"])
                if primitive is not None:
                    parts = [primitive]
                    from_primitives += 1
            if parts:
                meshes[key] = parts
        if not meshes:
            return {"available": False, "reason": "no_models", "notes": notes, "reader": available()}
        # Ausdehnung aus Netzen und Positionen
        lo = [math.inf] * 3
        hi = [-math.inf] * 3

        def grow(node: Dict[str, Any], parent: List[float]) -> None:
            world = _mul(parent, node["matrix"])
            parts_ = meshes.get(node["model"])
            if parts_:
                box = _bounds(parts_)
                if box:
                    for cx in (box[0], box[3]):
                        for cy in (box[1], box[4]):
                            for cz in (box[2], box[5]):
                                p = _apply(world, (cx, cy, cz))
                                for axis in range(3):
                                    lo[axis] = min(lo[axis], p[axis])
                                    hi[axis] = max(hi[axis], p[axis])
            for child in node["children"]:
                grow(child, world)

        grow(main, list(IDENTITY))
        # Strahl-Knoten ohne Modell zaehlen mit (Ursprung)
        bounds = None if lo[0] == math.inf else [round(v, 5) for v in lo + hi]
        packed = {key: [_pack(p) for p in parts] for key, parts in meshes.items()}
        return {"available": True, "source": "files" if from_files and not from_primitives else "primitives" if from_primitives and not from_files else "mixed",
                "reader": available(), "notes": notes[:6], "root": main, "models": packed, "bounds": bounds, "axes": _axes(main, root),
                "stats": {"files": from_files, "primitives": from_primitives, "vertices": sum(p["vertices"] for ps in packed.values() for p in ps),
                          "triangles": sum(p["indices"] for ps in packed.values() for p in ps) // 3}}
    finally:
        archive.close()
