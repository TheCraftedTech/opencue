# Copyright (C) 2026 Samuel Zenker
# SPDX-License-Identifier: GPL-3.0-or-later
"""
logsetup.py
Protokolldatei von OpenCue: jeder Start schreibt alles, was sonst nur auf der Konsole stuende (Logging, print, Fehler), zusaetzlich in
`<Datenordner>\\logs\\opencue.log` (Standard %LOCALAPPDATA%\\OpenCue\\logs). Die Datei des vorigen Starts bleibt als `opencue.previous.log` erhalten - nach einem
Absturz und Neustart ist der Fehler also noch da. Native Abstuerze (faulthandler) landen ebenfalls dort.

Beim PyInstaller-Build ohne Konsole (--windowed) sind sys.stdout/sys.stderr None; uvicorns Logging ruft isatty() darauf auf und bricht ab - sie zeigen dann auf die Datei.

prepare() laeuft ganz am Anfang von main.py, VOR allen Importen, die Logging einrichten (uvicorn, app.server). Es ist idempotent. Nur Standardbibliothek.
"""
from __future__ import annotations

import faulthandler
import logging
import os
import re
import sys
from pathlib import Path
from typing import List, Optional

LOG_FORMAT = "%(asctime)s [%(name)s] %(message)s"

# Zugangsschluessel gehoeren nie ins Protokoll (und damit nie in "Copy details" eines Fehlerberichts): REST-API-Tokens kommen als ?access_token=oc_... in der Adresse
# (Mikrocontroller, Browser, WebSocket) und stehen sonst in jeder Zugriffszeile von uvicorn.
_SECRET_PARAM = re.compile(r"((?:access_token|token|api_key|apikey|password|passwd|secret)=)[^&\s\"'<>]+", re.IGNORECASE)
_SECRET_TOKEN = re.compile(r"\boc_[A-Za-z0-9_\-]{12,}")


def redact(text: str) -> str:
    """Zugangsschluessel unkenntlich machen: Werte in ?access_token=..., token=, password= ... und OpenCue-Tokens (oc_...)."""
    if "=" not in text and "oc_" not in text:
        return text
    return _SECRET_TOKEN.sub("oc_***", _SECRET_PARAM.sub(r"\1***", text))

_stream = None


def log_dir() -> Path:
    from app import paths
    return paths.default_data_root() / "logs"


def log_path() -> Path:
    return log_dir() / "opencue.log"


def previous_log_path() -> Path:
    return log_dir() / "opencue.previous.log"


class _Tee:
    """Schreibt auf die Konsole (falls es eine gibt) und in die Protokolldatei."""

    def __init__(self, original, sink) -> None:
        self._original = original
        self._sink = sink

    def write(self, data: str) -> int:
        data = redact(data)
        for target in (self._original, self._sink):
            if target is not None:
                try:
                    target.write(data)
                except Exception:
                    pass                                                 # z. B. Zeichen, die die Konsole nicht darstellen kann
        return len(data)

    def flush(self) -> None:
        for target in (self._original, self._sink):
            if target is not None:
                try:
                    target.flush()
                except Exception:
                    pass

    def isatty(self) -> bool:
        try:
            return bool(self._original is not None and self._original.isatty())
        except Exception:
            return False

    def __getattr__(self, name: str):
        return getattr(self._original if self._original is not None else self._sink, name)


def prepare() -> Optional[Path]:
    """Protokolldatei oeffnen (vorige sichern), stdout/stderr spiegeln, Logging und faulthandler einrichten. Gibt den Pfad zurueck (None, wenn nichts moeglich war)."""
    global _stream
    if _stream is not None:
        return log_path()
    try:
        folder = log_dir()
        folder.mkdir(parents=True, exist_ok=True)
        path = log_path()
        if path.is_file():
            try:
                os.replace(path, previous_log_path())
            except OSError:
                pass
        _stream = open(path, "w", buffering=1, encoding="utf-8", errors="replace")
    except OSError:
        _stream = None
    if _stream is None:
        if sys.stdout is None or sys.stderr is None:                     # ohne Datei und ohne Konsole: wenigstens nicht abstuerzen
            devnull = open(os.devnull, "w", encoding="utf-8")
            sys.stdout = sys.stdout or devnull
            sys.stderr = sys.stderr or devnull
        return None
    sys.stdout = _Tee(sys.stdout, _stream)
    sys.stderr = _Tee(sys.stderr, _stream)
    try:
        faulthandler.enable(file=_stream)                                # Abstuerze in nativem Code (Zugriffsverletzung) hinterlassen wenigstens eine Spur
    except Exception:
        pass
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)           # gleiche Einstellung wie app/server.py; hier zuerst, damit auch fruehe Meldungen in der Datei stehen
    return log_path()


def read_tail(lines: int = 40) -> List[str]:
    """Die letzten Zeilen des aktuellen Logs (fuer "Copy details")."""
    try:
        if _stream is not None:
            _stream.flush()
        with open(log_path(), "r", encoding="utf-8", errors="replace") as handle:
            return [row.rstrip("\n") for row in handle.readlines()[-lines:]]
    except Exception:                                                    # OSError, oder der Datenordner ist nicht benutzbar
        return []
