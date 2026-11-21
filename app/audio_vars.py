# Copyright (C) 2026 Samuel Zenker
# SPDX-License-Identifier: GPL-3.0-or-later
"""
audio_vars.py
Die Audio-Variablen, die Effekt-Skripte lesen duerfen (wie `t`, `index`, `phase`), und eine Beispiel-Belegung fuer die Vorschau im Effekt-Studio.
Alle Namen beginnen mit `a_`, damit sie nie mit eigenen Variablen eines Skripts kollidieren. Die echten Werte liefert app/audio_engine.py.
Dieses Modul importiert nichts aus dem Programm (und kein numpy): die Skriptsprache und das Studio koennen es immer laden.

  a_active        1 = es kommt Audio (Quelle laeuft und ist nicht stumm), sonst 0
  a_level         Gesamtlautstaerke 0-1 (relativ zu den lautesten Stellen der letzten Sekunden)
  a_bass          Bass (Sub + Bass, ca. 20-150 Hz) 0-1;  a_mid  Mitten (150 Hz - 2,5 kHz);  a_high  Hoehen (ab 2,5 kHz)
  a_b1 .. a_b8    die acht Baender einzeln: 20-60, 60-150, 150-400, 400-1k, 1k-2,5k, 2,5k-5k, 5k-10k, 10k-20k Hz
  a_kick          Einsatz der Bassdrum: springt bei jedem Schlag auf 0-1 und klingt in ca. 0,15 s ab
  a_snare         Einsatz der Snare / Klatscher (wie a_kick);  a_hat  Hi-Hat (kuerzer)
  a_beat          Impuls bei jedem Beat des erkannten Tempos (springt auf 1, klingt ab)
  a_beat_phase    Position im Beat 0-1 (steigt gleichmaessig von einem Beat zum naechsten); ideal fuer tempo-synchrone Verlaeufe
  a_beat_count    laufende Nummer des Beats (zaehlt bei jedem Beat um 1 hoch)
  a_bpm           erkanntes (oder eingestelltes) Tempo in Schlaegen pro Minute
  a_conf          Sicherheit der Tempo-Erkennung 0-1
"""
from __future__ import annotations

import math
from typing import Dict, Tuple

AUDIO_VARS: Tuple[str, ...] = (
    "a_active", "a_level", "a_bass", "a_mid", "a_high",
    "a_b1", "a_b2", "a_b3", "a_b4", "a_b5", "a_b6", "a_b7", "a_b8",
    "a_kick", "a_snare", "a_hat", "a_beat", "a_beat_phase", "a_beat_count", "a_bpm", "a_conf",
)

BEAT_TAU = 0.18             # Abklingzeit der Impulse (Sekunden)
KICK_TAU = 0.15
SNARE_TAU = 0.15
HAT_TAU = 0.07


def silent() -> Dict[str, float]:
    """Alle Audio-Variablen ohne Audio (alles 0; das Tempo bleibt 0, `a_active` 0)."""
    return {name: 0.0 for name in AUDIO_VARS}


def demo_vars(t: float, bpm: float = 120.0) -> Dict[str, float]:
    """Beispiel-Belegung zum Zeitpunkt t (Sekunden) fuer die Vorschau im Effekt-Studio: ein gleichmaessiger Viervierteltakt mit Bassdrum auf jedem Schlag, Snare auf 2 und 4 und
    Hi-Hat auf jeder Achtel-Zwischenzeit - so sieht man, wie ein Audio-Effekt auf Musik reagieren wuerde."""
    bpm = max(30.0, min(240.0, float(bpm)))
    beats = t * bpm / 60.0
    count = math.floor(beats)
    phase = beats - count
    since_beat = phase * 60.0 / bpm
    kick = math.exp(-since_beat / KICK_TAU)
    snare = math.exp(-since_beat / SNARE_TAU) if count % 2 == 1 else 0.0
    eighths = beats * 2.0
    hat_since = (eighths - math.floor(eighths)) * 30.0 / bpm
    hat = math.exp(-hat_since / HAT_TAU) if math.floor(eighths) % 2 == 1 else 0.0
    b = [0.15 + 0.85 * kick, 0.12 + 0.8 * kick, 0.2 + 0.2 * kick + 0.4 * snare, 0.2 + 0.55 * snare, 0.15 + 0.4 * snare + 0.2 * hat, 0.1 + 0.3 * snare + 0.4 * hat, 0.05 + 0.6 * hat, 0.03 + 0.5 * hat]
    values = {
        "a_active": 1.0, "a_level": 0.45 + 0.4 * kick + 0.15 * snare,
        "a_bass": max(b[0], b[1]), "a_mid": max(b[2], b[3], b[4]), "a_high": max(b[5], b[6], b[7]),
        "a_kick": kick, "a_snare": snare, "a_hat": hat, "a_beat": kick,
        "a_beat_phase": phase, "a_beat_count": float(count), "a_bpm": bpm, "a_conf": 1.0,
    }
    for i, v in enumerate(b, 1):
        values[f"a_b{i}"] = min(1.0, v)
    return values


# ---- Cue-Ausloeser "audio": EIN Ausloeser mit einer Quelle und einem Wert (Cue.audio_source / Cue.audio_value)
#   beat, kick, snare, hat   Wert = jeder n-te Beat bzw. Schlag (1 = jeder)
#   level, bass, mid, high, b1 .. b8   Wert = Schwelle in Prozent: der Cue feuert, wenn der Pegel dieses Teils die Schwelle von unten erreicht
CUE_AUDIO_COUNT_SOURCES: Tuple[str, ...] = ("beat", "kick", "snare", "hat")
CUE_AUDIO_LEVEL_SOURCES: Tuple[str, ...] = ("level", "bass", "mid", "high", "b1", "b2", "b3", "b4", "b5", "b6", "b7", "b8")
CUE_AUDIO_SOURCES: Tuple[str, ...] = CUE_AUDIO_COUNT_SOURCES + CUE_AUDIO_LEVEL_SOURCES
CUE_AUDIO_DEFAULT_COUNT = 1.0
CUE_AUDIO_DEFAULT_LEVEL = 70.0


def clean_audio_trigger(source, value):
    """Quelle und Wert eines Audio-Ausloesers pruefen: unbekannte Quelle -> beat; der Wert wird auf den Bereich der Quelle begrenzt
    (n = 1 bis 64 ganzzahlig, Schwelle = 1 bis 100 Prozent); fehlt er oder ist er ungueltig, gilt der Vorgabewert der Quelle."""
    text = str(source or "").strip().lower()
    src = text if text in CUE_AUDIO_SOURCES else "beat"
    try:
        number = float(value)
        if number != number or number in (float("inf"), float("-inf")):
            raise ValueError
    except (TypeError, ValueError):
        number = CUE_AUDIO_DEFAULT_COUNT if src in CUE_AUDIO_COUNT_SOURCES else CUE_AUDIO_DEFAULT_LEVEL
    if src in CUE_AUDIO_COUNT_SOURCES:
        return src, float(max(1, min(64, int(round(number)))))
    return src, float(max(1.0, min(100.0, round(number, 1))))
