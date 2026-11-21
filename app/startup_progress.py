# Copyright (C) 2026 Samuel Zenker
# SPDX-License-Identifier: GPL-3.0-or-later
"""
startup_progress.py
Duenne Kopplung zwischen den Start-Stationen (main.py, Server) und dem Startbild (app/splash.py): jede Station ruft report(prozent, text) auf,
main.py hat das Startbild als Empfaenger eingetragen. Ohne Empfaenger (Tests, Browser-Betrieb, --no-splash) tut report() nichts und kostet nichts.
Die Prozentwerte steigen nur; Texte sind immer Englisch und kurz ("Loading effects").
"""
from __future__ import annotations

from typing import Callable, Optional

_callback: Optional[Callable[[float, str], None]] = None


def set_callback(callback: Optional[Callable[[float, str], None]]) -> None:
    global _callback
    _callback = callback


def report(percent: float, text: str) -> None:
    cb = _callback
    if cb is None:
        return
    try:
        cb(percent, text)
    except Exception:
        pass                                                         # ein Startbild darf den Start nie stoeren
