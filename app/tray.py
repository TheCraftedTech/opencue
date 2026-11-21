# Copyright (C) 2026 Samuel Zenker
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Symbol im Infobereich der Taskleiste (Tray) fuer den Server-Betrieb ohne Fenster (`--no-ui`, siehe app/cli.py): ohne Fenster gaebe es sonst keinen sichtbaren Hinweis, dass OpenCue
laeuft, und keinen Weg, es zu beenden. Klick / Doppelklick: Konsole im Browser oeffnen; Rechtsklick: Menue (Im Browser oeffnen, Log-Ordner oeffnen, Beenden).

Rein ctypes, eigene Bibliotheks-Objekte (kein Konflikt mit den getypten Funktionen in app/winui.py). Laeuft in einem eigenen Thread mit eigener Nachrichtenschleife. Windows meldet
das Ende der Sitzung (Abmelden / Herunterfahren) an dieses Fenster: dann wird `on_end_session` gerufen, damit OpenCue sauber beendet (Sicherung, Einstellungen).
"""
from __future__ import annotations

import ctypes
import logging
import sys
import threading
from ctypes import wintypes
from typing import Callable, Dict, Optional

logger = logging.getLogger("opencue.tray")

WM_DESTROY, WM_CLOSE, WM_NULL, WM_COMMAND = 0x0002, 0x0010, 0x0000, 0x0111
WM_QUERYENDSESSION, WM_ENDSESSION = 0x0011, 0x0016
WM_USER, WM_LBUTTONUP, WM_LBUTTONDBLCLK, WM_RBUTTONUP, WM_CONTEXTMENU = 0x0400, 0x0202, 0x0203, 0x0205, 0x007B
NIM_ADD, NIM_MODIFY, NIM_DELETE = 0, 1, 2
NIF_MESSAGE, NIF_ICON, NIF_TIP = 1, 2, 4
MF_STRING, MF_SEPARATOR, MF_GRAYED = 0, 0x800, 0x1
TPM_RIGHTBUTTON = 0x0002
IMAGE_ICON, LR_LOADFROMFILE, LR_DEFAULTSIZE = 1, 0x10, 0x40
ID_OPEN, ID_LOGS, ID_QUIT = 1, 2, 3
ID_URL_BASE = 100                                                           # Menuepunkte 100 ... : die Netzwerk-Adressen (ein Klick oeffnet sie im Browser)
CALLBACK_MESSAGE = WM_USER + 1
CLASS_NAME = "OpenCueTray"

LRESULT = ctypes.c_ssize_t
WNDPROC = ctypes.WINFUNCTYPE(LRESULT, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)


class WNDCLASSW(ctypes.Structure):
    _fields_ = [("style", wintypes.UINT), ("lpfnWndProc", WNDPROC), ("cbClsExtra", ctypes.c_int), ("cbWndExtra", ctypes.c_int), ("hInstance", wintypes.HINSTANCE),
                ("hIcon", wintypes.HICON), ("hCursor", wintypes.HANDLE), ("hbrBackground", wintypes.HBRUSH), ("lpszMenuName", wintypes.LPCWSTR), ("lpszClassName", wintypes.LPCWSTR)]


class GUID(ctypes.Structure):
    _fields_ = [("Data1", wintypes.DWORD), ("Data2", wintypes.WORD), ("Data3", wintypes.WORD), ("Data4", ctypes.c_ubyte * 8)]


class NOTIFYICONDATAW(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.DWORD), ("hWnd", wintypes.HWND), ("uID", wintypes.UINT), ("uFlags", wintypes.UINT), ("uCallbackMessage", wintypes.UINT), ("hIcon", wintypes.HICON),
                ("szTip", wintypes.WCHAR * 128), ("dwState", wintypes.DWORD), ("dwStateMask", wintypes.DWORD), ("szInfo", wintypes.WCHAR * 256), ("uTimeout", wintypes.UINT),
                ("szInfoTitle", wintypes.WCHAR * 64), ("dwInfoFlags", wintypes.DWORD), ("guidItem", GUID), ("hBalloonIcon", wintypes.HICON)]


class Tray:
    """`labels` liefert bei jedem Aufruf die Menuetexte {"open", "logs", "quit"} (Sprache der Konsole); `tooltip` ist der Hinweistext am Symbol (hoechstens 127 Zeichen)."""

    def __init__(self, tooltip: str, labels: Callable[[], Dict[str, str]], on_open: Callable[[], None], on_logs: Callable[[], None], on_quit: Callable[[], None],
                 on_end_session: Optional[Callable[[], None]] = None, icon_path: Optional[str] = None,
                 info: Optional[Callable[[], Dict[str, object]]] = None, on_url: Optional[Callable[[str], None]] = None) -> None:
        """info (optional): {"title": Text der Kopfzeile, "warning": Text einer Warnzeile oder "", "urls": [Adressen]} - steht oben im Menue (Anzeige der Netzwerk-Adressen, ungespeicherte Show)."""
        self.tooltip, self.labels, self.icon_path = tooltip[:127], labels, icon_path
        self._info, self._on_url = info, on_url
        self._urls: list = []
        self._on_open, self._on_logs, self._on_quit, self._on_end = on_open, on_logs, on_quit, on_end_session
        self.hwnd: Optional[int] = None
        self._thread: Optional[threading.Thread] = None
        self._ready = threading.Event()
        self._proc = None
        self._icon = None
        self._taskbar_created = 0
        self._u = self._s = self._k = None

    # ------------------------------------------------------------------------------------------------ Lebenszyklus
    def start(self, timeout: float = 5.0) -> bool:
        """Symbol anlegen (eigener Thread). True, wenn es da ist."""
        if sys.platform != "win32":
            return False
        self._thread = threading.Thread(target=self._run, name="tray", daemon=True)
        self._thread.start()
        self._ready.wait(timeout)
        return self.hwnd is not None

    def stop(self) -> None:
        if self.hwnd and self._u is not None:
            try:
                self._u.PostMessageW(self.hwnd, WM_CLOSE, 0, 0)
            except Exception:
                pass
        if self._thread is not None:
            self._thread.join(timeout=2.0)

    def set_tooltip(self, text: str) -> None:
        self.tooltip = text[:127]
        if self.hwnd:
            self._notify(NIM_MODIFY)

    # ------------------------------------------------------------------------------------------------ intern
    def _libs(self) -> None:
        u, s, k = ctypes.WinDLL("user32", use_last_error=True), ctypes.WinDLL("shell32", use_last_error=True), ctypes.WinDLL("kernel32", use_last_error=True)
        H, UI = wintypes.HWND, wintypes.UINT
        u.DefWindowProcW.argtypes, u.DefWindowProcW.restype = [H, UI, wintypes.WPARAM, wintypes.LPARAM], LRESULT
        u.RegisterClassW.argtypes = [ctypes.POINTER(WNDCLASSW)]
        u.CreateWindowExW.argtypes = [wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, H, wintypes.HMENU,
                                      wintypes.HINSTANCE, wintypes.LPVOID]
        u.CreateWindowExW.restype = H
        u.GetMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), H, UI, UI]
        u.TranslateMessage.argtypes = [ctypes.POINTER(wintypes.MSG)]
        u.DispatchMessageW.argtypes = [ctypes.POINTER(wintypes.MSG)]
        u.PostMessageW.argtypes = [H, UI, wintypes.WPARAM, wintypes.LPARAM]
        u.PostQuitMessage.argtypes = [ctypes.c_int]
        u.DestroyWindow.argtypes = [H]
        u.CreatePopupMenu.restype = wintypes.HMENU
        u.AppendMenuW.argtypes = [wintypes.HMENU, UI, ctypes.c_size_t, wintypes.LPCWSTR]
        u.SetMenuDefaultItem.argtypes = [wintypes.HMENU, UI, UI]
        u.TrackPopupMenu.argtypes = [wintypes.HMENU, UI, ctypes.c_int, ctypes.c_int, ctypes.c_int, H, ctypes.c_void_p]
        u.DestroyMenu.argtypes = [wintypes.HMENU]
        u.GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]
        u.SetForegroundWindow.argtypes = [H]
        u.LoadImageW.argtypes = [wintypes.HINSTANCE, wintypes.LPCWSTR, UI, ctypes.c_int, ctypes.c_int, UI]
        u.LoadImageW.restype = wintypes.HANDLE
        u.LoadIconW.argtypes = [wintypes.HINSTANCE, ctypes.c_void_p]
        u.LoadIconW.restype = wintypes.HANDLE
        u.DestroyIcon.argtypes = [wintypes.HANDLE]
        u.RegisterWindowMessageW.argtypes = [wintypes.LPCWSTR]
        u.RegisterWindowMessageW.restype = UI
        s.Shell_NotifyIconW.argtypes = [wintypes.DWORD, ctypes.POINTER(NOTIFYICONDATAW)]
        s.Shell_NotifyIconW.restype = wintypes.BOOL
        k.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
        k.GetModuleHandleW.restype = wintypes.HINSTANCE
        self._u, self._s, self._k = u, s, k

    def _load_icon(self):
        u = self._u
        if self.icon_path:
            icon = u.LoadImageW(None, self.icon_path, IMAGE_ICON, 0, 0, LR_LOADFROMFILE | LR_DEFAULTSIZE)
            if icon:
                return icon
        return u.LoadIconW(None, ctypes.c_void_p(32512))                      # IDI_APPLICATION

    def _notify(self, message: int) -> bool:
        data = NOTIFYICONDATAW()
        data.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
        data.hWnd, data.uID, data.uFlags, data.uCallbackMessage, data.hIcon = self.hwnd, 1, NIF_MESSAGE | NIF_ICON | NIF_TIP, CALLBACK_MESSAGE, self._icon
        data.szTip = self.tooltip
        return bool(self._s.Shell_NotifyIconW(message, ctypes.byref(data)))

    def _menu(self) -> None:
        u = self._u
        texts = self.labels()
        menu = u.CreatePopupMenu()
        self._urls = []
        try:
            info = self._info() if self._info is not None else {}
        except Exception:                                                     # noqa: BLE001 - das Menue muss immer aufgehen
            info = {}
        if info.get("title"):
            u.AppendMenuW(menu, MF_STRING | MF_GRAYED, 0, str(info["title"]))
        if info.get("warning"):
            u.AppendMenuW(menu, MF_STRING | MF_GRAYED, 0, str(info["warning"]))
        for index, address in enumerate(list(info.get("urls") or [])[:8]):
            self._urls.append(str(address))
            u.AppendMenuW(menu, MF_STRING, ID_URL_BASE + index, str(address))
        if info.get("title") or info.get("warning") or info.get("urls"):
            u.AppendMenuW(menu, MF_SEPARATOR, 0, None)
        u.AppendMenuW(menu, MF_STRING, ID_OPEN, texts.get("open", "Open OpenCue in the browser"))
        u.AppendMenuW(menu, MF_STRING, ID_LOGS, texts.get("logs", "Open log folder"))
        u.AppendMenuW(menu, MF_SEPARATOR, 0, None)
        u.AppendMenuW(menu, MF_STRING, ID_QUIT, texts.get("quit", "Quit OpenCue"))
        u.SetMenuDefaultItem(menu, ID_OPEN, 0)                                # fett: das tut ein Klick auf das Symbol
        point = wintypes.POINT()
        u.GetCursorPos(ctypes.byref(point))
        u.SetForegroundWindow(self.hwnd)                                      # sonst schliesst das Menue nicht, wenn man daneben klickt
        u.TrackPopupMenu(menu, TPM_RIGHTBUTTON, point.x, point.y, 0, self.hwnd, None)
        u.PostMessageW(self.hwnd, WM_NULL, 0, 0)
        u.DestroyMenu(menu)

    def _call(self, fn: Optional[Callable[[], None]]) -> None:
        if fn is None:
            return
        threading.Thread(target=self._safe, args=(fn,), name="tray-action", daemon=True).start()          # Rueckfragen (Beenden) blockieren die Nachrichtenschleife nicht

    @staticmethod
    def _safe(fn: Callable[[], None]) -> None:
        try:
            fn()
        except Exception:                                                       # noqa: BLE001
            logger.exception("[TRAY] action failed")

    def _wndproc(self, hwnd, message, wparam, lparam):
        u = self._u
        if message == CALLBACK_MESSAGE:
            if lparam in (WM_LBUTTONUP, WM_LBUTTONDBLCLK):
                self._call(self._on_open)
            elif lparam in (WM_RBUTTONUP, WM_CONTEXTMENU):
                self._menu()
            return 0
        if message == WM_COMMAND:
            command = wparam & 0xFFFF
            if ID_URL_BASE <= command < ID_URL_BASE + 8 and command - ID_URL_BASE < len(self._urls) and self._on_url is not None:
                address = self._urls[command - ID_URL_BASE]
                self._call(lambda: self._on_url(address))
                return 0
            self._call({ID_OPEN: self._on_open, ID_LOGS: self._on_logs, ID_QUIT: self._on_quit}.get(command))
            return 0
        if message == WM_QUERYENDSESSION:
            return 1
        if message == WM_ENDSESSION:
            if wparam and self._on_end is not None:
                self._safe(self._on_end)
            return 0
        if self._taskbar_created and message == self._taskbar_created:        # der Explorer wurde neu gestartet: Symbol wieder anlegen
            self._notify(NIM_ADD)
            return 0
        if message == WM_CLOSE:
            u.DestroyWindow(hwnd)
            return 0
        if message == WM_DESTROY:
            self._notify(NIM_DELETE)
            u.PostQuitMessage(0)
            return 0
        return u.DefWindowProcW(hwnd, message, wparam, lparam)

    def _run(self) -> None:
        try:
            self._libs()
            u = self._u
            self._proc = WNDPROC(self._wndproc)
            instance = self._k.GetModuleHandleW(None)
            wc = WNDCLASSW()
            wc.lpfnWndProc, wc.hInstance, wc.lpszClassName = self._proc, instance, CLASS_NAME
            u.RegisterClassW(ctypes.byref(wc))
            hwnd = u.CreateWindowExW(0, CLASS_NAME, "OpenCue", 0x80000000, 0, 0, 0, 0, None, None, instance, None)        # WS_POPUP, nie gezeigt
            if not hwnd:
                raise OSError("tray window could not be created")
            self.hwnd = hwnd
            self._taskbar_created = u.RegisterWindowMessageW("TaskbarCreated")
            self._icon = self._load_icon()
            if not self._notify(NIM_ADD):
                logger.warning("[TRAY] The tray icon could not be added")
            self._ready.set()
            msg = wintypes.MSG()
            while u.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
                u.TranslateMessage(ctypes.byref(msg))
                u.DispatchMessageW(ctypes.byref(msg))
        except Exception:                                                       # noqa: BLE001
            logger.exception("[TRAY] Tray icon thread failed")
        finally:
            self.hwnd = None
            self._ready.set()
