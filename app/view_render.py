# Copyright (C) 2026 Samuel Zenker
# SPDX-License-Identifier: GPL-3.0-or-later
"""
view_render.py
Kleine Ausgabe-Ansichten ("Status-Anzeigen") fuer einfache Geraete: aus EINEM Anzeigemodell entstehen
  - ein Bild (PNG, BMP oder rohes RGB565 fuer ein TFT-Display am ESP32) - gerendert mit numpy und einer eingebauten 5x7-Schrift, ohne zusaetzliche Bibliothek,
  - eine schlichte Web-Seite (HTML, aktualisiert sich selbst) und
  - JSON (das Modell selbst).
Das Modell ist eine Liste von Teilen, von oben nach unten angeordnet:
    {"t": "title", "text": "DMX 1"}                              Kopfzeile
    {"t": "big", "text": "00:01:23.400", "sub": "LAEUFT"}        grosse Zahl / Text (so gross, wie die Breite es zulaesst)
    {"t": "kv", "k": "Master", "v": "100 %", "state": "ok"}      Zeile "Name ... Wert" (state: ok | off | warn | "" )
    {"t": "bars", "values": [0..1, ...], "labels": ["B", ...]}   Balken (Pegel, Baender)
    {"t": "grid", "cols": 32, "values": [0..1, ...]}             Raster aus Feldern (DMX-Kanaele)
Reine Rechnung, keine Anbindung an den Server (api_v1_views.py liefert die Modelle) - dadurch einzeln pruefbar.
"""
from __future__ import annotations

import html
import json
import struct
import zlib
from typing import Any, Dict, List, Tuple

import numpy as np

THEMES: Dict[str, Dict[str, Tuple[int, int, int]]] = {
    "dark": {"bg": (16, 16, 18), "panel": (24, 24, 27), "text": (231, 231, 234), "dim": (154, 154, 163), "accent": (255, 176, 0), "ok": (63, 207, 142), "warn": (255, 107, 107), "off": (110, 110, 118), "line": (44, 44, 49)},
    "light": {"bg": (246, 246, 247), "panel": (255, 255, 255), "text": (26, 26, 29), "dim": (92, 92, 102), "accent": (168, 106, 0), "ok": (20, 140, 90), "warn": (200, 50, 50), "off": (140, 140, 150), "line": (217, 217, 222)},
}

_GLYPHS_RAW: Dict[str, List[str]] = {
    "A": [" ### ", "#   #", "#   #", "#####", "#   #", "#   #", "#   #"], "B": ["#### ", "#   #", "#   #", "#### ", "#   #", "#   #", "#### "],
    "C": [" ### ", "#   #", "#    ", "#    ", "#    ", "#   #", " ### "], "D": ["#### ", "#   #", "#   #", "#   #", "#   #", "#   #", "#### "],
    "E": ["#####", "#    ", "#    ", "#### ", "#    ", "#    ", "#####"], "F": ["#####", "#    ", "#    ", "#### ", "#    ", "#    ", "#    "],
    "G": [" ### ", "#   #", "#    ", "# ###", "#   #", "#   #", " ####"], "H": ["#   #", "#   #", "#   #", "#####", "#   #", "#   #", "#   #"],
    "I": [" ### ", "  #  ", "  #  ", "  #  ", "  #  ", "  #  ", " ### "], "J": ["  ###", "   # ", "   # ", "   # ", "   # ", "#  # ", " ##  "],
    "K": ["#   #", "#  # ", "# #  ", "##   ", "# #  ", "#  # ", "#   #"], "L": ["#    ", "#    ", "#    ", "#    ", "#    ", "#    ", "#####"],
    "M": ["#   #", "## ##", "# # #", "# # #", "#   #", "#   #", "#   #"], "N": ["#   #", "##  #", "# # #", "#  ##", "#   #", "#   #", "#   #"],
    "O": [" ### ", "#   #", "#   #", "#   #", "#   #", "#   #", " ### "], "P": ["#### ", "#   #", "#   #", "#### ", "#    ", "#    ", "#    "],
    "Q": [" ### ", "#   #", "#   #", "#   #", "# # #", "#  # ", " ## #"], "R": ["#### ", "#   #", "#   #", "#### ", "# #  ", "#  # ", "#   #"],
    "S": [" ####", "#    ", "#    ", " ### ", "    #", "    #", "#### "], "T": ["#####", "  #  ", "  #  ", "  #  ", "  #  ", "  #  ", "  #  "],
    "U": ["#   #", "#   #", "#   #", "#   #", "#   #", "#   #", " ### "], "V": ["#   #", "#   #", "#   #", "#   #", "#   #", " # # ", "  #  "],
    "W": ["#   #", "#   #", "#   #", "# # #", "# # #", "## ##", "#   #"], "X": ["#   #", "#   #", " # # ", "  #  ", " # # ", "#   #", "#   #"],
    "Y": ["#   #", "#   #", " # # ", "  #  ", "  #  ", "  #  ", "  #  "], "Z": ["#####", "    #", "   # ", "  #  ", " #   ", "#    ", "#####"],
    "0": [" ### ", "#   #", "#  ##", "# # #", "##  #", "#   #", " ### "], "1": ["  #  ", " ##  ", "  #  ", "  #  ", "  #  ", "  #  ", " ### "],
    "2": [" ### ", "#   #", "    #", "   # ", "  #  ", " #   ", "#####"], "3": ["#####", "   # ", "  #  ", "   # ", "    #", "#   #", " ### "],
    "4": ["   # ", "  ## ", " # # ", "#  # ", "#####", "   # ", "   # "], "5": ["#####", "#    ", "#### ", "    #", "    #", "#   #", " ### "],
    "6": ["  ## ", " #   ", "#    ", "#### ", "#   #", "#   #", " ### "], "7": ["#####", "    #", "   # ", "  #  ", " #   ", " #   ", " #   "],
    "8": [" ### ", "#   #", "#   #", " ### ", "#   #", "#   #", " ### "], "9": [" ### ", "#   #", "#   #", " ####", "    #", "   # ", " ##  "],
    " ": ["     "] * 7, ".": ["     "] * 5 + ["  ## ", "  ## "], ":": ["     ", "  ## ", "  ## ", "     ", "  ## ", "  ## ", "     "],
    ",": ["     "] * 5 + ["  ## ", "  #  "], "-": ["     ", "     ", "     ", "#####", "     ", "     ", "     "], "+": ["     ", "  #  ", "  #  ", "#####", "  #  ", "  #  ", "     "],
    "/": ["    #", "    #", "   # ", "  #  ", " #   ", "#    ", "#    "], "%": ["##   ", "##  #", "   # ", "  #  ", " #   ", "#  ##", "   ##"],
    "#": [" # # ", " # # ", "#####", " # # ", "#####", " # # ", " # # "], "(": ["   # ", "  #  ", " #   ", " #   ", " #   ", "  #  ", "   # "],
    ")": [" #   ", "  #  ", "   # ", "   # ", "   # ", "  #  ", " #   "], "_": ["     "] * 6 + ["#####"], "=": ["     ", "     ", "#####", "     ", "#####", "     ", "     "],
    "!": ["  #  "] * 5 + ["     ", "  #  "], "?": [" ### ", "#   #", "    #", "   # ", "  #  ", "     ", "  #  "], "<": ["   # ", "  #  ", " #   ", "#    ", " #   ", "  #  ", "   # "],
    ">": [" #   ", "  #  ", "   # ", "    #", "   # ", "  #  ", " #   "], "*": ["     ", "# # #", " ### ", "#####", " ### ", "# # #", "     "], "'": ["  #  ", "  #  ", " #   ", "     ", "     ", "     ", "     "],
    "[": [" ### ", " #   ", " #   ", " #   ", " #   ", " #   ", " ### "], "]": [" ### ", "   # ", "   # ", "   # ", "   # ", "   # ", " ### "], "|": ["  #  "] * 7,
    "°": [" ##  ", "#  # ", "#  # ", " ##  ", "     ", "     ", "     "],
}
GLYPHS: Dict[str, np.ndarray] = {ch: np.array([[c == "#" for c in row] for row in rows], dtype=bool) for ch, rows in _GLYPHS_RAW.items()}
_FOLD = {"Ä": "A", "Ö": "O", "Ü": "U", "ß": "S", "ä": "A", "ö": "O", "ü": "U"}
MAX_W, MAX_H = 800, 600
COLORS: Dict[str, Tuple[int, int, int]] = {"amber": (255, 176, 0), "green": (46, 204, 113), "red": (255, 90, 90), "blue": (80, 160, 255), "cyan": (60, 210, 230), "white": (235, 235, 235),
                                          "magenta": (230, 90, 200), "violet": (160, 120, 255), "orange": (255, 120, 40), "yellow": (240, 220, 60)}


def parse_color(text: Any) -> Any:
    """Farbname (amber, green, red, blue, cyan, white, magenta, violet, orange, yellow) oder #rrggbb -> (r, g, b); sonst None."""
    value = str(text or "").strip().lower().lstrip("#") if str(text or "").strip().startswith("#") else str(text or "").strip().lower()
    if value in COLORS:
        return COLORS[value]
    if len(value) == 6 and all(c in "0123456789abcdef" for c in value):
        return (int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16))
    return None


def wrap_text(text: str, max_chars: int, max_lines: int = 4) -> List[str]:
    words, lines, current = str(text).split(), [], ""
    for word in words:
        if current and len(current) + 1 + len(word) > max_chars:
            lines.append(current)
            current = word
        else:
            current = (current + " " + word).strip()
    if current:
        lines.append(current)
    return [line[:max_chars] for line in lines[:max_lines]]


def _glyph(ch: str) -> np.ndarray:
    ch = _FOLD.get(ch, ch.upper())
    return GLYPHS.get(ch, GLYPHS["?"])


def text_width(text: str, scale: int) -> int:
    return len(text) * 6 * scale - scale if text else 0


class Canvas:
    def __init__(self, width: int, height: int, theme: Dict[str, Tuple[int, int, int]]) -> None:
        self.w, self.h, self.theme = width, height, theme
        self.px = np.empty((height, width, 3), dtype=np.uint8)
        self.px[:, :] = theme["bg"]

    def rect(self, x: int, y: int, w: int, h: int, color: Tuple[int, int, int]) -> None:
        x0, y0, x1, y1 = max(0, x), max(0, y), min(self.w, x + w), min(self.h, y + h)
        if x1 > x0 and y1 > y0:
            self.px[y0:y1, x0:x1] = color

    def text(self, x: int, y: int, text: str, scale: int, color: Tuple[int, int, int]) -> int:
        """Text mit der linken oberen Ecke (x, y); gibt die Breite zurueck."""
        cursor = x
        for ch in text:
            mask = np.kron(_glyph(ch), np.ones((scale, scale), dtype=bool))
            h, w = mask.shape
            x0, y0, x1, y1 = max(0, cursor), max(0, y), min(self.w, cursor + w), min(self.h, y + h)
            if x1 > x0 and y1 > y0:
                sub = mask[y0 - y:y1 - y, x0 - cursor:x1 - cursor]
                self.px[y0:y1, x0:x1][sub] = color
            cursor += 6 * scale
        return cursor - x - scale


def _fit_scale(text: str, width: int, height: int, limit: int = 40) -> int:
    scale = 1
    while scale < limit and text_width(text, scale + 1) <= width and 7 * (scale + 1) <= height:
        scale += 1
    return scale


def _themed(theme_name: str, accent: Any = None) -> Dict[str, Tuple[int, int, int]]:
    theme = dict(THEMES.get(theme_name, THEMES["dark"]))
    if accent:
        theme["accent"] = tuple(accent)
    return theme


def draw(model: Dict[str, Any], width: int, height: int, theme_name: str = "dark", accent: Any = None) -> np.ndarray:
    """Zeichnet das Modell auf eine Flaeche width x height (Pixel) und gibt die Pixel (Hoehe x Breite x 3, uint8) zurueck. `accent`: eigene Hervorhebungsfarbe (r, g, b)."""
    width, height = max(64, min(MAX_W, int(width))), max(48, min(MAX_H, int(height)))
    theme = _themed(theme_name, accent)
    canvas = Canvas(width, height, theme)
    base = max(1, min(width // 160, height // 110))                 # Grundmassstab der Schrift
    pad = max(2, base * 3)
    parts = model.get("parts", [])
    fixed = 0
    flex = 0
    for part in parts:
        kind = part["t"]
        fixed += {"title": 7 * base + 2 * pad, "kv": 7 * base + pad, "big": 0}.get(kind, 0)
        flex += {"big": 2, "bars": 3, "grid": 3}.get(kind, 0)
    free = max(0, height - fixed - pad)
    y = 0
    for part in parts:
        kind = part["t"]
        if kind == "title":
            h = 7 * base + 2 * pad
            canvas.rect(0, 0, width, h, theme["panel"])
            canvas.rect(0, h - 1, width, 1, theme["line"])
            canvas.text(pad, pad, str(part.get("text", "")), base, theme["accent"])
            y += h
        elif kind == "kv":
            h = 7 * base + pad
            color = theme.get(part.get("state") or "", theme["text"]) if part.get("state") else theme["text"]
            canvas.text(pad, y + pad // 2 + 1, str(part.get("k", "")), base, theme["dim"])
            value = str(part.get("v", ""))
            canvas.text(width - pad - text_width(value, base), y + pad // 2 + 1, value, base, color)
            y += h
        else:
            h = int(free * {"big": 2, "bars": 3, "grid": 3}.get(kind, 1) / max(1, flex))
            if kind == "big":
                text = str(part.get("text", ""))
                max_chars = max(6, (width - 2 * pad) // (6 * base))
                sub_lines = wrap_text(str(part.get("sub", "")), max_chars) if part.get("sub") else []
                sub = sub_lines[0] if sub_lines else ""
                sub_h = (8 * base * len(sub_lines) + pad) if sub_lines else 0
                scale = _fit_scale(text, width - 2 * pad, h - sub_h - pad)
                top = y + max(0, (h - sub_h - 7 * scale) // 2)
                canvas.text(max(pad, (width - text_width(text, scale)) // 2), top, text, scale, theme.get(part.get("state") or "", theme["text"]) if part.get("state") else theme["text"])
                sub_color = theme.get(part.get("sub_state") or "", theme["dim"]) if part.get("sub_state") else theme["dim"]
                for number, line in enumerate(sub_lines):
                    canvas.text(max(pad, (width - text_width(line, base)) // 2), top + 7 * scale + pad + number * 8 * base, line, base, sub_color)
            elif kind == "bars":
                values = list(part.get("values", []))
                labels = list(part.get("labels", []))
                n = max(1, len(values))
                label_h = 7 * base + pad if labels else 0
                area_h = h - label_h - pad
                gap = max(1, base)
                bar_w = max(2, (width - 2 * pad - gap * (n - 1)) // n)
                for i, value in enumerate(values):
                    x = pad + i * (bar_w + gap)
                    canvas.rect(x, y + pad, bar_w, area_h, theme["panel"])
                    fill = int(round(max(0.0, min(1.0, float(value))) * area_h))
                    canvas.rect(x, y + pad + area_h - fill, bar_w, fill, theme["accent"])
                    if labels and i < len(labels) and bar_w >= 6 * base:
                        canvas.text(x + (bar_w - text_width(str(labels[i]), base)) // 2, y + pad + area_h + pad // 2, str(labels[i]), base, theme["dim"])
            elif kind == "grid":
                values = list(part.get("values", []))
                cols = max(1, int(part.get("cols", 32)))
                rows = max(1, -(-len(values) // cols))
                cell = max(1, min((width - 2 * pad) // cols, (h - pad) // rows))
                ox = (width - cell * cols) // 2
                for i, value in enumerate(values):
                    v = max(0.0, min(1.0, float(value)))
                    cx, cy = ox + (i % cols) * cell, y + pad // 2 + (i // cols) * cell
                    if v <= 0:
                        canvas.rect(cx, cy, max(1, cell - 1), max(1, cell - 1), theme["panel"])
                    else:
                        base_c, top_c = np.array(theme["panel"], dtype=float), np.array(theme["accent"], dtype=float)
                        canvas.rect(cx, cy, max(1, cell - 1), max(1, cell - 1), tuple(int(c) for c in base_c + (top_c - base_c) * (0.25 + 0.75 * v)))
            y += h
    return canvas.px


# ------------------------------------------------------------------------------------------------------------------ Dateiformate
def to_png(pixels: np.ndarray) -> bytes:
    h, w, _ = pixels.shape
    raw = np.concatenate([np.zeros((h, 1), dtype=np.uint8), pixels.reshape(h, w * 3)], axis=1).tobytes()

    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw, 3)) + chunk(b"IEND", b"")


def to_bmp(pixels: np.ndarray) -> bytes:
    """24-Bit-BMP (unten zuerst, BGR, Zeilen auf 4 Bytes aufgefuellt) - jeder kleine Decoder kann es."""
    h, w, _ = pixels.shape
    row = w * 3
    pad = (-row) % 4
    bgr = pixels[::-1, :, ::-1].reshape(h, row)
    if pad:
        bgr = np.concatenate([bgr, np.zeros((h, pad), dtype=np.uint8)], axis=1)
    data = bgr.tobytes()
    return b"BM" + struct.pack("<IHHI", 54 + len(data), 0, 0, 54) + struct.pack("<IiiHHIIiiII", 40, w, h, 1, 24, 0, len(data), 2835, 2835, 0, 0) + data


def to_rgb565(pixels: np.ndarray) -> bytes:
    """Rohe Bildpunkte, 16 Bit je Punkt (5-6-5), High-Byte zuerst: direkt an ein TFT (TFT_eSPI pushImage / Adafruit_GFX drawRGBBitmap) uebergeben."""
    r = pixels[:, :, 0].astype(np.uint16) >> 3
    g = pixels[:, :, 1].astype(np.uint16) >> 2
    b = pixels[:, :, 2].astype(np.uint16) >> 3
    return (((r << 11) | (g << 5) | b).astype(">u2")).tobytes()


# ------------------------------------------------------------------------------------------------------------------ HTML
def _css_color(rgb: Tuple[int, int, int]) -> str:
    return "#%02x%02x%02x" % rgb


def to_html_fragment(model: Dict[str, Any], theme_name: str = "dark", accent: Any = None) -> str:
    """Der Inhalt der Seite (ohne <html>): gleiche Teile wie das Bild."""
    theme = _themed(theme_name, accent)
    out: List[str] = []
    for part in model.get("parts", []):
        kind = part["t"]
        if kind == "title":
            out.append(f'<h1>{html.escape(str(part.get("text", "")))}</h1>')
        elif kind == "big":
            state = part.get("state")
            style = f' style="color:{_css_color(theme[state])}"' if state in theme else ""
            out.append(f'<div class="big"{style}>{html.escape(str(part.get("text", "")))}</div>')
            if part.get("sub"):
                out.append(f'<div class="sub">{html.escape(str(part["sub"]))}</div>')
        elif kind == "kv":
            state = part.get("state")
            style = f' style="color:{_css_color(theme[state])}"' if state in theme else ""
            out.append(f'<div class="kv"><span>{html.escape(str(part.get("k", "")))}</span><b{style}>{html.escape(str(part.get("v", "")))}</b></div>')
        elif kind == "bars":
            labels = part.get("labels", [])
            cells = "".join(f'<div class="bar"><i style="height:{int(max(0.0, min(1.0, float(v))) * 100)}%"></i><em>{html.escape(str(labels[i])) if i < len(labels) else ""}</em></div>' for i, v in enumerate(part.get("values", [])))
            out.append(f'<div class="bars">{cells}</div>')
        elif kind == "grid":
            cols = max(1, int(part.get("cols", 32)))
            cells = "".join(f'<u style="opacity:{0.12 + 0.88 * max(0.0, min(1.0, float(v))):.2f}"></u>' for v in part.get("values", []))
            out.append(f'<div class="grid" style="grid-template-columns:repeat({cols},1fr)">{cells}</div>')
    return "".join(out)


def to_html_page(model: Dict[str, Any], theme_name: str, refresh: float, fragment_url: str, accent: Any = None, offline_text: str = "No connection to OpenCue") -> str:
    theme = _themed(theme_name, accent)
    css = (f"body{{margin:0;background:{_css_color(theme['bg'])};color:{_css_color(theme['text'])};font:16px/1.4 system-ui,Segoe UI,Roboto,sans-serif}}"
           f"main{{max-width:44rem;margin:0 auto;padding:.6rem}}h1{{margin:0 0 .6rem;font-size:1rem;letter-spacing:.06em;text-transform:uppercase;color:{_css_color(theme['accent'])}}}"
           f".big{{font:700 clamp(2rem,12vw,5rem)/1.1 ui-monospace,Consolas,monospace;text-align:center;margin:1rem 0 .2rem}}.sub{{text-align:center;color:{_css_color(theme['dim'])};margin-bottom:1rem}}"
           f".kv{{display:flex;justify-content:space-between;border-bottom:1px solid {_css_color(theme['line'])};padding:.25rem 0}}.kv span{{color:{_css_color(theme['dim'])}}}"
           f".bars{{display:flex;gap:4px;height:10rem;margin:.8rem 0}}.bar{{flex:1;background:{_css_color(theme['panel'])};position:relative;display:flex;align-items:flex-end}}"
           f".bar i{{display:block;width:100%;background:{_css_color(theme['accent'])}}}.bar em{{position:absolute;bottom:-1.2rem;left:0;right:0;text-align:center;font-style:normal;font-size:.7rem;color:{_css_color(theme['dim'])}}}"
           f".grid{{display:grid;gap:2px;margin:.8rem 0}}.grid u{{aspect-ratio:1;background:{_css_color(theme['accent'])}}}"
           f"#e{{display:none;position:sticky;top:0;margin:0 0 .6rem;padding:.5rem .7rem;border-radius:6px;background:{_css_color(theme['warn'])};color:#fff;font-weight:600}}#v{{transition:opacity .3s}}")
    interval = max(500, int(refresh * 1000))
    script = ("var box=document.getElementById('v'),msg=document.getElementById('e'),url=" + json.dumps(fragment_url) + ",offline=" + json.dumps(offline_text) + ";"
              "function fail(e){msg.textContent=offline+' ('+e.message+')';msg.style.display='block';box.style.opacity='.35'}"
              "function tick(){fetch(url,{cache:'no-store'}).then(function(r){if(r.ok)return r.text();"
              "return r.json().then(function(j){throw new Error((j&&j.error&&j.error.message)||('HTTP '+r.status))},function(){throw new Error('HTTP '+r.status)})})"
              ".then(function(t){box.innerHTML=t;msg.style.display='none';box.style.opacity='1'}).catch(fail)}"
              "setInterval(tick," + str(interval) + ");")
    return (f'<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>OpenCue</title><style>{css}</style>'
            f'<noscript><meta http-equiv="refresh" content="{max(1, int(round(refresh)))}"></noscript></head><body><main><div id="e" role="alert"></div><div id="v">{to_html_fragment(model, theme_name, accent)}</div></main>'
            f'<script>{script}</script></body></html>')
