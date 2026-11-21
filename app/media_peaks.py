# Copyright (C) 2026 Samuel Zenker
# SPDX-License-Identifier: GPL-3.0-or-later
"""
media_peaks.py
Wellenform eines Mediums (Audio oder die Tonspur eines Videos) fuer den Timeline-Editor: GET /api/media/<id>/peaks.

- ffmpeg (das mitgelieferte, wie bei den Kameras) dekodiert den Ton als Mono mit 8 kHz; daraus werden je 10 ms (PEAKS_PER_SECOND = 100) der groesste Betrag gebildet und als Bytes
  (0..255) abgelegt. So bleibt die Wellenform auch bei einer Stunde Musik klein (rund 360 KB) und laesst sich beliebig herauszoomen.
- Das Ergebnis liegt neben dem Medium im Medien-Ordner (<id>.peaks) und wird beim naechsten Mal sofort geliefert. Mehrere gleichzeitige Anfragen derselben Datei rechnen nur einmal.
- Zusaetzlich GET /api/timeline/sources: welche Medien-Player-Panels (Konsole + Fernzugriffs-Geraete) welches Medium bei welcher Timecode-Zeit starten.
- Antwort: {"pps": 100, "duration_ms": ..., "data": "<Base64 der Bytes>"}; ohne ffmpeg 503 {"error": "ffmpeg_missing"}; unbekanntes Medium 404.
"""
from __future__ import annotations

import asyncio
import base64
import logging
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app import media_store

logger = logging.getLogger("opencue.peaks")
router = APIRouter()

PEAKS_PER_SECOND = 100
SAMPLE_RATE = 8000
BLOCK = SAMPLE_RATE // PEAKS_PER_SECOND                 # 80 Samples = 10 ms
MAGIC = b"OCPK1"
_locks: Dict[str, asyncio.Lock] = {}


def cache_path(media_id: str) -> Optional[Path]:
    base = media_store.path_for(media_id)
    return base.with_name(media_id + ".peaks") if base is not None else None


def _creation_flags() -> int:
    return 0x08000000 if sys.platform == "win32" else 0                      # CREATE_NO_WINDOW


def compute(path: Path, ffmpeg: str) -> Tuple[bytes, int]:
    """Spitzenwerte einer Datei: (Bytes, Dauer in ms). Wirft RuntimeError, wenn ffmpeg scheitert (kein Ton, kaputte Datei)."""
    import numpy as np                                                      # erst hier: numpy wird nur gebraucht, wenn eine Wellenform berechnet wird
    command = [ffmpeg, "-v", "error", "-nostdin", "-i", str(path), "-vn", "-ac", "1", "-ar", str(SAMPLE_RATE), "-f", "f32le", "-"]
    proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=_creation_flags())
    out = bytearray()
    carry = np.zeros(0, dtype=np.float32)
    total = 0
    try:
        assert proc.stdout is not None
        while True:
            raw = proc.stdout.read(BLOCK * 4 * 2000)                         # 20 s je Lesevorgang
            if not raw:
                break
            data = np.frombuffer(raw[: len(raw) // 4 * 4], dtype=np.float32)
            if carry.size:
                data = np.concatenate([carry, data])
            usable = (data.size // BLOCK) * BLOCK
            carry = data[usable:].copy()
            if usable:
                peaks = np.abs(data[:usable]).reshape(-1, BLOCK).max(axis=1)
                out += np.clip(peaks * 255.0, 0, 255).astype(np.uint8).tobytes()
            total += data.size
        if carry.size:                                                       # der Rest (weniger als 10 ms) zaehlt als letzter Wert
            out += bytes([int(min(255, float(np.abs(carry).max()) * 255.0))])
    finally:
        proc.stdout.close() if proc.stdout else None
        code = proc.wait(timeout=30)
        err = proc.stderr.read().decode("utf-8", "replace") if proc.stderr else ""
        if proc.stderr:
            proc.stderr.close()
    if code != 0 and not out:
        raise RuntimeError(err.strip().splitlines()[-1] if err.strip() else f"ffmpeg exit {code}")
    return bytes(out), int(total * 1000 / SAMPLE_RATE)


def load_cache(media_id: str) -> Optional[Tuple[bytes, int]]:
    path = cache_path(media_id)
    if path is None or not path.is_file():
        return None
    try:
        raw = path.read_bytes()
        if raw[:5] != MAGIC:
            return None
        duration = int.from_bytes(raw[5:9], "little")
        return raw[9:], duration
    except OSError:
        return None


def save_cache(media_id: str, data: bytes, duration_ms: int) -> None:
    path = cache_path(media_id)
    if path is None:
        return
    try:
        path.write_bytes(MAGIC + int(duration_ms).to_bytes(4, "little") + data)
    except OSError:
        logger.debug("Wellenform konnte nicht zwischengespeichert werden", exc_info=True)


def peaks_for(media_id: str) -> Dict[str, Any]:
    """Wellenform eines Mediums (blockierend). Rueckgabe wie die HTTP-Antwort oder {"error": code, "status": n}."""
    from app.host_cameras import find_ffmpeg
    cached = load_cache(media_id)
    if cached is not None:
        return {"pps": PEAKS_PER_SECOND, "duration_ms": cached[1], "data": base64.b64encode(cached[0]).decode("ascii")}
    path = media_store.path_for(media_id)
    if path is None or not path.is_file():
        return {"error": "not_found", "status": 404}
    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        return {"error": "ffmpeg_missing", "status": 503}
    try:
        data, duration = compute(path, ffmpeg)
    except Exception as exc:                                                 # noqa: BLE001
        logger.warning("Wellenform von %s fehlgeschlagen: %s", media_id[:12], exc)
        return {"error": "decode_failed", "message": str(exc), "status": 422}
    save_cache(media_id, data, duration)
    return {"pps": PEAKS_PER_SECOND, "duration_ms": duration, "data": base64.b64encode(data).decode("ascii")}


@router.get("/api/timeline/sources")
async def timeline_sources() -> JSONResponse:
    """Welche Medien starten bei welcher Zeit des Timecodes? Aus allen Medien-Player-Panels der Show-Konsole UND der Fernzugriffs-Geraete (Modus "Timecode", Medium gewaehlt).
    Der Timeline-Editor zeigt daraus von selbst die Tonspuren - man muss kein Lied von Hand waehlen. [{"panel_id", "origin": "console"|"remote", "media_id", "tc_start_ms", "name"}]"""
    from app import remote
    from app.state_manager import state
    found: list = []
    seen: set = set()

    def scan(panels: Any, origin: str) -> None:
        for panel in panels or []:
            if getattr(panel, "type", "") != "media_player":
                continue
            mc = getattr(panel, "module_config", None) or {}
            media_id = str(mc.get("media_id") or "")
            if not media_id or mc.get("sync") == "free":
                continue
            try:
                start = max(0, int(mc.get("tc_start_ms") or 0))
            except (TypeError, ValueError):
                start = 0
            key = (media_id, start)
            if key in seen:
                continue
            seen.add(key)
            meta = state.media.get(media_id) or {}
            found.append({"panel_id": str(getattr(panel, "id", "")), "origin": origin, "media_id": media_id, "tc_start_ms": start, "name": str(meta.get("name") or ""), "kind": str(meta.get("kind") or "")})

    scan(state.panels, "console")
    for session in list(remote.sessions.values()):
        scan(session.panels, "remote")
    return JSONResponse({"sources": found}, headers={"Cache-Control": "no-store"})


@router.get("/api/media/{media_id}/peaks")
async def get_peaks(media_id: str) -> JSONResponse:
    if media_store.path_for(media_id) is None:
        return JSONResponse({"error": "not_found"}, status_code=404)
    lock = _locks.setdefault(media_id, asyncio.Lock())
    async with lock:                                                         # zwei Fenster, dieselbe Datei: nur einmal rechnen
        result = await asyncio.to_thread(peaks_for, media_id)
    status = int(result.pop("status", 200))
    return JSONResponse(result, status_code=status, headers={"Cache-Control": "no-store"})
