# Copyright (C) 2026 Samuel Zenker
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Start mit Windows (Einstellungen -> Allgemein -> Verhalten): OpenCue startet beim Anmelden des Benutzers, auf Wunsch ohne Fenster als Server (`--no-ui`, siehe app/cli.py) - praktisch
fuer einen Rechner, der nur DMX ausgibt und per iPad oder Browser bedient wird. Ein Eintrag im Registry-Zweig des Benutzers (HKCU, Zweig Run): keine Administratorrechte noetig,
nur fuer diesen Benutzer, jederzeit wieder entfernbar. Nur im gebauten Programm (OpenCue.exe); aus dem Quelltext heraus gibt es keinen festen Programmpfad.

  get()                    {"available", "enabled", "headless", "command"}
  set(enabled, headless)   Eintrag anlegen / entfernen
"""
from __future__ import annotations

import subprocess
import sys
from typing import Any, Dict

from app import windows_env

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"                  # Tests setzen einen eigenen Zweig
VALUE_NAME = "OpenCue"


def _command(headless: bool) -> str:
    exe = sys.executable
    return subprocess.list2cmdline([exe] + (["--no-ui"] if headless else []))


def available() -> bool:
    import os
    return windows_env.available() and (bool(getattr(sys, "frozen", False)) or bool(os.environ.get("OPENCUE_AUTOSTART_TEST")))


def get() -> Dict[str, Any]:
    out: Dict[str, Any] = {"available": available(), "enabled": False, "headless": False, "command": ""}
    if not windows_env.available():
        return out
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            value, _kind = winreg.QueryValueEx(key, VALUE_NAME)
    except OSError:
        return out
    out.update({"enabled": True, "headless": "--no-ui" in str(value), "command": str(value)})
    return out


def set(enabled: bool, headless: bool = False) -> Dict[str, Any]:                  # noqa: A001 - Name wie in der Oberflaeche
    if not windows_env.available():
        return get()
    import winreg
    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
        if enabled:
            winreg.SetValueEx(key, VALUE_NAME, 0, winreg.REG_SZ, _command(headless))
        else:
            try:
                winreg.DeleteValue(key, VALUE_NAME)
            except OSError:
                pass
    return get()
