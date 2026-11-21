# Copyright (C) 2026 Samuel Zenker
# SPDX-License-Identifier: GPL-3.0-or-later
"""
keep_awake.py
Rechner und Bildschirm wach halten, solange OpenCue laeuft (Einstellungen -> Weitere Optionen -> "Bildschirm wach halten"): waehrend einer Show darf Windows den Laptop nicht in den
Ruhezustand schicken, den Bildschirm nicht ausschalten und die Leerlauf-Sperre nicht ausloesen.

- Windows: `SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED [| ES_DISPLAY_REQUIRED])`. Der Zustand haengt an dem Thread, der ihn setzt - darum haelt ein eigener Hintergrund-Thread ihn
  (und erneuert ihn alle 30 s) und nimmt ihn beim Ausschalten wieder zurueck. Im Server-Betrieb ohne Fenster (`OPENCUE_HEADLESS=1`) wird nur der Ruhezustand verhindert, nicht das Abschalten des Bildschirms.
- Fernzugriffs-Geraete (iPad, Tablet) halten ihren Bildschirm selbst an (Screen Wake Lock API im Browser, braucht eine sichere Seite = HTTPS; static/js/app.js WakeLockKeeper); der Schalter ist derselbe.
- Grenze: eine von der IT erzwungene Bildschirmsperre (Gruppenrichtlinie) kann ein Programm nicht aufheben.
"""
from __future__ import annotations

import logging
import os
import sys
import threading
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger("opencue.awake")

ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001
ES_DISPLAY_REQUIRED = 0x00000002
RENEW_SECONDS = 30.0


def _windows_call(flags: int) -> int:
    import ctypes
    return int(ctypes.windll.kernel32.SetThreadExecutionState(ctypes.c_uint(flags)))


class KeepAwake:
    def __init__(self, call: Optional[Callable[[int], int]] = None, available: Optional[bool] = None) -> None:
        self._call = call or _windows_call
        self._available = (sys.platform == "win32") if available is None else available
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self.enabled = False
        self.display = True
        self.error = ""

    def available(self) -> bool:
        return self._available

    def status(self) -> Dict[str, Any]:
        return {"available": self.available(), "enabled": self.enabled, "active": bool(self._thread and self._thread.is_alive()), "display": self.display, "error": self.error}

    def apply(self, enabled: bool, display: Optional[bool] = None) -> Dict[str, Any]:
        """Ein- oder ausschalten (jederzeit wiederholbar). display=None: mit Bildschirm, ausser im Server-Betrieb ohne Fenster."""
        with self._lock:
            self.display = (os.environ.get("OPENCUE_HEADLESS") != "1") if display is None else bool(display)
            self.enabled = bool(enabled)
            self._shutdown_thread()
            self.error = ""
            if self.enabled and self.available():
                self._stop.clear()
                flags = ES_CONTINUOUS | ES_SYSTEM_REQUIRED | (ES_DISPLAY_REQUIRED if self.display else 0)
                self._thread = threading.Thread(target=self._run, args=(flags,), name="keep-awake", daemon=True)
                self._thread.start()
        return self.status()

    def _shutdown_thread(self) -> None:
        thread = self._thread
        if thread is not None:
            self._stop.set()
            thread.join(timeout=2.0)
        self._thread = None

    def _run(self, flags: int) -> None:
        try:
            while True:
                if not self._call(flags):
                    self.error = "call_failed"
                    logger.warning("SetThreadExecutionState wurde abgelehnt")
                if self._stop.wait(RENEW_SECONDS):
                    break
        except Exception as exc:                                                    # noqa: BLE001
            self.error = str(exc)
            logger.warning("Wach halten fehlgeschlagen: %s", exc)
        finally:
            try:
                self._call(ES_CONTINUOUS)                                           # Zustand wieder freigeben (der Thread, der ihn gesetzt hat, nimmt ihn zurueck)
            except Exception:                                                       # noqa: BLE001
                pass


keep_awake = KeepAwake()
