# Copyright (C) 2026 Samuel Zenker
# SPDX-License-Identifier: GPL-3.0-or-later
"""
midi_engine.py
MIDI-Ein- und -Ausgang (Controller, Keyboards, Pads, DAW): Eine MIDI-Nachricht (Taste, Regler, Programmwechsel ...) loest einen Befehl der Befehlszeile aus - wie die eigene
Tastaturbelegung, nur mit Reglern dazu - und OpenCue kann selbst MIDI senden (Befehl `Midi ...`).

Die Belegung gehoert dem Programm (App-Config `midi`, nicht der Show). Sie wird in `state.midi` gehalten und hier bereinigt (`normalize_config`):

    {"enabled": bool, "output": "<Anschluss-Kennung oder leer = automatisch>", "ignore": [nicht benutzte Geraete], "clock": bool (Tempo aus dem MIDI-Takt), "mtc": bool (Timecode aus MIDI Timecode), "bindings": [Eintrag, ...]}

    Eintrag: {id, enabled, type, channel, number, device, device_name, mode, command, command_off, run, log, min, max, invert, pickup, curve, hold_ms, step, encoding, feedback, fb_on, fb_off}
    type     "note" | "cc" | "pc" | "pitch" | "aftertouch" | "pressure" | "start" | "stop" | "continue" (Transport der Musiksoftware) ("" = noch kein Signal festgelegt: der Eintrag tut nichts)
    channel  0 = jeder Kanal, 1-16
    number   Noten- / Controller- / Programm-Nummer 0-127 (pitch: egal)
    device   "" = jedes Geraet, sonst die Kennung eines Anschlusses (Name ohne die Nummer, die Windows anhaengt)
    mode     trigger  - Taste: beim Druecken laeuft `command`
             toggle   - Taste: abwechselnd `command` und `command_off` (leer = beide Male `command`)
             hold     - Taste: beim Druecken `command`, beim Loslassen `command_off`
             fader    - Regler: `command` mit {value} (min..max, invertierbar); Wert nur bei Aenderung, hoechstens ~40 mal pro Sekunde.
                        pickup: der Regler greift erst, wenn er den aktuellen Wert des Ziels erreicht / durchquert hat (kein Sprung; Ziele, deren Wert bekannt ist: Master, Fader)
             relative - Endlos-Drehgeber: `command` mit {delta} (immer mit Vorzeichen, mal `step`); encoding twos | signed | offset
             double   - Taste: der Befehl laeuft erst beim ZWEITEN Druecken innerhalb von 0,4 s
             long     - Taste: der Befehl laeuft, wenn sie `hold_ms` Millisekunden gehalten wird (Loslassen vorher bricht ab)
    curve    linear | square (langsam anfangen) | sqrt (schnell anfangen): Kennlinie eines Reglers (vor Von / Bis)
    Rueckmeldung (feedback): signal blackout | master | selection | cue_active | timecode_running | cuelist_fader -> wird als Note / Controller / Pitch-Bend GLEICHER Nummer an den
             Ausgang gesendet, der so heisst wie das Geraet des Eintrags (sonst an den gewaehlten Ausgang): LED an Pads (fb_on / fb_off = Anschlagstaerke, bei RGB-Pads die Farbe)
             und Motorfader (Wert 0-100 % -> 0-127). Wird nur gesendet, wenn sich der Wert aendert.
    Platzhalter im Befehl: {value} {raw} {velocity} {note} {number} {channel} {delta}

Zeit und Takt von der Musiksoftware (Einstellungen -> MIDI), beide nur bei passendem Format UND tatsaechlich eintreffenden Daten:
    mtc    - MIDI Timecode (Quarter-Frame-Nachrichten, dazu die Full-Frame-Nachricht beim Springen): wird der globale Timecode von aussen gefuehrt (`MtcDecoder`)
    clock  - MIDI-Takt (24 Impulse pro Viertelnote): gleichmaessiger Takt im Bereich 30-300 BPM setzt das Tempo (`BPM <zahl>`)
    msc    - MIDI Show Control (System Exclusive, Geraete-Kennung `msc_device`, 127 = alle): GO / STOP / RESUME / ALL_OFF / RESTORE steuern die Cue-Listen (`parse_msc`, `msc_command`)
Senden (OpenCue als Zeitgeber): mtc_out - der globale Timecode als MIDI Timecode (Quarter Frames + Full Frame bei Spruengen, Bildrate mtc_fps), clock_out - Start / Stop und MIDI-Takt
im Tempo des Audio-Panels, solange der Timecode laeuft. Beides in einem eigenen Thread mit genauer Zeitsteuerung (`_out_loop`); der Befehl `Midi MSC ...` sendet Show-Control-Nachrichten.

Die Anschluesse werden NUR geoeffnet, solange sie gebraucht werden (ein aktiver Eintrag, der Monitor oder das Einlernen): ein MIDI-Geraet kann unter Windows meist nur EIN
Programm lesen - OpenCue haelt es nicht unnoetig fest. Eine Abfrage alle 2 s findet neu angesteckte Geraete.
Alles Zuordnen und Ausloesen laeuft im asyncio-Thread des Servers (die rtmidi-Funktion gibt die Nachricht nur dorthin weiter); `handle()` ist ohne Hardware testbar.
"""
from __future__ import annotations

import asyncio
import collections
import logging
import re
import threading
import time
import uuid
from typing import Any, Awaitable, Callable, Deque, Dict, List, Optional, Tuple

logger = logging.getLogger("opencue.midi")

try:                                                            # python-rtmidi (Windows: WinMM)
    import rtmidi                                               # type: ignore
    _IMPORT_ERROR = ""
except Exception as exc:                                        # pragma: no cover - nur ohne Bibliothek
    rtmidi = None
    _IMPORT_ERROR = f"{type(exc).__name__}: {exc}"

MAX_BINDINGS = 500
MAX_COMMAND_LENGTH = 1000
TRANSPORT = ("start", "stop", "continue")                          # Start / Stop / Continue der Musiksoftware (kein Kanal, keine Nummer)
TYPES = ("note", "cc", "pc", "pitch", "aftertouch", "pressure") + TRANSPORT
MODES = ("trigger", "toggle", "hold", "fader", "relative", "double", "long")
CURVES = ("linear", "square", "sqrt")
CONTINUOUS_ONLY = ("pitch", "aftertouch", "pressure")             # keine Tasten: nur als Regler
FEEDBACK_SIGNALS = ("blackout", "master", "selection", "cue_active", "timecode_running", "cuelist_fader")
FEEDBACK_BOOL = ("blackout", "selection", "cue_active", "timecode_running")
DOUBLE_S = 0.4                                                  # Zeitfenster fuer den zweiten Druck
MSC_COMMANDS = {0x01: "GO", 0x02: "STOP", 0x03: "RESUME", 0x04: "TIMED_GO", 0x05: "LOAD", 0x06: "SET", 0x07: "FIRE", 0x08: "ALL_OFF", 0x09: "RESTORE", 0x0A: "RESET", 0x0B: "GO_OFF"}
ENCODINGS = ("twos", "signed", "offset")
CONTINUOUS_GAP_S = 0.02                                         # zwischen zwei Ausfuehrungen eines Reglers (Zusammenfassen, ~40 Hz)
POLL_S = 2.0
WATCH_TTL_S = 15.0                                              # Monitor ohne Lebenszeichen des Fensters: geht von selbst aus
LEARN_TTL_S = 40.0                                              # Einlernen ohne Signal: endet von selbst
OUT_IDLE_S = 20.0                                               # der Ausgang wird nach so langer Ruhe wieder freigegeben
MONITOR_FLUSH_S = 0.1
MONITOR_BATCH = 40
SYNTH_HINT = "microsoft gs wavetable"                           # der eingebaute Windows-Synthesizer: nur Notausgang, wenn sonst nichts da ist
NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
_PORT_NUMBER = re.compile(r"\s+\d+$")
_DEVICE_OK = re.compile(r"^[^\x00-\x1f]{1,160}$")


def note_name(number: int) -> str:
    """60 -> "C4" (mittleres C = C4)."""
    return f"{NOTE_NAMES[number % 12]}{number // 12 - 1}"


def port_id(name: str) -> str:
    """Kennung eines Anschlusses: sein Name ohne die Nummer, die Windows hinten anhaengt ("Keystation 61 1" -> "Keystation 61")."""
    return _PORT_NUMBER.sub("", str(name or "")).strip()


def default_config() -> Dict[str, Any]:
    return {"enabled": True, "output": "", "ignore": [], "clock": False, "mtc": False, "msc": False, "msc_device": 127, "mtc_out": False, "mtc_fps": 1, "clock_out": False, "bindings": []}


def _num(value: Any, default: float, low: float, high: float) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return default
    if result != result:                                        # NaN
        return default
    return max(low, min(high, result))


def normalize_config(raw: Any) -> Dict[str, Any]:
    """Bereinigt die Belegung vom Client: nur bekannte Felder, begrenzte Laengen und Werte, eindeutige Ids. Unbrauchbares wird weggelassen."""
    out = default_config()
    if not isinstance(raw, dict):
        return out
    out["enabled"] = raw.get("enabled", True) is not False
    output = str(raw.get("output", "") or "").strip()
    out["output"] = output if _DEVICE_OK.match(output) else ""
    out["clock"] = raw.get("clock", False) is True
    out["mtc"] = raw.get("mtc", False) is True
    out["msc"] = raw.get("msc", False) is True
    out["msc_device"] = int(_num(raw.get("msc_device", 127), 127, 0, 127))
    out["mtc_out"] = raw.get("mtc_out", False) is True
    out["mtc_fps"] = int(_num(raw.get("mtc_fps", 1), 1, 0, 3))
    out["clock_out"] = raw.get("clock_out", False) is True
    ignore = raw.get("ignore")                                  # Geraete, die OpenCue NICHT benutzen soll (Einstellungen -> MIDI); alle anderen werden benutzt
    out["ignore"] = list(dict.fromkeys(str(i).strip() for i in (ignore if isinstance(ignore, list) else [])[:100] if _DEVICE_OK.match(str(i).strip())))
    items = raw.get("bindings")
    seen = set()
    for item in (items if isinstance(items, list) else [])[:MAX_BINDINGS]:
        if not isinstance(item, dict):
            continue
        kind = str(item.get("type", "")).strip().lower()
        if kind not in TYPES:
            kind = ""
        mode = str(item.get("mode", "trigger")).strip().lower()
        if mode not in MODES:
            mode = "trigger"
        if (kind == "pc" or kind in TRANSPORT) and mode in ("fader", "relative", "hold"):
            mode = "trigger"
        if kind in CONTINUOUS_ONLY:
            mode = "fader"
        if mode == "relative" and kind != "cc":
            mode = "fader" if kind in ("note",) else "trigger"
        if mode == "long" and kind not in ("note", "cc"):
            mode = "trigger"
        curve = str(item.get("curve", "linear")).strip().lower()
        if curve not in CURVES:
            curve = "linear"
        feedback = str(item.get("feedback", "") or "").strip().lower()
        if feedback not in FEEDBACK_SIGNALS or (kind and kind not in ("note", "cc", "pitch")):        # (ein noch leeres Signal darf die Rueckmeldung schon haben: Vorlagen)
            feedback = ""
        device = str(item.get("device", "") or "").strip()
        if not _DEVICE_OK.match(device):
            device = ""
        encoding = str(item.get("encoding", "twos")).strip().lower()
        if encoding not in ENCODINGS:
            encoding = "twos"
        key = str(item.get("id", "")).strip()[:40]
        if not key or key in seen:
            key = uuid.uuid4().hex[:12]
        seen.add(key)
        out["bindings"].append({
            "id": key,
            "enabled": item.get("enabled", True) is not False,
            "type": kind,
            "channel": int(_num(item.get("channel", 0), 0, 0, 16)),
            "number": int(_num(item.get("number", 0), 0, 0, 127)),
            "device": device,
            "device_name": " ".join(str(item.get("device_name", "") or "").split())[:120] if device else "",
            "mode": mode,
            "command": " ".join(str(item.get("command", "") or "").split())[:MAX_COMMAND_LENGTH],
            "command_off": " ".join(str(item.get("command_off", "") or "").split())[:MAX_COMMAND_LENGTH],
            "run": item.get("run", True) is not False,
            "log": item.get("log", True) is not False,
            "min": _num(item.get("min", 0), 0.0, -100000.0, 100000.0),
            "max": _num(item.get("max", 100), 100.0, -100000.0, 100000.0),
            "invert": item.get("invert", False) is True,
            "pickup": item.get("pickup", False) is True,
            "step": _num(item.get("step", 1), 1.0, -1000.0, 1000.0),
            "encoding": encoding,
            "curve": curve,
            "hold_ms": int(_num(item.get("hold_ms", 600), 600, 200, 3000)),
            "feedback": feedback,
            "fb_on": int(_num(item.get("fb_on", 127), 127, 0, 127)),
            "fb_off": int(_num(item.get("fb_off", 0), 0, 0, 127)),
        })
    return out


# ------------------------------------------------------------------------------------------------ Nachrichten
def parse(message: List[int]) -> Optional[Dict[str, Any]]:
    """Rohbytes -> {type, channel, number, value, raw}; None bei Unbrauchbarem / Systemnachrichten.
    type: note_on | note_off | cc | pc | pitch | aftertouch | pressure. channel 1-16. Eine Note-On mit Anschlagstaerke 0 ist ein Note-Off.
    pitch: value 0-16383 (Mitte 8192). Alle anderen: number und value 0-127 (pc: nur number)."""
    if not message:
        return None
    status = int(message[0])
    if status in (0xFA, 0xFB, 0xFC):                            # Transport der Musiksoftware
        name = {0xFA: "start", 0xFB: "continue", 0xFC: "stop"}[status]
        return {"type": name, "channel": 0, "number": 0, "value": 127, "raw": 127}
    if status < 0x80 or status >= 0xF0:
        return None
    kind = status & 0xF0
    channel = (status & 0x0F) + 1
    d1 = int(message[1]) & 0x7F if len(message) > 1 else 0
    d2 = int(message[2]) & 0x7F if len(message) > 2 else 0
    if kind == 0x90:
        return {"type": "note_on" if d2 > 0 else "note_off", "channel": channel, "number": d1, "value": d2, "raw": d2}
    if kind == 0x80:
        return {"type": "note_off", "channel": channel, "number": d1, "value": d2, "raw": d2}
    if kind == 0xB0:
        return {"type": "cc", "channel": channel, "number": d1, "value": d2, "raw": d2}
    if kind == 0xC0:
        return {"type": "pc", "channel": channel, "number": d1, "value": 127, "raw": 127}
    if kind == 0xE0:
        bend = d1 | (d2 << 7)
        return {"type": "pitch", "channel": channel, "number": 0, "value": bend, "raw": bend}
    if kind == 0xA0:
        return {"type": "aftertouch", "channel": channel, "number": d1, "value": d2, "raw": d2}
    if kind == 0xD0:
        return {"type": "pressure", "channel": channel, "number": 0, "value": d1, "raw": d1}
    return None


def describe(event: Dict[str, Any]) -> str:
    """Kurztext fuer den Monitor ("Note On C4 (60) · 100")."""
    kind = event["type"]
    if kind in TRANSPORT:
        return {"start": "Start", "stop": "Stop", "continue": "Continue"}[kind]
    if kind in ("note_on", "note_off"):
        return f"{'Note On' if kind == 'note_on' else 'Note Off'} {note_name(event['number'])} ({event['number']}) · {event['value']}"
    if kind == "cc":
        return f"CC {event['number']} · {event['value']}"
    if kind == "pc":
        return f"Program {event['number']}"
    if kind == "pitch":
        return f"Pitch Bend · {event['value']}"
    if kind == "aftertouch":
        return f"Aftertouch {note_name(event['number'])} · {event['value']}"
    return f"Pressure · {event['value']}"


def _fmt(value: float) -> str:
    if abs(value - round(value)) < 1e-9:
        return str(int(round(value)))
    return f"{value:.2f}".rstrip("0").rstrip(".")


def render(template: str, context: Dict[str, Any]) -> str:
    """{value} {raw} {velocity} {note} {number} {channel} {delta} im Befehl ersetzen."""
    text = template
    for name, value in context.items():
        text = text.replace("{" + name + "}", str(value))
    return text


def relative_delta(raw: int, encoding: str) -> int:
    """Wert eines Endlos-Drehgebers -> Schritte (+ rechts / - links)."""
    if encoding == "offset":
        return raw - 64
    if encoding == "signed":
        return raw if raw < 64 else (0 if raw == 64 else -(raw - 64))
    return raw if raw < 64 else raw - 128                       # twos


def is_blocked(command: str) -> bool:
    """Per MIDI nie: Loeschen und Ueberschreiben (eine versehentlich getroffene Taste darf keine Daten vernichten)."""
    for part in str(command or "").split(";"):
        words = part.lower().split()
        if words and (words[0] == "delete" or "overwrite" in words):
            return True
    return False


MTC_RATES = {0: (24.0, 24), 1: (25.0, 25), 2: (30000.0 / 1001.0, 30), 3: (30.0, 30)}      # Rate-Code -> (Bilder pro Sekunde, Bilder pro Zaehlsekunde)
MTC_LOCK_GROUPS = 3                                                                       # so viele lueckenlose, zeitlich passende Gruppen (je 2 Bilder), bevor der Timecode uebernommen wird


class MtcDecoder:
    """MIDI Timecode: acht Quarter-Frame-Nachrichten (0xF1 + Datenbyte) ergeben einen Zeitwert (Bilder, Sekunden, Minuten, Stunden + Bildrate), zwei Bilder lang.
    Ein Zeitwert zaehlt erst, wenn er plausibel ist (Bilder < Bildrate, Sekunden / Minuten < 60, Stunden < 24), die Stuecke lueckenlos in Reihenfolge 0..7 kamen
    und MTC_LOCK_GROUPS Gruppen hintereinander zeitlich zueinander passen (je 2 Bilder weiter, in echter Zeit etwa so schnell). Eine Luecke oder Rueckwaertslauf
    beginnt von vorn. `feed()` ist reine Rechnung (ohne Uhr: die Zeit kommt als Parameter) und damit testbar."""

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.pieces = [0] * 8
        self.mask = 0                                           # welche Stuecke der laufenden Gruppe da sind
        self.expect: Optional[int] = None
        self.count = 0                                          # zusammenpassende Gruppen in Folge
        self.last_ms = 0.0
        self.last_at = 0.0
        self.fps = 0.0

    def feed(self, data: int, now: float) -> Optional[Dict[str, Any]]:
        """Ein Datenbyte einer Quarter-Frame-Nachricht. Gibt {"ms", "fps", "first"} zurueck, sobald ein vollstaendiger Zeitwert im gesperrten (passenden) Lauf vorliegt."""
        if not isinstance(data, int) or data < 0 or data > 0x7F:
            return None
        piece, value = (data >> 4) & 7, data & 0x0F
        if self.expect is None:
            if piece != 0:
                return None                                     # erst am Anfang einer Gruppe einsteigen
        elif piece != self.expect:
            self.reset()                                        # Luecke / Rueckwaertslauf / fremdes Signal: neu beginnen
            if piece != 0:
                return None
        self.pieces[piece] = value
        self.mask = (self.mask | (1 << piece)) if piece else 1
        self.expect = (piece + 1) % 8
        if piece != 7 or self.mask != 0xFF:
            return None
        self.mask = 0
        p = self.pieces
        frames, seconds, minutes, hours = p[0] | ((p[1] & 1) << 4), p[2] | ((p[3] & 3) << 4), p[4] | ((p[5] & 3) << 4), p[6] | ((p[7] & 1) << 4)
        fps, nominal = MTC_RATES[(p[7] >> 1) & 3]
        if frames >= nominal or seconds > 59 or minutes > 59 or hours > 23:
            self.count = 0
            return None
        frame_ms = 1000.0 / fps
        ms = ((hours * 60 + minutes) * 60 + seconds) * 1000.0 + (frames + 2) * frame_ms         # +2 Bilder: der Wert gilt fuer den Beginn der Gruppe
        step = ms - self.last_ms
        real = now - self.last_at
        fits = self.count > 0 and fps == self.fps and 0 < step <= 6 * frame_ms and real >= 0.5 * (2 * frame_ms / 1000.0) and real <= 20.0
        self.count = self.count + 1 if fits else 1
        self.last_ms, self.last_at, self.fps = ms, now, fps
        if self.count < MTC_LOCK_GROUPS:
            return None
        return {"ms": ms, "fps": fps, "first": self.count == MTC_LOCK_GROUPS}


def parse_full_frame(message: List[int]) -> Optional[Dict[str, Any]]:
    """MTC Full Frame (System Exclusive F0 7F <Geraet> 01 01 hh mm ss ff F7): die Musiksoftware springt an eine Stelle, ohne zu laufen. -> {"ms", "fps"} oder None."""
    if len(message) < 10 or message[0] != 0xF0 or message[1] != 0x7F or message[3] != 0x01 or message[4] != 0x01:
        return None
    fps, nominal = MTC_RATES[(message[5] >> 5) & 3]
    hours, minutes, seconds, frames = message[5] & 0x1F, message[6], message[7], message[8]
    if frames >= nominal or seconds > 59 or minutes > 59 or hours > 23:
        return None
    return {"ms": ((hours * 60 + minutes) * 60 + seconds) * 1000.0 + frames * 1000.0 / fps, "fps": fps}


def parse_msc(message: List[int]) -> Optional[Dict[str, Any]]:
    """MIDI Show Control (System Exclusive F0 7F <Geraet> 02 <Format> <Befehl> [Daten] F7) -> {"device", "command", "cue", "list"} oder None.
    Nur Beleuchtungs-Formate (0x01 - 0x1F, 0x7F = alle). Cue und Liste stehen als ASCII-Ziffern ("1.5"), getrennt durch 0x00."""
    if len(message) < 7 or message[0] != 0xF0 or message[1] != 0x7F or message[3] != 0x02:
        return None
    fmt, code = message[4], message[5]
    if not (0x01 <= fmt <= 0x1F or fmt == 0x7F) or code not in MSC_COMMANDS:
        return None
    body = message[6:-1] if message[-1] == 0xF7 else message[6:]
    parts: List[str] = []
    current: List[int] = []
    for byte in body:
        if byte == 0x00:
            parts.append("".join(chr(c) for c in current))
            current = []
        elif 0x20 <= byte < 0x7F:
            current.append(byte)
    parts.append("".join(chr(c) for c in current))
    cue = parts[0] if parts and re.fullmatch(r"\d+(\.\d+)?", parts[0]) else ""
    cue_list = parts[1] if len(parts) > 1 and re.fullmatch(r"\d+", parts[1]) else ""
    return {"device": message[2], "command": MSC_COMMANDS[code], "cue": cue, "list": cue_list}


def msc_command(msc: Dict[str, Any]) -> str:
    """MSC-Befehl -> Befehl der Befehlszeile ("" = nichts zu tun)."""
    command, cue, cue_list = msc["command"], msc.get("cue", ""), msc.get("list", "")
    head = f"Cuelist {cue_list} " if cue_list else ""
    if command in ("GO", "TIMED_GO"):
        return head + ("Go Cue " + cue if cue else "Go")
    if command == "STOP":
        return head + "Pause"
    if command == "RESUME":
        return head + "Resume"
    if command == "ALL_OFF":
        return "Blackout On"
    if command == "RESTORE":
        return "Blackout Off"
    return ""


def build_msc(command: str, cue: str = "", cue_list: str = "", device: int = 127) -> List[int]:
    """Show-Control-Nachricht (Beleuchtung allgemein, Format 0x01) zum Senden: GO / STOP / RESUME / ALL_OFF / RESTORE ..."""
    code = next((c for c, name in MSC_COMMANDS.items() if name == command.upper()), None)
    if code is None:
        raise ValueError(command)
    data: List[int] = []
    if cue:
        data += [ord(ch) for ch in cue]
        if cue_list:
            data += [0x00] + [ord(ch) for ch in cue_list]
    return [0xF0, 0x7F, device & 0x7F, 0x02, 0x01, code] + data + [0xF7]


Fire = Callable[[Dict[str, Any], str], Awaitable[None]]
Emit = Callable[[str, Dict[str, Any]], Awaitable[None]]


class MidiEngine:
    def __init__(self) -> None:
        self.config: Dict[str, Any] = default_config()
        self.available: bool = rtmidi is not None
        self.error: str = _IMPORT_ERROR
        self.on_fire: Optional[Fire] = None                     # async (Eintrag, Befehl)
        self.on_mtc: Optional[Callable[[str, Dict[str, Any]], Awaitable[None]]] = None       # async (Art "fix" | "locate" | "lost", Daten): der Server fuehrt damit den globalen Timecode
        self.on_emit: Optional[Emit] = None                     # async (Art, Daten) -> an die Konsolen-Fenster (Monitor, Einlernen, Status)
        self.value_of: Optional[Callable[[str], Optional[float]]] = None      # Befehlsvorlage -> aktueller Wert des Ziels in den Einheiten von {value} (None = unbekannt); fuer "pickup"
        self.on_msc: Optional[Callable[[str, Dict[str, Any]], Awaitable[None]]] = None      # async (Befehl der Befehlszeile, MSC-Daten): der Server fuehrt ihn aus
        self.timecode_source: Optional[Callable[[], Tuple[bool, float]]] = None             # () -> (laeuft, Position in ms) des globalen Timecodes (zum Senden von MTC)
        self.bpm_source: Optional[Callable[[], float]] = None                               # () -> Tempo (BPM) fuer den gesendeten MIDI-Takt
        self.watching = False                                   # Monitor offen: alle Anschluesse hoeren, Nachrichten melden
        self.learning = False                                   # naechstes Signal einlernen
        self.cue_wanted = False                                 # ein Cue hat den Ausloeser "midi": Anschluesse offen halten und die Ereignisse fuer den Server sammeln
        self._cue_events: Deque[Dict[str, Any]] = collections.deque(maxlen=512)
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._lock = threading.RLock()
        self._inputs: Dict[str, Dict[str, Any]] = {}            # Kennung -> {midi, name, index}
        self._errors: Dict[str, str] = {}                       # Kennung -> Fehlertext des letzten Oeffnens
        self._probe_in: Any = None
        self._probe_out: Any = None
        self._outs: Dict[str, Any] = {}                         # Kennung -> offener Ausgang
        self._out_used: Dict[str, float] = {}
        self._out_cache: List[str] = []
        self._out_cache_at = 0.0
        self._out_cfg = ""
        self._out_thread: Optional[threading.Thread] = None
        self._fb_reset = True                                   # Rueckmeldung komplett neu senden (nach Aenderung der Belegung / der Geraete)
        self._poll_thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._wake = threading.Event()
        self._rt: Dict[str, Dict[str, Any]] = {}               # Eintrags-Id -> Laufzeit (down, toggle, last_cmd)
        self._work: "collections.OrderedDict[Any, Tuple[Dict[str, Any], str]]" = collections.OrderedDict()
        self._work_event: Optional[asyncio.Event] = None
        self._worker: Optional["asyncio.Task[None]"] = None
        self._seq = 0
        self._monitor: Deque[Dict[str, Any]] = collections.deque(maxlen=200)
        self._hits: set = set()
        self._monitor_scheduled = False
        self._ports_cache: Tuple[List[str], List[str]] = ([], [])
        self._watch_until = 0.0
        self._learn_until = 0.0
        self._ticks: Deque[float] = collections.deque(maxlen=49)            # Zeitpunkte der letzten MIDI-Takt-Impulse (24 pro Viertel)
        self.clock_bpm = 0.0                                                # zuletzt gemessenes Tempo (0 = kein Takt)
        self._clock_seen = 0.0
        self._clock_sent = 0.0
        self._clock_sent_at = 0.0
        self._mtc = MtcDecoder()
        self.mtc_locked = False
        self.mtc_ms = 0.0
        self.mtc_fps = 0.0
        self._mtc_seen = 0.0
        self._mtc_watching = False

    # ------------------------------------------------------------------ Start / Ende
    def attach(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop
        self._work_event = asyncio.Event()
        if self._worker is None or self._worker.done():
            self._worker = loop.create_task(self._work_loop())
        if self.available and (self._poll_thread is None or not self._poll_thread.is_alive()):
            self._stop.clear()
            self._poll_thread = threading.Thread(target=self._poll, name="opencue-midi", daemon=True)
            self._poll_thread.start()

    def shutdown(self) -> None:
        self._stop.set()
        self._wake.set()
        with self._lock:
            self._close_inputs(set())
            self._close_output()
        if self._out_thread is not None:
            self._out_thread.join(timeout=1.0)
        if self._worker is not None:
            self._worker.cancel()

    def configure(self, config: Any) -> None:
        was_mtc = bool(self.config.get("mtc")) and bool(self.config.get("enabled", True))
        self.config = normalize_config(config)
        if was_mtc and not (self.config.get("mtc") and self.config.get("enabled", True)) and self.mtc_locked:
            self._mtc_lost()
        keep = {b["id"] for b in self.config["bindings"]}
        for key in [k for k in self._rt if k not in keep]:
            self._rt.pop(key, None)
        with self._lock:
            if self._out_cfg != self.config["output"]:
                self._out_cfg = self.config["output"]
                self._close_output()
        self._fb_reset = True
        self.reconcile()
        self.ensure_out_thread()

    def set_watching(self, on: bool) -> None:
        """Monitor an/aus. Das Fenster meldet sich alle paar Sekunden erneut ("Lebenszeichen"); bleibt es aus (Seite geschlossen), geht der Monitor von selbst aus."""
        self.watching = bool(on)
        self._watch_until = time.monotonic() + WATCH_TTL_S
        if not on:
            self._monitor.clear()
            self._hits.clear()
        self.reconcile()

    def set_cue_triggers(self, wanted: bool) -> None:
        """Der Server meldet, ob irgendein Cue den Ausloeser "midi" hat (app/midi_vars.py). Aendert sich das, werden die Anschluesse neu abgeglichen."""
        wanted = bool(wanted)
        if wanted == self.cue_wanted:
            return
        self.cue_wanted = wanted
        if not wanted:
            self._cue_events.clear()
        self.reconcile()

    def pop_cue_events(self) -> List[Dict[str, Any]]:
        """Die seit dem letzten Aufruf eingetroffenen Ereignisse (note_on / cc / pc) fuer die MIDI-Cue-Ausloeser."""
        events: List[Dict[str, Any]] = []
        while self._cue_events:
            try:
                events.append(self._cue_events.popleft())
            except IndexError:
                break
        return events

    def set_learning(self, on: bool) -> None:
        self.learning = bool(on)
        self._learn_until = time.monotonic() + LEARN_TTL_S
        self.reconcile()

    # ------------------------------------------------------------------ Anschluesse
    def _list(self, kind: str) -> List[str]:
        """Namen der Eingaenge / Ausgaenge. Leer ohne Bibliothek oder bei einem Fehler."""
        if rtmidi is None:
            return []
        with self._lock:
            try:
                if kind == "in":
                    if self._probe_in is None:
                        self._probe_in = rtmidi.MidiIn()
                    return list(self._probe_in.get_ports())
                if self._probe_out is None:
                    self._probe_out = rtmidi.MidiOut()
                return list(self._probe_out.get_ports())
            except Exception as exc:
                self.error = f"{type(exc).__name__}: {exc}"
                logger.debug("MIDI-Anschluesse nicht lesbar", exc_info=True)
                return []

    def list_inputs(self) -> List[Dict[str, str]]:
        names = self._list("in")
        return [{"id": port_id(n), "name": port_id(n)} for n in names]

    def list_outputs(self) -> List[Dict[str, str]]:
        names = self._list("out")
        return [{"id": port_id(n), "name": port_id(n)} for n in names]

    def _wanted_inputs(self, available: List[str]) -> set:
        if not self.config.get("enabled", True):
            return set()
        ids = {port_id(n) for n in available} - set(self.config.get("ignore", []))
        if self.watching or self.learning or self.cue_wanted or self.config.get("clock") or self.config.get("mtc") or self.config.get("msc"):
            return ids
        wanted = set()
        for b in self.config["bindings"]:
            if not (b["enabled"] and b["type"] and b["command"]):
                continue
            if not b["device"]:
                return ids
            if b["device"] in ids:
                wanted.add(b["device"])
        return wanted

    def reconcile(self) -> None:
        """Anschluesse oeffnen / schliessen, so dass genau die offen sind, die gebraucht werden."""
        if rtmidi is None:
            return
        with self._lock:
            names = self._list("in")
            self._ports_cache = (names, self._ports_cache[1])
            wanted = self._wanted_inputs(names)
            clock, mtc, msc = bool(self.config.get("clock")), bool(self.config.get("mtc")), bool(self.config.get("msc"))
            same = lambda i: (self._inputs.get(i, {}).get("clock", clock), self._inputs.get(i, {}).get("mtc", mtc), self._inputs.get(i, {}).get("msc", msc)) == (clock, mtc, msc)
            self._close_inputs({i for i in wanted if same(i)})      # Takt-/Timecode-/Show-Control-Einstellung geaendert: Anschluss neu oeffnen
            for index, name in enumerate(names):
                ident = port_id(name)
                if ident not in wanted or ident in self._inputs:
                    continue
                try:
                    midi_in = rtmidi.MidiIn()
                    midi_in.ignore_types(sysex=not (mtc or msc), timing=not (clock or mtc), active_sense=True)
                    midi_in.open_port(index)
                    midi_in.set_callback(self._make_callback(ident, clock, mtc, msc))
                    self._inputs[ident] = {"midi": midi_in, "name": ident, "index": index, "clock": clock, "mtc": mtc, "msc": msc}
                    self._errors.pop(ident, None)
                    logger.info("MIDI-Eingang geoeffnet: %s", ident)
                except Exception as exc:
                    message = f"{type(exc).__name__}: {exc}"
                    if self._errors.get(ident) != message:       # nur einmal melden (die Abfrage versucht es alle 2 s erneut)
                        logger.warning("OC-3301 MIDI-Eingang '%s' nicht zu oeffnen: %s", ident, exc)
                    self._errors[ident] = message

    def _close_inputs(self, keep: set) -> None:
        for ident in [i for i in self._inputs if i not in keep]:
            item = self._inputs.pop(ident)
            try:
                item["midi"].cancel_callback()
                item["midi"].close_port()
            except Exception:
                logger.debug("MIDI-Eingang schliessen", exc_info=True)
            logger.info("MIDI-Eingang geschlossen: %s", ident)

    def tick(self, now: float) -> None:
        """Ein MIDI-Takt-Impuls (24 pro Viertelnote) zur Zeit `now` (Sekunden): aus den letzten Abstaenden ergibt sich das Tempo. Laeuft im MIDI-Thread (nur Rechnen); das Ergebnis geht an den Ereignis-Thread."""
        if self._ticks and now - self._ticks[-1] > 0.5:                          # Pause im Takt (Musiksoftware gestoppt): neu messen
            self._ticks.clear()
        self._ticks.append(now)
        self._clock_seen = now
        if len(self._ticks) < 25:
            return
        span = self._ticks[-1] - self._ticks[0]
        if span <= 0:
            return
        stamps = list(self._ticks)
        gaps = [b - a for a, b in zip(stamps, stamps[1:])]
        mean = span / len(gaps)
        deviation = (sum((g - mean) ** 2 for g in gaps) / len(gaps)) ** 0.5
        if deviation > 0.35 * mean:                                         # kein gleichmaessiger Takt (Rauschen, fremde Nachrichten): nichts uebernehmen
            self.clock_bpm = 0.0
            return
        bpm = 60.0 / (mean * 24.0)
        self.clock_bpm = bpm
        if 30.0 <= bpm <= 300.0 and (abs(bpm - self._clock_sent) >= 0.4 or (now - self._clock_sent_at > 5.0 and abs(bpm - self._clock_sent) >= 0.1)) and now - self._clock_sent_at >= 0.4:
            self._clock_sent, self._clock_sent_at = bpm, now
            loop = self._loop
            if loop is not None and not loop.is_closed():
                loop.call_soon_threadsafe(self._clock_command, bpm)

    def _clock_command(self, bpm: float) -> None:
        """Das gemessene Tempo wird wie ein getippter Befehl `BPM <zahl>` ausgefuehrt (Audio-Panel: festes Tempo), ohne Eintrag im Verlauf."""
        if not self.config.get("enabled", True) or not self.config.get("clock"):
            return
        self._submit({"id": "__clock", "run": True, "log": False}, f"BPM {bpm:.1f}", {}, key="__clock", rendered=True)

    # ---- MIDI Timecode
    def mtc_quarter(self, data: int, now: float) -> None:
        """Ein Quarter-Frame-Datenbyte (im MIDI-Thread): nur Rechnen, ein vollstaendiger plausibler Zeitwert geht an den Ereignis-Thread."""
        fix = self._mtc.feed(data, now)
        if fix is None:
            return
        loop = self._loop
        if loop is not None and not loop.is_closed():
            loop.call_soon_threadsafe(self._mtc_fix, fix, now)

    def _mtc_fix(self, fix: Dict[str, Any], now: float) -> None:
        if not (self.config.get("enabled", True) and self.config.get("mtc")):
            return
        self.mtc_locked, self.mtc_ms, self.mtc_fps, self._mtc_seen = True, fix["ms"], fix["fps"], now
        self._spawn(self._call_mtc("fix", {"ms": fix["ms"], "fps": fix["fps"], "first": fix["first"]}))
        if not self._mtc_watching and self._loop is not None:
            self._mtc_watching = True
            self._loop.call_later(0.5, self._mtc_watch)

    def _mtc_watch(self) -> None:
        """Kommt kein Timecode mehr (Musiksoftware gestoppt, Kabel ab), wird die Fuehrung freigegeben."""
        self._mtc_watching = False
        if not self.mtc_locked:
            return
        if time.perf_counter() - self._mtc_seen > 0.5:
            self._mtc_lost()
        elif self._loop is not None:
            self._mtc_watching = True
            self._loop.call_later(0.25, self._mtc_watch)

    def _mtc_lost(self) -> None:
        self.mtc_locked = False
        self._mtc.reset()
        self._spawn(self._call_mtc("lost", {}))

    def _mtc_locate(self, fix: Dict[str, Any]) -> None:
        if self.config.get("enabled", True) and self.config.get("mtc"):
            self._spawn(self._call_mtc("locate", {"ms": fix["ms"], "fps": fix["fps"]}))

    async def _call_mtc(self, kind: str, payload: Dict[str, Any]) -> None:
        if self.on_mtc is not None:
            try:
                await self.on_mtc(kind, payload)
            except Exception:
                logger.exception("MIDI-Timecode '%s'", kind)

    def _msc_in(self, message: List[int]) -> None:
        """Eine MIDI-Show-Control-Nachricht (im Ereignis-Thread): fuer unsere Geraete-Kennung (oder 127 = alle) wird der Befehl ausgefuehrt."""
        if not (self.config.get("enabled", True) and self.config.get("msc")):
            return
        msc = parse_msc(message)
        if msc is None:
            return
        wanted = int(self.config.get("msc_device", 127))
        if msc["device"] not in (wanted, 127) and wanted != 127:
            return
        command = msc_command(msc)
        if command and self.on_msc is not None:
            self._spawn(self._call_msc(command, msc))

    async def _call_msc(self, command: str, msc: Dict[str, Any]) -> None:
        try:
            await self.on_msc(command, msc)                     # type: ignore[misc]
        except Exception:
            logger.exception("MIDI Show Control '%s'", command)

    def _make_callback(self, ident: str, clock: bool = False, mtc: bool = False, msc: bool = False) -> Callable[[Any, Any], None]:
        def callback(event: Any, _data: Any = None) -> None:
            try:
                message = list(event[0])
            except Exception:
                return
            first = message[0] if message else 0
            if first == 0xF8:                                               # Takt: nur wenn eingeschaltet, nie weiterreichen
                if clock:
                    self.tick(time.perf_counter())
                return
            if first == 0xF1:                                               # MTC Quarter Frame
                if mtc and len(message) >= 2:
                    self.mtc_quarter(int(message[1]), time.perf_counter())
                return
            if first == 0xF0:                                               # System Exclusive: nur MTC-Full-Frame (Springen) und MIDI Show Control
                located = parse_full_frame(message) if mtc else None
                loop = self._loop
                if loop is not None and not loop.is_closed():
                    if located is not None:
                        loop.call_soon_threadsafe(self._mtc_locate, located)
                    elif msc:
                        loop.call_soon_threadsafe(self._msc_in, message)
                return
            loop = self._loop
            if loop is not None and not loop.is_closed():
                loop.call_soon_threadsafe(self._handle_sync, ident, message)
        return callback

    def _poll(self) -> None:
        """Alle 2 s: neu angesteckte / entfernte Geraete erkennen, den Ausgang bei Ruhe freigeben."""
        last_names: Optional[List[str]] = None
        while not self._stop.is_set():
            self._wake.wait(POLL_S)
            self._wake.clear()
            if self._stop.is_set():
                break
            try:
                now = time.monotonic()
                if (self.watching and now > self._watch_until) or (self.learning and now > self._learn_until):
                    self.watching = self.watching and now <= self._watch_until
                    self.learning = self.learning and now <= self._learn_until
                    self.reconcile()
                    self._notify_status()
                names = self._list("in")
                outs = self._list("out")
                self._ports_cache = (names, outs)
                if names != last_names or len(self._inputs) != len(self._wanted_inputs(names)):
                    last_names = names
                    self._fb_reset = True
                    self.reconcile()
                    self._notify_status()
                with self._lock:
                    for ident in [i for i, at in self._out_used.items() if time.monotonic() - at > OUT_IDLE_S]:
                        self._close_output(ident)
            except Exception:
                logger.debug("MIDI-Abfrage", exc_info=True)

    def _notify_status(self) -> None:
        loop = self._loop
        if loop is not None and not loop.is_closed():
            loop.call_soon_threadsafe(lambda: loop.create_task(self._emit("status", self.status())))

    def refresh_ports(self) -> Dict[str, Any]:
        """Anschlussliste jetzt neu lesen und den Status liefern."""
        self._ports_cache = (self._list("in"), self._list("out"))
        return self.status()

    def status(self) -> Dict[str, Any]:
        names_in, names_out = self._ports_cache
        ignored = set(self.config.get("ignore", []))
        inputs = [{"id": port_id(n), "name": port_id(n), "open": port_id(n) in self._inputs, "error": self._errors.get(port_id(n), "") if port_id(n) not in ignored else "",
                   "ignored": port_id(n) in ignored} for n in names_in]
        out_ids = [port_id(n) for n in names_out]
        chosen = self._choose_output(out_ids)
        outputs = [{"id": i, "name": i, "selected": i == chosen} for i in out_ids]
        return {"available": self.available, "error": self.error if not self.available else "", "enabled": bool(self.config.get("enabled", True)),
                "inputs": inputs, "outputs": outputs, "output": chosen, "watching": self.watching, "learning": self.learning,
                "bindings": sum(1 for b in self.config["bindings"] if b["enabled"] and b["type"] and b["command"]),
                "mtc": bool(self.config.get("mtc")), "mtc_locked": bool(self.mtc_locked and time.perf_counter() - self._mtc_seen < 1.0),
                "mtc_ms": round(self.mtc_ms) if self.mtc_locked else 0, "mtc_fps": round(self.mtc_fps, 3) if self.mtc_locked else 0,
                "msc": bool(self.config.get("msc")), "mtc_out": bool(self.config.get("mtc_out")), "clock_out": bool(self.config.get("clock_out")),
                "clock": bool(self.config.get("clock")), "clock_bpm": round(self.clock_bpm, 1) if self.clock_bpm and time.perf_counter() - self._clock_seen < 2.0 else 0.0}

    # ------------------------------------------------------------------ Ausgang
    def _choose_output(self, out_ids: List[str]) -> str:
        wanted = self.config.get("output", "")
        if wanted and wanted in out_ids:
            return wanted
        for ident in out_ids:
            if SYNTH_HINT not in ident.lower():
                return ident
        return out_ids[0] if out_ids else ""

    def _close_output(self, ident: Optional[str] = None) -> None:
        """Einen (oder alle) offenen Ausgaenge schliessen."""
        for key in ([ident] if ident else list(self._outs)):
            handle = self._outs.pop(key, None)
            self._out_used.pop(key, None)
            if handle is not None:
                try:
                    handle.close_port()
                except Exception:
                    logger.debug("MIDI-Ausgang schliessen", exc_info=True)

    def send(self, message: List[int], port: str = "") -> Tuple[bool, str]:
        """Rohbytes an einen Ausgang: `port` (Kennung), sonst der gewaehlte / automatische. (ok, Meldung). Mehrere Ausgaenge bleiben offen; die Liste wird alle 2 s neu gelesen."""
        if rtmidi is None:
            return False, "MIDI is not available (python-rtmidi missing)"
        with self._lock:
            try:
                now = time.monotonic()
                if not self._out_cache or now - self._out_cache_at > 2.0:
                    names = self._list("out")
                    self._ports_cache = (self._ports_cache[0], names)
                    self._out_cache, self._out_cache_at = [port_id(n) for n in names], now
                ids = self._out_cache
                chosen = port if port and port in ids else self._choose_output(ids)
                if not chosen:
                    return False, "No MIDI output available"
                handle = self._outs.get(chosen)
                if handle is None:
                    handle = rtmidi.MidiOut()
                    handle.open_port(ids.index(chosen))
                    self._outs[chosen] = handle
                handle.send_message(list(message))
                self._out_used[chosen] = now
                return True, chosen
            except Exception as exc:
                self._close_output(chosen if "chosen" in locals() and chosen else None)
                self._out_cache_at = 0.0
                return False, f"MIDI output failed: {exc}"

    # ------------------------------------------------------------------ Rueckmeldung (LED an Pads, Motorfader)
    def feedback(self, values: Dict[str, float]) -> int:
        """Zustaende der Konsole an die Geraete zurueckmelden: jeder Eintrag mit `feedback` sendet seine Note / seinen Controller / Pitch-Bend (gleiche Nummer und Kanal wie das Signal)
        an den Ausgang, der wie das Geraet heisst (sonst der gewaehlte). Gesendet wird nur bei einer Aenderung (oder nach `_fb_reset`). Gibt die Zahl der gesendeten Nachrichten zurueck."""
        if not self.config.get("enabled", True):
            return 0
        sent = 0
        reset = self._fb_reset
        for b in self.config["bindings"]:
            signal = b.get("feedback")
            if not (b["enabled"] and signal and signal in values and b["type"] in ("note", "cc", "pitch")):
                continue
            value = values[signal]
            if signal in FEEDBACK_BOOL:
                out = b["fb_on"] if value else b["fb_off"]
            else:
                out = int(round(max(0.0, min(100.0, float(value))) / 100.0 * (16383 if b["type"] == "pitch" else 127)))
            rt = self._runtime(b)
            if rt.get("fb_last") == out and not reset:
                continue
            channel = (b["channel"] or 1) - 1
            if b["type"] == "note":
                message = [0x90 | channel, b["number"], out]
            elif b["type"] == "cc":
                message = [0xB0 | channel, b["number"], out]
            else:
                message = [0xE0 | channel, out & 0x7F, (out >> 7) & 0x7F]
            ok, _info = self.send(message, port=b["device"])
            if ok:
                rt["fb_last"] = out
                sent += 1
        self._fb_reset = False
        return sent

    # ------------------------------------------------------------------ Senden: MIDI Timecode und MIDI-Takt (eigener Thread mit genauer Zeitsteuerung)
    def ensure_out_thread(self) -> None:
        wanted = self.config.get("enabled", True) and (self.config.get("mtc_out") or self.config.get("clock_out")) and self.available
        if wanted and (self._out_thread is None or not self._out_thread.is_alive()):
            self._out_thread = threading.Thread(target=self._out_loop, name="opencue-midi-out", daemon=True)
            self._out_thread.start()

    @staticmethod
    def mtc_pieces(position_ms: float, fps_code: int) -> Tuple[List[int], int]:
        """Die acht Quarter-Frame-Datenbytes fuer die Bildnummer an `position_ms` (und diese Bildnummer)."""
        fps, nominal = MTC_RATES[fps_code]
        frame = int(position_ms / (1000.0 / fps))
        frames = frame % nominal
        seconds_total = frame // nominal
        hours, minutes, seconds = (seconds_total // 3600) % 24, (seconds_total // 60) % 60, seconds_total % 60
        values = [frames & 0xF, (frames >> 4) & 1, seconds & 0xF, (seconds >> 4) & 3, minutes & 0xF, (minutes >> 4) & 3, hours & 0xF, ((hours >> 4) & 1) | (fps_code << 1)]
        return [(i << 4) | v for i, v in enumerate(values)], frame

    @staticmethod
    def full_frame(position_ms: float, fps_code: int) -> List[int]:
        fps, nominal = MTC_RATES[fps_code]
        frame = int(position_ms / (1000.0 / fps))
        seconds_total = frame // nominal
        return [0xF0, 0x7F, 0x7F, 0x01, 0x01, ((fps_code & 3) << 5) | ((seconds_total // 3600) % 24), (seconds_total // 60) % 60, seconds_total % 60, frame % nominal, 0xF7]

    def _out_loop(self) -> None:
        winmm = None
        try:                                                    # Windows: 1-ms-Zeitgeber, sonst waeren die Abstaende ~15 ms grob
            import ctypes
            winmm = ctypes.windll.winmm                         # type: ignore[attr-defined]
            winmm.timeBeginPeriod(1)
        except Exception:
            winmm = None
        send = lambda message: self.send(message)
        last_run = False
        last_pos = 0.0
        qf = 0
        qf_next = 0.0
        pieces: List[int] = []
        prev_frame: Optional[int] = None
        clock_next = 0.0
        try:
            while not self._stop.is_set():
                cfg = self.config
                want_mtc = bool(cfg.get("enabled", True) and cfg.get("mtc_out"))
                want_clock = bool(cfg.get("enabled", True) and cfg.get("clock_out"))
                if not (want_mtc or want_clock):
                    break
                code = int(cfg.get("mtc_fps", 1))
                fps, _nominal = MTC_RATES[code]
                frame_s = 1.0 / fps
                running, pos = self.timecode_source() if self.timecode_source else (False, 0.0)
                now = time.perf_counter()
                if running != last_run:
                    last_run = running
                    if want_clock:
                        send([0xFA if running else 0xFC])
                    if want_mtc:
                        send(self.full_frame(pos, code))
                    qf, qf_next, prev_frame, clock_next = 0, now, None, now
                elif want_mtc and not running and abs(pos - last_pos) > 2 * frame_s * 1000.0:
                    send(self.full_frame(pos, code))             # Position bei stehender Uhr geaendert: Full Frame
                last_pos = pos
                if running and want_mtc and now >= qf_next:
                    if qf == 0:
                        pieces, frame = self.mtc_pieces(pos, code)
                        if prev_frame is not None and abs(frame - (prev_frame + 2)) > 2:
                            send(self.full_frame(pos, code))     # Sprung im laufenden Timecode
                        prev_frame = frame
                    send([0xF1, pieces[qf]])
                    qf = (qf + 1) % 8
                    qf_next += frame_s / 4.0
                    if qf_next < now - 0.1:                      # weit zurueckgefallen (Ruckler): neu aufsetzen
                        qf_next = now + frame_s / 4.0
                if running and want_clock:
                    bpm = max(30.0, min(300.0, float(self.bpm_source() if self.bpm_source else 120.0)))
                    interval = 60.0 / (bpm * 24.0)
                    while clock_next <= now:
                        send([0xF8])
                        clock_next += interval
                        if clock_next < now - 0.1:
                            clock_next = now + interval
                        break
                next_events = [t for t, on in ((qf_next, running and want_mtc), (clock_next, running and want_clock)) if on]
                delay = (min(next_events) - time.perf_counter()) if next_events else 0.02
                delay = min(delay, 0.02)
                if delay > 0.002:
                    time.sleep(delay - 0.001)
                else:
                    time.sleep(0)
        finally:
            if winmm is not None:
                try:
                    winmm.timeEndPeriod(1)
                except Exception:
                    pass

    # ------------------------------------------------------------------ Nachrichten verarbeiten
    def _handle_sync(self, ident: str, message: List[int]) -> None:
        self.handle(ident, message)

    def handle(self, device: str, message: List[int]) -> None:
        """Eine Rohnachricht eines Anschlusses. Im Ereignis-Thread aufrufen (so auch fuer Tests)."""
        event = parse(message)
        if event is None:
            return
        event["device"] = device
        if self.learning and event["type"] in ("note_on", "cc", "pc", "pitch", "aftertouch", "pressure") + TRANSPORT:
            if event["type"] in ("cc", "pitch", "aftertouch", "pressure") or event["value"] > 0:
                self.learning = False
                self.reconcile()
                self._spawn(self._emit("learned", {
                    "device": device, "name": device, "type": "note" if event["type"] == "note_on" else event["type"], "channel": event["channel"],
                    "number": event["number"], "value": event["value"], "text": describe(event)}))
                return                                           # das eingelernte Signal selbst loest nichts aus
        if self.cue_wanted and self.config.get("enabled", True) and event["type"] in ("note_on", "cc", "pc"):
            self._cue_events.append(event)                      # fuer die MIDI-Ausloeser der Cues (Server: _midi_cue_step)
        hit = self._dispatch(event)
        if self.watching:
            entry = {"t": time.time(), "device": device, "channel": event["channel"], "type": event["type"], "text": describe(event)}
            self._monitor.append(entry)
            if hit:
                self._hits.update(hit)
            if not self._monitor_scheduled:
                self._monitor_scheduled = True
                if self._loop is not None:
                    self._loop.call_later(MONITOR_FLUSH_S, self._flush_monitor)

    def _flush_monitor(self) -> None:
        self._monitor_scheduled = False
        events = list(self._monitor)[-MONITOR_BATCH:]
        self._monitor.clear()
        hits, self._hits = list(self._hits), set()
        if events or hits:
            self._spawn(self._emit("monitor", {"events": events, "hits": hits}))

    def _match(self, b: Dict[str, Any], event: Dict[str, Any]) -> bool:
        if not (b["enabled"] and b["type"] and b["command"]):
            return False
        if b["device"] and b["device"] != event["device"]:
            return False
        kind = event["type"]
        group = "note" if kind in ("note_on", "note_off") else kind
        if b["type"] != group:
            return False
        if b["type"] in TRANSPORT:
            return True
        if b["channel"] and b["channel"] != event["channel"]:
            return False
        return b["type"] in ("pitch", "pressure") or b["number"] == event["number"]

    def _dispatch(self, event: Dict[str, Any]) -> List[str]:
        """Passende Eintraege ausloesen. Gibt die Ids der getroffenen Eintraege zurueck (fuer die Anzeige im Dialog)."""
        hits: List[str] = []
        if not self.config.get("enabled", True):
            return hits
        for b in self.config["bindings"]:
            if not self._match(b, event):
                continue
            hits.append(b["id"])
            try:
                self._apply(b, event)
            except Exception:
                logger.exception("MIDI-Eintrag %s", b["id"])
        return hits

    def _runtime(self, b: Dict[str, Any]) -> Dict[str, Any]:
        return self._rt.setdefault(b["id"], {"down": False, "toggled": False, "last_cmd": None})

    def _apply(self, b: Dict[str, Any], event: Dict[str, Any]) -> None:
        mode = b["mode"]
        kind = event["type"]
        rt = self._runtime(b)
        context = {"note": event["number"], "number": event["number"], "channel": event["channel"], "velocity": event["value"] if kind in ("note_on", "note_off") else 127, "raw": event["raw"]}
        if mode in ("trigger", "toggle", "hold", "double", "long"):
            if kind == "cc":
                pressed = event["value"] >= 64
                edge = pressed != rt["down"]
                rt["down"] = pressed
                if not edge:
                    return
            elif kind == "note_on" or kind == "pc" or kind in TRANSPORT:
                pressed = True
                rt["down"] = True
            elif kind == "note_off":
                pressed = False
                rt["down"] = False
            else:
                return
            if mode == "trigger":
                if pressed:
                    self._submit(b, b["command"], context, key=None)
            elif mode == "toggle":
                if pressed:
                    rt["toggled"] = not rt["toggled"]
                    text = b["command_off"] if (not rt["toggled"] and b["command_off"]) else b["command"]
                    self._submit(b, text, context, key=None)
            elif mode == "hold":
                if pressed:
                    self._submit(b, b["command"], context, key=None)
                elif b["command_off"]:
                    self._submit(b, b["command_off"], context, key=None)
            elif mode == "double":                              # erst der zweite Druck innerhalb von DOUBLE_S loest aus
                if pressed:
                    now = time.monotonic()
                    if now - rt.get("last_press", -10.0) <= DOUBLE_S:
                        rt["last_press"] = -10.0
                        self._submit(b, b["command"], context, key=None)
                    else:
                        rt["last_press"] = now
            else:                                               # long: nur wenn die Taste lange genug gehalten wird
                timer = rt.pop("timer", None)
                if timer is not None:
                    timer.cancel()
                if pressed and self._loop is not None:
                    rt["timer"] = self._loop.call_later(b["hold_ms"] / 1000.0, self._long_fire, b, context)
            return
        if mode == "fader":
            top = 16383.0 if kind == "pitch" else 127.0
            if kind == "note_off":
                return
            fraction = max(0.0, min(1.0, event["raw"] / top))
            if b["curve"] == "square":
                fraction = fraction * fraction
            elif b["curve"] == "sqrt":
                fraction = fraction ** 0.5
            if b["invert"]:
                fraction = 1.0 - fraction
            value = b["min"] + fraction * (b["max"] - b["min"])
            if b.get("pickup") and not self._pickup_ok(b, rt, value):
                return
            context["value"] = _fmt(value)
            text = render(b["command"], {k: v for k, v in context.items()})
            if text == rt["last_cmd"]:
                return
            rt["last_cmd"] = text
            rt["last_value"], rt["last_fire_t"] = value, time.monotonic()
            self._submit(b, text, context, key=b["id"], rendered=True)
            return
        if mode == "relative" and kind == "cc":
            delta = relative_delta(event["raw"], b["encoding"]) * b["step"]
            if delta == 0:
                return
            context["delta"] = ("+" if delta > 0 else "-") + _fmt(abs(delta))
            self._submit(b, b["command"], context, key=None)             # jeder Schritt bleibt erhalten (Reihenfolge)

    def _long_fire(self, b: Dict[str, Any], context: Dict[str, Any]) -> None:
        self._runtime(b).pop("timer", None)
        if self.config.get("enabled", True):
            self._submit(b, b["command"], context, key=None)

    def _pickup_ok(self, b: Dict[str, Any], rt: Dict[str, Any], value: float) -> bool:
        """Soft-Takeover: ein Regler ohne Motor steht oft anders als das Ziel. Der Wert wird erst uebernommen, wenn der Regler das Ziel erreicht (3 % des Bereichs) oder durchquert hat.
        Wurde das Ziel zwischenzeitlich anderswo veraendert (Regler ruhte > 0,4 s), muss er es neu einfangen. Ist der Zielwert unbekannt, gilt der Regler sofort."""
        target = self.value_of(b["command"]) if self.value_of is not None else None
        if target is None:
            return True
        span = abs(b["max"] - b["min"]) or 1.0
        tolerance = 0.03 * span
        now = time.monotonic()
        if rt.get("picked") and now - rt.get("last_fire_t", 0.0) > 0.4 and rt.get("last_value") is not None and abs(target - rt["last_value"]) > tolerance:
            rt["picked"] = False                                # das Ziel wurde woanders veraendert
        if rt.get("picked"):
            return True
        previous = rt.get("prev_in")
        rt["prev_in"] = value
        if abs(value - target) <= tolerance or (previous is not None and (previous - target) * (value - target) <= 0):
            rt["picked"], rt["last_cmd"] = True, None
            return True
        return False

    def _submit(self, b: Dict[str, Any], template: str, context: Dict[str, Any], key: Any, rendered: bool = False) -> None:
        text = template if rendered else render(template, context)
        if not text.strip():
            return
        self._seq += 1
        # Regler: ein neuerer Wert ersetzt einen noch wartenden (Zusammenfassen); Tasten und Drehgeber-Schritte bleiben alle erhalten
        slot = key if key is not None else ("n", self._seq)
        if slot in self._work:
            self._work.pop(slot)
        self._work[slot] = (b, text)
        if self._work_event is not None:
            self._work_event.set()

    async def _work_loop(self) -> None:
        assert self._work_event is not None
        while True:
            await self._work_event.wait()
            self._work_event.clear()
            while self._work:
                slot, (b, text) = self._work.popitem(last=False)
                await self._fire(b, text)
                if isinstance(slot, str):                       # Regler: kurze Pause, damit schnelle Bewegungen zusammengefasst werden
                    await asyncio.sleep(CONTINUOUS_GAP_S)

    async def _fire(self, b: Dict[str, Any], text: str) -> None:
        if is_blocked(text):
            logger.warning("MIDI: '%s' ist per MIDI gesperrt", text)
            await self._emit("blocked", {"id": b["id"], "command": text})
            return
        if self.on_fire is not None:
            try:
                await self.on_fire(b, text)
            except Exception:
                logger.exception("MIDI-Befehl '%s'", text)

    # ------------------------------------------------------------------ Meldungen an die Fenster
    def _spawn(self, coro: Awaitable[None]) -> None:
        if self._loop is not None and not self._loop.is_closed():
            self._loop.create_task(coro)    # type: ignore[arg-type]

    async def _emit(self, kind: str, payload: Dict[str, Any]) -> None:
        if self.on_emit is not None:
            try:
                await self.on_emit(kind, payload)
            except Exception:
                logger.debug("MIDI-Meldung", exc_info=True)


midi = MidiEngine()
