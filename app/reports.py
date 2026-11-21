# Copyright (C) 2026 Samuel Zenker
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Dokumentation zum Drucken / als PDF (Datei-Menue -> Drucken / PDF ...): was Techniker auf Papier brauchen. Alles aus der geladenen Show, ohne Fremdbibliothek (app/pdf_lite.py).

  patch       Patch-Liste: Nummer (FID), Name, Typ, Modus, Universum, DMX-Adresse von / bis, Kanaele
  universes   DMX-Belegung: je Universum ein Streifen mit den 512 Kanaelen, wer welchen Bereich belegt, Ueberschneidungen rot
  groups      Gruppen: welcher Scheinwerfer in welcher Gruppe ist
  plan        Plan (Draufsicht): Scheinwerfer an ihren Plaetzen - aus der 3D-Buehne (Meter), sonst aus der Layout-Ansicht der Scheinwerfersteuerung (Raster)
  cues        Cue-Listen: Nummer, Name, Ausloeser, Zeiten

  GET /api/report/info                                    {fixtures, groups, cuelists, stage_positions, layout_positions}
  GET /api/report/pdf?parts=patch,universes,...&paper=a4|letter&inline=0|1   das PDF
"""
from __future__ import annotations

import math
import re
import time
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response

from app import fixture_library, languages, sim_stages, timeofday
from app.pdf_lite import Pdf, fit, text_width, wrap, wrap_limited
from app.state_manager import state

router = APIRouter()

PARTS = ("patch", "universes", "groups", "plan", "cues")
MAX_CELL_LINES = 4                                       # Tabellenzelle: hoechstens so viele Zeilen (sehr lange Namen werden danach mit ... gekuerzt)
PAPERS = {"a4": (595.28, 841.89), "letter": (612.0, 792.0)}
PALETTE: List[Tuple[float, float, float]] = [(0.35, 0.55, 0.85), (0.90, 0.55, 0.25), (0.35, 0.70, 0.45), (0.75, 0.40, 0.70), (0.85, 0.75, 0.25),
                                             (0.30, 0.70, 0.75), (0.80, 0.40, 0.40), (0.55, 0.55, 0.60)]
INK = (0.10, 0.10, 0.12)
GRAY = (0.45, 0.45, 0.50)
LIGHT = (0.93, 0.93, 0.95)
RED = (0.85, 0.15, 0.15)

_TEXT_KEYS = ("title", "created", "fixtures", "groups", "cuelists", "page", "patch", "universes", "groups_h", "plan", "cues", "fid", "name", "type", "mode", "univ", "from", "to", "chan", "none_fx",
              "none_groups", "none_cues", "empty", "used", "universe", "universes_help", "overlap", "free", "no_pos", "plan_stage", "plan_layout", "plan_none", "cue", "trigger", "fade", "delay", "go",
              "follow", "timecode", "audio", "midi", "clock")


def _texts(language: str) -> Dict[str, str]:
    """Texte des PDFs aus den Sprachdateien (Schluessel PDF_<NAME>, app/languages.py)."""
    return {key: languages.tr("PDF_" + key.upper(), language) for key in _TEXT_KEYS}


def _fixtures_sorted() -> List[Any]:
    return sorted(state.fixtures.values(), key=lambda f: (f.fid or 0, f.universe, f.start_channel, f.name.lower()))


def _type_names() -> Dict[str, str]:
    usage: Dict[str, int] = {}
    for fx in state.fixtures.values():
        usage[fx.fixture_type] = usage.get(fx.fixture_type, 0) + 1
    names: Dict[str, str] = {}
    try:
        for row in fixture_library.show_types(usage):
            maker, nm = str(row.get("manufacturer") or "").strip(), str(row["name"])
            names[row["id"]] = nm if not maker or nm.lower().startswith(maker.lower()) else f"{maker} {nm}"
    except Exception:                                                              # noqa: BLE001 - ein defekter Typ darf die Dokumentation nicht verhindern
        pass
    return names


def _positions() -> Tuple[Dict[str, Tuple[float, float]], str]:
    """(Scheinwerfer-Id -> (x, y), Quelle 'stage' | 'layout' | '')."""
    sim_stages.store.ensure()
    stage = {fid: (float(item["position"][0]), float(item["position"][1])) for fid, item in sim_stages.store.layout.items() if fid in state.fixtures and item.get("position")}
    if stage:
        return stage, "stage"
    grid = {fid: (float(fx.layout_x), float(fx.layout_y)) for fid, fx in state.fixtures.items() if fx.layout_x is not None and fx.layout_y is not None}
    return (grid, "layout") if grid else ({}, "")


# ---------------------------------------------------------------------------------------------------------------- Seitenfluss
class Doc:
    def __init__(self, paper: str, lang: str) -> None:
        width, height = PAPERS.get(paper, PAPERS["a4"])
        self.t = _texts(lang)
        self.show = state.showfile_name or "Show"
        self.pdf = Pdf(width, height, 36.0, title=f"{self.t['title']} - {self.show}")
        self.left = self.pdf.margin
        self.right = width - self.pdf.margin
        self.bottom = height - self.pdf.margin - 8
        self.y = self.pdf.margin
        self.first = True

    @property
    def width(self) -> float:
        return self.right - self.left

    def ensure(self, height: float) -> None:
        if self.y + height > self.bottom:
            self.pdf.new_page()
            self.y = self.pdf.margin
            self.first = False

    def heading(self, text: str, size: float = 13.0) -> None:
        self.ensure(size + 70)                                                      # nach der Ueberschrift muss noch etwas Platz sein (keine Ueberschrift allein am Seitenende)
        self.y += size + 6
        self.pdf.text(self.left, self.y, text, size=size, bold=True, color=INK)
        self.pdf.line(self.left, self.y + 3, self.right, self.y + 3, 0.8, GRAY)
        self.y += 12

    def note(self, text: str, color: Tuple[float, float, float] = GRAY, size: float = 8.5) -> None:
        for line in wrap(text, size, self.width):
            self.ensure(size + 4)
            self.y += size + 2
            self.pdf.text(self.left, self.y, line, size=size, color=color)

    def table(self, columns: List[Tuple[str, float, str]], rows: List[List[str]], size: float = 8.5) -> None:
        """columns: (Titel, relative Breite, Ausrichtung l|r|c). Die Kopfzeile wiederholt sich auf jeder Seite."""
        total = sum(c[1] for c in columns)
        widths = [self.width * c[1] / total for c in columns]
        row_height = size + 5
        line_height = size + 1.5

        def header() -> None:
            self.pdf.rect(self.left, self.y, self.width, row_height, fill=(0.85, 0.86, 0.9))
            x = self.left
            for (title, _w, align), w in zip(columns, widths):
                self._cell(x, self.y + size + 1.5, w, [fit(title, size, w - 6, True)], size, True, align)
                x += w
            self.y += row_height

        def cells(row: List[str]) -> List[List[str]]:
            """Jede Zelle in Zeilen: Textspalten (links) brechen um (bis zu 4 Zeilen), Zahlen bleiben einzeilig."""
            return [wrap_limited(str(value), size, w - 6, MAX_CELL_LINES) if align == "l" else [fit(str(value), size, w - 6)]
                    for (_title, _w, align), w, value in zip(columns, widths, row)]

        self.ensure(row_height * 3)
        header()
        for index, row in enumerate(rows):
            lines = cells(row)
            height = max(len(c) for c in lines) * line_height + 3.5
            if self.y + height > self.bottom:
                self.pdf.new_page()
                self.y = self.pdf.margin
                header()
            if index % 2:
                self.pdf.rect(self.left, self.y, self.width, height, fill=LIGHT)
            x = self.left
            for (_title, _w, align), w, cell in zip(columns, widths, lines):
                self._cell(x, self.y + size + 1.5, w, cell, size, False, align, line_height)
                x += w
            self.y += height
        self.y += 4

    def _cell(self, x: float, baseline: float, width: float, lines: List[str], size: float, bold: bool, align: str, line_height: float = 0.0) -> None:
        for number, shown in enumerate(lines):
            y = baseline + number * line_height
            if align == "r":
                self.pdf.text(x + width - 3, y, shown, size, bold, INK, "r")
            elif align == "c":
                self.pdf.text(x + width / 2, y, shown, size, bold, INK, "c")
            else:
                self.pdf.text(x + 3, y, shown, size, bold, INK, "l")


# ---------------------------------------------------------------------------------------------------------------- Teile
def _title(doc: Doc) -> None:
    t = doc.t
    doc.pdf.text(doc.left, doc.y + 20, f"{t['title']}", size=20, bold=True, color=INK)
    doc.pdf.text(doc.left, doc.y + 40, fit(doc.show, 13, doc.width), size=13, color=INK)
    doc.pdf.text(doc.left, doc.y + 55, f"{t['created']}: {time.strftime('%Y-%m-%d %H:%M')}   -   {len(state.fixtures)} {t['fixtures']}, {len(state.groups)} {t['groups']}, "
                 f"{len(state.cuelists)} {t['cuelists']}", size=9, color=GRAY)
    doc.y += 62


def _patch(doc: Doc, types: Dict[str, str]) -> None:
    t = doc.t
    doc.heading(t["patch"])
    fixtures = _fixtures_sorted()
    if not fixtures:
        doc.note(t["none_fx"])
        return
    rows = [[str(fx.fid or ""), fx.name, types.get(fx.fixture_type, fx.fixture_type), fx.mode if fx.mode != "default" else "", str(fx.universe), str(fx.start_channel),
             str(fx.start_channel + max(fx.channel_count, 1) - 1), str(fx.channel_count)] for fx in fixtures]
    doc.table([(t["fid"], 5, "r"), (t["name"], 20, "l"), (t["type"], 28, "l"), (t["mode"], 12, "l"), (t["univ"], 6, "r"), (t["from"], 6.5, "r"), (t["to"], 6.5, "r"), (t["chan"], 5.5, "r")], rows)


def _universes(doc: Doc) -> None:
    t = doc.t
    doc.heading(t["universes"])
    fixtures = _fixtures_sorted()
    if not fixtures:
        doc.note(t["none_fx"])
        return
    doc.note(t["universes_help"])
    by_universe: Dict[int, List[Any]] = {}
    for fx in fixtures:
        by_universe.setdefault(int(fx.universe), []).append(fx)
    strip_w = doc.width
    per = strip_w / 512.0
    for universe in sorted(by_universe):
        items = sorted(by_universe[universe], key=lambda f: (f.start_channel, f.fid or 0))
        used = [0] * 512
        for fx in items:
            for ch in range(max(fx.start_channel, 1) - 1, min(fx.start_channel - 1 + max(fx.channel_count, 1), 512)):
                used[ch] += 1
        legend_rows = (len(items) + 1) // 2
        doc.ensure(70 + min(legend_rows, 6) * 11)
        doc.y += 14
        doc.pdf.text(doc.left, doc.y, f"{t['universe']} {universe}", size=11, bold=True, color=INK)
        doc.pdf.text(doc.right, doc.y, t["used"].format(used=sum(1 for u in used if u)), size=8.5, color=GRAY, align="r")
        top = doc.y + 6
        doc.pdf.rect(doc.left, top, strip_w, 20, fill=(0.97, 0.97, 0.98), stroke=GRAY, width=0.4)
        for index, fx in enumerate(items):
            x = doc.left + (max(fx.start_channel, 1) - 1) * per
            w = min(max(fx.channel_count, 1), 512 - (max(fx.start_channel, 1) - 1)) * per
            clash = any(used[c] > 1 for c in range(max(fx.start_channel, 1) - 1, min(max(fx.start_channel, 1) - 1 + max(fx.channel_count, 1), 512)))
            doc.pdf.rect(x, top, w, 20, fill=PALETTE[index % len(PALETTE)], stroke=RED if clash else (1, 1, 1), width=1.2 if clash else 0.4)
            label = str(fx.fid or "")
            if label and text_width(label, 6.5) + 2 <= w:
                doc.pdf.text(x + w / 2, top + 13.5, label, 6.5, True, (1, 1, 1), "c")
        for tick in (1, 64, 128, 192, 256, 320, 384, 448, 512):
            x = doc.left + (tick - 1) * per
            doc.pdf.line(x, top + 20, x, top + 24, 0.4, GRAY)
            doc.pdf.text(min(max(x, doc.left + 6), doc.right - 6), top + 32, str(tick), 6.5, False, GRAY, "c")
        doc.y = top + 38
        # Legende: je Scheinwerfer Farbe, Nummer, Name und der Kanalbereich (zwei Spalten)
        column_w = doc.width / 2
        rows = (len(items) + 1) // 2                                                  # erst die linke Spalte von oben nach unten, dann die rechte
        for row in range(rows):
            texts = {}
            for col in range(2):
                index = col * rows + row
                if index < len(items):
                    texts[col] = wrap_limited(f"{items[index].fid or '?'}  {items[index].name}", 8, column_w - 90, 3)       # lange Namen: bis zu drei Zeilen statt abschneiden
            doc.ensure(11 * max((len(v) for v in texts.values()), default=1) + 1)
            doc.y += 11
            for col, lines in texts.items():
                index = col * rows + row
                fx = items[index]
                x = doc.left + col * column_w
                end = fx.start_channel + max(fx.channel_count, 1) - 1
                doc.pdf.rect(x, doc.y - 7, 8, 8, fill=PALETTE[index % len(PALETTE)])
                for number, line in enumerate(lines):
                    doc.pdf.text(x + 12, doc.y + number * 9.5, line, 8, False, INK)
                doc.pdf.text(x + column_w - 12, doc.y, f"{fx.start_channel}-{end}", 8, True, INK, "r")
            doc.y += 9.5 * (max(len(v) for v in texts.values()) - 1)
        doc.y += 4
        clashes = sorted({(a.fid, b.fid) for i, a in enumerate(items) for b in items[i + 1:]
                          if a.start_channel < b.start_channel + b.channel_count and b.start_channel < a.start_channel + a.channel_count})
        if clashes:
            doc.note(f"{t['overlap']}: " + ", ".join(f"FID {a} / FID {b}" for a, b in clashes[:12]) + (" ..." if len(clashes) > 12 else ""), color=RED)
        runs, start = [], None
        for ch in range(513):                                                       # freie Bereiche
            free = ch < 512 and not used[ch]
            if free and start is None:
                start = ch + 1
            if not free and start is not None:
                runs.append((start, ch))
                start = None
        big = [r for r in runs if r[1] - r[0] >= 15][:6]
        if big and sum(1 for u in used if u):
            doc.note(f"{t['free']}: " + ", ".join(f"{a}-{b}" for a, b in big) + (" ..." if len(runs) > len(big) else ""))
        doc.y += 6


def _groups(doc: Doc) -> None:
    t = doc.t
    doc.heading(t["groups_h"])
    if not state.groups:
        doc.note(t["none_groups"])
        return
    for name, ids in state.groups.items():
        members = [state.fixtures[i] for i in ids if i in state.fixtures]
        members.sort(key=lambda f: (f.fid or 0, f.name.lower()))
        doc.ensure(34)
        doc.y += 14
        doc.pdf.text(doc.left, doc.y, f"{name}  ({len(members)})", size=10, bold=True, color=INK)
        text = ", ".join(f"{fx.fid or '?'} {fx.name}" for fx in members) if members else t["empty"]
        for line in wrap(text, 8.5, doc.width - 10):
            doc.ensure(13)
            doc.y += 11
            doc.pdf.text(doc.left + 10, doc.y, line, 8.5, False, INK)
        doc.y += 3


def _group_colors() -> Dict[str, Tuple[float, float, float]]:
    colors: Dict[str, Tuple[float, float, float]] = {}
    for index, (_name, ids) in enumerate(state.groups.items()):
        for fid in ids:
            colors.setdefault(fid, PALETTE[index % len(PALETTE)])
    return colors


def _hex_color(text: Any, fallback: Tuple[float, float, float] = (0.62, 0.62, 0.65)) -> Tuple[float, float, float]:
    try:
        value = str(text).lstrip("#")
        return (int(value[0:2], 16) / 255.0, int(value[2:4], 16) / 255.0, int(value[4:6], 16) / 255.0)
    except (ValueError, IndexError):
        return fallback


def _inside(point: Tuple[float, float], polygon: List[Tuple[float, float]]) -> bool:
    x, y = point
    inside = False
    j = len(polygon) - 1
    for i in range(len(polygon)):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-12) + xi:
            inside = not inside
        j = i
    return inside


def _hull(points: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
    """Konvexe Huelle (Monotone Chain) - der Umriss eines Koerpers von oben."""
    pts = sorted(set((round(x, 4), round(y, 4)) for x, y in points))
    if len(pts) <= 2:
        return pts

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lower: List[Tuple[float, float]] = []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    upper: List[Tuple[float, float]] = []
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


def _local_points(kind: str, w: float, d: float, h: float) -> List[Tuple[float, float, float]]:
    """Eckpunkte / Umfangspunkte des Koerpers im eigenen System (Fusspunkt im Ursprung, Unterseite auf z = 0, Hoehe h) - wie die Einheitsgeometrien der 3D-Ansicht."""
    if kind == "cylinder":
        ring = [(w / 2 * math.cos(a * math.pi / 12), d / 2 * math.sin(a * math.pi / 12)) for a in range(24)]
        return [(x, y, 0.0) for x, y in ring] + [(x, y, h) for x, y in ring]
    if kind == "sphere":
        out = []
        for i in range(9):
            phi = math.pi * i / 8
            for j in range(16):
                theta = 2 * math.pi * j / 16
                out.append((w / 2 * math.sin(phi) * math.cos(theta), d / 2 * math.sin(phi) * math.sin(theta), h / 2 + h / 2 * math.cos(phi)))
        return out
    if kind == "wedge":                                                            # Dreiecksprisma: hoch bei -X
        return [(-w / 2, -d / 2, 0), (w / 2, -d / 2, 0), (-w / 2, -d / 2, h), (-w / 2, d / 2, 0), (w / 2, d / 2, 0), (-w / 2, d / 2, h)]
    return [(sx * w / 2, sy * d / 2, z) for sx in (-1, 1) for sy in (-1, 1) for z in (0.0, h)]


def _rotate_xyz(point: Tuple[float, float, float], rx: float, ry: float, rz: float) -> Tuple[float, float, float]:
    """Drehung wie three.js Euler "XYZ" (Matrix Rx * Ry * Rz): erst um Z, dann um Y, zuletzt um X."""
    x, y, z = point
    c, s = math.cos(rz), math.sin(rz)
    x, y = x * c - y * s, x * s + y * c
    c, s = math.cos(ry), math.sin(ry)
    x, z = x * c + z * s, -x * s + z * c
    c, s = math.cos(rx), math.sin(rx)
    y, z = y * c - z * s, y * s + z * c
    return x, y, z


def _within(shape: Dict[str, Any], other: Dict[str, Any]) -> bool:
    """Liegt der Umriss von `shape` ganz im Umriss von `other` (ein Randpunkt zaehlt als drinnen: die Punkte werden minimal zur Mitte von `other` gerueckt)?"""
    cx, cy = other["center"]
    return all(_inside((x + (cx - x) * 0.01, y + (cy - y) * 0.01), other["poly"]) for x, y in shape["poly"])


def _stage_shapes() -> List[Dict[str, Any]]:
    """Koerper der 3D-Buehne als Umrisse von oben (x, y in Metern; Z nach oben) mit echter Drehung um alle drei Achsen: Wand, Decke oder Quader sehen von oben so aus wie in der 3D-Ansicht."""
    shapes: List[Dict[str, Any]] = []
    for obj in sim_stages.store.objects:
        px, py, pz = (float(v) for v in obj["position"][:3])
        w, d, h = (float(v) for v in obj["size"][:3])
        rx, ry, rz = (math.radians(float(v)) for v in (list(obj.get("rotation") or [0, 0, 0]) + [0, 0, 0])[:3])
        moved = [_rotate_xyz(p, rx, ry, rz) for p in _local_points(obj.get("type", "box"), w, d, h)]
        pts = [(px + x, py + y, pz + z) for x, y, z in moved]
        poly = _hull([(x, y) for x, y, _z in pts])
        if len(poly) < 2:
            continue
        zs = [z for _x, _y, z in pts]
        shapes.append({"poly": poly, "color": _hex_color(obj.get("color")), "base": min(zs), "top": max(zs), "name": str(obj.get("name", "")),
                       "center": (sum(p[0] for p in poly) / len(poly), sum(p[1] for p in poly) / len(poly))})
    return shapes


def _span_at(points: List[Tuple[float, float]], y: float) -> Optional[Tuple[float, float]]:
    """Wo eine waagerechte Linie in Hoehe y ein (konvexes) Vieleck schneidet: (links, rechts) oder None."""
    xs: List[float] = []
    for (x1, y1), (x2, y2) in zip(points, points[1:] + points[:1]):
        if (y1 - y) * (y2 - y) <= 0 and y1 != y2:
            xs.append(x1 + (x2 - x1) * (y - y1) / (y2 - y1))
        elif y1 == y2 == y:
            xs.extend((x1, x2))
    return (min(xs), max(xs)) if xs else None


def _label_lines(points: List[Tuple[float, float]], label: str, size: float = 6.0) -> Optional[Tuple[float, float, List[str]]]:
    """Beschriftung einer Flaeche im Plan: unten in der Flaeche (dort stoeren die Scheinwerfer am wenigsten), so viele Zeilen (bis 3), wie in die Form passen.
    Rueckgabe (x-Mitte, Grundlinie der ersten Zeile, Zeilen) oder None, wenn nichts hineinpasst (schmale Waende bleiben ohne Beschriftung)."""
    center_x = sum(p[0] for p in points) / len(points)
    low = max(p[1] for p in points)
    line_h = size + 1.0
    for count in (1, 2, 3):
        base_last = low - 2.0 - _edge_gap(points, center_x, low)                      # Grundlinie der letzten Zeile: knapp ueber dem unteren Rand an dieser Stelle
        first = base_last - (count - 1) * line_h
        spans = [_span_at(points, y) for y in (base_last + 0.5, first - size)]
        if not all(spans):
            continue
        left = max(s[0] for s in spans)
        right = min(s[1] for s in spans)
        avail = right - left - 4.0
        if avail < 18:
            continue
        lines = wrap_limited(label, size, avail, count)
        if len(wrap(label, size, avail)) <= count and all(text_width(x, size) <= avail for x in lines):
            return (left + right) / 2, first, lines
    left_right = _span_at(points, low - 4.0)
    if left_right and left_right[1] - left_right[0] >= 30:
        return (left_right[0] + left_right[1]) / 2, low - 3.0, [fit(label, size, left_right[1] - left_right[0] - 4.0)]
    return None


def _edge_gap(points: List[Tuple[float, float]], x: float, low: float) -> float:
    """Abstand der Unterkante des Vielecks an der Stelle x zur tiefsten Stelle (bei gedrehten Rechtecken liegt die Kante in der Mitte hoeher als die Ecke)."""
    ys = []
    for (x1, y1), (x2, y2) in zip(points, points[1:] + points[:1]):
        if (x1 - x) * (x2 - x) <= 0 and x1 != x2:
            ys.append(y1 + (y2 - y1) * (x - x1) / (x2 - x1))
    return (low - max(ys)) if ys else 0.0


def _soft(color: Tuple[float, float, float], amount: float = 0.55) -> Tuple[float, float, float]:
    """Farbe zum Weiss hin aufhellen (Flaechen auf dem Plan sollen nicht dunkel wirken)."""
    return tuple(c + (1.0 - c) * amount for c in color)                              # type: ignore[return-value]


def _plan(doc: Doc) -> None:
    t = doc.t
    pdf = doc.pdf
    positions, source = _positions()
    if positions:
        doc.ensure(340)                                                             # Ueberschrift und Plan zusammen auf eine Seite
    doc.heading(t["plan"])
    if not positions:
        doc.note(t["plan_none"])
        return
    doc.note(t["plan_stage"] if source == "stage" else t["plan_layout"])
    shapes = _stage_shapes() if source == "stage" else []
    heights = {fid: float(item["position"][2]) if len(item.get("position", [])) > 2 else 4.0 for fid, item in sim_stages.store.layout.items()} if source == "stage" else {}
    xs = [p[0] for p in positions.values()] + [p[0] for s in shapes for p in s["poly"]]
    ys = [p[1] for p in positions.values()] + [p[1] for s in shapes for p in s["poly"]]
    min_x, max_x, min_y, max_y = min(xs), max(xs), min(ys), max(ys)
    span_x, span_y = max(max_x - min_x, 1e-6), max(max_y - min_y, 1e-6)
    area_w = doc.width - 50
    area_h = max(min(doc.bottom - doc.y - 80, 450.0), 150.0)
    scale = min(area_w / span_x, area_h / span_y)
    plan_w, plan_h = span_x * scale, span_y * scale
    ox = doc.left + 25 + (area_w - plan_w) / 2
    oy = doc.y + 24
    box_top, box_h = oy - 18, plan_h + 36 + (16 if source == "stage" else 0)                 # unten Platz fuer den Massstab (in der Zeichnung)
    pdf.rect(doc.left, box_top, doc.width, box_h, fill=(0.985, 0.985, 0.99), stroke=(0.8, 0.8, 0.85), width=0.5)

    def to_pdf(x: float, y: float) -> Tuple[float, float]:
        return ox + (x - min_x) * scale, oy + (max_y - y) * scale

    # Koerper von unten nach oben; was ganz unter einem hoeheren Koerper liegt, ist von oben verdeckt: nur gestrichelter Umriss (wie durch das Dach gesehen). Alle Flaechen sind hell und durchsichtig,
    # darunterliegendes scheint durch; jeder Koerper traegt seinen Namen.
    ordered = sorted(shapes, key=lambda s: (s["top"], s["base"]))
    for index, shape in enumerate(ordered):
        covered = any(other["top"] > shape["top"] + 1e-6 and _within(shape, other) for other in ordered[index + 1:])
        shape["covered"] = covered
        pts = [to_pdf(x, y) for x, y in shape["poly"]]
        base = shape["color"]
        if covered:
            pdf.polygon(pts, stroke=_soft(base, 0.15), width=0.7, dash=(3, 2))
        else:
            pdf.polygon(pts, fill=_soft(base, 0.45), stroke=tuple(c * 0.75 for c in base), width=0.8, alpha=0.28)
    for shape in ordered:                                                             # Namen oben drauf (klein, grau)
        if shape["name"] and len(shape["poly"]) >= 3:
            pts = [to_pdf(x, y) for x, y in shape["poly"]]
            width_pt = max(p[0] for p in pts) - min(p[0] for p in pts)
            height_pt = max(p[1] for p in pts) - min(p[1] for p in pts)
            if width_pt < 24 or height_pt < 10:                                       # schmale Waende bleiben ohne Beschriftung
                continue
            placed = _label_lines(pts, shape["name"])
            if placed is None:
                continue
            label_x, first_baseline, lines = placed
            for number, line in enumerate(lines):
                pdf.text(label_x, first_baseline + number * 7, line, 6, False, (0.5, 0.5, 0.55) if shape["covered"] else (0.35, 0.35, 0.4), "c")
    colors = _group_colors()
    for fid, (x, y) in positions.items():
        fx = state.fixtures[fid]
        px, py = to_pdf(x, y)
        z = heights.get(fid, 4.0)
        covered = any(shape["top"] > z + 1e-6 and _inside((x, y), shape["poly"]) for shape in shapes)           # unter einem Koerper: von oben nicht zu sehen
        color = colors.get(fid, (0.45, 0.45, 0.5))
        if covered:
            pdf.circle(px, py, 4.2, fill=color, stroke=color, width=0.8, alpha=0.3, dash=(1.6, 1.4))
            pdf.text(px + 6, py + 2.5, str(fx.fid or "?"), 7, False, GRAY)
        else:
            pdf.circle(px, py, 4.2, fill=color, stroke=(1, 1, 1), width=0.6)
            pdf.text(px + 6, py + 2.5, str(fx.fid or "?"), 7, True, INK)
    if source == "stage":                                                             # Massstab IN der Zeichnung (links unten)
        for meters in (10, 5, 2, 1, 0.5):
            if meters * scale <= plan_w / 2:
                break
        sy = box_top + box_h - 9
        pdf.line(doc.left + 10, sy, doc.left + 10 + meters * scale, sy, 1.2, INK)
        pdf.line(doc.left + 10, sy - 2.5, doc.left + 10, sy + 2.5, 0.8, INK)
        pdf.line(doc.left + 10 + meters * scale, sy - 2.5, doc.left + 10 + meters * scale, sy + 2.5, 0.8, INK)
        pdf.text(doc.left + 16 + meters * scale, sy + 2.5, f"{meters:g} m", 7.5, False, GRAY)
    doc.y = box_top + box_h + 6
    legend = list(state.groups.items())
    x = doc.left
    for index, (name, ids) in enumerate(legend):
        label = fit(name, 8, doc.width - 30)
        need = text_width(label, 8) + 22
        if x + need > doc.right:
            x = doc.left
            doc.y += 12
        doc.ensure(14)
        pdf.rect(x, doc.y + 1, 8, 8, fill=PALETTE[index % len(PALETTE)])
        pdf.text(x + 12, doc.y + 8.5, label, 8, False, INK)
        x += need
    if legend:
        doc.y += 14
    keyed = sorted((state.fixtures[fid] for fid in positions), key=lambda f: (f.fid or 0, f.name.lower()))                  # Schluessel: Nummer im Plan -> Name des Scheinwerfers (3 Spalten)
    if keyed:
        doc.y += 2
        columns = 3
        column_w = doc.width / columns
        per_column = (len(keyed) + columns - 1) // columns
        for row in range(per_column):
            texts = {}
            for col in range(columns):
                index = col * per_column + row
                if index < len(keyed):
                    texts[col] = wrap_limited(f"{keyed[index].fid or '?'}  {keyed[index].name}", 7.5, column_w - 10, 3)
            height = 9 * max(len(v) for v in texts.values()) + 1
            doc.ensure(height + 2)
            doc.y += 9
            for col, lines in texts.items():
                for number, line in enumerate(lines):
                    pdf.text(doc.left + col * column_w + 2, doc.y + number * 8.5, line, 7.5, False, INK)
            doc.y += 8.5 * (max(len(v) for v in texts.values()) - 1)
        doc.y += 4
    missing = [fx for fid, fx in state.fixtures.items() if fid not in positions]
    if missing:
        doc.note(f"{t['no_pos']}: " + ", ".join(str(fx.fid or fx.name) for fx in sorted(missing, key=lambda f: f.fid or 0)[:40]) + (" ..." if len(missing) > 40 else ""))


def _trigger_text(doc: Doc, cue: Any) -> str:
    t = doc.t
    trigger = getattr(cue, "trigger", "go")
    if trigger == "timecode" and cue.timecode_ms is not None:
        ms = int(cue.timecode_ms)
        return f"{t['timecode']} {ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d}"
    if trigger == "audio":
        return f"{t['audio']} {cue.audio_source}"
    if trigger == "midi":
        return f"{t['midi']} {cue.midi_type} {cue.midi_number}"
    if trigger == "clock":
        return f"{t['clock']} {cue.clock_time} {timeofday.days_label(list(cue.clock_days))}".strip()
    return t.get(trigger, trigger)


def _cues(doc: Doc) -> None:
    t = doc.t
    doc.heading(t["cues"])
    if not state.cuelists:
        doc.note(t["none_cues"])
        return
    for cuelist in state.cuelists.values():
        doc.ensure(50)
        doc.y += 14
        doc.pdf.text(doc.left, doc.y, f"{cuelist.name}  ({len(cuelist.cues)})", size=10, bold=True, color=INK)
        doc.y += 2
        rows = [[f"{cue.number:g}", cue.name or "", _trigger_text(doc, cue), f"{cue.fade:g} s" if cue.fade else "", f"{cue.delay:g} s" if cue.delay else ""]
                for cue in sorted(cuelist.cues, key=lambda c: c.number)]
        if rows:
            doc.table([(t["cue"], 8, "r"), (t["name"], 40, "l"), (t["trigger"], 30, "l"), (t["fade"], 9, "r"), (t["delay"], 9, "r")], rows)
        else:
            doc.note(t["empty"])


def build_pdf(parts: List[str], lang: str = "en", paper: str = "a4") -> Tuple[bytes, str]:
    parts = [p for p in PARTS if p in parts] or list(PARTS)
    doc = Doc(paper, languages.normalize(lang))
    _title(doc)
    types = _type_names() if "patch" in parts else {}
    for part in parts:
        if part == "patch":
            _patch(doc, types)
        elif part == "universes":
            _universes(doc)
        elif part == "groups":
            _groups(doc)
        elif part == "plan":
            _plan(doc)
        elif part == "cues":
            _cues(doc)
    data = doc.pdf.render(footer=f"OpenCue - {doc.show}", page_label=doc.t["page"])
    safe = re.sub(r'[\\/:*?"<>|]+', "_", doc.show).strip() or "show"
    return data, f"{safe} - {doc.t['title']}.pdf"


# ---------------------------------------------------------------------------------------------------------------- HTTP
@router.get("/api/report/info")
async def report_info() -> JSONResponse:
    positions, source = _positions()
    return JSONResponse({"fixtures": len(state.fixtures), "groups": len(state.groups), "cuelists": len(state.cuelists), "positions": len(positions), "plan_source": source})


@router.get("/api/report/pdf")
async def report_pdf(request: Request) -> Response:
    import asyncio
    q = request.query_params
    parts = [p for p in (q.get("parts") or "").split(",") if p in PARTS]
    paper = q.get("paper", "a4").lower()
    data, name = await asyncio.to_thread(build_pdf, parts, q.get("lang") or state.language, paper if paper in PAPERS else "a4")
    disposition = "inline" if q.get("inline") in ("1", "true") else "attachment"
    import urllib.parse
    fallback = re.sub(r"[^A-Za-z0-9._ -]", "_", name)
    return Response(content=data, media_type="application/pdf", headers={
        "Content-Disposition": f"{disposition}; filename=\"{fallback}\"; filename*=UTF-8''{urllib.parse.quote(name)}", "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})
