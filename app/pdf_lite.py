# Copyright (C) 2026 Samuel Zenker
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Ein kleiner PDF-Schreiber ohne Fremdbibliothek: Seiten mit Text (Helvetica, WinAnsi), Linien, Rechtecken und Vielecken - genug fuer Listen, Tabellen und Plaene (app/reports.py).
Koordinaten: Punkt (1/72 Zoll), Ursprung OBEN links, y waechst nach unten (wie auf dem Bildschirm). Farben als (r, g, b) von 0 bis 1.

    pdf = Pdf(title="Show")
    pdf.text(40, 60, "Hallo", size=12, bold=True)
    pdf.rect(40, 80, 100, 20, fill=(0.9, 0.9, 0.9), stroke=(0, 0, 0))
    pdf.new_page()
    data = pdf.render(footer="Show", page_label="Seite {n} / {total}")
"""
from __future__ import annotations

import math
import zlib
from typing import List, Optional, Sequence, Tuple

Color = Tuple[float, float, float]

# Breiten der Standardschrift Helvetica (je 1000 Einheiten) fuer die Zeichen 32..126; Fettschrift wird mit einem Zuschlag gerechnet (nur fuer das Kuerzen / Ausrichten)
_WIDTHS = [278, 278, 355, 556, 556, 889, 667, 191, 333, 333, 389, 584, 278, 333, 278, 278,
           556, 556, 556, 556, 556, 556, 556, 556, 556, 556, 278, 278, 584, 584, 584, 556,
           1015, 667, 667, 722, 722, 667, 611, 778, 722, 278, 500, 667, 556, 833, 722, 778,
           667, 778, 722, 667, 611, 722, 667, 944, 667, 667, 611, 278, 278, 278, 469, 556,
           333, 556, 556, 500, 556, 556, 278, 556, 556, 222, 222, 500, 222, 833, 556, 556,
           556, 556, 333, 500, 278, 556, 500, 722, 500, 500, 500, 334, 260, 334, 584]
_WIDE = {"Ä": 667, "Ö": 778, "Ü": 722, "ä": 556, "ö": 556, "ü": 556, "ß": 611, "é": 556, "è": 556, "à": 556, "…": 1000, "–": 556, "—": 1000, "°": 400, "€": 556}


def _escape(text: str) -> bytes:
    out = bytearray()
    for byte in text.encode("cp1252", "replace"):
        if byte in (0x28, 0x29, 0x5C):
            out += b"\\" + bytes([byte])
        elif byte < 32 or byte > 126:
            out += b"\\%03o" % byte
        else:
            out.append(byte)
    return bytes(out)


def text_width(text: str, size: float, bold: bool = False) -> float:
    total = 0
    for ch in text:
        code = ord(ch)
        total += _WIDTHS[code - 32] if 32 <= code <= 126 else _WIDE.get(ch, 556)
    return total * size / 1000.0 * (1.07 if bold else 1.0)


def fit(text: str, size: float, max_width: float, bold: bool = False) -> str:
    """Text auf eine Breite kuerzen (mit ...)."""
    if text_width(text, size, bold) <= max_width:
        return text
    while text and text_width(text + "...", size, bold) > max_width:
        text = text[:-1]
    return text + "..."


def _split_word(word: str, size: float, max_width: float, bold: bool) -> List[str]:
    """Ein einzelnes Wort, das breiter als die Zeile ist (ein langer Dateiname ohne Leerzeichen), an Trennstellen (_ - . / ,) oder notfalls mitten im Wort teilen."""
    pieces: List[str] = []
    rest = word
    while rest and text_width(rest, size, bold) > max_width:
        cut = len(rest)
        while cut > 1 and text_width(rest[:cut], size, bold) > max_width:
            cut -= 1
        soft = max((rest.rfind(ch, 0, cut) for ch in "_-./,"), default=-1)              # lieber nach einem Trennzeichen brechen
        if soft >= max(2, cut // 2):
            cut = soft + 1
        pieces.append(rest[:cut])
        rest = rest[cut:]
    if rest:
        pieces.append(rest)
    return pieces


def wrap(text: str, size: float, max_width: float, bold: bool = False) -> List[str]:
    """Text an Leerzeichen auf Zeilen der Breite max_width umbrechen; zu lange Woerter werden geteilt (nie ueber den Rand)."""
    lines: List[str] = []
    current = ""
    for word in text.split():
        for piece in (_split_word(word, size, max_width, bold) if text_width(word, size, bold) > max_width else [word]):
            trial = (current + " " + piece).strip()
            if current and text_width(trial, size, bold) > max_width:
                lines.append(current)
                current = piece
            else:
                current = trial
    if current:
        lines.append(current)
    return lines or [""]


def wrap_limited(text: str, size: float, max_width: float, max_lines: int, bold: bool = False) -> List[str]:
    """Wie wrap(), aber hoechstens max_lines Zeilen: was darueber hinausgeht, wird in der letzten Zeile mit ... gekuerzt."""
    lines = wrap(text, size, max_width, bold)
    if len(lines) <= max_lines:
        return lines
    kept = lines[:max_lines - 1]
    kept.append(fit(" ".join(lines[max_lines - 1:]), size, max_width, bold))
    return kept


def _num(value: float) -> str:
    return f"{value:.2f}".rstrip("0").rstrip(".") or "0"


def _rgb(color: Color) -> str:
    return " ".join(_num(max(0.0, min(1.0, c))) for c in color)


class Pdf:
    def __init__(self, width: float = 595.28, height: float = 841.89, margin: float = 36.0, title: str = "") -> None:
        self.width, self.height, self.margin, self.title = width, height, margin, title
        self._pages: List[List[str]] = []
        self._alphas: set = set()                                            # benutzte Durchsichtigkeiten (ExtGState je Wert)
        self.new_page()

    # ---------------------------------------------------------------- Seiten
    def new_page(self) -> None:
        self._pages.append([])

    @property
    def page_count(self) -> int:
        return len(self._pages)

    def _ops(self) -> List[str]:
        return self._pages[-1]

    def _y(self, y: float) -> float:
        return self.height - y

    # ---------------------------------------------------------------- Zeichnen
    def text(self, x: float, y: float, text: str, size: float = 9.0, bold: bool = False, color: Color = (0, 0, 0), align: str = "l") -> None:
        """Text mit der GRUNDLINIE bei y. align: l (x = linker Rand), r (x = rechter Rand), c (x = Mitte)."""
        if not text:
            return
        width = text_width(text, size, bold)
        if align == "r":
            x -= width
        elif align == "c":
            x -= width / 2
        font = "F2" if bold else "F1"
        self._ops().append(f"BT /{font} {_num(size)} Tf {_rgb(color)} rg {_num(x)} {_num(self._y(y))} Td (".replace("\n", " ") + _escape(text).decode("latin-1") + ") Tj ET")

    def line(self, x1: float, y1: float, x2: float, y2: float, width: float = 0.5, color: Color = (0, 0, 0), dash: Optional[Sequence[float]] = None) -> None:
        dash_op = f"[{' '.join(_num(d) for d in dash)}] 0 d " if dash else "[] 0 d "
        self._ops().append(f"q {dash_op}{_num(width)} w {_rgb(color)} RG {_num(x1)} {_num(self._y(y1))} m {_num(x2)} {_num(self._y(y2))} l S Q")

    def _alpha_op(self, alpha: float) -> str:
        """Operator fuer eine Durchsichtigkeit (1 = deckend); die Zustaende werden beim Ausgeben angelegt."""
        if alpha >= 0.999:
            return ""
        level = max(1, min(99, int(round(alpha * 100))))
        self._alphas.add(level)
        return f"/GS{level} gs"

    def rect(self, x: float, y: float, w: float, h: float, fill: Optional[Color] = None, stroke: Optional[Color] = None, width: float = 0.5,
             alpha: float = 1.0, dash: Optional[Sequence[float]] = None) -> None:
        """Rechteck mit der OBEREN linken Ecke bei (x, y). alpha: Durchsichtigkeit, dash: gestrichelte Linie."""
        if fill is None and stroke is None:
            return
        op = "B" if fill is not None and stroke is not None else ("f" if fill is not None else "S")
        parts = ["q", self._alpha_op(alpha), f"[{' '.join(_num(d) for d in dash)}] 0 d" if dash else "", f"{_num(width)} w"]
        if fill is not None:
            parts.append(f"{_rgb(fill)} rg")
        if stroke is not None:
            parts.append(f"{_rgb(stroke)} RG")
        parts.append(f"{_num(x)} {_num(self._y(y + h))} {_num(w)} {_num(h)} re {op} Q")
        self._ops().append(" ".join(parts))

    def polygon(self, points: Sequence[Tuple[float, float]], fill: Optional[Color] = None, stroke: Optional[Color] = None, width: float = 0.5,
                alpha: float = 1.0, dash: Optional[Sequence[float]] = None) -> None:
        if len(points) < 2 or (fill is None and stroke is None):
            return
        op = "b" if fill is not None and stroke is not None else ("f" if fill is not None else "s")
        parts = ["q", self._alpha_op(alpha), f"[{' '.join(_num(d) for d in dash)}] 0 d" if dash else "", f"{_num(width)} w"]
        if fill is not None:
            parts.append(f"{_rgb(fill)} rg")
        if stroke is not None:
            parts.append(f"{_rgb(stroke)} RG")
        parts.append(f"{_num(points[0][0])} {_num(self._y(points[0][1]))} m")
        parts.extend(f"{_num(px)} {_num(self._y(py))} l" for px, py in points[1:])
        parts.append(f"{op} Q")
        self._ops().append(" ".join(parts))

    def circle(self, cx: float, cy: float, r: float, fill: Optional[Color] = None, stroke: Optional[Color] = None, width: float = 0.5,
               alpha: float = 1.0, dash: Optional[Sequence[float]] = None) -> None:
        self.polygon([(cx + r * math.cos(a * math.pi / 8), cy + r * math.sin(a * math.pi / 8)) for a in range(16)], fill, stroke, width, alpha, dash)

    # ---------------------------------------------------------------- Ausgabe
    def render(self, footer: str = "", page_label: str = "{n} / {total}") -> bytes:
        total = len(self._pages)
        if footer or page_label:
            for index, ops in enumerate(self._pages, start=1):
                self._pages_footer(ops, footer, page_label.format(n=index, total=total))
        objects: List[bytes] = []                                             # Objekt 1 = Katalog, 2 = Seitenbaum, 3/4 = Schriften, 5 = Info, danach je Seite 2

        def add(body: bytes) -> int:
            objects.append(body)
            return len(objects)

        add(b"<< /Type /Catalog /Pages 2 0 R >>")
        add(b"")                                                              # Platz fuer den Seitenbaum
        add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
        add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>")
        add(b"<< /Title (" + _escape(self.title) + b") /Producer (OpenCue) /Creator (OpenCue) >>")
        states = ("/ExtGState << " + " ".join(f"/GS{level} << /ca {level / 100:.2f} /CA {level / 100:.2f} >>" for level in sorted(self._alphas)) + " >>") if self._alphas else ""
        kids = []
        for ops in self._pages:
            stream = zlib.compress("\n".join(ops).encode("latin-1", "replace"))
            content = add(b"<< /Length " + str(len(stream)).encode() + b" /Filter /FlateDecode >>\nstream\n" + stream + b"\nendstream")
            page = add(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {_num(self.width)} {_num(self.height)}] /Resources << /Font << /F1 3 0 R /F2 4 0 R >> {states} >> /Contents {content} 0 R >>".encode())
            kids.append(f"{page} 0 R")
        objects[1] = f"<< /Type /Pages /Kids [{' '.join(kids)}] /Count {len(kids)} >>".encode()
        out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offsets = []
        for number, body in enumerate(objects, start=1):
            offsets.append(len(out))
            out += f"{number} 0 obj\n".encode() + body + b"\nendobj\n"
        xref = len(out)
        out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
        for offset in offsets:
            out += f"{offset:010d} 00000 n \n".encode()
        out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R /Info 5 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
        return bytes(out)

    def _pages_footer(self, ops: List[str], footer: str, label: str) -> None:
        y = self._y(self.height - self.margin / 2 - 2)
        gray = _rgb((0.45, 0.45, 0.45))
        ops.append(f"q 0.4 w {_rgb((0.75, 0.75, 0.75))} RG {_num(self.margin)} {_num(y + 11)} m {_num(self.width - self.margin)} {_num(y + 11)} l S Q")
        if footer:
            ops.append(f"BT /F1 7.5 Tf {gray} rg {_num(self.margin)} {_num(y)} Td (" + _escape(footer).decode("latin-1") + ") Tj ET")
        if label:
            width = text_width(label, 7.5)
            ops.append(f"BT /F1 7.5 Tf {gray} rg {_num(self.width - self.margin - width)} {_num(y)} Td (" + _escape(label).decode("latin-1") + ") Tj ET")
