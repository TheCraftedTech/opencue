# Copyright (C) 2026 Samuel Zenker
# SPDX-License-Identifier: GPL-3.0-or-later
"""
winui.py
Gemeinsame Win32-Helfer fuer die kleinen, selbst gezeichneten Fenster, die schon vor der Oberflaeche da sein muessen (Fehlerfenster, app/error_window.py):
typisierte ctypes-Schnittstelle zu user32/gdi32/kernel32 (64-Bit-sicher), DPI-Skalierung, Farben, Monitor-Mitte, Zwischenablage.

Nur Standardbibliothek (ctypes) - kein tkinter, keine weiteren Pakete. Der Import kostet nichts; erst load() baut die Schnittstelle auf (nur unter Windows).
"""
from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes
from types import SimpleNamespace
from typing import Optional

LRESULT = ctypes.c_ssize_t
WPARAM = ctypes.c_size_t
LPARAM = ctypes.c_ssize_t
WNDPROC = ctypes.WINFUNCTYPE(LRESULT, wintypes.HWND, wintypes.UINT, WPARAM, LPARAM)

# Fensternachrichten und Konstanten, die die eigenen Fenster brauchen
WM_DESTROY, WM_CLOSE, WM_PAINT, WM_ERASEBKGND = 0x0002, 0x0010, 0x000F, 0x0014
WM_NCHITTEST, WM_KEYDOWN, WM_TIMER = 0x0084, 0x0100, 0x0113
WM_LBUTTONDOWN, WM_LBUTTONUP, WM_NCDESTROY = 0x0201, 0x0202, 0x0082
HTCLIENT, HTCAPTION = 1, 2
VK_RETURN, VK_ESCAPE, VK_CONTROL = 0x0D, 0x1B, 0x11
SRCCOPY = 0x00CC0020
DT_LEFT, DT_CENTER, DT_VCENTER, DT_SINGLELINE, DT_WORDBREAK, DT_CALCRECT, DT_NOPREFIX, DT_END_ELLIPSIS = 0x0, 0x1, 0x4, 0x20, 0x10, 0x400, 0x800, 0x8000


class WNDCLASSW(ctypes.Structure):
    _fields_ = [("style", wintypes.UINT), ("lpfnWndProc", WNDPROC), ("cbClsExtra", ctypes.c_int), ("cbWndExtra", ctypes.c_int),
                ("hInstance", wintypes.HINSTANCE), ("hIcon", wintypes.HANDLE), ("hCursor", wintypes.HANDLE),
                ("hbrBackground", wintypes.HBRUSH), ("lpszMenuName", wintypes.LPCWSTR), ("lpszClassName", wintypes.LPCWSTR)]


class PAINTSTRUCT(ctypes.Structure):
    _fields_ = [("hdc", wintypes.HDC), ("fErase", wintypes.BOOL), ("rcPaint", wintypes.RECT), ("fRestore", wintypes.BOOL),
                ("fIncUpdate", wintypes.BOOL), ("rgbReserved", ctypes.c_byte * 32)]


class MONITORINFO(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.DWORD), ("rcMonitor", wintypes.RECT), ("rcWork", wintypes.RECT), ("dwFlags", wintypes.DWORD)]


_api: Optional[SimpleNamespace] = None


def available() -> bool:
    return sys.platform == "win32"


def load() -> SimpleNamespace:
    """Typisierte Win32-Funktionen (einmal aufgebaut). Ohne richtige Typen wuerden 64-Bit-Handles abgeschnitten."""
    global _api
    if _api is not None:
        return _api
    u, g, k = ctypes.windll.user32, ctypes.windll.gdi32, ctypes.windll.kernel32
    H, UI, I, B, D = wintypes.HWND, wintypes.UINT, ctypes.c_int, wintypes.BOOL, wintypes.DWORD
    RECTP = ctypes.POINTER(wintypes.RECT)

    def sig(fn, args, res=None):
        fn.argtypes = args
        if res is not None:
            fn.restype = res

    sig(u.DefWindowProcW, [H, UI, WPARAM, LPARAM], LRESULT)
    sig(u.RegisterClassW, [ctypes.POINTER(WNDCLASSW)], wintypes.ATOM)
    sig(u.UnregisterClassW, [wintypes.LPCWSTR, wintypes.HINSTANCE], B)
    sig(u.LoadCursorW, [wintypes.HINSTANCE, ctypes.c_void_p], wintypes.HANDLE)
    sig(u.CreateWindowExW, [D, wintypes.LPCWSTR, wintypes.LPCWSTR, D, I, I, I, I, H, wintypes.HMENU, wintypes.HINSTANCE, wintypes.LPVOID], H)
    sig(u.BeginPaint, [H, ctypes.POINTER(PAINTSTRUCT)], wintypes.HDC)
    sig(u.EndPaint, [H, ctypes.POINTER(PAINTSTRUCT)])
    sig(u.FillRect, [wintypes.HDC, RECTP, wintypes.HBRUSH])
    sig(u.DrawTextW, [wintypes.HDC, wintypes.LPCWSTR, I, RECTP, UI], I)
    sig(u.SetTimer, [H, WPARAM, UI, wintypes.LPVOID])
    sig(u.KillTimer, [H, WPARAM])
    sig(u.InvalidateRect, [H, ctypes.c_void_p, B])
    sig(u.DestroyWindow, [H])
    sig(u.ShowWindow, [H, I])
    sig(u.IsWindowVisible, [H], B)
    sig(u.IsIconic, [H], B)
    sig(u.SetForegroundWindow, [H], B)
    sig(u.SetFocus, [H])
    sig(u.SwitchToThisWindow, [H, B])
    sig(u.GetWindowRect, [H, RECTP])
    sig(u.GetCursorPos, [ctypes.POINTER(wintypes.POINT)])
    sig(u.GetKeyState, [I], ctypes.c_short)
    sig(u.MonitorFromPoint, [wintypes.POINT, D], wintypes.HANDLE)
    sig(u.GetMonitorInfoW, [wintypes.HANDLE, ctypes.POINTER(MONITORINFO)])
    sig(u.SetLayeredWindowAttributes, [H, D, ctypes.c_ubyte, D])
    sig(u.OpenClipboard, [H], B)
    sig(u.SetClipboardData, [UI, ctypes.c_void_p], ctypes.c_void_p)
    sig(g.CreateSolidBrush, [D], wintypes.HBRUSH)
    sig(g.CreateCompatibleDC, [wintypes.HDC], wintypes.HDC)
    sig(g.CreateCompatibleBitmap, [wintypes.HDC, I, I], wintypes.HBITMAP)
    sig(g.SelectObject, [wintypes.HDC, wintypes.HANDLE], wintypes.HANDLE)
    sig(g.DeleteObject, [wintypes.HANDLE])
    sig(g.DeleteDC, [wintypes.HDC])
    sig(g.BitBlt, [wintypes.HDC, I, I, I, I, wintypes.HDC, I, I, D])
    sig(g.SetTextColor, [wintypes.HDC, D])
    sig(g.SetBkMode, [wintypes.HDC, I])
    sig(g.GetTextExtentPoint32W, [wintypes.HDC, wintypes.LPCWSTR, I, ctypes.POINTER(wintypes.SIZE)])
    sig(g.Ellipse, [wintypes.HDC, I, I, I, I])
    sig(g.Polygon, [wintypes.HDC, ctypes.c_void_p, I])
    sig(g.TextOutW, [wintypes.HDC, I, I, wintypes.LPCWSTR, I])
    sig(g.GetStockObject, [I], wintypes.HANDLE)
    g.CreateFontW.restype = wintypes.HANDLE
    sig(k.GlobalAlloc, [UI, ctypes.c_size_t], ctypes.c_void_p)
    sig(k.GlobalLock, [ctypes.c_void_p], ctypes.c_void_p)
    sig(k.GlobalUnlock, [ctypes.c_void_p])
    sig(k.GetModuleHandleW, [wintypes.LPCWSTR], wintypes.HINSTANCE)
    sig(u.GetClassNameW, [H, wintypes.LPWSTR, I], I)
    sig(u.GetWindowTextW, [H, wintypes.LPWSTR, I], I)
    sig(u.GetWindowThreadProcessId, [H, ctypes.POINTER(D)], D)
    _api = SimpleNamespace(user32=u, gdi32=g, kernel32=k)
    return _api


def rgb(color: tuple) -> int:
    return color[0] | (color[1] << 8) | (color[2] << 16)


def mix(a: tuple, b: tuple, t: float) -> tuple:
    t = max(0.0, min(1.0, t))
    return (int(a[0] + (b[0] - a[0]) * t), int(a[1] + (b[1] - a[1]) * t), int(a[2] + (b[2] - a[2]) * t))


def dpi_scale() -> float:
    """Skalierung des Bildschirms (1.0 = 100 %). Macht den Prozess DPI-bewusst, damit selbst gezeichnete Fenster scharf bleiben."""
    api = load()
    try:
        api.user32.SetProcessDPIAware()                                  # dieselbe Einstellung setzt pywebview spaeter selbst
        return max(1.0, api.user32.GetDpiForSystem() / 96.0)
    except Exception:
        return 1.0


def monitor_origin(width: int, height: int, near: Optional[tuple] = None) -> tuple:
    """Linke obere Ecke fuer ein Fenster dieser Groesse, mittig auf dem Monitor am Punkt `near` (sonst Hauptmonitor)."""
    api = load()
    point = wintypes.POINT(near[0], near[1]) if near else wintypes.POINT(0, 0)
    mon = api.user32.MonitorFromPoint(point, 2 if near else 1)           # 2 = naechster Monitor, 1 = Hauptmonitor
    info = MONITORINFO()
    info.cbSize = ctypes.sizeof(MONITORINFO)
    if mon and api.user32.GetMonitorInfoW(mon, ctypes.byref(info)):
        r = info.rcWork
        return r.left + (r.right - r.left - width) // 2, r.top + (r.bottom - r.top - height) // 2
    return (api.user32.GetSystemMetrics(0) - width) // 2, (api.user32.GetSystemMetrics(1) - height) // 2


def copy_text(text: str, hwnd=None) -> bool:
    """Text in die Zwischenablage (Unicode). True bei Erfolg."""
    api = load()
    u, k = api.user32, api.kernel32
    data = (text + "\0").encode("utf-16-le")
    handle = k.GlobalAlloc(0x0002, len(data))                            # GMEM_MOVEABLE
    if not handle:
        return False
    ptr = k.GlobalLock(handle)
    if not ptr:
        return False
    ctypes.memmove(ptr, data, len(data))
    k.GlobalUnlock(handle)
    if not u.OpenClipboard(hwnd):
        return False
    try:
        u.EmptyClipboard()
        return bool(u.SetClipboardData(13, handle))                      # CF_UNICODETEXT; die Zwischenablage uebernimmt den Speicher
    finally:
        u.CloseClipboard()


def window_title(hwnd) -> str:
    api = load()
    buf = ctypes.create_unicode_buffer(256)
    api.user32.GetWindowTextW(hwnd, buf, 256)
    return buf.value


def window_class(hwnd) -> str:
    api = load()
    buf = ctypes.create_unicode_buffer(128)
    api.user32.GetClassNameW(hwnd, buf, 128)
    return buf.value
