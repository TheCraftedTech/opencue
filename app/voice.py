# Copyright (C) 2026 Samuel Zenker
# SPDX-License-Identifier: GPL-3.0-or-later
"""
voice.py
Sprachsteuerung: das WECKWORT (Standard "OpenCue", englisch gesprochen: "open cue") - komplett offline.

Erkennung
  Vosk (Kaldi) mit dem kleinen englischen Modell aus defaults/voice/ (wird mit dem Programm ausgeliefert, ~70 MB, Apache-2.0). Der Erkenner bekommt eine
  GRAMMATIK, die nur das Weckwort und "[unk]" (alles andere) kennt - dadurch braucht es kein Training, jedes Wort aus dem Wortschatz des Modells geht, und
  gewoehnliche Rede faellt in "[unk]". Ausgeloest wird,
    - sobald das Zwischenergebnis ("partial") eine Weile stabil auf das Weckwort endet (schnell: ~0,5 s nach dem Wort; die Dauer haengt an der Empfindlichkeit),
    - oder spaetestens, wenn der Satz abgeschlossen ist und jedes Wort des Weckworts sicher genug erkannt wurde.
  Gemessen mit Windows-Sprachausgabe (scratchpad verify_voice_*.py): echte Weckwoerter stehen ~0,9 s stabil im Zwischenergebnis, Fehlhypothesen in normalen
  Saetzen ("open the doors") hoechstens 0,3 s. Klangverwandte Schreibweisen (cue/queue/q) NICHT zusaetzlich in die Grammatik: sie teilen sich sonst die
  Sicherheit (je ~33 %).
Mikrofon
  Eigenes, unabhaengig von der Audio-Analyse (leer = Standard-Mikrofon von Windows). Aufnahme ueber PyAudioWPatch (WASAPI) in der Abtastrate des Geraets,
  umgerechnet auf 16 kHz mono.
Sprachbefehle (nach dem Weckwort)
  Nach dem Weckwort schneidet die Erkennung den Ton mit: die letzten 4 s davor (ein Befehl im gleichen Atemzug "OpenCue blackout on" steht schon im Puffer) und alles danach, bis
  eine Pause von 0,9 s kommt (hoechstens 10 s; kommt nach dem Weckwort 1,8 s lang nichts, zaehlt nur der Puffer). Whisper (app/dictation.py, ENGLISCH, mit den Befehlswoertern als
  Hinweis) schreibt es auf, app/voice_commands.py macht daraus eine Zeile der Befehlszeile ("Fixture 5 At 79 Color Green"), und die wird SOFORT ausgefuehrt (wie getippt: Eintrag
  im Befehlsverlauf, alle Fenster folgen). Loeschen, "Clear Clear" und Ueberschreiben gehen nie per Sprache.
Meldungen
  "voice_wake" an alle Geraete ({phrase, confidence, at, source}) -> static/js/voice.js zeigt "Ich hoere ...". "voice_phase" ({phase: recording | thinking | done | error, text,
  heard, command, success, message, error}) begleitet den Befehl bis zum Ergebnis. "voice_state" bei Start/Stopp. Der Mikrofon-Knopf in der Menueleiste ist ein reiner
  Ein/Aus-Schalter der Sprachsteuerung (POST /api/voice/config {enabled}).
Einstellungen
  App-Config, Schluessel "voice": enabled, device, wake_word, sensitivity (0-100). Gesetzt werden sie nur ueber "Speichern & Anwenden" der Einstellungen
  (static/js/voice_settings.js) und nur an der Konsole selbst.
Schnittstellen
  GET  /api/voice[?devices=1]   Stand (laeuft, Fehler, Pegel, zuletzt verstanden/erkannt), auf Wunsch die Mikrofone
  POST /api/voice/check         {wake_word} -> {phrase, unknown}: passt das Wort zum Wortschatz? (fuer den Entwurf in den Einstellungen, nichts wird gespeichert)
  POST /api/voice/config        Einstellungen uebernehmen und speichern (nur lokal)
  POST /api/voice/trigger       Mikrofon-Knopf: wirkt wie das gesprochene Weckwort
Fehlt das Paket "vosk" oder das Modell, meldet der Stand das (error "vosk_missing" / "model_missing"); das Programm laeuft ohne Sprachsteuerung weiter.
"""
from __future__ import annotations

import asyncio
import collections
import json
import logging
import os
import queue
import re
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app import paths as _paths
from app import portaudio_lock
from app import remote

logger = logging.getLogger("opencue.voice")
router = APIRouter()

MODEL_NAME = "vosk-model-small-en-us-0.15"
RATE = 16000                       # das Modell erwartet 16 kHz mono
CHUNK_S = 0.1                      # so viel Ton geht je Schritt an den Erkenner (Takt der Zwischenergebnisse)
COOLDOWN_S = 1.5
RING_S = 4.0                       # so viel Ton vor dem Weckwort bleibt im Puffer (ein Befehl im gleichen Atemzug steht schon darin)
ONSET_WAIT_S = 1.8                 # nach dem Weckwort so lange auf den Befehl warten
END_SILENCE_S = 0.9                # Pause, die den Befehl beendet
MAX_CAPTURE_S = 10.0               # laengster Befehl
SPEECH_MIN_RMS = 0.012             # darunter gilt es als Stille (der Rauschpegel des Raums hebt die Schwelle an)
COMMAND_PROMPT = ("OpenCue. Fixture 5 at 79 percent, color green. Fixtures 1 thru 5 at full. Fixtures 10 thru 20 at 70. Fixture 1 thru 8 minus 4. Fixture 3 and 7 at 50. At at. Blackout on. Blackout off. Go cue 3. Cuelist main go. Master 80. "
                  "Pan minus 10 percent. Tilt 45. Zoom half. Gobo 40. Timecode play. BPM 128. RGB 255 0 0. Group front at full. Effect off. Back. Pause. Stop.")
COMMAND_HOTWORDS = "OpenCue blackout fixture fixtures cue cuelist dimmer gobo master thru at full color pan tilt zoom strobe timecode group effect"
OPEN_ATTEMPTS = 4                  # das Mikrofon oeffnen: so oft versuchen ...
OPEN_RETRY_S = 0.8                 # ... mit dieser Wartezeit mal Nummer des Versuchs dazwischen
DEFAULTS: Dict[str, Any] = {"enabled": False, "device": "", "wake_word": "OpenCue", "sensitivity": 60,
                            "dictation_device": "", "dictation_model": "accurate"}          # Diktieren (app/dictation.py): Mikrofon ("" = Standard) und Whisper-Modell ("fast" | "accurate")
WAKE_KEYS = ("enabled", "device", "wake_word", "sensitivity")                              # nur diese Werte betreffen die laufende Weckwort-Erkennung


MODEL_URL = "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip"       # offizielle Quelle (Apache-2.0), ~41 MB
MODEL_SHA256 = "30f26242c4eb449f948e42cb302dd7a686cb29a3423a8367f99ff41780942498"
MODEL_ZIP_SIZE = 41205931


def model_dir() -> Path:
    """Das Modell: zuerst im Datenordner (vom Programm nachgeladen: Einstellungen -> Triggerwort), sonst das mitgelieferte (Quelltext-Betrieb: defaults/voice)."""
    own = _paths.get_data_root() / "voice" / MODEL_NAME
    return own if own.is_dir() else _paths.defaults_dir() / "voice" / MODEL_NAME


class ModelDownload:
    """Laedt das kleine Sprachmodell (Vosk) bei Bedarf: Zustand idle | downloading | extracting | done | error, Fortschritt in Prozent. Pruefsumme, sicheres Entpacken, nie ein halbes Modell."""

    def __init__(self) -> None:
        self.state = "idle"
        self.percent = 0.0
        self.error = ""
        self._lock = threading.Lock()

    def status(self) -> Dict[str, Any]:
        return {"state": self.state, "percent": round(self.percent, 1), "error": self.error, "size": MODEL_ZIP_SIZE}

    def start(self) -> bool:
        with self._lock:
            if self.state in ("downloading", "extracting"):
                return False
            self.state, self.percent, self.error = "downloading", 0.0, ""
        threading.Thread(target=self._run, daemon=True, name="voice-model-download").start()
        return True

    def _run(self) -> None:
        import hashlib
        import shutil
        import tempfile
        import urllib.request
        import zipfile
        temp_zip = None
        staging = None
        try:
            target_root = _paths.get_data_root() / "voice"
            target_root.mkdir(parents=True, exist_ok=True)
            fd, temp_zip = tempfile.mkstemp(prefix="opencue-vosk-", suffix=".zip", dir=str(target_root))
            digest = hashlib.sha256()
            request = urllib.request.Request(MODEL_URL, headers={"User-Agent": "OpenCue"})
            with urllib.request.urlopen(request, timeout=30) as response, os.fdopen(fd, "wb") as handle:
                total = int(response.headers.get("Content-Length") or MODEL_ZIP_SIZE)
                done = 0
                while True:
                    block = response.read(1 << 18)
                    if not block:
                        break
                    handle.write(block)
                    digest.update(block)
                    done += len(block)
                    self.percent = min(99.0, 100.0 * done / max(1, total))
            if digest.hexdigest() != MODEL_SHA256:
                raise RuntimeError("checksum")
            self.state, self.percent = "extracting", 99.0
            staging = Path(tempfile.mkdtemp(prefix="opencue-vosk-", dir=str(target_root)))
            with zipfile.ZipFile(temp_zip) as archive:
                for member in archive.infolist():                                     # nichts ausserhalb des Zielordners schreiben
                    name = member.filename.replace("\\", "/")
                    if name.startswith("/") or ".." in name.split("/") or ":" in name:
                        raise RuntimeError("unsafe_archive")
                archive.extractall(staging)
            extracted = staging / MODEL_NAME
            if not (extracted / "am" / "final.mdl").exists():
                raise RuntimeError("bad_archive")
            final = target_root / MODEL_NAME
            if final.exists():
                shutil.rmtree(final, ignore_errors=True)
            os.replace(extracted, final)
            global _model
            with _model_lock:
                _model = None
            self.state, self.percent = "done", 100.0
            logger.info("Sprachmodell geladen: %s", final)
            try:                                                                       # war die Sprachsteuerung schon eingeschaltet: jetzt starten
                if engine.config.get("enabled"):
                    engine.apply(dict(engine.config))
            except Exception:                                                          # noqa: BLE001
                logger.debug("Sprachsteuerung nach dem Modell-Download nicht gestartet", exc_info=True)
        except Exception as exc:                                                       # noqa: BLE001
            self.state, self.error = "error", str(exc)[:200] or exc.__class__.__name__
            logger.warning("Sprachmodell konnte nicht geladen werden: %s", exc)
        finally:
            for leftover in (temp_zip, ):
                if leftover:
                    try:
                        os.unlink(leftover)
                    except OSError:
                        pass
            if staging:
                shutil.rmtree(staging, ignore_errors=True)


model_download = ModelDownload()


# ------------------------------------------------------------------------------------------------ Einstellungen und Weckwort
def normalize(raw: Any) -> Dict[str, Any]:
    raw = raw if isinstance(raw, dict) else {}
    out = dict(DEFAULTS)
    out["enabled"] = bool(raw.get("enabled", DEFAULTS["enabled"]))
    out["device"] = str(raw.get("device") or "")[:200]
    word = re.sub(r"\s+", " ", str(raw.get("wake_word") or "")).strip()[:40]
    out["wake_word"] = word or DEFAULTS["wake_word"]
    try:
        out["sensitivity"] = int(max(0, min(100, round(float(raw.get("sensitivity", DEFAULTS["sensitivity"]))))))
    except (TypeError, ValueError):
        out["sensitivity"] = DEFAULTS["sensitivity"]
    out["dictation_device"] = str(raw.get("dictation_device") or "")[:200]
    out["dictation_model"] = raw.get("dictation_model") if raw.get("dictation_model") in ("fast", "accurate") else DEFAULTS["dictation_model"]
    return out


def words_of(wake_word: str) -> List[str]:
    """'OpenCue' -> ['open', 'cue']; 'Hey Lights' -> ['hey', 'lights'] (Grossbuchstaben im Wort trennen, nur Buchstaben und Apostroph)."""
    spaced = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", wake_word)
    return [w for w in re.split(r"[^a-zA-Z']+", spaced.lower()) if w]


def confidence_needed(sensitivity: int) -> float:
    """Endergebnis: geforderte Sicherheit je Wort (Empfindlichkeit 0 = 0,95 ... 100 = 0,45)."""
    return round(0.95 - max(0, min(100, sensitivity)) / 100.0 * 0.5, 3)


def stable_chunks_needed(sensitivity: int) -> int:
    """Zwischenergebnis: so viele Schritte (je 0,1 s) muss das Weckwort stehen bleiben (Empfindlichkeit 0 = 8 ... 100 = 5; Standard 60 = 6).
    Gemessen: Fehlhypothesen in normalen Saetzen stehen hoechstens 3 Schritte, ein gesprochenes Weckwort ~9 - die Grenze liegt dazwischen."""
    return int(8 - max(0, min(100, sensitivity)) / 100.0 * 3 + 0.5)          # .5 rundet auf (wie die Anzeige in den Einstellungen)


# ------------------------------------------------------------------------------------------------ Modell (einmal geladen, ~0,5 s)
_model = None
_model_lock = threading.Lock()


def load_model():
    """Das Vosk-Modell; RuntimeError("vosk_missing" | "model_missing" | "model_failed")."""
    global _model
    with _model_lock:
        if _model is not None:
            return _model
        try:
            import vosk
        except Exception as exc:
            raise RuntimeError("vosk_missing") from exc
        if not (model_dir() / "am" / "final.mdl").exists():
            raise RuntimeError("model_missing")
        vosk.SetLogLevel(-1)
        try:
            _model = vosk.Model(str(model_dir()))
        except Exception as exc:
            raise RuntimeError("model_failed") from exc
        return _model


def check_wake_word(wake_word: str) -> Tuple[str, List[str]]:
    """(Phrase fuer die Grammatik, Woerter, die das Modell nicht kennt). Wirft RuntimeError, wenn kein Modell da ist."""
    model = load_model()
    words = words_of(wake_word)
    unknown = [w for w in words if model.vosk_model_find_word(w) < 0]
    return " ".join(words), unknown


def list_microphones() -> List[Dict[str, Any]]:
    """Nur echte Eingaenge (Mikrofone, Line-In, USB-Interfaces) - kein Systemton, keine Demo. Enthaelt Index, Kanaele und Abtastrate zum Oeffnen."""
    from app import audio_engine
    return [d for d in audio_engine.list_devices() if d.get("kind") == "input"]


# ------------------------------------------------------------------------------------------------ Erkennung
class WakeDetector:
    """Wertet die Ergebnisse des Vosk-Erkenners aus (ohne Mikrofon testbar): feed() bekommt 16-kHz-PCM, ruft on_wake(phrase, confidence) auf."""

    def __init__(self, model, phrase: str, sensitivity: int, on_wake: Callable[[str, float], None]) -> None:
        import vosk
        self.phrase = phrase
        self.parts = phrase.split()
        self.min_conf = confidence_needed(sensitivity)
        self.min_stable = stable_chunks_needed(sensitivity)
        self.on_wake = on_wake
        self.recognizer = vosk.KaldiRecognizer(model, RATE, json.dumps([phrase, "[unk]"]))
        self.recognizer.SetWords(True)
        self.stable = 0
        self.last_text = ""
        self.last_heard_s: Optional[float] = None      # Sekunden, die das Weckwort beim Ausloesen stabil stand (nur beim schnellen Weg ueber das Zwischenergebnis)

    def feed(self, pcm: bytes) -> None:
        if self.recognizer.AcceptWaveform(pcm):
            self.stable = 0
            self._final(json.loads(self.recognizer.Result()))
            return
        partial = json.loads(self.recognizer.PartialResult()).get("partial", "")
        self.stable = self.stable + 1 if partial.endswith(self.phrase) else 0
        if self.stable >= self.min_stable:
            self._wake(1.0)

    def _final(self, result: Dict[str, Any]) -> None:
        text = str(result.get("text", "")).strip()
        if text:
            self.last_text = text
        words = result.get("result") or []
        n = len(self.parts)
        for i in range(len(words) - n + 1):
            window = words[i:i + n]
            if [w.get("word") for w in window] == self.parts:
                confidence = min(float(w.get("conf", 0.0)) for w in window)
                if confidence >= self.min_conf:
                    self._wake(confidence)
                return

    def _wake(self, confidence: float) -> None:
        # Die "Sicherheit" des Erkenners ist mit einer festen Grammatik immer 1,0 (gemessen) und sagt nichts aus. Aussagekraeftig ist, wie lange das Weckwort stabil stand.
        self.last_heard_s = round(self.stable * CHUNK_S, 1) if self.stable else None
        self.stable = 0
        self.recognizer.Reset()                              # ein Weckwort loest einmal aus (der Rest des Satzes gehoert dem naechsten Schritt)
        self.last_text = self.phrase
        self.on_wake(self.phrase, confidence)


class VoiceEngine:
    """Haelt das Mikrofon offen und fuettert den WakeDetector in einem eigenen Faden."""

    def __init__(self) -> None:
        self.config: Dict[str, Any] = dict(DEFAULTS)
        self.running = False
        self.suspended = False                 # Bedienmodus der Konsole: das Mikrofon bleibt zu, die Einstellung "an" bleibt erhalten
        self.error = ""
        self.phrase = ""
        self.device_name = ""
        self.level = 0.0
        self.last_wake: Optional[Dict[str, Any]] = None
        self._detector: Optional[WakeDetector] = None
        self._pa = None
        self._stream = None
        self._queue: "queue.Queue[np.ndarray]" = queue.Queue(maxsize=100)
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.RLock()
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._broadcast: Optional[Callable[[Dict[str, Any]], Any]] = None
        self._last_fire = 0.0
        self._ring: "collections.deque[np.ndarray]" = collections.deque(maxlen=int(RING_S / CHUNK_S))
        self._mode = "listen"                  # listen (Weckwort suchen) | capture (Befehl aufnehmen) | busy (wird umgeschrieben / ausgefuehrt)
        self._cap: Optional[Dict[str, Any]] = None
        self._want_capture = False
        self.phase = "idle"
        self.last_command: Optional[Dict[str, Any]] = None
        self.command_runner: Optional[Callable[[str], Any]] = None      # async Funktion: Befehlszeile ausfuehren -> {success, message} (setzt der Server)

    # ---- Anbindung an den Server
    def attach(self, loop: asyncio.AbstractEventLoop, broadcast: Callable[[Dict[str, Any]], Any]) -> None:
        self._loop, self._broadcast = loop, broadcast

    def _send(self, message: Dict[str, Any]) -> None:
        if self._loop is not None and self._broadcast is not None:
            try:
                asyncio.run_coroutine_threadsafe(self._broadcast(message), self._loop)
            except RuntimeError:
                pass

    def status(self) -> Dict[str, Any]:
        return {"config": dict(self.config), "running": self.running, "suspended": self.suspended, "error": self.error, "phrase": self.phrase, "device": self.device_name,
                "level": round(self.level, 3), "last_wake": self.last_wake, "last_heard": self._detector.last_text if self._detector else "", "phase": self.phase, "last_command": self.last_command,
                "model": MODEL_NAME, "model_present": (model_dir() / "am" / "final.mdl").exists(), "model_download": model_download.status()}

    # ---- Ein / Aus
    def apply(self, raw: Any) -> Dict[str, Any]:
        """Neue Einstellungen uebernehmen; ist die Sprachsteuerung an, startet die Erkennung (neu)."""
        with self._lock:
            self.stop(announce=False)
            self.config = normalize(raw)
            self.error = ""
            self._mode, self._cap, self._want_capture = "listen", None, False
            self._ring.clear()
            if self.config["enabled"]:
                self.start()
        self._send({"type": "voice_state", "payload": self.status()})
        return self.status()

    def suspend(self, on: bool) -> None:
        """Bedienmodus an der Konsole: Sprachsteuerung stoppen und gesperrt halten; beim Verlassen wieder starten, wenn sie eingeschaltet ist."""
        self.suspended = bool(on)
        if on:
            self.stop()
        elif self.config.get("enabled"):
            self.start()
        self._send({"type": "voice_state", "payload": self.status()})

    def start(self) -> bool:
        with self._lock:
            if self.suspended:
                return False
            if self.running:
                return True
            try:
                phrase, unknown = check_wake_word(self.config["wake_word"])
            except RuntimeError as exc:
                self.error = str(exc)
                return False
            if unknown or not phrase:
                self.error = "wake_word_unknown"
                return False
            mics = list_microphones()
            target = self.config["device"]
            mic = next((m for m in mics if m["id"] == target), None) if target else next((m for m in mics if m.get("default")), mics[0] if mics else None)
            if mic is None:
                self.error = "device_missing"
                return False
            try:
                import pyaudiowpatch as pyaudio
            except Exception:
                self.error = "audio_unavailable"
                return False
            channels = max(1, min(2, int(mic["channels"])))
            rate = int(mic["rate"])
            q: "queue.Queue[np.ndarray]" = queue.Queue(maxsize=100)

            def callback(data, frames, time_info, status):
                try:
                    block = np.frombuffer(data, dtype=np.float32)
                    q.put_nowait(block.reshape(-1, channels).mean(axis=1) if channels > 1 else block.copy())
                except queue.Full:
                    pass
                return (None, pyaudio.paContinue)

            pa = stream = None
            last_error: Optional[Exception] = None
            for attempt in range(OPEN_ATTEMPTS):
                if attempt:
                    time.sleep(OPEN_RETRY_S * attempt)                  # direkt nach dem Programmstart ist das Geraet oft noch nicht bereit ("Unanticipated host error")
                with portaudio_lock.LOCK:
                    pa = pyaudio.PyAudio()
                    try:
                        stream = pa.open(format=pyaudio.paFloat32, channels=channels, rate=rate, input=True, input_device_index=int(mic["index"]),
                                         frames_per_buffer=max(256, int(rate * CHUNK_S)), stream_callback=callback)
                        break
                    except Exception as exc:
                        last_error = exc
                        logger.warning("OC-3202 Sprachsteuerung: Mikrofon '%s' liess sich nicht oeffnen (Versuch %d von %d): %s", mic["name"], attempt + 1, OPEN_ATTEMPTS, exc)
                        try:
                            pa.terminate()
                        except Exception:
                            pass
                        pa = None
            if stream is None:
                self.error = "open_failed"
                return False
            self._detector = WakeDetector(load_model(), phrase, self.config["sensitivity"], self._on_wake)
            self._pa, self._stream, self._queue = pa, stream, q
            self.phrase, self.device_name = phrase, mic["name"]
            self._stop.clear()
            self._thread = threading.Thread(target=self._run, args=(rate,), name="voice-wake", daemon=True)
            self._thread.start()
            self.running = True
            logger.info("Sprachsteuerung hoert zu (%s, %d Hz) auf '%s'", mic["name"], rate, phrase)
            return True

    def stop(self, announce: bool = True) -> None:
        with self._lock:
            self._stop.set()
            stream, pa, thread = self._stream, self._pa, self._thread
            self._stream = self._pa = self._thread = None
            was = self.running
            self.running = False
            self.level = 0.0
        with portaudio_lock.LOCK:
            for close in (lambda: stream and stream.stop_stream(), lambda: stream and stream.close(), lambda: pa and pa.terminate()):
                try:
                    close()
                except Exception:
                    pass
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=2)
        if was and announce:
            self._send({"type": "voice_state", "payload": self.status()})

    # ---- Aufnahme -> Erkenner (eigener Faden)
    def _run(self, rate: int) -> None:
        detector = self._detector
        step = int(RATE * CHUNK_S)
        pending = np.zeros(0, dtype=np.float32)
        while not self._stop.is_set():
            try:
                block = self._queue.get(timeout=0.3)
            except queue.Empty:
                continue
            self.level = float(min(1.0, np.sqrt(np.mean(block * block)) * 4.0)) if len(block) else 0.0
            pending = np.concatenate([pending, resample(block, rate)])
            while len(pending) >= step:
                chunk, pending = pending[:step], pending[step:]
                chunk = np.clip(chunk, -1.0, 1.0)
                self._ring.append(chunk)
                try:
                    if self._mode == "listen":
                        detector.feed((chunk * 32767).astype("<i2").tobytes())
                        if self._want_capture and self._mode == "listen":      # das Weckwort kam (gesprochen oder ueber die Schnittstelle)
                            self._begin_capture()
                    elif self._mode == "capture":
                        self._capture_step(chunk)
                except Exception:
                    logger.exception("Sprachsteuerung: Erkennung fehlgeschlagen")
                    self._mode, self._cap, self._want_capture = "listen", None, False

    # ---- Sprachbefehl: nach dem Weckwort aufnehmen -> Whisper -> Befehlszeile -> ausfuehren
    def _set_phase(self, phase: str, **info: Any) -> None:
        self.phase = phase
        self._send({"type": "voice_phase", "payload": {"phase": phase, **info}})

    def _begin_capture(self) -> None:
        self._want_capture = False
        pre = list(self._ring)
        rms = [float(np.sqrt(np.mean(c * c))) for c in pre] or [0.0]
        noise = float(np.percentile(rms, 20))                              # Rauschpegel des Raums: die leisesten Stellen der letzten Sekunden
        self._cap = {"pre": pre, "post": [], "threshold": max(SPEECH_MIN_RMS, noise * 2.5), "speech": False, "silence": 0.0, "elapsed": 0.0}
        self._mode = "capture"
        self._set_phase("recording")

    def _capture_step(self, chunk: np.ndarray) -> None:
        cap = self._cap
        cap["post"].append(chunk)
        cap["elapsed"] += CHUNK_S
        if float(np.sqrt(np.mean(chunk * chunk))) > cap["threshold"]:
            cap["speech"], cap["silence"] = True, 0.0
        else:
            cap["silence"] += CHUNK_S
        done = (cap["speech"] and cap["silence"] >= END_SILENCE_S) or (not cap["speech"] and cap["elapsed"] >= ONSET_WAIT_S) or cap["elapsed"] >= MAX_CAPTURE_S
        if not done:
            return
        audio = np.concatenate(cap["pre"] + cap["post"]) if (cap["pre"] or cap["post"]) else np.zeros(0, dtype=np.float32)
        self._cap = None
        self._mode = "busy"
        self._set_phase("thinking")
        threading.Thread(target=self._process, args=(audio,), name="voice-command", daemon=True).start()

    def _process(self, audio: np.ndarray) -> None:
        from app import dictation, voice_commands
        info: Dict[str, Any] = {}
        try:
            result = dictation.engine.transcribe_samples(audio, self.config.get("dictation_model"), "en", COMMAND_PROMPT, COMMAND_HOTWORDS)
            if not result.get("ok"):
                self._set_phase("error", error=result.get("error", "transcribe_failed"))
                return
            if result.get("empty"):
                self._set_phase("error", error="nothing_heard")
                return
            parsed = voice_commands.interpret(result["text"], words_of(self.config["wake_word"]))
            info = {"text": result["text"], "heard": parsed["heard"], "command": parsed["command"], "notes": parsed.get("notes", [])[:6]}
            if parsed["blocked"]:
                self.last_command = {**info, "success": False, "message": "blocked: " + parsed["blocked"]}
                self._set_phase("error", error="blocked", blocked=parsed["blocked"], **info)
                return
            if not parsed["command"]:
                self.last_command = {**info, "success": False, "message": "no command"}
                self._set_phase("error", error="no_command", **info)
                return
            outcome = self._run_command(parsed["command"])
            self.last_command = {**info, "success": bool(outcome.get("success")), "message": str(outcome.get("message", "")), "at": time.strftime("%H:%M:%S")}
            self._set_phase("done", success=bool(outcome.get("success")), message=str(outcome.get("message", "")), **info)
        except Exception:
            logger.exception("Sprachbefehl fehlgeschlagen")
            self._set_phase("error", error="failed", **info)
        finally:
            self._mode = "listen"
            self._ring.clear()
            self._last_fire = time.monotonic()                              # kurze Sperre: das Echo des Befehls loest kein neues Weckwort aus
            if self._detector is not None:
                try:
                    self._detector.recognizer.Reset()
                except Exception:
                    pass

    def _run_command(self, command: str) -> Dict[str, Any]:
        """Die Befehlszeile im Server ausfuehren (wie ein getippter Befehl) und auf das Ergebnis warten."""
        if self.command_runner is None or self._loop is None:
            return {"success": False, "message": "not connected"}
        future = asyncio.run_coroutine_threadsafe(self.command_runner(command), self._loop)
        return future.result(timeout=20)

    def _on_wake(self, phrase: str, confidence: float) -> None:
        self.fire(phrase, confidence, "voice", self._detector.last_heard_s if self._detector else None)

    def fire(self, phrase: str, confidence: float, source: str, heard_s: Optional[float] = None) -> Optional[Dict[str, Any]]:
        now = time.monotonic()
        if (source == "voice" and now - self._last_fire < COOLDOWN_S) or self._mode != "listen":
            return None
        self._last_fire = now
        if self.running and self._mode == "listen":
            self._want_capture = True                                       # die Aufnahme beginnt im Audio-Faden (nach dem naechsten Block)
        info = {"phrase": phrase, "confidence": round(confidence, 3), "heard_s": heard_s, "at": time.strftime("%H:%M:%S"), "source": source}
        self.last_wake = info
        logger.info("Weckwort: '%s' (%s, stabil %s s)", phrase, source, heard_s)
        self._send({"type": "voice_wake", "payload": info})
        return info


def resample(block: np.ndarray, rate: int) -> np.ndarray:
    """Lineare Umrechnung eines Blocks auf 16 kHz (fuer Sprache ausreichend; die Bloecke sind gross genug, dass die Fugen nicht stoeren)."""
    if rate == RATE or not len(block):
        return block.astype(np.float32)
    count = max(1, int(round(len(block) * RATE / rate)))
    return np.interp(np.linspace(0, len(block) - 1, count), np.arange(len(block)), block).astype(np.float32)


engine = VoiceEngine()


def _state():
    from app.state_manager import state
    return state


def load_from_config() -> None:
    """Beim Programmstart: gespeicherte Einstellungen uebernehmen und ggf. zuhoeren."""
    if (getattr(_state(), "voice_config", {}) or {}).get("enabled"):
        time.sleep(1.0)                                  # die Audio-Geraete von Windows brauchen kurz nach dem Start einen Moment
    engine.apply(getattr(_state(), "voice_config", {}) or {})


def _is_local(request: Request) -> bool:
    return remote.is_local(request.client.host if request.client else None)


async def _body(request: Request) -> Dict[str, Any]:
    try:
        body = await request.json()
    except ValueError:
        return {}
    return body if isinstance(body, dict) else {}


@router.get("/api/voice")
async def api_status(request: Request) -> JSONResponse:
    data = engine.status()
    if request.query_params.get("devices"):
        mics = await asyncio.to_thread(list_microphones)
        data["microphones"] = [{"id": m["id"], "name": m["name"], "default": bool(m.get("default"))} for m in mics]
    return JSONResponse(data)


@router.post("/api/voice/model/download")
async def api_model_download() -> JSONResponse:
    """Das Sprachmodell laden (nur wenn es fehlt); der Fortschritt steht in GET /api/voice (model_download)."""
    if (model_dir() / "am" / "final.mdl").exists():
        return JSONResponse({"ok": True, "present": True})
    started = model_download.start()
    return JSONResponse({"ok": True, "started": started, "model_download": model_download.status()})


@router.post("/api/voice/check")
async def api_check(request: Request) -> JSONResponse:
    word = normalize({"wake_word": (await _body(request)).get("wake_word")})["wake_word"]
    try:
        phrase, unknown = await asyncio.to_thread(check_wake_word, word)
    except RuntimeError as exc:
        return JSONResponse({"ok": False, "error": str(exc), "phrase": " ".join(words_of(word)), "unknown": []})
    return JSONResponse({"ok": not unknown and bool(phrase), "phrase": phrase, "unknown": unknown})


@router.post("/api/voice/config")
async def api_config(request: Request) -> JSONResponse:
    config = normalize({**engine.config, **(await _body(request))})
    try:
        if all(config[k] == engine.config.get(k) for k in WAKE_KEYS):             # nur Diktier-Einstellungen geaendert: die laufende Weckwort-Erkennung nicht neu starten
            engine.config = config
            status = engine.status()
        else:
            status = await asyncio.to_thread(engine.apply, config)
    except Exception as exc:                                         # Einstellungen werden trotzdem gespeichert; der Fehler steht im Stand
        logger.exception("Sprachsteuerung: Einstellungen anwenden fehlgeschlagen")
        engine.error = f"apply_failed: {exc}"
        status = engine.status()
    state = _state()
    state.voice_config = config
    state.save_app_config()
    return JSONResponse({"ok": True, **status})


@router.post("/api/voice/trigger")
async def api_trigger() -> JSONResponse:
    info = engine.fire(" ".join(words_of(engine.config["wake_word"])), 1.0, "button")
    return JSONResponse({"ok": True, "wake": info})
