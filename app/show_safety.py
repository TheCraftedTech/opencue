# Copyright (C) 2026 Samuel Zenker
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Schutz der Show-Dateien: Sperre ("Schloss") und die Frage "kann die geladene Show gerade gespeichert werden?".

Gesperrt ist eine Show-Datei, wenn in ihr `"locked": true` steht (gleich hinter `saved_at`, damit der Dateimanager es aus den ersten Bytes lesen kann). Eine gesperrte
Show wird von OpenCue nicht mehr ueberschrieben, umbenannt oder geloescht - "Speichern unter" (neuer Name) und Duplizieren gehen weiter, die Kopie ist nicht gesperrt.
Das ist ein Schutz gegen Versehen waehrend einer Veranstaltung, kein Kopierschutz: die Datei selbst kann man mit jedem Editor aendern.

Gruende, warum eine Show nicht gespeichert werden kann (`save_blockers`): die Datei ist gesperrt, schreibgeschuetzt (Windows-Attribut) oder ihr Ordner nicht beschreibbar.
Sie stehen im Beenden-Dialog (orange Hinweis, Beenden ohne Speichern nur mit zwei Klicks).
"""
from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

_LOCKED = re.compile(r'"locked"\s*:\s*true', re.IGNORECASE)


class ShowLocked(Exception):
    """Die Zieldatei ist gesperrt: nicht ueberschreiben."""

    def __init__(self, path: Path):
        super().__init__(f"The show file {path.name} is locked")
        self.path = path


def is_locked(path: Any) -> bool:
    """Steht in der Datei `"locked": true` (am Dateianfang)? Fehlende oder unlesbare Datei = nicht gesperrt."""
    if not path:
        return False
    try:
        with open(path, "rb") as handle:
            head = handle.read(4096).decode("utf-8", "replace")
    except OSError:
        return False
    return bool(_LOCKED.search(head))


def _atomic_write(path: Path, text: str) -> None:
    """Erst in eine Nachbardatei, dann ersetzen: ein Abbruch mittendrin zerstoert die Show nicht."""
    fd, tmp = tempfile.mkstemp(prefix=path.stem + ".", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def set_locked(path: Path, locked: bool) -> Dict[str, Any]:
    """Sperre setzen oder aufheben; der Rest der Datei bleibt, nur `locked` kommt (oder geht) hinter `saved_at`. Wirft OSError / ValueError bei unlesbarer Datei."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("not a show file")
    data.pop("locked", None)
    if locked:
        out: Dict[str, Any] = {}
        placed = False
        for key, value in data.items():
            out[key] = value
            if key == "saved_at":
                out["locked"] = True
                placed = True
        if not placed:                                                  # keine Zeitangabe (sehr alte Datei): ganz an den Anfang
            out = {"locked": True, **out}
        data = out
    _atomic_write(path, json.dumps(data, indent=2, ensure_ascii=False))
    return data


def strip_lock(data: Dict[str, Any]) -> Dict[str, Any]:
    """Eine Kopie (Duplizieren, Export) ist nie gesperrt."""
    data.pop("locked", None)
    return data


def save_blockers(path: Optional[str]) -> List[str]:
    """Warum sich die Show unter `path` jetzt nicht speichern laesst (leer = es geht). Kennungen: locked, read_only, folder_unwritable."""
    if not path:
        return []                                                       # noch keine Datei: "Speichern unter" fragt nach dem Namen
    target = Path(path)
    reasons: List[str] = []
    if is_locked(target):
        reasons.append("locked")
    try:
        if target.exists() and not os.access(target, os.W_OK):
            reasons.append("read_only")
        parent = target.parent
        if not parent.exists() or not os.access(parent, os.W_OK):
            reasons.append("folder_unwritable")
    except OSError:
        reasons.append("folder_unwritable")
    return reasons
