# Copyright (C) 2026 Samuel Zenker
# SPDX-License-Identifier: GPL-3.0-or-later
"""
timeline_tracks.py
Befehlsspuren der Timeline: Befehle der Befehlszeile, die der GLOBALE TIMECODE zu bestimmten Zeiten ausfuehrt - unabhaengig von den Cues ("Blackout Off" bei 1:30, "Cuelist Show Go" bei 2:00,
"Effect Off" beim Refrain). Sie gehoeren zur SHOW (stehen in der Show-Datei, werden mit ihr gesichert und geladen) und werden im Timeline-Editor (static/js/timeline_panel.js) auf
Spuren gelegt.

Spur:   {id, name, events: [{id, ms, command}]}
Ablauf: Wie bei Cues mit Ausloeser "timecode": laeuft der Timecode VORWAERTS durch `ms`, fuehrt der Server den Befehl aus (er steht im Befehlsverlauf). Springen (Seek) und Rueckwaertslauf
        loesen nichts aus (siehe `due()` und `_timecode_cross` in app/server.py).
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Tuple

MAX_TRACKS = 16
MAX_EVENTS = 500                       # je Spur
MAX_COMMAND_LENGTH = 1000
MAX_NAME_LENGTH = 60
MAX_MS = 100 * 3600 * 1000


def _id(raw: Any, seen: set) -> str:
    key = str(raw or "").strip()[:40]
    if not key or key in seen:
        key = uuid.uuid4().hex[:12]
    seen.add(key)
    return key


def normalize(raw: Any) -> List[Dict[str, Any]]:
    """Bereinigt die Spuren vom Client oder aus der Show-Datei: bekannte Felder, begrenzte Laengen, eindeutige Ids, Zeiten 0..100 h (gerundet); Unbrauchbares wird weggelassen."""
    out: List[Dict[str, Any]] = []
    if not isinstance(raw, list):
        return out
    track_ids: set = set()
    for index, track in enumerate(raw[:MAX_TRACKS]):
        if not isinstance(track, dict):
            continue
        name = " ".join(str(track.get("name") or "").split())[:MAX_NAME_LENGTH] or f"Commands {index + 1}"
        event_ids: set = set()
        events: List[Dict[str, Any]] = []
        for event in (track.get("events") if isinstance(track.get("events"), list) else [])[:MAX_EVENTS]:
            if not isinstance(event, dict):
                continue
            command = " ".join(str(event.get("command") or "").split())[:MAX_COMMAND_LENGTH]
            try:
                ms = int(round(float(event.get("ms"))))
            except (TypeError, ValueError):
                continue
            if not 0 <= ms <= MAX_MS:
                continue
            events.append({"id": _id(event.get("id"), event_ids), "ms": ms, "command": command})
        events.sort(key=lambda e: (e["ms"], e["id"]))
        out.append({"id": _id(track.get("id"), track_ids), "name": name, "events": events})
    return out


def due(tracks: Any, prev_ms: float, cur_ms: float) -> List[Tuple[int, str, str]]:
    """Befehle, deren Zeit in (prev_ms, cur_ms] liegt: [(ms, Spur-Id, Befehl)] in zeitlicher Reihenfolge (leere Befehle fehlen)."""
    found: List[Tuple[int, str, str]] = []
    for track in tracks or []:
        for event in track.get("events", []):
            if event.get("command") and prev_ms < event["ms"] <= cur_ms:
                found.append((int(event["ms"]), str(track.get("id", "")), str(event["command"])))
    found.sort(key=lambda item: item[0])
    return found
