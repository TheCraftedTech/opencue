# Copyright (C) 2026 Samuel Zenker
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Sprachen der Oberflaeche - EINE Stelle. Jede Sprache ist eine Datei static/locales/<Kuerzel>.json (alle Texte der Oberflaeche); dieselben Dateien lesen auch die Teile, die der SERVER schreibt
(PDF-Dokumentation, Tray-Symbol, Anmeldeseite des Fernzugriffs). Eine neue Sprache: Datei anlegen (gleiche Schluessel wie en.json), hier und in static/js/app.js (LANGUAGES) eintragen,
dazu die Schluessel LANGUAGE_<KUERZEL> in allen Sprachdateien.

  tr("PDF_PATCH", "fr")                     Text einer Sprache (fehlt er: Englisch, sonst der Schluessel)
  tr("SRV_LOGIN_LOCKED", "de", s=5)         Platzhalter {s} ersetzen
"""
from __future__ import annotations

import json
from typing import Any, Dict

LANGUAGES = (("en", "English"), ("de", "Deutsch"), ("fr", "Français"), ("nl", "Nederlands"), ("it", "Italiano"), ("es", "Español"))
CODES = tuple(code for code, _name in LANGUAGES)
NAMES: Dict[str, str] = dict(LANGUAGES)
DEFAULT = "en"

_cache: Dict[str, Dict[str, str]] = {}


def normalize(language: Any) -> str:
    """Ein gueltiges Sprachkuerzel (sonst Englisch); auch "de-DE" -> "de"."""
    code = str(language or "").lower().replace("_", "-").split("-")[0]
    return code if code in NAMES else DEFAULT


def locale(language: str) -> Dict[str, str]:
    code = normalize(language)
    if code not in _cache:
        from app import paths
        try:
            _cache[code] = json.loads((paths.project_root() / "static" / "locales" / f"{code}.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            _cache[code] = {}
    return _cache[code]


def tr(key: str, language: str = DEFAULT, **values: Any) -> str:
    text = locale(language).get(key) or locale(DEFAULT).get(key) or key
    for name, value in values.items():
        text = text.replace("{" + name + "}", str(value))
    return text
