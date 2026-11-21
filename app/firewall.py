# Copyright (C) 2026 Samuel Zenker
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Windows-Firewall-Regel fuer OpenCue (Einstellungen -> Fernzugriff -> "Windows-Firewall").

Ohne Regel fragt Windows beim ersten Netzwerk-Zugriff ("Zugriff zulassen?"), und eine nicht beantwortete oder abgelehnte Frage blockiert die Fernsteuerung (iPad, Handy), sACN,
Art-Net-Empfang und den Netzwerk-Namen (mDNS). Eine Regel fuer das Programm (nur private und Domaenen-Netzwerke, nicht oeffentliche) loest das ein fuer alle Mal.

  status()   {"available", "exists", "admin", "program"}: gibt es die Regel "OpenCue" fuer DIESES Programm? (lesen geht ohne Administratorrechte)
  add()      Regel anlegen. Mit Administratorrechten gleich, sonst fragt Windows (UAC) nach: nur der kleine `netsh`-Aufruf wird erhoeht, nicht OpenCue selbst.
  remove()   Regel wieder loeschen (genauso).

Es wird nichts anderes an der Firewall geaendert; die Regel gilt fuer genau diese Programmdatei (eingehend, private + Domaene).
"""
from __future__ import annotations

import ctypes
import logging
import subprocess
import sys
import time
from typing import Any, Dict, List

from app import windows_env

logger = logging.getLogger("opencue.firewall")
RULE_NAME = "OpenCue"
_NO_WINDOW = 0x08000000                                                   # CREATE_NO_WINDOW


def program_path() -> str:
    return sys.executable


def _netsh(args: List[str], timeout: float = 15.0) -> subprocess.CompletedProcess:
    return subprocess.run(["netsh", "advfirewall", "firewall"] + args, capture_output=True, text=True, timeout=timeout, creationflags=_NO_WINDOW,
                          encoding="oem", errors="replace")


def exists() -> bool:
    """Gibt es eine Regel "OpenCue", die auf dieses Programm zeigt? (Rueckgabecode und Pfad im Text - unabhaengig von der Sprache von Windows.)"""
    if not windows_env.available():
        return False
    try:
        result = _netsh(["show", "rule", f"name={RULE_NAME}", "verbose"])
    except Exception:
        return False
    return result.returncode == 0 and program_path().lower() in (result.stdout or "").lower()


def status() -> Dict[str, Any]:
    return {"available": windows_env.available(), "exists": exists(), "admin": windows_env.is_admin(), "program": program_path()}


def _add_args() -> List[str]:
    return ["add", "rule", f"name={RULE_NAME}", "dir=in", "action=allow", f"program={program_path()}", "enable=yes", "profile=private,domain"]


def _delete_args() -> List[str]:
    return ["delete", "rule", f"name={RULE_NAME}", f"program={program_path()}"]


def _run_elevated(args: List[str], wait_for: bool) -> bool:
    """`netsh advfirewall firewall <args>` mit Administratorrechten ausfuehren. Als Administrator direkt, sonst ueber die Windows-Rueckfrage (UAC, ShellExecute "runas").
    Rueckgabe: True, wenn der Befehl gestartet wurde (die Rueckfrage nicht abgelehnt); das Ergebnis prueft der Aufrufer ueber exists()."""
    if windows_env.is_admin():
        try:
            return _netsh(args).returncode == 0
        except Exception:
            logger.warning("[FIREWALL] netsh failed", exc_info=True)
            return False
    try:
        parameters = subprocess.list2cmdline(["advfirewall", "firewall"] + args)
        shell32 = ctypes.windll.shell32
        shell32.ShellExecuteW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_int]
        shell32.ShellExecuteW.restype = ctypes.c_void_p
        result = shell32.ShellExecuteW(None, "runas", "netsh.exe", parameters, None, 0)        # SW_HIDE
        started = (result or 0) > 32                                                              # <= 32: Fehler oder "Nein" bei der Rueckfrage (ERROR_CANCELLED = 1223 -> 5)
    except Exception:
        logger.warning("[FIREWALL] elevation failed", exc_info=True)
        return False
    if started and wait_for:
        time.sleep(0.3)
    return started


def _wait_until(want: bool, seconds: float = 8.0) -> bool:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if exists() == want:
            return True
        time.sleep(0.5)
    return exists() == want


def add() -> Dict[str, Any]:
    """Regel anlegen. {ok, exists, cancelled}: cancelled = die Windows-Rueckfrage wurde abgelehnt."""
    if exists():
        return {"ok": True, "exists": True, "cancelled": False}
    started = _run_elevated(_add_args(), True)
    ok = started and _wait_until(True)
    logger.info("[FIREWALL] add rule: started=%s exists=%s", started, ok)
    return {"ok": ok, "exists": exists(), "cancelled": not started}


def remove() -> Dict[str, Any]:
    if not exists():
        return {"ok": True, "exists": False, "cancelled": False}
    started = _run_elevated(_delete_args(), True)
    ok = started and _wait_until(False)
    logger.info("[FIREWALL] remove rule: started=%s removed=%s", started, ok)
    return {"ok": ok, "exists": exists(), "cancelled": not started}
