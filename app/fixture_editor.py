# Copyright (C) 2026 Samuel Zenker
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Eigene Scheinwerfer anlegen (Bibliothek -> "Eigener Scheinwerfer"): aus einer einfachen Beschreibung (Hersteller, Name, Kategorie, Stichwoerter, Modi, Kanaele mit Attribut, 8/16 Bit, Standardwert, benannten Bereichen,
optional Profilbild und 3D-Modell) wird eine ECHTE GDTF-Datei (GDTF 1.2, Aufbau wie bei GDTF Builder / GDTF Share) gebaut und wie jede andere Datei in die Bibliothek eingebaut. Die Datei laesst sich aus dem Ordner kopieren
und auf einem anderen Rechner (oder in jeder anderen GDTF-Software) importieren; das Programm behandelt sie nicht anders als Dateien von GDTF Share.

Die Beschreibung steckt zusaetzlich als `opencue_editor.json` in der ZIP-Datei: daran erkennt die Bibliothek "eigene" Typen (Kennzeichen "eigen, ungeprueft"), und der Editor kann sie wieder oeffnen. Programme, die das nicht kennen,
ignorieren die Zusatzdatei.

  spec = {"manufacturer", "name", "short_name"?, "description"?, "category"?, "tags"?: [..], "weight"?,
          "thumbnail"?: {"keep": true} | {"data": <PNG als Base64>} | {"copy_from": <Typ-ID>},
          "model"?: {"keep": true, "length", "width", "height"} | {"filename", "data": <Base64>, "length", "width", "height"},
          "modes": [{"name", "channels": [{"attribute", "label"?, "bits": 8|16, "default": 0-255, "ranges": [{"from": 0-255, "name"}], "physical_from"?, "physical_to"?}]}]}
"""
from __future__ import annotations

import base64
import binascii
import io
import json
import re
import struct
import uuid
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from xml.etree import ElementTree as ET

MARKER = "opencue_editor.json"
MAX_MODES = 8
MAX_CHANNELS = 128           # Eintraege je Modus
MAX_FOOTPRINT = 512
MAX_RANGES = 64
MAX_TAGS = 12
MAX_IMAGE_BYTES = 1_500_000
MAX_MODEL_BYTES = 25 * 1024 * 1024
MAX_MODEL_TRIANGLES = 250_000          # darueber zeigt die 3D-Vorschau nur Grundformen (siehe gdtf_model.MAX_TOTAL_INDICES)
CATEGORIES = ("moving_head", "led_bar", "par", "dimmer", "strobe", "effect", "other")

# Auswahl-Liste: (Name, Anzeigename, Feature, Gruppe, physikalische Einheit, leuchtet). Namen und Features wie in echten GDTF-Dateien (z. B. Fog1 -> Control.Control).
_PALETTE_SRC = [
    ("Dimmer", "Dim", "Dimmer.Dimmer", "dimmer", "None", True),
    ("ColorAdd_R", "R", "Color.RGB", "color", "ColorComponent", True),
    ("ColorAdd_G", "G", "Color.RGB", "color", "ColorComponent", True),
    ("ColorAdd_B", "B", "Color.RGB", "color", "ColorComponent", True),
    ("ColorAdd_W", "White", "Color.RGB", "color", "ColorComponent", True),
    ("ColorAdd_WW", "Warm White", "Color.RGB", "color", "ColorComponent", True),
    ("ColorAdd_CW", "Cold White", "Color.RGB", "color", "ColorComponent", True),
    ("ColorAdd_RY", "Amber", "Color.RGB", "color", "ColorComponent", True),
    ("ColorAdd_UV", "UV", "Color.RGB", "color", "ColorComponent", True),
    ("ColorSub_C", "C", "Color.RGB", "color", "ColorComponent", True),
    ("ColorSub_M", "M", "Color.RGB", "color", "ColorComponent", True),
    ("ColorSub_Y", "Y", "Color.RGB", "color", "ColorComponent", True),
    ("CTO", "CTO", "Color.Color", "color", "None", True),
    ("ColorMacro1", "Color Macro1", "Color.RGB", "color", "None", True),
    ("Pan", "P", "Position.PanTilt", "position", "Angle", True),
    ("Tilt", "T", "Position.PanTilt", "position", "Angle", True),
    ("PositionMSpeed", "Pos MSpeed", "Control.Control", "position", "None", False),
    ("Shutter1", "Sh1", "Beam.Beam", "beam", "None", True),
    ("StrobeRate", "Strobe Rate", "Beam.Beam", "beam", "None", True),
    ("Zoom", "Zoom", "Focus.Focus", "beam", "Angle", True),
    ("Focus1", "Focus1", "Focus.Focus", "beam", "None", True),
    ("Iris", "Iris", "Beam.Beam", "beam", "None", True),
    ("Frost1", "Frost1", "Beam.Beam", "beam", "None", True),
    ("Effects1", "FX1", "Beam.Beam", "effects", "None", True),
    ("Effects1Rate", "FX1 Rate", "Beam.Beam", "effects", "Frequency", True),
    ("Fog1", "Fog1", "Control.Control", "effects", "None", False),
    ("Fog2", "Fog2", "Control.Control", "effects", "None", False),
    ("Fog3", "Fog3", "Control.Control", "effects", "None", False),
    ("Haze1", "Haze1", "Control.Control", "effects", "None", False),
    ("Haze2", "Haze2", "Control.Control", "effects", "None", False),
    ("Haze3", "Haze3", "Control.Control", "effects", "None", False),
    ("Fan1", "Fan1", "Control.Control", "effects", "None", False),
    ("Fan2", "Fan2", "Control.Control", "effects", "None", False),
    ("Fan3", "Fan3", "Control.Control", "effects", "None", False),
    ("Control1", "Ctrl1", "Control.Control", "control", "None", False),
    ("Control2", "Ctrl2", "Control.Control", "control", "None", False),
    ("Control3", "Ctrl3", "Control.Control", "control", "None", False),
    ("LampControl", "Lamp Ctrl", "Control.Control", "control", "None", False),
    ("NoFeature", "NoFeature", "Control.Control", "control", "None", False),
]
PALETTE: List[Dict[str, Any]] = [{"name": n, "pretty": p, "feature": f, "group": g, "unit": u, "light": flag} for n, p, f, g, u, flag in _PALETTE_SRC]
_BY_NAME = {item["name"]: item for item in PALETTE}
_PHYSICAL = {"Pan": (-270.0, 270.0), "Tilt": (-135.0, 135.0), "Zoom": (10.0, 40.0)}      # Standard fuer die Felder "Winkel von / bis" (Grad)
_ATTR_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_ \-]{0,39}$")
_IDENT = "{1.000000,0.000000,0.000000,0.000000}{0.000000,1.000000,0.000000,0.000000}{0.000000,0.000000,1.000000,%s}{0,0,0,1}"


class EditorError(Exception):
    """code = maschinenlesbar (die Oberflaeche uebersetzt ihn), params = Werte fuer den Text, message = deutscher Rueckfall."""

    def __init__(self, code: str, message: str, **extra: Any) -> None:
        super().__init__(message)
        self.code, self.message, self.extra = code, message, extra


def _text(value: Any, limit: int, field: str, required: bool = False) -> str:
    out = re.sub(r"[\x00-\x1f\x7f]", " ", str(value if value is not None else "")).strip()
    if required and not out:
        raise EditorError("missing", f"{field} is missing", field=field)
    if len(out) > limit:
        raise EditorError("too_long", f"{field} is too long (max. {limit} characters)", field=field, limit=limit)
    return out


def _label(value: Any, field: str) -> str:
    return _text(value, 40, field).replace(".", " ").replace('"', " ")             # der Punkt trennt in GDTF-Namen die Ebenen


def _number(value: Any, default: float, low: float, high: float, field: str) -> float:
    if value in (None, ""):
        return default
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise EditorError("bad_number", f"{field}: not a number", field=field)
    if not low <= number <= high:
        raise EditorError("bad_number", f"{field}: Wert ausserhalb von {low} bis {high}", field=field)
    return number


def _b64(data: Any, limit: int, field: str) -> bytes:
    try:
        raw = base64.b64decode(str(data or ""), validate=False)
    except (binascii.Error, ValueError):
        raise EditorError("bad_file", "The file is damaged", field=field)
    if not raw:
        raise EditorError("bad_file", "The file is empty", field=field)
    if len(raw) > limit:
        raise EditorError("file_too_large", "The file is too large", field=field, limit_mb=round(limit / 1048576, 1))
    return raw


def png_size(data: bytes) -> Optional[Tuple[int, int]]:
    if len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    width, height = struct.unpack(">II", data[16:24])
    return (width, height) if width and height else None


def _model_kind(filename: str, data: bytes) -> str:
    name = filename.lower()
    if name.endswith(".glb") and data[:4] == b"glTF":
        return "glb"
    if name.endswith(".3ds") and data[:2] == b"MM":
        return "3ds"
    if name.endswith((".stl", ".obj")):
        return "tri"                                  # wird zu GLB umgewandelt
    raise EditorError("bad_model", "The 3D model must be a .glb, .3ds, .stl or .obj file", field="model")


def to_glb(filename: str, data: bytes) -> bytes:
    """STL / OBJ -> GLB (ein Netz, flache Normalen). Quellen sind meist Z-oben (CAD); GLB ist Y-oben und das Programm dreht beim Lesen zurueck, darum hier (x, y, z) -> (x, z, -y)."""
    import numpy as np
    from app import sim_models
    try:
        tri = np.asarray(sim_models.read_any(filename, data), dtype=np.float32).reshape(-1, 3, 3)
    except Exception:
        raise EditorError("bad_model", "The 3D model could not be read", field="model")
    if len(tri) > MAX_MODEL_TRIANGLES:
        raise EditorError("model_too_detailed", "Das 3D-Modell hat zu viele Dreiecke", field="model", n=int(len(tri)), limit=MAX_MODEL_TRIANGLES)
    pos = np.stack([tri[..., 0], tri[..., 2], -tri[..., 1]], axis=-1)
    normal = np.cross(pos[:, 1] - pos[:, 0], pos[:, 2] - pos[:, 0])
    length = np.linalg.norm(normal, axis=1, keepdims=True)
    normal = np.where(length > 1e-12, normal / np.maximum(length, 1e-12), np.array([0, 1, 0], dtype=np.float32))
    normals = np.repeat(normal[:, None, :], 3, axis=1).astype(np.float32)
    pos_b, nor_b = pos.astype(np.float32).tobytes(), normals.tobytes()
    count = len(tri) * 3
    doc = {"asset": {"version": "2.0", "generator": "OpenCue"}, "scene": 0, "scenes": [{"nodes": [0]}], "nodes": [{"mesh": 0}],
           "meshes": [{"primitives": [{"attributes": {"POSITION": 0, "NORMAL": 1}, "mode": 4}]}],
           "buffers": [{"byteLength": len(pos_b) + len(nor_b)}],
           "bufferViews": [{"buffer": 0, "byteOffset": 0, "byteLength": len(pos_b), "target": 34962}, {"buffer": 0, "byteOffset": len(pos_b), "byteLength": len(nor_b), "target": 34962}],
           "accessors": [{"bufferView": 0, "componentType": 5126, "count": count, "type": "VEC3", "min": pos.reshape(-1, 3).min(axis=0).tolist(), "max": pos.reshape(-1, 3).max(axis=0).tolist()},
                         {"bufferView": 1, "componentType": 5126, "count": count, "type": "VEC3"}]}
    js = json.dumps(doc, separators=(",", ":")).encode("utf-8")
    js += b" " * (-len(js) % 4)
    bin_chunk = pos_b + nor_b
    total = 12 + 8 + len(js) + 8 + len(bin_chunk)
    return b"glTF" + struct.pack("<II", 2, total) + struct.pack("<I", len(js)) + b"JSON" + js + struct.pack("<I", len(bin_chunk)) + b"BIN\x00" + bin_chunk


def clean(spec: Any) -> Dict[str, Any]:
    """Prueft und normalisiert die Beschreibung; wirft EditorError mit Code + Werten (die Oberflaeche uebersetzt die Meldung)."""
    if not isinstance(spec, dict):
        raise EditorError("invalid", "Ungueltige Beschreibung")
    category = str(spec.get("category") or "")
    if category and category not in CATEGORIES:
        category = ""
    tags: List[str] = []
    for raw in (spec.get("tags") or [])[:MAX_TAGS * 2] if isinstance(spec.get("tags"), list) else []:
        tag = _text(raw, 30, "tags")
        if tag and tag.lower() not in {t.lower() for t in tags}:
            tags.append(tag)
    if len(tags) > MAX_TAGS:
        raise EditorError("too_many", f"Hoechstens {MAX_TAGS} Stichwoerter", field="tags", limit=MAX_TAGS)
    out: Dict[str, Any] = {
        "manufacturer": _text(spec.get("manufacturer"), 60, "manufacturer", True),
        "name": _text(spec.get("name"), 60, "name", True),
        "short_name": _text(spec.get("short_name"), 8, "short_name"),
        "description": _text(spec.get("description"), 300, "description"),
        "category": category,
        "tags": tags,
        "weight": _number(spec.get("weight"), 0.0, 0.0, 2000.0, "weight"),
        "thumbnail": spec.get("thumbnail") if isinstance(spec.get("thumbnail"), dict) else None,
        "model": spec.get("model") if isinstance(spec.get("model"), dict) else None,
        "modes": [],
    }
    model = out["model"]
    if model is not None:
        out["model"] = {"length": _number(model.get("length"), 0.25, 0.01, 50.0, "model"), "width": _number(model.get("width"), 0.25, 0.01, 50.0, "model"),
                        "height": _number(model.get("height"), 0.3, 0.01, 50.0, "model")}
        for key in ("keep", "filename", "data", "file"):
            if key in model:
                out["model"][key] = model[key]
    modes = spec.get("modes")
    if not isinstance(modes, list) or not modes:
        raise EditorError("no_modes", "At least one mode is required", field="modes")
    if len(modes) > MAX_MODES:
        raise EditorError("too_many", f"Hoechstens {MAX_MODES} Modi", field="modes", limit=MAX_MODES)
    seen_modes = set()
    for m_index, mode in enumerate(modes):
        mode = mode if isinstance(mode, dict) else {}
        m_name = _label(mode.get("name"), "mode") or f"Mode {m_index + 1}"
        if m_name.lower() in seen_modes:
            raise EditorError("duplicate_mode", f"The mode name \"{m_name}\" is used twice", field="mode", mode=m_index, name=m_name)
        seen_modes.add(m_name.lower())
        channels = mode.get("channels")
        if not isinstance(channels, list) or not channels:
            raise EditorError("no_channels", f"Mode \"{m_name}\" has no channels", field="channels", mode=m_index, name=m_name)
        if len(channels) > MAX_CHANNELS:
            raise EditorError("too_many", f"Mode \"{m_name}\": at most {MAX_CHANNELS} channels", field="channels", mode=m_index, limit=MAX_CHANNELS)
        used: Dict[str, int] = {}
        footprint = 0
        rows: List[Dict[str, Any]] = []
        for c_index, ch in enumerate(channels):
            ch = ch if isinstance(ch, dict) else {}
            n = c_index + 1
            attr = _text(ch.get("attribute"), 40, "attribute", True)
            if not _ATTR_RE.match(attr):
                raise EditorError("bad_attribute", f"Channel {n}: the attribute name \"{attr}\" is not allowed", field="attribute", mode=m_index, channel=c_index, n=n, attr=attr)
            if attr.lower() in used:
                raise EditorError("duplicate", f"Channel {n}: the attribute \"{attr}\" already exists in this mode", field="attribute", mode=m_index, channel=c_index, n=n, attr=attr, other=used[attr.lower()] + 1)
            used[attr.lower()] = c_index
            bits = 16 if str(ch.get("bits", 8)) == "16" else 8
            try:
                default = int(ch.get("default", 0) or 0)
            except (TypeError, ValueError):
                default = -1
            if not 0 <= default <= 255:
                raise EditorError("bad_default", f"Channel {n}: the default value must be between 0 and 255", field="default", mode=m_index, channel=c_index, n=n)
            ranges: List[Dict[str, Any]] = []
            raw_ranges = ch.get("ranges") or []
            if not isinstance(raw_ranges, list) or len(raw_ranges) > MAX_RANGES:
                raise EditorError("too_many", f"Channel {n}: at most {MAX_RANGES} ranges", field="ranges", mode=m_index, channel=c_index, n=n, limit=MAX_RANGES)
            for r in raw_ranges:
                r = r if isinstance(r, dict) else {}
                try:
                    start = int(r.get("from"))
                except (TypeError, ValueError):
                    start = -1
                if not 0 <= start <= 255:
                    raise EditorError("bad_range", f"Channel {n}: every range needs a start from 0 to 255", field="ranges", mode=m_index, channel=c_index, n=n)
                ranges.append({"from": start, "name": _label(r.get("name"), "range")})
            ranges.sort(key=lambda r: r["from"])
            if ranges and ranges[0]["from"] != 0:
                raise EditorError("bad_range", f"Channel {n}: the first range must start at 0", field="ranges", mode=m_index, channel=c_index, n=n)
            if len({r["from"] for r in ranges}) != len(ranges):
                raise EditorError("bad_range", f"Channel {n}: two ranges start at the same value", field="ranges", mode=m_index, channel=c_index, n=n)
            row = {"attribute": attr, "label": _label(ch.get("label"), "label"), "bits": bits, "default": default, "ranges": ranges}
            if attr in _PHYSICAL:
                lo, hi = _PHYSICAL[attr]
                row["physical_from"] = _number(ch.get("physical_from"), lo, -100000.0, 100000.0, "physical")
                row["physical_to"] = _number(ch.get("physical_to"), hi, -100000.0, 100000.0, "physical")
            rows.append(row)
            footprint += bits // 8
        if footprint > MAX_FOOTPRINT:
            raise EditorError("too_many_channels", f"Mode \"{m_name}\" uses {footprint} DMX channels", field="channels", mode=m_index, n=footprint, limit=MAX_FOOTPRINT)
        out["modes"].append({"name": m_name, "channels": rows})
    return out


def _attr_info(name: str) -> Dict[str, Any]:
    return _BY_NAME.get(name) or {"name": name, "pretty": name, "feature": "Control.Control", "group": "control", "unit": "None", "light": False}


def _dmx(value: int, bits: int) -> str:
    return f"{value * (257 if bits == 16 else 1)}/{2 if bits == 16 else 1}"


def _zip_member(path: Optional[Path], names: Tuple[str, ...]) -> Optional[Tuple[str, bytes]]:
    if path is None:
        return None
    try:
        with zipfile.ZipFile(path) as archive:
            for name in names:
                if name in archive.namelist():
                    return name, archive.read(name)
    except (OSError, zipfile.BadZipFile):
        return None
    return None


def build_gdtf(spec: Any, previous: Optional[Path] = None, copy_source: Optional[Path] = None) -> bytes:
    """Baut aus der (geprueften) Beschreibung die ZIP-Datei: description.xml, Profilbild, 3D-Modell und die Beschreibung selbst.
    previous = die bisherige Datei desselben Typs (fuer {"keep": true} bei Bild / Modell), copy_source = Datei, aus der ein Bild uebernommen wird ({"copy_from": ...})."""
    spec = clean(spec)
    all_attrs: Dict[str, Dict[str, Any]] = {}
    for mode in spec["modes"]:
        for ch in mode["channels"]:
            all_attrs.setdefault(ch["attribute"], _attr_info(ch["attribute"]))
    moving = any(a in all_attrs for a in ("Pan", "Tilt"))
    has_beam = moving or any(info["light"] for info in all_attrs.values())
    short = spec["short_name"] or re.sub(r"\s+", "", spec["name"])[:8]
    stamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    files: Dict[str, bytes] = {}

    # --- Profilbild (thumbnail.png), wie bei GDTF Share
    thumb: Optional[bytes] = None
    t_spec = spec["thumbnail"]
    if t_spec:
        if t_spec.get("data"):
            thumb = _b64(t_spec["data"], MAX_IMAGE_BYTES, "thumbnail")
            if png_size(thumb) is None:
                raise EditorError("bad_image", "The image must be a PNG", field="thumbnail")
        elif t_spec.get("keep"):
            found = _zip_member(previous, ("thumbnail.png",))
            thumb = found[1] if found else None
        elif t_spec.get("copy_from_file"):
            found = _zip_member(copy_source, ("thumbnail.png",))
            thumb = found[1] if found else None
    thumb_size = png_size(thumb) if thumb else None
    if thumb:
        files["thumbnail.png"] = thumb

    # --- 3D-Modell (nur fuer feststehende Geraete; bewegliche Koepfe nutzen Sockel / Buegel / Kopf)
    model_file = ""
    m_spec = spec["model"] if not moving else None
    model_dims = (0.25, 0.25, 0.3)
    model_note: Optional[Dict[str, Any]] = None
    if m_spec:
        model_dims = (m_spec["length"], m_spec["width"], m_spec["height"])
        if m_spec.get("data"):
            filename = _text(m_spec.get("filename"), 80, "model", True)
            data = _b64(m_spec["data"], MAX_MODEL_BYTES, "model")
            kind = _model_kind(filename, data)
            if kind == "tri":
                data, kind = to_glb(filename, data), "glb"
            stem = re.sub(r"[^A-Za-z0-9_\-]+", "_", Path(filename).stem).strip("_")[:40] or "model"
            folder, ext = ("models/gltf", ".glb") if kind == "glb" else ("models/3ds", ".3ds")
            files[f"{folder}/{stem}{ext}"] = data
            model_file = stem
            model_note = {"file": stem + ext}
        elif m_spec.get("keep") and previous is not None:
            for folder, ext in (("models/gltf", ".glb"), ("models/3ds", ".3ds")):
                try:
                    with zipfile.ZipFile(previous) as archive:
                        for name in archive.namelist():
                            if name.lower().startswith(folder + "/") and name.lower().endswith(ext):
                                files[name] = archive.read(name)
                                model_file = Path(name).stem
                                model_note = {"file": Path(name).name}
                except (OSError, zipfile.BadZipFile):
                    pass
        if not model_file:
            m_spec = None

    root = ET.Element("GDTF", {"DataVersion": "1.2"})
    ft = ET.SubElement(root, "FixtureType", {
        "CanHaveChildren": "No", "Description": spec["description"], "FixtureTypeID": str(uuid.uuid4()).upper(), "LongName": spec["name"], "Manufacturer": spec["manufacturer"],
        "Name": spec["name"], "RefFT": "", "ShortName": short, "Thumbnail": "thumbnail" if thumb else "",
        "ThumbnailOffsetX": str(thumb_size[0] // 2) if thumb_size else "0", "ThumbnailOffsetY": str(thumb_size[1] // 2) if thumb_size else "0"})
    defs = ET.SubElement(ft, "AttributeDefinitions")
    ET.SubElement(defs, "ActivationGroups")
    groups: Dict[str, List[str]] = {}
    for info in all_attrs.values():
        group, _, feature = info["feature"].partition(".")
        groups.setdefault(group, [])
        if feature not in groups[group]:
            groups[group].append(feature)
    fgs = ET.SubElement(defs, "FeatureGroups")
    for group, features in groups.items():
        fg = ET.SubElement(fgs, "FeatureGroup", {"Name": group, "Pretty": group})
        for feature in features:
            ET.SubElement(fg, "Feature", {"Name": feature})
    attrs = ET.SubElement(defs, "Attributes")
    for name, info in all_attrs.items():
        ET.SubElement(attrs, "Attribute", {"Feature": info["feature"], "Name": name, "PhysicalUnit": info["unit"], "Pretty": info["pretty"]})
    ET.SubElement(ft, "Wheels")
    phys = ET.SubElement(ft, "PhysicalDescriptions")
    ET.SubElement(phys, "ColorSpace", {"Mode": "sRGB", "Name": ""})
    for tag in ("AdditionalColorSpaces", "Gamuts", "Filters", "Emitters", "DMXProfiles", "CRIs", "Connectors"):
        ET.SubElement(phys, tag)
    props = ET.SubElement(phys, "Properties")
    ET.SubElement(props, "OperatingTemperature", {"High": "40.000000", "Low": "0.000000"})
    ET.SubElement(props, "Weight", {"Value": f"{spec['weight']:.6f}"})
    ET.SubElement(props, "LegHeight", {"Value": "0.000000"})

    off = {"SVGFrontOffsetX": "0.000000", "SVGFrontOffsetY": "0.000000", "SVGOffsetX": "0.000000", "SVGOffsetY": "0.000000", "SVGSideOffsetX": "0.000000", "SVGSideOffsetY": "0.000000"}

    def model(name: str, kind: str, length: float, width: float, height: float, file: str = "") -> Dict[str, str]:
        return {"File": file, "Height": f"{height:.6f}", "Length": f"{length:.6f}", "Name": name, "PrimitiveType": kind, **off, "Width": f"{width:.6f}"}

    models = ET.SubElement(ft, "Models")
    geos = ET.SubElement(ft, "Geometries")
    beam_attrs = {"BeamAngle": "25.000000", "BeamRadius": "0.035000", "BeamType": "Wash", "ColorRenderingIndex": "100", "ColorTemperature": "6000.000000", "FieldAngle": "25.000000", "LampType": "LED",
                  "LuminousFlux": "1000.000000", "Model": "Beam", "Name": "Beam", "PowerConsumption": "100.000000", "RectangleRatio": "1.777700", "ThrowRatio": "1.000000"}
    if moving:                                                  # Sockel -> Buegel (Pan) -> Kopf (Tilt) -> Strahl, wie bei echten Moving-Head-Dateien (z. B. Eurolite TMH-S400)
        ET.SubElement(models, "Model", model("Base", "Base1_1", 0.31, 0.31, 0.12))
        ET.SubElement(models, "Model", model("Yoke", "Yoke", 0.38, 0.12, 0.32))
        ET.SubElement(models, "Model", model("Head", "Head", 0.25, 0.22, 0.45))
        ET.SubElement(models, "Model", model("Beam", "Cylinder", 0.07, 0.07, 0.02))
        base = ET.SubElement(geos, "Geometry", {"Model": "Base", "Name": "Base", "Position": _IDENT % "0.000000"})
        yoke = ET.SubElement(base, "Axis", {"Model": "Yoke", "Name": "Yoke", "Position": _IDENT % "-0.280000"})
        head = ET.SubElement(yoke, "Axis", {"Model": "Head", "Name": "Head", "Position": _IDENT % "-0.140000"})
        ET.SubElement(head, "Beam", {**beam_attrs, "Position": _IDENT % "-0.206904"})
        top = "Base"
    else:
        ET.SubElement(models, "Model", model("Body", "Conventional1_1", model_dims[0], model_dims[1], model_dims[2], model_file))
        body = ET.SubElement(geos, "Geometry", {"Model": "Body", "Name": "Body", "Position": _IDENT % "0.000000"})
        if has_beam:
            ET.SubElement(models, "Model", model("Beam", "Cylinder", 0.2, 0.2, 0.02))
            ET.SubElement(body, "Beam", {**beam_attrs, "BeamRadius": "0.100000", "LampType": "Discharge", "Model": "Beam", "Position": _IDENT % "-0.280000"})
        top = "Body"

    def geometry_for(attr: str, info: Dict[str, Any]) -> str:
        if moving:
            return "Base" if attr in ("Pan", "Tilt") else ("Head" if info["light"] else "Base")
        return "Beam" if (has_beam and info["light"]) else top

    dmx_modes = ET.SubElement(ft, "DMXModes")
    for mode in spec["modes"]:
        dm = ET.SubElement(dmx_modes, "DMXMode", {"Description": "", "Geometry": top, "Name": mode["name"]})
        chs = ET.SubElement(dm, "DMXChannels")
        offset = 1
        for ch in mode["channels"]:
            info = _attr_info(ch["attribute"])
            geometry = geometry_for(ch["attribute"], info)
            func_name = ch["label"] or (ch["attribute"] + " 1")
            bits = ch["bits"]
            offsets = ",".join(str(offset + i) for i in range(bits // 8))
            offset += bits // 8
            dc = ET.SubElement(chs, "DMXChannel", {"DMXBreak": "1", "Geometry": geometry, "Highlight": "None", "Offset": offsets,
                                                    "InitialFunction": f"{geometry}_{ch['attribute']}.{ch['attribute']}.{func_name}"})
            lc = ET.SubElement(dc, "LogicalChannel", {"Attribute": ch["attribute"], "DMXChangeTimeLimit": "0.000000", "Master": "None", "MibFade": "0.000000", "Snap": "No"})
            p_from, p_to = ch.get("physical_from", 0.0), ch.get("physical_to", 1.0)
            cf = ET.SubElement(lc, "ChannelFunction", {"Attribute": ch["attribute"], "CustomName": "", "DMXFrom": "0/1", "Default": _dmx(ch["default"], bits), "Max": f"{p_to:.6f}", "Min": f"{p_from:.6f}",
                                                         "Name": func_name, "OriginalAttribute": "", "PhysicalFrom": f"{p_from:.6f}", "PhysicalTo": f"{p_to:.6f}", "RealAcceleration": "0.000000", "RealFade": "0.000000"})
            for r in ch["ranges"]:
                ET.SubElement(cf, "ChannelSet", {"DMXFrom": _dmx(r["from"], bits), "Name": r["name"], "PhysicalFrom": f"{p_from:.6f}", "PhysicalTo": f"{p_to:.6f}", "WheelSlotIndex": "0"})
        ET.SubElement(dm, "Relations")
        ET.SubElement(dm, "FTMacros")
    revs = ET.SubElement(ft, "Revisions")
    ET.SubElement(revs, "Revision", {"Date": stamp, "ModifiedBy": "OpenCue Fixture Editor", "Text": "Eigen", "UserID": "0"})
    ET.SubElement(ft, "FTPresets")
    ET.SubElement(ft, "Protocols")
    ET.indent(root, space="  ")
    xml = b'<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n' + ET.tostring(root, encoding="utf-8")
    stored = dict(spec)
    stored["thumbnail"] = bool(thumb)
    stored["model"] = ({**model_note, "length": model_dims[0], "width": model_dims[1], "height": model_dims[2]} if (m_spec and model_note) else None)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("description.xml", xml)
        for name, data in files.items():
            archive.writestr(name, data)
        archive.writestr(MARKER, json.dumps(stored, ensure_ascii=False, indent=1))
    return buffer.getvalue()


def read_spec(path: Any) -> Optional[Dict[str, Any]]:
    """Die Beschreibung aus einer vom Editor gebauten Datei (None bei jeder anderen Datei). thumbnail = ob die Datei ein Bild hat, model = {file, length, width, height} oder None."""
    try:
        with zipfile.ZipFile(path) as archive:
            if MARKER not in archive.namelist():
                return None
            data = json.loads(archive.read(MARKER).decode("utf-8"))
        had_thumb = bool(data.get("thumbnail"))
        model = data.get("model") if isinstance(data.get("model"), dict) else None
        spec = clean({**data, "thumbnail": None, "model": None})
        spec["thumbnail"] = had_thumb
        spec["model"] = ({"file": str(model.get("file") or ""), "length": float(model.get("length", 0.25)), "width": float(model.get("width", 0.25)), "height": float(model.get("height", 0.3))}
                         if model and model.get("file") else None)
        return spec
    except (OSError, ValueError, zipfile.BadZipFile, EditorError):
        return None


def own_info(path: Any) -> Optional[Dict[str, Any]]:
    """Fuer die Liste der installierten Typen: None bei fremden Dateien, sonst Kategorie und Stichwoerter aus der Beschreibung."""
    try:
        with zipfile.ZipFile(path) as archive:
            if MARKER not in archive.namelist():
                return None
            data = json.loads(archive.read(MARKER).decode("utf-8"))
    except (OSError, ValueError, zipfile.BadZipFile):
        return {"category": "", "tags": []}
    category = str(data.get("category") or "")
    tags = [str(t)[:30] for t in (data.get("tags") or []) if isinstance(t, str)][:MAX_TAGS]
    return {"category": category if category in CATEGORIES else "", "tags": tags}


def is_own(path: Any) -> bool:
    return own_info(path) is not None


# --------------------------------------------------------------------------------------------- Kopie eines vorhandenen Typs
def _coarse_default(text: str) -> int:
    try:
        value, _, count = str(text or "0/1").partition("/")
        n = max(1, int(count or 1))
        return max(0, min(255, int(float(value)) >> (8 * (n - 1))))
    except ValueError:
        return 0


def _safe_attr(name: str, taken: set) -> str:
    out = re.sub(r"[^A-Za-z0-9_ \-]+", "_", str(name or "").strip()) or "Attr"
    if not out[0].isalpha():
        out = "A" + out
    out = out[:36].rstrip()
    candidate, n = out, 2
    while candidate.lower() in taken:
        candidate, n = f"{out} {n}", n + 1
    return candidate


def derive_spec(path: Path) -> Dict[str, Any]:
    """Beschreibung aus einer beliebigen GDTF-Datei (Kopie zum Bearbeiten). Uebernommen werden Stammdaten, Modi, Kanaele, Funktionsnamen, Bereiche und das Profilbild; NICHT uebernommen werden Raeder (Gobos,
    Farbraeder), die Geometrie und die 3D-Modelle (der Editor baut sie neu) - "notes" nennt, was weggefallen ist."""
    from app import fixture_library
    with zipfile.ZipFile(path) as archive:
        root = ET.fromstring(archive.read("description.xml"))
    ft = root.find("FixtureType")
    if ft is None:
        raise EditorError("invalid", "Not a GDTF file")
    notes: Dict[str, int] = {}
    wheels = len(ft.findall("Wheels/Wheel"))
    if wheels:
        notes["wheels"] = wheels
    modes: List[Dict[str, Any]] = []
    for dm in ft.iterfind("DMXModes/DMXMode"):
        channels: List[Dict[str, Any]] = []
        taken: set = set()
        for dc in dm.iterfind("DMXChannels/DMXChannel"):
            offs = [o for o in str(dc.get("Offset") or "").replace(" ", "").split(",") if o.isdigit()]
            logicals = dc.findall("LogicalChannel")
            if not offs or not logicals:
                continue
            if len(logicals) > 1:
                notes["logicals"] = notes.get("logicals", 0) + len(logicals) - 1
            lc = logicals[0]
            funcs = lc.findall("ChannelFunction")
            attr = _safe_attr(lc.get("Attribute") or "", taken)
            taken.add(attr.lower())
            label, default, ranges = "", 0, []
            row: Dict[str, Any] = {}
            if funcs:
                cf = funcs[0]
                name = str(cf.get("Name") or "")
                label = "" if re.fullmatch(re.escape(str(lc.get("Attribute") or "")) + r" \d+", name) else name[:40].replace(".", " ")
                default = _coarse_default(cf.get("Default") or "0/1")
                for cs in cf.findall("ChannelSet"):
                    if str(cs.get("Name") or "").strip():
                        ranges.append({"from": _coarse_default(cs.get("DMXFrom") or "0/1"), "name": str(cs.get("Name")).strip()[:40].replace(".", " ")})
                if ranges and min(r["from"] for r in ranges) != 0:
                    ranges.insert(0, {"from": 0, "name": ""})
                seen = set()
                ranges = [r for r in sorted(ranges, key=lambda r: r["from"]) if not (r["from"] in seen or seen.add(r["from"]))][:MAX_RANGES]
                if attr in _PHYSICAL:
                    try:
                        row["physical_from"], row["physical_to"] = float(cf.get("PhysicalFrom")), float(cf.get("PhysicalTo"))
                    except (TypeError, ValueError):
                        pass
            channels.append({"attribute": attr, "label": label, "bits": 16 if len(offs) > 1 else 8, "default": default, "ranges": ranges, **row})
        if channels:
            modes.append({"name": str(dm.get("Name") or "Mode")[:40].replace(".", " "), "channels": channels[:MAX_CHANNELS]})
    if not modes:
        raise EditorError("invalid", "The file contains no DMX mode")
    seen_names: set = set()
    for m in modes:
        base, n = m["name"], 2
        while m["name"].lower() in seen_names:
            m["name"], n = f"{base} {n}", n + 1
        seen_names.add(m["name"].lower())
    main = max(modes, key=lambda m: len(m["channels"]))
    category = fixture_library.category_from_channels([c["attribute"] for c in main["channels"]], f"{ft.get('Name', '')} {ft.get('Manufacturer', '')}")
    geos = len(list(ft.iter("Geometry"))) + len(list(ft.iter("Axis")))
    if geos > 2:
        notes["geometry"] = geos
    props = ft.find("PhysicalDescriptions/Properties/Weight")
    try:
        weight = float(props.get("Value")) if props is not None else 0.0
    except (TypeError, ValueError):
        weight = 0.0
    thumb = _zip_member(path, ("thumbnail.png",))
    spec = clean({"manufacturer": ft.get("Manufacturer") or path.stem.split("@")[0], "name": (ft.get("Name") or path.stem)[:52] + " (2)", "short_name": ft.get("ShortName") or "",
                  "description": ft.get("Description") or "", "category": category if category in CATEGORIES else "", "tags": [], "weight": weight, "modes": modes})
    spec["thumbnail"] = {"copy_from": path.stem} if thumb else None
    spec["model"] = None
    spec["notes"] = notes
    return spec
