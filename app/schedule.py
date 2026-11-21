# Copyright (C) 2026 Samuel Zenker
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Zeitplan: Befehle der Befehlszeile zu einer Uhrzeit (an Wochentagen oder an einem Datum) - Fassadenlicht, "Einlass 19:00", Pausenmusik, "Cue-Liste um 18:55 starten".

Der Zeitplan gehoert zur SHOW (steht in der Show-Datei, wird mit der Show gesichert und geladen). Er laeuft, solange OpenCue laeuft; `_schedule_pump` in app/server.py prueft alle
0,25 s, ob eine Uhrzeit zwischen zwei Pruefungen liegt (app/timeofday.py: crossed) und fuehrt den Befehl wie einen getippten aus (er steht im Befehlsverlauf). Wacht der Rechner aus dem
Ruhezustand auf, zaehlen nur Zeiten der letzten 60 Sekunden (sonst wuerde alles Verpasste auf einmal feuern). Ein Eintrag mit Datum gilt einmal und schaltet sich danach aus.

Eintrag: {id, enabled, label, time "HH:MM[:SS]", days [0-6, Montag = 0; leer = jeden Tag], date "" | "JJJJ-MM-TT", command}

Ausserdem gibt es den Cue-Ausloeser "Uhrzeit" (clock): ein Cue wartet als naechster Cue einer laufenden Liste auf seine Uhrzeit (state_manager.Cue.clock_time / clock_days).
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, List

from app import timeofday

MAX_ENTRIES = 200
MAX_COMMAND_LENGTH = 1000


def normalize(raw: Any) -> List[Dict[str, Any]]:
    """Bereinigt die Liste vom Client oder aus der Show-Datei: nur bekannte Felder, begrenzte Laengen, eindeutige Ids; Unbrauchbares wird weggelassen."""
    out: List[Dict[str, Any]] = []
    seen = set()
    if not isinstance(raw, list):
        return out
    for item in raw[:MAX_ENTRIES]:
        if not isinstance(item, dict):
            continue
        time_text = timeofday.clean_time(item.get("time"))
        if time_text is None:
            continue
        key = str(item.get("id", "")).strip()[:40]
        if not key or key in seen:
            key = uuid.uuid4().hex[:12]
        seen.add(key)
        date = timeofday.clean_date(item.get("date"))
        out.append({
            "id": key,
            "enabled": item.get("enabled", True) is not False,
            "label": " ".join(str(item.get("label", "")).split())[:60],
            "time": time_text,
            "days": [] if date else timeofday.clean_days(item.get("days")),
            "date": date,
            "command": " ".join(str(item.get("command", "")).split())[:MAX_COMMAND_LENGTH],
        })
    return out
