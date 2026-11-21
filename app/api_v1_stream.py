# Copyright (C) 2026 Samuel Zenker
# SPDX-License-Identifier: GPL-3.0-or-later
"""
api_v1_stream.py
REST-API (Teil 4): der WebSocket-Strom  `ws://<Konsole>/api/v1/ws`  fuer Hardware und schnelle Anwendungen (ESP32, Arduino, Raspberry Pi, TouchOSC-Bruecken, eigene Programme).
Eine Verbindung bleibt offen, beide Seiten schicken kleine JSON-Nachrichten (Textrahmen) - ohne die Kosten einer neuen HTTP-Anfrage je Wert:

  Hardware -> OpenCue   joystick   Knueppel (x / y, -1..1): RELATIV = Auslenkung bestimmt die Geschwindigkeit (innen genau, aussen schnell, mit Totmann-Zeit), oder "position" = absolut
                        set        Werte setzen: absolut (Prozent) oder relativ (Prozentpunkte dazu), fuer Scheinwerfer / Gruppe / Auswahl
                        select, cmd, cue, master, blackout, dmx, tap       wie die REST-Routen
                        audio_in + Binaerrahmen             Audio (PCM s16le) von einem Mikrofon am Geraet -> Audio-Analyse von OpenCue (Quelle "network")
  OpenCue -> Hardware   audio      Audio-Variablen (a_level, a_bass, a_beat ...) mit bis zu 60 Hz
                        dmx        geaenderte DMX-Kanaele eines Universums (nur Aenderungen) mit bis zu 60 Hz
                        fixtures   Live-Werte der Scheinwerfer (pan, tilt, dimmer, color ...) bei Aenderung
                        event      Ereignisse (cue, blackout, master, timecode, selection ... wie `GET /events`)

Anmeldung wie bei den HTTP-Routen (Token mit Berechtigungen; `app/api_v1.py: authenticate`): im Kopf `Authorization: Bearer <token>` / `X-API-Key`, in der Adresse
`?access_token=<token>` (einfach fuer Mikrocontroller) oder als erste Nachricht `{"op": "auth", "token": "oc_..."}` (binnen 5 s). Jede Nachricht verlangt dieselbe Berechtigung wie die
entsprechende HTTP-Route (joystick / set / select: write.programmer, cmd: write.command, cue: write.cue, master / blackout: write.blackout, dmx: write.dmx, audio_in / tap: write.audio;
Abonnements: audio / event: read.status, dmx / fixtures: read.dmx). Ein Joystick-Knueppel ohne Nachrichten (Kabel ab, WLAN weg) bleibt nach `timeout_ms` (Standard 500 ms) stehen.
"""
from __future__ import annotations

import asyncio
import json
import uuid
import logging
import math
import time
from typing import Any, Dict, List, Optional, Set

from fastapi import WebSocket, WebSocketDisconnect

from app import remote
from app.api_v1 import API_PREFIX, ApiError, CAPABILITIES, _cue_command, _message, _note_failure, _run_command, _set_raw, _srv, authenticate, router, store
from app.api_v1_manage import PCT_ATTRS
from app.api_v1_system import Targets, _clean_deltas, _resolve_targets, current_value, hub, relative_values
from app.version import APP_NAME, APP_VERSION

logger = logging.getLogger("opencue.api.ws")

MAX_CONNECTIONS = 10
AUTH_TIMEOUT_S = 5.0
SEND_TIMEOUT_S = 5.0                              # ein Client, der so lange nichts liest (voller Puffer), wird getrennt - sonst haengt seine Verbindung fuer immer und belegt einen der Plaetze
MAX_TEXT = 8192                                  # laengste Textnachricht (Bytes)
MAX_BINARY = 65536                               # laengster Audio-Rahmen (Bytes)
RATE_PER_S = 300.0                               # erlaubte Nachrichten je Sekunde (Dauerlast) ...
RATE_BURST = 600.0                               # ... mit Spitzen bis zu dieser Zahl
PUSH_BASE_S = 0.01                               # Takt der Abo-Schleife (hoechste Rate 60 Hz kommt daraus nicht ueber ~100 Hz)
MAX_HZ = 60.0
JOY_TICK_S = 0.025                               # Takt des Joystick-Integrierers (40 Hz)
JOY_TIMEOUT_MS = (100, 5000, 500)                # kleinste / groesste / Standard-Totmannzeit
JOY = {"dead": 0.04, "k": 5.0, "vmax": 0.5}      # wie der Joystick der Oberflaeche: Totzone, Kruemmung der Kennlinie, Anteil des Bereichs je Sekunde ganz aussen

OPS = ("auth", "ping", "subscribe", "unsubscribe", "set", "joystick", "select", "cmd", "cue", "master", "blackout", "dmx", "tap", "audio_in", "timecode")
TOPICS = ("audio", "dmx", "fixtures", "events", "timecode")
GLOBAL_RATE_PER_S = 1200.0                       # alle Verbindungen zusammen: die Ereignisschleife (Cues, Effekte) und die DMX-Ausgabe haben Vorrang vor der Hardware-Steuerung
GLOBAL_BURST = 1500.0
_global_bucket = {"tokens": GLOBAL_BURST, "at": time.monotonic()}
_connections: Set["Connection"] = set()


def joystick_speed(r: float, dead: float = JOY["dead"], k: float = JOY["k"], vmax: float = JOY["vmax"]) -> float:
    """Geschwindigkeit (Anteil des ganzen Bereichs je Sekunde) fuer eine Auslenkung r = 0..1: Totzone, dann exponentiell (innen genau, aussen schnell)."""
    if r <= dead:
        return 0.0
    x = min(1.0, (r - dead) / (1.0 - dead))
    return vmax * (math.exp(k * x) - 1.0) / (math.exp(k) - 1.0)


def _num(value: Any, name: str, low: float, high: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ApiError(400, "bad_request", f"{name} must be a number.")
    return max(low, min(high, float(value)))


def _targets_of(message: Dict[str, Any], default_selection: bool = True) -> List[Any]:
    spec = {key: message[key] for key in ("fixtures", "fixture", "group", "selection") if key in message}
    return _resolve_targets(Targets(**spec), default_selection)


class Stick:
    """Ein Joystick-Knueppel einer Verbindung (z. B. "main"): Ziele, Achsen, Auslenkung und Startwerte (relativ je Scheinwerfer)."""

    def __init__(self, name: str, key: str, fixtures: List[Any], axes: Dict[str, str], mode: str, speed: float, dead: float, timeout: float) -> None:
        self.name, self.key, self.fixtures, self.axes, self.mode = name, key, fixtures, axes, mode
        self.speed, self.dead, self.timeout = speed, dead, timeout
        self.x = self.y = 0.0
        self.seen = time.monotonic()
        self.acc = {"x": 0.0, "y": 0.0}                     # gemeinsame Verschiebung (16-Bit-Einheiten)
        self.start: Dict[str, Dict[str, float]] = {}        # Scheinwerfer-ID -> Achse -> Startwert (0-65535)
        self.sent: Dict[str, Any] = {}
        self.dirty = True
        for fx in fixtures:
            self.start[fx.id] = {axis: float(round(current_value(fx, attr) * 655.35)) for axis, attr in axes.items()}
        spans = {axis: [v[axis] for v in self.start.values()] for axis in axes}
        self.lo = {axis: -min(values) for axis, values in spans.items()}                 # so weit darf die Verschiebung nach unten / oben, bevor der erste Scheinwerfer anschlaegt
        self.hi = {axis: 65535.0 - max(values) for axis, values in spans.items()}


class Connection:
    def __init__(self, websocket: WebSocket) -> None:
        self.ws = websocket
        self.token: Optional[Dict[str, Any]] = None
        self.ip = websocket.client.host if websocket.client else "?"
        self.lock = asyncio.Lock()
        self.tokens = RATE_BURST
        self.token_at = time.monotonic()
        self.closed = False
        self.sticks: Dict[str, Stick] = {}
        self.pump: Optional["asyncio.Task"] = None
        self.subs: Dict[str, Dict[str, Any]] = {}
        self.pusher: Optional["asyncio.Task"] = None
        self.hub_key: Optional[int] = None
        self.audio_rate: Optional[int] = None
        self.last_error: Dict[str, float] = {}
        self.sent_frames = 0
        self.id = uuid.uuid4().hex[:8]
        self.since = time.time()
        self.received = 0
        self.rate_window: List[float] = []              # Zeitpunkte der letzten Nachrichten (fuer "Nachrichten je Sekunde" in den Einstellungen)
        self.audio_frames = 0

    # ---- Senden
    async def send(self, frame: Dict[str, Any]) -> None:
        if self.closed:
            return
        try:
            async with self.lock:
                await asyncio.wait_for(self.ws.send_text(json.dumps(frame, separators=(",", ":"), ensure_ascii=False)), SEND_TIMEOUT_S)
            self.sent_frames += 1
        except Exception as exc:
            self.closed = True
            if isinstance(exc, asyncio.TimeoutError):                       # Langsamer Leser: Verbindung beenden, damit die Empfangsschleife aufwacht und alles aufraeumt
                logger.info("API-WebSocket %s getrennt: der Client liest nicht schnell genug", self.id)
                asyncio.ensure_future(self._drop())

    async def _drop(self) -> None:
        try:
            await asyncio.wait_for(self.ws.close(code=1013), 2.0)
        except Exception:
            pass

    async def error(self, code: str, message: str, request_id: Any = None) -> None:
        frame: Dict[str, Any] = {"op": "error", "code": code, "message": message}
        if request_id is not None:
            frame["id"] = request_id
        await self.send(frame)

    def allow(self, cap: str) -> None:
        if cap not in (self.token or {}).get("capabilities", []):
            raise ApiError(403, "forbidden", f"This token does not have the permission '{cap}'.")

    def take(self) -> bool:
        """Eimer fuer die Nachrichtenrate (Schutz vor Dauerfeuer) - je Verbindung UND fuer alle zusammen."""
        now = time.monotonic()
        self.tokens = min(RATE_BURST, self.tokens + (now - self.token_at) * RATE_PER_S)
        self.token_at = now
        g = _global_bucket
        g["tokens"] = min(GLOBAL_BURST, g["tokens"] + (now - g["at"]) * GLOBAL_RATE_PER_S)
        g["at"] = now
        if self.tokens < 1.0 or g["tokens"] < 1.0:
            return False
        self.tokens -= 1.0
        g["tokens"] -= 1.0
        self.received += 1
        self.rate_window.append(now)
        if len(self.rate_window) > 600:
            del self.rate_window[:300]
        return True

    def messages_per_second(self) -> int:
        now = time.monotonic()
        return sum(1 for moment in self.rate_window[-600:] if now - moment <= 1.0)


# ------------------------------------------------------------------------------------------------------------------ Joystick
async def _apply_stick(conn: Connection, stick: Stick) -> None:
    """Die aktuelle Verschiebung auf alle Scheinwerfer anwenden (jeder von seinem Startwert aus); gleiche Werte gehen in EINER Nachricht hinaus."""
    groups: Dict[tuple, List[str]] = {}
    values: Dict[tuple, Dict[str, float]] = {}
    for fx in stick.fixtures:
        mine: Dict[str, float] = {}
        for axis in stick.axes:
            base = 0.0 if stick.mode == "position" else stick.start[fx.id][axis]
            if stick.mode == "position":
                mine[axis] = round((stick.x if axis == "x" else stick.y) * 0.5 * 65535 + 32767.5)
            else:
                mine[axis] = round(max(0.0, min(65535.0, base + max(stick.lo[axis], min(stick.hi[axis], stick.acc[axis])))))
        key = tuple(sorted(mine.items()))
        groups.setdefault(key, []).append(fx.id)
        values[key] = mine
    for key, ids in groups.items():
        mine = values[key]
        payload: Dict[str, Any] = {"ids": ids}
        for axis, attr in stick.axes.items():
            v16 = int(max(0, min(65535, mine[axis])))
            payload[attr] = int(round(v16 / 65535.0 * 255.0))
            if attr in ("pan", "tilt"):
                payload[attr + "16"] = v16
        signature = (tuple(ids), key)
        if stick.sent.get(tuple(ids)) == signature:
            continue
        stick.sent[tuple(ids)] = signature
        await _message("set_fixture_values", payload)


async def _end_stick(conn: Connection, name: str, reason: str) -> None:
    stick = conn.sticks.pop(name, None)
    if stick is None:
        return
    if stick.mode == "rate":
        await _apply_stick(conn, stick)                               # letzter Stand garantiert
    if reason != "release":
        await conn.send({"op": "joystick", "stick": name, "state": reason})


async def _pump(conn: Connection) -> None:
    """Integriert die Auslenkungen aller Knueppel der Verbindung (40 Hz): Geschwindigkeit x Zeit = Verschiebung."""
    last = time.monotonic()
    try:
        while conn.sticks and not conn.closed:
            await asyncio.sleep(JOY_TICK_S)
            now = time.monotonic()
            dt = min(0.1, now - last)
            last = now
            for name, stick in list(conn.sticks.items()):
                if now - stick.seen > stick.timeout:
                    await _end_stick(conn, name, "timeout")           # Totmann: keine Nachricht mehr -> stehen bleiben
                    continue
                if stick.mode == "position":
                    if stick.dirty:
                        stick.dirty = False
                        await _apply_stick(conn, stick)
                    continue
                r = min(1.0, math.hypot(stick.x, stick.y))
                if r <= stick.dead:
                    continue
                move = joystick_speed(r, stick.dead) * stick.speed * 65535.0 * dt
                scale = move / r
                stick.acc["x"] += stick.x * scale
                stick.acc["y"] += stick.y * scale
                await _apply_stick(conn, stick)
    except asyncio.CancelledError:
        raise
    except Exception:
        logger.exception("Joystick-Schleife")
    finally:
        conn.pump = None


async def _op_joystick(conn: Connection, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    conn.allow("write.programmer")
    name = str(message.get("stick", "main"))[:20]
    x = _num(message.get("x", 0.0), "x", -1.0, 1.0)
    y = _num(message.get("y", 0.0), "y", -1.0, 1.0)
    mode = str(message.get("mode", "rate"))
    if mode not in ("rate", "position"):
        raise ApiError(400, "bad_request", "mode must be 'rate' (deflection = speed) or 'position' (deflection = position).")
    dead = _num(message.get("deadzone", JOY["dead"]), "deadzone", 0.0, 0.5)
    stick = conn.sticks.get(name)
    spec_key = json.dumps({k: message.get(k) for k in ("fixtures", "fixture", "group", "selection", "axes", "mode")}, sort_keys=True, default=str)
    if stick is not None and stick.key != spec_key:                    # andere Ziele / Achsen: den alten Knueppel beenden, neu beginnen
        await _end_stick(conn, name, "release")
        stick = None
    if message.get("release") or (mode == "rate" and math.hypot(x, y) <= dead):
        if stick is not None:
            stick.x = stick.y = 0.0
            await _end_stick(conn, name, "release")
        return {"stick": name, "state": "idle"}
    if stick is None:
        axes_in = message.get("axes") or {}
        axes = {"x": str(axes_in.get("x", "pan")).lower(), "y": str(axes_in.get("y", "tilt")).lower()}
        for attr in axes.values():
            if attr not in PCT_ATTRS:
                raise ApiError(400, "bad_request", f"axes: '{attr}' is not an attribute (pan, tilt, dimmer, zoom, focus ...).")
        if len(conn.sticks) >= 4:
            raise ApiError(429, "too_many_sticks", "At most 4 joysticks per connection.")
        timeout = _num(message.get("timeout_ms", JOY_TIMEOUT_MS[2]), "timeout_ms", JOY_TIMEOUT_MS[0], JOY_TIMEOUT_MS[1]) / 1000.0
        speed = _num(message.get("speed", 1.0), "speed", 0.05, 4.0)
        stick = Stick(name, spec_key, _targets_of(message), axes, mode, speed, dead, timeout)
        conn.sticks[name] = stick
        if conn.pump is None or conn.pump.done():
            conn.pump = asyncio.get_running_loop().create_task(_pump(conn))
    if message.get("invert_y"):
        y = -y
    stick.x, stick.y, stick.seen, stick.dirty = x, y, time.monotonic(), True
    return None


# ------------------------------------------------------------------------------------------------------------------ Werte setzen
def _byte(pct: float) -> int:
    return int(round(max(0.0, min(100.0, pct)) * 2.55))


async def _op_set(conn: Connection, message: Dict[str, Any]) -> Dict[str, Any]:
    conn.allow("write.programmer")
    values = message.get("values")
    if not isinstance(values, dict) or not values:
        raise ApiError(400, "bad_request", "values must be an object, e.g. {\"dimmer\": 80}.")
    mode = str(message.get("mode", "absolute"))
    if mode not in ("absolute", "relative"):
        raise ApiError(400, "bad_request", "mode must be absolute or relative.")
    fixtures = _targets_of(message)
    raw: Dict[str, Any] = {}
    deltas: Dict[str, Any] = {}
    absolute: Dict[str, Any] = {}
    if mode == "relative":
        deltas = _clean_deltas(values)
    else:
        from app.api_v1_manage import _clean_values
        cleaned = _clean_values(values)
        raw = {k: v for k, v in cleaned.items() if k.startswith("ch")}
        absolute = {k: v for k, v in cleaned.items() if not k.startswith("ch")}
    groups: Dict[str, List[str]] = {}
    for fx in fixtures:
        mine = relative_values(fx, deltas) if mode == "relative" else absolute
        if mine:
            groups.setdefault(json.dumps(mine, sort_keys=True), []).append(fx.id)
    for key, ids in groups.items():
        mine = json.loads(key)
        payload: Dict[str, Any] = {"ids": ids}
        for attr, value in mine.items():
            if attr == "color":
                payload["color"] = {"r": int(value["r"]), "g": int(value["g"]), "b": int(value["b"])}
            else:
                payload[attr] = _byte(value)
                if attr in ("pan", "tilt"):
                    payload[attr + "16"] = int(round(max(0.0, min(100.0, value)) * 655.35))
        await _message("set_fixture_values", payload)
    for attr, value in raw.items():
        from app.dmx_resolve import raw_offset
        await _message("set_fixture_raw_channel", {"ids": [fx.id for fx in fixtures], "channel_offset": raw_offset(attr), "value": value})
    return {"fixtures": [fx.fid for fx in fixtures]}


async def _op_select(conn: Connection, message: Dict[str, Any]) -> Dict[str, Any]:
    conn.allow("write.programmer")
    srv = _srv()
    st = srv.state
    mode = str(message.get("mode", "set"))
    if mode not in ("set", "add", "remove", "clear"):
        raise ApiError(400, "bad_request", "mode must be set, add, remove or clear.")
    if mode == "clear":
        ids: List[str] = []
    else:
        chosen = [fx.id for fx in _targets_of(message, default_selection=False)]
        current = list(st.selected_fixture_ids)
        ids = chosen if mode == "set" else (current + [i for i in chosen if i not in current] if mode == "add" else [i for i in current if i not in chosen])
    ids = st.set_selection(ids)
    await srv.event_bus.broadcast({"type": "selection_changed", "payload": {"selected_ids": ids}})
    return {"selected": [st.fixtures[i].fid for i in ids if i in st.fixtures]}


async def _op_cmd(conn: Connection, message: Dict[str, Any]) -> Dict[str, Any]:
    conn.allow("write.command")
    return await _run_command(str(message.get("line", message.get("command", ""))), bool(message.get("log", True)))


async def _op_cue(conn: Connection, message: Dict[str, Any]) -> Dict[str, Any]:
    conn.allow("write.cue")
    from app.api_v1 import _cue_by_ref, _num as _fmt, _resolve_cuelist
    action = str(message.get("action", "go")).lower()
    ref = str(message.get("list", message.get("cuelist", "")))
    if not ref:
        raise ApiError(400, "bad_request", "list: name or id of the cue list.")
    if action == "go" and message.get("cue") not in (None, ""):
        cl = _resolve_cuelist(ref)
        return await _cue_command(ref, f"Go Cue {_fmt(_cue_by_ref(cl, str(message['cue'])).number)}")
    suffix = {"go": "Go", "back": "Back", "pause": "Pause", "resume": "Resume", "stop": "Stop"}.get(action)
    if action == "fader":
        suffix = f"Fader {_num(message.get('value'), 'value', 0, 100):g}"
    if suffix is None:
        raise ApiError(400, "bad_request", "action must be go, back, pause, resume, stop or fader.")
    return await _cue_command(ref, suffix)


async def _op_master(conn: Connection, message: Dict[str, Any]) -> Dict[str, Any]:
    conn.allow("write.blackout")
    value = _num(message.get("value"), "value", 0, 100)
    result = await _run_command(f"Master {value:g}", log=False)
    if not result["success"]:
        raise ApiError(400, "rejected", result["message"])
    return {"value": _srv().state.grand_master}


async def _op_blackout(conn: Connection, message: Dict[str, Any]) -> Dict[str, Any]:
    conn.allow("write.blackout")
    srv = _srv()
    await srv.set_blackout(bool(message.get("on", message.get("enabled", True))), srv._broadcast_generic)
    return {"enabled": bool(srv.state.blackout)}


async def _op_dmx(conn: Connection, message: Dict[str, Any]) -> Dict[str, Any]:
    conn.allow("write.dmx")
    universe = int(_num(message.get("universe", 1), "universe", 1, 63999))
    channels = message.get("channels")
    if not isinstance(channels, dict) or not channels or len(channels) > 512:
        raise ApiError(400, "bad_request", "channels: an object {\"1\": 255, ...} with 1 to 512 entries.")
    done = 0
    for key, value in channels.items():
        channel = int(_num(float(key), "channel", 1, 512))
        await _set_raw(universe, channel, int(_num(value, "value", 0, 255)))
        done += 1
    return {"universe": universe, "set": done}


async def _op_tap(conn: Connection, message: Dict[str, Any]) -> Dict[str, Any]:
    conn.allow("write.audio")
    from app import audio_routes
    from app.audio_engine import audio_engine
    bpm = audio_engine.tap()
    await audio_routes._announce()
    return {"tap_bpm": bpm}


async def _op_timecode(conn: Connection, message: Dict[str, Any]) -> Dict[str, Any]:
    """Timecode steuern oder (action "sync") als MASTER mit einer aeusseren Uhr mitlaufen lassen: `{"op":"timecode","action":"sync","position":12345,"running":true}` - Position in ms oder "0:12.345",
    jede Nachricht gleicht nach (kleine Abweichungen unter 60 ms bleiben unangetastet, damit die Uhr nicht ruckelt; ein Sprung versetzt sie). Andere Aktionen wie PUT /timecode: play, pause, stop, seek, rate."""
    conn.allow("write.timecode")
    from app.timecode import parse_timecode_ms
    srv = _srv()
    action = str(message.get("action", "sync")).lower()
    raw = message.get("position", message.get("ms"))
    position: Optional[int] = None
    if raw is not None and raw != "":
        position = int(round(float(raw))) if isinstance(raw, (int, float)) and not isinstance(raw, bool) else parse_timecode_ms(raw)
        if position is None or position < 0:
            raise ApiError(400, "bad_request", "position: milliseconds or a time such as '1:04.300'.")
    if action == "sync":
        if position is None:
            raise ApiError(400, "bad_request", "sync needs a position.")
        tc = srv.timecode
        if message.get("rate") is not None:
            await _message("timecode_rate", {"rate": message["rate"]})
        if bool(message.get("running", True)):
            if not tc.running:
                await _message("timecode_play", {"position_ms": position, "direction": 1})
            elif abs(tc.position_ms() - position) > 60:
                await _message("timecode_seek", {"position_ms": position})
        else:
            if tc.running:
                await _message("timecode_pause", {})
            if abs(tc.position_ms() - position) > 1:
                await _message("timecode_seek", {"position_ms": position})
    elif action == "play":
        payload: Dict[str, Any] = {"direction": -1 if float(message.get("direction", 1)) < 0 else 1}
        if position is not None:
            payload["position_ms"] = position
        await _message("timecode_play", payload)
    elif action in ("pause", "stop"):
        await _message("timecode_" + action, {})
    elif action == "seek":
        if position is None:
            raise ApiError(400, "bad_request", "seek needs a position.")
        await _message("timecode_seek", {"position_ms": position})
    elif action == "rate":
        await _message("timecode_rate", {"rate": message.get("rate")})
    else:
        raise ApiError(400, "bad_request", "action must be sync, play, pause, stop, seek or rate.")
    from app.api_v1 import _timecode_dict
    return _timecode_dict()


async def _op_audio_in(conn: Connection, message: Dict[str, Any]) -> Dict[str, Any]:
    """Meldet an, dass Binaerrahmen mit PCM (16 Bit, little endian, Mono) folgen. `open: true` oeffnet dafuer die Audio-Quelle "network" (ersetzt die jetzige Quelle)."""
    conn.allow("write.audio")
    from app import audio_routes
    from app.audio_engine import audio_engine
    rate = int(_num(message.get("rate", 16000), "rate", 8000, 48000))
    fmt = str(message.get("format", "s16le")).lower()
    if fmt != "s16le":
        raise ApiError(400, "bad_request", "format must be 's16le' (16 bit signed, little endian, mono).")
    if message.get("open"):
        ok = await asyncio.to_thread(audio_engine.start, "network")
        await audio_routes._announce()
        if not ok:
            raise ApiError(409, "audio_failed", audio_engine.error or "The network audio source could not be opened.")
    conn.audio_rate = rate
    return {"rate": rate, "source_open": bool(audio_engine.running and audio_engine.config.get("device") == "network")}


# ------------------------------------------------------------------------------------------------------------------ Abonnements (Server -> Geraet)
async def _op_subscribe(conn: Connection, message: Dict[str, Any]) -> Dict[str, Any]:
    topic = str(message.get("topic", ""))
    if topic not in TOPICS:
        raise ApiError(400, "bad_request", f"topic must be one of {', '.join(TOPICS)}.")
    conn.allow("read.status" if topic in ("audio", "events", "timecode") else "read.dmx")
    hz = _num(message.get("hz", 30), "hz", 1, MAX_HZ)
    sub: Dict[str, Any] = {"hz": hz, "due": 0.0}
    if topic == "audio":
        keys = message.get("keys")
        sub["keys"] = [str(k) for k in keys] if isinstance(keys, list) else None
        sub["last"] = None
    elif topic == "dmx":
        universes = message.get("universes", [1])
        if not isinstance(universes, list) or not universes or len(universes) > 8:
            raise ApiError(400, "bad_request", "universes: a list with 1 to 8 universe numbers.")
        sub["universes"] = [int(_num(u, "universe", 1, 63999)) for u in universes]
        sub["last"] = {}
    elif topic == "fixtures":
        sub["last"] = {}
    elif topic == "timecode":
        sub["last"] = None
    else:
        wanted = message.get("events")
        names = [str(e) for e in wanted] if isinstance(wanted, list) else list(hub.DEFAULT)
        unknown = [e for e in names if e not in hub.ALL]
        if unknown:
            raise ApiError(400, "bad_request", f"Unknown event '{unknown[0]}' (events: {', '.join(hub.ALL)}).")
        sub["events"] = set(names)
        if conn.hub_key is None:
            conn.hub_key = hub.subscribe()
        for item in hub.snapshot_events():                       # Ausgangslage wie beim SSE-Strom
            if item["event"] in sub["events"]:
                await conn.send({"op": "event", "event": item["event"], "data": item["data"]})
    conn.subs[topic] = sub
    if conn.pusher is None or conn.pusher.done():
        conn.pusher = asyncio.get_running_loop().create_task(_pusher(conn))
    return {"topic": topic, "hz": hz}


async def _op_unsubscribe(conn: Connection, message: Dict[str, Any]) -> Dict[str, Any]:
    topic = str(message.get("topic", ""))
    conn.subs.pop(topic, None)
    if topic == "events" and conn.hub_key is not None:
        hub.unsubscribe(conn.hub_key)
        conn.hub_key = None
    return {"topic": topic}


async def _push_audio(conn: Connection, sub: Dict[str, Any]) -> None:
    from app.audio_engine import audio_engine
    values = audio_engine.values() if audio_engine.running else {}
    keys = sub["keys"]
    shown = {k: round(float(v), 3) for k, v in values.items() if keys is None or k in keys}
    if shown != sub["last"]:
        sub["last"] = shown
        await conn.send({"op": "audio", "t": int(time.time() * 1000), "running": bool(audio_engine.running), "v": shown})


async def _push_dmx(conn: Connection, sub: Dict[str, Any]) -> None:
    engine = _srv().dmx_engine
    for universe in sub["universes"]:
        now = list(engine.get_universe_snapshot(universe))
        before = sub["last"].get(universe)
        if before is None:
            await conn.send({"op": "dmx", "universe": universe, "full": True, "values": now})
        else:
            changes = {str(i + 1): v for i, (v, w) in enumerate(zip(now, before)) if v != w}
            if changes:
                await conn.send({"op": "dmx", "universe": universe, "changes": changes})
        sub["last"][universe] = now


async def _push_fixtures(conn: Connection, sub: Dict[str, Any]) -> None:
    from app.dmx_resolve import abstract_from_dmx
    srv = _srv()
    st = srv.state
    snapshots: Dict[int, List[int]] = {}
    changed: Dict[str, Any] = {}
    for fx in st.fixtures.values():
        if fx.universe not in snapshots:
            snapshots[fx.universe] = srv.dmx_engine.get_universe_snapshot(fx.universe)
        values = abstract_from_dmx(fx, snapshots[fx.universe], st.effective_master(fx.id))
        values.pop("wheels", None)
        if values and sub["last"].get(fx.id) != values:
            sub["last"][fx.id] = values
            changed[str(fx.fid)] = values
    if changed:
        await conn.send({"op": "fixtures", "values": changed})


async def _push_timecode(conn: Connection, sub: Dict[str, Any]) -> None:
    """Position der Uhr: laeuft sie, mit jedem Takt; steht sie, nur wenn sich etwas aendert (Start / Stopp / Sprung / Tempo)."""
    from app.api_v1 import _timecode_dict
    tc = _timecode_dict()
    key = (tc["running"], tc["direction"], tc["rate"], None if tc["running"] else tc["position_ms"])
    if tc["running"] or key != sub["last"]:
        sub["last"] = key
        await conn.send({"op": "timecode", "ms": int(round(tc["position_ms"])), "text": tc["position"], "running": tc["running"], "direction": tc["direction"], "rate": tc["rate"], "server_ms": int(time.time() * 1000)})


async def _push_events(conn: Connection, sub: Dict[str, Any]) -> None:
    queue = hub.queues.get(conn.hub_key) if conn.hub_key is not None else None
    if queue is None:
        return
    for _ in range(50):
        try:
            item = queue.get_nowait()
        except asyncio.QueueEmpty:
            break
        if item["event"] in sub["events"]:
            await conn.send({"op": "event", "event": item["event"], "data": item["data"]})


_PUSH = {"audio": _push_audio, "dmx": _push_dmx, "fixtures": _push_fixtures, "events": _push_events, "timecode": _push_timecode}


async def _pusher(conn: Connection) -> None:
    try:
        while conn.subs and not conn.closed:
            await asyncio.sleep(PUSH_BASE_S)
            now = time.monotonic()
            for topic, sub in list(conn.subs.items()):
                if now < sub["due"]:
                    continue
                sub["due"] = max(sub["due"] + 1.0 / sub["hz"], now - 1.0 / sub["hz"])           # feste Taktung (kein Aufsummieren der Wartezeit): die mittlere Rate stimmt auch bei groeber Zeitgebung von Windows
                try:
                    await _PUSH[topic](conn, sub)
                except Exception:
                    logger.debug("Abo %s", topic, exc_info=True)
    except asyncio.CancelledError:
        raise
    finally:
        conn.pusher = None


# ------------------------------------------------------------------------------------------------------------------ Verbindung
HANDLERS = {"set": _op_set, "select": _op_select, "cmd": _op_cmd, "cue": _op_cue, "master": _op_master, "blackout": _op_blackout, "dmx": _op_dmx, "tap": _op_tap,
            "audio_in": _op_audio_in, "timecode": _op_timecode, "subscribe": _op_subscribe, "unsubscribe": _op_unsubscribe}


async def _handle(conn: Connection, message: Dict[str, Any]) -> None:
    op = str(message.get("op", ""))
    request_id = message.get("id")
    try:
        if op == "ping":
            await conn.send({"op": "pong", "t": message.get("t"), "server_ms": int(time.time() * 1000), **({"id": request_id} if request_id is not None else {})})
            return
        if op == "joystick":
            result = await _op_joystick(conn, message)                  # sehr haeufig: nur Fehler und Statuswechsel werden beantwortet
            if result is not None and request_id is not None:
                await conn.send({"op": "ack", "id": request_id, **result})
            return
        handler = HANDLERS.get(op)
        if handler is None:
            raise ApiError(400, "bad_request", f"Unknown op '{op}' (ops: {', '.join(OPS)}).")
        result = await handler(conn, message)
        if request_id is not None:
            await conn.send({"op": "ack", "id": request_id, **(result or {})})
    except ApiError as exc:
        await conn.error(exc.code, exc.message, request_id)
    except Exception as exc:                                              # noqa: BLE001 - eine Nachricht darf nie die Verbindung beenden
        logger.exception("WebSocket-Nachricht '%s'", op)
        await conn.error("internal", str(exc)[:200], request_id)


async def _close(websocket: WebSocket, code: int) -> None:
    try:
        await websocket.close(code=code)
    except Exception:
        pass


def _secret_of(websocket: WebSocket) -> Optional[str]:
    header = websocket.headers.get("authorization", "")
    if header.lower().startswith("bearer "):
        return header[7:].strip()
    return websocket.headers.get("x-api-key") or websocket.query_params.get("access_token") or None


@router.websocket("/ws")
async def api_ws(websocket: WebSocket) -> None:
    """Live stream for hardware (see the documentation page /api/v1/docs, section "WebSocket"). Text frames = JSON messages, binary frames = audio (PCM s16le mono) after `audio_in`."""
    await websocket.accept()
    host = websocket.client.host if websocket.client else None
    conn = Connection(websocket)
    from app.state_manager import state
    try:
        if len(_connections) >= MAX_CONNECTIONS:
            await conn.error("too_many_connections", f"At most {MAX_CONNECTIONS} WebSocket connections at once.")
            return await _close(websocket, 4429)
        if not remote.is_local(host) and not state.remote_enabled:
            await conn.error("remote_disabled", "Remote access is switched off on the console.")
            return await _close(websocket, 4403)

        async def log_in(secret: Optional[str]) -> bool:
            try:
                conn.token = authenticate(conn.ip, host, secret)
            except ApiError as exc:
                await conn.error(exc.code, exc.message)
                await _close(websocket, 4401 if exc.status == 401 else 4429 if exc.status == 429 else 4403)
                return False
            store.touch(conn.token)
            return True

        secret = _secret_of(websocket)
        if secret is None:                                                # Anmeldung als erste Nachricht
            try:
                first = await asyncio.wait_for(websocket.receive_text(), AUTH_TIMEOUT_S)
                message = json.loads(first)
                secret = str(message.get("token", "")) if isinstance(message, dict) and message.get("op") == "auth" else None
            except Exception:
                secret = None
            if not secret:
                _note_failure(conn.ip)
                await conn.error("unauthorized", "Send the token in the header (Authorization: Bearer ...), as ?access_token=... or as first message {\"op\":\"auth\",\"token\":\"oc_...\"} within 5 s.")
                return await _close(websocket, 4401)
        if not await log_in(secret):
            return
        _connections.add(conn)
        await conn.send({"op": "hello", "app": APP_NAME, "version": str(APP_VERSION), "api": 1, "token": conn.token.get("name"), "capabilities": conn.token.get("capabilities", []),
                         "ops": list(OPS), "topics": list(TOPICS), "limits": {"messages_per_second": RATE_PER_S, "burst": RATE_BURST, "max_hz": MAX_HZ,
                                                                                 "joystick_timeout_ms": JOY_TIMEOUT_MS[2], "max_text_bytes": MAX_TEXT, "max_binary_bytes": MAX_BINARY},
                         "server_ms": int(time.time() * 1000)})
        while not conn.closed:
            data = await websocket.receive()
            if data.get("type") == "websocket.disconnect":
                break
            if not conn.take():
                now = time.monotonic()
                if now - conn.last_error.get("rate", 0.0) > 1.0:
                    conn.last_error["rate"] = now
                    await conn.error("rate_limited", f"Too many messages (limit {int(RATE_PER_S)} per second).")
                continue
            if data.get("bytes") is not None:
                blob = data["bytes"]
                if len(blob) > MAX_BINARY:
                    await conn.error("too_large", f"Binary frames up to {MAX_BINARY} bytes.")
                    continue
                if conn.audio_rate is None:
                    if now_ok(conn, "audio"):
                        await conn.error("bad_request", "Send {\"op\":\"audio_in\",\"rate\":16000} before binary audio frames.")
                    continue
                try:
                    conn.allow("write.audio")
                    import numpy as np
                    from app.audio_engine import audio_engine
                    samples = np.frombuffer(blob[: len(blob) // 2 * 2], dtype="<i2").astype(np.float32) / 32768.0
                    conn.audio_frames += 1
                    if not await asyncio.to_thread(audio_engine.feed_network, samples, conn.audio_rate) and now_ok(conn, "audio-src"):         # Analyse im Thread: die Ereignisschleife bleibt frei
                        await conn.error("audio_source", "The audio source 'network' is not open: select it in the Audio panel, PUT /api/v1/audio {\"device\":\"network\"} or send audio_in with \"open\": true.")
                except ApiError as exc:
                    await conn.error(exc.code, exc.message)
                continue
            text = data.get("text")
            if text is None:
                continue
            if len(text) > MAX_TEXT:
                await conn.error("too_large", f"Text messages up to {MAX_TEXT} bytes.")
                continue
            try:
                message = json.loads(text)
            except ValueError:
                await conn.error("bad_json", "Messages must be JSON objects.")
                continue
            if not isinstance(message, dict):
                await conn.error("bad_json", "Messages must be JSON objects.")
                continue
            await _handle(conn, message)
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.debug("WebSocket beendet", exc_info=True)
    finally:
        conn.closed = True
        _connections.discard(conn)
        for task in (conn.pump, conn.pusher):
            if task is not None:
                task.cancel()
        for name in list(conn.sticks):
            conn.sticks.pop(name, None)                                  # Verbindung weg: die Scheinwerfer bleiben stehen
        if conn.hub_key is not None:
            hub.unsubscribe(conn.hub_key)


def now_ok(conn: Connection, key: str) -> bool:
    """Eine Fehlermeldung je Art hoechstens einmal pro Sekunde (Audio-Rahmen kommen sehr oft)."""
    now = time.monotonic()
    if now - conn.last_error.get(key, 0.0) > 1.0:
        conn.last_error[key] = now
        return True
    return False


def connections_info() -> Dict[str, Any]:
    """Fuer Einstellungen -> REST-API: wer ist gerade ueber den WebSocket verbunden."""
    now = time.time()
    rows = []
    for conn in sorted(_connections, key=lambda c: c.since):
        rows.append({"id": conn.id, "token": (conn.token or {}).get("name", "?"), "ip": conn.ip, "since": int(conn.since), "seconds": int(now - conn.since),
                     "topics": sorted(conn.subs), "sticks": sorted(conn.sticks), "audio_in": conn.audio_rate, "messages_per_second": conn.messages_per_second(),
                     "received": conn.received, "sent": conn.sent_frames})
    return {"connections": rows, "max": MAX_CONNECTIONS, "event_streams": len(hub.queues)}


async def close_connection(conn_id: str) -> bool:
    for conn in list(_connections):
        if conn.id == conn_id:
            await conn.error("closed", "The connection was closed in the OpenCue settings.")
            await _close(conn.ws, 4403)
            return True
    return False
