"""
timecode.py
Globaler Timecode ("die interne Uhr"): ein einziger, vom Server gefuehrter Zaehler in Millisekunden.

- Zustand: laeuft / steht, Richtung (vorwaerts/rueckwaerts), Geschwindigkeit (Rate), Position.
- Die Position wird nie "mitgezaehlt", sondern aus einem Ankerpunkt berechnet (Basiswert + Richtung * Rate * verstrichene
  monotone Zeit). Dadurch ist sie auf jedem Geraet identisch berechenbar: die Clients bekommen bei jeder Aenderung und alle
  paar Sekunden als Herzschlag den Zustand und rechnen die Zwischenzeit selbst aus (Videos/Audio folgen so ohne Dauerverkehr).
- Cue-Ausloeser: Cues mit Ausloeser "timecode" feuern, wenn der Timecode im LAUFENDEN Vorwaertslauf ihre Zeit ueberschreitet.
  Springen (Seek) und Rueckwaertslauf loesen nichts aus - sonst wuerde ein Sprung alle dazwischenliegenden Cues auf einmal abfeuern.
- Der Tick-Task laeuft nur, solange der Timecode laeuft (kein Leerlauf-Verbrauch) und wird beim ersten Start angelegt.
"""
from __future__ import annotations

import asyncio
import re
import time
from typing import Any, Awaitable, Callable, Dict, Optional

MAX_MS = 100 * 3600 * 1000          # 100 Stunden: obere Grenze (und Grenze fuer gespeicherte Cue-Zeiten)
MIN_RATE, MAX_RATE = 0.1, 8.0
TICK_SECONDS = 0.02                 # 50 Hz Pruefung auf Cue-Zeiten
HEARTBEAT_SECONDS = 1.0             # Zustandsmeldung an die Clients waehrend des Laufs (gegen Drift)

StateCallback = Callable[[Dict[str, Any]], Awaitable[None]]
CrossCallback = Callable[[float, float], Awaitable[None]]


def parse_timecode_ms(text: Any) -> Optional[int]:
    """Zeit als Text -> Millisekunden oder None. Gleiche Regeln wie im Browser (OCTimecode.parse): '4.3' / '4,3' (Sekunden),
    '1:04.300', '00:00:04.300'; hoechstens 100 Stunden."""
    raw = str(text if text is not None else "").strip().replace(",", ".")
    if not raw:
        return None
    parts = raw.split(":")
    if len(parts) > 3:
        return None
    seconds = parts.pop()
    if not re.fullmatch(r"\d+(\.\d+)?", seconds):
        return None
    total = float(seconds)
    for index, part in enumerate(reversed(parts)):            # erst Minuten, dann Stunden
        if not re.fullmatch(r"\d+", part):
            return None
        total += int(part) * (60, 3600)[index]
    ms = int(round(total * 1000))
    return ms if 0 <= ms <= MAX_MS else None


def format_timecode(ms: Any) -> str:
    total = max(0, int(ms))
    return f"{total // 3600000:02d}:{total // 60000 % 60:02d}:{total // 1000 % 60:02d}.{total % 1000:03d}"


def clamp_ms(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    if number != number:                      # NaN
        return 0.0
    return min(float(MAX_MS), max(0.0, number))


class TimecodeEngine:
    def __init__(self) -> None:
        self._base_ms = 0.0
        self._anchor = time.monotonic()
        self.running = False
        self.direction = 1
        self.rate = 1.0
        self._scan_pos = 0.0                  # bis hierher wurden Cue-Zeiten schon geprueft
        self._skip_scan = False
        self._task: Optional[asyncio.Task] = None
        self._wake: Optional[asyncio.Event] = None
        self._on_state: Optional[StateCallback] = None
        self._on_cross: Optional[CrossCallback] = None
        self._last_beat = 0.0

    # ---- Anbindung (der Server setzt die Rueckrufe)
    def set_callbacks(self, on_state: Optional[StateCallback], on_cross: Optional[CrossCallback]) -> None:
        self._on_state, self._on_cross = on_state, on_cross

    # ---- Position
    def position_ms(self, now: Optional[float] = None) -> float:
        if not self.running:
            return self._base_ms
        now = time.monotonic() if now is None else now
        pos = self._base_ms + self.direction * self.rate * (now - self._anchor) * 1000.0
        return min(float(MAX_MS), max(0.0, pos))

    def _rebase(self) -> float:
        pos = self.position_ms()
        self._base_ms, self._anchor = pos, time.monotonic()
        return pos

    def state(self) -> Dict[str, Any]:
        return {"running": self.running, "direction": self.direction, "rate": self.rate,
                "position_ms": round(self.position_ms(), 1), "server_time_ms": int(time.time() * 1000)}

    # ---- Bedienung (synchron; der Server verteilt danach den Zustand)
    def play(self, direction: int = 1) -> Dict[str, Any]:
        pos = self._rebase()
        self.direction = -1 if direction < 0 else 1
        if self.direction < 0 and pos <= 0:
            self.running = False             # rueckwaerts am Anfang: nichts zu tun
        else:
            self.running = True
            self._scan_pos = -1.0 if pos == 0 else pos      # Start bei 0: ein Cue bei 0 s soll feuern
            self._skip_scan = False
        self._ensure_task()
        self._poke()
        return self.state()

    def pause(self) -> Dict[str, Any]:
        self._rebase()
        self.running = False
        self._poke()
        return self.state()

    def stop(self) -> Dict[str, Any]:
        """Anhalten und auf 0 zuruecksetzen."""
        self.running = False
        self._base_ms, self._anchor = 0.0, time.monotonic()
        self._skip_scan = True
        self._poke()
        return self.state()

    def seek(self, ms: Any) -> Dict[str, Any]:
        """Auf eine Zeit springen (laeuft weiter, wenn er lief). Loest keine Cues aus."""
        self._base_ms, self._anchor = clamp_ms(ms), time.monotonic()
        self._scan_pos = self._base_ms
        self._skip_scan = True
        self._poke()
        return self.state()

    def set_rate(self, rate: Any) -> Dict[str, Any]:
        self._rebase()
        try:
            value = float(rate)
        except (TypeError, ValueError):
            value = 1.0
        self.rate = round(min(MAX_RATE, max(MIN_RATE, value)), 3)
        return self.state()

    def reset(self) -> None:
        """Neue/geladene Show: Uhr anhalten und auf 0 (kein Zustand der alten Show)."""
        self.running = False
        self._base_ms, self._anchor = 0.0, time.monotonic()
        self.direction, self.rate = 1, 1.0
        self._skip_scan = True
        self._poke()

    # ---- Tick
    def _poke(self) -> None:
        if self._wake is not None:
            self._wake.set()

    def _ensure_task(self) -> None:
        if self._task is not None and not self._task.done():
            return
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return                           # ohne laufende Schleife (reine Rechentests) gibt es keinen Tick
        self._wake = asyncio.Event()
        self._task = loop.create_task(self._run())

    async def _emit(self) -> None:
        if self._on_state is not None:
            await self._on_state(self.state())

    async def _run(self) -> None:
        try:
            while True:
                if not self.running:
                    assert self._wake is not None
                    self._wake.clear()
                    if self.running:                 # zwischen Pruefung und clear() gestartet
                        continue
                    await self._wake.wait()
                    continue
                now = time.monotonic()
                pos = self.position_ms(now)
                prev = self._scan_pos
                self._scan_pos = pos
                if self._skip_scan:
                    self._skip_scan = False
                elif self.direction > 0 and pos > prev and self._on_cross is not None:
                    await self._on_cross(prev, pos)
                if self.direction < 0 and pos <= 0:
                    self.running = False
                    self._base_ms, self._anchor = 0.0, time.monotonic()
                    await self._emit()
                    continue
                if now - self._last_beat >= HEARTBEAT_SECONDS:
                    self._last_beat = now
                    await self._emit()
                await asyncio.sleep(TICK_SECONDS)
        except asyncio.CancelledError:
            pass

    def shutdown(self) -> None:
        if self._task is not None:
            self._task.cancel()
            self._task = None


timecode = TimecodeEngine()
