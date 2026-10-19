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

from pathlib import Path
from typing import Any, Dict, List, Optional

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

    result = [_parse_gdtf(p) for p in gdtf_files]
    taken = {str(item.get("name", "")).strip().lower() for item in result}
    result += [dict(item) for item in FALLBACK_FIXTURES if str(item["name"]).strip().lower() not in taken]       # die eingebauten Generic-Geraete (ohne 3D-Modell) gibt es immer, solange keine GDTF-Datei denselben Namen hat
    _fixture_types_cache = result
    _fixture_types_cache_key = cache_key
    # Wheels-Cache mitinvalidieren, wenn sich GDTF-Dateien geaendert haben.
    _fixture_wheels_cache.clear()
    _fixture_shutter_cache.clear()
    _fixture_beamfx_cache.clear()
    return result


def get_fixture_type_by_id(fixture_type_id: str) -> Optional[Dict[str, Any]]:
    """Einen Fixture-Typ nach seiner ID zurueckgeben."""
    return next((ft for ft in get_fixture_types() if ft["id"] == fixture_type_id), None)


_fixture_wheels_cache: Dict[str, List[Dict[str, Any]]] = {}


def get_fixture_wheels(fixture_id: str) -> List[Dict[str, Any]]:
    """Extrahiert Wheel-Slot-Daten (Gobo/Farbe/Prism) inkl. DMX-Bereiche und Base64-Bilder.

    Liest Wheel-Definitionen (Slots + media_file_name) sowie die zugehoerigen
    ChannelSets (genaue DMX-Bereiche pro Slot) aus der GDTF-Datei. Bilder werden
    direkt aus dem wheels/-Ordner des ZIP gelesen und als data:-URI zurueckgegeben.
    """
    import base64
    import zipfile

    if fixture_id in _fixture_wheels_cache:
        return _fixture_wheels_cache[fixture_id]

    gdtf_path = next((p for p in gdtf_paths() if p.stem == fixture_id), None)
    if gdtf_path is None:
        _fixture_wheels_cache[fixture_id] = []
        return []

    try:
        ft = pygdtf.FixtureType(str(gdtf_path))
        ft.__exit__(None, None, None)        # ZIP-Handle freigeben (Windows: sonst nicht loeschbar)
    except Exception:
        _fixture_wheels_cache[fixture_id] = []
        return []

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

    _fixture_wheels_cache[fixture_id] = result
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


def get_fixture_beamfx(fixture_id: str) -> Dict[str, Dict[str, Any]]:
    """Gobo-/Prismenkanaele eines Typs (erster DMX-Modus, der solche Kanaele hat): {Kanalattribut: {role: select|spin, type: gobo|prism, wheel: Radname, ranges: [{from, to, kind, slot, name,
    phys: [von, bis]}]}}. select = Kanal, der den Slot des Rads waehlt (Gobo1, Prism1; slot = Nummer im Rad ab 1); spin = Drehung/Position des Rads (Gobo1SelectSpin, Prism1Pos, Prism1PosRotate ...).
    kind siehe _classify_beamfx; phys = physikalische Werte der Datei (Winkel oder Drehgeschwindigkeit, Vorzeichen = Richtung)."""
    if fixture_id in _fixture_beamfx_cache:
        return _fixture_beamfx_cache[fixture_id]
    result: Dict[str, Dict[str, Any]] = {}
    _fixture_beamfx_cache[fixture_id] = result
    gdtf_path = next((p for p in gdtf_paths() if p.stem == fixture_id), None)
    if gdtf_path is None:
        return result
    try:
        ft = pygdtf.FixtureType(str(gdtf_path))
        ft.__exit__(None, None, None)
    except Exception:
        return result
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


def get_fixture_shutter(fixture_id: str) -> Dict[str, List[Dict[str, Any]]]:
    """DMX-Bereiche der Shutter-/Strobe-Kanaele eines Typs: {Kanalattribut: [{from, to, kind, hz: [von, bis]}]} (aus dem ersten DMX-Modus, der solche Kanaele hat).
    kind: closed | open | strobe | pulse_in | pulse_out | random; hz = Blitzfrequenz am Anfang/Ende des Bereichs (GDTF: Einheit Hz; ohne Angabe 1-20 Hz); name = Name des Bereichs."""
    if fixture_id in _fixture_shutter_cache:
        return _fixture_shutter_cache[fixture_id]
    result: Dict[str, List[Dict[str, Any]]] = {}
    _fixture_shutter_cache[fixture_id] = result
    gdtf_path = next((p for p in gdtf_paths() if p.stem == fixture_id), None)
    if gdtf_path is None:
        return result
    try:
        ft = pygdtf.FixtureType(str(gdtf_path))
        ft.__exit__(None, None, None)
    except Exception:
        return result
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
