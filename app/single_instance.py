# Copyright (C) 2026 Samuel Zenker
# SPDX-License-Identifier: GPL-3.0-or-later
"""
single_instance.py
Nur ein OpenCue je Datenordner zugleich. Beim Start - noch bevor Server, Port und Fenster angefasst werden - wird ein benannter Windows-Mutex angelegt. Gibt es ihn
schon, laeuft bereits ein OpenCue: das neue Programm holt dessen Fenster in den Vordergrund, zeigt das Fehlerfenster OC-1001 und beendet sich.

Der Name haengt vom Datenordner ab (Standard %LOCALAPPDATA%\\OpenCue, oder OPENCUE_DATA_DIR): Tests und Aufnahmen mit eigenem Datenordner stoeren das echte Programm
nicht. Ob der Port frei ist, prueft main.py getrennt (OC-1002). Unter anderen Betriebssystemen passiert nichts.
"""
from __future__ import annotations

import ctypes
import hashlib
import os
from ctypes import wintypes
from typing import Optional

from app import winui

ERROR_ALREADY_EXISTS = 183
_handle: Optional[int] = None
_OWN_CLASSES = ("OpenCueSplash", "OpenCueError")                         # Fenster dieses Programms, die nicht das Hauptfenster sind


def _mutex_name() -> str:
    from app import paths
    root = str(paths.default_data_root().resolve()).lower()
    return "Local\\OpenCue.Console." + hashlib.sha1(root.encode("utf-8")).hexdigest()[:16]


def acquire() -> bool:
    """True = wir sind das einzige OpenCue (Mutex gehalten bis zum Prozessende). False = es laeuft schon eines."""
    global _handle
    if not winui.available():
        return True
    try:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
        kernel32.CreateMutexW.restype = ctypes.c_void_p
        kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
        handle = kernel32.CreateMutexW(None, False, _mutex_name())
        error = ctypes.get_last_error()
    except Exception:
        return True                                                      # im Zweifel starten (lieber ein Doppelstart als gar keiner)
    if not handle:
        return True
    if error == ERROR_ALREADY_EXISTS:
        kernel32.CloseHandle(handle)
        return False
    _handle = handle
    return True


def raise_running_window() -> bool:
    """Das Fenster des laufenden OpenCue nach vorn holen (aus der Taskleiste wiederherstellen, falls minimiert). True, wenn eines gefunden wurde."""
    if not winui.available():
        return False
    u = winui.load().user32
    own_pid = os.getpid()
    found = []

    def visit(hwnd, _lparam) -> bool:
        if winui.window_title(hwnd) != "OpenCue" or winui.window_class(hwnd) == "OpenCueTray":          # das unsichtbare Tray-Fenster (Server ohne Fenster) ist kein Programmfenster
            return True
        pid = wintypes.DWORD()
        u.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value == own_pid:
            return True
        rank = 1 if winui.window_class(hwnd).startswith(_OWN_CLASSES) else 0     # Hauptfenster zuerst, ein noch laufendes Startbild nur zur Not
        found.append((rank, not u.IsWindowVisible(hwnd), hwnd))
        return True

    callback = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)(visit)
    u.EnumWindows(callback, 0)
    if not found:
        return False
    found.sort()
    hwnd = found[0][2]
    try:
        if u.IsIconic(hwnd):
            u.ShowWindow(hwnd, 9)                                        # SW_RESTORE
        u.SwitchToThisWindow(hwnd, True)
        u.SetForegroundWindow(hwnd)
    except Exception:
        return False
    return True


def forward_show(port: int, path: str) -> bool:
    """Dem laufenden OpenCue (Port aus der Lauf-Datei) sagen, dass es diese Show-Datei oeffnen soll (Doppelklick auf eine .ocshow, waehrend OpenCue schon laeuft). True = angenommen."""
    import json
    import urllib.request
    try:
        request = urllib.request.Request(f"http://127.0.0.1:{int(port)}/api/showfiles/open-file", data=json.dumps({"path": str(path)}).encode("utf-8"),
                                         headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(request, timeout=15) as response:
            return bool(json.loads(response.read().decode("utf-8")).get("ok"))
    except Exception:                                                        # noqa: BLE001 - dann gilt der normale Doppelstart-Hinweis
        return False


# ---------------------------------------------------------------------------------------------------------------- Lauf-Datei
# Das laufende OpenCue schreibt <Datenordner>/config/run.json (Port, ob ohne Fenster). Ein zweiter Start findet damit heraus, ob er ein Fenster nach vorn holen kann - oder, bei einem
# Server ohne Fenster (--no-ui), stattdessen den Browser auf dessen Adresse oeffnen soll.
def _runfile():
    from app import paths
    return paths.default_data_root() / "config" / "run.json"


def write_runfile(port: int, headless: bool) -> None:
    import json
    try:
        _runfile().write_text(json.dumps({"pid": os.getpid(), "port": int(port), "headless": bool(headless)}), encoding="utf-8")
    except OSError:
        pass


def mark_stopping() -> None:
    """Das laufende OpenCue beendet sich gerade (Fenster zu, Aufraeumen laeuft): ein neuer Start wartet dann, statt den Fehler OC-1001 zu zeigen."""
    import json
    try:
        data = read_runfile()
        if data.get("pid") == os.getpid() and not data.get("stopping"):
            data["stopping"] = True
            _runfile().write_text(json.dumps(data), encoding="utf-8")
    except OSError:
        pass


def wait_until_free(timeout: float = 25.0) -> bool:
    """Wartet, bis das beendende OpenCue den Mutex freigibt, und uebernimmt ihn (True). Nach `timeout` Sekunden False."""
    import time
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if acquire():
            return True
        time.sleep(0.2)
    return False


def clear_runfile() -> None:
    try:
        data = read_runfile()
        if data.get("pid") == os.getpid():                               # nur die eigene Datei loeschen
            _runfile().unlink()
    except OSError:
        pass


def read_runfile() -> dict:
    import json
    try:
        data = json.loads(_runfile().read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}
