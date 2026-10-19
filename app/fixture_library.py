"""
fixture_library.py
Scheinwerfer-Bibliothek: installierte GDTF-Dateien verwalten (Liste, Vorschau, Import, Loeschen) und die Fixture-Datenbank
GDTF Share durchsuchen und daraus installieren.

GDTF Share (https://gdtf-share.com) ist die offizielle, kostenlose Sammelstelle fuer GDTF-Dateien. Ihre Schnittstelle
(/apis/public/login.php, getList.php, downloadFile.php) braucht ein kostenloses Konto: ohne Anmeldung antwortet sie mit 401.
Das Passwort wird deshalb nur fuer die laufende Sitzung im Arbeitsspeicher gehalten (nie gespeichert); angemeldet bleibt eine
Sitzung ueber das PHPSESSID-Cookie, das hier nur im Prozess lebt.

Die Dateien landen im Fixture-Ordner der Anwendung (paths.FIXTURES_DIR) und heissen wie bei GDTF Share
"Hersteller@Name@Revision.gdtf"; der Dateiname (ohne Endung) ist zugleich die Fixture-Typ-ID der Show.

Netzwerkzugriffe laufen nur gegen den festen Host (SHARE_BASE), mit Zeitlimit und Groessengrenze; heruntergeladene Dateien
werden vor dem Einbau als ZIP mit gueltiger description.xml geprueft und mit pygdtf einmal komplett eingelesen. Es wird nie
etwas aus einem ZIP entpackt; Dateinamen werden aus den Metadaten gebildet, nie aus Namen im Archiv.
"""
from __future__ import annotations

import http.cookiejar
import json
import os
import re
import shutil
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pygdtf
from xml.etree import ElementTree

from app import fixture_manager
from app import gdtf_model
from app import paths as _paths

SHARE_BASE = os.environ.get("OPENCUE_GDTF_SHARE_URL", "https://gdtf-share.com").rstrip("/")
HTTP_TIMEOUT = 25.0
MAX_GDTF_BYTES = 30 * 1024 * 1024          # groesser ist keine GDTF-Datei, die wir einbauen wollen
MAX_UNPACKED_BYTES = 200 * 1024 * 1024     # Schutz vor ZIP-Bomben (Summe der entpackten Groessen laut Verzeichnis)
LIST_MAX_AGE = 30 * 60.0                   # die Liste von GDTF Share wird so lange im Speicher gehalten
USER_AGENT = "OpenCue-FixtureLibrary/1.0"

CATEGORIES = ["moving_head", "led_bar", "par", "dimmer", "strobe", "effect", "other"]


class LibraryError(Exception):
    """Fehler mit maschinenlesbarem Code (code) fuer die Oberflaeche und lesbarem Text (message)."""

    def __init__(self, code: str, message: str = "", status: int = 400, **extra: Any) -> None:
        super().__init__(message or code)
        self.code, self.message, self.status, self.extra = code, message or code, status, extra


# ---------------------------------------------------------------------------------------------- Kategorien

_TEXT_RULES: List[Tuple[str, Tuple[str, ...]]] = [
    ("dimmer", ("dimmer", "dimmerpack", "dim pack")),
    ("strobe", ("strobe", "blinder")),
    ("effect", ("fog", "haze", "smoke", "laser", "derby", "effect", "bubble", "snow")),
    ("led_bar", ("bar", "batten", "strip", "pixel", "tube", "ledbar", "linear")),
    ("moving_head", ("moving", "mover", "spot", "beam", "profile", "scanner", "tmh", "mh-", "sharpy", "wash")),
    ("par", ("par", "flood", "led wash", "fresnel", "cyc")),
]


def category_from_text(name: str, manufacturer: str = "") -> str:
    """Grobe Einordnung nur aus dem Namen (fuer Eintraege von GDTF Share, deren Kanaele wir noch nicht kennen)."""
    text = f" {name} {manufacturer} ".lower()
    words = set(re.findall(r"[a-z0-9]+", text))
    for category, keys in _TEXT_RULES:
        for key in keys:
            if (" " in key or "-" in key) and key in text:
                return category
            if key in words or (len(key) >= 4 and key in text and key not in ("wash", "beam", "spot", "bar")):
                return category
    return "other"


def category_from_channels(attribute_names: List[str], fallback_text: str = "") -> str:
    """Einordnung aus den echten Kanaelen (Pan/Tilt -> Moving Head, nur Dimmer -> Dimmer, ...)."""
    names = [str(n) for n in attribute_names]
    base = {n[:-4] if n.endswith("Fine") else n for n in names}
    if base & {"Pan", "Tilt"}:
        return "moving_head"
    reds = sum(1 for n in names if n in ("ColorAdd_R", "ColorRGB_Red", "Red"))
    cmy = sum(1 for n in names if n.startswith("ColorSub_C"))
    if reds >= 3 or cmy >= 3:
        return "led_bar"
    if any(n.startswith(("ColorAdd", "ColorSub", "ColorRGB", "Color")) or n in ("Red", "Green", "Blue") for n in names):
        return "par"
    if base and base <= {"Dimmer"}:
        return "dimmer"
    if base & {"Strobe", "Shutter1", "StrobeMode"} and not (base - {"Dimmer", "Strobe", "Shutter1", "StrobeMode"}):
        return "strobe"
    if base & {"Fog", "Haze", "Smoke", "Fan"}:
        return "effect"
    return category_from_text(fallback_text)


# -------------------------------------------------------------------------------------------- Dateinamen

def sanitize_part(text: str) -> str:
    """Wie bei GDTF Share ueblich: Leerzeichen -> Unterstrich, nur sichere Zeichen."""
    cleaned = re.sub(r"[^\w\-.+()]+", "_", str(text or "").strip(), flags=re.UNICODE).strip("._")
    return cleaned[:60] or "x"


def install_id(manufacturer: str, name: str, revision: str) -> str:
    return "@".join((sanitize_part(manufacturer), sanitize_part(name), sanitize_part(revision or "Rev")))


def _normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(text or "").lower())


# ----------------------------------------------------------------------------------------- installierte Dateien

def _path_for(fixture_id: str, scope: str = "library") -> Path:
    """Pfad der installierten Datei - nur fuer eine ID, die es als Datei im Ordner gibt (keine Pfadteile moeglich). scope bleibt aus Kompatibilitaet (die Show hat keine eigenen Kopien mehr)."""
    if not fixture_id or fixture_id != Path(fixture_id).name or "/" in fixture_id or "\\" in fixture_id:
        raise LibraryError("not_found", "Unbekannter Scheinwerfertyp", 404)
    for path in _paths.FIXTURES_DIR.glob("*.gdtf"):
        if path.stem == fixture_id:
            return path
    raise LibraryError("not_found", "Unbekannter Scheinwerfertyp", 404)


def _revision_of(stem: str) -> str:
    parts = stem.split("@")
    return parts[2] if len(parts) >= 3 else ""


def installed_entries(usage: Optional[Dict[str, int]] = None) -> List[Dict[str, Any]]:
    """Alle installierten GDTF-Dateien mit Metadaten fuer die Liste (Name, Hersteller, Modi, Kategorie, Groesse, Nutzung)."""
    usage = usage or {}
    entries: List[Dict[str, Any]] = []
    parsed = {ft["id"]: ft for ft in fixture_manager.get_fixture_types() if ft.get("source") == "gdtf"}
    for path in sorted(_paths.FIXTURES_DIR.glob("*.gdtf"), key=lambda p: p.stem.lower()):
        ft = parsed.get(path.stem) or fixture_manager._parse_gdtf(path)
        modes = ft.get("modes") or []
        main = max(modes, key=lambda m: len(m.get("channels", [])), default={"channels": []})
        names = [c["name"] for c in main.get("channels", [])]
        stat = path.stat()
        entries.append({
            "id": path.stem,
            "name": ft.get("name") or path.stem,
            "manufacturer": ft.get("manufacturer") or path.stem.split("@")[0],
            "revision": _revision_of(path.stem),
            "modes": [{"name": m.get("name", ""), "channel_count": m.get("channel_count", 0)} for m in modes],
            "channel_count": ft.get("channel_count", 0),
            "category": category_from_channels(names, f"{ft.get('name', '')} {ft.get('manufacturer', '')}") if names else category_from_text(path.stem),
            "size": stat.st_size,
            "installed_at": int(stat.st_mtime),
            "file": path.name,
            "has_thumbnail": _thumbnail_name(path) is not None,
            "in_use": int(usage.get(path.stem, 0)),
            "error": ft.get("error"),
        })
    return entries


def _thumbnail_name(path: Path) -> Optional[str]:
    try:
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
            head = archive.read("description.xml")[:4000].decode("utf-8", "replace") if "description.xml" in names else ""
    except (OSError, zipfile.BadZipFile, KeyError):
        return None
    match = re.search(r'<FixtureType\b[^>]*\bThumbnail="([^"]+)"', head)
    stem = match.group(1) if match else ""
    for candidate in (f"{stem}.png", f"{stem}.svg") if stem else ():
        if candidate in names:
            return candidate
    for name in names:
        if "/" not in name and name.lower().endswith(".png"):
            return name
    return None


def thumbnail(fixture_id: str, scope: str = "library") -> Tuple[bytes, str, int]:
    """Vorschaubild (PNG oder SVG) aus der GDTF-Datei, dazu Typ und Aenderungszeit (fuer den Browser-Cache)."""
    path = _path_for(fixture_id, scope)
    name = _thumbnail_name(path)
    if name is None:
        raise LibraryError("no_thumbnail", "Kein Vorschaubild", 404)
    with zipfile.ZipFile(path) as archive:
        info = archive.getinfo(name)
        if info.file_size > 2 * 1024 * 1024:
            raise LibraryError("no_thumbnail", "Vorschaubild zu gross", 404)
        data = archive.read(name)
    return data, ("image/svg+xml" if name.lower().endswith(".svg") else "image/png"), int(path.stat().st_mtime)


def _num(value: Any) -> Optional[float]:
    """pygdtf kapselt Zahlen teils in Objekte mit .value (DMX-Werte, physikalische Werte); None wenn nichts Brauchbares."""
    raw = getattr(value, "value", value)
    try:
        number = float(raw)
    except (TypeError, ValueError):
        return None
    return number if number == number and abs(number) != float("inf") else None


def _dmx(value: Any) -> Optional[int]:
    number = _num(value)
    return None if number is None else int(round(number))


def _nice(number: Optional[float]) -> Optional[float]:
    return None if number is None else round(number, 3)


MAX_DETAIL_CHANNELS = 600
MAX_DETAIL_FUNCTIONS = 40
MAX_DETAIL_SETS = 64


def details(fixture_id: str, scope: str = "library") -> Dict[str, Any]:
    """Alles Lesbare aus einer installierten GDTF-Datei fuer den Detail-Dialog: Stammdaten, physikalische Angaben, Modi mit allen
    DMX-Kanaelen (Adresse, Attribut, Funktionen mit DMX-Bereichen, Kanalsets), Raeder, Verweise auf 3D-Modelle in der Datei."""
    path = _path_for(fixture_id, scope)
    try:
        fixture = pygdtf.FixtureType(str(path))
        fixture.__exit__(None, None, None)
    except Exception as exc:
        raise LibraryError("invalid_file", f"Die Datei konnte nicht gelesen werden ({type(exc).__name__})", 422)
    try:
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
    except (OSError, zipfile.BadZipFile):
        names = []
    pretty = {str(a.name): (a.pretty or "") for a in fixture.attributes}
    feature = {str(a.name): str(a.feature or "") for a in fixture.attributes}
    props = fixture.properties
    revisions = [{"text": r.text or "", "date": str(r.date or "")} for r in (fixture.revisions or [])][-5:]
    modes: List[Dict[str, Any]] = []
    truncated = False
    for mode in fixture.dmx_modes:
        channels: List[Dict[str, Any]] = []
        for ch in mode.dmx_channels:
            if not ch.offset or not ch.logical_channels:
                continue                                     # virtueller Kanal: belegt keine DMX-Adresse
            if len(channels) >= MAX_DETAIL_CHANNELS:
                truncated = True
                break
            logical = ch.logical_channels[0]
            attr = str(logical.attribute)
            functions = []
            for cf in logical.channel_functions[:MAX_DETAIL_FUNCTIONS]:
                low, high = _dmx(cf.dmx_from), _dmx(cf.dmx_to)
                phys_from, phys_to = _nice(_num(cf.physical_from)), _nice(_num(cf.physical_to))
                sets = []
                for cs in (cf.channel_sets or [])[:MAX_DETAIL_SETS]:
                    sets.append({"name": str(cs.name or ""), "from": _dmx(cs.dmx_from), "to": _dmx(cs.dmx_to),
                                 "physical_from": _nice(_num(cs.physical_from)), "physical_to": _nice(_num(cs.physical_to))})
                functions.append({"name": str(cf.name or ""), "attribute": str(cf.attribute or ""), "from": low, "to": high,
                                  "physical_from": phys_from, "physical_to": phys_to, "default": _dmx(cf.default),
                                  "wheel": "" if str(getattr(cf, "wheel", None)) in ("None", "") else str(cf.wheel), "sets": sets,
                                  "sets_truncated": len(cf.channel_sets or []) > MAX_DETAIL_SETS})
            channels.append({"offset": [int(o) for o in ch.offset], "attribute": attr, "pretty": pretty.get(attr, ""),
                             "feature": feature.get(attr, ""), "geometry": str(ch.geometry or ""),
                             "bytes": len(ch.offset), "default": _dmx(ch.default),
                             "highlight": _dmx(ch.highlight) if ch.highlight is not None else None,
                             "functions": functions, "functions_truncated": len(logical.channel_functions) > MAX_DETAIL_FUNCTIONS})
        channels.sort(key=lambda c: c["offset"][0])
        modes.append({"name": mode.name or "default", "description": mode.description or "", "geometry": str(mode.geometry or ""),
                      "channel_count": mode.dmx_channels_count or (max((max(c["offset"]) for c in channels), default=0)),
                      "channels": channels})
    return {
        "id": fixture_id, "scope": scope, "name": fixture.name or fixture_id, "long_name": fixture.long_name or "", "short_name": fixture.short_name or "",
        "manufacturer": fixture.manufacturer or "", "description": fixture.description or "", "data_version": str(fixture.data_version or ""),
        "fixture_type_id": str(fixture.fixture_type_id or ""), "revisions": revisions,
        "physical": {"weight": _nice(_num(getattr(props, "weight", None))),
                     "temp_low": _nice(_num(getattr(props, "operating_temperature_low", None))),
                     "temp_high": _nice(_num(getattr(props, "operating_temperature_high", None))),
                     "leg_height": _nice(_num(getattr(props, "leg_height", None)))} if props is not None else {},
        "wheels": [{"name": str(w.name or ""), "slots": len(w.wheel_slots or [])} for w in (fixture.wheels or [])],
        "emitters": len(fixture.emitters or []), "geometries": len(fixture.geometries or []),
        "structure": _structure(path),
        "modes": modes, "size": path.stat().st_size, "has_thumbnail": _thumbnail_name(path) is not None, "truncated": truncated,
        "category": category_from_channels([c["attribute"] for c in (max(modes, key=lambda m: len(m["channels"]), default={"channels": []})["channels"])],
                                           f"{fixture.name or ''} {fixture.manufacturer or ''}"),
    }


def _structure(path: Path) -> Dict[str, Any]:
    """Raeder (Gobos/Farben/Prismen mit Bildern), Optik und Modell-Uebersicht aus app/gdtf_model.py; ein Fehler dort laesst den Rest des Dialogs leben."""
    try:
        return gdtf_model.structure(path)
    except Exception as exc:
        return {"wheels": [], "beams": [], "connectors": [], "emitters": [], "models": {"count": 0, "files": 0, "primitives": 0, "reader": gdtf_model.available()},
                "error": f"{type(exc).__name__}"}


def model_scene(fixture_id: str, scope: str = "library") -> Dict[str, Any]:
    """3D-Vorschau eines installierten Typs: Geometrie-Baum + Netze (siehe gdtf_model.scene)."""
    path = _path_for(fixture_id, scope)
    try:
        return gdtf_model.scene(path)
    except gdtf_model.ModelError as exc:
        raise LibraryError("invalid_file", str(exc), 422)
    except Exception as exc:
        raise LibraryError("invalid_file", f"Die 3D-Daten konnten nicht gelesen werden ({type(exc).__name__})", 422)


def asset(fixture_id: str, relative: str, scope: str = "library") -> Tuple[bytes, str, int]:
    """Gobo-/Farbrad-Bild (wheels/*.png|svg) aus der Datei: (Bytes, Inhaltstyp, Aenderungszeit)."""
    path = _path_for(fixture_id, scope)
    try:
        data, media_type = gdtf_model.asset(path, relative)
    except gdtf_model.ModelError as exc:
        raise LibraryError("not_found", str(exc), 404)
    return data, media_type, int(path.stat().st_mtime)


def uninstall(fixture_id: str, usage: Dict[str, int]) -> Dict[str, Any]:
    """Aus der Bibliothek entfernen. Benutzt die geladene Show den Typ, wird nicht geloescht (die Scheinwerfer der Show wuerden ihre Datei verlieren)."""
    path = _path_for(fixture_id)
    used = int(usage.get(fixture_id, 0))
    if used:
        raise LibraryError("in_use", f"Die geladene Show benutzt diesen Typ ({used} Scheinwerfer)", 409)
    path.unlink()
    fixture_manager.get_fixture_types()          # Cache neu aufbauen (Schluessel aus Dateinamen/Zeiten aendert sich)
    return {"ok": True, "id": fixture_id, "pinned": False, "used": used}
def show_types(usage: Dict[str, int]) -> List[Dict[str, Any]]:
    """Die Scheinwerfertypen, die die geladene Show benutzt (Tab 'In dieser Show'): Version, Anzahl und ob die Datei in der Bibliothek liegt. source: 'library' = Datei
    der Bibliothek, 'builtin' = eingebauter Ersatz ohne Datei, 'missing' = Datei fehlt (Show-Export mitnehmen oder die GDTF-Datei importieren)."""
    library = {p.stem: p for p in _paths.FIXTURES_DIR.glob("*.gdtf")}
    result: List[Dict[str, Any]] = []
    for type_id, count in usage.items():
        path = library.get(type_id)
        if path is None:
            builtin = type_id.startswith("__")
            result.append({"id": type_id, "name": type_id.strip("_").replace("_", " ").title() if builtin else type_id, "manufacturer": "", "revision": "",
                           "count": int(count), "source": "builtin" if builtin else "missing", "library": "none", "size": 0, "category": "other", "has_thumbnail": False,
                           "modes": [], "others": []})
            continue
        ft = fixture_manager._parse_gdtf(path)
        modes = ft.get("modes") or []
        main = max(modes, key=lambda m: len(m.get("channels", [])), default={"channels": []})
        names = [c["name"] for c in main.get("channels", [])]
        parts = type_id.split("@")
        others = sorted(p.stem for stem, p in library.items()
                        if stem != type_id and len(parts) >= 2 and stem.split("@")[:2] == parts[:2])        # andere Revisionen desselben Geraets in der Bibliothek
        result.append({
            "id": type_id, "name": ft.get("name") or type_id, "manufacturer": ft.get("manufacturer") or parts[0], "revision": _revision_of(type_id),
            "count": int(count), "source": "library", "library": "same", "size": path.stat().st_size, "has_thumbnail": _thumbnail_name(path) is not None,
            "category": category_from_channels(names, f"{ft.get('name', '')} {ft.get('manufacturer', '')}") if names else category_from_text(type_id),
            "modes": [{"name": m.get("name", ""), "channel_count": m.get("channel_count", 0)} for m in modes], "others": [_revision_of(o) for o in others],
        })
    result.sort(key=lambda r: (r["manufacturer"].lower(), r["name"].lower()))
    return result
# --------------------------------------------------------------------------------------------- Einbau von Dateien

def _inspect_gdtf(data: bytes) -> Dict[str, Any]:
    """Prueft die Bytes als GDTF-Datei und liefert Hersteller/Name/Revision; wirft LibraryError("invalid_file").
    pygdtf ist nachsichtig (bei kaputtem XML oder ohne DMX-Modus erfindet es Ersatzwerte), deshalb wird die description.xml hier
    selbst gelesen und streng geprueft; pygdtf muss die Datei danach zusaetzlich einlesen koennen."""
    if len(data) > MAX_GDTF_BYTES:
        raise LibraryError("too_large", "Die Datei ist zu gross (max. 30 MB)", 413)
    if len(data) < 100 or data[:2] != b"PK":
        raise LibraryError("invalid_file", "Das ist keine GDTF-Datei (kein ZIP-Archiv)", 400)
    tmp_dir = Path(tempfile.mkdtemp(prefix="opencue-gdtf-"))
    try:
        tmp = tmp_dir / "check.gdtf"
        tmp.write_bytes(data)
        try:
            with zipfile.ZipFile(tmp) as archive:
                infos = {i.filename: i for i in archive.infolist()}
                if sum(i.file_size for i in infos.values()) > MAX_UNPACKED_BYTES:
                    raise LibraryError("invalid_file", "Die Datei ist ungewoehnlich gross entpackt", 400)
                info = infos.get("description.xml")
                if info is None:
                    raise LibraryError("invalid_file", "In der Datei fehlt die description.xml", 400)
                if info.file_size > 40 * 1024 * 1024:
                    raise LibraryError("invalid_file", "Die description.xml ist ungewoehnlich gross", 400)
                xml = archive.read("description.xml")
            if b"<!ENTITY" in xml or b"<!DOCTYPE" in xml:
                raise LibraryError("invalid_file", "Die description.xml enthaelt unzulaessige Deklarationen", 400)
            try:
                root = ElementTree.fromstring(xml)
            except ElementTree.ParseError:
                raise LibraryError("invalid_file", "Die description.xml ist kein gueltiges XML", 400)
            ft = root.find("FixtureType") if root.tag == "GDTF" else None
            if ft is None:
                raise LibraryError("invalid_file", "Kein GDTF-Geraetetyp (FixtureType) in der description.xml", 400)
            if not any(m.find("DMXChannels") is not None and m.find("DMXChannels").find("DMXChannel") is not None
                       for m in ft.iterfind("DMXModes/DMXMode")):
                raise LibraryError("invalid_file", "Die GDTF-Datei enthaelt keinen DMX-Modus mit Kanaelen", 400)
            fixture = pygdtf.FixtureType(str(tmp))
            fixture.__exit__(None, None, None)           # Handle freigeben, sonst laesst sich das Temp-Verzeichnis unter Windows nicht loeschen
            if not fixture.dmx_modes:
                raise LibraryError("invalid_file", "Die GDTF-Datei enthaelt keinen DMX-Modus", 400)
        except LibraryError:
            raise
        except Exception as exc:
            raise LibraryError("invalid_file", f"Die GDTF-Datei konnte nicht gelesen werden ({type(exc).__name__})", 400)
        revisions = [r.get("Text", "") for r in ft.iterfind("Revisions/Revision")]
        return {"name": str(ft.get("Name") or ""), "manufacturer": str(ft.get("Manufacturer") or ""),
                "revision": str(revisions[-1]) if revisions else ""}
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def install_bytes(data: bytes, stem_hint: str = "", revision_hint: str = "", usage: Optional[Dict[str, int]] = None, on_conflict: str = "replace") -> Dict[str, Any]:
    """Baut eine GDTF-Datei in den Fixture-Ordner ein. on_conflict bei gleichem Namen: "replace" (ersetzt, so wie das Aktualisieren der Bibliothek) oder "copy" (gleicher Inhalt: nichts
    wird geschrieben, identical=True; anderer Inhalt: unter einem freien Namen "<id> (2)" ...). Rueckgabe: id + ob ersetzt wurde."""
    meta = _inspect_gdtf(data)
    hint = Path(stem_hint).stem if stem_hint else ""
    if hint.count("@") >= 2:
        stem = "@".join(sanitize_part(p) for p in hint.split("@")[:3])
    else:
        stem = install_id(meta["manufacturer"] or "Unbekannt", meta["name"] or hint or "Fixture", revision_hint or "Import")
    target = _paths.FIXTURES_DIR / f"{stem}.gdtf"
    existed = target.exists()
    pinned = False
    original = stem
    if existed and on_conflict == "copy":
        n = 1
        while True:
            try:
                if target.read_bytes() == data:
                    return {"ok": True, "id": stem, "replaced": False, "identical": True, "copied_from": original if stem != original else None,
                            "name": meta["name"], "manufacturer": meta["manufacturer"], "pinned": False}
            except OSError:
                pass
            n += 1
            stem = f"{original} ({n})"
            target = _paths.FIXTURES_DIR / f"{stem}.gdtf"
            if not target.exists():
                break
        existed = False
    _paths.FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    partial = _paths.FIXTURES_DIR / f".{stem}.part"
    try:
        partial.write_bytes(data)
        os.replace(partial, target)
    finally:
        if partial.exists():
            partial.unlink()
    fixture_manager.get_fixture_types()
    return {"ok": True, "id": stem, "replaced": existed, "identical": False, "copied_from": original if on_conflict == "copy" and stem != original else None,
            "name": meta["name"], "manufacturer": meta["manufacturer"], "pinned": pinned}


# ------------------------------------------------------------------------------------- gespeicherte Anmeldung (optional)
# Nur auf ausdruecklichen Wunsch ("Angemeldet bleiben"): die Zugangsdaten werden mit der Windows-Datenschutz-Schnittstelle (DPAPI)
# fuer den aktuellen Windows-Benutzer verschluesselt in einer Datei im Datenordner abgelegt - nie im Klartext, nie in einer Show,
# nie im Browser. Ohne Windows gibt es diese Funktion nicht (dann bleibt das Passwort nur fuer die Sitzung im Speicher).
_ENTROPY = b"OpenCue GDTF Share login v1"


def remember_available() -> bool:
    return os.name == "nt"


def _login_file() -> Path:
    return _paths.FIXTURES_DIR.parent / "gdtf_share_login.bin"


def _dpapi(data: bytes, protect: bool) -> bytes:
    import ctypes
    from ctypes import wintypes

    class Blob(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

    crypt32, kernel32 = ctypes.windll.crypt32, ctypes.windll.kernel32
    function = crypt32.CryptProtectData if protect else crypt32.CryptUnprotectData
    function.argtypes = [ctypes.POINTER(Blob), ctypes.c_void_p, ctypes.POINTER(Blob), ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(Blob)]
    function.restype = wintypes.BOOL
    kernel32.LocalFree.argtypes = [ctypes.c_void_p]
    buffer = ctypes.create_string_buffer(data, len(data))
    entropy = ctypes.create_string_buffer(_ENTROPY, len(_ENTROPY))
    blob_in = Blob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_char)))
    blob_entropy = Blob(len(_ENTROPY), ctypes.cast(entropy, ctypes.POINTER(ctypes.c_char)))
    blob_out = Blob()
    if not function(ctypes.byref(blob_in), None, ctypes.byref(blob_entropy), None, None, 0, ctypes.byref(blob_out)):
        raise OSError("DPAPI nicht verfuegbar oder Daten gehoeren einem anderen Benutzer")
    try:
        return ctypes.string_at(blob_out.pbData, blob_out.cbData)
    finally:
        kernel32.LocalFree(blob_out.pbData)


def save_login(user: str, password: str) -> bool:
    if not remember_available():
        return False
    try:
        blob = _dpapi(json.dumps({"user": user, "password": password}).encode("utf-8"), True)
        target = _login_file()
        partial = target.with_suffix(".part")
        partial.write_bytes(blob)
        os.replace(partial, target)
        return True
    except OSError:
        return False


def load_login() -> Optional[Dict[str, str]]:
    if not remember_available() or not _login_file().is_file():
        return None
    try:
        data = json.loads(_dpapi(_login_file().read_bytes(), False).decode("utf-8"))
        return {"user": str(data["user"]), "password": str(data["password"])}
    except (OSError, ValueError, KeyError, TypeError):
        return None


def forget_login() -> None:
    try:
        _login_file().unlink()
    except OSError:
        pass


def remembered_user() -> str:
    """Nur der Benutzername der gespeicherten Anmeldung (fuer das Formular); nie das Passwort."""
    saved = load_login()
    return saved["user"] if saved else ""


# ------------------------------------------------------------------------------------------------ GDTF Share

class RateLimiter:
    """Gleitendes Fenster: hoechstens `calls` Aufrufe je `seconds` und Schluessel (z. B. Client-Adresse)."""

    def __init__(self, calls: int, seconds: float) -> None:
        self.calls, self.seconds = calls, seconds
        self._hits: Dict[str, List[float]] = {}
        self._lock = threading.Lock()

    def check(self, key: str) -> float:
        """0.0 = erlaubt (und gezaehlt), sonst die Sekunden bis wieder ein Aufruf frei ist."""
        now = time.monotonic()
        with self._lock:
            recent = [t for t in self._hits.get(key, []) if now - t < self.seconds]
            if len(recent) >= self.calls:
                self._hits[key] = recent
                return max(0.1, self.seconds - (now - recent[0]))
            recent.append(now)
            self._hits[key] = recent
            if len(self._hits) > 500:                       # alte Schluessel nicht ewig behalten
                self._hits = {k: v for k, v in self._hits.items() if v and now - v[-1] < self.seconds}
            return 0.0


# Schutz der eigenen Schnittstelle (je Client-Adresse): normale Bedienung bleibt weit darunter, ein haengender Browser oder ein
# Skript wird gebremst. Anmelden strenger (auch gegen Raten von Zugangsdaten).
LIMITS: Dict[str, Tuple[int, float]] = {"search": (120, 10.0), "install": (12, 60.0), "login": (8, 60.0), "details": (60, 10.0)}
_limiters: Dict[str, RateLimiter] = {}
# Gegenueber GDTF Share selbst: Mindestabstand zwischen zwei Anfragen und zwischen zwei Downloads; die Liste wird zwischengespeichert,
# 'Liste aktualisieren' hoechstens alle REFRESH_MIN_INTERVAL Sekunden wirklich neu geladen.
OUTBOUND_MIN_INTERVAL = 1.0
DOWNLOAD_MIN_INTERVAL = 2.0
REFRESH_MIN_INTERVAL = 60.0
BACKOFF_DEFAULT = 30.0
BACKOFF_MAX = 300.0


def throttle(kind: str, key: str) -> None:
    calls, seconds = LIMITS[kind]
    limiter = _limiters.get(kind)
    if limiter is None or (limiter.calls, limiter.seconds) != (calls, seconds):
        limiter = _limiters[kind] = RateLimiter(calls, seconds)
    wait = limiter.check(key or "?")
    if wait:
        raise LibraryError("rate_limited", f"Zu viele Anfragen - bitte {int(wait) + 1} s warten", 429, retry_after=int(wait) + 1)


_VERIFIED_KEYS = ("verified", "isVerified", "is_verified", "manufacturerVerified", "manufacturer_verified", "verifiedByManufacturer",
                  "officialByManufacturer", "official", "approved")


def _verified_flag(raw: Dict[str, Any]) -> Optional[bool]:
    """Hersteller-verifiziert? True/False, wenn die Liste dazu etwas sagt, sonst None (Feldnamen bei GDTF Share nicht dokumentiert)."""
    for key in _VERIFIED_KEYS:
        if key in raw and raw[key] not in (None, ""):
            value = raw[key]
            if isinstance(value, str):
                return value.strip().lower() in ("1", "true", "yes", "ja", "verified", "official", "approved")
            return bool(value)
    for key in ("status", "state", "verification"):
        value = raw.get(key)
        if isinstance(value, str) and value:
            return value.strip().lower() in ("verified", "official", "approved", "manufacturer verified")
    return None


def _date_key(text: str) -> Tuple[int, Any]:
    try:
        return (1, float(text))
    except (TypeError, ValueError):
        return (0, str(text or ""))


def _rid_key(rid: Any) -> Tuple[int, Any]:
    return (1, int(rid)) if str(rid).isdigit() else (0, str(rid))


def _version_key(item: Dict[str, Any]) -> Tuple[Any, Any]:
    return (_date_key(item["modified"] or item["created"]), _rid_key(item["rid"]))


class GdtfShareClient:
    """Sitzung bei GDTF Share (Cookie im Speicher), Liste mit Zwischenspeicher, Download mit Groessengrenze, Rate-Limit + Backoff."""

    def __init__(self) -> None:
        self._lock = threading.RLock()          # Sitzungszustand (Anmelden/Abmelden/Liste)
        self._net_lock = threading.Lock()       # Netzzugriffe nacheinander (ein Download zur Zeit), mit Mindestabstand
        self._last_request = 0.0
        self._last_download = 0.0
        self._blocked_until = 0.0               # GDTF Share hat 429/503 gemeldet: bis dahin keine Anfragen
        self._reset()

    def _reset(self) -> None:
        self._jar = http.cookiejar.CookieJar()
        self._opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self._jar))
        self.user = ""
        self.logged_in = False
        self._list: Optional[List[Dict[str, Any]]] = None
        self._list_at = 0.0

    # ---- HTTP
    def _request(self, path: str, body: Optional[bytes] = None, content_type: str = "", max_bytes: int = 64 * 1024 * 1024,
                 download: bool = False) -> Tuple[int, bytes]:
        remaining = self._blocked_until - time.monotonic()
        if remaining > 0:                                              # Server hat um Geduld gebeten: gar nicht erst anfragen
            raise LibraryError("rate_limited", f"GDTF Share bittet um Geduld - bitte {int(remaining) + 1} s warten", 429, retry_after=int(remaining) + 1)
        request = urllib.request.Request(SHARE_BASE + path, data=body, headers={"User-Agent": USER_AGENT, "Accept": "application/json, */*"})
        if content_type:
            request.add_header("Content-Type", content_type)
        with self._net_lock:
            spacing = max(OUTBOUND_MIN_INTERVAL - (time.monotonic() - self._last_request),
                          (DOWNLOAD_MIN_INTERVAL - (time.monotonic() - self._last_download)) if download else 0.0)
            if spacing > 0:
                time.sleep(spacing)
            try:
                try:
                    with self._opener.open(request, timeout=HTTP_TIMEOUT) as response:
                        data = response.read(max_bytes + 1)
                        if len(data) > max_bytes:
                            raise LibraryError("too_large", "Die Antwort ist zu gross", 413)
                        return response.status, data
                except urllib.error.HTTPError as err:
                    if err.code in (429, 503):
                        header = err.headers.get("Retry-After", "") if err.headers else ""
                        wait = float(header) if header.strip().isdigit() else BACKOFF_DEFAULT
                        self._blocked_until = time.monotonic() + min(BACKOFF_MAX, max(1.0, wait))
                        raise LibraryError("rate_limited", "GDTF Share bittet um Geduld - bitte etwas warten", 429,
                                           retry_after=int(min(BACKOFF_MAX, max(1.0, wait))))
                    return err.code, err.read(65536)
                except (urllib.error.URLError, TimeoutError, OSError) as exc:
                    reason = getattr(exc, "reason", exc)
                    raise LibraryError("network", f"GDTF Share ist nicht erreichbar ({reason})", 502)
            finally:
                self._last_request = time.monotonic()
                if download:
                    self._last_download = self._last_request

    @staticmethod
    def _json(data: bytes) -> Dict[str, Any]:
        try:
            parsed = json.loads(data.decode("utf-8", "replace"))
        except ValueError:
            raise LibraryError("bad_response", "Unerwartete Antwort von GDTF Share", 502)
        return parsed if isinstance(parsed, dict) else {"list": parsed}

    # ---- Sitzung
    def login(self, user: str, password: str, remember: Optional[bool] = False) -> Dict[str, Any]:
        """remember=True: Zugangsdaten verschluesselt speichern; False: eine gespeicherte Anmeldung loeschen; None: unveraendert (Wiederanmeldung)."""
        user, password = str(user or "").strip(), str(password or "")
        if not user or not password:
            raise LibraryError("auth", "Bitte E-Mail-Adresse bzw. Benutzernamen und Passwort eingeben", 401)
        with self._lock:
            self._reset()
            ok, message = False, ""
            # Das Format des Anmelde-Aufrufs ist bei GDTF Share nicht dokumentiert: erst JSON, dann Formular.
            for body, ctype in ((json.dumps({"user": user, "password": password}).encode(), "application/json"),
                                (urllib.parse.urlencode({"user": user, "password": password}).encode(), "application/x-www-form-urlencoded")):
                status, data = self._request("/apis/public/login.php", body, ctype, max_bytes=1024 * 1024)
                try:
                    parsed = self._json(data)
                except LibraryError:
                    parsed = {}
                if status == 200 and parsed.get("result") is True:
                    ok = True
                    break
                message = str(parsed.get("error") or message)
            if not ok:
                self._reset()
                raise LibraryError("auth", message or "Anmeldung bei GDTF Share fehlgeschlagen", 401)
            self.user, self.logged_in = user, True
            if remember is True:
                save_login(user, password)
            elif remember is False:
                forget_login()
            return self.status()

    def resume(self) -> Dict[str, Any]:
        """Meldet mit der gespeicherten Anmeldung an (falls vorhanden). Ungueltige Zugangsdaten werden verworfen, ein Netzfehler nicht."""
        with self._lock:
            if self.logged_in:
                return self.status()
            saved = load_login()
            if saved is None:
                return self.status()
            try:
                return self.login(saved["user"], saved["password"], remember=None)
            except LibraryError as exc:
                if exc.code == "auth":
                    forget_login()
                raise

    def logout(self) -> Dict[str, Any]:
        """Abmelden - vergisst auch eine gespeicherte Anmeldung."""
        with self._lock:
            self._reset()
            forget_login()
            return self.status()

    def status(self) -> Dict[str, Any]:
        items = self._list
        blocked = self._blocked_until - time.monotonic()
        return {"logged_in": self.logged_in, "user": self.user, "count": len(items) if items is not None else None,
                "list_age": int(time.time() - self._list_at) if items is not None else None, "base": SHARE_BASE,
                "remember_available": remember_available(), "remembered": remember_available() and _login_file().is_file(),
                "remembered_user": remembered_user() if not self.logged_in else "",
                "has_verified": bool(items) and any(i["verified"] is not None for i in items),
                "blocked_for": int(blocked) + 1 if blocked > 0 else 0}

    # ---- Liste
    @staticmethod
    def _normalize_item(raw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        def pick(*keys: str) -> Any:
            for key in keys:
                if raw.get(key) not in (None, ""):
                    return raw[key]
            return ""
        rid = pick("rid", "id", "RID")
        name = str(pick("fixture", "name", "fixtureName", "Name")).strip()
        if rid == "" or not name:
            return None
        manufacturer = str(pick("manufacturer", "Manufacturer")).strip()
        revision = str(pick("revision", "Revision", "rev")).strip()
        try:
            rating = float(pick("rating", "Rating") or 0)
        except (TypeError, ValueError):
            rating = 0.0
        return {
            "rid": int(rid) if str(rid).isdigit() else str(rid),
            "name": name,
            "manufacturer": manufacturer,
            "revision": revision,
            "creator": str(pick("creator", "uploader", "uploadedBy", "designedBy", "user", "username")),
            "rating": rating,
            "version": str(pick("version", "gdtfVersion", "GDTFVersion")),
            "modified": str(pick("lastModified", "modified", "uploadDate", "date")),
            "created": str(pick("creationDate", "created", "uploaded")),
            "uuid": str(pick("uuid", "UUID")),
            "verified": _verified_flag(raw),
            "category": category_from_text(name, manufacturer),
            "id": install_id(manufacturer or "Unbekannt", name, revision or "Rev"),
        }

    def fetch_list(self, force: bool = False) -> Tuple[List[Dict[str, Any]], bool]:
        """Die Liste (aus dem Zwischenspeicher, wenn jung genug). Rueckgabe: (Eintraege, 'Neuladen wurde gebremst')."""
        with self._lock:
            if not self.logged_in:
                raise LibraryError("auth", "Bitte zuerst bei GDTF Share anmelden", 401)
            throttled = False
            if self._list is not None:
                age = time.time() - self._list_at
                if not force and age < LIST_MAX_AGE:
                    return self._list, False
                if force and age < REFRESH_MIN_INTERVAL:        # jemand drueckt 'Liste aktualisieren' im Sekundentakt
                    return self._list, True
            status, data = self._request("/apis/public/getList.php")
            if status == 401:
                self._reset()
                raise LibraryError("auth", "Die Sitzung bei GDTF Share ist abgelaufen - bitte neu anmelden", 401)
            if status != 200:
                raise LibraryError("bad_response", f"GDTF Share antwortete mit Status {status}", 502)
            parsed = self._json(data)
            if parsed.get("result") is False:
                raise LibraryError("bad_response", str(parsed.get("error") or "Liste nicht verfuegbar"), 502)
            rows = parsed.get("list")
            if rows is None:
                rows = parsed.get("data") or parsed.get("fixtures") or []
            items = [item for item in (self._normalize_item(r) for r in rows if isinstance(r, dict)) if item]
            self._list, self._list_at = items, time.time()
            return items, throttled

    def download(self, rid: Any) -> bytes:
        with self._lock:
            if not self.logged_in:
                raise LibraryError("auth", "Bitte zuerst bei GDTF Share anmelden", 401)
        status, data = self._request("/apis/public/downloadFile.php?" + urllib.parse.urlencode({"rid": str(rid)}), max_bytes=MAX_GDTF_BYTES, download=True)
        if status == 401:
            with self._lock:
                self._reset()
            raise LibraryError("auth", "Die Sitzung bei GDTF Share ist abgelaufen - bitte neu anmelden", 401)
        if status == 404:
            raise LibraryError("not_found", "Diese Datei gibt es bei GDTF Share nicht (mehr)", 404)
        if status != 200:
            raise LibraryError("bad_response", f"GDTF Share antwortete mit Status {status}", 502)
        return data


share = GdtfShareClient()


def _group_key(item: Dict[str, Any]) -> Tuple[str, str]:
    return (_normalize(item["manufacturer"]), _normalize(item["name"]))


def _version_row(item: Dict[str, Any], installed_ids: set) -> Dict[str, Any]:
    return {"rid": item["rid"], "revision": item["revision"], "modified": item["modified"] or item["created"], "creator": item["creator"],
            "verified": item["verified"], "rating": item["rating"], "version": item["version"], "id": item["id"], "installed": item["id"] in installed_ids}


def search_online(query: str = "", category: str = "", manufacturer: str = "", offset: int = 0, limit: int = 50,
                  all_revisions: bool = False, refresh: bool = False, sort: str = "name", verified_only: bool = False,
                  min_rating: float = 0.0, verified_first: bool = False) -> Dict[str, Any]:
    """Durchsucht die (zwischengespeicherte) Liste von GDTF Share: Freitext (Name/Hersteller), Typ, Hersteller, nur verifizierte,
    Sortierung, Seite; min_rating = mindestens so viele Sterne (unbewertete fallen heraus); verified_first = von Herstellern verifizierte
    vor allen anderen (die Reihenfolge innerhalb der Gruppen bleibt die gewaehlte Sortierung). Standardmaessig ein Eintrag je Geraet (neueste Revision) mit allen Versionen in `versions`;
    all_revisions=True liefert stattdessen jede Revision einzeln."""
    items, throttled = share.fetch_list(force=refresh)
    tokens = [t for t in re.split(r"\s+", (query or "").strip().lower()) if t]
    wanted_mfr = _normalize(manufacturer)
    wanted_cat = category if category in CATEGORIES else ""
    hits = []
    for item in items:
        if wanted_cat and item["category"] != wanted_cat:
            continue
        if wanted_mfr and _normalize(item["manufacturer"]) != wanted_mfr:
            continue
        haystack = f"{item['name']} {item['manufacturer']} {item['revision']} {item['creator']}".lower()
        if tokens and not all(t in haystack for t in tokens):
            continue
        hits.append(item)
    installed_ids = {p.stem for p in _paths.FIXTURES_DIR.glob("*.gdtf")}
    installed_keys = {(_normalize(p.stem.split("@")[0]), _normalize(p.stem.split("@")[1] if "@" in p.stem else "")) for p in _paths.FIXTURES_DIR.glob("*.gdtf")}
    groups: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
    for item in items if not all_revisions else hits:
        groups.setdefault(_group_key(item), []).append(item)
    rows: List[Dict[str, Any]] = []
    if all_revisions:
        rows = [{**i, "versions": [_version_row(i, installed_ids)]} for i in hits]
    else:
        seen = set()
        for item in hits:                                  # Treffer pruefen mit der Revision, die zur Suche passt; Anzeige: neueste
            key = _group_key(item)
            if key in seen:
                continue
            seen.add(key)
            versions = sorted(groups[key], key=_version_key, reverse=True)
            rows.append({**versions[0], "versions": [_version_row(v, installed_ids) for v in versions]})
    for row in rows:
        row["installed"] = row["id"] in installed_ids
        row["same_fixture_installed"] = _group_key(row) in installed_keys
        installed_versions = [v for v in row["versions"] if v["installed"]]
        row["installed_version"] = installed_versions[0] if installed_versions else None
        row["update_available"] = bool(installed_versions) and not row["installed"] and not all_revisions
    if verified_only:
        rows = [r for r in rows if r["verified"]]
    try:
        floor = max(0.0, float(min_rating))
    except (TypeError, ValueError):
        floor = 0.0
    if floor > 0:
        rows = [r for r in rows if r["rating"] >= floor]
    if sort == "newest":
        rows.sort(key=lambda r: (_version_key(r)), reverse=True)
    elif sort == "rating":
        rows.sort(key=lambda r: (-r["rating"], r["manufacturer"].lower(), r["name"].lower()))
    else:
        rows.sort(key=lambda i: (i["manufacturer"].lower(), i["name"].lower(), i["revision"].lower()))
    if verified_first:
        rows.sort(key=lambda r: 0 if r["verified"] else 1)               # stabil: die gewaehlte Sortierung bleibt innerhalb der Gruppen
    offset, limit = max(0, int(offset)), max(1, min(200, int(limit)))
    manufacturers = sorted({i["manufacturer"] for i in items if i["manufacturer"]}, key=str.lower)
    return {"total": len(rows), "offset": offset, "items": rows[offset:offset + limit], "manufacturers": manufacturers, "list_total": len(items),
            "has_verified": any(i["verified"] is not None for i in items), "has_rating": any(i["rating"] > 0 for i in items), "refresh_throttled": throttled,
            "list_age": int(time.time() - share._list_at) if share._list is not None else None}


def updates_for_installed() -> Dict[str, Dict[str, Any]]:
    """Fuer installierte Dateien, die aus GDTF Share stammen: gibt es eine neuere Revision? Nur aus dem Zwischenspeicher, kein Netzzugriff."""
    items = share._list
    if not items or not share.logged_in:
        return {}
    by_id = {i["id"]: i for i in items}
    groups: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
    for item in items:
        groups.setdefault(_group_key(item), []).append(item)
    updates: Dict[str, Dict[str, Any]] = {}
    for path in _paths.FIXTURES_DIR.glob("*.gdtf"):
        current = by_id.get(path.stem)
        if current is None:
            continue
        newest = max(groups[_group_key(current)], key=_version_key)
        if newest["id"] != current["id"] and _version_key(newest) > _version_key(current):
            updates[path.stem] = {"rid": newest["rid"], "revision": newest["revision"], "modified": newest["modified"] or newest["created"],
                                  "verified": newest["verified"]}
    return updates


def install_from_share(rid: Any, replace: str = "", usage: Optional[Dict[str, int]] = None) -> Dict[str, Any]:
    """Laedt die Datei zur rid herunter und baut sie ein (Dateiname wie bei GDTF Share aus der Liste: Hersteller@Name@Revision).
    replace = ID einer installierten aelteren Revision desselben Geraets ('Aktualisieren'): sie wird danach entfernt, ausser die Show benutzt sie."""
    items, _ = share.fetch_list()
    item = next((i for i in items if str(i["rid"]) == str(rid)), None)
    if item is None:
        raise LibraryError("not_found", "Diese Datei gibt es bei GDTF Share nicht (mehr)", 404)
    data = share.download(rid)
    result = install_bytes(data, stem_hint=item["id"], revision_hint=item["revision"], usage=usage)
    result["removed_old"] = None
    result["kept_old"] = None
    result["pinned_old"] = None
    if replace and replace != result["id"]:
        old_item = next((i for i in items if i["id"] == replace), None)
        old_path = next((p for p in _paths.FIXTURES_DIR.glob("*.gdtf") if p.stem == replace), None)
        if old_item is not None and old_path is not None and _group_key(old_item) == _group_key(item):
            try:
                if (usage or {}).get(replace, 0):                                   # die Show benutzt die alte Revision: sie bleibt
                    result["kept_old"] = "in_use"
                    return result
                old_path.unlink()
                result["removed_old"] = replace
                fixture_manager.get_fixture_types()
            except OSError:
                result["kept_old"] = "locked"
    return result
