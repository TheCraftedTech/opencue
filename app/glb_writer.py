# Copyright (C) 2026 Samuel Zenker
# SPDX-License-Identifier: GPL-3.0-or-later
"""
glb_writer.py
Schreibt ein Dreiecksnetz als glTF 2.0 Binary (.glb) - ohne zusaetzliche Bibliothek (nur numpy). Gebraucht vom MVR-Export (app/mvr_export.py): MVR nimmt 3D-Dateien als 3ds oder glTF.

Eingabe: Dreiecke (n, 3, 3) in METERN, Z oben (so rechnet OpenCue); optional eine Farbe je Dreieck (n, 3) uint8. Ausgabe: .glb im Stil der Spezifikation - Y oben, Meter, ein Netz, ein Material
(PBR: Grundfarbe, Metall, Rauheit), Normalen je Dreieck, Farben je Ecke, wenn Dreiecksfarben da sind. Die Drehung Z oben -> Y oben ist (x, y, z) -> (x, z, -y): die Umkehr dessen, was
der MVR-Import beim Lesen tut (app/mvr_import.py load_mesh), damit ein Rundlauf dieselben Masse ergibt.
"""
from __future__ import annotations

import json
import struct
from typing import Any, Optional

import numpy as np

JSON_CHUNK = 0x4E4F534A
BIN_CHUNK = 0x004E4942


def _pad(data: bytes, fill: bytes) -> bytes:
    return data + fill * ((4 - len(data) % 4) % 4)


def write_glb(triangles: np.ndarray, colors: Optional[np.ndarray] = None, base_color: Any = (0.62, 0.62, 0.64), metallic: float = 0.0, roughness: float = 0.9, name: str = "mesh") -> bytes:
    tris = np.asarray(triangles, dtype=np.float32).reshape(-1, 3, 3)
    if len(tris) == 0:
        raise ValueError("no triangles")
    flat = tris.reshape(-1, 3)
    yup = np.stack([flat[:, 0], flat[:, 2], -flat[:, 1]], axis=1).astype(np.float32)            # Z oben -> Y oben
    t3 = yup.reshape(-1, 3, 3)
    normal = np.cross(t3[:, 1] - t3[:, 0], t3[:, 2] - t3[:, 0])
    length = np.linalg.norm(normal, axis=1, keepdims=True)
    normal = np.where(length > 1e-12, normal / np.maximum(length, 1e-12), np.array([0.0, 1.0, 0.0]))
    normals = np.repeat(normal.astype(np.float32), 3, axis=0)
    blobs = [yup.tobytes(), normals.tobytes()]
    views = [{"buffer": 0, "byteOffset": 0, "byteLength": len(blobs[0]), "target": 34962}, {"buffer": 0, "byteOffset": len(blobs[0]), "byteLength": len(blobs[1]), "target": 34962}]
    accessors = [
        {"bufferView": 0, "componentType": 5126, "count": int(len(yup)), "type": "VEC3", "min": [float(v) for v in yup.min(axis=0)], "max": [float(v) for v in yup.max(axis=0)]},
        {"bufferView": 1, "componentType": 5126, "count": int(len(normals)), "type": "VEC3"},
    ]
    attributes = {"POSITION": 0, "NORMAL": 1}
    if colors is not None and len(colors) == len(tris):
        per_vertex = np.repeat(np.asarray(colors, dtype=np.float32) / 255.0, 3, axis=0).astype(np.float32)
        offset = sum(len(b) for b in blobs)
        blobs.append(per_vertex.tobytes())
        views.append({"buffer": 0, "byteOffset": offset, "byteLength": len(blobs[-1]), "target": 34962})
        accessors.append({"bufferView": len(views) - 1, "componentType": 5126, "count": int(len(per_vertex)), "type": "VEC3"})
        attributes["COLOR_0"] = len(accessors) - 1
    binary = b"".join(blobs)
    color = [float(c) for c in base_color][:3]
    document = {
        "asset": {"version": "2.0", "generator": "OpenCue"},
        "scene": 0, "scenes": [{"nodes": [0]}], "nodes": [{"mesh": 0, "name": str(name)[:60]}],
        "meshes": [{"name": str(name)[:60], "primitives": [{"attributes": attributes, "material": 0, "mode": 4}]}],
        "materials": [{"name": "material", "doubleSided": True, "pbrMetallicRoughness": {"baseColorFactor": [color[0], color[1], color[2], 1.0], "metallicFactor": float(metallic), "roughnessFactor": float(roughness)}}],
        "accessors": accessors, "bufferViews": views, "buffers": [{"byteLength": len(binary)}],
    }
    json_chunk = _pad(json.dumps(document, separators=(",", ":")).encode("utf-8"), b" ")
    bin_chunk = _pad(binary, b"\x00")
    total = 12 + 8 + len(json_chunk) + 8 + len(bin_chunk)
    return b"glTF" + struct.pack("<II", 2, total) + struct.pack("<II", len(json_chunk), JSON_CHUNK) + json_chunk + struct.pack("<II", len(bin_chunk), BIN_CHUNK) + bin_chunk
