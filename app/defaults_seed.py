"""
defaults_seed.py
Erstbefuellung des Benutzerordners mit den mitgelieferten Vorlagen aus defaults/ (nur lesen, siehe defaults/README.md):

  defaults/fixtures/*.gdtf   ->  <Datenordner>/fixtures/     Standard-Scheinwerfer (GDTF-Dateien) der Bibliothek
  defaults/showfiles/*.json  ->  <Datenordner>/showfiles/    Demo-Shows

Regeln (wie bei den Beispiel-Effekten und -Layouts): einmalig, nie etwas ueberschreiben, danach gehoert der Ordner dem Benutzer - was er loescht, kommt nicht zurueck
(eine Markierungsdatei `.defaults_seeded` im Zielordner merkt sich das). Fehlen die Vorlagen (leerer defaults-Ordner), wird nichts angelegt und nichts markiert, damit ein
spaeterer Programmstand mit Vorlagen sie noch bekommt. Die Effekte und Layouts werden an ihren eigenen Stellen angelegt (fx_script.seed_default_effects, server.seed_example_layouts).
"""
from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import List

from app import paths as _paths

logger = logging.getLogger("opencue.defaults")
MARKER = ".defaults_seeded"


def _seed(source: Path, target: Path, pattern: str, label: str) -> List[str]:
    """Kopiert source/pattern einmalig nach target. Gibt die neu angelegten Dateinamen zurueck."""
    templates = sorted(p for p in source.glob(pattern) if p.is_file()) if source.is_dir() else []
    if not templates:
        return []
    target.mkdir(parents=True, exist_ok=True)
    marker = target / MARKER
    if marker.exists():
        return []
    created: List[str] = []
    for path in templates:
        destination = target / path.name
        if destination.exists():
            continue                                                      # nie ueberschreiben
        try:
            shutil.copyfile(path, destination)
            created.append(path.name)
        except OSError as exc:
            logger.warning("[Defaults] %s konnte nicht kopiert werden: %s", path.name, exc)
    marker.write_text(f"{label} uebernommen\n", encoding="utf-8")
    return created


def seed_default_fixtures() -> List[str]:
    """Standard-Scheinwerfer (GDTF) in die Bibliothek legen (einmalig)."""
    return _seed(_paths.default_fixtures_dir(), _paths.FIXTURES_DIR, "*.gdtf", "Standard-Scheinwerfer")


def seed_demo_shows() -> List[str]:
    """Demo-Shows in den Showfile-Ordner legen (einmalig). Eine Demo-Show nennt Scheinwerfer-Typen aus defaults/fixtures (gleicher Dateiname)."""
    return _seed(_paths.default_shows_dir(), _paths.SHOWFILES_DIR, "*.json", "Demo-Shows")


def seed_all() -> dict:
    """Beide Vorlagenarten; Fehler brechen den Programmstart nie ab."""
    out = {}
    for name, function in (("fixtures", seed_default_fixtures), ("showfiles", seed_demo_shows)):
        try:
            out[name] = function()
        except Exception:
            logger.exception("[Defaults] Vorlagen (%s) konnten nicht angelegt werden", name)
            out[name] = []
    return out
