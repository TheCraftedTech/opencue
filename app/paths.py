"""
paths.py
Zentrale Pfadverwaltung von OpenCue.

Schreibbare Benutzerdaten (Konfiguration, Shows, Layouts, Fixtures) liegen
immer unter %LOCALAPPDATA%\\OpenCue (Windows) bzw. ~/.opencue (Linux/macOS).
app_config.json ist der Bootstrapping-Anker und liegt immer im Standard-
Konfigurationsverzeichnis - auch wenn ein benutzerdefinierter Datenpfad gesetzt ist.
"""
from __future__ import annotations

import json
import logging
import os
import shutil
import sys
from pathlib import Path

logger = logging.getLogger("opencue.paths")


def _default_data_root() -> Path:
    """Windows: %LOCALAPPDATA%\\OpenCue  |  Fallback (Linux/macOS Dev): ~/.opencue"""
    local = os.environ.get("LOCALAPPDATA", "")
    if local:
        return Path(local) / "OpenCue"
    return Path.home() / ".opencue"


# Config-Verzeichnis liegt IMMER am Standard-Ort (Bootstrapping-Anker).
_CONFIG_DIR: Path = _default_data_root() / "config"
_CONFIG_DIR.mkdir(parents=True, exist_ok=True)

APP_CONFIG_PATH: Path = _CONFIG_DIR / "app_config.json"


def _load_custom_data_root() -> Path | None:
    """Liest nur custom_data_path aus app_config.json (vor StateManager-Init)."""
    if not APP_CONFIG_PATH.exists():
        return None
    try:
        raw = json.loads(APP_CONFIG_PATH.read_text(encoding="utf-8-sig")).get("custom_data_path", "")
        if raw and isinstance(raw, str):
            p = Path(raw)
            if p.is_absolute():
                return p
    except Exception:
        pass
    return None


def get_data_root() -> Path:
    """Gibt den effektiven Datenpfad zurück (benutzerdefiniert oder Standard)."""
    custom = _load_custom_data_root()
    return custom if custom is not None else _default_data_root()


def _ensure_data_dirs(root: Path) -> tuple[Path, Path, Path]:
    sf  = root / "showfiles"
    lay = root / "layouts"
    fix = root / "fixtures"
    for d in (sf, lay, fix):
        d.mkdir(parents=True, exist_ok=True)
    return sf, lay, fix


# Modul-globale Pfad-Variablen - bei refresh_paths() aktualisiert.
SHOWFILES_DIR: Path
LAYOUTS_DIR: Path
FIXTURES_DIR: Path

SHOWFILES_DIR, LAYOUTS_DIR, FIXTURES_DIR = _ensure_data_dirs(get_data_root())


def refresh_paths() -> None:
    """Aktualisiert SHOWFILES_DIR/LAYOUTS_DIR/FIXTURES_DIR nach Pfadänderung.
    Muss nach dem Setzen von custom_data_path und erneutem save_app_config() aufgerufen werden.
    """
    global SHOWFILES_DIR, LAYOUTS_DIR, FIXTURES_DIR
    SHOWFILES_DIR, LAYOUTS_DIR, FIXTURES_DIR = _ensure_data_dirs(get_data_root())


def defaults_dir() -> Path:
    """Mitgelieferte Vorlagen im Programmordner (defaults/): nur lesen, nie beschreiben. Siehe defaults/README.md."""
    return _project_root() / "defaults"


def default_effects_dir() -> Path:
    """Mitgelieferte Effekt-Skripte (defaults/effects/*.fx)."""
    return defaults_dir() / "effects"


def default_layouts_dir() -> Path:
    """Mitgelieferte Beispiel-Layouts (defaults/layouts/*.json)."""
    return defaults_dir() / "layouts"


def default_fixtures_dir() -> Path:
    """Mitgelieferte Standard-Scheinwerfer (defaults/fixtures/*.gdtf)."""
    return defaults_dir() / "fixtures"


def default_shows_dir() -> Path:
    """Mitgelieferte Demo-Shows (defaults/showfiles/*.json)."""
    return defaults_dir() / "showfiles"


def project_effects_dir() -> Path:
    """Alter Name von default_effects_dir()."""
    return default_effects_dir()


def themes_dir() -> Path:
    """Ordner fuer Farbprofile (Themes, je Profil eine .json) - im aktuellen Datenverzeichnis; der Dateimanager zeigt ihn als Art 'Farben'."""
    directory = get_data_root() / "themes"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def effects_dir() -> Path:
    """Ordner fuer Effekt-Skripte (.fx) - im aktuellen Datenverzeichnis."""
    directory = get_data_root() / "effects"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _project_root() -> Path:
    """Projektordner - bei PyInstaller-Builds sys._MEIPASS, sonst Repo-Root."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent


def project_root() -> Path:
    """Ordner mit den mitgelieferten Dateien (static/, templates/, defaults/, ffmpeg): im Quelltext der Repo-Ordner, im PyInstaller-Build sys._MEIPASS (<Programmordner>/_internal).
    Alle Zugriffe auf mitgelieferte Dateien laufen hierueber, nie ueber __file__."""
    return _project_root()


def migrate_legacy_data() -> None:
    """Kopiert alte Dateien aus dem Projektordner (Vorversion) ins AppData-Verzeichnis.
    Einmalig: überschreibt keine vorhandenen Zieldateien.
    """
    project = _project_root()

    mappings: list[tuple[Path, Path]] = [
        (project / "app_config.json", APP_CONFIG_PATH),
        (project / "showfiles",       SHOWFILES_DIR),
        (project / "panel_layouts",   LAYOUTS_DIR),
        (project / "fixtures",        FIXTURES_DIR),
    ]

    for src, dst in mappings:
        if not src.exists():
            continue
        if src.is_file():
            if not dst.exists():
                try:
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, dst)
                    logger.info("[Paths] Migrated %s -> %s", src.name, dst)
                except Exception as exc:
                    logger.warning("[Paths] Migration failed for %s: %s", src, exc)
        elif src.is_dir():
            for f in src.glob("*"):
                if not f.is_file():
                    continue
                target = dst / f.name
                if not target.exists():
                    try:
                        shutil.copy2(f, target)
                        logger.info("[Paths] Migrated %s -> %s", f.name, dst)
                    except Exception as exc:
                        logger.warning("[Paths] Migration failed for %s: %s", f, exc)


# Läuft einmalig beim Modul-Import – BEVOR state_manager.py OpenCueState
# instanziiert, damit load_app_config() die migrierten Daten vorfindet.
migrate_legacy_data()
