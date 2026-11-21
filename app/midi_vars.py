# Copyright (C) 2026 Samuel Zenker
# SPDX-License-Identifier: GPL-3.0-or-later
"""
midi_vars.py
Der Cue-Ausloeser "midi": ein Cue wartet auf EIN bestimmtes MIDI-Signal und feuert, wenn es eintrifft - genau wie der Ausloeser "audio" (app/audio_vars.py):
er gilt, solange der Cue der FOLGENDE Cue einer laufenden Liste ist (erst die Liste mit Go starten, dann wartet der naechste MIDI-Cue auf sein Signal).

Felder am Cue (app/state_manager.py):  midi_type  note | cc | pc      midi_number  0-127      midi_channel  0 = jeder Kanal, 1-16      midi_value  nur bei cc: Schwelle 1-127
  note   feuert beim Druecken der Taste (Note On mit Anschlagstaerke > 0)
  cc     feuert, sobald der Reglerwert von UNTEN die Schwelle erreicht (Taste als CC: 127 >= 64; ein Regler: beim Ueberschreiten; Zurueckdrehen und wieder hoch feuert erneut)
  pc     feuert beim Programmwechsel mit dieser Nummer
Leichtgewichtig (nur Standardbibliothek): der Zustand und die Befehlszeile brauchen ihn auch ohne MIDI-Bibliothek.
"""
from __future__ import annotations

from typing import Any, Dict, Tuple

CUE_MIDI_TYPES: Tuple[str, ...] = ("note", "cc", "pc")
CUE_MIDI_DEFAULT_NUMBER = 60
CUE_MIDI_DEFAULT_THRESHOLD = 64
_ALIASES = {"controller": "cc", "control": "cc", "ctrl": "cc", "program": "pc", "prg": "pc", "programchange": "pc", "key": "note", "pad": "note", "note_on": "note"}
_NAMES = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")


def _int(value: Any, default: int, low: int, high: int) -> int:
    try:
        number = float(value)
        if number != number or number in (float("inf"), float("-inf")):
            raise ValueError
    except (TypeError, ValueError):
        return default
    return max(low, min(high, int(round(number))))


def clean_midi_trigger(kind: Any, number: Any, channel: Any, value: Any) -> Tuple[str, int, int, int]:
    """Art, Nummer, Kanal und Schwelle eines MIDI-Ausloesers pruefen: unbekannte Art -> note; Nummer 0-127, Kanal 0-16 (0 = jeder), Schwelle 1-127;
    Fehlendes oder Ungueltiges bekommt den Vorgabewert."""
    text = str(kind or "").strip().lower().replace(" ", "")
    text = _ALIASES.get(text, text)
    k = text if text in CUE_MIDI_TYPES else "note"
    return (k, _int(number, CUE_MIDI_DEFAULT_NUMBER if k == "note" else 0, 0, 127), _int(channel, 0, 0, 16), _int(value, CUE_MIDI_DEFAULT_THRESHOLD, 1, 127))


def note_name(number: int) -> str:
    return f"{_NAMES[number % 12]}{number // 12 - 1}"


def label(kind: str, number: int, channel: int, value: int) -> str:
    """Kurzform wie in der Cue-Liste: "MIDI: Note C4 (60)", "MIDI: CC 20 >= 64 Ch 2", "MIDI: Program 5"."""
    if kind == "cc":
        text = f"CC {number} ≥ {value}"
    elif kind == "pc":
        text = f"Program {number}"
    else:
        text = f"Note {note_name(number)} ({number})"
    return f"MIDI: {text}" + (f" Ch {channel}" if channel else "")


def check(event: Dict[str, Any], kind: str, number: int, channel: int, value: int, memory: Dict[int, int]) -> bool:
    """Passt das MIDI-Ereignis (app/midi_engine.py parse(): type, channel, number, value) zum Ausloeser? `memory` merkt sich je Kanal den letzten CC-Wert (Flanke von unten)."""
    if channel and event.get("channel") != channel:
        return False
    kind_of_event = event.get("type")
    if kind == "note":
        return kind_of_event == "note_on" and event.get("number") == number
    if kind == "pc":
        return kind_of_event == "pc" and event.get("number") == number
    if kind_of_event != "cc" or event.get("number") != number:
        return False
    key = int(event.get("channel", 0))
    previous = memory.get(key, 0)
    current = int(event.get("value", 0))
    memory[key] = current
    return previous < value <= current
