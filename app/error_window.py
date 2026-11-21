# Copyright (C) 2026 Samuel Zenker
# SPDX-License-Identifier: GPL-3.0-or-later
"""
error_window.py
Das Fehlerfenster von OpenCue: ein eigenes, selbst gezeichnetes Fenster im Stil der Oberflaeche (dunkel, Bernstein als Akzent, Logo), das auch dann
funktioniert, wenn das Programm noch nicht oder nicht mehr laeuft (Doppelstart, belegter Port, Absturz beim Start oder im Betrieb).

Immer Englisch, nicht konfigurierbar (Farben, Sprache). Inhalt: Ueberschrift, kurzer Text, Fehlercode (OC-xxxx, Liste in app/errors.py), optional eine Box mit
den technischen Angaben und Knoepfe: **Copy details** (Fehlercode, Version, System, Fehlertext und die letzten Log-Zeilen in die Zwischenablage - zum Einfuegen in
einen Fehlerbericht oder in eine KI), **Open log folder**, **Open log file** und die eigentliche Aktion (Standard: Close; Beschriftungen in der Sprache von OpenCue, siehe app/errors_i18n.py). Tasten: Esc schliesst, Enter = Hauptknopf,
Strg+C = Details kopieren. Das Fenster laesst sich an der Titelleiste verschieben.

Nur ctypes/GDI (app/winui.py), keine weiteren Pakete. Benutzung ueber app.errors.present(); direkt: show(...) -> Schluessel des gedrueckten Knopfes oder None.
Das Fenster laeuft in einem eigenen Thread mit eigener Nachrichtenschleife; show(block=True) wartet darauf, show(block=False) kehrt sofort zurueck.
"""
from __future__ import annotations

import itertools
import os
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional, Union

from app import winui

_BG = (13, 13, 16)
_TITLE_BG = (20, 20, 25)
_BORDER = (42, 42, 49)
_WHITE = (240, 240, 244)
_GREY = (160, 160, 170)
_DIM = (110, 110, 120)
_AMBER = (255, 176, 0)
_RED = (226, 74, 58)
_BOX = (9, 9, 12)
_BTN = (36, 36, 43)
_BTN_HOVER = (52, 52, 61)
_BTN_PRIMARY_HOVER = (255, 196, 64)
_counter = itertools.count(1)


@dataclass
class Button:
    key: str
    label: str
    primary: bool = False


def show(code: str, title: str, message: str, details: str = "", severity: str = "error", buttons: Optional[List[Button]] = None,
         clipboard: Union[str, Callable[[], str], None] = None, log_path: Optional[Path] = None, block: bool = True) -> Optional[str]:
    """Fehlerfenster zeigen. Rueckgabe: `key` des gedrueckten Hauptknopfes/Knopfes (z. B. "close"), None wenn per Esc/X geschlossen oder nicht moeglich."""
    if not winui.available():
        print(f"[OpenCue] {code}: {title}\n{message}\n{details}")
        return None
    result: List[Optional[str]] = [None]

    def run() -> None:
        try:
            _run(result, code, title, message, details, severity, buttons, clipboard, log_path)
        except Exception as exc:                                         # ein Fehlerfenster darf nie selbst zum Absturz werden
            print(f"[OpenCue] Error window failed ({exc}). {code}: {title}\n{message}\n{details}")

    thread = threading.Thread(target=run, name="error-window", daemon=False)
    thread.start()
    if block:
        thread.join()
    return result[0]


def _run(result, code, title, message, details, severity, buttons, clipboard, log_path) -> None:
    import ctypes
    from ctypes import wintypes
    from app.splash import read_logo_rects                               # dasselbe Pixel-Logo wie das Startbild

    api = winui.load()
    u, g, k = api.user32, api.gdi32, api.kernel32
    scale = winui.dpi_scale()

    def S(v: float) -> int:
        return int(round(v * scale))

    custom = buttons is not None
    primary_buttons = buttons or [Button("close", "Close", primary=True)]
    secondary: List[Button] = [Button("@copy", "Copy details")]
    if not custom and log_path:                                          # ohne Log (z. B. Datenordner unbenutzbar, OC-1004) gibt es nichts zu oeffnen
        secondary += [Button("@folder", "Open log folder"), Button("@file", "Open log file")]
    all_buttons: List[Button] = secondary + [b for b in primary_buttons if not b.primary] + [b for b in primary_buttons if b.primary]
    from app import errors_i18n                                          # Beschriftungen in der Sprache von OpenCue (Englisch, wenn unbekannt)
    ui_lang = errors_i18n.current_language()
    all_buttons = [Button(b.key, errors_i18n.ui(b.label, ui_lang), b.primary) for b in all_buttons]
    code_label = errors_i18n.ui("ERROR CODE", ui_lang)
    code_label_w = S(max(96, 9 * len(code_label) + 10))                  # laengere Beschriftung (fr, es) braucht mehr Platz
    accent = _RED if severity == "error" else _AMBER

    # ------------------------------------------------------------------ Schriften
    fonts: dict = {}

    def font(px: float, weight: int = 400, face: str = "Segoe UI"):
        key = (px, weight, face)
        if key not in fonts:
            fonts[key] = g.CreateFontW(-S(px), 0, 0, 0, weight, 0, 0, 0, 1, 0, 0, 5, 0, face)
        return fonts[key]

    brushes: dict = {}

    def brush(c: tuple):
        if c not in brushes:
            brushes[c] = g.CreateSolidBrush(winui.rgb(c))
        return brushes[c]

    # ------------------------------------------------------------------ Aufbau berechnen (Hoehe richtet sich nach dem Text)
    W = S(640)
    pad, title_h = S(28), S(40)
    unit = max(1, int(scale))
    logo = read_logo_rects()
    logo_px = 64 * unit
    text_x = pad + logo_px + S(24)
    text_w = W - text_x - pad
    measure_dc = g.CreateCompatibleDC(u.GetDC(None))

    def measure(text: str, f, width: int, flags: int = winui.DT_WORDBREAK | winui.DT_NOPREFIX) -> int:
        old = g.SelectObject(measure_dc, f)
        r = wintypes.RECT(0, 0, width, 0)
        u.DrawTextW(measure_dc, text, -1, ctypes.byref(r), flags | winui.DT_CALCRECT)
        g.SelectObject(measure_dc, old)
        return r.bottom

    y = title_h + S(28)
    head_h = measure(title, font(19, 700), text_w)
    head_y = y
    y += head_h + S(10)
    msg_h = measure(message, font(13), text_w)
    msg_y = y
    y += msg_h + S(16)
    code_y = y
    y += S(24)
    body_bottom = max(y, title_h + S(28) + logo_px)
    lines = _detail_lines(details)
    box_y = box_h = 0
    if lines:
        box_y = body_bottom + S(14)
        box_h = len(lines) * S(16) + S(20)
        body_bottom = box_y + box_h
    btn_y = body_bottom + S(24)
    btn_h = S(36)
    H = btn_y + btn_h + S(26)

    # Knoepfe von rechts nach links
    btn_rects: List[tuple] = []                                          # (Knopf, l, t, r, b)
    x = W - pad
    for b in reversed(all_buttons):
        w = _text_width(g, measure_dc, font(12.5, 600), b.label) + S(40)
        btn_rects.append((b, x - w, btn_y, x, btn_y + btn_h))
        x -= w + S(10)
    btn_rects.reverse()
    close_rect = (W - S(46), 0, W, title_h)

    state = {"hover": None, "copied_until": 0.0, "done": False}

    def clip_text() -> str:
        if callable(clipboard):
            try:
                return clipboard()
            except Exception as exc:
                return f"{code}: {title}\n{message}\n{details}\n(could not collect diagnostics: {exc})"
        return clipboard or f"{code}: {title}\n{message}\n{details}"

    # ------------------------------------------------------------------ Zeichnen
    def text(dc, s: str, rect: tuple, f, color: tuple, flags: int = winui.DT_NOPREFIX) -> None:
        old = g.SelectObject(dc, f)
        g.SetTextColor(dc, winui.rgb(color))
        r = wintypes.RECT(*rect)
        u.DrawTextW(dc, s, -1, ctypes.byref(r), flags)
        g.SelectObject(dc, old)

    def fill(dc, rect: tuple, color: tuple) -> None:
        u.FillRect(dc, ctypes.byref(wintypes.RECT(*rect)), brush(color))

    def cursor_in_window(hwnd) -> tuple:
        pt = wintypes.POINT()
        u.GetCursorPos(ctypes.byref(pt))
        wr = wintypes.RECT()
        u.GetWindowRect(hwnd, ctypes.byref(wr))
        return pt.x - wr.left, pt.y - wr.top

    def draw(dc, hwnd) -> None:
        cx, cy = cursor_in_window(hwnd)
        fill(dc, (0, 0, W, H), _BG)
        fill(dc, (0, 0, W, title_h), _TITLE_BG)
        fill(dc, (0, 0, W, S(3)), accent)
        g.SetBkMode(dc, 1)
        text(dc, "OPENCUE", (pad, S(3), W // 2, title_h), font(11, 700), _AMBER, winui.DT_SINGLELINE | winui.DT_VCENTER | winui.DT_NOPREFIX)
        hover_close = close_rect[0] <= cx < close_rect[2] and close_rect[1] <= cy < close_rect[3]
        if hover_close:
            fill(dc, close_rect, (150, 40, 34))
        text(dc, "×", close_rect, font(20, 300), _WHITE if hover_close else _GREY, winui.DT_CENTER | winui.DT_SINGLELINE | winui.DT_VCENTER)
        # Logo
        lx, ly = pad, title_h + S(28)
        for rx, ry, rw, rh, rc in logo:
            fill(dc, (lx + rx * unit, ly + ry * unit, lx + (rx + rw) * unit, ly + (ry + rh) * unit), rc)
        # Texte
        text(dc, title, (text_x, head_y, text_x + text_w, head_y + head_h), font(19, 700), _WHITE, winui.DT_WORDBREAK | winui.DT_NOPREFIX)
        text(dc, message, (text_x, msg_y, text_x + text_w, msg_y + msg_h), font(13), (190, 190, 198), winui.DT_WORDBREAK | winui.DT_NOPREFIX)
        text(dc, code_label, (text_x, code_y, text_x + code_label_w, code_y + S(24)), font(10, 700), _DIM, winui.DT_SINGLELINE | winui.DT_VCENTER | winui.DT_NOPREFIX)
        text(dc, code, (text_x + code_label_w, code_y, text_x + text_w, code_y + S(24)), font(14, 700, "Consolas"), accent, winui.DT_SINGLELINE | winui.DT_VCENTER | winui.DT_NOPREFIX)
        # Technische Angaben
        if lines:
            fill(dc, (pad - 1, box_y - 1, W - pad + 1, box_y + box_h + 1), _BORDER)
            fill(dc, (pad, box_y, W - pad, box_y + box_h), _BOX)
            for i, line in enumerate(lines):
                text(dc, line, (pad + S(12), box_y + S(10) + i * S(16), W - pad - S(12), box_y + S(10) + (i + 1) * S(16)), font(11, 400, "Consolas"), (196, 196, 204),
                     winui.DT_SINGLELINE | winui.DT_NOPREFIX | winui.DT_END_ELLIPSIS)
        # Knoepfe
        for b, l, t, r, bt in btn_rects:
            over = l <= cx < r and t <= cy < bt
            label = b.label
            if b.key == "@copy" and time.monotonic() < state["copied_until"]:
                label = "Copied ✓"
            if b.primary:
                fill(dc, (l, t, r, bt), _BTN_PRIMARY_HOVER if over else _AMBER)
                color = (20, 14, 0)
            else:
                fill(dc, (l, t, r, bt), _BTN_HOVER if over else _BTN)
                color = _WHITE
            text(dc, label, (l, t, r, bt), font(12.5, 600), color, winui.DT_CENTER | winui.DT_SINGLELINE | winui.DT_VCENTER | winui.DT_NOPREFIX)
        for edge in ((0, 0, W, 1), (0, H - 1, W, H), (0, 0, 1, H), (W - 1, 0, W, H)):
            fill(dc, edge, _BORDER)

    # ------------------------------------------------------------------ Aktionen
    def activate(hwnd, key: str) -> None:
        if key == "@copy":
            if winui.copy_text(clip_text(), hwnd):
                state["copied_until"] = time.monotonic() + 1.6
        elif key == "@folder":
            _open_path(log_path.parent if log_path else None)
        elif key == "@file":
            _open_path(log_path)
        else:
            result[0] = key
            u.DestroyWindow(hwnd)

    def primary_key() -> str:
        for b in primary_buttons:
            if b.primary:
                return b.key
        return primary_buttons[-1].key

    def wndproc(hwnd, msg, wparam, lparam):
        if msg == winui.WM_PAINT:
            ps = winui.PAINTSTRUCT()
            hdc = u.BeginPaint(hwnd, ctypes.byref(ps))
            mem = g.CreateCompatibleDC(hdc)
            bmp = g.CreateCompatibleBitmap(hdc, W, H)
            old = g.SelectObject(mem, bmp)
            try:
                draw(mem, hwnd)
                g.BitBlt(hdc, 0, 0, W, H, mem, 0, 0, winui.SRCCOPY)
            finally:
                g.SelectObject(mem, old)
                g.DeleteObject(bmp)
                g.DeleteDC(mem)
                u.EndPaint(hwnd, ctypes.byref(ps))
            return 0
        if msg == winui.WM_ERASEBKGND:
            return 1
        if msg == winui.WM_NCHITTEST:
            sx, sy = ctypes.c_short(lparam & 0xFFFF).value, ctypes.c_short((lparam >> 16) & 0xFFFF).value
            wr = wintypes.RECT()
            u.GetWindowRect(hwnd, ctypes.byref(wr))
            x_, y_ = sx - wr.left, sy - wr.top
            if y_ < title_h and not (close_rect[0] <= x_ < close_rect[2]):
                return winui.HTCAPTION                                   # Titelleiste: Fenster ziehen
            return winui.HTCLIENT
        if msg == winui.WM_LBUTTONUP:
            x_, y_ = ctypes.c_short(lparam & 0xFFFF).value, ctypes.c_short((lparam >> 16) & 0xFFFF).value
            if close_rect[0] <= x_ < close_rect[2] and close_rect[1] <= y_ < close_rect[3]:
                u.DestroyWindow(hwnd)
                return 0
            for b, l, t, r, bt in btn_rects:
                if l <= x_ < r and t <= y_ < bt:
                    activate(hwnd, b.key)
                    break
            return 0
        if msg == winui.WM_KEYDOWN:
            if wparam == winui.VK_ESCAPE:
                u.DestroyWindow(hwnd)
            elif wparam == winui.VK_RETURN:
                activate(hwnd, primary_key())
            elif wparam == 0x43 and u.GetKeyState(winui.VK_CONTROL) < 0:        # Strg+C
                activate(hwnd, "@copy")
            return 0
        if msg == winui.WM_TIMER:
            u.InvalidateRect(hwnd, None, False)                          # Hover und "Copied" nachziehen
            return 0
        if msg == winui.WM_NCDESTROY:
            state["done"] = True
            ctypes.windll.user32.PostQuitMessage(0)
        return u.DefWindowProcW(hwnd, msg, wparam, lparam)

    proc = winui.WNDPROC(wndproc)                                        # Referenz halten
    hinst = k.GetModuleHandleW(None)
    class_name = f"OpenCueError{next(_counter)}"
    cls = winui.WNDCLASSW()
    cls.lpfnWndProc = proc
    cls.hInstance = hinst
    cls.hCursor = u.LoadCursorW(None, 32512)
    cls.hbrBackground = None
    cls.lpszClassName = class_name
    u.RegisterClassW(ctypes.byref(cls))
    x0, y0 = winui.monitor_origin(W, H)
    # WS_POPUP; TOPMOST (ueber dem Startbild) + APPWINDOW (Taskleisten-Schaltflaeche: bei einem Absturz laesst sich das Fenster wiederfinden)
    hwnd = u.CreateWindowExW(0x8 | 0x40000, class_name, "OpenCue - " + title, 0x80000000, x0, y0, W, H, None, None, hinst, None)
    if not hwnd:
        raise RuntimeError("CreateWindowEx failed")
    u.ShowWindow(hwnd, 5)                                                # SW_SHOW
    u.SetForegroundWindow(hwnd)
    u.SetFocus(hwnd)
    u.SetTimer(hwnd, 1, 60, None)
    msg = wintypes.MSG()
    while u.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
        u.TranslateMessage(ctypes.byref(msg))
        u.DispatchMessageW(ctypes.byref(msg))
    for b_ in brushes.values():
        g.DeleteObject(b_)
    for f_ in fonts.values():
        g.DeleteObject(f_)
    g.DeleteDC(measure_dc)
    u.UnregisterClassW(class_name, hinst)


def _text_width(g, dc, f, label: str) -> int:
    import ctypes
    from ctypes import wintypes
    old = g.SelectObject(dc, f)
    size = wintypes.SIZE()
    g.GetTextExtentPoint32W(dc, label, len(label), ctypes.byref(size))
    g.SelectObject(dc, old)
    return size.cx


def _detail_lines(details: str, max_lines: int = 8, max_chars: int = 96) -> List[str]:
    """Die letzten Zeilen der technischen Angaben (bei einem Traceback ist das Wichtigste unten); lange Zeilen werden gekuerzt, vollstaendig steht alles im Kopierten."""
    rows = [line.rstrip() for line in (details or "").splitlines() if line.strip() and set(line.strip()) - set("~^")]      # ohne die Zeiger-Zeilen (~~^^^) von Python 3.13
    rows = rows[-max_lines:]
    return [r if len(r) <= max_chars else r[: max_chars - 1] + "…" for r in rows]


def _open_path(path: Optional[Path]) -> None:
    if not path:
        return
    try:
        target = Path(path)
        if not target.exists() and target.parent.exists():
            target = target.parent                                       # Log-Datei noch nicht da: wenigstens den Ordner
        os.startfile(str(target))                                        # type: ignore[attr-defined]  (nur Windows)
    except Exception:
        pass
