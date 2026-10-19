# Copyright (C) 2026 Samuel Zenker
# SPDX-License-Identifier: GPL-3.0-or-later
"""
version.py
Die EINE Stelle fuer Version und Programm-Metadaten von OpenCue.

Wird gelesen von main.py (Start, Fenster), app/about.py ("Ueber OpenCue" im Hilfe-Menue), packaging/make_version_info.py (Datei-Eigenschaften der OpenCue.exe),
packaging/OpenCue.iss (Installer) und dem Build-Skript. Nirgends sonst steht eine Versionsnummer.

Neue Version: nur APP_VERSION aendern (Schema MAJOR.MINOR.PATCH, optional mit Zusatz wie "1.1.0-beta.1"), dann CHANGELOG.md ergaenzen und neu bauen.
Texte fuer die Datei-Eigenschaften sind bewusst Englisch.
"""
from __future__ import annotations

import re
from typing import Any, Dict, Tuple

APP_NAME = "OpenCue"
APP_VERSION = "1.0.0"                                   # Zusatz fuer Vorabversionen z. B. "1.0.0-beta.1"
APP_VERSION_LABEL = "v" + APP_VERSION                   # so steht es in der Oberflaeche, im Installer und im Release-Namen
APP_DESCRIPTION = "DMX lighting control console"          # kurz halten: Windows kuerzt die Datei-Beschreibung (Task-Manager, Eigenschaften) schnell ab
APP_COMPANY = "Samuel Zenker"
APP_COPYRIGHT = "Copyright (C) 2026 Samuel Zenker"
APP_LICENSE_NAME = "GNU General Public License v3.0 or later"
APP_LICENSE_ID = "GPL-3.0-or-later"
APP_EXE_NAME = "OpenCue.exe"
SOURCE_URL = "https://github.com/TheCraftedTech/opencue"                 # Quellcode (oeffentliches Repository; GPL: Quellcode muss auffindbar sein)
WEBSITE_URL = "https://thecraftedtech.github.io/opencue/"              # Projektseite (GitHub Pages des oeffentlichen Repositories)
WEBVIEW2_URL = "https://developer.microsoft.com/microsoft-edge/webview2/"
RELEASES_URL = SOURCE_URL + "/releases/latest"                           # Seite des neuesten Releases (Download im Browser)
UPDATE_API_URL = "https://api.github.com/repos/TheCraftedTech/opencue/releases/latest"       # Update-Pruefung (app/updater.py); gleiches Repository wie SOURCE_URL


def version_tuple() -> Tuple[int, int, int, int]:
    """(Major, Minor, Patch, 0) fuer die Windows-Versionsresource (Vorabversions-Zusaetze zaehlen nicht)."""
    match = re.match(r"^(\d+)\.(\d+)\.(\d+)", APP_VERSION)
    if not match:
        raise ValueError(f"APP_VERSION '{APP_VERSION}' hat nicht die Form MAJOR.MINOR.PATCH")
    major, minor, patch = (int(part) for part in match.groups())
    return major, minor, patch, 0


def info() -> Dict[str, Any]:
    """Alle Angaben fuer die Oberflaeche (Ueber-Dialog) und /api/about."""
    return {
        "name": APP_NAME,
        "version": APP_VERSION,
        "label": APP_VERSION_LABEL,
        "description": APP_DESCRIPTION,
        "company": APP_COMPANY,
        "copyright": APP_COPYRIGHT,
        "license": APP_LICENSE_NAME,
        "license_id": APP_LICENSE_ID,
        "source_url": SOURCE_URL,
        "website_url": WEBSITE_URL,
    }
