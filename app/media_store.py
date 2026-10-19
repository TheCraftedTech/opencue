"""
media_store.py
Medien (Video/Audio) der Show: Ablage und Pruefung.

- Jedes Medium wird beim Hinzufuegen in den lokalen Ordner "media" im Datenordner KOPIERT (Dateiname = SHA-256 des Inhalts, ohne Endung): gleiche Datei = ein Eintrag,
  nichts liegt doppelt, ein Name kann nie auf andere Ordner zeigen. Es gibt kein Verknuepfen und kein Einbetten in die Showfile.
- Die Show kennt nur Metadaten (Id, Name, Typ, Groesse, Dauer). Die Bytes gehen nie in WebSocket-Schnappschuesse oder die Showfile; abgespielt wird ueber
  GET /api/media/<id> (mit Bereichsanfragen, damit Vor-/Zurueckspulen geht). Wer eine Show weitergibt, nimmt die Medien im Export-Paket (ZIP) mit (app/file_manager.py).
- Entfernen loescht die Kopie wirklich (ausser eine andere gespeicherte Show nennt sie noch).
- Dateitypen werden am Inhalt erkannt (Magic Bytes), nicht an der Endung.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from app import paths as _paths

MAX_FILE_BYTES = 1024 * 1024 * 1024        # 1 GB: groesser wird nicht angenommen/verknuepft
ID_RE = re.compile(r"^[0-9a-f]{64}$")


def store_dir() -> Path:
    return _paths.FIXTURES_DIR.parent / "media"


def path_for(media_id: str) -> Optional[Path]:
    """Pfad der gespeicherten Datei - nur fuer eine gueltige ID (64 Hex-Zeichen), sonst None."""
    if not isinstance(media_id, str) or not ID_RE.match(media_id):
        return None
    return store_dir() / media_id
def file_path(meta: Dict[str, Any]) -> Optional[Path]:
    """Wo die Datei zu diesem Medium liegt: die Kopie im Medien-Ordner."""
    return path_for(str(meta.get("id", "")))
def sniff(head: bytes, filename: str = "") -> Optional[Tuple[str, str, str]]:
    """Erkennt Video/Audio am Dateianfang. Rueckgabe (mime, art, kuerzel) oder None.
    art: 'video' | 'audio' (bei mp4/ogg/webm nach Dateiendung/Marke; abgespielt wird immer in einem <video>-Element)."""
    ext = Path(filename).suffix.lower()
    if len(head) >= 12 and head[4:8] == b"ftyp":
        brand = head[8:12]
        audio_brand = brand in (b"M4A ", b"M4B ", b"F4A ") or ext in (".m4a", ".m4b")
        return ("audio/mp4", "audio", "m4a") if audio_brand else ("video/mp4", "video", "mp4")
    if head[:4] == b"\x1a\x45\xdf\xa3":
        return ("audio/webm", "audio", "weba") if ext in (".weba", ".mka") else ("video/webm", "video", "webm")
    if head[:4] == b"OggS":
        return ("audio/ogg", "audio", "ogg") if ext in (".oga", ".ogg", ".opus", ".spx") else ("video/ogg", "video", "ogv")
    if head[:4] == b"RIFF" and head[8:12] == b"WAVE":
        return ("audio/wav", "audio", "wav")
    if len(head) >= 2 and head[0] == 0xFF and head[1] in (0xF1, 0xF9):          # AAC (ADTS)
        return ("audio/aac", "audio", "aac")
    if head[:3] == b"ID3" or (len(head) >= 2 and head[0] == 0xFF and (head[1] & 0xE0) == 0xE0 and (head[1] & 0x06) != 0):
        return ("audio/mpeg", "audio", "mp3")
    if head[:4] == b"fLaC":
        return ("audio/flac", "audio", "flac")
    return None


def clean_name(name: str) -> str:
    base = Path(str(name or "").replace("\\", "/")).name
    base = re.sub(r"[\x00-\x1f<>:\"|?*]+", "_", base).strip(" .")
    return (base or "media")[:120]


class MediaError(Exception):
    def __init__(self, code: str, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.code, self.message, self.status = code, message, status


def ingest(temp_path: Path, filename: str, size: int, digest: str, duration_ms: Any = None) -> Dict[str, Any]:
    """Nimmt eine vollstaendig empfangene Datei in den Speicher auf (verschiebt temp_path). Rueckgabe: Metadaten."""
    if size <= 0:
        raise MediaError("invalid_file", "Die Datei ist leer")
    if size > MAX_FILE_BYTES:
        raise MediaError("too_large", "Die Datei ist zu gross (max. 1 GB)", 413)
    with open(temp_path, "rb") as handle:
        head = handle.read(64)
    kind = sniff(head, filename)
    if kind is None:
        raise MediaError("invalid_type", "Das ist keine unterstuetzte Video- oder Audiodatei (MP4, WebM, OGG, WAV, MP3, FLAC, AAC, M4A)", 415)
    mime, art, _ = kind
    target = path_for(digest)
    if target is None:
        raise MediaError("invalid_file", "Ungueltige Pruefsumme")
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        temp_path.unlink(missing_ok=True)            # gleicher Inhalt liegt schon da
    else:
        os.replace(temp_path, target)
    try:
        duration = max(0, int(float(duration_ms))) if duration_ms not in (None, "") else None
    except (TypeError, ValueError):
        duration = None
    return {"id": digest, "name": clean_name(filename), "mime": mime, "kind": art, "size": size, "duration_ms": duration}


def file_digest(path: Path) -> Tuple[str, int]:
    sha, total = hashlib.sha256(), 0
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            sha.update(chunk)
            total += len(chunk)
    return sha.hexdigest(), total


def temp_file() -> Tuple[Path, Any]:
    """Temporaere Zieldatei im selben Ordner (damit os.replace auf demselben Laufwerk bleibt)."""
    directory = store_dir()
    directory.mkdir(parents=True, exist_ok=True)
    handle, name = tempfile.mkstemp(prefix=".upload-", suffix=".part", dir=str(directory))
    return Path(name), os.fdopen(handle, "wb")


def exists(meta_or_id: Any) -> bool:
    """Gibt es die Datei (noch)? Akzeptiert die Metadaten oder eine ID (Kopie)."""
    meta = meta_or_id if isinstance(meta_or_id, dict) else {"id": meta_or_id}
    path = file_path(meta)
    return bool(path and path.is_file())
def delete_stored(media_id: str) -> bool:
    """Die Kopie im Medien-Ordner loeschen. Rueckgabe: wurde etwas geloescht?"""
    path = path_for(media_id)
    if path is None or not path.is_file():
        return False
    try:
        path.unlink()
        return True
    except OSError:
        return False


def ids_in_showfile(path: Any) -> list:
    """IDs der Medien, die eine Showfile nennt."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    found = []
    for entry in ((data.get("media") or {}).values() if isinstance(data, dict) else []):
        if isinstance(entry, dict) and ID_RE.match(str(entry.get("id", ""))):
            found.append(str(entry["id"]))
    return found
def referenced_elsewhere(media_id: str, directories: list, exclude: Optional[str] = None) -> Optional[str]:
    """Nennt eine andere gespeicherte Showfile, die dieses Medium noch erwaehnt (reine Textsuche nach der ID, ohne zu parsen)."""
    needle = media_id.encode("ascii", "ignore")
    skip = os.path.normcase(str(exclude)) if exclude else None
    for directory in directories:
        try:
            files = [p for p in Path(directory).glob("*.json") if p.is_file()]
        except OSError:
            continue
        for path in files:
            if skip and os.path.normcase(str(path)) == skip:
                continue
            try:
                tail = b""
                with open(path, "rb") as handle:
                    for chunk in iter(lambda: handle.read(4 * 1024 * 1024), b""):
                        if needle in tail + chunk:
                            return path.stem
                        tail = chunk[-(len(needle) - 1):]
            except OSError:
                continue
    return None


# ------------------------------------------------------------------------------------------ Showfile (nur Metadaten)
def public_meta(meta: Dict[str, Any]) -> Dict[str, Any]:
    """Eintrag fuer die Showfile: nur Metadaten."""
    return {k: meta[k] for k in ("id", "name", "mime", "kind", "size", "duration_ms") if k in meta}


def clean_entry(entry: Any) -> Optional[Dict[str, Any]]:
    """Eintrag aus einer Showfile pruefen. Rueckgabe: bereinigte Metadaten oder None (ungueltig). Die Datei selbst liegt (oder fehlt) im Medien-Ordner."""
    if not isinstance(entry, dict):
        return None
    media_id = str(entry.get("id", ""))
    if not ID_RE.match(media_id):
        return None
    mime = str(entry.get("mime", ""))
    if not re.match(r"^(audio|video)/[a-z0-9.+-]{1,30}$", mime):
        return None
    try:
        size = int(entry.get("size", 0))
    except (TypeError, ValueError):
        return None
    return {"id": media_id, "name": clean_name(str(entry.get("name", "media"))), "mime": mime, "kind": "audio" if entry.get("kind") == "audio" else "video", "size": size,
            "duration_ms": entry.get("duration_ms") if isinstance(entry.get("duration_ms"), int) else None}
