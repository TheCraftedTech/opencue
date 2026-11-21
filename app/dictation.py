# Copyright (C) 2026 Samuel Zenker
# SPDX-License-Identifier: GPL-3.0-or-later
"""
dictation.py
DIKTIEREN: Sprache -> Text fuer das Chat-Fenster des KI-Assistenten (und spaeter weitere Textfelder). Komplett offline nach dem einmaligen Laden des Sprachmodells.

Ablauf
  1. "Diktieren" im Chat -> POST /api/dictation/start: das Mikrofon der Konsole nimmt auf (Mikrofon aus den Einstellungen, sonst das Standard-Mikrofon von Windows).
     Waehrenddessen melden "dictation_level" (Pegel, Sekunden) an die Oberflaeche die Balkenanimation.
  2. "Stopp" -> POST /api/dictation/stop: die Aufnahme wird mit faster-whisper (Whisper-Modell, CPU, int8) in Text umgewandelt und zurueckgegeben. Die Oberflaeche setzt den Text
     in das Eingabefeld; abgeschickt wird von Hand.
Sprache
  Die Sprache der Oberflaeche (Deutsch / Englisch) ist die Sprache des Diktats - es gibt dafuer keine eigene Einstellung.
Modell
  Whisper "base" (schnell, ~145 MB) oder "small" (genauer, ~480 MB), Einstellung "Diktieren" bei der Sprachsteuerung. Das Modell wird beim ersten Diktat (oder ueber den Knopf in den
  Einstellungen) von Hugging Face geladen und liegt danach im Datenordner (models/whisper/<Name>); danach braucht Diktieren kein Internet mehr. Lizenz des Modells: MIT (OpenAI).
Einstellungen
  In der Sprach-Konfiguration (App-Config, Schluessel "voice"): dictation_device ("" = Standard-Mikrofon, sonst die Kennung aus der Geraeteliste), dictation_model ("fast" | "accurate").
Schnittstellen (nur an der Konsole selbst)
  GET  /api/dictation            Stand: state (idle | recording | downloading | transcribing | error), Pegel, Sekunden, Modelle (vorhanden / Groesse), Fehler
  POST /api/dictation/start      Aufnahme beginnen
  POST /api/dictation/stop       Aufnahme beenden und umschreiben -> {ok, text}
  POST /api/dictation/cancel     Aufnahme / Umschreiben verwerfen
  POST /api/dictation/download   das gewaehlte Modell jetzt laden
  GET  /api/audio/io             Uebersicht aller Ein- und Ausgaenge des Computers
Meldungen an alle Geraete: "dictation_state" (Stand wie oben), "dictation_level" ({level, seconds}).
"""
from __future__ import annotations

import asyncio
import logging
import os
import queue
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import numpy as np
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app import paths as _paths
from app import portaudio_lock
from app import remote

logger = logging.getLogger("opencue.dictation")
router = APIRouter()

RATE = 16000
MAX_SECONDS = 120                  # laengste Aufnahme (danach stoppt die Oberflaeche selbst)
MIN_SECONDS = 0.4                  # kuerzer = nichts gesagt
LEVEL_INTERVAL_S = 0.08
OPEN_ATTEMPTS = 3
OPEN_RETRY_S = 0.6
MODELS = {                         # Einstellung -> (Whisper-Name, Repository, ungefaehre Groesse in MB)
    "fast": ("base", "Systran/faster-whisper-base", 145),
    "accurate": ("small", "Systran/faster-whisper-small", 484),
}
DEFAULT_MODEL = "accurate"
PATTERNS = ["config.json", "preprocessor_config.json", "model.bin", "tokenizer.json", "vocabulary.*"]
# Fachwoerter der Lichtsteuerung als Vorgabe-Text: Whisper schreibt sie dann richtig (Cue statt Kju, Gobo, Dimmer ...)
PROMPTS = {"de": "OpenCue, Scheinwerfer, Cue, Cue-Liste, Dimmer, Gobo, Fixture, Blackout, Grand Master, Effekt, Variable.",
           "en": "OpenCue, fixtures, cue, cue list, dimmer, gobo, blackout, grand master, effect, variable.",
           "fr": "OpenCue, projecteurs, cue, liste de cues, dimmer, gobo, blackout, grand master, effet, variable.",
           "nl": "OpenCue, projectoren, cue, cuelijst, dimmer, gobo, blackout, grand master, effect, variabele.",
           "it": "OpenCue, apparecchi, cue, lista cue, dimmer, gobo, blackout, grand master, effetto, variabile.",
           "es": "OpenCue, proyectores, cue, lista de cues, dimmer, gobo, blackout, grand master, efecto, variable."}


def model_dir(setting: str) -> Path:
    return _paths.get_data_root() / "models" / "whisper" / MODELS.get(setting, MODELS[DEFAULT_MODEL])[0]


def model_present(setting: str) -> bool:
    folder = model_dir(setting)
    return (folder / "model.bin").is_file() and (folder / "config.json").is_file() and (folder / "tokenizer.json").is_file()


def clean_setting(value: Any) -> str:
    return value if value in MODELS else DEFAULT_MODEL


# ------------------------------------------------------------------------------------------------ Geraete (Uebersicht fuer die Einstellungen)
def list_io_devices() -> Dict[str, List[Dict[str, Any]]]:
    """Alle Ein- und Ausgaenge, die Windows (WASAPI) kennt: Mikrofone / Line-In ("inputs"), Ausgabegeraete ("outputs") und der Systemton jedes Ausgabegeraets ("loopbacks")."""
    out: Dict[str, List[Dict[str, Any]]] = {"inputs": [], "outputs": [], "loopbacks": []}
    try:
        import pyaudiowpatch as pyaudio
    except Exception as exc:
        logger.warning("Audio-Geraete nicht lesbar: %s", exc)
        return out
    with portaudio_lock.LOCK:
        pa = None
        try:
            pa = pyaudio.PyAudio()
            wasapi = pa.get_host_api_info_by_type(pyaudio.paWASAPI)
            default_in, default_out = wasapi.get("defaultInputDevice", -1), wasapi.get("defaultOutputDevice", -1)
            for index in range(pa.get_device_count()):
                info = pa.get_device_info_by_index(index)
                if info.get("hostApi") != wasapi["index"]:
                    continue
                name = str(info["name"])
                loop = bool(info.get("isLoopbackDevice"))
                item = {"name": name[:-len(" [Loopback]")] if loop and name.endswith(" [Loopback]") else name, "rate": int(info.get("defaultSampleRate", 0))}
                if loop:
                    out["loopbacks"].append({**item, "channels": int(info.get("maxInputChannels", 0)), "default": False})
                    continue
                if int(info.get("maxInputChannels", 0)) > 0:
                    out["inputs"].append({**item, "id": "input:" + name, "channels": int(info["maxInputChannels"]), "default": index == default_in})
                if int(info.get("maxOutputChannels", 0)) > 0:
                    out["outputs"].append({**item, "channels": int(info["maxOutputChannels"]), "default": index == default_out})
        except Exception as exc:
            logger.warning("Audio-Geraete konnten nicht gelesen werden: %s", exc)
        finally:
            if pa is not None:
                try:
                    pa.terminate()
                except Exception:
                    pass
    for key in out:
        out[key].sort(key=lambda d: (not d["default"], d["name"].lower()))
    return out


# ------------------------------------------------------------------------------------------------ Modell laden
def _make_progress(report: Callable[[float], None], expected_bytes: float):
    """tqdm-Klasse fuer huggingface_hub: zaehlt die geladenen Bytes aller Dateien zusammen und meldet sie als Prozent der erwarteten Groesse."""
    from tqdm.auto import tqdm

    class _Mute:
        def write(self, *_):
            return 0

        def flush(self):
            pass

    class Progress(tqdm):
        _bars: Dict[int, "Progress"] = {}
        _done = 0.0                                               # Bytes der schon abgeschlossenen Dateien

        def __init__(self, *args, **kwargs):
            kwargs["file"] = _Mute()                              # nichts auf die Konsole schreiben (der Balken muss weiterzaehlen, darum nicht "disable")
            super().__init__(*args, **kwargs)
            Progress._bars[id(self)] = self

        def update(self, n=1):
            result = super().update(n)
            try:
                loaded = Progress._done + sum(b.n for b in Progress._bars.values() if getattr(b, "unit", "") == "B")
                report(min(99.0, loaded / expected_bytes * 100.0))
            except Exception:
                pass
            return result

        def close(self):
            if Progress._bars.pop(id(self), None) is not None and getattr(self, "unit", "") == "B":
                Progress._done += self.n
            super().close()

    return Progress


def download_model(setting: str, report: Callable[[float], None]) -> Path:
    """Laedt das Modell nach models/whisper/<Name> (nur dort; der Hugging-Face-Zwischenspeicher bleibt aussen vor)."""
    from huggingface_hub import snapshot_download
    name, repo, _mb = MODELS[setting]
    target = model_dir(setting)
    target.mkdir(parents=True, exist_ok=True)
    snapshot_download(repo, local_dir=str(target), allow_patterns=PATTERNS, tqdm_class=_make_progress(report, _mb * 1024 * 1024))
    if not model_present(setting):
        raise RuntimeError("model_incomplete")
    return target


# ------------------------------------------------------------------------------------------------ Engine
def _without_pyav() -> None:
    """faster-whisper importiert PyAV nur, um Audio-DATEIEN zu dekodieren; OpenCue gibt ihm fertige Audio-Daten. Im gebauten Programm fehlt PyAV deshalb (spart ~20 MB im Installer): ein leeres Modul genuegt."""
    import sys
    import types
    try:
        import av  # noqa: F401
    except ImportError:
        sys.modules.setdefault("av", types.ModuleType("av"))


class DictationEngine:
    def __init__(self) -> None:
        self._transcribe_lock = threading.Lock()
        self.state = "idle"
        self.error = ""
        self.level = 0.0
        self.seconds = 0.0
        self.percent = 0.0                  # Fortschritt beim Laden des Modells
        self.model_setting = DEFAULT_MODEL
        self._lock = threading.RLock()
        self._blocks: List[np.ndarray] = []
        self._rate = RATE
        self._pa = None
        self._stream = None
        self._ticker: Optional[threading.Thread] = None
        self._stop_ticker = threading.Event()
        self._models: Dict[str, Any] = {}
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._broadcast: Optional[Callable[[Dict[str, Any]], Any]] = None
        self._generation = 0                # jede Aufnahme eine Nummer: ein "Abbrechen" macht eine laufende Umschreibung wirkungslos
        self._started = 0.0

    # ---- Anbindung an den Server
    def attach(self, loop: asyncio.AbstractEventLoop, broadcast: Callable[[Dict[str, Any]], Any]) -> None:
        self._loop, self._broadcast = loop, broadcast

    def _send(self, message: Dict[str, Any]) -> None:
        if self._loop is not None and self._broadcast is not None:
            try:
                asyncio.run_coroutine_threadsafe(self._broadcast(message), self._loop)
            except RuntimeError:
                pass

    def _set_state(self, state: str, error: str = "") -> None:
        self.state, self.error = state, error
        self._send({"type": "dictation_state", "payload": self.status()})

    def status(self) -> Dict[str, Any]:
        return {"state": self.state, "error": self.error, "level": round(self.level, 3), "seconds": round(self.seconds, 1), "percent": round(self.percent, 1),
                "limit_s": MAX_SECONDS, "model": self.model_setting,
                "models": {key: {"name": name, "mb": mb, "present": model_present(key)} for key, (name, _repo, mb) in MODELS.items()}}

    # ---- Aufnahme
    def start(self, device: str, model_setting: str) -> bool:
        """Mikrofon oeffnen und aufnehmen. False (Fehler im Stand), wenn es nicht klappt."""
        with self._lock:
            if self.state in ("recording", "transcribing", "downloading"):
                self.error = "busy"
                return False
            self.model_setting = clean_setting(model_setting)
            try:
                import pyaudiowpatch as pyaudio
            except Exception:
                self._set_state("error", "audio_unavailable")
                return False
            from app import voice
            mics = voice.list_microphones()
            mic = next((m for m in mics if m["id"] == device), None) if device else next((m for m in mics if m.get("default")), mics[0] if mics else None)
            if mic is None:
                self._set_state("error", "device_missing")
                return False
            channels = max(1, min(2, int(mic["channels"])))
            rate = int(mic["rate"])
            blocks: List[np.ndarray] = []
            t0 = time.monotonic()

            def callback(data, frames, time_info, status):
                block = np.frombuffer(data, dtype=np.float32)
                block = block.reshape(-1, channels).mean(axis=1) if channels > 1 else block.copy()
                if time.monotonic() - t0 < MAX_SECONDS + 5:
                    blocks.append(block)
                self.level = float(min(1.0, np.sqrt(np.mean(block * block)) * 4.0)) if len(block) else 0.0
                return (None, pyaudio.paContinue)

            pa = stream = None
            for attempt in range(OPEN_ATTEMPTS):
                if attempt:
                    time.sleep(OPEN_RETRY_S * attempt)
                with portaudio_lock.LOCK:
                    pa = pyaudio.PyAudio()
                    try:
                        stream = pa.open(format=pyaudio.paFloat32, channels=channels, rate=rate, input=True, input_device_index=int(mic["index"]),
                                         frames_per_buffer=max(256, int(rate * 0.05)), stream_callback=callback)
                        break
                    except Exception as exc:
                        logger.warning("Diktieren: Mikrofon '%s' liess sich nicht oeffnen (Versuch %d von %d): %s", mic["name"], attempt + 1, OPEN_ATTEMPTS, exc)
                        try:
                            pa.terminate()
                        except Exception:
                            pass
                        pa = None
            if stream is None:
                self._set_state("error", "open_failed")
                return False
            self._pa, self._stream, self._blocks, self._rate = pa, stream, blocks, rate
            self._generation += 1
            self._started = t0
            self.level, self.seconds, self.percent = 0.0, 0.0, 0.0
            self._stop_ticker.clear()
            self._ticker = threading.Thread(target=self._tick, args=(self._generation,), name="dictation-level", daemon=True)
            self._ticker.start()
            self._set_state("recording")
            logger.info("Diktieren: Aufnahme auf '%s' (%d Hz)", mic["name"], rate)
            return True

    def _tick(self, generation: int) -> None:
        while not self._stop_ticker.wait(LEVEL_INTERVAL_S):
            if generation != self._generation or self.state != "recording":
                return
            self.seconds = time.monotonic() - self._started
            self._send({"type": "dictation_level", "payload": {"level": round(self.level, 3), "seconds": round(self.seconds, 1)}})

    def _close_stream(self) -> np.ndarray:
        """Aufnahme schliessen; gibt den Ton als 16-kHz-Mono zurueck."""
        self._stop_ticker.set()
        with portaudio_lock.LOCK:
            stream, pa = self._stream, self._pa
            self._stream = self._pa = None
            for close in (lambda: stream and stream.stop_stream(), lambda: stream and stream.close(), lambda: pa and pa.terminate()):
                try:
                    close()
                except Exception:
                    pass
        blocks, self._blocks = list(self._blocks), []
        self.level = 0.0
        if not blocks:
            return np.zeros(0, dtype=np.float32)
        from app.voice import resample
        return resample(np.concatenate(blocks), self._rate)

    def cancel(self) -> None:
        with self._lock:
            self._generation += 1
            if self._stream is not None:
                self._close_stream()
            if self.state in ("recording", "transcribing", "downloading"):
                self._set_state("idle")

    # ---- Umschreiben
    def _load(self, setting: str):
        if setting in self._models:
            return self._models[setting]
        _without_pyav()
        from faster_whisper import WhisperModel
        threads = max(1, min(4, (os.cpu_count() or 2) // 2))              # nicht alle Kerne: DMX und Cues muessen weiter puenktlich laufen
        model = WhisperModel(str(model_dir(setting)), device="cpu", compute_type="int8", cpu_threads=threads, local_files_only=True)
        self._models = {setting: model}                                    # immer nur ein Modell im Speicher
        return model

    def ensure_model(self, setting: str) -> None:
        if model_present(setting):
            return
        self.percent = 0.0
        self._set_state("downloading")
        last = [0.0]

        def report(percent: float) -> None:
            self.percent = percent
            if percent - last[0] >= 1.0:
                last[0] = percent
                self._send({"type": "dictation_state", "payload": self.status()})

        download_model(setting, report)
        self.percent = 100.0

    def stop_and_transcribe(self, language: str) -> Dict[str, Any]:
        """Aufnahme beenden, Modell bei Bedarf laden und den Text liefern: {ok, text, error, seconds}. Laeuft in einem Faden (rechnet einige Sekunden)."""
        with self._lock:
            if self.state != "recording":
                return {"ok": False, "error": "not_recording", "text": ""}
            generation = self._generation
            audio = self._close_stream()
            setting = self.model_setting
            self._set_state("transcribing")
        seconds = len(audio) / RATE
        try:
            if seconds < MIN_SECONDS or float(np.max(np.abs(audio))) < 0.004:
                self._finish(generation, "idle")
                return {"ok": True, "text": "", "empty": True, "seconds": round(seconds, 1)}
            self.ensure_model(setting)
            if generation != self._generation:
                return {"ok": False, "error": "cancelled", "text": ""}
            self._set_state("transcribing")
            model = self._load(setting)
            lang = language if language in PROMPTS else "en"
            started = time.monotonic()
            segments, _info = model.transcribe(audio, language=lang, beam_size=3, vad_filter=True, vad_parameters={"min_silence_duration_ms": 500},
                                               condition_on_previous_text=False, temperature=0.0, initial_prompt=PROMPTS[lang])
            text = " ".join(s.text.strip() for s in segments).strip()
            logger.info("Diktieren: %.1f s Ton in %.1f s umgeschrieben (%s, %s)", seconds, time.monotonic() - started, MODELS[setting][0], lang)
            if generation != self._generation:
                return {"ok": False, "error": "cancelled", "text": ""}
            self._finish(generation, "idle")
            return {"ok": True, "text": text, "empty": not text, "seconds": round(seconds, 1)}
        except Exception as exc:
            logger.exception("Diktieren fehlgeschlagen")
            code = "download_failed" if self.state == "downloading" else "transcribe_failed"
            self._finish(generation, "error", code)
            return {"ok": False, "error": code, "detail": str(exc)[:200], "text": ""}

    def transcribe_samples(self, audio: np.ndarray, setting: str, language: str = "en", prompt: str = "", hotwords: str = "") -> Dict[str, Any]:
        """Eine fertige Aufnahme (16 kHz, Mono, float) umschreiben - fuer die Sprachbefehle (app/voice.py). Laedt KEIN Modell aus dem Netz: fehlt es, kommt {"ok": False, "error": "model_missing"}.
        Laeuft in einem Faden des Aufrufers; ein Modell wird von hoechstens einem Umschreiben zugleich benutzt."""
        setting = clean_setting(setting)
        seconds = len(audio) / RATE
        if seconds < MIN_SECONDS or float(np.max(np.abs(audio))) < 0.004:
            return {"ok": True, "text": "", "empty": True, "seconds": round(seconds, 1)}
        if not model_present(setting):
            return {"ok": False, "error": "model_missing", "text": ""}
        lang = language if language in PROMPTS else "en"
        try:
            with self._transcribe_lock:
                model = self._load(setting)
                started = time.monotonic()
                options = dict(language=lang, beam_size=3, vad_filter=True, vad_parameters={"min_silence_duration_ms": 400}, condition_on_previous_text=False, temperature=0.0,
                               initial_prompt=prompt or PROMPTS[lang])
                try:
                    segments, _info = model.transcribe(audio, hotwords=hotwords or None, **options)
                except TypeError:                                       # aeltere faster-whisper-Version ohne hotwords
                    segments, _info = model.transcribe(audio, **options)
                text = " ".join(s.text.strip() for s in segments).strip()
            logger.info("Sprachbefehl: %.1f s Ton in %.1f s umgeschrieben (%s): %r", seconds, time.monotonic() - started, MODELS[setting][0], text)
            return {"ok": True, "text": text, "empty": not text, "seconds": round(seconds, 1)}
        except Exception as exc:
            logger.exception("Umschreiben fehlgeschlagen")
            return {"ok": False, "error": "transcribe_failed", "detail": str(exc)[:200], "text": ""}

    def _finish(self, generation: int, state: str, error: str = "") -> None:
        if generation == self._generation:
            self._set_state(state, error)

    def download_only(self, setting: str) -> Dict[str, Any]:
        """Modell jetzt laden (Knopf in den Einstellungen)."""
        setting = clean_setting(setting)
        with self._lock:
            if self.state != "idle" and self.state != "error":
                return {"ok": False, "error": "busy"}
            self._generation += 1
            generation = self._generation
        try:
            self.ensure_model(setting)
            self._finish(generation, "idle")
            return {"ok": True}
        except Exception as exc:
            logger.exception("Sprachmodell konnte nicht geladen werden")
            self._finish(generation, "error", "download_failed")
            return {"ok": False, "error": "download_failed", "detail": str(exc)[:200]}


engine = DictationEngine()


def _state():
    from app.state_manager import state
    return state


def _local(request: Request) -> bool:
    return remote.is_local(request.client.host if request.client else None)


def _settings() -> Dict[str, str]:
    cfg = getattr(_state(), "voice_config", {}) or {}
    return {"device": str(cfg.get("dictation_device") or ""), "model": clean_setting(cfg.get("dictation_model"))}


@router.get("/api/dictation")
async def api_status(request: Request) -> JSONResponse:
    settings = _settings()
    engine.model_setting = settings["model"] if engine.state == "idle" else engine.model_setting
    return JSONResponse({**engine.status(), "local": _local(request)})


@router.post("/api/dictation/start")
async def api_start(request: Request) -> JSONResponse:
    if not _local(request):
        return JSONResponse({"ok": False, "error": "local_only"}, status_code=403)
    settings = _settings()
    ok = await asyncio.to_thread(engine.start, settings["device"], settings["model"])
    return JSONResponse({"ok": ok, "error": engine.error if not ok else "", **engine.status()})


@router.post("/api/dictation/stop")
async def api_stop(request: Request) -> JSONResponse:
    if not _local(request):
        return JSONResponse({"ok": False, "error": "local_only"}, status_code=403)
    result = await asyncio.to_thread(engine.stop_and_transcribe, _state().language)
    return JSONResponse(result)


@router.post("/api/dictation/cancel")
async def api_cancel(request: Request) -> JSONResponse:
    if not _local(request):
        return JSONResponse({"ok": False, "error": "local_only"}, status_code=403)
    await asyncio.to_thread(engine.cancel)
    return JSONResponse({"ok": True})


@router.post("/api/dictation/download")
async def api_download(request: Request) -> JSONResponse:
    try:
        body = await request.json()
    except ValueError:
        body = {}
    setting = clean_setting((body or {}).get("model") or _settings()["model"])
    result = await asyncio.to_thread(engine.download_only, setting)
    return JSONResponse(result)


@router.get("/api/audio/io")
async def api_io() -> JSONResponse:
    return JSONResponse(await asyncio.to_thread(list_io_devices))
