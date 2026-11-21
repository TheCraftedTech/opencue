# Copyright (C) 2026 Samuel Zenker
# SPDX-License-Identifier: GPL-3.0-or-later
"""
audio_engine.py
Audio-Live-Analyse von OpenCue: nimmt ein Audio-Eingangssignal auf (Mikrofon, Line-In, USB-Interface oder den Systemton des Computers ("Loopback"),
alles, was Windows als Eingang kennt) und berechnet daraus in Echtzeit

  - Pegel und acht Frequenzbaender (mit automatischer Verstaerkung, 0-1),
  - Einsaetze (Bassdrum, Snare, Hi-Hat) als abklingende Impulse,
  - das Tempo (BPM) und eine gleichmaessige Beat-Position 0-1 samt Beat-Impuls und -Zaehler,
  - ein Spektrum mit 32 Balken fuer die Anzeige.

Die Effekt-Skripte lesen die Werte als Systemvariablen `a_...` (Namen: app/audio_vars.py), die Oberflaeche zeigt sie im Panel "Audio".

Aufbau: `AudioAnalyzer` ist die reine Rechnung (numpy, kennt keine Geraete, bekommt die Zeit von aussen - dadurch genau pruefbar); `AudioEngine` verwaltet Quelle,
Einstellungen und Faden (Aufnahme-Callback, Waechter fuer stumme Loopback-Quellen, Demo-Beat) und liefert den Stand an Effekt-Engine, Server und API.
Die Verzoegerung der Analyse betraegt ein Fenster (2048 Samples, ca. 43 ms) - der Einsatz wird aber schon im ersten Bild erkannt, in dem er hoerbar anschwillt
(Schrittweite ca. 10 ms); dazu kommt die Puffergroesse des Audiogeraets (Windows-Standard ca. 10 ms).
"""
from __future__ import annotations

import collections
import logging
import math
import threading
import time
from typing import Any, Deque, Dict, List, Optional, Tuple

import numpy as np

from app import portaudio_lock
from app.audio_vars import AUDIO_VARS, BEAT_TAU, HAT_TAU, KICK_TAU, SNARE_TAU, silent

logger = logging.getLogger("opencue.audio")

WINDOW = 2048                              # Samples je Spektrum
HOP_SECONDS = 0.0107                       # Schrittweite (ca. 93 Bilder pro Sekunde)
BAND_EDGES = (20, 60, 150, 400, 1000, 2500, 5000, 10000, 20000)          # acht Baender in Hz
SPECTRUM_BARS = 32
SPECTRUM_LOW, SPECTRUM_HIGH = 30.0, 16000.0
CEIL_MIN = 0.02                            # leiseste Obergrenze der automatischen Verstaerkung (darunter = Stille / Rauschen)
FIXED_CEIL = 0.15                          # Obergrenze ohne automatische Verstaerkung (Regler "Verstaerkung" wirkt dann direkt)
CEIL_DECAY_DB_PER_SECOND = 4.0             # so schnell vergisst die automatische Verstaerkung laute Stellen
GAMMA = 0.75                               # leichte Anhebung leiser Anteile
SHORT_WINDOW = 512                         # kurzes Fenster (ca. 11 ms) fuer die scharfen Einsaetze von Snare und Hi-Hat
FLUX_FLOOR = {"kick": 0.4, "snare": 0.25, "hat": 0.2}      # kleinster Bezugswert je Einsatz (Rauschen loest nichts aus)
FLOOR_MIN = FLUX_FLOOR
MIN_BPM, MAX_BPM, PRIOR_BPM = 70.0, 180.0, 125.0        # Suchbereich des Tempos und das haeufigste Tempo (Gewichtung gegen Verwechslung mit halbem/doppeltem Tempo)
TEMPO_HISTORY_SECONDS = 8.0
TEMPO_INTERVAL_SECONDS = 0.5
SILENCE_RMS = 0.002

DEFAULTS: Dict[str, Any] = {
    "device": "",                          # "" = keine Quelle gewaehlt, "demo" = Demo-Beat, sonst die Kennung aus devices()
    "autostart": False,                    # beim Programmstart die Quelle wieder oeffnen
    "gain": 1.0,                           # Eingangsverstaerkung (Faktor)
    "auto_gain": True,                     # automatische Verstaerkung (Bezug = die lautesten Stellen der letzten Sekunden)
    "sensitivity": 0.5,                    # Empfindlichkeit der Einsatz-Erkennung 0-1
    "smoothing": 0.5,                      # Traegheit der Pegel (0 = flink, 1 = traege)
    "latency_ms": 0.0,                     # Ausgleich: positiv = Lichter reagieren frueher (Verzoegerung der Geraete/Technik)
    "mode": "auto",                        # Tempo: "auto" (erkannt) oder "manual" (fest eingestellt / getippt)
    "bpm": 120.0,                          # Tempo im Modus "manual"
    "phase_follow": True,                  # Modus "manual": die Beat-Position folgt sanft den Einsaetzen der Musik
    "demo_bpm": 120.0,                     # Tempo des Demo-Beats
}
LIMITS: Dict[str, Tuple[float, float]] = {"gain": (0.05, 20.0), "sensitivity": (0.0, 1.0), "smoothing": (0.0, 1.0), "latency_ms": (-150.0, 300.0), "bpm": (30.0, 300.0), "demo_bpm": (60.0, 200.0)}


def clean_config(raw: Any, base: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Prueft Einstellungen (unbekannte Schluessel und falsche Typen werden verworfen, Zahlen auf ihren Bereich begrenzt)."""
    result = dict(base if base is not None else DEFAULTS)
    if not isinstance(raw, dict):
        return result
    for key, default in DEFAULTS.items():
        if key not in raw:
            continue
        value = raw[key]
        if isinstance(default, bool):
            result[key] = value is True or str(value).lower() in ("1", "true", "on")
        elif key == "device":
            result[key] = str(value or "")[:200]
        elif key == "mode":
            result[key] = "manual" if str(value).lower() == "manual" else "auto"
        else:
            try:
                number = float(value)
            except (TypeError, ValueError):
                continue
            if not math.isfinite(number):
                continue
            low, high = LIMITS[key]
            result[key] = max(low, min(high, number))
    return result


# ------------------------------------------------------------------------------------------------------------------ Analyse
class AudioAnalyzer:
    """Rechnet Audio-Bloecke (Mono, float, -1..1) in Pegel, Baender, Einsaetze, Tempo und Beat-Position um. Nicht thread-sicher: der Aufrufer sperrt."""

    def __init__(self, rate: int, settings: Optional[Dict[str, Any]] = None) -> None:
        self.rate = int(rate)
        self.settings = settings if settings is not None else dict(DEFAULTS)
        self.hop = max(64, int(round(self.rate * HOP_SECONDS)))
        self.fps = self.rate / self.hop
        self.dt = 1.0 / self.fps
        self.window = np.hanning(WINDOW).astype(np.float32)
        self._scale = 2.0 / float(self.window.sum())
        freqs = np.fft.rfftfreq(WINDOW, 1.0 / self.rate)
        self._freqs = freqs
        nyquist = self.rate / 2.0

        def span(low: float, high: float) -> Tuple[int, int]:
            first = int(np.searchsorted(freqs, low))
            last = max(first + 1, int(np.searchsorted(freqs, min(high, nyquist))))
            return first, last

        self.band_spans = [span(lo, hi) for lo, hi in zip(BAND_EDGES[:-1], BAND_EDGES[1:])]
        self.window_short = np.hanning(SHORT_WINDOW).astype(np.float32)
        self._scale_short = 2.0 / float(self.window_short.sum())
        freqs_short = np.fft.rfftfreq(SHORT_WINDOW, 1.0 / self.rate)

        def span_short(low: float, high: float) -> Tuple[int, int]:
            first = int(np.searchsorted(freqs_short, low))
            return first, max(first + 1, int(np.searchsorted(freqs_short, min(high, nyquist))))

        # Bassdrum ueber das lange Fenster (tiefe Toene brauchen Frequenzaufloesung), Snare und Hi-Hat ueber das kurze (scharfe Zeitaufloesung)
        self.onset_spans = {"kick": span(35, 140), "snare": span_short(250, 2800), "hat": span_short(7000, 16000)}
        self._refractory = {"kick": 0.12, "snare": 0.10, "hat": 0.05}
        edges = np.logspace(math.log10(SPECTRUM_LOW), math.log10(min(SPECTRUM_HIGH, nyquist * 0.98)), SPECTRUM_BARS + 1)
        self._bar_spans = [span(edges[i], edges[i + 1]) for i in range(SPECTRUM_BARS)]
        centres = np.sqrt(edges[:-1] * edges[1:])
        self._bar_tilt = (centres / 1000.0) ** 0.5            # +3 dB je Oktave: Musik faellt zu den Hoehen ab, so bleiben die Balken lesbar
        self._ceil_decay = 10.0 ** (-CEIL_DECAY_DB_PER_SECOND / 20.0 / self.fps)
        self.on_event: Optional[Any] = None                    # fn(name, zeit, staerke) bei jedem Einsatz und Beat (Tests, Anzeige)
        self.reset()

    def reset(self) -> None:
        self._pending = np.zeros(0, dtype=np.float32)
        self._buf = np.zeros(WINDOW, dtype=np.float32)
        self._prev_c: Optional[np.ndarray] = None
        self._prev_cs: Optional[np.ndarray] = None
        self._frames = 0
        self._time = 0.0
        self._ceil = np.full(len(BAND_EDGES) - 1, CEIL_MIN)
        self.bands = np.zeros(len(BAND_EDGES) - 1)
        self._level_ceil = CEIL_MIN
        self.level = 0.0
        self._bar_ceil = CEIL_MIN
        self.spectrum = np.zeros(SPECTRUM_BARS)
        self.peak = 0.0
        self._clip_until = 0.0
        self._loud_until = 0.0
        # Einsaetze
        n = max(8, int(self.fps))
        self._flux_hist = {k: collections.deque(maxlen=n) for k in self.onset_spans}
        self._flux_peak = {k: FLUX_FLOOR[k] for k in self.onset_spans}
        self._peak_decay = math.exp(-self.dt / 4.0)
        self._last_event = {k: -1e9 for k in self.onset_spans}
        self._snare_pending: Optional[Tuple[float, float, int, float]] = None      # Snare-Kandidat: (Zeit, Fluss, Bilder bis zur Pruefung, Fluss danach)
        self.events = {k: (-1e9, 0.0) for k in self.onset_spans}          # Zeitpunkt, Staerke des letzten Einsatzes
        self._main_times: Deque[float] = collections.deque(maxlen=16)
        # Tempo
        self._env: Deque[float] = collections.deque(maxlen=int(TEMPO_HISTORY_SECONDS * self.fps))
        self._tempo_next = 0.0
        self.bpm_auto = 0.0
        self.confidence = 0.0
        self.locked = False
        self._pending_bpm = 0.0
        self._pending_hits = 0
        self._low_conf = 0
        self.phase = 0.0                                                    # Beats seit dem Start; ganzzahliger Teil = Beat-Zaehler
        self.beat_time = -1e9
        self._last_main = -1e9
        self._last_corr = -1e9
        self._taps: List[float] = []

    # ---- Eingang
    def process(self, samples: np.ndarray, now: float) -> None:
        """Ein Block Mono-Samples; `now` = Zeitpunkt des Blockendes (Sekunden, gleichmaessige Uhr)."""
        if samples.size == 0:
            return
        self._pending = np.concatenate((self._pending, samples.astype(np.float32, copy=False)))
        hop = self.hop
        total = len(self._pending)
        used = 0
        while total - used >= hop:
            block = self._pending[used:used + hop]
            used += hop
            self._buf = np.concatenate((self._buf[hop:], block)) if hop < WINDOW else block[-WINDOW:]
            self._time = now - (total - used) / self.rate
            self._frame(self._time)
        self._pending = self._pending[used:]

    def feed_silence(self, seconds: float, now: float) -> None:
        self.process(np.zeros(int(seconds * self.rate), dtype=np.float32), now)

    # ---- ein Bild
    def _frame(self, t: float) -> None:
        s = self.settings
        gain = float(s.get("gain", 1.0))
        self._frames += 1
        seg = self._buf
        recent = seg[-2 * self.hop:]
        peak = float(np.max(np.abs(recent))) * gain
        self.peak = peak
        if peak >= 0.99:
            self._clip_until = t + 1.0
        rms = float(np.sqrt(np.mean(recent * recent))) * gain
        if rms > SILENCE_RMS:
            self._loud_until = t + 1.0
        spec = np.abs(np.fft.rfft(seg * self.window)) * (self._scale * gain)
        power = spec * spec
        amps = np.sqrt(np.array([power[a:b].sum() for a, b in self.band_spans]))
        auto = bool(s.get("auto_gain", True))
        if auto:
            self._ceil = np.maximum(np.maximum(amps, self._ceil * self._ceil_decay), CEIL_MIN)
            ceil = self._ceil
            self._level_ceil = max(rms, self._level_ceil * self._ceil_decay, CEIL_MIN)
            level_ceil = self._level_ceil
        else:
            ceil, level_ceil = FIXED_CEIL, FIXED_CEIL
        release = 0.04 + 0.4 * float(s.get("smoothing", 0.5))
        a_up = 1.0 - math.exp(-self.dt / 0.008)
        a_down = 1.0 - math.exp(-self.dt / release)
        raw = np.clip(amps / ceil, 0.0, 1.0) ** GAMMA
        self.bands += np.where(raw > self.bands, (raw - self.bands) * a_up, (raw - self.bands) * a_down)
        raw_level = min(1.0, rms / level_ceil) ** GAMMA
        self.level += (raw_level - self.level) * (a_up if raw_level > self.level else a_down)
        # Spektrum fuer die Anzeige
        bar_amp = np.array([float(spec[a:b].max()) if b - a > 1 else float(np.interp((self._freqs[a] + self._freqs[min(b, len(self._freqs) - 1)]) / 2, self._freqs, spec))
                            for a, b in self._bar_spans]) * self._bar_tilt
        self._bar_ceil = max(float(bar_amp.max()), self._bar_ceil * self._ceil_decay, CEIL_MIN) if auto else FIXED_CEIL
        bars = np.clip((20.0 * np.log10(np.maximum(bar_amp, 1e-9) / self._bar_ceil) + 48.0) / 48.0, 0.0, 1.0)
        bar_down = 1.0 - math.exp(-self.dt / 0.12)
        self.spectrum += np.where(bars > self.spectrum, (bars - self.spectrum) * 0.8, (bars - self.spectrum) * bar_down)
        short = seg[-SHORT_WINDOW:] * self.window_short
        self._onsets(spec, np.abs(np.fft.rfft(short)) * (self._scale_short * gain), t)
        self._advance_phase(t)
        if t >= self._tempo_next and len(self._env) >= int(3.0 * self.fps):
            self._tempo_next = t + TEMPO_INTERVAL_SECONDS
            self._estimate_tempo(t)

    # ---- Einsaetze
    def _onsets(self, spec: np.ndarray, spec_short: np.ndarray, t: float) -> None:
        s = self.settings
        c = np.log1p(spec * 60.0)
        cs = np.log1p(spec_short * 60.0)
        prev, prev_short = self._prev_c, self._prev_cs
        self._prev_c, self._prev_cs = c, cs
        if prev is None or prev_short is None:
            return
        sens = float(s.get("sensitivity", 0.5))
        k = 3.2 - 2.2 * sens
        ratio = 4.2 - 2.4 * sens                                # ein Einsatz muss mehrfach ueber dem Durchschnitt liegen (gleichmaessiges Rauschen schwankt nur wenig)
        fluxes: Dict[str, float] = {}
        fired: Dict[str, float] = {}
        fired_at: Dict[str, float] = {}
        for name, (a, b) in self.onset_spans.items():
            now_c, was_c = (c, prev) if name == "kick" else (cs, prev_short)
            flux = float(np.maximum(now_c[a:b] - was_c[a:b], 0.0).mean())
            fluxes[name] = flux
            hist = self._flux_hist[name]
            peak = max(flux, self._flux_peak[name] * self._peak_decay, FLUX_FLOOR[name])
            self._flux_peak[name] = peak
            if name == "snare" and self._snare_pending is not None:
                # Ein Snare haelt an (Rauschen der Teppichspirale), der kurze Klick einer Bassdrum nicht: erst zwei Bilder spaeter entscheiden
                pt, pflux, left, after = self._snare_pending
                after += flux
                left -= 1
                if left <= 0:
                    self._snare_pending = None
                    if after >= 0.25 * pflux:
                        fired[name], fired_at[name] = 0.45 + 0.55 * min(1.0, pflux / peak), pt
                else:
                    self._snare_pending = (pt, pflux, left, after)
            elif len(hist) >= 8 and self._frames > int(0.3 * self.fps):
                arr = np.fromiter(hist, float, len(hist))
                arr = np.minimum(arr, float(np.percentile(arr, 85)))           # einzelne laute Schlaege sollen die Schwelle fuer leisere nicht hochziehen
                threshold = max(float(arr.mean()) + k * float(arr.std()), ratio * float(arr.mean()), 0.2 * peak, 0.5 * FLOOR_MIN[name])
                if flux > threshold and t - self._last_event[name] > self._refractory[name]:
                    if name == "snare":
                        self._snare_pending = (t, flux, 2, 0.0)
                        self._last_event[name] = t
                    else:
                        fired[name], fired_at[name] = 0.45 + 0.55 * min(1.0, flux / peak), t
            hist.append(flux)
        for name, strength in fired.items():
            when = fired_at[name]
            self._last_event[name] = when
            self.events[name] = (when, strength)
            if self.on_event is not None:
                self.on_event(name, when, strength)
        # Tempo-Huellkurve: die Einsaetze gewichtet (Bass tragend), jeder auf seinen eigenen Spitzenwert bezogen
        env = 1.0 * fluxes["kick"] / self._flux_peak["kick"] + 0.6 * fluxes["snare"] / self._flux_peak["snare"] + 0.25 * fluxes["hat"] / self._flux_peak["hat"]
        self._env.append(env)
        main = "kick" if "kick" in fired else ("snare" if "snare" in fired and not self._recent_kicks(t) else None)
        if main is not None:
            self._main_times.append(fired_at[main])
            self._on_main_onset(fired_at[main])

    def _recent_kicks(self, t: float) -> bool:
        return self.events["kick"][0] > t - 4.0

    # ---- Tempo
    def _estimate_tempo(self, t: float) -> None:
        n = len(self._env)
        x = np.fromiter(self._env, float, n)
        x -= x.mean()
        if float(x.std()) < 1e-3:
            self.confidence *= 0.8
            return
        size = 1 << int(math.ceil(math.log2(2 * n)))
        f = np.fft.rfft(x, size)
        ac = np.fft.irfft(f * np.conj(f))[:n]
        ac = ac / (ac[0] + 1e-12) * (n / (n - np.arange(n)))
        lo = int(self.fps * 60.0 / MAX_BPM)
        hi = min(n // 4 - 1, int(self.fps * 60.0 / MIN_BPM))
        if hi <= lo + 2:
            return
        lags = np.arange(lo, hi + 1)
        score = ac[lags].copy()
        for mult, weight in ((2, 0.5), (4, 0.25)):
            idx = lags * mult
            ok = idx < n
            score[ok] += weight * ac[idx[ok]]
        bpm_c = 60.0 * self.fps / lags
        prior = np.exp(-0.5 * (np.log2(bpm_c / PRIOR_BPM) / 0.6) ** 2)
        best = int(lags[int(np.argmax(score * prior))])

        def refine(centre: int) -> Optional[Tuple[float, float]]:
            a, b = max(1, centre - 3), min(n - 2, centre + 3)
            if b <= a:
                return None
            j = a + int(np.argmax(ac[a:b + 1]))
            if j <= 0 or j >= n - 1:
                return None
            y0, y1, y2 = ac[j - 1], ac[j], ac[j + 1]
            denom = y0 - 2 * y1 + y2
            shift = 0.5 * (y0 - y2) / denom if abs(denom) > 1e-12 else 0.0
            return j + max(-1.0, min(1.0, shift)), float(y1)

        estimates: List[Tuple[float, float]] = []
        for mult in (1, 2, 4):
            if best * mult + 4 >= n:
                break
            got = refine(best * mult)
            if got is not None and (mult == 1 or got[1] > 0.3 * (estimates[0][1] if estimates else 0.0)):
                estimates.append((got[0] / mult, got[1]))
        if not estimates:
            return
        weights = sum(max(w, 1e-6) for _, w in estimates)
        lag = sum(l * max(w, 1e-6) for l, w in estimates) / weights
        bpm = 60.0 * self.fps / lag
        confidence = float(max(0.0, min(1.0, estimates[0][1])))
        self.confidence += (confidence - self.confidence) * 0.5
        if confidence < 0.12:
            self._low_conf += 1
            if self._low_conf >= 4:
                self.locked = False
            return
        self._low_conf = 0
        if self.bpm_auto <= 0:
            self.bpm_auto = bpm
            self.locked = confidence >= 0.2
        elif abs(bpm - self.bpm_auto) <= 0.04 * self.bpm_auto:
            self.bpm_auto += (bpm - self.bpm_auto) * 0.3
            self._pending_hits = 0
            if confidence >= 0.2:
                self.locked = True
        else:                                                    # ein anderes Tempo erst uebernehmen, wenn es mehrmals hintereinander gefunden wird
            if self._pending_bpm > 0 and abs(bpm - self._pending_bpm) <= 0.04 * self._pending_bpm:
                self._pending_hits += 1
            else:
                self._pending_bpm, self._pending_hits = bpm, 1
            if self._pending_hits >= 3:
                self.bpm_auto, self._pending_hits = self._pending_bpm, 0
                self.locked = confidence >= 0.2

    def current_bpm(self) -> float:
        if self.settings.get("mode") == "manual":
            return float(self.settings.get("bpm", 120.0))
        return self.bpm_auto

    # ---- Beat-Position
    def _beat_running(self, t: float) -> bool:
        if self.settings.get("mode") == "manual":
            return True
        return self.locked and self.bpm_auto > 0 and t - self._last_main < 4.0

    def _emit_beat(self, t: float) -> None:
        self.beat_time = t
        if self.on_event is not None:
            self.on_event("beat", t, 1.0)

    def _advance_phase(self, t: float) -> None:
        if not self._beat_running(t):
            return
        new = self.phase + self.current_bpm() / 60.0 * self.dt
        if math.floor(new) > math.floor(self.phase):
            self._emit_beat(t)
        self.phase = new

    def _shift_phase(self, delta: float, t: float) -> None:
        floor_now = math.floor(self.phase)
        new = self.phase + delta
        if delta < 0:
            new = max(new, float(floor_now))                    # ein schon gezaehlter Beat wird nicht zurueckgenommen
        elif math.floor(new) > floor_now:
            self._emit_beat(t)
        self.phase = new

    def _on_main_onset(self, t: float) -> None:
        manual = self.settings.get("mode") == "manual"
        self._last_main = t
        if manual and not self.settings.get("phase_follow", True):
            return
        if not manual and not self.locked:                       # noch kein Tempo: jeder Bassdrum-Schlag ist ein Beat
            self.phase = math.floor(self.phase) + 1.0
            self._emit_beat(t)
            return
        frac = self.phase - math.floor(self.phase)
        err = frac if frac < 0.5 else frac - 1.0                 # Abstand zum naechsten Beat in Beats (-0,5 .. 0,5)
        limit = 0.22 if not manual else 0.15
        if abs(err) <= limit:
            self._last_corr = t
            self._shift_phase(-(0.3 if not manual else 0.12) * err, t)
        elif not manual and t - self._last_corr > 2.5:           # lange keine Uebereinstimmung: neu einrasten
            self._last_corr = t
            self.phase = math.floor(self.phase) + 1.0
            self._emit_beat(t)

    def tap(self, t: float) -> Optional[float]:
        """Ein Tipp aufs Tempo: gibt das neue Tempo zurueck (ab dem zweiten Tipp) und setzt den Beat auf diesen Zeitpunkt."""
        if self._taps and t - self._taps[-1] > 2.0:
            self._taps = []
        self._taps.append(t)
        self._taps = self._taps[-6:]
        self.phase = math.floor(self.phase) + 1.0
        self._emit_beat(t)
        if len(self._taps) < 2:
            return None
        gaps = [b - a for a, b in zip(self._taps[:-1], self._taps[1:])]
        return max(30.0, min(300.0, 60.0 / (sum(gaps) / len(gaps))))

    # ---- Ausgabe
    def outputs(self, now: float) -> Dict[str, Any]:
        """Alle Werte zum Zeitpunkt `now` (Impulse klingen abhaengig von `now` ab - unabhaengig davon, wie oft gelesen wird)."""
        s = self.settings
        latency = float(s.get("latency_ms", 0.0)) / 1000.0
        bpm = self.current_bpm()

        def pulse(t0: float, strength: float, tau: float) -> float:
            age = now - t0 + latency
            return strength * math.exp(-age / tau) if t0 > -1e8 and age >= 0 else 0.0

        beats = self.phase + latency * bpm / 60.0
        active = now < self._loud_until + 0.0
        kick = pulse(*self.events["kick"], KICK_TAU)
        snare = pulse(*self.events["snare"], SNARE_TAU)
        hat = pulse(*self.events["hat"], HAT_TAU)
        beat = pulse(self.beat_time, 1.0, BEAT_TAU) if (bpm > 0 and (self._beat_running(now) or s.get("mode") == "manual" or not self.locked)) else 0.0
        b = [float(v) for v in self.bands]
        values = {
            "a_active": 1.0 if active else 0.0, "a_level": float(self.level) if active else 0.0,
            "a_bass": max(b[0], b[1]), "a_mid": max(b[2], b[3], b[4]), "a_high": max(b[5], b[6], b[7]),
            "a_kick": kick, "a_snare": snare, "a_hat": hat, "a_beat": beat,
            "a_beat_phase": beats - math.floor(beats) if bpm > 0 else 0.0, "a_beat_count": float(math.floor(beats)) if bpm > 0 else 0.0,
            "a_bpm": float(bpm), "a_conf": 1.0 if s.get("mode") == "manual" else float(self.confidence) if self.locked else 0.0,
        }
        for i, v in enumerate(b, 1):
            values[f"a_b{i}"] = v if active else 0.0
        return {k: float(v) for k, v in values.items()}

    def display(self, now: float) -> Dict[str, Any]:
        """Stand fuer die Anzeige (Panel): die Variablen plus Spektrum, Spitzenpegel und Uebersteuerung."""
        values = self.outputs(now)
        return {"v": {k: round(v, 4) for k, v in values.items()}, "spectrum": [round(float(x), 3) for x in self.spectrum],
                "peak": round(min(1.5, self.peak), 3), "clip": now < self._clip_until, "locked": bool(self.locked)}


# ------------------------------------------------------------------------------------------------------------------ Demo-Signal
class DemoSignal:
    """Ein Schlagzeug-Loop (Bassdrum auf jedem Schlag, Snare auf 2 und 4, Hi-Hat dazwischen) als Audio - zum Ausprobieren ohne Musik und fuer Tests."""

    def __init__(self, rate: int) -> None:
        self.rate = int(rate)
        rng = np.random.default_rng(7)
        t = np.arange(int(0.30 * rate)) / rate
        sweep = 2 * np.pi * (45.0 * t + 105.0 * 0.03 * (1 - np.exp(-t / 0.03)))
        self.kick = (0.9 * np.sin(sweep) * np.exp(-t / 0.09)).astype(np.float32)
        t = np.arange(int(0.22 * rate)) / rate
        noise = np.diff(rng.standard_normal(len(t) + 1))
        self.snare = (1.4 * noise * np.exp(-t / 0.05) / 2.0 + 0.5 * np.sin(2 * np.pi * 190 * t) * np.exp(-t / 0.06)).astype(np.float32)
        t = np.arange(int(0.08 * rate)) / rate
        hat_noise = np.diff(np.diff(rng.standard_normal(len(t) + 2)))
        self.hat = (0.35 * hat_noise * np.exp(-t / 0.012) / 3.0).astype(np.float32)

    def render(self, bpm: float, start: int, count: int) -> np.ndarray:
        """`count` Samples ab Probe `start` (gleichmaessig ab 0)."""
        out = np.zeros(count, dtype=np.float32)
        step = self.rate * 60.0 / max(30.0, float(bpm))
        for shot, offset, every in ((self.kick, 0.0, 1), (self.snare, 1.0, 2), (self.hat, 0.5, 1)):
            length = len(shot)
            period = step * (2 if shot is self.snare else 1)
            first = math.ceil((start - length - offset * step) / period)
            k = first
            while True:
                s0 = int(round(offset * step + k * period))
                if s0 >= start + count:
                    break
                lo, hi = max(s0, start), min(s0 + length, start + count)
                if hi > lo:
                    out[lo - start:hi - start] += shot[lo - s0:hi - s0]
                k += 1
        return out * 0.8                                       # etwas unter Vollaussteuerung (sonst leuchtet die Uebersteuerungs-Anzeige dauernd)


# ------------------------------------------------------------------------------------------------------------------ Geraete und Engine
def list_devices() -> List[Dict[str, Any]]:
    """Alle Audio-Eingaenge, die Windows kennt: Mikrofone, Line-In, USB-Interfaces ("input") und der Systemton jedes Ausgabegeraets ("loopback"); dazu der Demo-Beat."""
    devices: List[Dict[str, Any]] = [{"id": "demo", "name": "Demo", "kind": "demo", "channels": 1, "rate": 48000, "default": False},
                                     {"id": "network", "name": "Network (API stream)", "kind": "network", "channels": 1, "rate": 16000, "default": False}]
    try:
        import pyaudiowpatch as pyaudio
    except Exception as exc:
        logger.warning("OC-3201 Audio-Aufnahme nicht verfuegbar: %s", exc)
        return devices
    pa = None
    portaudio_lock.LOCK.acquire()                         # PortAudio nie aus zwei Faeden gleichzeitig starten / beenden (Sprachsteuerung startet mit)
    try:
        pa = pyaudio.PyAudio()
        wasapi = pa.get_host_api_info_by_type(pyaudio.paWASAPI)
        default_in = wasapi.get("defaultInputDevice", -1)
        try:
            default_out_name = pa.get_device_info_by_index(wasapi.get("defaultOutputDevice", -1))["name"]
        except Exception:
            default_out_name = ""
        found: List[Dict[str, Any]] = []
        for index in range(pa.get_device_count()):
            info = pa.get_device_info_by_index(index)
            if info.get("hostApi") != wasapi["index"] or int(info.get("maxInputChannels", 0)) <= 0:
                continue
            loop = bool(info.get("isLoopbackDevice"))
            name = str(info["name"])
            base = name[:-len(" [Loopback]")] if name.endswith(" [Loopback]") else name
            found.append({
                "id": ("loopback:" if loop else "input:") + name, "name": base, "kind": "loopback" if loop else "input",
                "channels": int(info["maxInputChannels"]), "rate": int(info["defaultSampleRate"]), "index": index,
                "default": (index == default_in) if not loop else (base == default_out_name),
            })
        order = {"loopback": 0, "input": 1}
        found.sort(key=lambda d: (order[d["kind"]], not d["default"], d["name"].lower()))
        devices += found
    except Exception as exc:
        logger.warning("Audio-Geraete konnten nicht gelesen werden: %s", exc)
    finally:
        if pa is not None:
            try:
                pa.terminate()
            except Exception:
                pass
        portaudio_lock.LOCK.release()
    return devices


class AudioEngine:
    def __init__(self) -> None:
        self.config: Dict[str, Any] = dict(DEFAULTS)
        self._lock = threading.RLock()
        self._analyzer: Optional[AudioAnalyzer] = None
        self._pa: Any = None
        self._stream: Any = None
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._last_data = 0.0
        self._last_feed = 0.0
        self.running = False
        self.error = ""
        self.device_name = ""
        self.rate = 0
        self._tap_listeners: List[Any] = []
        self._events: Deque[str] = collections.deque(maxlen=256)         # Einsaetze und Beats seit dem letzten Abholen (Cue-Ausloeser)
        self._taps: List[Any] = []                                       # Abgriffe fn(name, staerke): sofort bei jedem Einsatz / Beat (Ereignis-Strom der REST-API); laufen im Audio-Thread, muessen kurz sein

    # ---- Einstellungen
    def configure(self, patch: Any) -> Dict[str, Any]:
        with self._lock:
            before = dict(self.config)
            self.config = clean_config(patch, self.config)
            if self._analyzer is not None:
                self._analyzer.settings = self.config
            if before.get("mode") == "manual" and self.config["mode"] == "auto" and self._analyzer is not None:
                self._analyzer.locked = False
            return dict(self.config)

    def load(self, raw: Any) -> None:
        with self._lock:
            self.config = clean_config(raw, dict(DEFAULTS))

    # ---- Quelle
    def start(self, device: Optional[str] = None) -> bool:
        """Oeffnet die Quelle (Standard: die gespeicherte). Gibt zurueck, ob sie laeuft; sonst steht der Grund in `error`."""
        self.stop()
        with self._lock:
            if device is not None:
                self.config["device"] = str(device)[:200]
            target = self.config.get("device", "")
            self.error = ""
            if not target:
                self.error = "no_device"
                return False
            self._stop.clear()
            self._last_data = self._last_feed = time.monotonic()
            if target == "network":                                   # Audio kommt als PCM ueber den WebSocket der API (z. B. ein ESP32 mit Mikrofon): feed_network()
                self.rate, self.device_name = 16000, "Network (API stream)"
                self._analyzer = AudioAnalyzer(self.rate, self.config)
                self._analyzer.on_event = self._queue_event
                self._thread = threading.Thread(target=self._watchdog, name="audio-network", daemon=True)       # ohne Daten rechnet die Analyse mit Stille weiter
                self._thread.start()
                self.running = True
                return True
            if target == "demo":
                self.rate, self.device_name = 48000, "Demo"
                self._analyzer = AudioAnalyzer(self.rate, self.config)
                self._analyzer.on_event = self._queue_event
                self._thread = threading.Thread(target=self._demo_loop, name="audio-demo", daemon=True)
                self._thread.start()
                self.running = True
                return True
            return self._open_device(target)

    def _open_device(self, target: str) -> bool:
        try:
            import pyaudiowpatch as pyaudio
        except Exception as exc:
            self.error = f"unavailable: {exc}"
            return False
        match = next((d for d in list_devices() if d["id"] == target and d["kind"] != "demo"), None)
        if match is None:
            self.error = "device_missing"
            return False
        portaudio_lock.LOCK.acquire()
        try:
            pa = pyaudio.PyAudio()
            channels = max(1, min(2, int(match["channels"])))
            rate = int(match["rate"])
            analyzer = AudioAnalyzer(rate, self.config)
            analyzer.on_event = self._queue_event

            def callback(data, frames, info, status):
                try:
                    block = np.frombuffer(data, dtype=np.float32)
                    mono = block.reshape(-1, channels).mean(axis=1) if channels > 1 else block
                    with self._lock:
                        if self._analyzer is analyzer:
                            analyzer.process(mono, time.monotonic())
                            self._last_data = self._last_feed = time.monotonic()
                except Exception:
                    logger.exception("Audio-Callback fehlgeschlagen")
                return (None, pyaudio.paContinue)

            stream = pa.open(format=pyaudio.paFloat32, channels=channels, rate=rate, input=True, input_device_index=int(match["index"]),
                             frames_per_buffer=analyzer.hop, stream_callback=callback)
        except Exception as exc:
            self.error = f"open_failed: {exc}"
            logger.warning("OC-3201 Audio-Quelle '%s' liess sich nicht oeffnen: %s", target, exc)
            try:
                pa.terminate()
            except Exception:
                pass
            return False
        finally:
            portaudio_lock.LOCK.release()
        self._pa, self._stream = pa, stream
        self._analyzer = analyzer
        self.rate, self.device_name = rate, match["name"]
        self._thread = threading.Thread(target=self._watchdog, name="audio-watchdog", daemon=True)
        self._thread.start()
        self.running = True
        return True

    def feed_network(self, samples: Any, rate: int) -> bool:
        """Ein Block Audio (Mono, -1..1) von aussen; nur wenn die Quelle "network" offen ist. Eine andere Abtastrate (8000-48000) baut die Analyse neu auf."""
        rate = int(rate)
        if not 8000 <= rate <= 48000:
            return False
        with self._lock:
            if not self.running or self.config.get("device") != "network":
                return False
            analyzer = self._analyzer
            if analyzer is None or analyzer.rate != rate:
                analyzer = AudioAnalyzer(rate, self.config)
                analyzer.on_event = self._queue_event
                self._analyzer = analyzer
                self.rate = rate
            now = time.monotonic()
            analyzer.process(np.asarray(samples, dtype=np.float32), now)
            self._last_data = self._last_feed = now
        return True

    def stop(self) -> None:
        self._stop.set()
        thread = self._thread
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=1.0)
        self._thread = None
        stream, pa = self._stream, self._pa
        self._stream = self._pa = None
        with portaudio_lock.LOCK:
            for action in (lambda: stream.stop_stream(), lambda: stream.close(), lambda: pa.terminate()):
                try:
                    action()
                except Exception:
                    pass
        with self._lock:
            self.running = False
            self._analyzer = None

    def _watchdog(self) -> None:
        """Loopback-Quellen liefern bei Stille oft gar keine Daten: dann rechnet die Analyse mit Stille weiter (Pegel fallen, Tempo laeuft aus)."""
        while not self._stop.wait(0.05):
            now = time.monotonic()
            with self._lock:
                analyzer = self._analyzer
                if analyzer is None:
                    return
                gap = now - self._last_data
                if gap > 0.08:
                    analyzer.feed_silence(min(gap, 0.25), now)
                    self._last_data = now

    def _demo_loop(self) -> None:
        analyzer = self._analyzer
        demo = DemoSignal(self.rate)
        start = time.monotonic()
        done = 0
        while not self._stop.wait(0.01):
            now = time.monotonic()
            target = int((now - start) * self.rate)
            if target - done < analyzer.hop:
                continue
            block = demo.render(float(self.config.get("demo_bpm", 120.0)), done, target - done)
            done = target
            with self._lock:
                if self._analyzer is not analyzer:
                    return
                analyzer.process(block, now)

    # ---- Bedienung
    def tap(self) -> Optional[float]:
        """Tempo antippen (Befehl `Tap`, Knopf im Panel): ab dem zweiten Tipp wechselt das Tempo auf "manuell" mit dem getippten Wert."""
        with self._lock:
            analyzer = self._analyzer
            if analyzer is None:
                analyzer = self._tap_analyzer = getattr(self, "_tap_analyzer", None) or AudioAnalyzer(48000, self.config)
            bpm = analyzer.tap(time.monotonic())
            if bpm is not None:
                self.config["mode"], self.config["bpm"] = "manual", round(bpm, 1)
            return bpm

    # ---- Ereignisse (fuer Cue-Ausloeser)
    def _queue_event(self, name: str, t: float, strength: float) -> None:
        self._events.append(name)
        for tap in self._taps:
            try:
                tap(name, strength)
            except Exception:
                pass

    def add_tap(self, callback: Any) -> None:
        if callback not in self._taps:
            self._taps.append(callback)

    def pop_events(self) -> List[str]:
        """Die Namen der Ereignisse seit dem letzten Aufruf (kick, snare, hat, beat); die Warteschlange ist danach leer."""
        out: List[str] = []
        try:
            while True:
                out.append(self._events.popleft())
        except IndexError:
            return out

    # ---- Lesen
    def values(self) -> Dict[str, float]:
        """Alle Audio-Variablen jetzt (fuer die Effekt-Engine); ohne laufende Quelle alles 0."""
        with self._lock:
            analyzer = self._analyzer
            if analyzer is None:
                if self.config.get("mode") == "manual":                  # ohne Quelle kann ein fester Tempo-Takt trotzdem laufen (Metronom)
                    return self._clock_values()
                return silent()
            return analyzer.outputs(time.monotonic())

    def _clock_values(self) -> Dict[str, float]:
        from app.audio_vars import demo_vars
        v = silent()
        bpm = float(self.config.get("bpm", 120.0))
        d = demo_vars(time.monotonic(), bpm)
        for key in ("a_beat", "a_beat_phase", "a_beat_count", "a_bpm", "a_conf"):
            v[key] = d[key]
        return v

    def snapshot(self) -> Dict[str, Any]:
        """Stand fuer das Panel und die API."""
        with self._lock:
            analyzer = self._analyzer
            now = time.monotonic()
            frame = analyzer.display(now) if analyzer is not None else {"v": {k: round(v, 4) for k, v in self.values().items()}, "spectrum": [0.0] * SPECTRUM_BARS, "peak": 0.0, "clip": False, "locked": False}
            frame.update({"running": self.running, "error": self.error, "device": self.device_name, "rate": self.rate, "mode": self.config["mode"]})
            return frame

    def status(self) -> Dict[str, Any]:
        return {"running": self.running, "error": self.error, "device": self.config.get("device", ""), "device_name": self.device_name, "rate": self.rate, "config": dict(self.config)}


audio_engine = AudioEngine()
