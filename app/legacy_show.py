"""
legacy_show.py
EINMALIGE Umwandlung alter Showfiles. Fruehere Fassungen schrieben Dateien direkt in die Show: Scheinwerfer-GDTF (Base64, "fixture_files"), Effekt-Skripte ("fx_scripts"),
Medien (Base64, "media[..].data", dazu "link_path"/"embed") und die Koerper der 3D-Buehne ("sim_stage.objects"). Heute enthaelt die Show nur noch ihre eigenen Daten; die Dateien
liegen in den lokalen Ordnern. unpack() legt beim Laden einer alten Show alles Eingebettete dort ab (vorhandene lokale Dateien bleiben unveraendert) und entfernt die alten
Schluessel aus den Daten. Sobald alle alten Shows einmal geladen und neu gespeichert sind, kann dieses Modul samt dem Aufruf in state_manager.load_showfile entfallen.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import logging
import os
from pathlib import Path
from typing import Any, Dict

from app import paths as _paths

logger = logging.getLogger("opencue.legacy")


def _decode(entry: Any, limit: int) -> bytes | None:
    """Bytes eines Base64-Eintrags {data, sha256?}; None bei Fehler/zu gross/falscher Pruefsumme."""
    if not isinstance(entry, dict) or not isinstance(entry.get("data"), str) or not entry["data"]:
        return None
    try:
        raw = base64.b64decode(entry["data"], validate=True)
    except (binascii.Error, ValueError):
        return None
    if len(raw) > limit:
        return None
    expected = entry.get("sha256")
    if isinstance(expected, str) and expected and hashlib.sha256(raw).hexdigest() != expected.lower():
        return None
    return raw


def _write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name("." + path.name + ".part")
    try:
        partial.write_bytes(data)
        os.replace(partial, path)
    finally:
        if partial.exists():
            partial.unlink()


def unpack(data: Dict[str, Any]) -> Dict[str, int]:
    """Wandelt `data` (eine geladene Showfile) in das heutige Format um und legt eingebettete Dateien lokal ab. Rueckgabe: Anzahl je Art (leer = war schon das neue Format)."""
    done: Dict[str, int] = {}
    if not isinstance(data, dict):
        return done

    fixtures = data.pop("fixture_files", None)
    if isinstance(fixtures, dict):
        from app import fixture_library, fixture_manager
        for key, entry in fixtures.items():
            fixture_id = str(entry.get("id", key)) if isinstance(entry, dict) else str(key)
            target = _paths.FIXTURES_DIR / f"{fixture_id}.gdtf"
            if not fixture_id or fixture_id != Path(fixture_id).name or target.exists():
                continue
            raw = _decode(entry, fixture_library.MAX_GDTF_BYTES)
            if raw is None:
                continue
            try:
                fixture_library._inspect_gdtf(raw)
                _write(target, raw)
                done["fixtures"] = done.get("fixtures", 0) + 1
            except Exception as exc:
                logger.warning("Altformat: Scheinwerfer-Datei %s uebersprungen (%s)", fixture_id, exc)
        if done.get("fixtures"):
            fixture_manager.get_fixture_types()

    scripts = data.pop("fx_scripts", None)
    if isinstance(scripts, dict):
        from app.fx_script import compile_script, valid_script_name
        for key, entry in scripts.items():
            name = str(entry.get("name", key)) if isinstance(entry, dict) else str(key)
            text = entry.get("text") if isinstance(entry, dict) else None
            target = _paths.effects_dir() / f"{name}.fx"
            if not valid_script_name(name) or not isinstance(text, str) or not text or target.exists():
                continue
            raw = text.encode("utf-8")
            expected = entry.get("sha256")
            if isinstance(expected, str) and expected and hashlib.sha256(raw).hexdigest() != expected.lower():
                continue
            try:
                compile_script(name, text)
                _write(target, raw)
                done["effects"] = done.get("effects", 0) + 1
            except Exception as exc:
                logger.warning("Altformat: Effekt-Skript %s uebersprungen (%s)", name, exc)

    media = data.get("media")
    if isinstance(media, dict):
        from app import media_store
        for key in list(media):
            entry = media[key]
            if not isinstance(entry, dict) or entry.get("link_path"):
                media.pop(key, None)                                        # verknuepfte Medien gibt es nicht mehr
                continue
            raw = _decode(entry, media_store.MAX_FILE_BYTES)
            target = media_store.path_for(str(entry.get("id", "")))
            if raw is not None and target is not None and not target.exists() and hashlib.sha256(raw).hexdigest() == entry.get("id"):
                _write(target, raw)
                done["media"] = done.get("media", 0) + 1
            for obsolete in ("data", "embed", "link_path"):
                entry.pop(obsolete, None)

    stage = data.get("sim_stage")
    if isinstance(stage, dict) and "objects" in stage:
        from app import sim_stages
        objects = sim_stages.normalize_objects(stage.pop("objects"))
        filename = stage.get("filename") if sim_stages.valid_filename(stage.get("filename")) else None
        try:
            if filename and (sim_stages.library_dir() / filename).is_file():
                pass                                                         # die lokale Datei gilt
            elif not objects:
                stage["filename"] = None                                     # leere Buehne: keine Datei noetig
            else:
                base = sim_stages.clean_name(stage.get("name"), sim_stages.suggest_name())
                name, n = base, 2
                while (sim_stages.library_dir() / sim_stages.filename_for(name)).exists():
                    name, n = f"{base} ({n})", n + 1
                stage["filename"] = sim_stages.write_file(name, objects, overwrite=False)
                stage["name"] = name
                done["stages"] = done.get("stages", 0) + 1
        except sim_stages.StageError:
            stage["filename"] = None

    if done:
        logger.info("Altformat umgewandelt: %s", done)
    return done
