# Copyright (C) 2026 Samuel Zenker
# SPDX-License-Identifier: GPL-3.0-or-later
"""
fixture_manager.py
Verwaltung verfuegbarer Fixture-Typen fuer OpenCue.

GDTF-Dateien (ZIP mit description.xml) im fixtures/-Ordner werden ueber die
offizielle "pygdtf"-Bibliothek (https://github.com/open-stage/python-gdtf,
PyPI: pygdtf) eingelesen. Diese loest DMXChannel -> LogicalChannel ->
Attribute korrekt auf (inkl. Mehrbyte-Kanaelen wie 16-Bit Pan/Tilt und
Geometrie-Referenzen) - ein manueller XML-Parser liest bei GDTF-Dateien
faelschlich das "Geometry"-Attribut statt des tatsaechlichen Kanalnamens,
der erst im verschachtelten <LogicalChannel Attribute="..."> steht.
Drei eingebaute generische Geraete (Dimmer, RGBW-Par, Moving Head; ohne 3D-Modell) stehen immer bereit - auch neben GDTF-Dateien; heisst eine GDTF-Datei genauso, gilt sie.
"""
from __future__ import annotations

import json
import logging
import os
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pygdtf

from app import paths as _paths


FALLBACK_FIXTURES: List[Dict[str, Any]] = [
    {
        "id": "__generic_dimmer",
        "name": "Generic Dimmer",
        "manufacturer": "Generic",
        "short_name": "DIM",
        "channel_count": 1,
        "modes": [{"name": "default", "channel_count": 1, "channels": [{"name": "Dimmer", "offset": 0}]}],
        "source": "builtin",
    },
    {
        "id": "__generic_rgbw_par",
        "name": "Generic RGBW LED Par",
        "manufacturer": "Generic",
        "short_name": "RGBW",
        "channel_count": 4,
        "modes": [
            {
                "name": "default",
                "channel_count": 4,
                # Standard-GDTF-Attributnamen (additive Farbmischung) statt
                # freier Namen wie "Red" - so greift die Programmer->DMX-
                # Aufloesung in server.py (sucht gezielt nach ColorAdd_R/G/B).
                "channels": [
                    {"name": "ColorAdd_R", "offset": 0},
                    {"name": "ColorAdd_G", "offset": 1},
                    {"name": "ColorAdd_B", "offset": 2},
                    {"name": "ColorAdd_W", "offset": 3},
                ],
            }
        ],
        "source": "builtin",
    },
    {
        "id": "__generic_moving_head",
        "name": "Generic Moving Head Spot 16ch",
        "manufacturer": "Generic",
        "short_name": "MH16",
        "channel_count": 16,
        "modes": [
            {
                "name": "default",
                "channel_count": 16,
                "channels": [
                    {"name": "Pan", "offset": 0, "physical_from": -270.0, "physical_to": 270.0},
                    {"name": "PanFine", "offset": 1},
                    {"name": "Tilt", "offset": 2, "physical_from": -135.0, "physical_to": 135.0},
                    {"name": "TiltFine", "offset": 3},
                    {"name": "PositionMSpeed", "offset": 4},
                    {"name": "Dimmer", "offset": 5},
                    {"name": "Shutter1", "offset": 6},
                    {"name": "Color1", "offset": 7},
                    {"name": "Gobo1", "offset": 8},
                    {"name": "Gobo1Pos", "offset": 9},
                    {"name": "Focus1", "offset": 10},
                    {"name": "Prism1", "offset": 11},
                    {"name": "Iris", "offset": 12},
                    {"name": "Frost1", "offset": 13},
                    {"name": "FixtureGlobalReset", "offset": 14},
                    {"name": "Reserved", "offset": 15},
                ],
            }
        ],
        "source": "builtin",
    },
]


def _parse_gdtf(path: Path) -> Dict[str, Any]:
    """Parst eine GDTF-Datei ueber pygdtf und gibt Fixture-Metadaten zurueck.

    Pro DMX-Modus werden alle echten (nicht-virtuellen) Kanaele mit ihrem
    tatsaechlichen Attribut-Namen (z.B. "Pan", "Dimmer", "ColorSub_C" - aus
    <LogicalChannel Attribute="..."> aufgeloest, inkl. Geometrie-Referenzen
    und Mehrbyte-Kanaelen) sowie ihrem 0-indizierten Offset innerhalb des
    Modus extrahiert. "channel_count" kommt aus pygdtf's dmx_channels_count
    (= tatsaechliche Byte-Fussabdruckgroesse, z.B. 2 Bytes fuer 16-Bit Pan),
    nicht aus der Anzahl der Kanal-EINTRAEGE - sonst wuerden beim Patchen
    mehrerer Fixtures des gleichen Typs die DMX-Adressbereiche ueberlappen.
    """
    try:
        fixture = pygdtf.FixtureType(str(path))
        fixture.__exit__(None, None, None)   # XML ist eingelesen; das ZIP-Handle sofort freigeben (unter Windows blockiert es sonst das Loeschen der Datei)

        modes: List[Dict[str, Any]] = []
        for mode in fixture.dmx_modes:
            # Deklarierter Byte-Footprint aus pygdtf (0 = nicht verfuegbar).
            declared_count = mode.dmx_channels_count or 0
            channels = []
            for ch in mode.dmx_channels:
                if not ch.offset or not ch.logical_channels:
                    continue  # virtueller Kanal - belegt keine echte DMX-Adresse
                coarse_off = ch.offset[0] - 1
                entry: Dict[str, Any] = {"name": str(ch.logical_channels[0].attribute), "offset": coarse_off}
                # Physikalischer Wertebereich (z.B. Pan -270..+270 Grad) aus der
                # ersten ChannelFunction - fuer Grad-Anzeige im Position-Tab.
                channel_functions = ch.logical_channels[0].channel_functions
                if channel_functions:
                    cf = channel_functions[0]
                    try:
                        entry["physical_from"] = float(cf.physical_from.value)
                        entry["physical_to"] = float(cf.physical_to.value)
                    except (AttributeError, TypeError, ValueError):
                        pass
                channels.append(entry)
                # 16-Bit-Kanal: Fein-Byte nur aufnehmen wenn er einen eigenen
                # Slot belegt und (falls deklariert) innerhalb des Footprints
                # liegt - verhindert Ghost-Zellen durch fehlerhafte GDTF-Offsets.
                if len(ch.offset) >= 2:
                    fine_off = ch.offset[1] - 1
                    if fine_off != coarse_off and (declared_count == 0 or fine_off < declared_count):
                        channels.append({"name": str(ch.logical_channels[0].attribute) + "Fine", "offset": fine_off})
            channels.sort(key=lambda c: c["offset"])
            # Footprint = max(deklarierter Wert, tatsaechlicher Max-Offset+1).
            # Korrigiert dmx_channels_count-Fehler in GDTF-Dateien (z.B. zaehlt
            # manche pygdtf-Version logische Kanaele statt Bytes) ohne Ghost-Zellen
            # durch Out-of-range-Offsets zu erzeugen.
            max_off = channels[-1]["offset"] if channels else -1
            footprint = max(declared_count, max_off + 1) or 1
            modes.append({
                "name": mode.name or "default",
                "channel_count": footprint,
                "channels": channels,
            })

        if not modes:
            modes = [{"name": "default", "channel_count": 1, "channels": []}]

        return {
            "id": path.stem,
            "name": fixture.name or path.stem,
            "manufacturer": fixture.manufacturer or path.stem.split("@")[0].strip(),
            "short_name": (fixture.short_name or fixture.name or path.stem)[:8],
            "long_name": fixture.long_name or "",
            "channel_count": modes[0]["channel_count"],
            "modes": modes,
            "source": "gdtf",
            "file": path.name,
        }
    except Exception as exc:
        return {
            "id": path.stem,
            "name": path.stem,
            "short_name": path.stem[:8],
            "channel_count": 1,
            "modes": [{"name": "default", "channels": []}],
            "source": "gdtf",
            "file": path.name,
            "error": str(exc),
        }


def gdtf_paths() -> List[Path]:
    """Alle GDTF-Dateien der Bibliothek (fixtures/)."""
    chosen = {p.stem: p for p in _paths.FIXTURES_DIR.glob("*.gdtf")}
    return [chosen[k] for k in sorted(chosen, key=lambda s: (s.lower(), s))]


_fixture_types_cache: Optional[List[Dict[str, Any]]] = None
_fixture_types_cache_key: Optional[tuple] = None
_parsed_files: Dict[str, Tuple[Tuple[float, int], Dict[str, Any]]] = {}      # Pfad -> ((mtime, Groesse), Ergebnis von _parse_gdtf): jede Datei wird nur neu gelesen, wenn SIE sich aendert


# ---- Zwischenspeicher auf der Platte: <Datenordner>/cache/gdtf_types.json {"version", "files": {Dateiname: {"key": [mtime, Groesse], "data": <Ergebnis von _parse_gdtf>}}}.
# Gilt nur, wenn Datei (Zeit + Groesse), Cache-Version (CACHE_VERSION: bei jeder Aenderung von _parse_gdtf hochzaehlen) und pygdtf-Version passen; Fehlerergebnisse werden nie gemerkt.
CACHE_VERSION = 1
_disk_lock = threading.Lock()
_disk: Optional[Dict[str, Any]] = None
_disk_dirty = False
_disk_logger = logging.getLogger("opencue.gdtf")


def _disk_path() -> Path:
    return _paths.get_data_root() / "cache" / "gdtf_types.json"


def _disk_load() -> Dict[str, Any]:
    global _disk
    if _disk is None:
        _disk = {}
        try:
            data = json.loads(_disk_path().read_text(encoding="utf-8"))
            if data.get("version") == CACHE_VERSION and data.get("pygdtf") == getattr(pygdtf, "__version__", "?") and isinstance(data.get("files"), dict):
                _disk = data["files"]
        except (OSError, ValueError, AttributeError):
            pass
    return _disk


def flush_parse_cache(existing: Optional[List[str]] = None) -> None:
    """Geaenderten Zwischenspeicher auf die Platte schreiben (existing: Dateinamen, die es noch gibt - der Rest wird vergessen)."""
    global _disk_dirty
    with _disk_lock:
        files = _disk_load()
        if existing is not None:
            for name in [n for n in files if n not in existing]:
                files.pop(name, None)
                _disk_dirty = True
        if not _disk_dirty:
            return
        try:
            target = _disk_path()
            target.parent.mkdir(parents=True, exist_ok=True)
            partial = target.with_suffix(".part")
            partial.write_text(json.dumps({"version": CACHE_VERSION, "pygdtf": getattr(pygdtf, "__version__", "?"), "files": files}, ensure_ascii=False), encoding="utf-8")
            os.replace(partial, target)
            _disk_dirty = False
        except OSError as exc:
            _disk_logger.warning("GDTF-Zwischenspeicher konnte nicht geschrieben werden: %s", exc)


def _parse_gdtf_cached(path: Path) -> Dict[str, Any]:
    """pygdtf braucht bei grossen Dateien (LED-Leisten mit vielen Pixeln) bis zu 13 s: jede Datei wird nur neu gelesen, wenn SIE sich aendert - im Speicher und (ueber Programmstarts
    hinweg) auf der Platte. Ein neu eingebautes GDTF darf nicht dazu fuehren, dass die ganze Bibliothek noch einmal gelesen wird."""
    global _disk_dirty
    try:
        stat = path.stat()
        key = (stat.st_mtime, stat.st_size)
    except OSError:
        return _parse_gdtf(path)
    cached = _parsed_files.get(str(path))
    if cached is not None and cached[0] == key:
        return cached[1]
    with _disk_lock:
        entry = _disk_load().get(path.name)
    if isinstance(entry, dict) and entry.get("key") == [key[0], key[1]] and isinstance(entry.get("data"), dict):
        _parsed_files[str(path)] = (key, entry["data"])
        return entry["data"]
    result = _parse_gdtf(path)
    _parsed_files[str(path)] = (key, result)
    if "error" not in result:
        with _disk_lock:
            _disk_load()[path.name] = {"key": [key[0], key[1]], "data": result}
            _disk_dirty = True
    return result


def get_fixture_types() -> List[Dict[str, Any]]:
    """Alle verfuegbaren Fixture-Typen: GDTF-Dateien aus fixtures/ oder Fallbacks.

    WICHTIG: Wird bei jedem Fader-Update im Programmer aufgerufen (ueber
    get_fixture_type_by_id -> Kanal-Aufloesung fuer set_fixture_values), also
    potenziell 30-60x/Sekunde waehrend eines Drags. Ohne Cache wuerde JEDE
    GDTF-Datei (ZIP + XML via pygdtf) bei JEDEM Aufruf synchron neu geparst -
    das blockiert den asyncio-Event-Loop und war die Hauptursache fuer das
    "Einfrieren"/Aufstauen des DMX-Signals bei schnellen Fader-Bewegungen.
    Der Cache wird ueber einen billigen (Dateiname, mtime)-Schluessel
    invalidiert, sodass neue/geaenderte .gdtf-Dateien trotzdem erkannt werden,
    ohne bei jedem Aufruf neu geparst werden zu muessen.
    """
    global _fixture_types_cache, _fixture_types_cache_key
    gdtf_files = gdtf_paths()
    cache_key = tuple((str(p), p.stat().st_mtime) for p in gdtf_files)
    if _fixture_types_cache is not None and cache_key == _fixture_types_cache_key:
        return _fixture_types_cache

    result = [_parse_gdtf_cached(p) for p in gdtf_files]
    flush_parse_cache([p.name for p in gdtf_files])
    taken = {str(item.get("name", "")).strip().lower() for item in result}
    result += [dict(item) for item in FALLBACK_FIXTURES if str(item["name"]).strip().lower() not in taken]       # die eingebauten Generic-Geraete (ohne 3D-Modell) gibt es immer, solange keine GDTF-Datei denselben Namen hat
    _fixture_types_cache = result
    _fixture_types_cache_key = cache_key
    # Wheels-Cache mitinvalidieren, wenn sich GDTF-Dateien geaendert haben.
    _fixture_wheels_cache.clear()
    _fixture_channel_info_cache.clear()
    _fixture_shutter_cache.clear()
    _fixture_beamfx_cache.clear()
    return result


_by_id: Dict[str, Any] = {"stamp": None, "checked": 0.0, "index": {}}


def get_fixture_type_by_id(fixture_type_id: str) -> Optional[Dict[str, Any]]:
    """Einen Fixture-Typ nach seiner ID zurueckgeben. Heisser Pfad (jede Fader-Bewegung, jeder Blackout, je Scheinwerfer): ein Index statt einer Suche ueber alle Typen, und ob sich
    GDTF-Dateien geaendert haben, wird hoechstens einmal je Sekunde geprueft (get_fixture_types() prueft jede Datei). Ein unbekannter Typ wird sofort frisch nachgeschlagen."""
    import time as _time
    now = _time.monotonic()
    cache = _by_id
    if not cache["index"] or now - cache["checked"] > 1.0:
        types = get_fixture_types()
        if cache["stamp"] is not types:
            cache["index"] = {ft["id"]: ft for ft in types}
            cache["stamp"] = types
        cache["checked"] = now
    found = cache["index"].get(fixture_type_id)
    if found is None and now - cache["checked"] > 0.0:
        types = get_fixture_types()
        cache["index"] = {ft["id"]: ft for ft in types}
        cache["stamp"] = types
        cache["checked"] = now
        found = cache["index"].get(fixture_type_id)
    return found


_fixture_wheels_cache: Dict[str, List[Dict[str, Any]]] = {}
_fixture_channel_info_cache: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}


# ---- Abgeleitete Typdaten (Raeder, Shutter, Gobo-/Prismenkanaele, Kanalliste): Jede dieser Abfragen musste frueher die GANZE GDTF-Datei neu durch pygdtf lesen (LED-Leisten bis 10 s je Abfrage,
# vier Abfragen je Typ, alle direkt in der Ereignisschleife des Servers: ein Programmstart mit einer grossen Show stand deshalb eine Minute still). Jetzt:
#  - alle vier Ergebnisse eines Typs entstehen in EINEM Durchgang (die Datei wird einmal gelesen; gleichzeitige Abfragen warten auf dieselbe Arbeit),
#  - das Lesen laeuft in einem eigenen Hilfsprozess (main.py --gdtf-worker): der XML-Leser von pygdtf haelt die Sperre des Interpreters Sekunden lang, ein Thread haette den Server trotzdem angehalten,
#  - die fertigen Ergebnisse stehen auf der Platte (<Datenordner>/cache/gdtf_derived/<Art>/<Typ>.json, gueltig nur fuer Datei-Zeit + Groesse, DERIVED_VERSION und pygdtf-Version), ein Neustart liest nichts mehr.
DERIVED_VERSION = 1
_MAX_PARSED_OBJECTS = 3
_KINDS = ("wheels", "channels", "shutter", "beamfx")
_EMPTY = {"wheels": [], "channels": {}, "shutter": {}, "beamfx": {}}
_ft_objects: "Dict[str, Tuple[Tuple[float, int], Any]]" = {}
_ft_guard = threading.Lock()
_ft_locks: Dict[str, threading.Lock] = {}
_path_override: Dict[str, Path] = {}               # Typ -> Datei (im Hilfsprozess: dort gibt es keinen Datenordner der Konfiguration)


class _Unreadable(Exception):
    """Die GDTF-Datei laesst sich nicht lesen: das Ergebnis ist leer, wird aber nicht auf der Platte gemerkt."""


def _find_gdtf(fixture_id: str) -> Optional[Path]:
    return _path_override.get(fixture_id) or next((p for p in gdtf_paths() if p.stem == fixture_id), None)


def _file_key(path: Path) -> Tuple[float, int]:
    stat = path.stat()
    return (stat.st_mtime, stat.st_size)


def _lock_for(name: str) -> threading.Lock:
    with _ft_guard:
        lock = _ft_locks.get(name)
        if lock is None:
            lock = _ft_locks[name] = threading.Lock()
        return lock


def _load_fixture_type(path: Path) -> Any:
    """pygdtf-Objekt einer Datei, je Prozess einmal gelesen (die letzten paar bleiben im Speicher)."""
    try:
        key = _file_key(path)
    except OSError as exc:
        raise _Unreadable(str(exc))
    with _lock_for("file:" + str(path)):
        with _ft_guard:
            hit = _ft_objects.get(str(path))
        if hit is not None and hit[0] == key:
            return hit[1]
        try:
            fixture = pygdtf.FixtureType(str(path))
            fixture.__exit__(None, None, None)        # ZIP-Handle freigeben (Windows: sonst nicht loeschbar)
        except Exception as exc:
            raise _Unreadable(str(exc))
        with _ft_guard:
            _ft_objects[str(path)] = (key, fixture)
            while len(_ft_objects) > _MAX_PARSED_OBJECTS:
                _ft_objects.pop(next(iter(_ft_objects)))
        return fixture


def _compute_all_here(fixture_id: str, path: Path) -> Optional[Dict[str, Any]]:
    """Alle vier Ergebnisse eines Typs in diesem Prozess berechnen (None: Datei nicht lesbar)."""
    _path_override[fixture_id] = path
    try:
        return {"wheels": _compute_wheels(fixture_id), "channels": _compute_channel_info(fixture_id), "shutter": _compute_shutter(fixture_id), "beamfx": _compute_beamfx(fixture_id)}
    except _Unreadable:
        return None
    finally:
        _path_override.pop(fixture_id, None)


def worker_main(argv: List[str]) -> int:
    """Hilfsprozess (main.py --gdtf-worker <Typ> <Datei>): berechnet die Typdaten und schreibt sie als JSON nach stdout."""
    import sys
    result = _compute_all_here(argv[0], Path(argv[1]))
    sys.stdout.write(json.dumps(result, ensure_ascii=False))
    sys.stdout.flush()
    return 0


def _worker_command(fixture_id: str, path: Path) -> List[str]:
    import sys
    if getattr(sys, "frozen", False):
        return [sys.executable, "--gdtf-worker", fixture_id, str(path)]
    return [sys.executable, str(Path(__file__).resolve().parent.parent / "main.py"), "--gdtf-worker", fixture_id, str(path)]


def _compute_all(fixture_id: str, path: Path) -> Optional[Dict[str, Any]]:
    """Im Hilfsprozess berechnen; geht das nicht (Prozess startet nicht, Ausgabe unbrauchbar), im eigenen Prozess."""
    import subprocess
    try:
        done = subprocess.run(_worker_command(fixture_id, path), capture_output=True, timeout=900, creationflags=0x08000000 if os.name == "nt" else 0)
        if done.returncode == 0 and done.stdout:
            data = json.loads(done.stdout.decode("utf-8"))
            if data is None or (isinstance(data, dict) and all(k in data for k in _KINDS)):
                return data
        _disk_logger.warning("GDTF-Hilfsprozess fuer %s lieferte nichts Brauchbares (Code %s)", fixture_id, done.returncode)
    except Exception as exc:
        _disk_logger.warning("GDTF-Hilfsprozess fuer %s nicht moeglich (%s) - es wird im Hauptprozess gelesen", fixture_id, exc)
    return _compute_all_here(fixture_id, path)


def _memory(kind: str) -> Dict[str, Any]:
    return {"wheels": _fixture_wheels_cache, "channels": _fixture_channel_info_cache, "shutter": _fixture_shutter_cache, "beamfx": _fixture_beamfx_cache}[kind]


def _derived_file(kind: str, fixture_id: str) -> Path:
    safe = "".join(c if c.isalnum() or c in "-_.@ " else "_" for c in fixture_id)
    return _paths.get_data_root() / "cache" / "gdtf_derived" / kind / (safe + ".json")


def _ensure_derived(fixture_id: str) -> None:
    """Alle vier Ergebnisse des Typs in den Speicher bringen: von der Platte (wenn die Datei unveraendert ist), sonst berechnen und auf der Platte merken."""
    path = _find_gdtf(fixture_id)
    if path is None:
        for kind in _KINDS:
            _memory(kind)[fixture_id] = _EMPTY[kind]
        return
    try:
        key = _file_key(path)
    except OSError:
        return
    stamp = {"v": DERIVED_VERSION, "pygdtf": getattr(pygdtf, "__version__", "?"), "key": [key[0], key[1]]}
    missing = []
    for kind in _KINDS:
        try:
            entry = json.loads(_derived_file(kind, fixture_id).read_text(encoding="utf-8"))
            if isinstance(entry, dict) and all(entry.get(k) == v for k, v in stamp.items()) and "data" in entry:
                _memory(kind)[fixture_id] = entry["data"]
                continue
        except (OSError, ValueError):
            pass
        missing.append(kind)
    if not missing:
        return
    results = _compute_all(fixture_id, path)
    if results is None:
        for kind in missing:
            _memory(kind)[fixture_id] = _EMPTY[kind]               # nicht lesbar: leer, aber nie auf der Platte merken
        return
    for kind in missing:
        _memory(kind)[fixture_id] = results[kind]
        target = _derived_file(kind, fixture_id)
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            partial = target.with_suffix(".part")
            partial.write_text(json.dumps(dict(stamp, data=results[kind]), ensure_ascii=False), encoding="utf-8")
            os.replace(partial, target)
        except (OSError, TypeError, ValueError) as exc:
            _disk_logger.warning("GDTF-Zwischenspeicher (%s) konnte nicht geschrieben werden: %s", kind, exc)


def _derived(kind: str, fixture_id: str) -> Any:
    memory = _memory(kind)
    if fixture_id in memory:
        return memory[fixture_id]
    with _lock_for("all:" + fixture_id):
        if fixture_id not in memory:
            _ensure_derived(fixture_id)
        return memory.get(fixture_id, _EMPTY[kind])


def get_fixture_channel_info(fixture_id: str) -> Dict[str, List[Dict[str, Any]]]:
    return _derived("channels", fixture_id)


def get_fixture_wheels(fixture_id: str) -> List[Dict[str, Any]]:
    return _derived("wheels", fixture_id)


def get_fixture_beamfx(fixture_id: str) -> Dict[str, Dict[str, Any]]:
    return _derived("beamfx", fixture_id)


def get_fixture_shutter(fixture_id: str) -> Dict[str, List[Dict[str, Any]]]:
    return _derived("shutter", fixture_id)


def _coarse(value: Any) -> Optional[int]:
    """DMX-Wert einer GDTF-Angabe als 8-Bit-Wert (bei 16/24 Bit das hoechste Byte)."""
    raw = getattr(value, "value", None)
    if raw is None:
        return None
    try:
        count = max(1, int(getattr(value, "byte_count", 1) or 1))
        return max(0, min(255, int(raw) >> (8 * (count - 1))))
    except (TypeError, ValueError):
        return None


def _closed_ranges(items: List[Dict[str, Any]]) -> None:
    """Setzt bei jedem Eintrag das Ende (bis zum Anfang des naechsten - 1, der letzte bis 255)."""
    items.sort(key=lambda it: it["from"])
    for index, item in enumerate(items):
        item["to"] = max(item["from"], items[index + 1]["from"] - 1) if index + 1 < len(items) else 255


def _compute_channel_info(fixture_id: str) -> Dict[str, List[Dict[str, Any]]]:
    """Lesbare Kanal-Beschreibung je Modus (Detail-Ansicht im DMX-Direct-Regler): Kanal-Offset, Attribut, schoener Attributname, Funktionen mit DMX-Bereichen und deren benannte Stufen."""
    result: Dict[str, List[Dict[str, Any]]] = {}
    path = _find_gdtf(fixture_id)
    if path is not None:
        try:
            fixture = _load_fixture_type(path)
            pretty = {str(a.name): str(a.pretty or "") for a in fixture.attributes}
            for mode in fixture.dmx_modes:
                rows: List[Dict[str, Any]] = []
                for ch in mode.dmx_channels:
                    if not ch.offset or not ch.logical_channels:
                        continue
                    logical = ch.logical_channels[0]
                    functions: List[Dict[str, Any]] = []
                    for cf in (logical.channel_functions or [])[:40]:
                        start = _coarse(cf.dmx_from)
                        sets: List[Dict[str, Any]] = []
                        for cs in (cf.channel_sets or [])[:64]:
                            s_from = _coarse(cs.dmx_from)
                            if s_from is not None and str(cs.name or "").strip():
                                sets.append({"name": str(cs.name).strip(), "from": s_from})
                        _closed_ranges(sets)
                        functions.append({"name": str(cf.name or "").strip(), "attribute": str(cf.attribute or ""), "from": 0 if start is None else start, "sets": sets})
                    _closed_ranges(functions)
                    attr = str(logical.attribute)
                    rows.append({"offset": int(ch.offset[0]) - 1, "attribute": attr, "pretty": pretty.get(attr, ""), "bytes": len(ch.offset),
                                 "default": _coarse(ch.default), "functions": functions})
                rows.sort(key=lambda r: r["offset"])
                result[mode.name or "default"] = rows
        except _Unreadable:
            raise
        except Exception:
            result = {}
    return result


def _compute_wheels(fixture_id: str) -> List[Dict[str, Any]]:
    """Extrahiert Wheel-Slot-Daten (Gobo/Farbe/Prism) inkl. DMX-Bereiche und Base64-Bilder.

    Liest Wheel-Definitionen (Slots + media_file_name) sowie die zugehoerigen
    ChannelSets (genaue DMX-Bereiche pro Slot) aus der GDTF-Datei. Bilder werden
    direkt aus dem wheels/-Ordner des ZIP gelesen und als data:-URI zurueckgegeben.
    """
    import base64
    import zipfile

    gdtf_path = _find_gdtf(fixture_id)
    if gdtf_path is None:
        return []

    ft = _load_fixture_type(gdtf_path)

    # Pro Wheel-Name: ChannelSets (exakte DMX-Bereiche), Attributname des
    # logischen Kanals (z.B. "Gobo1", "Gobo2", "Color1") und Kanal-Offset.
    # Erste Fundstelle pro Wheel-Name gewinnt (wird aus dem ersten DMX-Mode
    # gelesen, spaetere Modi koennen andere Offsets haben - aber fuers
    # Frontend-Mapping genuegt der erste vollstaendig definierende Kanal).
    wheel_ch_info: Dict[str, Dict[str, Any]] = {}
    for mode in ft.dmx_modes:
        for ch in mode.dmx_channels:
            if not ch.logical_channels or not ch.offset:
                continue
            lc = ch.logical_channels[0]
            attr_name = str(lc.attribute)
            offset = ch.offset[0] - 1
            for cf in lc.channel_functions:
                wobj = getattr(cf, "wheel", None)
                wname = str(wobj) if wobj else ""
                if wname and wname not in wheel_ch_info:
                    wheel_ch_info[wname] = {
                        "attribute_name": attr_name,
                        "channel_offset": offset,
                        "channel_sets": list(cf.channel_sets) if cf.channel_sets else [],
                    }

    # Bilder aus dem ZIP (max. 100 kB pro Bild; grosse Rad-Uebersichten ueberspringen)
    images: Dict[str, str] = {}
    try:
        with zipfile.ZipFile(str(gdtf_path)) as z:
            for entry in z.namelist():
                if not entry.startswith("wheels/") or entry == "wheels/":
                    continue
                fname = entry[len("wheels/"):]
                if z.getinfo(entry).file_size > 100_000:
                    continue
                data = z.read(entry)
                ext = fname.rsplit(".", 1)[-1].lower() if "." in fname else "png"
                mime = "image/svg+xml" if ext == "svg" else "image/png"
                images[fname] = "data:" + mime + ";base64," + base64.b64encode(data).decode()
    except Exception:
        pass

    result: List[Dict[str, Any]] = []
    for wheel in ft.wheels:
        wname = wheel.name
        wname_l = wname.lower()
        if "gobo" in wname_l:
            wtype = "gobo"
        elif "color" in wname_l or "colour" in wname_l:
            wtype = "color"
        elif "prism" in wname_l:
            wtype = "prism"
        elif "animation" in wname_l:
            wtype = "animation"
        else:
            wtype = "other"

        ch_info = wheel_ch_info.get(wname, {})
        csets = ch_info.get("channel_sets", [])
        cset_by_slot: Dict[int, Any] = {}
        for cs in csets:
            wsi = getattr(cs, "wheel_slot_index", None)
            # Erste Fundstelle pro Slot-Index gewinnt (Shake/Rotation-Varianten
            # teilen denselben wheel_slot_index wie ihr Basis-Gobo -> ueberspringen).
            if wsi is not None and wsi not in cset_by_slot:
                cset_by_slot[wsi] = cs

        n_slots = len(wheel.wheel_slots) or 1
        slots: List[Dict[str, Any]] = []
        for i, slot in enumerate(wheel.wheel_slots):
            slot_idx = i + 1
            mfn = str(slot.media_file_name) if slot.media_file_name else ""
            cs = cset_by_slot.get(slot_idx)
            if cs:
                dmx_from = int(cs.dmx_from.value)
                dmx_to = int(cs.dmx_to.value)
            else:
                dmx_from = max(0, slot_idx * 256 // n_slots - 256 // n_slots)
                dmx_to = min(255, slot_idx * 256 // n_slots - 1)
            dmx_center = max(0, min(255, (dmx_from + dmx_to) // 2))
            slots.append({
                "name": slot.name,
                "index": slot_idx,
                "dmx_from": dmx_from,
                "dmx_to": dmx_to,
                "dmx_center": dmx_center,
                "image": images.get(mfn),
            })

        result.append({
            "name": wname,
            "type": wtype,
            "attribute_name": ch_info.get("attribute_name", ""),
            "channel_offset": ch_info.get("channel_offset", None),
            "slots": slots,
        })

    # Farbe (CIE xyY -> sRGB) und Prismen-Facetten je Slot aus der description.xml (siehe app/gdtf_model.py); pygdtf liefert sie nicht brauchbar
    try:
        from app import gdtf_model
        extra = {w["name"]: w["slots"] for w in gdtf_model.structure(gdtf_path)["wheels"]}
        for wheel in result:
            slots_extra = extra.get(wheel["name"], [])
            for index, slot in enumerate(wheel["slots"]):
                more = slots_extra[index] if index < len(slots_extra) else {}
                slot["color"] = more.get("color")
                slot["facets"] = more.get("facets", 0)
    except Exception:
        pass

    return result


_fixture_shutter_cache: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}


def _classify_shutter(attribute: str, set_name: str) -> str:
    """Art eines Shutter-Bereichs: closed | open | strobe | pulse_in | pulse_out | random (Name der Funktion/des Bereichs, sonst offen)."""
    text = f"{attribute} {set_name}".lower()
    if "random" in text or "rnd" in text:
        return "random"
    if "pulseclose" in text or "pulse close" in text or "pulse out" in text or "pulseout" in text:
        return "pulse_out"
    if "pulseopen" in text or "pulse open" in text or "pulse in" in text or "pulsein" in text:
        return "pulse_in"
    if "strobe" in text or "pulse" in text:
        return "strobe"
    if "clos" in text or "off" in text or "black" in text:
        return "closed"
    return "open"


_fixture_beamfx_cache: Dict[str, Dict[str, Dict[str, Any]]] = {}


def _classify_beamfx(role: str, attribute: str, set_name: str, prism: bool) -> str:
    """Art eines DMX-Bereichs eines Gobo-/Prismenkanals: slot (festes Gobo/Prisma) | shake | scroll (Rad laeuft durch die Gobos) | spin (Dauerdrehung, Vorzeichen = Richtung) |
    index (Drehwinkel) | selectspin (Auswahl+Drehung auf einem Kanal ohne Angaben in der Datei)."""
    text = f"{attribute} {set_name}".lower()
    if role == "select":
        if "shake" in text:
            return "shake"
        if attribute.endswith(("WheelSpin", "WheelRandom", "WheelAudio")) or any(k in text for k in ("rotat", "scroll", "random", "audio")):
            return "scroll"
        return "slot"
    if attribute.endswith("SelectSpin"):
        return "selectspin"
    if attribute.endswith(("Rotate", "Spin")) or "rotat" in text:
        return "spin"
    if attribute.endswith(("Pos", "Index")) or "index" in text:
        return "index"
    return "spin" if "spin" in text else "index"


def _compute_beamfx(fixture_id: str) -> Dict[str, Dict[str, Any]]:
    """Gobo-/Prismenkanaele eines Typs (erster DMX-Modus, der solche Kanaele hat): {Kanalattribut: {role: select|spin, type: gobo|prism, wheel: Radname, ranges: [{from, to, kind, slot, name,
    phys: [von, bis]}]}}. select = Kanal, der den Slot des Rads waehlt (Gobo1, Prism1; slot = Nummer im Rad ab 1); spin = Drehung/Position des Rads (Gobo1SelectSpin, Prism1Pos, Prism1PosRotate ...).
    kind siehe _classify_beamfx; phys = physikalische Werte der Datei (Winkel oder Drehgeschwindigkeit, Vorzeichen = Richtung)."""
    result: Dict[str, Dict[str, Any]] = {}
    gdtf_path = _find_gdtf(fixture_id)
    if gdtf_path is None:
        return result
    ft = _load_fixture_type(gdtf_path)
    num = lambda v: float(getattr(v, "value", v) or 0.0)           # noqa: E731 - GDTF-Werte sind kleine Wert-Objekte
    for mode in ft.dmx_modes:
        found = False
        for ch in mode.dmx_channels:
            if not ch.logical_channels or not ch.offset:
                continue
            attribute = str(ch.logical_channels[0].attribute)
            if not attribute.startswith(("Gobo", "Prism")) or attribute in result:
                continue
            found = True
            prism = attribute.startswith("Prism")
            role = "select" if attribute.rstrip("0123456789") in ("Gobo", "Prism") else "spin"
            bytes_ = len(ch.offset)
            ranges: List[Dict[str, Any]] = []
            wheel_name = ""
            for cf in ch.logical_channels[0].channel_functions:
                function_attribute = str(cf.attribute)
                wheel = getattr(cf, "wheel", None)
                if wheel is not None and not wheel_name:
                    wheel_name = str(getattr(wheel, "name", wheel))
                sets = list(cf.channel_sets or []) or [None]
                for cs in sets:
                    lo = num(cs.dmx_from if cs is not None else cf.dmx_from)
                    hi = num(cs.dmx_to if cs is not None else cf.dmx_to)
                    if bytes_ > 1:                                   # auf ein Byte (grob) abbilden
                        lo, hi = lo / 256 ** (bytes_ - 1), hi / 256 ** (bytes_ - 1)
                    name = str(cs.name) if cs is not None and cs.name else str(cf.name or function_attribute)
                    p0 = num(cs.physical_from if cs is not None else cf.physical_from)
                    p1 = num(cs.physical_to if cs is not None else cf.physical_to)
                    slot = int(getattr(cs, "wheel_slot_index", 0) or 0) if cs is not None else 0
                    ranges.append({"from": int(lo), "to": int(hi), "kind": _classify_beamfx(role, function_attribute, name, prism), "slot": slot, "name": name, "phys": [round(p0, 3), round(p1, 3)]})
            ranges.sort(key=lambda r: r["from"])
            result[attribute] = {"role": role, "type": "prism" if prism else "gobo", "wheel": wheel_name, "ranges": ranges}
        if found:
            break
    return result


def _compute_shutter(fixture_id: str) -> Dict[str, List[Dict[str, Any]]]:
    """DMX-Bereiche der Shutter-/Strobe-Kanaele eines Typs: {Kanalattribut: [{from, to, kind, hz: [von, bis]}]} (aus dem ersten DMX-Modus, der solche Kanaele hat).
    kind: closed | open | strobe | pulse_in | pulse_out | random; hz = Blitzfrequenz am Anfang/Ende des Bereichs (GDTF: Einheit Hz; ohne Angabe 1-20 Hz); name = Name des Bereichs."""
    result: Dict[str, List[Dict[str, Any]]] = {}
    gdtf_path = _find_gdtf(fixture_id)
    if gdtf_path is None:
        return result
    ft = _load_fixture_type(gdtf_path)
    num = lambda v: float(getattr(v, "value", v) or 0.0)           # noqa: E731 - GDTF-Werte sind kleine Wert-Objekte
    for mode in ft.dmx_modes:
        for ch in mode.dmx_channels:
            if not ch.logical_channels or not ch.offset:
                continue
            attribute = str(ch.logical_channels[0].attribute)
            if not attribute.startswith("Shutter") or attribute in result:
                continue
            ranges: List[Dict[str, Any]] = []
            bytes_ = len(ch.offset)
            for cf in ch.logical_channels[0].channel_functions:
                function_attribute = str(cf.attribute)
                sets = list(cf.channel_sets or [])
                if not sets:
                    sets = [None]
                for cs in sets:
                    lo = num(cs.dmx_from if cs is not None else cf.dmx_from)
                    hi = num(cs.dmx_to if cs is not None else cf.dmx_to)
                    if bytes_ > 1:                                   # auf ein Byte (grob) abbilden
                        lo, hi = lo / 256 ** (bytes_ - 1), hi / 256 ** (bytes_ - 1)
                    kind = _classify_shutter(function_attribute, str(cs.name) if cs is not None else "")
                    p0 = num(cs.physical_from if cs is not None else cf.physical_from)
                    p1 = num(cs.physical_to if cs is not None else cf.physical_to)
                    in_hz = kind in ("strobe", "pulse_in", "pulse_out", "random") and max(p0, p1) > 1.5
                    name = str(cs.name) if cs is not None and cs.name else str(cf.name or function_attribute)
                    ranges.append({"from": int(lo), "to": int(hi), "kind": kind, "name": name, "hz": [round(p0, 3), round(p1, 3)] if in_hz else [1.0, 20.0]})
            ranges.sort(key=lambda r: r["from"])
            result[attribute] = ranges
    return result
