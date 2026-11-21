# Copyright (C) 2026 Samuel Zenker
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Windows-Umgebung des Prozesses: laeuft OpenCue als Administrator, Prozess-Prioritaet, genaue Zeitgeber.

  is_admin()                  True, wenn das Programm "als Administrator" (mit erhoehten Rechten) laeuft.
  set_priority(level)         "normal" | "above" (Standard) | "high": das Zeitverhalten der DMX-Ausgabe bleibt stabil, wenn der Rechner ausgelastet ist. Braucht keine Administratorrechte.
  precise_timers(True/False)  Zeitgeber-Aufloesung 1 ms statt ~15,6 ms: die 40-Hz-Schleifen (Cues, Effekte, DMX) laufen gleichmaessiger. Braucht keine Administratorrechte.
  describe()                  eine Zeile fuer Protokoll und Fehlerbericht.

Was Administratorrechte WIRKLICH bringen: nur die Windows-Firewall-Regel (app/firewall.py) laesst sich damit ohne Rueckfrage anlegen - sonst fragt Windows einmal nach. Fuer den normalen
Betrieb sind sie weder noetig noch erwuenscht: ein als Administrator gestartetes Programm bekommt von Windows keine Dateien per Drag & Drop aus dem (nicht erhoehten) Explorer, und
ein Webserver mit Administratorrechten ist ein groesseres Ziel. Deshalb warnt OpenCue im Protokoll, wenn es so laeuft.
"""
from __future__ import annotations

import ctypes
import logging
import sys
from typing import Dict

logger = logging.getLogger("opencue.system")

_PRIORITY_CLASS: Dict[str, int] = {"normal": 0x00000020, "above": 0x00008000, "high": 0x00000080}
_timers_on = False


def available() -> bool:
    return sys.platform == "win32"


def is_admin() -> bool:
    if not available():
        return False
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def set_priority(level: str) -> bool:
    """Prozess-Prioritaet setzen; unbekannte Stufe = Standard "above". Gibt zurueck, ob Windows sie angenommen hat."""
    if not available():
        return False
    try:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.GetCurrentProcess.restype = ctypes.c_void_p
        kernel32.SetPriorityClass.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
        kernel32.SetPriorityClass.restype = ctypes.c_int
        return bool(kernel32.SetPriorityClass(kernel32.GetCurrentProcess(), _PRIORITY_CLASS.get(level, _PRIORITY_CLASS["above"])))
    except Exception:
        logger.warning("[SYSTEM] Process priority could not be set", exc_info=True)
        return False


def precise_timers(on: bool) -> None:
    """Zeitgeber-Aufloesung 1 ms ein-/ausschalten (paarweise; mehrfaches Einschalten zaehlt einmal)."""
    global _timers_on
    if not available() or on == _timers_on:
        return
    try:
        winmm = ctypes.WinDLL("winmm")
        winmm.timeBeginPeriod.argtypes = [ctypes.c_uint]
        winmm.timeEndPeriod.argtypes = [ctypes.c_uint]
        (winmm.timeBeginPeriod if on else winmm.timeEndPeriod)(1)
        _timers_on = on
    except Exception:
        logger.warning("[SYSTEM] Timer resolution could not be changed", exc_info=True)


def describe() -> str:
    admin = is_admin()
    return "Administrator: " + ("yes" if admin else "no")
