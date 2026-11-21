# Copyright (C) 2026 Samuel Zenker
# SPDX-License-Identifier: GPL-3.0-or-later
"""
rawkeys.py
Tasten EINER bestimmten Tastatur (z. B. ein USB-Macropad neben der Haupttastatur) als Ausloeser der eigenen Tastaturbelegung (app/hotkeys.py).

Der Browser sieht nicht, von welcher Tastatur ein Tastendruck kommt. Unter Windows meldet die "Raw Input"-Schnittstelle jeden Tastendruck mit dem Geraet,
das ihn gesendet hat - ohne zusaetzliche Bibliothek (nur ctypes). Ein eigener Thread legt dafuer ein unsichtbares Nachrichtenfenster an und meldet sich fuer
Tastaturen an (auch im Hintergrund: das Macropad geht, wenn OpenCue nicht im Vordergrund ist).

Datenschutz: Der Mithoerer laeuft NUR, solange es einen eingeschalteten Eintrag fuer eine bestimmte Tastatur gibt oder gerade eine Taste aufgenommen wird.
Er ordnet nur Tastendruecke der Tastaturen zu, die in der Liste stehen; alles andere wird sofort verworfen und nie gespeichert oder protokolliert.

Grenze: Raw Input BEOBACHTET nur - der Tastendruck kommt trotzdem auch bei dem Programm an, das gerade den Fokus hat (ein Leerzeichen in einem Textfeld, ein Klick auf
einen fokussierten Knopf). Fuer ein Macropad also Tasten waehlen, die sonst nichts tun (F13-F24, Ziffernblock, Medientasten ...).

Die Tasten tragen dieselben Namen wie im Browser-Teil (static/js/hotkeys.js): Modifikatoren Ctrl, Alt, Shift, Meta, dann die Haupttasten alphabetisch sortiert, z. B.
"Ctrl+H+J", "Space", "Num1", "F13". Ein Geraet wird ueber seinen Modell-Schluessel erkannt (Teil des Geraetepfads, z. B. "VID_258A&PID_002A&MI_00"): das bleibt
gleich, auch wenn das Macropad an einem anderen USB-Anschluss steckt.
"""

from __future__ import annotations

import asyncio
import logging
import sys
import threading
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("opencue.rawkeys")

IS_WINDOWS = sys.platform == "win32"
MOD_ORDER = ["Ctrl", "Alt", "Shift", "Meta"]
CHORD_WAIT = 0.18                       # so lange warten, wenn es eine laengere Kombination mit denselben Tasten gibt (Strg+H wartet auf ein moegliches Strg+H+J)
MAX_KEYS = 4

# ---------------------------------------------------------------------------- Tastennamen (Scancode -> Name wie im Browser)
_SCAN: Dict[int, str] = {0x01: "Esc", 0x0C: "-", 0x0D: "=", 0x0E: "Backspace", 0x0F: "Tab", 0x1A: "[", 0x1B: "]", 0x1C: "Enter", 0x27: ";", 0x28: "'", 0x29: "`", 0x2B: "\\",
                         0x33: ",", 0x34: ".", 0x35: "/", 0x37: "NumMul", 0x39: "Space", 0x3A: "CapsLock", 0x45: "NumLock", 0x46: "ScrollLock", 0x4A: "NumSub", 0x4E: "NumAdd",
                         0x53: "NumDec", 0x56: "<", 0x57: "F11", 0x58: "F12"}
for _i, _c in enumerate("1234567890"):
    _SCAN[0x02 + _i] = _c
for _i, _c in enumerate("QWERTYUIOP"):
    _SCAN[0x10 + _i] = _c
for _i, _c in enumerate("ASDFGHJKL"):
    _SCAN[0x1E + _i] = _c
for _i, _c in enumerate("ZXCVBNM"):
    _SCAN[0x2C + _i] = _c
for _i in range(10):
    _SCAN[0x3B + _i] = f"F{_i + 1}"
for _sc, _n in {0x47: 7, 0x48: 8, 0x49: 9, 0x4B: 4, 0x4C: 5, 0x4D: 6, 0x4F: 1, 0x50: 2, 0x51: 3, 0x52: 0}.items():
    _SCAN[_sc] = f"Num{_n}"
_SCAN_E0: Dict[int, str] = {0x1C: "NumEnter", 0x35: "NumDiv", 0x47: "Home", 0x48: "Up", 0x49: "PageUp", 0x4B: "Left", 0x4D: "Right", 0x4F: "End", 0x50: "Down", 0x51: "PageDown",
                            0x52: "Insert", 0x53: "Delete", 0x37: "PrintScreen"}
_MODS: Dict[Tuple[int, bool], str] = {(0x1D, False): "Ctrl", (0x1D, True): "Ctrl", (0x2A, False): "Shift", (0x36, False): "Shift", (0x38, False): "Alt", (0x38, True): "Alt",
                                      (0x5B, True): "Meta", (0x5C, True): "Meta"}


def key_name(make: int, e0: bool, vkey: int) -> Tuple[str, bool]:
    """(Name, ist_Modifikator) der Taste - ("", False) fuer Unbekanntes und Windows' Schein-Tasten."""
    if (make, e0) in _MODS:
        return _MODS[(make, e0)], True
    if 0x7C <= vkey <= 0x87:                                   # F13-F24: die Scancodes sind je Hersteller verschieden, der virtuelle Code nicht
        return f"F{vkey - 0x7B + 12}", False
    if e0:
        return _SCAN_E0.get(make, ""), False
    return _SCAN.get(make, ""), False


def combo_of(mods: Set[str], keys: Set[str]) -> str:
    return "+".join([m for m in MOD_ORDER if m in mods] + sorted(keys))


def split_combo(combo: str) -> Tuple[frozenset, frozenset]:
    mods, keys = set(), set()
    for part in str(combo).split("+"):
        if not part:
            continue
        (mods if part in MOD_ORDER else keys).add(part)
    return frozenset(mods), frozenset(keys)


def model_key(path: str) -> str:
    """Modell-Schluessel aus dem Geraetepfad: `\\\\?\\HID#VID_258A&PID_002A&MI_00#7&abc&0&0000#{guid}` -> `VID_258A&PID_002A&MI_00`."""
    parts = str(path).split("#")
    return parts[1] if len(parts) > 2 else str(path)


# ---------------------------------------------------------------------------- Windows: Raw Input
if IS_WINDOWS:
    import ctypes
    from ctypes import wintypes

    _user32 = ctypes.WinDLL("user32", use_last_error=True)
    _kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    try:
        _hid = ctypes.WinDLL("hid", use_last_error=True)
    except OSError:
        _hid = None

    LRESULT = ctypes.c_ssize_t
    WNDPROC = ctypes.WINFUNCTYPE(LRESULT, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)

    class _WNDCLASS(ctypes.Structure):
        _fields_ = [("style", wintypes.UINT), ("lpfnWndProc", WNDPROC), ("cbClsExtra", ctypes.c_int), ("cbWndExtra", ctypes.c_int), ("hInstance", wintypes.HINSTANCE),
                    ("hIcon", wintypes.HANDLE), ("hCursor", wintypes.HANDLE), ("hbrBackground", wintypes.HANDLE), ("lpszMenuName", wintypes.LPCWSTR), ("lpszClassName", wintypes.LPCWSTR)]

    class _RAWINPUTDEVICE(ctypes.Structure):
        _fields_ = [("usUsagePage", wintypes.USHORT), ("usUsage", wintypes.USHORT), ("dwFlags", wintypes.DWORD), ("hwndTarget", wintypes.HWND)]

    class _RAWINPUTHEADER(ctypes.Structure):
        _fields_ = [("dwType", wintypes.DWORD), ("dwSize", wintypes.DWORD), ("hDevice", wintypes.HANDLE), ("wParam", wintypes.WPARAM)]

    class _RAWKEYBOARD(ctypes.Structure):
        _fields_ = [("MakeCode", wintypes.USHORT), ("Flags", wintypes.USHORT), ("Reserved", wintypes.USHORT), ("VKey", wintypes.USHORT), ("Message", wintypes.UINT), ("ExtraInformation", wintypes.ULONG)]

    class _RAWINPUTKEY(ctypes.Structure):
        _fields_ = [("header", _RAWINPUTHEADER), ("keyboard", _RAWKEYBOARD)]

    class _RAWINPUTDEVICELIST(ctypes.Structure):
        _fields_ = [("hDevice", wintypes.HANDLE), ("dwType", wintypes.DWORD)]

    _user32.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    _user32.DefWindowProcW.restype = LRESULT
    _user32.CreateWindowExW.argtypes = [wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                        wintypes.HWND, wintypes.HMENU, wintypes.HINSTANCE, wintypes.LPVOID]
    _user32.CreateWindowExW.restype = wintypes.HWND
    _user32.RegisterClassW.argtypes = [ctypes.POINTER(_WNDCLASS)]
    _user32.RegisterClassW.restype = wintypes.ATOM
    _user32.RegisterRawInputDevices.argtypes = [ctypes.POINTER(_RAWINPUTDEVICE), wintypes.UINT, wintypes.UINT]
    _user32.RegisterRawInputDevices.restype = wintypes.BOOL
    _user32.GetRawInputData.argtypes = [wintypes.HANDLE, wintypes.UINT, wintypes.LPVOID, ctypes.POINTER(wintypes.UINT), wintypes.UINT]
    _user32.GetRawInputData.restype = wintypes.UINT
    _user32.GetRawInputDeviceInfoW.argtypes = [wintypes.HANDLE, wintypes.UINT, wintypes.LPVOID, ctypes.POINTER(wintypes.UINT)]
    _user32.GetRawInputDeviceInfoW.restype = wintypes.UINT
    _user32.GetRawInputDeviceList.argtypes = [ctypes.POINTER(_RAWINPUTDEVICELIST), ctypes.POINTER(wintypes.UINT), wintypes.UINT]
    _user32.GetRawInputDeviceList.restype = wintypes.UINT
    _user32.GetMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT]
    _user32.GetMessageW.restype = ctypes.c_int
    _user32.DispatchMessageW.argtypes = [ctypes.POINTER(wintypes.MSG)]
    _user32.PostThreadMessageW.argtypes = [wintypes.DWORD, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    _user32.DestroyWindow.argtypes = [wintypes.HWND]
    _kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
    _kernel32.GetModuleHandleW.restype = wintypes.HINSTANCE
    _kernel32.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
    _kernel32.CreateFileW.restype = wintypes.HANDLE
    _kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    if _hid:
        for _fn in (_hid.HidD_GetManufacturerString, _hid.HidD_GetProductString):
            _fn.argtypes = [wintypes.HANDLE, wintypes.LPVOID, wintypes.ULONG]
            _fn.restype = ctypes.c_ubyte

    WM_INPUT, WM_QUIT = 0x00FF, 0x0012
    RIDEV_INPUTSINK, RID_INPUT, RIM_TYPEKEYBOARD, RIDI_DEVICENAME = 0x100, 0x10000003, 1, 0x20000007
    RI_KEY_BREAK, RI_KEY_E0, RI_KEY_E1 = 1, 2, 4
    HWND_MESSAGE = wintypes.HWND(-3)


def _handle_path(handle: Any) -> str:
    size = wintypes.UINT(0)
    _user32.GetRawInputDeviceInfoW(handle, RIDI_DEVICENAME, None, ctypes.byref(size))
    if not size.value:
        return ""
    buf = ctypes.create_unicode_buffer(size.value + 1)
    if _user32.GetRawInputDeviceInfoW(handle, RIDI_DEVICENAME, buf, ctypes.byref(size)) in (0xFFFFFFFF, 0):
        return ""
    return buf.value


def _product_name(path: str) -> str:
    """Name aus dem Geraet ("Hersteller Produkt"); leer, wenn es keinen gibt (PS/2- und Laptop-Tastaturen)."""
    if not (IS_WINDOWS and _hid and path):
        return ""
    handle = _kernel32.CreateFileW(path, 0, 3, None, 3, 0, None)
    if handle in (None, wintypes.HANDLE(-1).value, -1):
        return ""
    try:
        parts = []
        for fn in (_hid.HidD_GetManufacturerString, _hid.HidD_GetProductString):
            buf = ctypes.create_unicode_buffer(128)
            if fn(wintypes.HANDLE(handle), buf, ctypes.sizeof(buf)) and buf.value.strip():
                parts.append(buf.value.strip())
        text = " ".join(parts)
        return text if len(parts) < 2 or parts[0].lower() not in parts[1].lower() else parts[1]
    except Exception:                                          # noqa: BLE001 - ein Name ist nur eine Hilfe
        return ""
    finally:
        _kernel32.CloseHandle(wintypes.HANDLE(handle))


class RawKeys:
    """Der Mithoerer fuer Tasten einzelner Tastaturen (siehe Moduldokumentation)."""

    def __init__(self) -> None:
        self.available = IS_WINDOWS
        self.error = "" if IS_WINDOWS else "Tasten einzelner Tastaturen gibt es nur unter Windows."
        self.on_fire: Optional[Callable[[Dict[str, Any]], Any]] = None            # (Eintrag) -> Coroutine (Befehl ausloesen)
        self.on_record: Optional[Callable[[str, Dict[str, Any]], Any]] = None     # ("live"|"done", {device, name, keys}) -> Coroutine
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._thread_id = 0
        self._hwnd = None
        self._wndproc = None
        self._lock = threading.Lock()
        self._table: Dict[str, Dict[Tuple[frozenset, frozenset], Dict[str, Any]]] = {}   # Modell -> (Modifikatoren, Tasten) -> Eintrag
        self._recording = False
        self._down: Dict[str, Set[str]] = {}                   # Modell -> gedrueckte Tasten (inkl. Modifikatoren)
        self._rec_device = ""                                  # Aufnahme: das Geraet, das die Aufnahme begonnen hat
        self._rec_mods: Set[str] = set()
        self._rec_keys: List[str] = []
        self._pending: Dict[str, threading.Timer] = {}
        self._names: Dict[str, str] = {}                       # Modell -> Name (Cache)
        self._paths: Dict[Any, str] = {}                       # Handle -> Pfad (Cache)

    # ------------------------------------------------------------------ Einrichten
    def attach(self, loop: asyncio.AbstractEventLoop) -> None:
        self.loop = loop

    def configure(self, hotkeys: List[Dict[str, Any]], recording: Optional[bool] = None) -> None:
        """Soll-Zustand setzen: nur Eintraege fuer bestimmte Tastaturen zaehlen; laeuft nur, wenn es welche gibt oder aufgenommen wird."""
        table: Dict[str, Dict[Tuple[frozenset, frozenset], Dict[str, Any]]] = {}
        for entry in hotkeys or []:
            device = str(entry.get("device") or "")
            if device and entry.get("enabled", True) and entry.get("keys") and str(entry.get("command") or "").strip():
                table.setdefault(device, {})[split_combo(entry["keys"])] = entry
        with self._lock:
            self._table = table
            if recording is not None:
                self._recording = bool(recording)
                self._rec_device, self._rec_mods, self._rec_keys = "", set(), []
            wanted = bool(self._table) or self._recording
        if wanted:
            self._start()
        else:
            self._stop()

    @property
    def running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def devices(self) -> List[Dict[str, str]]:
        """Alle angeschlossenen Tastaturen (id = Modell-Schluessel, name)."""
        out: List[Dict[str, str]] = []
        if not IS_WINDOWS:
            return out
        count = wintypes.UINT(0)
        size = ctypes.sizeof(_RAWINPUTDEVICELIST)
        if _user32.GetRawInputDeviceList(None, ctypes.byref(count), size) == 0xFFFFFFFF or not count.value:
            return out
        items = (_RAWINPUTDEVICELIST * count.value)()
        got = _user32.GetRawInputDeviceList(items, ctypes.byref(count), size)
        if got == 0xFFFFFFFF:
            return out
        seen = set()
        for item in items[:got]:
            if item.dwType != RIM_TYPEKEYBOARD:
                continue
            path = _handle_path(item.hDevice)
            model = model_key(path)
            if not model or model in seen:
                continue
            seen.add(model)
            out.append({"id": model, "name": self._name_for(model, path)})
        return out

    def _name_for(self, model: str, path: str) -> str:
        if model not in self._names:
            self._names[model] = _product_name(path)
        return self._names[model]

    # ------------------------------------------------------------------ Thread mit Nachrichtenfenster
    def _start(self) -> None:
        if not IS_WINDOWS or not self.available or self.running:
            return
        ready = threading.Event()
        result: Dict[str, Any] = {}
        self._thread = threading.Thread(target=self._run, args=(ready, result), name="opencue-rawkeys", daemon=True)
        self._thread.start()
        ready.wait(3.0)
        if result.get("error"):
            self.error = result["error"]
            logger.warning("[RAWKEYS] %s", self.error)
        else:
            self.error = ""
            logger.info("[RAWKEYS] Mithoeren fuer einzelne Tastaturen gestartet")

    def _stop(self) -> None:
        thread = self._thread
        if not thread or not thread.is_alive():
            self._thread = None
            return
        _user32.PostThreadMessageW(self._thread_id, WM_QUIT, 0, 0)
        thread.join(2.0)
        self._thread = None
        for timer in self._pending.values():
            timer.cancel()
        self._pending.clear()
        self._down.clear()
        logger.info("[RAWKEYS] Mithoeren beendet")

    def _run(self, ready: threading.Event, result: Dict[str, Any]) -> None:
        self._thread_id = _kernel32.GetCurrentThreadId()

        def proc(hwnd, msg, wparam, lparam):
            if msg == WM_INPUT:
                try:
                    self._on_input(lparam)
                except Exception:                              # noqa: BLE001 - ein defektes Ereignis darf den Mithoerer nie beenden
                    logger.debug("[RAWKEYS] Ereignis nicht auswertbar", exc_info=True)
            return _user32.DefWindowProcW(hwnd, msg, wparam, lparam)

        if self._wndproc is None:                              # nur EINMAL anlegen: die Fensterklasse behaelt den Zeiger darauf, auch nach dem Beenden des Threads
            self._wndproc = WNDPROC(proc)
        cls = _WNDCLASS()
        cls.lpfnWndProc = self._wndproc
        cls.hInstance = _kernel32.GetModuleHandleW(None)
        cls.lpszClassName = "OpenCueRawKeys"
        _user32.RegisterClassW(ctypes.byref(cls))                # ein zweites Mal schlaegt es fehl (Klasse existiert) - das ist in Ordnung
        hwnd = _user32.CreateWindowExW(0, "OpenCueRawKeys", "OpenCue raw keys", 0, 0, 0, 0, 0, HWND_MESSAGE, None, cls.hInstance, None)
        if not hwnd:
            result["error"] = f"Message window not possible (error {ctypes.get_last_error()})"
            ready.set()
            return
        device = _RAWINPUTDEVICE(1, 6, RIDEV_INPUTSINK, hwnd)          # Generic Desktop / Keyboard, auch im Hintergrund
        if not _user32.RegisterRawInputDevices(ctypes.byref(device), 1, ctypes.sizeof(device)):
            result["error"] = f"Raw Input not available (error {ctypes.get_last_error()})"
            _user32.DestroyWindow(hwnd)
            ready.set()
            return
        self._hwnd = hwnd
        ready.set()
        msg = wintypes.MSG()
        while _user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            _user32.DispatchMessageW(ctypes.byref(msg))
        device.dwFlags = 0x1                                           # RIDEV_REMOVE
        device.hwndTarget = None
        _user32.RegisterRawInputDevices(ctypes.byref(device), 1, ctypes.sizeof(device))
        _user32.DestroyWindow(hwnd)
        self._hwnd = None

    # ------------------------------------------------------------------ Tastendruck
    def _on_input(self, lparam: int) -> None:
        size = wintypes.UINT(0)
        header = ctypes.sizeof(_RAWINPUTHEADER)
        _user32.GetRawInputData(lparam, RID_INPUT, None, ctypes.byref(size), header)
        if not size.value:
            return
        buf = ctypes.create_string_buffer(size.value)
        if _user32.GetRawInputData(lparam, RID_INPUT, buf, ctypes.byref(size), header) != size.value:
            return
        raw = _RAWINPUTKEY.from_buffer_copy(buf.raw[:ctypes.sizeof(_RAWINPUTKEY)])
        if raw.header.dwType != RIM_TYPEKEYBOARD:
            return
        key = raw.keyboard
        if key.VKey == 0xFF or key.Flags & RI_KEY_E1:                  # Overrun / Pause
            return
        handle = raw.header.hDevice
        path = self._paths.get(handle)
        if path is None:
            path = self._paths[handle] = _handle_path(handle) if handle else ""
        model = model_key(path) if path else ""
        name, is_mod = key_name(key.MakeCode, bool(key.Flags & RI_KEY_E0), key.VKey)
        if name:
            self.feed(model, name, is_mod, not (key.Flags & RI_KEY_BREAK), path)

    def feed(self, model: str, name: str, is_mod: bool, down: bool, path: str = "") -> None:
        """Ein Tastenereignis eines Geraets verarbeiten (auch fuer Tests: ohne Windows-Nachrichten)."""
        with self._lock:
            recording = self._recording
            table = self._table.get(model)
            if not recording and not table:
                return                                                  # eine Tastatur, die in der Liste nicht vorkommt: sofort verworfen
            pressed = self._down.setdefault(model, set())
            if down:
                if name in pressed:
                    return                                              # Dauerfeuer
                pressed.add(name)
            else:
                pressed.discard(name)
            mods = {k for k in pressed if k in MOD_ORDER}
            keys = {k for k in pressed if k not in MOD_ORDER}
            if recording:
                self._feed_record(model, name, is_mod, down, mods, keys, path)
                return
            if not down or is_mod:
                return
            entry = table.get((frozenset(mods), frozenset(keys)))
            timer = self._pending.pop(model, None)
            if timer:
                timer.cancel()
            if not entry:
                return
            longer = any(m == frozenset(mods) and k > frozenset(keys) for (m, k) in table)
            if longer:
                timer = threading.Timer(CHORD_WAIT, self._fire_if_unchanged, (model, entry))
                timer.daemon = True
                self._pending[model] = timer
                timer.start()
                return
        self._fire(entry)

    def _fire_if_unchanged(self, model: str, entry: Dict[str, Any]) -> None:
        """Nach der Wartezeit: kam keine weitere Taste dazu (jeder Druck wuerde diesen Timer ersetzen), gilt die kuerzere Kombination."""
        with self._lock:
            if self._pending.get(model) is not threading.current_thread():
                return
            self._pending.pop(model, None)
        self._fire(entry)

    def _fire(self, entry: Dict[str, Any]) -> None:
        if self.on_fire and self.loop:
            asyncio.run_coroutine_threadsafe(self.on_fire(dict(entry)), self.loop)

    def _feed_record(self, model: str, name: str, is_mod: bool, down: bool, mods: Set[str], keys: Set[str], path: str) -> None:
        """Aufnahme: vom ersten Druck an bis alle Tasten dieses Geraets los sind; das Geraet des ersten Drucks gilt."""
        pressed = self._down.get(model, set())
        if self._rec_device and model != self._rec_device:
            return
        if down:
            if not self._rec_device:
                self._rec_device = model
            self._rec_mods |= mods
            if not is_mod and name not in self._rec_keys and len(self._rec_keys) < MAX_KEYS:
                self._rec_keys.append(name)
            self._emit_record("live", model, path)
            return
        if not pressed:
            done = self._rec_device == model and bool(self._rec_keys)
            combo = combo_of(self._rec_mods, set(self._rec_keys))
            if done:
                self._rec_device, self._rec_mods, self._rec_keys = "", set(), []
                self._emit_record("done", model, path, combo)
            else:
                self._rec_device, self._rec_mods, self._rec_keys = "", set(), []

    def _emit_record(self, kind: str, model: str, path: str, combo: Optional[str] = None) -> None:
        if not (self.on_record and self.loop):
            return
        name = self._name_for(model, path) if (path or model in self._names) else self._names.get(model, "")
        payload = {"device": model, "name": name, "keys": combo if combo is not None else combo_of(self._rec_mods, set(self._rec_keys))}
        asyncio.run_coroutine_threadsafe(self.on_record(kind, payload), self.loop)

    def shutdown(self) -> None:
        self._stop()


rawkeys = RawKeys()
