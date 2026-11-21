# Copyright (C) 2026 Samuel Zenker
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Scheinwerfer-Liste aus CSV oder Excel (.xlsx) einlesen (Scheinwerfer hinzufuegen -> Erweiterte Importfunktionen, Menue Bibliothek). Fuer viele Geraete auf einmal: Name, Typ, Modus, Universum,
DMX-Adresse, Nummer (FID), Anzahl - eine Zeile je Scheinwerfer (oder je Reihe gleicher Geraete). Der Dialog (static/js/fixture_import.js) arbeitet in zwei Schritten ohne Zustand auf dem Server:
  POST /api/fixtures/import/parse?filename=...   (roher Body)      -> {headers, rows, total, mapping, types}      Datei lesen, Spalten erraten
  POST /api/fixtures/import/preview              {rows, mapping, default_type, default_universe}   -> {items: [{ok, errors, ...}]}
  POST /api/fixtures/import/apply                dasselbe + skip_invalid                            -> {ok, added}   legt die Scheinwerfer an
  GET  /api/fixtures/export.csv                  die Patch-Liste der Show als CSV (auch als Vorlage)

Typ-Zuordnung: genaue Kennung, "Hersteller Name" oder Name; sonst ohne Satz- und Sonderzeichen gleich; sonst genau ein Typ, dessen Name den Text enthaelt. Mehrdeutig oder unbekannt = Fehler in der
Zeile (die Zeile wird nicht importiert). Adresse darf "45" oder "2.045" / "2/45" (Universum.Adresse) sein.
"""
from __future__ import annotations

import csv
import io
import re
import uuid
import zipfile
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response

from app import fixture_manager
from app.state_manager import MAX_UNIVERSE, MIN_UNIVERSE, Fixture, state

router = APIRouter()

MAX_ROWS = 5000
MAX_COLUMNS = 30
MAX_BYTES = 20 * 1024 * 1024
FIELDS = ("name", "type", "mode", "universe", "address", "fid", "count")
SYNONYMS = {
    "name": ("name", "bezeichnung", "label", "scheinwerfer", "geraet", "gerat", "fixture", "fixturename", "beschriftung"),
    "type": ("type", "typ", "fixturetype", "geraetetyp", "geratetyp", "modell", "model", "geraet", "gerat", "fixture", "profil", "profile", "hersteller"),
    "mode": ("mode", "modus", "personality", "dmxmode"),
    "universe": ("universe", "universum", "uni", "u", "dmxuniverse"),
    "address": ("address", "adresse", "dmx", "dmxaddress", "dmxadresse", "startadresse", "start", "startchannel", "startkanal", "kanal", "channel", "patch"),
    "fid": ("fid", "nr", "no", "number", "nummer", "id", "fixtureid", "fixturenumber", "scheinwerfernummer"),
    "count": ("count", "quantity", "anzahl", "menge", "qty", "stueck", "stuck", "pieces"),
}


class ImportError_(Exception):
    def __init__(self, code: str, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.code, self.message, self.status = code, message, status


def _norm(text: Any) -> str:
    text = str(text or "").lower().replace("ä", "a").replace("ö", "o").replace("ü", "u").replace("ß", "ss")
    return re.sub(r"[^a-z0-9]+", "", text)


# ---------------------------------------------------------------------------------------------------------------- Dateien lesen
def _decode(data: bytes) -> str:
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("latin-1", "replace")


def read_csv(data: bytes) -> List[List[str]]:
    text = _decode(data)
    first = next((line for line in text.splitlines() if line.strip()), "")
    delimiter = max((";", ",", "\t"), key=lambda d: first.count(d))
    rows = []
    for row in csv.reader(io.StringIO(text), delimiter=delimiter):
        if any(cell.strip() for cell in row):
            rows.append([cell.strip() for cell in row[:MAX_COLUMNS]])
        if len(rows) > MAX_ROWS + 1:
            break
    return rows


def _column(ref: str) -> int:
    letters = re.match(r"[A-Z]+", ref.upper())
    number = 0
    for ch in (letters.group(0) if letters else "A"):
        number = number * 26 + ord(ch) - 64
    return number - 1


def read_xlsx(data: bytes) -> List[List[str]]:
    """Erstes Blatt einer .xlsx-Datei (Texte und Zahlen; Formeln als zuletzt berechneter Wert)."""
    import xml.etree.ElementTree as ET

    def parse(raw: bytes):
        if b"<!DOCTYPE" in raw[:2000].upper() or b"<!ENTITY" in raw[:5000].upper():           # keine Entitaets-Bomben
            raise ImportError_("invalid_file", "The Excel file is invalid")
        return ET.fromstring(raw)

    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        raise ImportError_("invalid_file", "This is not an Excel file (.xlsx)") from None
    with archive:
        names = set(archive.namelist())
        sheets = sorted(n for n in names if re.match(r"xl/worksheets/sheet\d+\.xml$", n))
        if not sheets:
            raise ImportError_("invalid_file", "The Excel file has no worksheet")
        if any(archive.getinfo(n).file_size > MAX_BYTES for n in sheets + ["xl/sharedStrings.xml"] if n in names):
            raise ImportError_("too_large", "The worksheet is too large", 413)
        shared: List[str] = []
        if "xl/sharedStrings.xml" in names:
            for si in parse(archive.read("xl/sharedStrings.xml")).iterfind(".//{*}si"):
                shared.append("".join(t.text or "" for t in si.iterfind(".//{*}t")))
        rows: List[List[str]] = []
        for row in parse(archive.read(sheets[0])).iterfind(".//{*}row"):
            cells: Dict[int, str] = {}
            for c in row.iterfind(".//{*}c"):
                index = _column(c.get("r", "A1"))
                if index >= MAX_COLUMNS:
                    continue
                kind = c.get("t")
                v = c.find("{*}v")
                if kind == "s" and v is not None and v.text is not None:
                    value = shared[int(v.text)] if v.text.isdigit() and int(v.text) < len(shared) else ""
                elif kind == "inlineStr":
                    value = "".join(t.text or "" for t in c.iterfind(".//{*}t"))
                else:
                    value = v.text if v is not None and v.text is not None else ""
                    if re.fullmatch(r"-?\d+\.0+", value):
                        value = value.split(".")[0]
                cells[index] = value.strip()
            if cells and any(cells.values()):
                rows.append([cells.get(i, "") for i in range(max(cells) + 1)])
            if len(rows) > MAX_ROWS + 1:
                break
        return rows


def read_table(filename: str, data: bytes) -> List[List[str]]:
    if len(data) > MAX_BYTES:
        raise ImportError_("too_large", "The file is too large (max. 20 MB)", 413)
    lower = filename.lower()
    if lower.endswith(".xlsx"):
        return read_xlsx(data)
    if lower.endswith((".csv", ".txt", ".tsv")):
        return read_csv(data)
    if data[:2] == b"PK":
        return read_xlsx(data)
    raise ImportError_("invalid_name", "A .csv or .xlsx file is expected")


def suggest_mapping(headers: List[str]) -> Dict[str, int]:
    """Welche Spalte ist welches Feld (Spaltennummer ab 0; fehlt ein Feld, steht es nicht drin). Jede Spalte hoechstens einmal."""
    mapping: Dict[str, int] = {}
    used: set = set()
    for field in FIELDS:                                                         # in dieser Reihenfolge: "name" vor "type" (beide kennen "fixture" / "geraet")
        words = SYNONYMS[field]
        for index, head in enumerate(headers):
            if index in used:
                continue
            if _norm(head) in words:
                mapping[field] = index
                used.add(index)
                break
    return mapping


def type_catalog() -> List[Dict[str, Any]]:
    out = []
    for ft in fixture_manager.get_fixture_types():
        out.append({"id": ft["id"], "name": ft.get("name", ft["id"]), "manufacturer": ft.get("manufacturer", ""), "channel_count": ft.get("channel_count", 0),
                    "modes": [{"name": m.get("name", ""), "channel_count": int(m.get("channel_count", 0))} for m in ft.get("modes", [])]})
    return out


# ---------------------------------------------------------------------------------------------------------------- Zeilen pruefen
def _int(text: Any) -> Optional[int]:
    try:
        return int(float(str(text).strip().replace(",", ".")))
    except (TypeError, ValueError):
        return None


def type_label(ft: Dict[str, Any]) -> str:
    """'Hersteller Name' - ohne den Hersteller doppelt zu nennen (Name beginnt oft schon damit)."""
    maker, name = str(ft.get("manufacturer", "")).strip(), str(ft.get("name", ft.get("id", ""))).strip()
    return name if not maker or name.lower().startswith(maker.lower()) else f"{maker} {name}"


def resolve_type(text: str, types: List[Dict[str, Any]]) -> Tuple[Optional[Dict[str, Any]], str]:
    wanted = text.strip()
    if not wanted:
        return None, "type missing"
    key = _norm(wanted)
    for ft in types:
        if wanted.lower() == ft["id"].lower():
            return ft, ""
    for ft in types:
        if key and key in (_norm(ft["name"]), _norm(f"{ft['manufacturer']} {ft['name']}"), _norm(ft["id"])):
            return ft, ""
    hits = [ft for ft in types if key and key in _norm(f"{ft['manufacturer']} {ft['name']}")]
    if len(hits) == 1:
        return hits[0], ""
    if len(hits) > 1:
        return None, "type ambiguous: " + ", ".join(f"{h['manufacturer']} {h['name']}".strip() for h in hits[:4])
    return None, f"type unknown: {wanted}"


def resolve_mode(text: str, ft: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], str]:
    modes = ft["modes"] or [{"name": "default", "channel_count": ft.get("channel_count", 1)}]
    wanted = text.strip()
    if not wanted:
        return next((m for m in modes if m["name"].lower() == "default"), modes[0]), ""
    for m in modes:
        if m["name"].lower() == wanted.lower() or _norm(m["name"]) == _norm(wanted):
            return m, ""
    number = _int(re.sub(r"(?i)ch(annels?)?|kan(a|ä)l(e)?|k", "", wanted))
    if number is not None:
        hits = [m for m in modes if m["channel_count"] == number]
        if len(hits) == 1:
            return hits[0], ""
    return None, f"mode unknown: {wanted} (available: " + ", ".join(m["name"] for m in modes[:6]) + ")"


def evaluate(rows: List[List[str]], mapping: Dict[str, Any], default_type: str = "", default_universe: int = MIN_UNIVERSE) -> List[Dict[str, Any]]:
    """Jede Zeile in einen fertigen Eintrag (oder Fehler) umsetzen. Fehlende Adressen laufen hinter dem vorigen Geraet desselben Universums weiter."""
    types = type_catalog()
    cells = {f: (int(mapping[f]) if str(mapping.get(f, "")).lstrip("-").isdigit() and int(mapping[f]) >= 0 else None) for f in FIELDS}

    def cell(row: List[str], field: str) -> str:
        index = cells[field]
        return row[index].strip() if index is not None and index < len(row) else ""

    items: List[Dict[str, Any]] = []
    next_free: Dict[int, int] = {}
    used_fids = {fx.fid for fx in state.fixtures.values()}
    for number, row in enumerate(rows[:MAX_ROWS], start=1):
        errors: List[str] = []
        type_text = cell(row, "type") or default_type
        ft, error = resolve_type(type_text, types)
        if error:
            errors.append(error)
        mode = None
        if ft is not None:
            mode, error = resolve_mode(cell(row, "mode"), ft)
            if error:
                errors.append(error)
        address_text = cell(row, "address")
        universe = _int(cell(row, "universe"))
        address = None
        combined = re.fullmatch(r"(\d+)\s*[./:]\s*(\d+)", address_text)
        if combined:
            universe = universe if universe is not None else int(combined.group(1))
            address = int(combined.group(2))
        elif address_text:
            address = _int(address_text)
            if address is None:
                errors.append(f"address invalid: {address_text}")
        if universe is None:
            universe = default_universe
        if not MIN_UNIVERSE <= universe <= MAX_UNIVERSE:
            errors.append(f"universe out of range: {universe}")
        count_text = cell(row, "count")
        count = _int(count_text) if count_text else 1
        if count is None or not 1 <= count <= 512:
            errors.append(f"count invalid: {count_text}")
            count = 1
        fid_text = cell(row, "fid")
        fid = _int(fid_text) if fid_text else None
        if fid_text and (fid is None or fid < 1):
            errors.append(f"number invalid: {fid_text}")
            fid = None
        channels = int(mode["channel_count"]) if mode else 0
        if address is None:
            address = next_free.get(universe, 1)
        if channels and (address < 1 or address + channels * count - 1 > 512):
            errors.append(f"does not fit into universe {universe} (address {address}, {channels * count} channels)")
        name = cell(row, "name") or (ft["name"] if ft else "")
        if fid is not None:
            if fid in used_fids:
                errors.append(f"number {fid} is already used")
            elif count > 1:
                errors.append("a number cannot be combined with a count above 1")
        item = {"row": number, "ok": not errors, "errors": errors, "name": name, "type_id": ft["id"] if ft else "", "type_name": (type_label(ft) if ft else type_text),
                "mode": mode["name"] if mode else "", "channels": channels, "universe": universe, "address": address, "fid": fid, "count": count}
        if not errors:
            next_free[universe] = address + channels * count
            if fid is not None:
                used_fids.add(fid)
        items.append(item)
    return items


def apply_items(items: List[Dict[str, Any]]) -> List[Fixture]:
    created: List[Fixture] = []
    for item in items:
        if not item["ok"]:
            continue
        address = item["address"]
        for i in range(item["count"]):
            name = item["name"] if item["count"] == 1 else f"{item['name']} {i + 1}"
            fx = Fixture(id=str(uuid.uuid4()), fid=item["fid"] if (item["fid"] and item["count"] == 1) else state._next_fid(), name=name[:80], fixture_type=item["type_id"],
                         universe=item["universe"], start_channel=address, channel_count=item["channels"], mode=item["mode"])
            state.fixtures[fx.id] = fx
            created.append(fx)
            address += item["channels"]
    if created:
        state.mark_dirty()
    return created


# ---------------------------------------------------------------------------------------------------------------- HTTP
def _body_ok(body: Any) -> Tuple[List[List[str]], Dict[str, Any], str, int]:
    if not isinstance(body, dict) or not isinstance(body.get("rows"), list) or not isinstance(body.get("mapping"), dict):
        raise ImportError_("bad_request", "Ungueltige Anfrage")
    rows = [[str(c) for c in r][:MAX_COLUMNS] for r in body["rows"][:MAX_ROWS] if isinstance(r, list)]
    universe = _int(body.get("default_universe")) or MIN_UNIVERSE
    return rows, body["mapping"], str(body.get("default_type") or ""), universe


@router.post("/api/fixtures/import/parse")
async def parse_file(request: Request) -> JSONResponse:
    import asyncio
    import urllib.parse
    filename = urllib.parse.unquote(request.query_params.get("filename", ""))
    data = await request.body()
    try:
        table = await asyncio.to_thread(read_table, filename, data)
    except ImportError_ as exc:
        return JSONResponse({"ok": False, "error": exc.code, "message": exc.message}, status_code=exc.status)
    if len(table) < 2:
        return JSONResponse({"ok": False, "error": "empty", "message": "The file has no rows (first row = column headers)"}, status_code=400)
    headers, rows = table[0], table[1:]
    width = max(len(headers), max((len(r) for r in rows), default=0))
    headers = headers + [""] * (width - len(headers))
    return JSONResponse({"ok": True, "headers": [h or f"({i + 1})" for i, h in enumerate(headers)], "rows": [r + [""] * (width - len(r)) for r in rows[:MAX_ROWS]], "total": len(rows),
                         "truncated": len(rows) > MAX_ROWS, "mapping": suggest_mapping(headers), "types": type_catalog(), "default_universe": state.default_universe})


@router.post("/api/fixtures/import/preview")
async def preview(request: Request) -> JSONResponse:
    try:
        rows, mapping, default_type, universe = _body_ok(await request.json())
    except ImportError_ as exc:
        return JSONResponse({"ok": False, "error": exc.code, "message": exc.message}, status_code=exc.status)
    items = evaluate(rows, mapping, default_type, universe)
    return JSONResponse({"ok": True, "items": items, "good": sum(1 for i in items if i["ok"]), "bad": sum(1 for i in items if not i["ok"])})


@router.post("/api/fixtures/import/apply")
async def apply(request: Request) -> JSONResponse:
    from app import server as S
    body = await request.json()
    try:
        rows, mapping, default_type, universe = _body_ok(body)
    except ImportError_ as exc:
        return JSONResponse({"ok": False, "error": exc.code, "message": exc.message}, status_code=exc.status)
    items = evaluate(rows, mapping, default_type, universe)
    bad = [i for i in items if not i["ok"]]
    if bad and not body.get("skip_invalid"):
        return JSONResponse({"ok": False, "error": "invalid_rows", "message": f"{len(bad)} Zeile(n) haben Probleme", "bad": len(bad)}, status_code=409)
    created = apply_items(items)
    if not created:
        return JSONResponse({"ok": False, "error": "nothing", "message": "There is nothing to import"}, status_code=409)
    await S.event_bus.broadcast({"type": "fixtures_changed", "payload": {"fixtures": state.fixtures_as_dicts(), "is_dirty": state.is_dirty}})
    return JSONResponse({"ok": True, "added": len(created), "skipped": len(bad)})


@router.get("/api/fixtures/export.csv")
async def export_csv() -> Response:
    out = io.StringIO()
    writer = csv.writer(out, delimiter=";", lineterminator="\r\n")
    names = {t["id"]: type_label(t) for t in type_catalog()}
    writer.writerow(["Name", "Type", "Mode", "Universe", "Address", "FID"])
    for fx in sorted(state.fixtures.values(), key=lambda f: (f.fid or 0, f.universe, f.start_channel)):
        writer.writerow([fx.name, names.get(fx.fixture_type, fx.fixture_type), fx.mode if fx.mode != "default" else "", fx.universe, fx.start_channel, fx.fid])
    if not state.fixtures:
        writer.writerow(["Front Wash 1", "Generic Dimmer", "", 1, 1, 1])
        writer.writerow(["Front Wash 2", "Generic Dimmer", "", 1, 2, 2])
    return Response(content=("﻿" + out.getvalue()).encode("utf-8"), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": "attachment; filename=\"fixtures.csv\"", "Cache-Control": "no-store"})
