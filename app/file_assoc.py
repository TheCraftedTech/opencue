# Copyright (C) 2026 Samuel Zenker
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Dateizuordnung fuer Shows (Standard, kein Schalter): Doppelklick auf eine `.ocshow`-Datei oeffnet sie in OpenCue. Die Endung `.ocshow` gehoert den Export-Paketen
(ein ZIP mit der Show und den Dateien, die sie braucht - Datei-Menue -> Show exportieren). Der Installer richtet die Zuordnung selbst ein; ensure() macht beim Start dasselbe fuer
ein Programm ohne Installer (entpackt / tragbar). Ein Eintrag im Registry-Zweig des Benutzers (HKCU\\Software\\Classes): keine Administratorrechte noetig.
Nur im gebauten Programm (OpenCue.exe); aus dem Quelltext heraus gibt es keinen festen Programmpfad.

  get()          {"available", "enabled", "command"}
  ensure()       beim Start: Zuordnung anlegen, falls sie fehlt oder auf einen anderen Programmpfad zeigt
  set(enabled)   Zuordnung anlegen / entfernen (Tests)
"""
from __future__ import annotations

import subprocess
import sys
from typing import Any, Dict

from app import windows_env

CLASSES_KEY = r"Software\Classes"                                            # Tests setzen einen eigenen Zweig
EXTENSION = ".ocshow"
PROG_ID = "OpenCue.Show"


def _command() -> str:
    return subprocess.list2cmdline([sys.executable]) + ' "%1"'


def available() -> bool:
    import os
    return windows_env.available() and (bool(getattr(sys, "frozen", False)) or bool(os.environ.get("OPENCUE_FILEASSOC_TEST")))


def get() -> Dict[str, Any]:
    out: Dict[str, Any] = {"available": available(), "enabled": False, "command": ""}
    if not windows_env.available():
        return out
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, f"{CLASSES_KEY}\\{EXTENSION}") as key:
            prog = winreg.QueryValueEx(key, "")[0]
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, f"{CLASSES_KEY}\\{prog}\\shell\\open\\command") as key:
            command = str(winreg.QueryValueEx(key, "")[0])
    except OSError:
        return out
    out.update({"enabled": prog == PROG_ID and sys.executable.lower() in command.lower(), "command": command})
    return out


def _set_default(path: str, value: str) -> None:
    import winreg
    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_SET_VALUE) as key:
        winreg.SetValueEx(key, "", 0, winreg.REG_SZ, value)


def _delete_tree(path: str) -> None:
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_READ | winreg.KEY_WRITE) as key:
            while True:
                try:
                    child = winreg.EnumKey(key, 0)
                except OSError:
                    break
                _delete_tree(f"{path}\\{child}")
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, path)
    except OSError:
        pass


def _notify() -> None:
    """Der Explorer soll die neue Zuordnung sofort kennen (Symbole, "Oeffnen mit")."""
    if CLASSES_KEY != r"Software\Classes":
        return                                                                  # Test-Zweig: die Shell nicht stoeren
    try:
        import ctypes
        ctypes.windll.shell32.SHChangeNotify(0x08000000, 0, None, None)          # SHCNE_ASSOCCHANGED
    except Exception:                                                            # noqa: BLE001
        pass


def ensure() -> bool:
    """Standard: Doppelklick auf .ocshow oeffnet die Datei in OpenCue. Beim Start im gebauten Programm sicherstellen (auch nach einem Umzug des Programmordners);
    aus dem Quelltext heraus passiert nichts. True, wenn die Zuordnung danach stimmt."""
    if not available():
        return False
    try:
        if not get()["enabled"]:
            set(True)
        return bool(get()["enabled"])
    except Exception:                                                            # noqa: BLE001 - Registry nicht beschreibbar: nicht schlimm, kein Abbruch beim Start
        return False


def set(enabled: bool) -> Dict[str, Any]:                                         # noqa: A001 - Name wie in der Oberflaeche
    if not windows_env.available():
        return get()
    if enabled:
        _set_default(f"{CLASSES_KEY}\\{EXTENSION}", PROG_ID)
        _set_default(f"{CLASSES_KEY}\\{PROG_ID}", "OpenCue show")
        _set_default(f"{CLASSES_KEY}\\{PROG_ID}\\DefaultIcon", subprocess.list2cmdline([sys.executable]) + ",0")
        _set_default(f"{CLASSES_KEY}\\{PROG_ID}\\shell\\open\\command", _command())
    else:
        _delete_tree(f"{CLASSES_KEY}\\{EXTENSION}")
        _delete_tree(f"{CLASSES_KEY}\\{PROG_ID}")
    _notify()
    return get()
