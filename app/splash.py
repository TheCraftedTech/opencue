# Copyright (C) 2026 Samuel Zenker
# SPDX-License-Identifier: GPL-3.0-or-later
"""
splash.py
Startbild von OpenCue: ein kleines, rahmenloses Fenster, das SOFORT beim Programmstart erscheint (noch bevor die schweren Module geladen
sind) und sich erst schliesst, wenn die Oberflaeche wirklich fertig aufgebaut ist.

Bewusst nur mit ctypes und GDI (Windows) gebaut: kein tkinter (ist im Build ausgeschlossen), keine weiteren Pakete, und der Import kostet
praktisch nichts. Das Fenster laeuft in einem eigenen Daemon-Thread mit eigener Nachrichtenschleife. Gezeichnet wird das Logo aus
static/icons/logo.svg (die <rect>-Elemente), ein weicher Lichtkegel, der wie im Intro-Film schwenkt und sich dann beruhigt, die Zeile
"DMX lighting control console" und ein Lade-Balken. Faellt irgendetwas aus (anderes Betriebssystem, kein Fenster moeglich), passiert
einfach nichts: das Programm startet dann wie bisher, nur ohne Startbild.

Benutzung:  splash = Splash(...); splash.start() ... splash.progress(42, "Loading ...") ... splash.close()   (progress() und close() duerfen aus jedem
Thread kommen). Der Balken zeigt echte Prozent (0-100) und darunter steht in einer kleinen Zeile, was gerade geschieht (immer Englisch); die Anzeige
steigt nur, nie zurueck, und gleitet weich zum neuen Wert. Die Stationen melden main.py und der Server ueber app/startup_progress.py.
Abschalten: `--no-splash` beim Start (main.py / OpenCue.exe) oder Umgebungsvariable OPENCUE_NO_SPLASH=1 (Tests, Aufnahmen).
Bedienung: das Fenster laesst sich an einer beliebigen Stelle ziehen; der Minus-Knopf oben rechts (oder ein Rechtsklick) versteckt es, das Programm laedt im Hintergrund weiter.
"""
from __future__ import annotations

import json
import math
import os
import re
import sys
import threading
import time
from pathlib import Path

from app import winui

_BG = (7, 7, 9)
_AMBER = (255, 176, 0)
_GREY = (132, 132, 140)
_W, _H = 640, 420                    # Groesse bei 100 % Skalierung (logische Pixel)
_FADE_IN = 0.18                      # Sekunden
_FADE_OUT = 0.28
_CONE_LAYERS = 14


def _rgb(c):
    return c[0] | (c[1] << 8) | (c[2] << 16)


def _mix(a, b, t):
    t = max(0.0, min(1.0, t))
    return (int(a[0] + (b[0] - a[0]) * t), int(a[1] + (b[1] - a[1]) * t), int(a[2] + (b[2] - a[2]) * t))


def _ease(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def _read_logo(path: Path):
    """Die gefuellten Rechtecke des Pixel-Logos (ohne das schwarze Hintergrund-Rechteck) als Liste (x, y, w, h, (r, g, b))."""
    rects = []
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return rects
    for m in re.finditer(r"<rect\b([^>]*)/>", text):
        attrs = dict(re.findall(r'([\w-]+)="([^"]*)"', m.group(1)))
        fill = attrs.get("fill", "")
        if not re.fullmatch(r"#[0-9a-fA-F]{6}", fill):
            continue
        w, h = float(attrs.get("width", 0)), float(attrs.get("height", 0))
        if w >= 64 and h >= 64:
            continue                                                     # Hintergrundflaeche
        rects.append((int(float(attrs.get("x", 0))), int(float(attrs.get("y", 0))), int(w), int(h),
                      (int(fill[1:3], 16), int(fill[3:5], 16), int(fill[5:7], 16))))
    return rects


def logo_path() -> Path:
    """Pfad zu static/icons/logo.svg (Quelltext und PyInstaller-Build)."""
    base = Path(getattr(sys, "_MEIPASS", None) or Path(__file__).resolve().parent.parent)
    for candidate in (base / "static" / "icons" / "logo.svg", base / "_internal" / "static" / "icons" / "logo.svg"):
        if candidate.is_file():
            return candidate
    return base / "static" / "icons" / "logo.svg"


def read_logo_rects():
    """Die Pixel-Rechtecke des Logos (auch vom Fehlerfenster genutzt)."""
    return _read_logo(logo_path())


def _saved_window_center():
    """Mitte des zuletzt benutzten Programmfensters (aus app_config.json), damit das Startbild auf demselben Monitor erscheint."""
    try:
        root = os.environ.get("OPENCUE_DATA_DIR", "").strip()
        base = Path(root) if root else Path(os.environ.get("LOCALAPPDATA", "")) / "OpenCue"
        data = json.loads((base / "config" / "app_config.json").read_text(encoding="utf-8"))
        x, y = data.get("window_x"), data.get("window_y")
        if isinstance(x, int) and isinstance(y, int):
            w = data.get("window_width") or 1200
            h = data.get("window_height") or 700
            if data.get("window_maximized"):
                return x + 200, y + 200                                  # maximiert: ein Punkt im Fenster genuegt, der Monitor ist gemeint
            return x + w // 2, y + h // 2
    except Exception:
        pass
    return None


class Splash:
    def __init__(self, logo_path: Path, subtitle: str, version: str = "") -> None:
        self._logo_path = logo_path
        self._subtitle = subtitle.upper()
        self._version = version
        self._thread: threading.Thread | None = None
        self._hwnd = None
        self._closing_at: float | None = None
        self._close_requested = threading.Event()
        self._dismissed = False                                          # per Minus-Knopf versteckt
        self._target = 0.0                                               # zuletzt gemeldeter Fortschritt in Prozent
        self._status = "Starting OpenCue"
        self._done = False
        self.shown = threading.Event()

    # ------------------------------------------------------------------ Steuerung
    def start(self) -> None:
        if sys.platform != "win32" or os.environ.get("OPENCUE_NO_SPLASH") or "--no-splash" in sys.argv[1:]:
            return
        self._thread = threading.Thread(target=self._run_safe, name="splash", daemon=True)
        self._thread.start()

    def progress(self, percent: float, text: str | None = None) -> None:
        """Fortschritt melden (aus jedem Thread): Prozent 0-100 und kurzer Text. Werte unter dem bisherigen werden ignoriert (der Balken laeuft nie zurueck)."""
        if self._done or percent < self._target:
            return
        self._target = min(100.0, float(percent))
        if text:
            self._status = text

    def close(self, wait: float = 1.0) -> None:
        """Blendet das Startbild aus und schliesst es (aus jedem Thread; kehrt nach hoechstens `wait` Sekunden zurueck)."""
        self._done = True
        self._close_requested.set()
        if self._thread is not None:
            self._thread.join(timeout=wait)

    # ------------------------------------------------------------------ Fenster
    def _run_safe(self) -> None:
        try:
            self._run()
        except Exception as exc:                                         # ein Startbild darf den Start nie verhindern
            print(f"[OpenCue] Startbild nicht moeglich: {exc}")

    def _run(self) -> None:
        import ctypes
        from ctypes import wintypes

        api = winui.load()                                               # typisierte Schnittstelle, gemeinsam mit dem Fehlerfenster
        user32, gdi32, kernel32 = api.user32, api.gdi32, api.kernel32
        WNDPROC, WNDCLASSW, PAINTSTRUCT, MONITORINFO = winui.WNDPROC, winui.WNDCLASSW, winui.PAINTSTRUCT, winui.MONITORINFO

        try:
            user32.SetProcessDPIAware()                                  # dieselbe Einstellung setzt pywebview spaeter selbst; so bleibt das Startbild scharf
            scale = max(1.0, user32.GetDpiForSystem() / 96.0)
        except Exception:
            scale = 1.0
        W, H = int(_W * scale), int(_H * scale)
        unit = max(2, int(4 * scale))                                    # Pixel-Logo: ganze Bildschirm-Pixel je Logo-Pixel (scharf)
        logo = _read_logo(self._logo_path)

        # --- Position: Mitte des zuletzt benutzten Fensters, sonst Hauptmonitor
        center = _saved_window_center()
        if center:
            mon = user32.MonitorFromPoint(wintypes.POINT(center[0], center[1]), 2)     # 2 = naechster Monitor
        else:
            mon = user32.MonitorFromPoint(wintypes.POINT(0, 0), 1)                     # 1 = Hauptmonitor
        mi = MONITORINFO()
        mi.cbSize = ctypes.sizeof(MONITORINFO)
        if mon and user32.GetMonitorInfoW(mon, ctypes.byref(mi)):
            r = mi.rcMonitor
            x, y = r.left + (r.right - r.left - W) // 2, r.top + (r.bottom - r.top - H) // 2
        else:
            x, y = (user32.GetSystemMetrics(0) - W) // 2, (user32.GetSystemMetrics(1) - H) // 2

        brushes: dict = {}

        def brush(c):
            b = brushes.get(c)
            if b is None:
                b = brushes[c] = gdi32.CreateSolidBrush(_rgb(c))
            return b

        fonts: dict = {}

        def font(px, weight):
            f = fonts.get((px, weight))
            if f is None:
                f = fonts[(px, weight)] = gdi32.CreateFontW(-px, 0, 0, 0, weight, 0, 0, 0, 1, 0, 0, 5, 0, "Segoe UI")      # 5 = ClearType
            return f

        def spaced(dc, text, cx, ty, px, weight, color, spacing):
            """Text mittig mit Buchstabenabstand (GDI kennt das nicht von allein)."""
            old = gdi32.SelectObject(dc, font(px, weight))
            gdi32.SetTextColor(dc, _rgb(color))
            widths = []
            for ch in text:
                s = wintypes.SIZE()
                gdi32.GetTextExtentPoint32W(dc, ch, 1, ctypes.byref(s))
                widths.append(s.cx)
            total = sum(widths) + spacing * (len(text) - 1)
            px_x = cx - total // 2
            for ch, w in zip(text, widths):
                gdi32.TextOutW(dc, int(px_x), ty, ch, 1)
                px_x += w + spacing
            gdi32.SelectObject(dc, old)

        started = time.monotonic()
        null_pen = gdi32.GetStockObject(8)
        logo_w = 64 * unit
        logo_x, logo_y = (W - logo_w) // 2, int(H * 0.085)
        apex = (W / 2, 0.0)
        button_rect = (W - int(46 * scale) - 1, 1, W - 1, int(32 * scale))     # Minus-Knopf, Fensterkoordinaten

        shown = [0.0]                                                   # angezeigter Fortschritt (gleitet zum gemeldeten Wert)
        state_t = [time.monotonic()]

        def draw(dc):
            t = time.monotonic() - started
            full = wintypes.RECT(0, 0, W, H)
            user32.FillRect(dc, ctypes.byref(full), brush(_BG))
            # --- Lichtkegel: Schwenk wie im Intro (links -> rechts), dann ruhig; weiche Kante durch gestaffelte Lagen
            lead = _ease(t / 0.7)
            angle = -17.0 + 26.0 * _ease((t - 0.2) / 2.0)
            if t > 2.4:
                angle = 9.0 * (1 - _ease((t - 2.4) / 1.2)) + 1.6 * math.sin((t - 3.6) * 0.9) * _ease((t - 3.6) / 1.5)
            theta = math.radians(angle)
            length = H * 1.25
            old_pen = gdi32.SelectObject(dc, null_pen)
            for k in range(_CONE_LAYERS):
                spread = 1.0 + 0.55 * (1 - k / (_CONE_LAYERS - 1))                 # aussen weiter und dunkler
                half_top, half_bottom = W * 0.025 * spread, W * 0.27 * spread
                color = _mix(_BG, (56, 40, 6), lead * (0.18 + 0.82 * (k + 1) / _CONE_LAYERS))
                pts = []
                for hx, depth in ((-half_top, 0.0), (half_top, 0.0), (half_bottom, length), (-half_bottom, length)):
                    px_ = apex[0] + hx * math.cos(theta) + depth * math.sin(theta)
                    py_ = apex[1] + depth * math.cos(theta) - hx * math.sin(theta)
                    pts.append((int(px_), int(py_)))
                arr = (ctypes.c_long * 8)(*[v for p in pts for v in p])
                gdi32.SelectObject(dc, brush(color))
                gdi32.Polygon(dc, arr, 4)
            gdi32.SelectObject(dc, old_pen)
            # --- Lampe oben
            lamp = brush(_mix(_BG, (255, 214, 120), lead))
            lr = int(7 * scale)
            gdi32.SelectObject(dc, null_pen)
            gdi32.SelectObject(dc, lamp)
            gdi32.Ellipse(dc, int(W / 2) - lr, -lr, int(W / 2) + lr, lr)
            # --- Logo (Pixel-Rechtecke), erscheint von oben nach unten
            reveal = _ease(t / 0.9) * 64.0
            for rx, ry, rw, rh, rc in logo:
                if ry > reveal:
                    continue
                rect = wintypes.RECT(logo_x + rx * unit, logo_y + ry * unit, logo_x + (rx + rw) * unit, logo_y + (ry + rh) * unit)
                user32.FillRect(dc, ctypes.byref(rect), brush(rc))
            gdi32.SetBkMode(dc, 1)                                      # TRANSPARENT
            # --- Zeile unter dem Logo
            sub_alpha = _ease((t - 1.2) / 0.8)
            spaced(dc, self._subtitle, W // 2, logo_y + logo_w + int(10 * scale), int(12 * scale), 700, _mix(_BG, _AMBER, sub_alpha), int(4.5 * scale))
            if self._version:
                spaced(dc, self._version, W - int(40 * scale), H - int(26 * scale), int(10 * scale), 400, _mix(_BG, _GREY, sub_alpha * 0.8), int(1 * scale))
            # --- Lade-Balken: echte Prozent. Die Anzeige gleitet weich zum gemeldeten Wert und kriecht zwischen zwei Meldungen etwas weiter (steht nie still)
            now = time.monotonic()
            dt = min(0.2, now - state_t[0])
            state_t[0] = now
            target = self._target
            if self._done:
                target = 100.0
            if shown[0] < target:
                shown[0] = min(target, shown[0] + max(0.25, (target - shown[0]) * 6.0) * dt)
            elif shown[0] < min(target + 3.0, 99.0):
                shown[0] += 0.8 * dt
            pct = max(0.0, min(100.0, shown[0]))
            track_w, track_h = int(W * 0.5), max(3, int(3 * scale))
            tx, ty = (W - track_w) // 2, H - int(66 * scale)
            rect = wintypes.RECT(tx, ty, tx + track_w, ty + track_h)
            user32.FillRect(dc, ctypes.byref(rect), brush((28, 28, 32)))
            fill = int(track_w * pct / 100.0)
            if fill > 0:
                rect = wintypes.RECT(tx, ty, tx + fill, ty + track_h)
                user32.FillRect(dc, ctypes.byref(rect), brush(_AMBER))
            bar_alpha = _ease((t - 0.1) / 0.35)                         # Balken und Statuszeile sind sofort da (nicht erst mit der Slogan-Zeile)
            spaced(dc, f"{int(pct)} %", tx + track_w + int(26 * scale), ty - int(5 * scale), int(11 * scale), 600, _mix(_BG, _GREY, bar_alpha), 0)
            spaced(dc, self._status, W // 2, ty + track_h + int(12 * scale), int(12 * scale), 400, _mix(_BG, (176, 176, 184), bar_alpha), 0)
            # --- Minus-Knopf oben rechts (versteckt das Startbild)
            bx0, by0, bx1, by1 = button_rect
            pt = wintypes.POINT()
            user32.GetCursorPos(ctypes.byref(pt))
            wr = wintypes.RECT()
            user32.GetWindowRect(self._hwnd, ctypes.byref(wr))
            cx_, cy_ = pt.x - wr.left, pt.y - wr.top
            hover = bx0 <= cx_ < bx1 and by0 <= cy_ < by1
            if hover:
                rect = wintypes.RECT(bx0, by0, bx1, by1)
                user32.FillRect(dc, ctypes.byref(rect), brush((44, 44, 50)))
            bar_w, bar_h = int(14 * scale), max(2, int(2 * scale))
            rect = wintypes.RECT((bx0 + bx1) // 2 - bar_w // 2, (by0 + by1) // 2, (bx0 + bx1) // 2 + bar_w // 2, (by0 + by1) // 2 + bar_h)
            user32.FillRect(dc, ctypes.byref(rect), brush((235, 235, 240) if hover else (150, 150, 158)))
            # --- feiner Rand
            for edge in (wintypes.RECT(0, 0, W, 1), wintypes.RECT(0, H - 1, W, H), wintypes.RECT(0, 0, 1, H), wintypes.RECT(W - 1, 0, W, H)):
                user32.FillRect(dc, ctypes.byref(edge), brush((34, 34, 38)))

        def wndproc(hwnd, msg, wparam, lparam):
            if msg == 0x000F:                                           # WM_PAINT
                ps = PAINTSTRUCT()
                hdc = user32.BeginPaint(hwnd, ctypes.byref(ps))
                mem = gdi32.CreateCompatibleDC(hdc)
                bmp = gdi32.CreateCompatibleBitmap(hdc, W, H)
                old = gdi32.SelectObject(mem, bmp)
                try:
                    draw(mem)
                    gdi32.BitBlt(hdc, 0, 0, W, H, mem, 0, 0, 0x00CC0020)       # SRCCOPY
                finally:
                    gdi32.SelectObject(mem, old)
                    gdi32.DeleteObject(bmp)
                    gdi32.DeleteDC(mem)
                    user32.EndPaint(hwnd, ctypes.byref(ps))
                return 0
            if msg == 0x0014:                                           # WM_ERASEBKGND
                return 1
            if msg == 0x0084:                                           # WM_NCHITTEST: Knopf = Klick, sonst Titelleiste (Fenster ziehen)
                sx, sy = ctypes.c_short(lparam & 0xFFFF).value, ctypes.c_short((lparam >> 16) & 0xFFFF).value
                wr = wintypes.RECT()
                user32.GetWindowRect(hwnd, ctypes.byref(wr))
                bx0, by0, bx1, by1 = button_rect
                if bx0 <= sx - wr.left < bx1 and by0 <= sy - wr.top < by1:
                    return 1                                            # HTCLIENT
                return 2                                                # HTCAPTION
            if msg == 0x0202:                                           # WM_LBUTTONUP (nur im Knopf, sonst ist alles Titelleiste)
                user32.ShowWindow(hwnd, 0)                              # SW_HIDE: das Programm laedt im Hintergrund weiter
                self._dismissed = True
                return 0
            if msg == 0x00A5:                                           # WM_NCRBUTTONUP: Rechtsklick versteckt es ebenfalls
                user32.ShowWindow(hwnd, 0)
                self._dismissed = True
                return 0
            if msg == 0x0113:                                           # WM_TIMER
                now = time.monotonic()
                if self._close_requested.is_set() and self._closing_at is None:
                    self._closing_at = now
                if self._closing_at is not None:
                    k = (now - self._closing_at) / _FADE_OUT
                    if k >= 1.0:
                        user32.DestroyWindow(hwnd)
                        return 0
                    user32.SetLayeredWindowAttributes(hwnd, 0, int(255 * (1 - k)), 2)
                elif now - started < _FADE_IN:
                    user32.SetLayeredWindowAttributes(hwnd, 0, int(255 * min(1.0, (now - started) / _FADE_IN)), 2)
                else:
                    user32.SetLayeredWindowAttributes(hwnd, 0, 255, 2)
                if not self._dismissed:
                    user32.InvalidateRect(hwnd, None, False)
                return 0
            if msg == 0x0082:                                           # WM_NCDESTROY
                user32.PostQuitMessage(0)
            return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

        proc = WNDPROC(wndproc)                                         # Referenz halten, sonst raeumt Python die Funktion ab
        hinst = kernel32.GetModuleHandleW(None)
        cls = WNDCLASSW()
        cls.lpfnWndProc = proc
        cls.hInstance = hinst
        cls.hCursor = user32.LoadCursorW(None, 32512)                   # IDC_ARROW
        cls.hbrBackground = None
        cls.lpszClassName = "OpenCueSplash"
        user32.RegisterClassW(ctypes.byref(cls))
        # WS_EX_TOPMOST | WS_EX_TOOLWINDOW (keine Taskleisten-Schaltflaeche) | WS_EX_LAYERED (Ein-/Ausblenden) | WS_EX_NOACTIVATE
        hwnd = user32.CreateWindowExW(0x8 | 0x80 | 0x80000 | 0x08000000, cls.lpszClassName, "OpenCue", 0x80000000, x, y, W, H, None, None, hinst, None)
        if not hwnd:
            return
        self._hwnd = hwnd
        user32.SetLayeredWindowAttributes(hwnd, 0, 0, 2)
        user32.ShowWindow(hwnd, 4)                                      # SW_SHOWNOACTIVATE
        user32.SetTimer(hwnd, 1, 33, None)
        self.shown.set()
        msg = wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))
        for b in brushes.values():
            gdi32.DeleteObject(b)
        for f in fonts.values():
            gdi32.DeleteObject(f)
        user32.UnregisterClassW(cls.lpszClassName, hinst)
