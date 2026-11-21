# Copyright (C) 2026 Samuel Zenker
# SPDX-License-Identifier: GPL-3.0-or-later
"""
crash.py
Unerwartete Fehler abfangen, protokollieren und dem Nutzer zeigen (Fehlerfenster app/error_window.py, Codes in app/errors.py):

  * Startfehler und Fehler im Hauptthread  -> OC-2001 / OC-2004, Fenster, dann Ende      (run(): umschliesst main())
  * Absturz des eingebauten Servers         -> OC-2003, Fenster, dann Ende               (fatal())
  * Ausnahme in einem Hintergrund-Thread    -> immer ins Log (OC-2002); das Fenster nur beim ERSTEN Mal je Start und nicht beim Beenden (Programm laeuft weiter)

install() setzt die Haken (sys.excepthook, threading.excepthook). Alles, was passiert, steht mit Fehlercode und Traceback im Log (app/logsetup.py).
"""
from __future__ import annotations

import os
import sys
import threading
import traceback
from typing import Callable, Optional

from app import errors

_before_dialog: Optional[Callable[[], None]] = None          # z. B. das Startbild schliessen, damit es das Fehlerfenster nicht verdeckt
_cleanup: Optional[Callable[[], None]] = None                # z. B. DMX sauber beenden, bevor der Prozess endet
_background_dialog_shown = False
_lock = threading.Lock()
dialogs_enabled = True                                       # beim Beenden aus: Fehler dabei sollen kein Fenster mehr oeffnen


def install(before_dialog: Optional[Callable[[], None]] = None, cleanup: Optional[Callable[[], None]] = None) -> None:
    global _before_dialog, _cleanup
    _before_dialog, _cleanup = before_dialog, cleanup
    sys.excepthook = _main_thread_hook
    threading.excepthook = _thread_hook


def _format(exc_type, exc, tb) -> str:
    return "".join(traceback.format_exception(exc_type, exc, tb))


def _prepare_dialog() -> None:
    if _before_dialog is not None:
        try:
            _before_dialog()
        except Exception:
            pass


def fatal(code: str, exc_info=None, details: str = "") -> None:
    """Schwerer Fehler: protokollieren, Fenster zeigen (wartet auf Schliessen), aufraeumen, Prozess beenden."""
    text = _format(*exc_info) if exc_info else ""
    full = (details + "\n" + text).strip()
    print(f"[OpenCue] {code} fatal error\n{full}", file=sys.stderr, flush=True)
    _prepare_dialog()
    errors.present(code, details=full)
    if _cleanup is not None:
        try:
            _cleanup()
        except Exception:
            pass
    try:
        sys.stderr.flush()
    except Exception:
        pass
    os._exit(1)


def run(main: Callable[[], None], startup_done: Callable[[], bool] = lambda: False) -> None:
    """main() ausfuehren; ein unbehandelter Fehler wird zum Fehlerfenster. `startup_done` sagt, ob das Programm schon lief (OC-2004) oder noch startete (OC-2001)."""
    try:
        main()
    except (SystemExit, KeyboardInterrupt):
        raise
    except BaseException:
        fatal("OC-2004" if startup_done() else "OC-2001", sys.exc_info())


def _main_thread_hook(exc_type, exc, tb) -> None:
    if issubclass(exc_type, (KeyboardInterrupt, SystemExit)):
        sys.__excepthook__(exc_type, exc, tb)
        return
    fatal("OC-2004", (exc_type, exc, tb))


def _thread_hook(args) -> None:
    global _background_dialog_shown
    if args.exc_type is SystemExit:
        return
    where = args.thread.name if args.thread else "?"
    text = _format(args.exc_type, args.exc_value, args.exc_traceback)
    print(f"[OpenCue] OC-2002 unexpected error in background thread '{where}'\n{text}", file=sys.stderr, flush=True)
    if not dialogs_enabled:
        return
    with _lock:
        if _background_dialog_shown:
            return
        _background_dialog_shown = True
    errors.present("OC-2002", details=f"Thread: {where}\n{text}", block=False)
