"""
sim_stages.py
Buehnen der "3D-Simulation": Quader, Zylinder, Kugeln und Keile (Name, Farbe, Position = Fusspunkt, Drehung, Groesse; Meter, Grad, Z nach oben).

- Bibliothek: eine Datei je Buehne in <Datenordner>/stages/<Name>.json  {"format": "opencue-sim-stage", "version": 1, "name", "objects": [...], "saved_at"}.
- Aktive Buehne: genau eine, auf dem Server (alle Geraete und Panels sehen dieselbe). Die Arbeitskopie (objects) wird vom Client laufend gesendet; "dirty" heisst:
  weicht von der zuletzt gespeicherten/geladenen Fassung ab (Stern in der Toolbar). Nichts wird ohne ausdrueckliches Speichern in eine Datei geschrieben.
- Die zuletzt benutzte Buehne merkt sich <Datenordner>/stages/.last und wird beim ersten Zugriff wieder geladen.
- Die aktive Buehne steckt auch in der Showfile (Schluessel "sim_stage": Name, Herkunftsdatei, Objekte): Export/Import der Show nimmt sie mit; beim Laden gilt die
  eingebettete Fassung (steht die Herkunftsdatei lokal anders da, zeigt der Stern "weicht von der Datei ab"). Aenderungen an der Buehne markieren die Show als geaendert.
- Die Buehnendatei enthaelt NUR die Buehne (Koerper). Alles andere gehoert zur Show und steckt im Block "sim_stage" der Showfile:
  * Positionen der Scheinwerfer in der 3D-Simulation (Modus "Scheinwerfer"): store.layout, je Scheinwerfer der Show {position, rotation}; REST /api/sim-fixtures. Eintraege
    von Scheinwerfern, die es in der Show nicht mehr gibt, werden beim Speichern der Show weggelassen.
  * Raum-Einstellungen (Arbeitslicht, Grundlicht, Raumlicht, Wandreflexion, Objektreflexion, Farbabstrahlung, Belichtung, Nebel, Raster in der Ansicht; store.room, REST /api/sim-room);
    die zuletzt benutzten merkt zusaetzlich die App-Config (app_config.json, Schluessel "sim_room") fuer eine neue Show.
Schnittstellen (REST, /api/sim-stage*): aktiver Stand, setzen, verwerfen, speichern, laden, neu, umbenennen, duplizieren, loeschen. Jede Aenderung geht als WebSocket-Nachricht
"sim_stage_changed" an alle Geraete.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import re
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app import paths as _paths

FORMAT = "opencue-sim-stage"
VERSION = 1
TYPES = ("box", "cylinder", "sphere", "wedge")
MATERIALS = ("matt", "satin", "glossy", "metal", "mirror")          # Oberflaechen: matt (Holz, Stein, Stoff) ... Spiegel (Chrom)
MAX_OBJECTS = 200
MAX_FILE_BYTES = 2 * 1024 * 1024
LIMIT = 2000.0
MIN_SIZE = 0.01
BASE_NAME = "Stage"                                  # Programmsprache ist Englisch: neue Buehnen heissen "Stage 1", "Stage 2" ...
_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")
_RESERVED = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}

router = APIRouter()


class StageError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


_STATUS = {"invalid_name": 400, "invalid_json": 400, "not_a_stage": 400, "too_big": 413, "not_found": 404, "exists": 409}


# ------------------------------------------------------------------ Dateien und Namen

def library_dir() -> Path:
    directory = _paths.get_data_root() / "stages"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def clean_name(raw: Any, fallback: str = "") -> str:
    text = re.sub(r"\s+", " ", re.sub(r'[\\/:*?"<>|\x00-\x1f]', "", str(raw if raw is not None else ""))).strip().rstrip(".")
    return text[:80] or fallback


def filename_for(name: str) -> str:
    cleaned = clean_name(name)
    if not cleaned or cleaned.split(".")[0].upper() in _RESERVED:
        return ""
    return cleaned + ".json"


def valid_filename(filename: Any) -> bool:
    return (isinstance(filename, str) and filename.lower().endswith(".json") and filename == Path(filename).name and "/" not in filename
            and "\\" not in filename and not filename.startswith(".") and "\x00" not in filename and len(filename) <= 90)


def suggest_name(extra: Any = ()) -> str:
    """Naechster freier Name "Stage N" (N fortlaufend; beruecksichtigt Bibliotheksdateien und weitere Namen)."""
    pattern = re.compile(r"^" + re.escape(BASE_NAME) + r" (\d+)$")
    names = list(extra) + [p.stem for p in library_dir().glob("*.json")]
    numbers = [0] + [int(m.group(1)) for m in (pattern.match(str(n).strip()) for n in names) if m]
    return f"{BASE_NAME} {max(numbers) + 1}"


# ------------------------------------------------------------------ Objekte pruefen

def _num(value: Any, default: float, low: float = -LIMIT, high: float = LIMIT) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return max(low, min(high, number)) if math.isfinite(number) else default


def _vec(value: Any, default, low: float = -LIMIT, high: float = LIMIT) -> List[float]:
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        return [float(d) for d in default]
    return [round(_num(v, d, low, high), 4) for v, d in zip(value, default)]


def normalize_objects(raw: Any) -> List[Dict[str, Any]]:
    """Beliebige Eingabe in eine gueltige Objektliste umwandeln (unbrauchbare Eintraege fallen weg, Grenzen werden eingehalten)."""
    objects: List[Dict[str, Any]] = []
    taken: set = set()
    for item in (raw if isinstance(raw, list) else [])[:MAX_OBJECTS]:
        if not isinstance(item, dict) or item.get("type") not in TYPES:
            continue
        oid = item.get("id") if isinstance(item.get("id"), str) and _ID_RE.match(item["id"]) and item["id"] not in taken else "o" + uuid.uuid4().hex[:10]
        taken.add(oid)
        objects.append({
            "id": oid, "type": item["type"], "name": clean_name(item.get("name"), item["type"])[:60],
            "color": item["color"].lower() if isinstance(item.get("color"), str) and _COLOR_RE.match(item["color"]) else "#9c9ca0",
            "position": _vec(item.get("position"), (0, 0, 0)), "rotation": _vec(item.get("rotation"), (0, 0, 0), -3600.0, 3600.0),
            "size": _vec(item.get("size"), (1, 1, 1), MIN_SIZE, LIMIT),
            "material": item["material"] if item.get("material") in MATERIALS else "matt",
        })
    return objects


ROOM_DEFAULTS: Dict[str, Any] = {"work": 100, "house": 0, "bounce": 0, "shell": 50, "reflect": 100, "bleed": 60, "exposure": 50, "haze": 10, "helpers": False}
ROOM_LIMITS = {"work": (0, 100), "house": (0, 100), "bounce": (0, 300), "shell": (0, 95), "reflect": (0, 200), "bleed": (0, 300), "exposure": (50, 200), "haze": (0, 100)}


def normalize_room(raw: Any) -> Dict[str, Any]:
    """Raum-Einstellungen bereinigen: fehlende/ungueltige Werte -> Standard, Zahlen in ihren Grenzen."""
    raw = raw if isinstance(raw, dict) else {}
    out: Dict[str, Any] = {}
    for key, (low, high) in ROOM_LIMITS.items():
        out[key] = round(_num(raw.get(key), ROOM_DEFAULTS[key], low, high))
    out["helpers"] = bool(raw["helpers"]) if "helpers" in raw else ROOM_DEFAULTS["helpers"]
    return out


MAX_FIXTURES = 500
LAYOUT_DEFAULT_POSITION = [0.0, 0.0, 4.0]


def normalize_layout(raw: Any) -> Dict[str, Dict[str, Any]]:
    """Positionen der Scheinwerfer bereinigen: {Scheinwerfer-Id (die UUID der Show): {position [x, y, z] in Metern, rotation [rx, ry, rz] in Grad, hidden / scale (optional)}}."""
    out: Dict[str, Dict[str, Any]] = {}
    if not isinstance(raw, dict):
        return out
    for fixture_id, item in raw.items():
        if len(out) >= MAX_FIXTURES:
            break
        if not isinstance(fixture_id, str) or not fixture_id or len(fixture_id) > 64 or not isinstance(item, dict):
            continue
        out[fixture_id] = {
            "position": [round(v, 3) for v in _vec(item.get("position"), LAYOUT_DEFAULT_POSITION)],
            "rotation": [round(v, 2) for v in _vec(item.get("rotation"), [0, 0, 0], -3600.0, 3600.0)],
        }
        if item.get("hidden") is True:                       # ausgeblendet (in der Liste abgehakt): nur gespeichert, wenn gesetzt
            out[fixture_id]["hidden"] = True
        scale = round(float(_num(item.get("scale"), 1.0, 0.05, 20.0)), 3)
        if abs(scale - 1.0) > 1e-6:                          # Skalierung des 3D-Modells (1 = Originalgroesse aus der Scheinwerfer-Datei): nur gespeichert, wenn anders
            out[fixture_id]["scale"] = scale
    return out


def digest(objects: List[Dict[str, Any]]) -> str:
    return hashlib.sha256(json.dumps(objects, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()


# ------------------------------------------------------------------ Bibliothek

def _read_text(text: str) -> Dict[str, Any]:
    if len(text.encode("utf-8")) > MAX_FILE_BYTES:
        raise StageError("too_big")
    try:
        data = json.loads(text)
    except ValueError:
        raise StageError("invalid_json") from None
    if not isinstance(data, dict) or data.get("format") != FORMAT:
        raise StageError("not_a_stage")
    return data


def read_file(filename: str) -> Dict[str, Any]:
    if not valid_filename(filename):
        raise StageError("invalid_name")
    path = library_dir() / filename
    if not path.is_file():
        raise StageError("not_found")
    try:
        data = _read_text(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError):
        raise StageError("not_found") from None
    return {"name": clean_name(data.get("name"), path.stem), "objects": normalize_objects(data.get("objects"))}


def list_files() -> List[Dict[str, Any]]:
    out = []
    for path in sorted(library_dir().glob("*.json"), key=lambda p: p.name.lower()):
        if not valid_filename(path.name) or path.stat().st_size > MAX_FILE_BYTES:
            continue
        try:
            unit = read_file(path.name)
        except StageError:
            continue
        out.append({"filename": path.name, "name": unit["name"], "objects": len(unit["objects"]), "modified": int(path.stat().st_mtime)})
    return out


def file_text(name: str, objects: List[Dict[str, Any]]) -> str:
    """Inhalt einer Buehnen-Datei."""
    body = {"format": FORMAT, "version": VERSION, "name": clean_name(name), "saved_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "objects": objects}
    return json.dumps(body, indent=2, ensure_ascii=False)


def write_file(name: str, objects: List[Dict[str, Any]], overwrite: bool = False) -> str:
    filename = filename_for(name)
    if not filename:
        raise StageError("invalid_name")
    path = library_dir() / filename
    if path.exists() and not overwrite:
        raise StageError("exists")
    text = file_text(name, objects)
    if len(text.encode("utf-8")) > MAX_FILE_BYTES:
        raise StageError("too_big")
    partial = path.with_name("." + path.name + ".part")
    partial.write_text(text, encoding="utf-8")
    partial.replace(path)
    return filename


def delete_file(filename: str) -> None:
    if not valid_filename(filename):
        raise StageError("invalid_name")
    path = library_dir() / filename
    if not path.is_file():
        raise StageError("not_found")
    path.unlink()


def rename_file(filename: str, new_name: str, overwrite: bool = False) -> str:
    unit = read_file(filename)
    new_filename = filename_for(new_name)
    if not new_filename:
        raise StageError("invalid_name")
    if new_filename.lower() != filename.lower() and (library_dir() / new_filename).exists() and not overwrite:
        raise StageError("exists")
    write_file(new_name, unit["objects"], overwrite=True)
    if new_filename != filename:
        delete_file(filename)
    return new_filename


def duplicate_file(filename: str) -> str:
    unit = read_file(filename)
    base, n = clean_name(unit["name"], "Kopie"), 2
    while (library_dir() / filename_for(f"{base} ({n})")).exists():
        n += 1
    return write_file(f"{base} ({n})", unit["objects"])


# ------------------------------------------------------------------ Aktive Buehne

class Store:
    """Die aktive Buehne (Name, Datei, Arbeitskopie der Koerper, gespeicherter Stand) plus die Show-Daten der 3D-Simulation (Raum-Einstellungen, Scheinwerfer-Positionen)."""

    def __init__(self) -> None:
        self.name = ""
        self.filename: Optional[str] = None
        self.objects: List[Dict[str, Any]] = []
        self.saved_objects: List[Dict[str, Any]] = []
        self.revision = 0
        self.ready = False
        self.room: Dict[str, Any] = dict(ROOM_DEFAULTS)
        self.layout: Dict[str, Dict[str, Any]] = {}

    # -- Zugriff
    def ensure(self) -> None:
        if self.ready:
            return
        self.ready = True
        self.room = normalize_room(getattr(_state(), "sim_room", None))        # zuletzt benutzte Einstellungen (fuer eine neue Show)
        last = library_dir() / ".last"
        try:
            filename = last.read_text(encoding="utf-8").strip() if last.is_file() else ""
            if filename:
                self.load(filename, remember=False)
                return
        except (OSError, StageError):
            pass
        self.new(create_file=False)                          # erster Start: leere, noch nicht gespeicherte Buehne (keine Datei ungefragt)

    def remember(self) -> None:
        try:
            (library_dir() / ".last").write_text(self.filename or "", encoding="utf-8")
        except OSError:
            pass

    def state_of(self) -> str:
        if not self.filename:
            return "none"
        try:
            return "same" if digest(read_file(self.filename)["objects"]) == digest(self.objects) else "modified"
        except StageError:
            return "missing"

    def payload(self, with_objects: bool = True, source: Optional[str] = None) -> Dict[str, Any]:
        self.ensure()
        out: Dict[str, Any] = {"name": self.name, "filename": self.filename, "dirty": digest(self.objects) != digest(self.saved_objects), "state": self.state_of(),
                               "count": len(self.objects), "revision": self.revision, "source": source, "room": self.room, "fixture_layout": self.layout}
        if with_objects:
            out["objects"] = self.objects
        return out

    # -- Aenderungen
    def set_objects(self, raw: Any) -> None:
        self.ensure()
        self.objects = normalize_objects(raw)
        self.revision += 1

    def set_room(self, raw: Any) -> None:
        self.ensure()
        self.room = normalize_room(raw)
        self.revision += 1
        state = _state()
        state.sim_room = dict(self.room)                          # zuletzt benutzte Einstellungen in der App-Config merken (fuer eine neue Show)
        state.save_app_config()

    def set_layout(self, raw: Any) -> None:
        self.ensure()
        self.layout = normalize_layout(raw)
        self.revision += 1

    def new(self, name: str = "", create_file: bool = True) -> None:
        """Neue, leere Buehne. Mit create_file entsteht die Datei sofort (die Buehne steht gleich in der Liste, der Name laesst sich spaeter aendern). Raum-Einstellungen und
        Scheinwerfer-Positionen gehoeren zur Show und bleiben."""
        self.ready = True
        self.name = clean_name(name) or suggest_name()
        self.filename = write_file(self.name, [], overwrite=False) if create_file else None
        self.objects = []
        self.saved_objects = []
        self.revision += 1
        self.remember()

    def reset(self) -> None:
        """Neue Show: leere, noch nicht gespeicherte Buehne, keine Scheinwerfer-Positionen. Die Raum-Einstellungen bleiben."""
        self.new(create_file=False)
        self.layout = {}

    def reference(self) -> Dict[str, Any]:
        """Fuer die Showfile: nur der Verweis auf die Buehnen-Datei (Name, Dateiname) plus Raum-Einstellungen und Scheinwerfer-Positionen - die Koerper stehen in der Datei."""
        self.ensure()
        known = set(getattr(_state(), "fixtures", {}) or {})
        layout = {fid: item for fid, item in self.layout.items() if fid in known}
        return {"name": self.name, "filename": self.filename, "room": dict(self.room), "fixture_layout": copy.deepcopy(layout)}

    def persist(self) -> None:
        """Beim Speichern der Show: ungespeicherte Aenderungen der Buehne in ihre Datei schreiben; eine Buehne ohne Datei (aber mit Koerpern) bekommt eine."""
        self.ensure()
        changed = digest(self.objects) != digest(self.saved_objects)
        if not changed and (self.filename or not self.objects):
            return
        try:
            if self.filename:
                self.filename = write_file(self.name, self.objects, overwrite=True)
            else:
                name = self.name
                while (library_dir() / filename_for(name)).exists():
                    name = suggest_name()
                self.name = clean_name(name)
                self.filename = write_file(self.name, self.objects, overwrite=False)
            self.saved_objects = copy.deepcopy(self.objects)
            self.revision += 1
            self.remember()
        except StageError:
            pass

    def restore(self, raw: Any) -> None:
        """Beim Laden einer Show: Raum-Einstellungen und Positionen aus der Show, die Koerper aus der Buehnen-Datei. Fehlt die Datei, ist die Buehne leer (die Show
        meldet sie als fehlend: filename None). Show ohne Buehne: leere Buehne."""
        if not isinstance(raw, dict):
            self.reset()
            return
        self.ready = True
        if isinstance(raw.get("room"), dict):
            self.room = normalize_room(raw["room"])
        self.layout = normalize_layout(raw.get("fixture_layout"))
        self.name = clean_name(raw.get("name"), suggest_name())
        self.objects, self.saved_objects, self.filename = [], [], None
        filename = raw.get("filename") if valid_filename(raw.get("filename")) else None
        if filename:
            try:
                unit = read_file(filename)
                self.objects = copy.deepcopy(unit["objects"])
                self.saved_objects = copy.deepcopy(unit["objects"])
                self.filename = filename
            except StageError:
                pass
        self.revision += 1
        self.remember()

    def load(self, filename: str, remember: bool = True) -> None:
        unit = read_file(filename)
        self.ready = True
        self.name, self.filename = unit["name"], filename
        self.objects = copy.deepcopy(unit["objects"])
        self.saved_objects = copy.deepcopy(unit["objects"])
        self.revision += 1
        if remember:
            self.remember()

    def discard(self) -> None:
        self.ensure()
        if self.filename:
            try:
                self.objects = copy.deepcopy(read_file(self.filename)["objects"])
                self.saved_objects = copy.deepcopy(self.objects)
            except StageError:
                self.objects = copy.deepcopy(self.saved_objects)
        else:
            self.objects = copy.deepcopy(self.saved_objects)
        self.revision += 1

    def save(self, name: str, overwrite: bool) -> None:
        self.ensure()
        filename = write_file(name, self.objects, overwrite=overwrite)
        self.name, self.filename = clean_name(name), filename
        self.saved_objects = copy.deepcopy(self.objects)
        self.revision += 1
        self.remember()


store = Store()


# ------------------------------------------------------------------ REST

def _state():
    from app.state_manager import state                      # spaet importieren: state_manager importiert dieses Modul
    return state


def _server():
    from app import server                                   # spaet importieren: server.py bindet diesen Router ein
    return server


def _bus():
    return _server().event_bus


def _error(exc: StageError, **extra: Any) -> JSONResponse:
    return JSONResponse({"ok": False, "error": exc.code, **extra}, status_code=_STATUS.get(exc.code, 400))


async def _broadcast(source: Optional[str] = None, touch: bool = True) -> Dict[str, Any]:
    """Aenderung an alle Geraete melden. touch: die Buehne steckt in der Show -> die Show gilt als geaendert."""
    srv = _server()
    if touch:
        srv.state.mark_dirty()
    payload = store.payload(source=source)
    payload["show_dirty"] = srv.state.is_dirty
    await _bus().broadcast({"type": "sim_stage_changed", "payload": payload})
    return payload


@router.get("/api/sim-stage")
async def current() -> JSONResponse:
    return JSONResponse(store.payload())


@router.get("/api/sim-stages")
async def listing() -> JSONResponse:
    store.ensure()
    return JSONResponse({"files": list_files(), "current": store.payload(with_objects=False), "suggested_name": suggest_name([store.name])})


@router.post("/api/sim-stage/objects")
async def set_objects(request: Request) -> JSONResponse:
    """Arbeitskopie setzen (vom Panel nach jeder Aenderung); "source" = Kennung des sendenden Panels, es ignoriert das Echo."""
    body = await request.json()
    store.set_objects(body.get("objects"))
    payload = await _broadcast(source=str(body.get("source") or "")[:40] or None)
    return JSONResponse({"ok": True, **{k: v for k, v in payload.items() if k != "objects"}})


@router.post("/api/sim-room")
async def set_room(request: Request) -> JSONResponse:
    """Raum-Einstellungen setzen (von jedem Geraet); "source" = Kennung des Senders, er ignoriert das Echo."""
    body = await request.json()
    store.set_room(body.get("room"))
    payload = await _broadcast(source=str(body.get("source") or "")[:40] or None)
    return JSONResponse({"ok": True, "room": payload["room"]})


@router.post("/api/sim-fixtures")
async def set_fixtures(request: Request) -> JSONResponse:
    """Positionen der Scheinwerfer setzen (Modus "Scheinwerfer"); "source" = Kennung des Senders, er ignoriert das Echo. Die Positionen gehoeren zur Show (Show gilt als geaendert)."""
    body = await request.json()
    store.set_layout(body.get("layout"))
    payload = await _broadcast(source=str(body.get("source") or "")[:40] or None)
    return JSONResponse({"ok": True, "fixture_layout": payload["fixture_layout"]})


@router.post("/api/sim-stage/discard")
async def discard() -> JSONResponse:
    store.discard()
    return JSONResponse({"ok": True, **{k: v for k, v in (await _broadcast()).items() if k != "objects"}})


@router.post("/api/sim-stage/new")
async def new_stage(request: Request) -> JSONResponse:
    body = await request.json()
    try:
        store.new(clean_name(body.get("name")))
    except StageError as exc:
        return _error(exc)
    await _broadcast()
    return JSONResponse({"ok": True, "name": store.name, "filename": store.filename})


@router.post("/api/sim-stage/save")
async def save_stage(request: Request) -> JSONResponse:
    body = await request.json()
    store.ensure()
    name = clean_name(body.get("name"), store.name)
    try:
        store.save(name, overwrite=bool(body.get("overwrite")))
    except StageError as exc:
        return _error(exc, name=name)
    await _broadcast(touch=False)
    return JSONResponse({"ok": True, "name": store.name, "filename": store.filename})


@router.post("/api/sim-stage/load")
async def load_stage(request: Request) -> JSONResponse:
    body = await request.json()
    try:
        store.load(str(body.get("filename", "")))
    except StageError as exc:
        return _error(exc)
    await _broadcast()
    return JSONResponse({"ok": True, "name": store.name})


@router.post("/api/sim-stage/rename")
async def rename_stage(request: Request) -> JSONResponse:
    body = await request.json()
    filename = str(body.get("filename", ""))
    try:
        new_filename = rename_file(filename, str(body.get("new_name", "")), overwrite=bool(body.get("overwrite")))
    except StageError as exc:
        return _error(exc)
    if store.filename == filename:                           # die aktive Buehne stammt aus dieser Datei: Datei und Name folgen
        store.filename, store.name = new_filename, clean_name(body.get("new_name"))
        store.remember()
        store.revision += 1
        await _broadcast()
    return JSONResponse({"ok": True, "filename": new_filename})


@router.post("/api/sim-stage/duplicate")
async def duplicate_stage(request: Request) -> JSONResponse:
    body = await request.json()
    try:
        filename = duplicate_file(str(body.get("filename", "")))
    except StageError as exc:
        return _error(exc)
    return JSONResponse({"ok": True, "filename": filename})


@router.post("/api/sim-stage/delete")
async def delete_stage(request: Request) -> JSONResponse:
    body = await request.json()
    filename = str(body.get("filename", ""))
    try:
        delete_file(filename)
    except StageError as exc:
        return _error(exc)
    if store.filename == filename:                           # die Arbeitskopie bleibt, ist aber keiner Datei mehr zugeordnet
        store.filename = None
        store.saved_objects = []
        store.remember()
        store.revision += 1
        await _broadcast()
    return JSONResponse({"ok": True})
