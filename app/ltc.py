# Copyright (C) 2026 Samuel Zenker
# SPDX-License-Identifier: GPL-3.0-or-later
"""
ltc.py
LTC (Linear Timecode, SMPTE 12M): Timecode als AUDIOSIGNAL. Ein Zuspieler, eine DJ- / Show-Software oder ein Pult legt die Uhrzeit auf eine Tonspur; OpenCue liest sie von einem
Audio-Eingang (Line-In, USB-Interface) und stellt die globale Uhr (app/timecode.py) danach - Cues mit Ausloeser "Timecode" feuern dann sekundengenau zur Musik.

- `LtcDecoder`: reine Rechnung (kein Geraet, testbar). Biphase-Mark-Decodierung: an jeder Bitgrenze wechselt der Pegel, bei einer 1 zusaetzlich in der Bitmitte. Aus den Abstaenden
  der Nulldurchgaenge (kurz = halbes Bit, lang = ganzes Bit) werden die 80 Bits eines Bildes gelesen; das Synchronwort 0x3FFD am Ende rahmt das Bild ein.
  Bildraten 24 / 25 / 29,97 (Drop Frame) / 30 werden aus dem Drop-Frame-Bit und dem Abstand der Bilder erkannt.
- `LtcInput`: oeffnet den Audio-Eingang (PyAudioWPatch, wie app/audio_engine.py), waehlt den Kanal (links / rechts / Mischung), liefert fertige Bilder an `on_frame` und meldet
  "verloren", wenn eine Weile kein gueltiges Bild mehr kam. Dazu ein eingebautes Testsignal ("demo") ohne Geraet.
- Zeitpunkt: Der Wert im Bild nennt dessen ANFANG; beim Synchronwort ist das Bild gerade zu Ende - die Position ist also Wert + ein Bild.
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

from app import portaudio_lock

logger = logging.getLogger("opencue.ltc")

SYNC = [0, 0] + [1] * 12 + [0, 1]                               # Synchronwort 0x3FFD in Sendereihenfolge (Bit 64..79): "00", zwoelf Einsen, "01"
FRAME_RATES = (24.0, 25.0, 30000.0 / 1001.0, 30.0)               # erkannte Bildraten (29,97 nur mit Drop-Frame-Bit)
LOST_AFTER_S = 0.6                                               # so lange darf kein Bild kommen, bevor "verloren" gemeldet wird
DEFAULT_OUT = {"enabled": False, "device": "", "channel": "both", "fps": 25.0, "level": 0.5}
DEFAULT_CONFIG = {"enabled": False, "device": "", "channel": "left", "out": dict(DEFAULT_OUT)}
CHANNELS = ("left", "right", "mix")
OUT_CHANNELS = ("left", "right", "both")
OUT_FPS = (24.0, 25.0, 29.97, 30.0)


def clean_out(raw: Any, base: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Einstellung "LTC senden" bereinigen: an / aus, Ausgabegeraet, Kanal (links / rechts / beide), Bildrate (24 / 25 / 29,97 Drop Frame / 30), Pegel 0,05..1."""
    out = dict(base or DEFAULT_OUT)
    if isinstance(raw, dict):
        if "enabled" in raw:
            out["enabled"] = raw["enabled"] is True
        if "device" in raw:
            out["device"] = str(raw["device"] or "")[:200]
        if raw.get("channel") in OUT_CHANNELS:
            out["channel"] = raw["channel"]
        if "fps" in raw:
            try:
                value = float(raw["fps"])
                out["fps"] = min(OUT_FPS, key=lambda candidate: abs(candidate - value))
            except (TypeError, ValueError):
                pass
        if "level" in raw:
            try:
                out["level"] = round(min(1.0, max(0.05, float(raw["level"]))), 2)
            except (TypeError, ValueError):
                pass
    return out


def clean_config(raw: Any, base: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    out = dict(base or DEFAULT_CONFIG)
    out["out"] = clean_out(None, out.get("out"))
    if isinstance(raw, dict):
        if "enabled" in raw:
            out["enabled"] = raw["enabled"] is True
        if "device" in raw:
            out["device"] = str(raw["device"] or "")[:200]
        if raw.get("channel") in CHANNELS:
            out["channel"] = raw["channel"]
        if isinstance(raw.get("out"), dict):
            out["out"] = clean_out(raw["out"], out["out"])
    return out


# ------------------------------------------------------------------------------------------------ Zeitrechnung
def frames_to_ms(hh: int, mm: int, ss: int, ff: int, fps: float, drop: bool) -> float:
    """Zeitwert hh:mm:ss:ff -> Millisekunden. Drop Frame (29,97): je Minute fallen die Bilder 0 und 1 weg, ausser jede zehnte Minute."""
    if drop:
        total_minutes = hh * 60 + mm
        frames = ((hh * 3600 + mm * 60 + ss) * 30) + ff - 2 * (total_minutes - total_minutes // 10)
        return frames * 1001.0 / 30.0
    nominal = round(fps)
    return (((hh * 3600 + mm * 60 + ss) * nominal) + ff) * 1000.0 / fps


def nominal_fps(fps: float) -> int:
    return int(round(fps))


class LtcDecoder:
    """Streaming-Decoder: `feed(samples, now)` -> Liste fertiger Bilder {ms, fps, drop, h, m, s, f, at}. Mono-Samples (float, -1..1) in beliebig grossen Bloecken."""

    def __init__(self, rate: int) -> None:
        self.rate = int(rate)
        self.reset()

    def reset(self) -> None:
        self.state = 0                       # Pegel nach Schmitt-Trigger: 0 = noch unbekannt, 1 = hoch, -1 = tief
        self.peak = 0.0                      # langsam nachgefuehrte Signalspitze (Schwelle = Anteil davon)
        self.pos = 0                         # laufende Sample-Nummer
        self.last_cross = None               # Sample-Nummer des letzten Nulldurchgangs
        self.short = 0.0                     # geschaetzter halber Bitabstand (Samples)
        self.intervals: List[int] = []       # Abstaende, solange noch kein Schaetzwert da ist
        self.half_pending = False            # ein kurzer Abstand wartet auf seinen Partner (zusammen = eine 1)
        self.bits: List[int] = []            # die letzten Bits
        self.last_frame_end: Optional[int] = None
        self.frame_periods: List[float] = []
        self.fps_guess = 0.0
        self.nominal = 0                     # Bilder pro Sekunde laut Bildzaehler (24 / 25 / 30): steht fest, sobald der Zaehler einmal von seinem Hoechstwert auf 0 zurueckgesprungen ist
        self.prev_ff = -1
        self.level = 0.0

    # ---- Nulldurchgaenge (Schmitt-Trigger mit Anteil der Signalspitze als Schwelle)
    def _crossings(self, x: np.ndarray) -> List[int]:
        out: List[int] = []
        if x.size == 0:
            return out
        block_peak = float(np.max(np.abs(x)))
        self.peak = max(block_peak, self.peak * 0.995) if self.peak else block_peak
        self.level = block_peak
        threshold = max(0.02, self.peak * 0.25)
        # nur die Stellen, an denen das Signal die Schwelle ueber- / unterschreitet (vektorisiert), dann im Schmitt-Trigger-Takt auswerten
        hi = x > threshold
        lo = x < -threshold
        marks = np.flatnonzero(hi | lo)
        if marks.size:
            levels = np.where(hi[marks], 1, -1)
            previous = np.concatenate(([self.state], levels[:-1]))
            changed = (levels != previous) & (previous != 0)                       # Wechsel von einem Pegel zum anderen (das allererste Ueberschreiten ist noch kein Durchgang)
            out = [self.pos + int(i) for i in marks[changed]]
            self.state = int(levels[-1])
        self.pos += int(x.size)
        return out

    def feed(self, samples: Any, now: float = 0.0) -> List[Dict[str, Any]]:
        x = np.asarray(samples, dtype=np.float32)
        frames: List[Dict[str, Any]] = []
        for cross in self._crossings(x):
            if self.last_cross is not None:
                frame = self._interval(cross - self.last_cross, cross)
                if frame:
                    frame["at"] = now
                    frames.append(frame)
            self.last_cross = cross
        return frames

    # ---- Biphase Mark
    def _interval(self, d: int, at: int) -> Optional[Dict[str, Any]]:
        if d < 3 or d > self.rate // 100:        # kuerzer als 3 Samples = Rauschen, laenger als 10 ms = kein LTC
            self.half_pending = False
            return None
        if self.short <= 0:                       # Anlauf: aus den ersten Abstaenden den halben Bitabstand schaetzen (LTC besteht zur Haelfte aus Einsen)
            self.intervals.append(d)
            if len(self.intervals) >= 24:
                ordered = sorted(self.intervals)
                self.short = float(np.median(ordered[: len(ordered) // 2]))
                self.intervals = []
            return None
        threshold = self.short * 1.5
        if d < threshold:
            self.short = self.short * 0.95 + d * 0.05
            if self.half_pending:
                self.half_pending = False
                return self._bit(1, at)
            self.half_pending = True
            return None
        if self.half_pending:                     # ein langer Abstand nach einem einzelnen kurzen: aus dem Takt
            self.half_pending = False
            self.bits.clear()
            return None
        if d < self.short * 3.0:                  # ein ganzes Bit = eine 0
            return self._bit(0, at)
        self.bits.clear()
        self.short = 0.0                          # viel zu lang: das Signal hat sich geaendert (Pause, anderes Tempo): neu schaetzen
        return None

    def _bit(self, value: int, at: int) -> Optional[Dict[str, Any]]:
        bits = self.bits
        bits.append(value)
        if len(bits) > 80:
            del bits[0]
        if len(bits) == 80 and bits[64:] == SYNC:
            return self._frame(bits, at)
        return None

    def _frame(self, bits: List[int], at: int) -> Optional[Dict[str, Any]]:
        frame_units = bits[0] + 2 * bits[1] + 4 * bits[2] + 8 * bits[3]
        frame_tens = bits[8] + 2 * bits[9]
        drop = bool(bits[10])
        sec = (bits[16] + 2 * bits[17] + 4 * bits[18] + 8 * bits[19]) + 10 * (bits[24] + 2 * bits[25] + 4 * bits[26])
        minute = (bits[32] + 2 * bits[33] + 4 * bits[34] + 8 * bits[35]) + 10 * (bits[40] + 2 * bits[41] + 4 * bits[42])
        hour = (bits[48] + 2 * bits[49] + 4 * bits[50] + 8 * bits[51]) + 10 * (bits[56] + 2 * bits[57])
        ff = frame_units + 10 * frame_tens
        if sec > 59 or minute > 59 or hour > 23 or ff > 29:
            self.bits.clear()
            return None
        # Bildrate: aus dem Abstand der Bilder (Samples pro Bild) und dem Drop-Frame-Bit
        if ff == 0 and self.prev_ff >= 23 and not drop:                           # Zaehler ist zurueck auf 0: sein letzter Wert +1 ist die Bildrate (auch bei anderem Abspieltempo)
            self.nominal = self.prev_ff + 1 if self.prev_ff + 1 in (24, 25, 30) else self.nominal
        self.prev_ff = ff
        if self.last_frame_end is not None:
            period = at - self.last_frame_end
            if 0 < period < self.rate:
                self.frame_periods.append(period)
                if len(self.frame_periods) > 12:
                    del self.frame_periods[0]
                avg = sum(self.frame_periods) / len(self.frame_periods)
                self.fps_guess = self.rate / avg
        self.last_frame_end = at
        if self.fps_guess <= 0 and not drop:                      # das allererste Bild: die Bildrate steht erst nach dem zweiten fest - dieses eine Bild wird uebersprungen
            self.bits.clear()
            return None
        fps = self._snap_fps(drop, ff)
        ms = frames_to_ms(hour, minute, sec, ff, fps, drop) + 1000.0 / fps          # Wert = Anfang des Bildes, jetzt ist es zu Ende
        self.bits.clear()
        return {"ms": ms, "fps": fps, "drop": drop, "h": hour, "m": minute, "s": sec, "f": ff}

    def _snap_fps(self, drop: bool, ff: int) -> float:
        if drop:
            return 30000.0 / 1001.0
        if self.nominal:
            return float(self.nominal)
        guess = self.fps_guess
        if guess <= 0:
            return 30.0 if ff >= 25 else 25.0
        return min((24.0, 25.0, 30.0), key=lambda candidate: abs(candidate - guess))


# ------------------------------------------------------------------------------------------------ Testsignal
def encode_frame(hh: int, mm: int, ss: int, ff: int, drop: bool = False) -> List[int]:
    """Die 80 Bits eines LTC-Bildes (Benutzerbits 0, Farbbild-Bit 0)."""
    bits = [0] * 80

    def put(position: int, value: int, count: int) -> None:
        for i in range(count):
            bits[position + i] = (value >> i) & 1
    put(0, ff % 10, 4)
    put(8, ff // 10, 2)
    bits[10] = 1 if drop else 0
    put(16, ss % 10, 4)
    put(24, ss // 10, 3)
    put(32, mm % 10, 4)
    put(40, mm // 10, 3)
    put(48, hh % 10, 4)
    put(56, hh // 10, 2)
    bits[64:80] = SYNC
    return bits


def render_bits(bits: List[int], samples_per_bit: float, level: float, state: Dict[str, float]) -> np.ndarray:
    """Biphase Mark als Audio: Pegelwechsel an jeder Bitgrenze, bei einer 1 zusaetzlich in der Mitte. `state` haelt Pegel und Rest-Samples zwischen den Aufrufen."""
    out: List[np.ndarray] = []
    polarity = state.get("polarity", 1.0)
    carry = state.get("carry", 0.0)
    for bit in bits:
        polarity = -polarity
        half = samples_per_bit / 2.0
        a = carry + half
        n1 = int(a)
        carry = a - n1
        out.append(np.full(n1, level * polarity, dtype=np.float32))
        if bit:
            polarity = -polarity
        b = carry + half
        n2 = int(b)
        carry = b - n2
        out.append(np.full(n2, level * polarity, dtype=np.float32))
    state["polarity"], state["carry"] = polarity, carry
    return np.concatenate(out) if out else np.zeros(0, dtype=np.float32)


def frame_bits(n: int, fps: float, drop: bool) -> List[int]:
    """Die 80 Bits des n-ten Bildes (n = laufende Bildnummer ab 0; Drop Frame: die Bildnummer wird in die Zeitangabe mit uebersprungenen Bildern 00 / 01 umgerechnet)."""
    nominal = nominal_fps(fps)
    if drop:
        d, m = divmod(n, 17982)
        n += 18 * d + (2 * ((m - 2) // 1798) if m >= 2 else 0)
    ff = n % nominal
    total_seconds = n // nominal
    return encode_frame(total_seconds // 3600 % 24, total_seconds // 60 % 60, total_seconds % 60, ff, drop)


def frame_start_ms(n: int, fps: float, drop: bool) -> float:
    """Wann (ms auf der Uhr) das n-te Bild beginnt."""
    return n * 1001.0 / 30.0 if drop else n * 1000.0 / fps


class LtcGenerator:
    """Erzeugt fortlaufendes LTC (zum Ausprobieren / fuer Tests). `render(count)` liefert den naechsten Block Samples; die Zeit laeuft im Takt der erzeugten Samples."""

    def __init__(self, rate: int = 48000, fps: float = 25.0, start_ms: float = 0.0, drop: bool = False, level: float = 0.5) -> None:
        self.rate, self.fps, self.drop, self.level = int(rate), float(fps), bool(drop), float(level)
        self.state: Dict[str, float] = {}
        self.frame_number = int(round(start_ms * self.fps / 1000.0))
        self.buffer = np.zeros(0, dtype=np.float32)

    def _next_frame_bits(self) -> List[int]:
        n = self.frame_number
        self.frame_number += 1
        return frame_bits(n, self.fps, self.drop)

    def render(self, count: int) -> np.ndarray:
        per_bit = self.rate / (self.fps * 80.0)
        while self.buffer.size < count:
            self.buffer = np.concatenate([self.buffer, render_bits(self._next_frame_bits(), per_bit, self.level, self.state)])
        block, self.buffer = self.buffer[:count], self.buffer[count:]
        return block


# ------------------------------------------------------------------------------------------------ Eingang
class LtcInput:
    """Liest LTC von einem Audio-Eingang und meldet Bilder. Rueckrufe kommen aus dem Audio-Thread: der Aufrufer muss selbst in seine Ereignisschleife wechseln."""

    def __init__(self) -> None:
        self.config: Dict[str, Any] = dict(DEFAULT_CONFIG)
        self.on_frame: Optional[Callable[[Dict[str, Any]], None]] = None
        self.on_lost: Optional[Callable[[], None]] = None
        self._lock = threading.RLock()
        self._decoder: Optional[LtcDecoder] = None
        self._stream: Any = None
        self._pa: Any = None
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self.running = False
        self.error = ""
        self.device_name = ""
        self.locked = False
        self.last_frame_at = 0.0
        self.last: Dict[str, Any] = {}
        self.level = 0.0

    # ---- Zustand fuer die Oberflaeche
    def status(self) -> Dict[str, Any]:
        frame = self.last
        text = ""
        if frame:
            text = "%02d:%02d:%02d%s%02d" % (frame["h"], frame["m"], frame["s"], ";" if frame["drop"] else ":", frame["f"])
        return {"config": dict(self.config), "running": self.running, "locked": self.locked, "error": self.error, "device": self.device_name,
                "fps": round(frame.get("fps", 0.0), 2) if frame else 0.0, "drop": bool(frame.get("drop")) if frame else False, "timecode": text if self.locked else "",
                "level": round(min(1.0, self.level), 3)}

    # ---- Betrieb
    def configure(self, raw: Any) -> Dict[str, Any]:
        with self._lock:
            self.config = clean_config(raw, self.config)
        self.start() if self.config["enabled"] else self.stop()
        return self.status()

    def start(self) -> bool:
        self.stop()
        with self._lock:
            if not self.config.get("enabled"):
                return False
            target = self.config.get("device", "")
            self.error = ""
            self._stop.clear()
            if not target:
                self.error = "no_device"
                return False
            if target == "demo":
                self.device_name = "Demo (25 fps)"
                self._decoder = LtcDecoder(48000)
                self._thread = threading.Thread(target=self._demo_loop, name="ltc-demo", daemon=True)
                self._thread.start()
                self.running = True
                return True
            return self._open_device(target)

    def stop(self) -> None:
        self._stop.set()
        with self._lock:
            stream, pa, thread = self._stream, self._pa, self._thread
            self._stream = self._pa = self._thread = None
            was_locked = self.locked
            self.running = False
            self.locked = False
            self.level = 0.0
        if stream is not None:
            try:
                stream.stop_stream()
                stream.close()
            except Exception:                                                       # noqa: BLE001
                pass
        if pa is not None:
            portaudio_lock.LOCK.acquire()
            try:
                pa.terminate()
            except Exception:                                                       # noqa: BLE001
                pass
            finally:
                portaudio_lock.LOCK.release()
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=1.5)
        if was_locked and self.on_lost:
            self.on_lost()

    def _open_device(self, target: str) -> bool:
        try:
            import pyaudiowpatch as pyaudio
        except Exception as exc:                                                    # noqa: BLE001
            self.error = f"unavailable: {exc}"
            return False
        from app.audio_engine import list_devices
        match = next((d for d in list_devices() if d["id"] == target and d["kind"] in ("input", "loopback")), None)
        if match is None:
            self.error = "device_missing"
            return False
        channels = max(1, min(2, int(match["channels"])))
        rate = int(match["rate"])
        decoder = LtcDecoder(rate)
        channel = self.config.get("channel", "left")
        portaudio_lock.LOCK.acquire()
        pa = None
        try:
            pa = pyaudio.PyAudio()

            def callback(data, frames, info, status):
                try:
                    block = np.frombuffer(data, dtype=np.float32)
                    if channels > 1:
                        block = block.reshape(-1, channels)
                        mono = block.mean(axis=1) if channel == "mix" else block[:, 1 if channel == "right" else 0]
                    else:
                        mono = block
                    self._process(decoder, mono)
                except Exception:                                                   # noqa: BLE001
                    logger.exception("LTC-Audio-Callback fehlgeschlagen")
                return (None, pyaudio.paContinue)

            stream = pa.open(format=pyaudio.paFloat32, channels=channels, rate=rate, input=True, input_device_index=int(match["index"]), frames_per_buffer=1024, stream_callback=callback)
        except Exception as exc:                                                    # noqa: BLE001
            self.error = f"open_failed: {exc}"
            logger.warning("OC-3201 LTC-Eingang '%s' liess sich nicht oeffnen: %s", target, exc)
            if pa is not None:
                try:
                    pa.terminate()
                except Exception:                                                   # noqa: BLE001
                    pass
            return False
        finally:
            portaudio_lock.LOCK.release()
        self._pa, self._stream, self._decoder = pa, stream, decoder
        self.device_name = match["name"]
        self._thread = threading.Thread(target=self._watchdog, name="ltc-watchdog", daemon=True)
        self._thread.start()
        self.running = True
        return True

    # ---- Verarbeitung (auch fuer Tests: feed() mit fertigen Samples)
    def feed(self, samples: Any, rate: int = 48000) -> None:
        with self._lock:
            if self._decoder is None or self._decoder.rate != rate:
                self._decoder = LtcDecoder(rate)
            decoder = self._decoder
        self._process(decoder, np.asarray(samples, dtype=np.float32))

    def _process(self, decoder: LtcDecoder, mono: np.ndarray) -> None:
        now = time.monotonic()
        frames = decoder.feed(mono, now)
        self.level = decoder.level
        for frame in frames:
            self.locked = True
            self.last_frame_at = now
            self.last = frame
            if self.on_frame:
                self.on_frame(frame)

    def _watchdog(self) -> None:
        while not self._stop.wait(0.2):
            if self.locked and time.monotonic() - self.last_frame_at > LOST_AFTER_S:
                self.locked = False
                if self.on_lost:
                    self.on_lost()

    def _demo_loop(self) -> None:
        """Testsignal ohne Geraet: LTC mit 25 Bildern pro Sekunde ab 00:00:00:00, in Echtzeit."""
        rate = 48000
        generator = LtcGenerator(rate, 25.0)
        decoder = self._decoder
        hop = 1024
        start = time.monotonic()
        produced = 0
        while not self._stop.is_set():
            due = int((time.monotonic() - start) * rate)
            while produced + hop <= due and not self._stop.is_set():
                self._process(decoder, generator.render(hop))
                produced += hop
            if self._stop.wait(0.01):
                break
            if self.locked and time.monotonic() - self.last_frame_at > LOST_AFTER_S:
                self.locked = False
                if self.on_lost:
                    self.on_lost()


class LtcOutput:
    """LTC SENDEN: solange der globale Timecode VORWAERTS laeuft, erzeugt OpenCue LTC im Takt der Uhr und gibt es auf einem Audio-Ausgang aus (Zuspieler, Pult, Aufnahmegeraet laufen mit).
    Steht die Uhr oder laeuft sie rueckwaerts, bleibt der Ausgang still. Die Bilder werden laufend an der Uhr ausgerichtet: ein Sprung der Uhr beginnt sofort beim richtigen Bild."""

    def __init__(self) -> None:
        self.config: Dict[str, Any] = dict(DEFAULT_OUT)
        self.provider: Optional[Callable[[], Tuple[bool, int, float, float]]] = None      # () -> (laeuft, Richtung, Tempo, Position in ms)
        self._lock = threading.RLock()
        self._stream: Any = None
        self._pa: Any = None
        self.running = False
        self.error = ""
        self.device_name = ""
        self.sending = False                                                                # gerade kommt LTC heraus
        self._gen_state: Dict[str, float] = {}
        self._buffer = np.zeros(0, dtype=np.float32)
        self._next_frame: Optional[int] = None

    def status(self) -> Dict[str, Any]:
        return {"config": dict(self.config), "running": self.running, "error": self.error, "device": self.device_name, "sending": bool(self.running and self.sending)}

    # ---- Reine Rechnung (testbar)
    def render(self, count: int, rate_hz: int, running: bool, direction: int, tc_rate: float, position_ms: float) -> np.ndarray:
        """Der naechste Block (Mono) fuer den Ausgang. position_ms = Uhrzeit am Anfang des Blocks."""
        if not running or direction < 0 or tc_rate <= 0:
            self._buffer = np.zeros(0, dtype=np.float32)
            self._next_frame = None
            self.sending = False
            return np.zeros(count, dtype=np.float32)
        fps = float(self.config.get("fps", 25.0))
        drop = abs(fps - 29.97) < 0.01
        real_fps = 30000.0 / 1001.0 if drop else fps
        level = float(self.config.get("level", 0.5))
        per_bit = rate_hz / (real_fps * 80.0) / tc_rate                                  # laeuft die Uhr schneller, werden die Bilder kuerzer
        while self._buffer.size < count:
            buffered_ms = self._buffer.size / rate_hz * 1000.0 * tc_rate
            target_ms = position_ms + buffered_ms                                         # so spaet beginnt das naechste Bild
            n = self._next_frame
            if n is None or abs(frame_start_ms(n, real_fps, drop) - target_ms) > 1.5 * 1000.0 / real_fps:
                n = int(max(0, round(target_ms * real_fps / 1000.0)))                    # ausrichten: erstes Bild, das jetzt beginnt
            self._buffer = np.concatenate([self._buffer, render_bits(frame_bits(n, real_fps, drop), per_bit, level, self._gen_state)])
            self._next_frame = n + 1
        block, self._buffer = self._buffer[:count], self._buffer[count:]
        self.sending = True
        return block

    # ---- Geraet
    def configure(self, raw: Any) -> Dict[str, Any]:
        with self._lock:
            self.config = clean_out(raw, self.config)
        self.start() if self.config["enabled"] else self.stop()
        return self.status()

    def start(self) -> bool:
        self.stop()
        with self._lock:
            self.error = ""
            if not self.config.get("enabled"):
                return False
            target = self.config.get("device", "")
            if not target:
                self.error = "no_device"
                return False
            try:
                import pyaudiowpatch as pyaudio
            except Exception as exc:                                                   # noqa: BLE001
                self.error = f"unavailable: {exc}"
                return False
            match = next((d for d in list_outputs() if d["id"] == target), None)
            if match is None:
                self.error = "device_missing"
                return False
            channels = max(1, min(2, int(match["channels"])))
            rate = int(match["rate"])
            pick = self.config.get("channel", "both")
            portaudio_lock.LOCK.acquire()
            pa = None
            try:
                pa = pyaudio.PyAudio()

                def callback(data, frames, info, status):
                    try:
                        running, direction, tc_rate, position = self.provider() if self.provider else (False, 1, 1.0, 0.0)
                        mono = self.render(frames, rate, running, direction, tc_rate, position)
                        if channels == 1:
                            out = mono
                        else:
                            out = np.zeros((frames, channels), dtype=np.float32)
                            if pick in ("left", "both"):
                                out[:, 0] = mono
                            if pick in ("right", "both"):
                                out[:, 1] = mono
                        return (out.astype(np.float32).tobytes(), pyaudio.paContinue)
                    except Exception:                                                  # noqa: BLE001
                        logger.exception("LTC-Ausgabe fehlgeschlagen")
                        return (np.zeros(frames * channels, dtype=np.float32).tobytes(), pyaudio.paContinue)

                stream = pa.open(format=pyaudio.paFloat32, channels=channels, rate=rate, output=True, output_device_index=int(match["index"]), frames_per_buffer=512, stream_callback=callback)
            except Exception as exc:                                                    # noqa: BLE001
                self.error = f"open_failed: {exc}"
                logger.warning("OC-3201 LTC-Ausgang '%s' liess sich nicht oeffnen: %s", target, exc)
                if pa is not None:
                    try:
                        pa.terminate()
                    except Exception:                                                   # noqa: BLE001
                        pass
                return False
            finally:
                portaudio_lock.LOCK.release()
            self._pa, self._stream = pa, stream
            self.device_name = match["name"]
            self.running = True
            return True

    def stop(self) -> None:
        with self._lock:
            stream, pa = self._stream, self._pa
            self._stream = self._pa = None
            self.running = False
            self.sending = False
            self._buffer = np.zeros(0, dtype=np.float32)
            self._next_frame = None
        if stream is not None:
            try:
                stream.stop_stream()
                stream.close()
            except Exception:                                                           # noqa: BLE001
                pass
        if pa is not None:
            portaudio_lock.LOCK.acquire()
            try:
                pa.terminate()
            except Exception:                                                           # noqa: BLE001
                pass
            finally:
                portaudio_lock.LOCK.release()


def list_outputs() -> List[Dict[str, Any]]:
    """Alle Audio-Ausgaenge (Lautsprecher, Kopfhoerer, USB-Interfaces), die Windows kennt (WASAPI)."""
    out: List[Dict[str, Any]] = []
    try:
        import pyaudiowpatch as pyaudio
    except Exception:                                                                    # noqa: BLE001
        return out
    pa = None
    portaudio_lock.LOCK.acquire()
    try:
        pa = pyaudio.PyAudio()
        wasapi = pa.get_host_api_info_by_type(pyaudio.paWASAPI)
        default_out = wasapi.get("defaultOutputDevice", -1)
        for index in range(pa.get_device_count()):
            info = pa.get_device_info_by_index(index)
            if info.get("hostApi") != wasapi["index"] or int(info.get("maxOutputChannels", 0)) <= 0 or info.get("isLoopbackDevice"):
                continue
            out.append({"id": "output:" + str(info["name"]), "name": str(info["name"]), "channels": int(info["maxOutputChannels"]), "rate": int(info["defaultSampleRate"]), "index": index,
                        "default": index == default_out})
    except Exception as exc:                                                             # noqa: BLE001
        logger.warning("Audio-Ausgaenge konnten nicht gelesen werden: %s", exc)
    finally:
        if pa is not None:
            try:
                pa.terminate()
            except Exception:                                                            # noqa: BLE001
                pass
        portaudio_lock.LOCK.release()
    out.sort(key=lambda d: (not d["default"], d["name"].lower()))
    return out


ltc = LtcInput()
ltc_out = LtcOutput()
