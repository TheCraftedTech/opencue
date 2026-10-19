"""
server.py
FastAPI-Anwendung + WebSocket Event-Bus von OpenCue.

ARCHITEKTUR-REGEL (SEHR WICHTIG):
Der Server liefert ausschliesslich JSON ueber den WebSocket-Kanal "/ws".
Es gibt kein Server-Side-Rendering von HTML-Fragmenten - das komplette
UI-Verhalten (Dialoge, Panel-Zustaende, Interaktionen) lebt im Client
(static/js/app.js). So bleibt das UI flackerfrei, es gibt keine vollen
Seiten-Reloads, und Business-Logik bleibt sauber vom Rendering getrennt.
"""

from __future__ import annotations

import asyncio
import collections
import copy
import json
import logging
import re
import time
import uuid
from contextlib import asynccontextmanager
from dataclasses import asdict
from datetime import datetime as _dt
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import app.panel_registry  # registriert alle Panel-Typen beim Start
from app.command_line import (
    apply_full_baseline_reset,
    apply_preset_to_fixtures,
    delete_cuelist as delete_cuelist_command,
    execute_command,
    get_suggestions,
    restore_dmx_universes,
    release_fixtures,
    restore_fixture_outputs,
    set_blackout,
    set_cuelist_master,
    write_stored_outputs,
)
from app.cue_engine import FADE_FPS, cue_engine
from app.lan_listener import lan
from app.fx_engine import UI_UPDATE_INTERVAL, fx_engine
from app import fx_categories
from app.fx_script import FxScriptError, FxScriptRuntimeError, compile_script, preview_script, registry, run_script, seed_default_effects
from app.dmx_engine import dmx_engine
from app.dmx_resolve import (
    BEAM_ATTRS,
    beam_attr_by_channel,
    abstract_from_dmx,
    apply_abstract_values,
    byte_to_pct,
    current_abstract_values,
    fixture_channel_offsets,
    preset_to_abstract,
)
from app import media_store
from app import stream_sources
#3D-AUS# from app import stage_api
from app import sim_stages
from app import file_manager
from app import about
from app import defaults_seed
from app import updater
from app import host_cameras
from app import paths as _paths
from app import remote
from app import remote_pwa
from app.state_manager import Panel, panels_from_dicts, state, undo_history
from app.timecode import timecode
from app.window_signals import file_dialog
from app.window_signals import exit_requested, fullscreen_toggle_requested

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
logger = logging.getLogger("opencue.server")

BASE_DIR = _paths.project_root()                 # mitgelieferte Dateien (static/, templates/); im PyInstaller-Build sys._MEIPASS
PING_INTERVAL_SECONDS = 15
ENTTEC_WATCHDOG_INTERVAL = 5  # Sekunden zwischen Hardware-Checks


# Live-Daten: bei einem langsamen Client werden sie NICHT verworfen, sondern zusammengefasst (der neueste Stand gewinnt: Universen komplett,
# Werte je Scheinwerfer, Wiedergabezustand je Liste). Verwerfen waere falsch: fixtures_live sind Aenderungen gegenueber einem Server-Zwischenspeicher -
# ein verlorenes Paket haette den Wert auf diesem Geraet dauerhaft fehlen lassen.
_DROPPABLE_TYPES = {"dmx_universe_changed", "fixtures_changed", "fixtures_live", "programmer_live_update", "cuelist_progress"}
_OUTBOX_LIMIT = 150
_COALESCED_TYPES = {"dmx_universe_changed", "fixtures_changed", "fixtures_live", "programmer_live_update", "cuelist_progress"}
_BACKLOG_COALESCE = 24        # ab so vielen wartenden Nachrichten fasst auch eine lokale Verbindung Live-Daten zusammen
# Mindestabstand der Live-Daten zu einem entfernten Geraet (Tablet/Smartphone im WLAN): 25 Hz wie am Rechner, damit Fades und
# Effekte fluessig aussehen. Was das Geraet davon verarbeiten kann, regelt es selbst (Browser: _coalesceLive, DMX-Monitor-Takt);
# der Server fasst nur zusammen, was sich zwischen zwei Takten angestaut hat.
REMOTE_LIVE_INTERVAL = 0.04


class _Outbox:
    """Ausgangswarteschlange einer WebSocket-Verbindung mit eigenem Schreib-Task. Broadcasts warten damit nie auf einen
    langsamen Client (iPad im WLAN, Fenster im Hintergrund) und senden nie gleichzeitig auf denselben Socket; die
    Reihenfolge je Verbindung bleibt erhalten. Staut sich bei einem Client Live-Daten, werden diese verworfen.

    Bei entfernten Geraeten (live_interval > 0) werden Live-Daten ausserdem zusammengefasst und hoechstens alle
    live_interval Sekunden gesendet. Kommt dazwischen eine "normale" Nachricht, gehen die wartenden Live-Daten
    davor hinaus - die Reihenfolge bleibt also exakt erhalten."""

    def __init__(self, websocket: WebSocket, loop: asyncio.AbstractEventLoop, live_interval: float = 0.0) -> None:
        self.websocket, self.loop = websocket, loop
        self.queue: Deque[str] = collections.deque()
        self.live: Dict[Any, Dict[str, Any]] = {}
        self.live_interval = live_interval
        self.last_live = 0.0
        self.wake = asyncio.Event()
        self.dead = False
        self.dropped = 0
        self.task = loop.create_task(self._run())

    def push(self, text: Optional[str], droppable: bool, message: Optional[Dict[str, Any]] = None) -> None:
        if message is not None and (self.live_interval > 0 or len(self.queue) >= _BACKLOG_COALESCE):
            self._push_live(message)
            return
        self._drain_live()                          # wartende Live-Daten bleiben vor dieser Nachricht
        if droppable and len(self.queue) > _OUTBOX_LIMIT:
            self.dropped += 1
            return
        self.queue.append(text if text is not None else json.dumps(message))
        self.wake.set()

    def _push_live(self, message: Dict[str, Any]) -> None:
        kind = message["type"]
        payload = message.get("payload") or {}
        if kind == "dmx_universe_changed":
            key: Any = (kind, payload.get("universe"))
            self.live.pop(key, None)                # neu einsortieren: Reihenfolge = Reihenfolge des neuesten Stands
            self.live[key] = message
        elif kind == "fixtures_changed":
            self.live.pop(kind, None)
            self.live[kind] = message
        elif kind == "cuelist_progress":
            key = (kind, payload.get("cuelist_id"))
            self.live.pop(key, None)
            self.live[key] = message
        else:                                       # Werte je Scheinwerfer zusammenfuehren
            held = self.live.get(kind)
            incoming = payload.get("values") or {}
            if held is None:
                self.live[kind] = {"type": kind, "payload": {"values": {fid: dict(attrs) for fid, attrs in incoming.items()}}}
            else:
                values = held["payload"]["values"]
                for fid, attrs in incoming.items():
                    values.setdefault(fid, {}).update(attrs)
        self.wake.set()

    def _drain_live(self) -> None:
        if not self.live:
            return
        pending, self.live = self.live, {}
        for message in pending.values():
            self.queue.append(json.dumps(message))
        self.last_live = self.loop.time()

    async def _run(self) -> None:
        try:
            while True:
                await self.wake.wait()
                self.wake.clear()
                while self.queue or self.live:
                    if self.queue:
                        await self.websocket.send_text(self.queue.popleft())
                        continue
                    wait = self.last_live + self.live_interval - self.loop.time()
                    if wait > 0:                    # Takt abwarten; eine normale Nachricht weckt sofort (und raeumt die Live-Daten vor sich her)
                        try:
                            await asyncio.wait_for(self._wait_for_push(), wait)
                        except asyncio.TimeoutError:
                            pass
                        continue
                    self._drain_live()
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            self.dead = True
            logger.warning("[WS] Senden an einen Client fehlgeschlagen (%s: %s) - Verbindung wird entfernt",
                           type(exc).__name__, exc)
            event_bus.disconnect(self.websocket)

    async def _wait_for_push(self) -> None:
        """Wartet auf eine neue normale Nachricht (Live-Daten allein verkuerzen den Takt nicht)."""
        while not self.queue:
            self.wake.clear()
            await self.wake.wait()


class EventBus:
    """Verwaltet alle aktiven WebSocket-Verbindungen und broadcastet JSON-Events.

    Jede Verbindung ist lokal (PyWebView auf der Konsole) oder extern (Netzwerk-Client,
    mit eigenem Layout). Live-Daten gehen an alle; Layout- und Fenster-Events nur an
    lokale Clients (siehe remote.LOCAL_ONLY_EVENTS)."""

    def __init__(self) -> None:
        self._connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        self._connections.add(websocket)
        logger.info("Client verbunden (%d aktiv)", len(self._connections))

    def disconnect(self, websocket: WebSocket) -> None:
        self._connections.discard(websocket)
        box = getattr(websocket.state, "outbox", None)
        if box is not None and not box.task.done() and asyncio.current_task() is not box.task:
            box.task.cancel()
        logger.info("Client getrennt (%d aktiv)", len(self._connections))

    @staticmethod
    def is_local(websocket: WebSocket) -> bool:
        return bool(getattr(websocket.state, "is_local", True))

    @staticmethod
    async def _send(websocket: WebSocket, text: str, message_type: Optional[str] = None,
                    message: Optional[Dict[str, Any]] = None) -> None:
        """Reiht eine Nachricht in die Ausgangswarteschlange der Verbindung ein (kehrt sofort zurueck).
        `message` (nur fuer Live-Daten) erlaubt der Warteschlange, mehrere Staende zusammenzufassen."""
        loop = asyncio.get_running_loop()
        box = getattr(websocket.state, "outbox", None)
        if box is None:
            local = EventBus.is_local(websocket)
            box = websocket.state.outbox = _Outbox(websocket, loop, 0.0 if local else REMOTE_LIVE_INTERVAL)
        if box.dead:
            raise RuntimeError("Verbindung nicht mehr nutzbar")
        droppable = message_type in _DROPPABLE_TYPES
        live = message if message_type in _COALESCED_TYPES else None
        if loop is box.loop:
            box.push(text, droppable, live)
        else:                                       # Aufruf aus einer anderen Event-Loop: in die Loop der Verbindung uebergeben
            box.loop.call_soon_threadsafe(box.push, text, droppable, live)

    @staticmethod
    async def send_to(websocket: WebSocket, message: Dict[str, Any]) -> None:
        await EventBus._send(websocket, json.dumps(message), message.get("type"))

    @staticmethod
    def _message_for(websocket: WebSocket, message: Dict[str, Any]) -> Dict[str, Any]:
        """Snapshots werden je Client aufbereitet: Host-Daten fuer die Konsole, eigenes
        Layout fuer externe Clients."""
        if message.get("type") != "state_snapshot":
            return message
        return _decorate_snapshot(message, EventBus.is_local(websocket), websocket.state.cid)

    async def broadcast(self, message: Dict[str, Any], exclude: Optional[WebSocket] = None) -> None:
        """Schickt ein JSON-Event an alle verbundenen Clients (ausser `exclude`, dem
        Absender einer Live-Bedienung - sein eigener Fader soll nicht zurueckspringen)."""
        if not self._connections:
            return
        local_only = message.get("type") in remote.LOCAL_ONLY_EVENTS
        shared = None if message.get("type") == "state_snapshot" else json.dumps(message)
        stale: Set[WebSocket] = set()
        for connection in list(self._connections):
            local = self.is_local(connection)
            if connection is exclude or (local_only and not local):
                continue
            try:
                await self._send(connection, shared if shared is not None
                                 else json.dumps(self._message_for(connection, message)), message.get("type"), message)
            except Exception:
                stale.add(connection)
        for connection in stale:
            self._connections.discard(connection)

    async def send_to_local(self, message: Dict[str, Any]) -> None:
        """Schickt eine Nachricht an alle Konsolen-Fenster (lokale Verbindungen)."""
        for connection in list(self._connections):
            if self.is_local(connection):
                try:
                    await self.send_to(connection, message)
                except Exception:
                    self._connections.discard(connection)

    async def send_to_client(self, cid: str, message: Dict[str, Any]) -> None:
        """Schickt eine Nachricht an alle Tabs eines externen Clients (Cookie-ID)."""
        for connection in list(self._connections):
            if not self.is_local(connection) and getattr(connection.state, "cid", None) == cid:
                try:
                    await self.send_to(connection, message)
                except Exception:
                    self._connections.discard(connection)

    async def close_remote(self, code: int) -> None:
        """Trennt alle externen Clients (Remote deaktiviert, Passwort geaendert)."""
        for connection in [c for c in self._connections if not self.is_local(c)]:
            self._connections.discard(connection)
            try:
                await connection.close(code=code)
            except Exception:
                pass


def _remote_client_infos() -> List[Dict[str, Any]]:
    """Verbundene externe Clients (ohne die Konsole selbst) fuer Anzeige und Kick."""
    now = time.time()
    return [
        {"id": c.state.client_id, "ip": c.state.ip, "device": remote.device_label(c.state.ua),
         "ua": c.state.ua[:160], "connected_for": int(now - c.state.connected_at)}
        for c in event_bus._connections if not event_bus.is_local(c)
    ]


def _decorate_snapshot(message: Dict[str, Any], local: bool, cid: Optional[str]) -> Dict[str, Any]:
    payload = dict(message["payload"])
    clients = _remote_client_infos()
    payload["is_local"] = local
    payload["cue_progress"] = cue_engine.progress_snapshot()   # Kompatibilitaet
    payload["cue_playback"] = cue_engine.playback_snapshot()   # Ladebalken/Pause/Stopp sofort korrekt
    payload["remote_enabled"] = state.remote_enabled
    payload["remote_client_count"] = len(clients)
    payload["remote"] = remote.remote_info(include_password=True)   # alle Geraete verwalten Remote gleichermassen
    if local:
        payload["remote_clients"] = clients
    else:
        sess = remote.session_for(cid)
        payload["panels"] = sess.panels_as_dicts()
        # Jedes Geraet hat sein eigenes Layout: der Snapshot nennt das zuletzt geladene dieses Geraets.
        payload["last_active_layout"] = sess.layout["name"] if sess.layout else None
        payload["remote_clients"] = clients       # wie am Desktop: welche Geraete insgesamt verbunden sind
    return {**message, "payload": payload}


async def _broadcast_remote_clients() -> None:
    """Anzahl an alle (Toolbar-Badge), Liste mit IPs nur an die Konsole."""
    clients = _remote_client_infos()
    await event_bus.broadcast({"type": "remote_client_count",
                               "payload": {"count": len(clients), "enabled": state.remote_enabled}})
    await event_bus.broadcast({"type": "remote_clients_changed", "payload": {"clients": clients}})


async def _kick_client(client_id: str) -> bool:
    """Trennt einen externen Client sofort und meldet seine Sitzung ab."""
    for connection in list(event_bus._connections):
        if event_bus.is_local(connection) or getattr(connection.state, "client_id", None) != client_id:
            continue
        logger.info("[Remote] Client %s entfernt (Kick)", connection.state.ip)
        connection.state.kicked = True
        remote.logout(getattr(connection.state, "token", None))
        event_bus._connections.discard(connection)
        try:
            await event_bus.send_to(connection, {"type": "kicked", "payload": {}})
            await connection.close(code=4402)
        except Exception:
            pass
        await _broadcast_remote_clients()
        return True
    return False


def _snapshot_for_client(local: bool, cid: Optional[str]) -> Dict[str, Any]:
    snapshot = state.get_snapshot()
    snapshot["payload"]["enttec_status"] = dmx_engine.get_enttec_status()
    snapshot["payload"]["enttec_ports"] = dmx_engine.scan_enttec_ports()
    snapshot["payload"]["timecode"] = timecode.state()
    snapshot["payload"]["stream_sources"] = stream_sources.public_list()
    return _decorate_snapshot(snapshot, local, cid)


def _snapshot_for(websocket: WebSocket) -> Dict[str, Any]:
    return _snapshot_for_client(EventBus.is_local(websocket), websocket.state.cid)


event_bus = EventBus()

# Letzter Wert jedes befehlsbasierten Faders (Muster -> Wert). Nur im Arbeitsspeicher:
# Fader und Buttons mit demselben Befehl bleiben so auf allen Geraeten deckungsgleich,
# auch fuer Clients, die sich spaeter verbinden oder nach einem Standby neu verbinden.
_command_values: Dict[str, float] = {}
MAX_COMMAND_PATTERNS = 500

def _log_dmx_driver(name: str, enabled: bool, detail: str = "") -> None:
    """Kurzes [DMX]-Log: "[DMX] Art-Net ON → 2.255.255.255"."""
    if enabled:
        suffix = f" → {detail}" if detail else ""
        logger.info("[DMX] %s ON%s", name, suffix)
    else:
        logger.info("[DMX] %s OFF", name)


# UI-Takt der Live-Werte waehrend einer Ueberblendung. Die CueEngine rechnet und sendet DMX mit 40 Hz;
# die Oberflaeche (Fader, DMX-Monitor, Scheinwerferliste) bekommt davon nur den jeweils neuesten Stand.
CUE_UI_INTERVAL = 0.06


class _CueUiPublisher:
    """Entkoppelt die Oberflaeche vom DMX-Takt.

    Die CueEngine ruft push()/push_playback() nur noch auf (Dictionary fuellen, kein await): Ein langsamer
    oder haengender Client (iPad im WLAN) kann den Fade-Takt damit nicht mehr verzoegern - das DMX-Signal
    hat Vorrang. Alle Live-Daten werden zusammengefasst (neuester Wert gewinnt) und hoechstens alle
    CUE_UI_INTERVAL Sekunden gesendet; Aenderungen des Wiedergabezustands gehen sofort hinaus."""

    def __init__(self) -> None:
        self._universes: Set[int] = set()
        self._values: Dict[str, Any] = {}
        self._playback: Dict[str, Dict[str, Any]] = {}
        self._wake: Optional[asyncio.Event] = None
        self._task: Optional[asyncio.Task] = None

    def _ensure_running(self) -> None:
        if self._task is None or self._task.done():
            self._wake = asyncio.Event()
            self._task = asyncio.get_running_loop().create_task(self._run())

    def push(self, data: Dict[str, Any]) -> None:
        self._ensure_running()
        self._universes.update(data.get("universes") or ())
        self._values.update(data.get("values") or {})
        self._wake.set()

    def push_dirty(self, universe: int) -> None:
        """Ein DMX-Puffer hat sich geaendert (von irgendwo): Monitor und Bedienelemente werden daraus nachgefuehrt."""
        self._ensure_running()
        self._universes.add(universe)
        self._wake.set()

    def push_playback(self, payload: Dict[str, Any]) -> None:
        self._ensure_running()
        self._playback[payload["cuelist_id"]] = payload     # pro Liste zaehlt nur der neueste Zustand
        self._wake.set()

    async def _flush_playback(self) -> None:
        pending, self._playback = self._playback, {}
        for payload in pending.values():
            await event_bus.broadcast({"type": "cuelist_progress", "payload": payload})

    async def _flush_live(self) -> None:
        universes, values = self._universes, self._values
        self._universes, self._values = set(), {}
        for universe in universes:
            await event_bus.broadcast({
                "type": "dmx_universe_changed",
                "payload": {"universe": universe, "values": dmx_engine.get_universe_snapshot(universe)},
            })
        if values:
            # Cue-Ausgabe (gemischt): raeumt die "angefasst"-Markierung der betroffenen Attribute auf
            await event_bus.broadcast({"type": "programmer_live_update", "payload": {"values": values}})
        # Quelle der Wahrheit ist der DMX-Puffer (was der DMX-Monitor zeigt): Bedienelemente folgen ihm live
        live = _live_values_for(universes)
        if live:
            await event_bus.broadcast({"type": "fixtures_live", "payload": {"values": live}})
        # Kein fixtures_changed mehr im Livetakt: Die Cue-/Effektausgabe veraendert die gespeicherten Scheinwerfer-Daten nicht, die
        # ganze Liste (samt Neuaufbau von Scheinwerferliste und Programmer-Raster auf jedem Geraet) war reine Last.

    async def _run(self) -> None:
        last_live = 0.0
        while True:
            await self._wake.wait()
            self._wake.clear()
            try:
                await self._flush_playback()
                if self._universes or self._values:
                    wait = last_live + CUE_UI_INTERVAL - time.monotonic()
                    if wait > 0:
                        await asyncio.sleep(wait)
                    await self._flush_playback()
                    await self._flush_live()
                    last_live = time.monotonic()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("[CUE] UI-Update fehlgeschlagen")


_cue_ui = _CueUiPublisher()


_live_cache: Dict[str, Dict[str, Any]] = {}      # fixture_id -> zuletzt gesendete abstrakte Werte (nur Aenderungen senden)


def _live_values_for(universes: Optional[Set[int]], full: bool = False) -> Dict[str, Dict[str, Any]]:
    """Abstrakte Werte der Fixtures aus dem DMX-Puffer (die Wahrheit). full=True: alle Fixtures (neue Verbindung,
    geladene Show), sonst nur die in `universes`, deren Werte sich seit dem letzten Senden geaendert haben."""
    snapshots: Dict[int, List[int]] = {}
    out: Dict[str, Dict[str, Any]] = {}
    for fx in state.fixtures.values():
        if not full and (universes is None or fx.universe not in universes):
            continue
        if fx.universe not in snapshots:
            snapshots[fx.universe] = dmx_engine.get_universe_snapshot(fx.universe)
        values = abstract_from_dmx(fx, snapshots[fx.universe], state.effective_master(fx.id))
        if not values:
            continue
        if not full and _live_cache.get(fx.id) == values:
            continue
        _live_cache[fx.id] = values
        out[fx.id] = values
    return out


def _dmx_changed(universe: int) -> None:
    """Callback der DMX-Engine (beliebiger Thread): zurueck in den Event-Loop und an die Live-Anzeige."""
    loop = _app_loop
    if loop is not None:
        try:
            loop.call_soon_threadsafe(_cue_ui.push_dirty, universe)
        except RuntimeError:                      # Loop schon geschlossen
            pass


dmx_engine.set_change_callback(_dmx_changed)


def _cue_engine_update(data: Dict[str, Any]) -> None:
    """Callback der CueEngine nach jedem Fade-Tick: nur uebergeben, nie warten (siehe _CueUiPublisher)."""
    _cue_ui.push(data)


def _cue_playback_update(payload: Dict[str, Any]) -> None:
    """Callback der CueEngine bei Start/Pause/Weiter/Stopp/Ende: Zustand des Ladebalkens an alle Clients."""
    _cue_ui.push_playback(payload)


async def _broadcast_cuelists_changed() -> None:
    """Broadcastet den kompletten CueList-Zustand (inkl. aktivem Cue pro
    Liste) an alle verbundenen Clients. Modul-weit statt nur innerhalb von
    _handle_client_message definiert, damit auch die CueEngine selbst
    (automatischer Follow-Trigger, siehe cue_engine.py) diesen Broadcast
    ausloesen kann - sie kennt den EventBus sonst nicht."""
    await event_bus.broadcast({
        "type": "cuelists_changed",
        "payload": {
            "cuelists": state.cuelists_as_dicts(),
            "active_cuelist_id": state.active_cuelist_id,
            "active_cue_ids": dict(state.active_cue_ids),
            "cue_playback": cue_engine.playback_snapshot(),   # Balken passt exakt zum neuen aktiven Cue
            "is_dirty": state.is_dirty,
        },
    })


async def _broadcast_timecode(snapshot: Optional[Dict[str, Any]] = None) -> None:
    """Zustand des globalen Timecodes an alle Clients (bei jeder Bedienung und als Herzschlag waehrend des Laufs)."""
    await event_bus.broadcast({"type": "timecode_state", "payload": snapshot or timecode.state()})


async def _timecode_cross(prev_ms: float, cur_ms: float) -> None:
    """Der laufende Timecode hat (prev, cur] durchquert: alle Cues mit Ausloeser 'timecode' in diesem Bereich feuern in
    zeitlicher Reihenfolge (wie 'Hierhin faden': mit ihren eigenen Zeiten; Follow-Ketten laufen danach wie gewohnt weiter)."""
    due = []
    for cuelist in list(state.cuelists.values()):
        for cue in list(cuelist.cues):
            if cue.trigger == "timecode" and cue.timecode_ms is not None and prev_ms < cue.timecode_ms <= cur_ms:
                due.append((cue.timecode_ms, cue.number, cuelist.id, cue.id))
    if not due:
        return
    due.sort()
    for _, _, cuelist_id, cue_id in due:
        await cue_engine.jump_to(cuelist_id, cue_id)
    await _broadcast_cuelists_changed()


timecode.set_callbacks(_broadcast_timecode, _timecode_cross)


async def _cue_result(websocket: WebSocket, **payload: Any) -> None:
    """Ergebnis einer Cue-Aktion (Speichern, Aktualisieren, Nummer aendern) nur an den Absender: ok/code + Details.
    Der Client zeigt daraus Rueckfragen (Nummer existiert) oder Hinweise."""
    await event_bus.send_to(websocket, {"type": "cue_store_result", "payload": payload})


async def _broadcast_generic(message_type: str, payload: Dict[str, Any]) -> None:
    """Generischer Broadcast-Kanal mit der Signatur, die app/command_line.py
    erwartet (Broadcast = async(message_type, payload)). Wird sowohl vom
    "run_command"-WS-Handler als auch von der automatischen CMD-Ausfuehrung
    der CueEngine (Cue.cmd, siehe cue_engine.set_broadcast_callback)
    verwendet - EIN Codepfad fuer beide Ausloeser."""
    await event_bus.broadcast({"type": message_type, "payload": payload})


async def _broadcast_command_log(command: str, result: Dict[str, Any]) -> None:
    """Gemeinsamer Log-Broadcast fuer manuell eingegebene Befehle UND
    automatisch von einem Cue ausgefuehrte (Cue.cmd) - beide landen in
    derselben Befehlshistorie aller geoeffneten Command-Line-Panels.
    Traegt einen sekundengenauen Server-Zeitstempel, damit alle Clients
    exakt dieselbe Uhrzeit anzeigen (statt je eigener Empfangszeit)."""
    await event_bus.broadcast({
        "type": "command_log",
        "payload": {
            "command": command,
            "success": result.get("success", False),
            "message": result.get("message", ""),
            "timestamp": _dt.now().strftime("%H:%M:%S"),
        },
    })


def _dmx_state_for_save() -> Dict[int, List[int]]:
    return {u: dmx_engine.get_universe_snapshot(u) for u in dmx_engine.universe_numbers()}


state.dmx_state_provider = _dmx_state_for_save


_RESERVED_NAMES = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)),
                   *(f"LPT{i}" for i in range(1, 10))}


def _script_file_name(raw: Any) -> str:
    """Dateiname ohne Endung, exakt wie eingegeben. Nur Zeichen, die das Dateisystem
    verbietet, werden entfernt. Leer oder reserviert (CON, NUL, ...) = kein gueltiger Name."""
    text = str(raw).strip()
    if text.lower().endswith(".fx"):
        text = text[:-3]
    cleaned = re.sub(r'[\\/:*?"<>|\x00-\x1f]', "", text).strip().rstrip(".")[:80]
    if cleaned.split(".")[0].upper() in _RESERVED_NAMES:
        return ""
    return cleaned


def _effect_sources() -> list:
    """Zusaetzliche Effekt-Ordner neben dem Benutzerordner (derzeit keine)."""
    return []


def _compile_result(name: str, text: str, test: bool = False) -> Dict[str, Any]:
    """Prueft ein Skript. Mit test=True wird es zusaetzlich probeweise ausgefuehrt
    (drei Ticks, drei Scheinwerfer), damit Laufzeitfehler sichtbar werden."""
    try:
        script = compile_script(name, text)
        if test:
            run_state: Dict[str, Any] = {}
            for i in range(3):
                run_script(script, run_state, script.default_params(), i, 3, i * 0.1, i)
        return {"ok": True, "name": name, "line": None, "message": "OK"}
    except FxScriptError as exc:
        return {"ok": False, "name": name, "line": exc.line, "message": exc.message}
    except Exception as exc:
        return {"ok": False, "name": name, "line": None, "message": str(exc)}


def _fx_script_list_message() -> Dict[str, Any]:
    registry.load(_effect_sources())
    files = [{"name": f["name"], "origin": f["origin"], "category": f["category"], "label": f.get("label", f["name"]),
              "description": f.get("description", ""), "rate": f.get("rate"),
              "default": bool(f.get("default")), "default_modified": bool(f.get("default_modified")), "favorite": f["name"] in state.fx_favorites,
              "ok": f["ok"], "line": f["line"], "message": f["message"]}
             for f in registry.files()]
    return {"type": "fx_script_list", "payload": {"files": files}}


def _fx_changed_message() -> Dict[str, Any]:
    return {"type": "fx_changed", "payload": fx_engine.state_payload()}


async def _release_fixtures(fixture_ids: List[str]) -> None:
    """Gibt Fixtures frei (Zuweisung entfernt) und zeigt sofort den gespeicherten Stand (Logik: app/command_line.py, auch fuer die Befehlszeile)."""
    await release_fixtures(fixture_ids, _broadcast_generic)


def _refs_message() -> Dict[str, Any]:
    """Welche Variable (Platzhalter) gerade welchen Teil welcher Fixture im Programmer vorgibt - die Dropdowns und gesperrten Fader folgen daraus."""
    return {"type": "programmer_refs", "payload": {"refs": state.programmer_refs_payload()}}


async def _apply_preset_to_fixtures(fixture_ids: List[str], preset, *, live: bool = False) -> None:
    """Wendet eine Variable auf Fixtures an UND verknuepft sie (Logik: app/command_line.py apply_preset_to_fixtures, auch fuer die Befehlszeile).
    live=True (die Variable wurde geaendert): gleiche Ausgabe, aber ohne die Werte als "angefasst" zu markieren."""
    await apply_preset_to_fixtures(fixture_ids, preset, _broadcast_generic, live=live)


async def _reapply_preset(preset_id: str) -> None:
    """Eine Variable wurde geaendert: alles, was ihr folgt (Programmer-Fixtures, aktive Cues), zeigt sofort den neuen Wert."""
    preset = state.presets.get(preset_id)
    if preset is None:
        return
    following = [fid for fid, refs in state.programmer_refs.items() if refs.get(preset.type) == preset_id]
    if following:
        await _apply_preset_to_fixtures(following, preset, live=True)
    await cue_engine.refresh_preset(preset_id)


async def _fx_monitor_pump() -> None:
    """Bedient den DMX-Monitor und die Scheinwerfer-Vorschau im UI-Takt (25 Hz).
    Effektwerte kommen als programmer_live_update - derselbe Pfad wie Cue-Fades,
    d.h. ohne "touched"-Markierung. Ein Fehler in einem Durchlauf beendet die Pumpe nicht."""
    try:
        while True:
            await asyncio.sleep(UI_UPDATE_INTERVAL)
            try:
                for universe in sorted(fx_engine.take_touched_universes()):
                    await event_bus.broadcast({"type": "dmx_universe_changed", "payload": {
                        "universe": universe, "values": dmx_engine.get_universe_snapshot(universe),
                    }})
                live = fx_engine.live_values()
                if live:
                    await event_bus.broadcast({"type": "programmer_live_update", "payload": {"values": live}})
                if fx_engine.take_assignments_changed():
                    await event_bus.broadcast(_fx_changed_message())
            except Exception:
                logger.exception("FX-Monitor-Durchlauf fehlgeschlagen")
    except asyncio.CancelledError:
        pass


def _live_state_messages() -> List[Dict[str, Any]]:
    """DMX-Ausgang und Programmer-Markierungen aller Universen - an jeden neu
    verbundenen Client und nach einem Wiederanlauf zu senden."""
    messages: List[Dict[str, Any]] = [
        {"type": "dmx_universe_changed", "payload": {
            "universe": u, "values": dmx_engine.get_universe_snapshot(u),
        }}
        for u in dmx_engine.universe_numbers()
    ]
    programmer = {fx_id: dict(vals) for fx_id, vals in state.programmer_values.items() if vals}
    if programmer:
        messages.append({"type": "programmer_command_update", "payload": {"values": programmer}})
    messages.append(_refs_message())
    messages.append({"type": "grand_master_changed", "payload": {"value": state.grand_master}})
    _live_cache.clear()
    live = _live_values_for(None, full=True)       # alle Fixtures aus dem DMX-Puffer: Bedienelemente starten richtig
    if live:
        messages.append({"type": "fixtures_live", "payload": {"values": live}})
    for cl_id, level in state.cuelist_masters.items():
        messages.append({"type": "cuelist_master_changed", "payload": {"cuelist_id": cl_id, "value": level}})
    messages.append({"type": "command_values_state", "payload": {"values": dict(_command_values)}})
    messages.append(_fx_changed_message())
    return messages


async def _restore_showfile_state() -> None:
    """Wiederanlauf nach Programmstart und jedem Laden eines Showfiles: Hat das
    Showfile einen gespeicherten Live-Zustand (runtime_state), wird das DMX-
    Universum exakt so hergestellt wie beim Speichern, Programmer-Werte und
    aktive Cues werden uebernommen. Sonst greift der Baseline-Reset (Dimmer 0,
    Pan/Tilt Home, Farbe Schwarz)."""
    if not state.runtime_state_loaded:
        await apply_full_baseline_reset(_broadcast_generic)
        return
    if state.restored_dmx_universes is not None:
        restore_dmx_universes(state.restored_dmx_universes)
    else:
        await write_stored_outputs(_broadcast_generic)
    if state.blackout:
        await set_blackout(True, _broadcast_generic)        # der Blackout hat Vorrang vor dem wiederhergestellten Stand
    state.set_selection([])
    await _broadcast_generic("selection_changed", {"selected_ids": []})
    for message in _live_state_messages():
        await event_bus.broadcast(message)


@asynccontextmanager
async def lifespan(_: FastAPI):
    global _app_loop, _host_baseline
    _app_loop = asyncio.get_running_loop()
    seed_default_effects(_paths.default_effects_dir(), _paths.effects_dir())
    registry.load(_effect_sources())
    # Zuletzt persistierte DMX/Netzwerk-Einstellungen uebernehmen, BEVOR die
    # Engine hochfaehrt - sie startet damit gleich in der vom Nutzer im
    # Settings-Modal gewaehlten Konfiguration, nicht mit Werkseinstellungen.
    dmx_engine.configure(
        artnet_enabled=state.artnet_enabled,
        artnet_target_ip=state.artnet_ip,
        artnet_bind_ip=state.artnet_bind_ip,
        sacn_enabled=state.sacn_enabled,
        enttec_enabled=state.enttec_enabled,
        enttec_port=state.enttec_port,
        enttec_universe=state.enttec_universe,
    )
    defaults_seed.seed_all()                       # Standard-Scheinwerfer (GDTF) und Demo-Shows aus defaults/, einmalig
    try:
        open_first_start_demo()                    # frische Installation: Demo-Show gleich oeffnen (vor dem Wiederanlauf des Live-Zustands unten)
    except Exception:
        logger.exception("Erststart: Demo-Show konnte nicht geoeffnet werden")
    try:
        seed_example_layouts()
    except Exception:
        logger.exception("Beispiel-Layouts konnten nicht angelegt werden")
    try:
        _adopt_startup_layout()
    except Exception:
        logger.exception("Start-Layout konnte nicht gewaehlt werden")
    dmx_engine.start()
    _e = dmx_engine.get_enttec_status()
    _artnet_part  = f"Art-Net ({state.artnet_ip})" if state.artnet_enabled else "Art-Net OFF"
    _sacn_part    = "sACN (Multicast)"              if state.sacn_enabled   else "sACN OFF"
    _enttec_part  = (
        f"Enttec ({state.enttec_port}) {'✓' if _e['connected'] else '✗'}"
        if state.enttec_enabled else "Enttec OFF"
    )
    logger.info("[DMX] %s | %s | %s", _artnet_part, _sacn_part, _enttec_part)
    lan_task = asyncio.create_task(lan.sync_when_started(state.remote_enabled))       # Netzwerk-Zugriff (Remote) einrichten, sobald der Port gebunden ist
    watchdog_task     = asyncio.create_task(_enttec_watchdog())

    # Cue-Execution-Engine (Phase 2): laeuft als eigener Tick-Loop, meldet
    # sich nach jedem Fade-Frame ueber diesen Callback zurueck, statt den
    # EventBus direkt zu kennen (vermeidet einen Zirkelimport).
    cue_engine.set_update_callback(_cue_engine_update)
    cue_engine.set_playback_callback(_cue_playback_update)
    cue_engine.set_cuelists_changed_callback(_broadcast_cuelists_changed)
    # Automatische CMD-Ausfuehrung (Cue.cmd, siehe cue_engine._run_cue_cmd):
    # nutzt denselben generischen Broadcast-Kanal + Log-Callback wie der
    # "run_command"-WS-Handler weiter unten - EIN Codepfad fuer beide Ausloeser.
    cue_engine.set_broadcast_callback(_broadcast_generic)
    cue_engine.set_command_log_callback(_broadcast_command_log)
    cue_engine.start()
    logger.info("[CUE] engine started (%d Hz)", FADE_FPS)
    fx_engine.start()
    fx_monitor_task = asyncio.create_task(_fx_monitor_pump())
    await _restore_showfile_state()
    _host_baseline = _strip_panels(state.panels) if state.last_active_layout else None

    async def _startup_update_check() -> None:
        """Kurz nach dem Start einmal nach einer neuen Version sehen (nur wenn eingeschaltet; ohne Netz bleibt es still). Die Oberflaeche fragt das Ergebnis mit /api/update/status ab."""
        await asyncio.sleep(4)
        if state.update_check_enabled:
            await updater.check()

    update_task = asyncio.create_task(_startup_update_check())
    yield
    update_task.cancel()
    lan_task.cancel()
    watchdog_task.cancel()
    fx_monitor_task.cancel()
    fx_engine.stop()
    cue_engine.stop()
    dmx_engine.shutdown()
    host_cameras.stop_all()
    logger.info("[DMX] engine stopped")


app = FastAPI(title="OpenCue", lifespan=lifespan)
#3D-AUS# app.include_router(stage_api.router)
app.include_router(sim_stages.router)
app.include_router(file_manager.router)
app.include_router(about.router)
@app.get("/api/effects")
async def list_effects() -> JSONResponse:
    """Alle verfuegbaren Effekt-Skripte (Benutzerordner, Skripte der geladenen Show) mit
    Kategorie und UI-Parametern - Grundlage der Dropdowns und Dialoge im Frontend."""
    registry.load(_effect_sources())
    return JSONResponse({
        "effects": registry.describe(),
        "categories": fx_categories.describe(),
        "errors": [f for f in registry.files() if not f["ok"]],
    })


@app.delete("/api/effects/{filename}")
async def delete_effect(filename: str) -> JSONResponse:
    """Loescht ein Effekt-Skript aus dem Benutzerordner. Laufende Zuweisungen dieses
    Skripts werden freigegeben; die Effekt-Definitionen bleiben erhalten."""
    name = _script_file_name(filename)
    registry.load(_effect_sources())
    entry = next((f for f in registry.files() if f["name"] == name), None)
    if entry is None:
        return JSONResponse({"error": "not found"}, status_code=404)
    if entry["origin"] != "user":
        return JSONResponse({"error": "Nur Skripte im Benutzerordner koennen geloescht werden."}, status_code=403)
    try:
        Path(entry["path"]).unlink()
    except OSError as exc:
        return JSONResponse({"error": f"Loeschen fehlgeschlagen: {exc}"}, status_code=500)
    registry.load(_effect_sources())
    state.forget_fx_favorite(name)
    released = fx_engine.drop_script_assignments(name)
    await _release_fixtures(released)
    await event_bus.broadcast(_fx_changed_message())
    await event_bus.broadcast(_fx_script_list_message())
    return JSONResponse({"ok": True, "released": len(set(released))})


class NoCacheStaticFiles(StaticFiles):
    """Statische Dateien immer beim Server nachfragen (ETag -> 304, praktisch kostenlos). Ohne Cache-Control behaelt ein
    Browser/WebView2 sie nach einer Heuristik (Bruchteil des Dateialters) stundenlang ohne Rueckfrage - das Programmfenster
    zeigte nach einem Update, auch nach Neustart, noch die alte Oberflaeche."""

    def file_response(self, *args, **kwargs):
        response = super().file_response(*args, **kwargs)
        response.headers["Cache-Control"] = "no-cache"
        return response


app.mount("/static", NoCacheStaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@app.middleware("http")
async def remote_access_guard(request: Request, call_next):
    """Lokale Verbindungen (PyWebView) laufen ohne Passwort. Externe nur bei aktivem Remote
    und gueltiger Session; sonst Login-Seite (GET /) bzw. 401."""
    client = request.client.host if request.client else None
    if remote.is_local(client):
        request.state.cid = None
        return await call_next(request)
    path = request.url.path
    if remote_pwa.is_public(path) and request.method == "GET":
        # Nur die Huelle (Manifest, Service Worker, Offline-Seite, Icons): keine Show-Daten, ohne Anmeldung.
        request.state.cid = remote.validate(request.cookies.get(remote.SESSION_COOKIE))
        return await call_next(request)
    if not state.remote_enabled:
        if request.method == "GET" and path in ("/", "/remote/"):
            return HTMLResponse(remote.login_page(), status_code=403)
        return JSONResponse({"error": "remote access disabled"}, status_code=403)
    if path == "/auth/login" and request.method == "POST":
        return await call_next(request)
    if request.method == "GET" and path in ("/", "/remote"):
        # Externe Geraete laufen immer unter /remote/ - nur dort gilt der Service Worker.
        return RedirectResponse("/remote/", status_code=302)
    cid = remote.validate(request.cookies.get(remote.SESSION_COOKIE))
    if cid is None:
        if request.method == "GET" and path == "/remote/":
            return HTMLResponse(remote.login_page())   # 200: die Start-URL der installierten App
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    request.state.cid = cid
    return await call_next(request)


@app.post("/auth/login")
async def auth_login(request: Request) -> JSONResponse:
    if not state.remote_enabled:
        return JSONResponse({"ok": False}, status_code=403)
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"ok": False}, status_code=400)
    result = remote.login(request.client.host if request.client else "?", str(body.get("password", "")),
                          request.cookies.get(remote.CLIENT_COOKIE))
    ip = request.client.host if request.client else "?"
    if result["ok"]:
        logger.info("[Remote] Anmeldung von %s", ip)
    else:
        logger.warning("[Remote] Anmeldung fehlgeschlagen von %s%s", ip,
                       " (gesperrt)" if result["locked"] else "")
    if not result["ok"]:
        status = 429 if result["locked"] else 401
        return JSONResponse({"ok": False, "locked": result["locked"]}, status_code=status)
    response = JSONResponse({"ok": True})
    # Sitzungs-Cookie ohne Ablaufdatum: es endet mit dem Schliessen des Browsers (serverseitig gilt zusaetzlich SESSION_TTL).
    response.set_cookie(remote.SESSION_COOKIE, result["token"], httponly=True, samesite="strict", path="/")
    response.set_cookie(remote.CLIENT_COOKIE, result["cid"], max_age=remote.CLIENT_COOKIE_TTL,
                        httponly=True, samesite="strict", path="/")
    if request.cookies.get(remote.LEGACY_REMEMBER_COOKIE):
        response.delete_cookie(remote.LEGACY_REMEMBER_COOKIE, path="/")   # Rest des frueheren Remember-Tokens
    return response


@app.get("/api/state")
async def api_state(request: Request) -> JSONResponse:
    """Kompletter aktueller Zustand (wie der Snapshot beim WebSocket-Verbindungsaufbau)
    - fuer Clients, die nach einem Verbindungsverlust nachsynchronisieren."""
    snapshot = _snapshot_for_client(request.state.cid is None, request.state.cid)
    return JSONResponse({"state": snapshot, "live": _live_state_messages()})


@app.post("/api/remote/kick")
async def api_remote_kick(request: Request) -> JSONResponse:
    """Trennt einen externen Client (nur an der Konsole selbst erlaubt, siehe Middleware)."""
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"ok": False}, status_code=400)
    ok = await _kick_client(str(body.get("id", "")))
    return JSONResponse({"ok": ok}, status_code=200 if ok else 404)


@app.post("/auth/logout")
async def auth_logout(request: Request) -> JSONResponse:
    remote.logout(request.cookies.get(remote.SESSION_COOKIE))
    response = JSONResponse({"ok": True})
    response.delete_cookie(remote.SESSION_COOKIE, path="/")
    response.delete_cookie(remote.LEGACY_REMEMBER_COOKIE, path="/")
    return response


@app.get("/", response_class=HTMLResponse)
@app.get("/remote/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    # Externe Clients bekommen die Klasse "is-remote" gleich im HTML (kein Flackern):
    # sie sperrt Scrollen/Ziehen der Seite auf Tablets.
    is_remote = request.state.cid is not None
    response = templates.TemplateResponse(request, "index.html", {
        "is_remote": is_remote,
        "pwa_head": remote_pwa.head_tags() if is_remote else "",
        "asset_v": remote_pwa.build_id(),        # Version in den Datei-Adressen: neuer Stand = neue Adresse = nie ein alter Cache
    })
    response.headers["Cache-Control"] = "no-cache"
    return response


# ---- PWA-Huelle der Remote-Control (siehe app/remote_pwa.py) --------------------------------------------

@app.get("/remote/manifest.webmanifest")
async def remote_manifest() -> Response:
    return JSONResponse(remote_pwa.manifest(), media_type="application/manifest+json",
                        headers={"Cache-Control": "no-cache"})


@app.get("/remote/sw.js")
async def remote_service_worker() -> Response:
    return Response(remote_pwa.service_worker(), media_type="application/javascript",
                    headers={"Cache-Control": "no-cache", "Service-Worker-Allowed": remote_pwa.REMOTE_SCOPE})


@app.get("/remote/offline.html")
async def remote_offline_page() -> Response:
    return HTMLResponse(remote_pwa.offline_page(), headers={"Cache-Control": "no-cache"})


@app.get("/remote/ping")
async def remote_ping() -> JSONResponse:
    """Erreichbarkeit fuer die Offline-Seite (laeuft immer live, nie aus dem Cache)."""
    return JSONResponse({"ok": True, "enabled": bool(state.remote_enabled)}, headers={"Cache-Control": "no-store"})


@app.get("/favicon.ico")
async def favicon() -> Response:
    """Manche Browser fragen /favicon.ico unabhaengig vom <link> an: das Logo als PNG liefern (kein 404)."""
    return FileResponse(remote_pwa.ICON_DIR / "logo-64.png", media_type="image/png", headers={"Cache-Control": "no-cache"})


@app.get("/remote/icons/{name}")
async def remote_icon(name: str) -> Response:
    media_type = remote_pwa.ICON_FILES.get(name)
    path = remote_pwa.ICON_DIR / name
    if media_type is None or not path.is_file():
        return JSONResponse({"error": "not found"}, status_code=404)
    return FileResponse(path, media_type=media_type, headers={"Cache-Control": "no-cache"})


@app.get("/fixture-types")
async def fixture_types() -> JSONResponse:
    from app.fixture_manager import get_fixture_types
    return JSONResponse(get_fixture_types())


@app.get("/api/dmx/enttec-ports")
async def enttec_ports() -> JSONResponse:
    """Gibt alle verfuegbaren seriellen Ports (COM-Port-Dropdown Refresh) zurueck."""
    return JSONResponse({"ports": dmx_engine.scan_enttec_ports()})


@app.get("/api/data-path")
async def get_data_path() -> JSONResponse:
    """Gibt den aktuell konfigurierten Datenpfad zurück."""
    return JSONResponse({
        "path": str(_paths.get_data_root()),
        "is_custom": bool(state.custom_data_path),
    })


@app.post("/api/data-path/open")
async def open_data_folder() -> JSONResponse:
    """Öffnet den Datenpfad im Windows Explorer."""
    import os
    try:
        os.startfile(str(_paths.get_data_root()))
        return JSONResponse({"ok": True})
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)


@app.post("/api/data-path/set")
async def set_data_path(request: Request) -> JSONResponse:
    """Setzt einen benutzerdefinierten Datenpfad (leer = Standard zurücksetzen)."""
    body = await request.json()
    raw = str(body.get("path", "")).strip()
    if raw:
        p = Path(raw)
        if not p.is_absolute():
            return JSONResponse({"error": "Absoluter Pfad erforderlich"}, status_code=400)
        try:
            p.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            return JSONResponse({"error": f"Ordner konnte nicht erstellt werden: {exc}"}, status_code=400)
    state.custom_data_path = raw
    state.save_app_config()
    _paths.refresh_paths()
    new_root = str(_paths.get_data_root())
    await event_bus.broadcast({"type": "data_path_changed", "payload": {"path": new_root, "is_custom": bool(raw)}})
    return JSONResponse({"ok": True, "path": new_root})


@app.get("/api/fixture-types/{fixture_id}/wheels")
async def fixture_type_wheels(fixture_id: str) -> JSONResponse:
    from app.fixture_manager import get_fixture_wheels
    return JSONResponse(get_fixture_wheels(fixture_id))


@app.get("/api/fixture-types/{fixture_id}/beamfx")
async def api_fixture_beamfx(fixture_id: str):
    from app.fixture_manager import get_fixture_beamfx
    return JSONResponse(get_fixture_beamfx(fixture_id))


@app.get("/api/fixture-types/{fixture_id}/shutter")
async def fixture_type_shutter(fixture_id: str) -> JSONResponse:
    from app.fixture_manager import get_fixture_shutter
    return JSONResponse(get_fixture_shutter(fixture_id))


# ---------------------------------------------------------------------------------------------------------------------
# Scheinwerfer-Bibliothek (installierte GDTF-Dateien verwalten, GDTF Share durchsuchen und daraus installieren)
# ---------------------------------------------------------------------------------------------------------------------

def _fixture_usage() -> Dict[str, int]:
    usage: Dict[str, int] = {}
    for fx in state.fixtures.values():
        usage[fx.fixture_type] = usage.get(fx.fixture_type, 0) + 1
    return usage


def _library_error(exc: Exception) -> JSONResponse:
    from app.fixture_library import LibraryError
    if isinstance(exc, LibraryError):
        headers = {"Retry-After": str(exc.extra["retry_after"])} if exc.status == 429 and "retry_after" in exc.extra else None
        return JSONResponse({"error": exc.code, "message": exc.message, **exc.extra}, status_code=exc.status, headers=headers)
    raise exc


def _library_throttle(request: Request, kind: str) -> Optional[JSONResponse]:
    """Bremse fuer die eigene Schnittstelle je Client-Adresse (siehe fixture_library.LIMITS); None = erlaubt."""
    from app import fixture_library
    try:
        fixture_library.throttle(kind, request.client.host if request.client else "?")
    except Exception as exc:
        return _library_error(exc)
    return None


async def _broadcast_library_changed() -> None:
    await event_bus.broadcast({"type": "fixture_library_changed", "payload": {}})


@app.get("/api/library/installed")
async def library_installed() -> JSONResponse:
    from app import fixture_library
    items = await asyncio.to_thread(fixture_library.installed_entries, _fixture_usage())
    return JSONResponse({"items": items, "categories": fixture_library.CATEGORIES, "path": str(_paths.FIXTURES_DIR),
                         "updates": fixture_library.updates_for_installed()},
                        headers={"Cache-Control": "no-store"})


@app.get("/api/library/installed/{fixture_id}/details")
async def library_details(fixture_id: str, request: Request, scope: str = "library") -> JSONResponse:
    from app import fixture_library
    if (limited := _library_throttle(request, "details")) is not None:
        return limited
    try:
        data = await asyncio.to_thread(fixture_library.details, fixture_id, "show" if scope == "show" else "library")
    except Exception as exc:
        return _library_error(exc)
    return JSONResponse(data, headers={"Cache-Control": "no-store"})


@app.get("/api/library/installed/{fixture_id}/thumbnail")
async def library_thumbnail(fixture_id: str, scope: str = "library") -> Response:
    from app import fixture_library
    try:
        data, media_type, mtime = await asyncio.to_thread(fixture_library.thumbnail, fixture_id, "show" if scope == "show" else "library")
    except Exception as exc:
        return _library_error(exc)
    headers = {"Cache-Control": "no-cache", "ETag": f'"{mtime}-{len(data)}"', "X-Content-Type-Options": "nosniff"}
    if media_type == "image/svg+xml":
        headers["Content-Security-Policy"] = "default-src 'none'; style-src 'unsafe-inline'; sandbox"   # kein Skript aus einer fremden SVG
    return Response(content=data, media_type=media_type, headers=headers)


@app.get("/api/library/installed/{fixture_id}/model")
async def library_model(fixture_id: str, request: Request, scope: str = "library") -> JSONResponse:
    """3D-Vorschau: Geometrie-Baum und Netze (Dateien aus der GDTF, sonst Grundformen)."""
    from app import fixture_library
    if (limited := _library_throttle(request, "details")) is not None:
        return limited
    try:
        data = await asyncio.to_thread(fixture_library.model_scene, fixture_id, "show" if scope == "show" else "library")
    except Exception as exc:
        return _library_error(exc)
    return JSONResponse(data, headers={"Cache-Control": "no-store"})


@app.get("/api/library/installed/{fixture_id}/asset")
async def library_asset(fixture_id: str, path: str = "", scope: str = "library") -> Response:
    """Bilder aus dem Ordner wheels/ der GDTF (Gobo-Muster, Farbrad)."""
    from app import fixture_library
    try:
        data, media_type, mtime = await asyncio.to_thread(fixture_library.asset, fixture_id, path, "show" if scope == "show" else "library")
    except Exception as exc:
        return _library_error(exc)
    headers = {"Cache-Control": "no-cache", "ETag": f'"{mtime}-{len(data)}"', "X-Content-Type-Options": "nosniff"}
    if media_type == "image/svg+xml":
        headers["Content-Security-Policy"] = "default-src 'none'; style-src 'unsafe-inline'; sandbox"
    return Response(content=data, media_type=media_type, headers=headers)


@app.delete("/api/library/installed/{fixture_id}")
async def library_uninstall(fixture_id: str) -> JSONResponse:
    from app import fixture_library
    try:
        result = await asyncio.to_thread(fixture_library.uninstall, fixture_id, _fixture_usage())
    except Exception as exc:
        return _library_error(exc)
    await _broadcast_library_changed()
    return JSONResponse(result)


@app.get("/api/library/show")
async def library_show() -> JSONResponse:
    """Tab 'In dieser Show': die Scheinwerfertypen der geladenen Show (Version, Anzahl, Herkunft der Datei)."""
    from app import fixture_library
    items = await asyncio.to_thread(fixture_library.show_types, _fixture_usage())
    return JSONResponse({"items": items, "show_name": state.showfile_name, "saved": bool(state.showfile_path)}, headers={"Cache-Control": "no-store"})


@app.post("/api/library/import")
async def library_import(request: Request) -> JSONResponse:
    """Eigene GDTF-Datei einbauen: der Rohinhalt der Datei im Body, der Dateiname im Header X-Filename (URL-kodiert)."""
    from urllib.parse import unquote
    from app import fixture_library
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > fixture_library.MAX_GDTF_BYTES:
        return JSONResponse({"error": "too_large", "message": "Die Datei ist zu gross (max. 30 MB)"}, status_code=413)
    chunks: List[bytes] = []
    size = 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > fixture_library.MAX_GDTF_BYTES:
            return JSONResponse({"error": "too_large", "message": "Die Datei ist zu gross (max. 30 MB)"}, status_code=413)
        chunks.append(chunk)
    filename = unquote(request.headers.get("x-filename", ""))
    try:
        result = await asyncio.to_thread(fixture_library.install_bytes, b"".join(chunks), filename, "", _fixture_usage())
    except Exception as exc:
        return _library_error(exc)
    await _broadcast_library_changed()
    return JSONResponse(result)


# ---------------------------------------------------------------------------------------------------------------------
# Medien (Video/Audio) der Show: hochladen (Kopie in den lokalen Ordner), abspielen (mit Bereichsanfragen), umbenennen, entfernen
# ---------------------------------------------------------------------------------------------------------------------

async def _broadcast_media_changed() -> None:
    await event_bus.broadcast({"type": "media_changed", "payload": {"media": state.media_payload(), "is_dirty": state.is_dirty}})


def _media_error(exc: Exception) -> JSONResponse:
    if isinstance(exc, media_store.MediaError):
        return JSONResponse({"error": exc.code, "message": exc.message}, status_code=exc.status)
    raise exc


@app.post("/api/media/upload")
async def media_upload(request: Request) -> JSONResponse:
    """Medium hochladen: Rohinhalt im Body, Name im Header X-Filename (URL-kodiert), optional X-Duration-Ms. Die Datei wird in den lokalen Medien-Ordner kopiert."""
    import hashlib
    from urllib.parse import unquote
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > media_store.MAX_FILE_BYTES:
        return JSONResponse({"error": "too_large", "message": "Die Datei ist zu gross (max. 1 GB)"}, status_code=413)
    temp_path, handle = media_store.temp_file()
    sha, size = hashlib.sha256(), 0
    try:
        async for chunk in request.stream():
            size += len(chunk)
            if size > media_store.MAX_FILE_BYTES:
                return JSONResponse({"error": "too_large", "message": "Die Datei ist zu gross (max. 1 GB)"}, status_code=413)
            sha.update(chunk)
            handle.write(chunk)
        handle.close()
        try:
            meta = await asyncio.to_thread(
                media_store.ingest, temp_path, unquote(request.headers.get("x-filename", "")), size, sha.hexdigest(), request.headers.get("x-duration-ms"))
        except Exception as exc:
            return _media_error(exc)
        meta = state.add_media(meta)
        await _broadcast_media_changed()
        return JSONResponse({"ok": True, "media": {**meta, "missing": False}})
    finally:
        if not handle.closed:
            handle.close()
        temp_path.unlink(missing_ok=True)


@app.api_route("/api/media/{media_id}", methods=["GET", "HEAD"])
async def media_get(media_id: str) -> Response:
    meta = state.media.get(media_id)
    path = media_store.file_path(meta) if meta else None
    if meta is None or path is None or not path.is_file():
        return JSONResponse({"error": "not_found"}, status_code=404)
    # Inhaltsadressiert (der Name ist die Pruefsumme): darf lange zwischengespeichert werden; FileResponse bedient Range-Anfragen.
    return FileResponse(path, media_type=meta["mime"], headers={"Cache-Control": "private, max-age=86400, immutable",
                                                               "X-Content-Type-Options": "nosniff"})


@app.patch("/api/media/{media_id}")
async def media_update(media_id: str, request: Request) -> JSONResponse:
    body = await request.json()
    meta = state.update_media(media_id, body.get("name"))
    if meta is None:
        return JSONResponse({"error": "not_found"}, status_code=404)
    await _broadcast_media_changed()
    return JSONResponse({"ok": True, "media": {**meta, "missing": not media_store.exists(meta)}})


@app.delete("/api/media/{media_id}")
async def media_delete(media_id: str) -> JSONResponse:
    """Medium aus der Show nehmen und die Kopie im Medien-Ordner loeschen (ausser eine andere gespeicherte Show nennt sie noch)."""
    meta = state.remove_media(media_id)
    if meta is None:
        return JSONResponse({"error": "not_found"}, status_code=404)
    deleted, kept = False, ""
    other = await asyncio.to_thread(media_store.referenced_elsewhere, media_id, _showfile_dirs(), state.showfile_path)
    if other:
        kept = "other_show"
        kept_name = other
    else:
        deleted = await asyncio.to_thread(media_store.delete_stored, media_id)
    await _broadcast_media_changed()
    result = {"ok": True, "file_deleted": deleted, "kept": kept}
    if kept == "other_show":
        result["show"] = kept_name
    return JSONResponse(result)


# ---------------------------------------------------------------------------------------------------------------------
# Livestream-Quellen (Kamera-URLs) und Weiterleitung durch den Server (siehe app/stream_sources.py)
# ---------------------------------------------------------------------------------------------------------------------

_STREAM_MAX_CONN = 6                      # gleichzeitige Weiterleitungen je Quelle
_stream_conn: Dict[str, int] = {}
_STREAM_PASS_TYPES = ("multipart/x-mixed-replace", "image/", "video/", "audio/", "application/octet-stream")


def _stream_error(exc: Exception) -> JSONResponse:
    if isinstance(exc, stream_sources.StreamError):
        return JSONResponse({"error": exc.code, "message": exc.message}, status_code=exc.status)
    raise exc


def _safe_media_type(content_type: str) -> str:
    """Der Inhaltstyp kommt von der Kamera: nur Bild-/Video-Typen werden so weitergegeben, alles andere (z. B. text/html)
    als nicht ausfuehrbarer Binaerstrom - sonst koennte eine fremde Seite Skripte in unserer Herkunft ausfuehren."""
    low = (content_type or "").lower().strip()
    return content_type if any(low.startswith(p) for p in _STREAM_PASS_TYPES) else "application/octet-stream"


def _stream_headers() -> Dict[str, str]:
    return {"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff", "Content-Security-Policy": "sandbox"}


async def _broadcast_stream_sources() -> None:
    await event_bus.broadcast({"type": "stream_sources_changed", "payload": {"sources": stream_sources.public_list()}})


class _RelayResponse(StreamingResponse):
    """Streaming-Antwort, die die Verbindung zur Kamera IMMER schliesst und den Zaehler freigibt - auch wenn der Client geht, bevor der
    erste Datenblock gesendet wurde (dann laeuft der Generator nie los und kann selbst nichts aufraeumen)."""

    def __init__(self, content: Any, on_close: Any, **kwargs: Any) -> None:
        super().__init__(content, **kwargs)
        self._on_close = on_close

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        try:
            await super().__call__(scope, receive, send)
        finally:
            self._on_close()


async def _relay(source_id: str, response: Any, content_type: str) -> StreamingResponse:
    """Reicht eine laufende Antwort der Kamera Stueck fuer Stueck weiter; beim Schliessen des Clients wird auch die Kamera-Verbindung geschlossen."""
    _stream_conn[source_id] = _stream_conn.get(source_id, 0) + 1
    closed = []

    def release() -> None:
        if closed:
            return
        closed.append(True)
        try:
            response.close()
        except Exception:
            pass
        _stream_conn[source_id] = max(0, _stream_conn.get(source_id, 1) - 1)

    async def body():
        while True:
            chunk = await asyncio.to_thread(response.read1, 16384)
            if not chunk:
                break
            yield chunk
    return _RelayResponse(body(), release, media_type=_safe_media_type(content_type), headers=_stream_headers())


@app.get("/api/streams")
async def streams_list() -> JSONResponse:
    return JSONResponse({"sources": stream_sources.public_list(), "password_storage": stream_sources.password_storage_available()},
                        headers={"Cache-Control": "no-store"})


@app.post("/api/streams")
async def streams_save(request: Request) -> JSONResponse:
    body = await request.json()
    try:
        saved = await asyncio.to_thread(stream_sources.save, body if isinstance(body, dict) else {}, (remote.bound_port,))
    except Exception as exc:
        return _stream_error(exc)
    await _broadcast_stream_sources()
    return JSONResponse({"ok": True, "source": saved})


@app.delete("/api/streams/{source_id}")
async def streams_delete(source_id: str) -> JSONResponse:
    if not stream_sources.delete(source_id):
        return JSONResponse({"error": "not_found"}, status_code=404)
    await _broadcast_stream_sources()
    return JSONResponse({"ok": True})


@app.post("/api/streams/test")
async def streams_test(request: Request) -> JSONResponse:
    """Verbindung pruefen (mit gespeicherter oder gerade eingetippter Quelle; ein leeres Passwort-Feld = das gespeicherte)."""
    body = await request.json()
    body = body if isinstance(body, dict) else {}
    stored = stream_sources.get(str(body.get("id") or "")) or {}
    try:
        url, url_user, url_password = stream_sources.clean_url(body.get("url") or stored.get("url", ""))
    except stream_sources.StreamError as exc:
        return _stream_error(exc)
    row = {"url": url, "user": str(body.get("user") or url_user or stored.get("user", "")),
           "password": body.get("password") or url_password or stored.get("password", "")}
    kind = str(body.get("type") or stored.get("type") or "auto")
    resolved = stream_sources.guess_type(url) if kind == "auto" else kind
    method = "OPTIONS" if resolved == "webrtc" else "GET"
    try:
        response = await asyncio.to_thread(stream_sources.open_upstream, row, None, method, None, None, 6.0)
    except stream_sources.StreamError as exc:
        if resolved == "webrtc" and exc.code == "upstream":
            return JSONResponse({"ok": True, "status": 0, "content_type": "", "resolved_type": resolved, "note": exc.message})
        return _stream_error(exc)
    try:
        head = await asyncio.to_thread(response.read, 256) if method == "GET" else b""
        return JSONResponse({"ok": True, "status": response.status, "content_type": response.headers.get("Content-Type", ""), "resolved_type": resolved, "bytes": len(head)})
    finally:
        response.close()


@app.get("/api/streams/{source_id}/live")
async def stream_live(source_id: str) -> Response:
    row = stream_sources.get(source_id)
    if row is None:
        return JSONResponse({"error": "not_found"}, status_code=404)
    if _stream_conn.get(source_id, 0) >= _STREAM_MAX_CONN:
        return JSONResponse({"error": "busy", "message": "Zu viele gleichzeitige Verbindungen zu dieser Kamera"}, status_code=429)
    try:
        response = await asyncio.to_thread(stream_sources.open_upstream, row)
    except Exception as exc:
        return _stream_error(exc)
    return await _relay(source_id, response, response.headers.get("Content-Type", ""))


@app.get("/api/streams/{source_id}/hls")
async def stream_hls(source_id: str, u: str = "") -> Response:
    """HLS ueber den Server: die Playlist wird umgeschrieben, damit auch jedes Segment ueber diese Schnittstelle (mit den Zugangsdaten) kommt."""
    row = stream_sources.get(source_id)
    if row is None:
        return JSONResponse({"error": "not_found"}, status_code=404)
    target = u or row["url"]
    try:
        response = await asyncio.to_thread(stream_sources.open_upstream, row, target)
    except Exception as exc:
        return _stream_error(exc)
    content_type = response.headers.get("Content-Type", "")
    if stream_sources.looks_like_playlist(target, content_type):
        try:
            raw = await asyncio.to_thread(response.read, stream_sources.MAX_PLAYLIST_BYTES + 1)
            base = response.geturl()
        finally:
            response.close()
        if len(raw) > stream_sources.MAX_PLAYLIST_BYTES:
            return JSONResponse({"error": "too_large"}, status_code=502)
        text = stream_sources.rewrite_playlist(raw.decode("utf-8", "replace"), base, f"/api/streams/{source_id}/hls")
        return Response(content=text, media_type="application/vnd.apple.mpegurl", headers=_stream_headers())
    return await _relay(source_id, response, content_type)


@app.post("/api/streams/{source_id}/whep")
async def stream_whep(source_id: str, request: Request) -> Response:
    """WebRTC (WHEP): das Angebot des Browsers geht mit den Zugangsdaten zur Kamera, die Antwort zurueck. Das Video selbst fliesst
    danach direkt zwischen Browser und Kamera-Server."""
    row = stream_sources.get(source_id)
    if row is None:
        return JSONResponse({"error": "not_found"}, status_code=404)
    offer = await request.body()
    if not offer or len(offer) > 64 * 1024:
        return JSONResponse({"error": "invalid"}, status_code=400)
    try:
        response = await asyncio.to_thread(stream_sources.open_upstream, row, None, "POST", offer, {"Content-Type": "application/sdp"})
        answer = await asyncio.to_thread(response.read, 128 * 1024)
        status = response.status
        response.close()
    except Exception as exc:
        return _stream_error(exc)
    return Response(content=answer, status_code=status, media_type="application/sdp", headers=_stream_headers())


# ---------------------------------------------------------------------------------------------------------------------
# Kameras am Hauptgeraet (siehe app/host_cameras.py): die Liste und das Bild kommen immer vom Computer, auf dem das Programm laeuft
# ---------------------------------------------------------------------------------------------------------------------

@app.get("/api/cameras")
async def cameras_list(refresh: int = 0) -> JSONResponse:
    return JSONResponse(await asyncio.to_thread(host_cameras.overview, bool(refresh)), headers={"Cache-Control": "no-store"})


@app.get("/api/cameras/{camera_id}/status")
async def camera_status(camera_id: str) -> JSONResponse:
    return JSONResponse(host_cameras.status(camera_id), headers={"Cache-Control": "no-store"})


@app.get("/api/cameras/{camera_id}/live")
async def camera_live(camera_id: str, q: str = "medium") -> Response:
    """Bildstrom (MJPEG) der Kamera; alle Betrachter teilen sich EINE Aufnahme. Beim Schliessen des Clients wird der Betrachter abgemeldet."""
    try:
        cap = await asyncio.to_thread(host_cameras.acquire, camera_id, q)
    except Exception as exc:
        return _stream_error(exc)

    async def body():
        seq = 0
        while True:
            seq, frame = await asyncio.to_thread(cap.wait_frame, seq, 5.0)
            if frame is None:
                if cap.state != "running":
                    break
                continue
            yield b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: %d\r\n\r\n" % len(frame) + frame + b"\r\n"
    closed = []

    def release() -> None:
        if not closed:
            closed.append(True)
            host_cameras.release(cap)
    return _RelayResponse(body(), release, media_type="multipart/x-mixed-replace; boundary=frame", headers=_stream_headers())


@app.get("/api/library/online/status")
async def library_online_status() -> JSONResponse:
    from app import fixture_library
    return JSONResponse(fixture_library.share.status(), headers={"Cache-Control": "no-store"})


@app.post("/api/library/online/login")
async def library_online_login(request: Request) -> JSONResponse:
    from app import fixture_library
    if (limited := _library_throttle(request, "login")) is not None:
        return limited
    body = await request.json()
    try:
        status = await asyncio.to_thread(fixture_library.share.login, body.get("user", ""), body.get("password", ""),
                                         body.get("remember") is True)
    except Exception as exc:
        return _library_error(exc)
    return JSONResponse(status)


@app.post("/api/library/online/resume")
async def library_online_resume() -> JSONResponse:
    """Anmeldung mit den (auf Wunsch) gespeicherten Zugangsdaten wiederherstellen."""
    from app import fixture_library
    try:
        status = await asyncio.to_thread(fixture_library.share.resume)
    except Exception as exc:
        return _library_error(exc)
    return JSONResponse(status)


@app.post("/api/library/online/logout")
async def library_online_logout() -> JSONResponse:
    from app import fixture_library
    return JSONResponse(fixture_library.share.logout())


@app.get("/api/library/online/search")
async def library_online_search(request: Request, q: str = "", category: str = "", manufacturer: str = "", offset: int = 0,
                                limit: int = 50, revisions: int = 0, refresh: int = 0, sort: str = "name", verified: int = 0,
                                min_rating: float = 0.0, verified_first: int = 0) -> JSONResponse:
    from app import fixture_library
    if (limited := _library_throttle(request, "search")) is not None:
        return limited
    try:
        result = await asyncio.to_thread(fixture_library.search_online, q, category, manufacturer, offset, limit,
                                         bool(revisions), bool(refresh), sort, bool(verified), min_rating, bool(verified_first))
    except Exception as exc:
        return _library_error(exc)
    return JSONResponse(result, headers={"Cache-Control": "no-store"})


@app.post("/api/library/online/install")
async def library_online_install(request: Request) -> JSONResponse:
    from app import fixture_library
    if (limited := _library_throttle(request, "install")) is not None:
        return limited
    body = await request.json()
    rid = body.get("rid")
    replace = body.get("replace") or ""
    if replace and (not isinstance(replace, str) or replace != Path(replace).name or "/" in replace or "\\" in replace):
        return JSONResponse({"error": "invalid", "message": "Ungueltige Kennung"}, status_code=400)
    if not isinstance(rid, (int, str)) or isinstance(rid, bool) or not re.fullmatch(r"[0-9A-Za-z_-]{1,40}", str(rid)):
        return JSONResponse({"error": "invalid", "message": "Ungueltige Kennung"}, status_code=400)
    try:
        result = await asyncio.to_thread(fixture_library.install_from_share, rid, replace, _fixture_usage())
    except Exception as exc:
        return _library_error(exc)
    await _broadcast_library_changed()
    return JSONResponse(result)


def _showfile_header(path: Path) -> Dict[str, Any]:
    """Name und Speicherzeit aus dem Dateikopf (beide Felder stehen am Anfang der Showfile). Grosse Showfiles - mit eingebetteten
    Medien - muessen fuer die Liste nicht komplett geparst werden."""
    with open(path, "rb") as handle:
        head = handle.read(4096).decode("utf-8", "replace")
    out: Dict[str, Any] = {}
    for key in ("showfile_name", "saved_at"):
        match = re.search(r'"' + key + r'"\s*:\s*("(?:[^"\\]|\\.)*")', head)
        if match:
            out[key] = json.loads(match.group(1))
    return out


@app.get("/showfiles")
async def list_showfiles() -> JSONResponse:
    files = []

    directory = _paths.SHOWFILES_DIR
    if directory.is_dir():
        for p in sorted(directory.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True):
            try:
                data = _showfile_header(p) if p.stat().st_size > 2_000_000 else json.loads(p.read_text(encoding="utf-8"))
                files.append({"name": data.get("showfile_name", p.stem), "saved_at": data.get("saved_at", ""), "path": str(p)})
            except Exception:
                files.append({"name": p.stem, "saved_at": "", "path": str(p)})

    return JSONResponse(files)


# ---- Showfile-Verwaltung (Dialog "Showfiles verwalten") -------------------------------------------------------
# Das Showfile ist global (ein geladenes Showfile fuer alle Geraete); "Gespeichert/Ungespeichert" ist state.is_dirty.
# Speichern/Neu/Oeffnen bleiben die bestehenden Nachrichten (save_show, save_show_as, new_show, load_show).

def _showfile_dirs() -> List[Path]:
    """Ordner, in denen Showfiles verwaltet werden duerfen."""
    return [_paths.SHOWFILES_DIR]


def _managed_showfile(path_str: str) -> Optional[Path]:
    """Die Showfile-Datei zu einem Pfad, wenn sie direkt in einem erlaubten Showfile-Ordner liegt (sonst None)."""
    try:
        path = Path(path_str)
        if path.suffix != ".json" or not path.is_file():
            return None
        resolved = path.resolve()
        for directory in _showfile_dirs():
            if resolved.parent == directory.resolve():
                return path
    except (OSError, ValueError):
        pass
    return None


def _same_path(a: Optional[str], b: Optional[Path]) -> bool:
    if not a or b is None:
        return False
    try:
        return Path(a).resolve() == b.resolve()
    except (OSError, ValueError):
        return False


def _showfile_status() -> Dict[str, Any]:
    path = state.showfile_path
    return {"name": state.showfile_name, "path": path, "dirty": bool(state.is_dirty), "saved": bool(path and Path(path).is_file())}


async def _announce_showfiles_changed() -> None:
    await event_bus.broadcast({"type": "showfile_status_changed", "payload": {}})


@app.get("/api/showfiles/status")
async def showfile_status() -> JSONResponse:
    return JSONResponse(_showfile_status())


@app.post("/api/showfiles/rename")
async def rename_showfile(request: Request) -> JSONResponse:
    body = await request.json()
    old_path = _managed_showfile(str(body.get("path", "")))
    new_name = str(body.get("new_name", "")).strip()
    if old_path is None or old_path.parent.resolve() != _paths.SHOWFILES_DIR.resolve():
        return JSONResponse({"error": "not found"}, status_code=404)
    if not new_name:
        return JSONResponse({"error": "name required"}, status_code=400)
    new_path = old_path.with_name(_safe_layout_filename(new_name) + ".json")
    same_file = new_path.exists() and old_path.samefile(new_path)         # nur Gross-/Kleinschreibung geaendert
    if new_path.exists() and not same_file:
        if _same_path(state.showfile_path, new_path):
            return JSONResponse({"ok": False, "error": "in_use", "name": new_name}, status_code=409)   # geladenes Showfile
        if not body.get("overwrite"):
            return JSONResponse({"ok": False, "error": "exists", "name": new_name, "path": str(new_path)}, status_code=409)
    try:
        data = json.loads(old_path.read_text(encoding="utf-8"))
    except Exception:
        return JSONResponse({"error": "invalid file"}, status_code=400)
    data["showfile_name"] = new_name
    target = old_path if same_file else new_path
    target.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    if not same_file:
        old_path.unlink()
    final = old_path if same_file else new_path
    if _same_path(state.showfile_path, old_path):
        # Das geladene Showfile wurde umbenannt: Arbeitsspeicher behaelt Inhalt und "ungespeichert"-Stand
        state.showfile_name = new_name
        state.showfile_path = str(final)
        state.last_showfile_path = str(final)
        state.save_app_config()
    await _announce_showfiles_changed()
    return JSONResponse({"ok": True, "path": str(final), "name": new_name})


@app.post("/api/showfiles/duplicate")
async def duplicate_showfile(request: Request) -> JSONResponse:
    """Legt eine lokale Kopie einer gespeicherten Showfile-Datei an Laedt sie nicht."""
    body = await request.json()
    src = _managed_showfile(str(body.get("path", "")))
    if src is None:
        return JSONResponse({"error": "not found"}, status_code=404)
    try:
        data = json.loads(src.read_text(encoding="utf-8"))
    except Exception:
        return JSONResponse({"error": "invalid file"}, status_code=400)
    directory = _paths.SHOWFILES_DIR
    new_name = _copy_name(str(data.get("showfile_name", src.stem)), directory)
    data["showfile_name"] = new_name
    directory.mkdir(parents=True, exist_ok=True)
    new_path = directory / (_safe_layout_filename(new_name) + ".json")
    new_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    await _announce_showfiles_changed()
    return JSONResponse({"ok": True, "path": str(new_path), "name": new_name})


@app.post("/api/showfiles/delete")
async def delete_showfile(request: Request) -> JSONResponse:
    body = await request.json()
    path = _managed_showfile(str(body.get("path", "")))
    if path is None:
        return JSONResponse({"error": "not found"}, status_code=404)
    was_loaded = _same_path(state.showfile_path, path)
    media_ids = await asyncio.to_thread(media_store.ids_in_showfile, path)
    path.unlink()
    # Medien-Kopien, die nur diese Show brauchte, gehen mit: nicht in der geladenen Show und in keiner anderen gespeicherten
    media_deleted = 0
    for media_id in media_ids:
        if media_id in state.media:
            continue
        if await asyncio.to_thread(media_store.referenced_elsewhere, media_id, _showfile_dirs(), None):
            continue
        if await asyncio.to_thread(media_store.delete_stored, media_id):
            media_deleted += 1
    if was_loaded:
        # Die geladene Show bleibt im Arbeitsspeicher erhalten, hat aber keine Datei mehr: gilt als ungespeichert.
        state.showfile_path = None
        state.last_showfile_path = None
        state.is_dirty = True
        state.save_app_config()
    await _announce_showfiles_changed()
    return JSONResponse({"ok": True, "was_loaded": was_loaded, "media_deleted": media_deleted})


# ---- Layout-Stand je Geraet und Live-Sync beim Ueberschreiben -----------------------------------------------
# Jedes Geraet (Konsole, jedes Remote-Geraet) hat sein eigenes Panel-Layout im Arbeitsspeicher. Merkmal "ungespeicherte
# Aenderungen" = Panels (ohne ui_state) weichen vom Stand beim Laden/Speichern ab. Wird ein Layout von einem Geraet
# ueberschrieben, bekommen alle anderen Geraete, die genau dieses Layout zeigen, die neue Anordnung - oder, bei eigenen
# ungespeicherten Aenderungen, nur einen Hinweis (layout_update_notice).
_host_baseline: Optional[List[Dict[str, Any]]] = None
_layout_written: Optional[str] = None     # Dateiname, den _write_active_layout zuletzt geschrieben hat


def _strip_panels(panels: List[Any]) -> List[Dict[str, Any]]:
    result = []
    for panel in panels:
        item = asdict(panel)
        item.pop("ui_state", None)
        result.append(item)
    return result


def _host_layout_filename() -> Optional[str]:
    if state.last_active_layout_path:
        return Path(state.last_active_layout_path).name
    if state.last_active_layout:
        return _safe_layout_filename(state.last_active_layout) + ".json"
    return None


def _layout_status_for(cid: Optional[str]) -> Dict[str, Any]:
    """Aktuell geladenes Layout eines Geraets (cid; None = Konsole) und ob es ungespeicherte Aenderungen hat."""
    if cid:
        sess = remote.session_for(cid)
        layout = sess.layout or {}
        name, filename = layout.get("name"), layout.get("filename")
        dirty = bool(name) and (sess.baseline is None or _strip_panels(sess.panels) != sess.baseline)
    else:
        name, filename = state.last_active_layout, _host_layout_filename()
        dirty = bool(name) and (_host_baseline is None or _strip_panels(state.panels) != _host_baseline)
    return {"name": name or None, "filename": filename if name else None, "dirty": bool(dirty)}


async def _announce_layouts_changed() -> None:
    """Alle Geraete holen Layout-Liste und -Status neu (nach Speichern, Umbenennen, Duplizieren, Loeschen ...)."""
    await event_bus.broadcast({"type": "layout_status_changed", "payload": {}})


def _local_layout_path(filename: str) -> Optional[Path]:
    """Pfad einer lokalen Layout-Datei; None bei unzulaessigem Dateinamen (kein Pfad) oder fehlender Datei."""
    if not filename or Path(filename).name != filename or not filename.endswith(".json"):
        return None
    path = _paths.LAYOUTS_DIR / filename
    return path if path.is_file() else None


def _fresh_copy(panels: List[Any]) -> List[Any]:
    return panels_from_dicts([asdict(p) for p in panels])


async def _propagate_layout_update(filename: str, name: str, panels: List[Any], saver_cid: Optional[str]) -> None:
    """Gibt eine ueberschriebene Layout-Datei an die anderen Geraete weiter, die dieses Layout zeigen."""
    global _host_baseline
    targets: List[Any] = [(cid, sess) for cid, sess in list(remote.sessions.items())
                          if cid != saver_cid and sess.layout and sess.layout.get("filename") == filename]
    for cid, sess in targets:
        dirty = sess.baseline is None or _strip_panels(sess.panels) != sess.baseline
        notice = {"type": "layout_update_notice", "payload": {"filename": filename, "name": name, "applied": not dirty}}
        if not dirty:
            sess.panels = _fresh_copy(panels)
            sess.baseline = _strip_panels(sess.panels)
            sess.undo.clear()
            await event_bus.send_to_client(cid, {"type": "panels_changed", "payload": {"panels": sess.panels_as_dicts()}})
        await event_bus.send_to_client(cid, notice)
    if saver_cid is not None and _host_layout_filename() == filename:
        # Die Konsole zeigt dasselbe Layout wie das speichernde Remote-Geraet.
        dirty = _host_baseline is None or _strip_panels(state.panels) != _host_baseline
        notice = {"type": "layout_update_notice", "payload": {"filename": filename, "name": name, "applied": not dirty}}
        if not dirty:
            state.panels = _fresh_copy(panels)
            _host_baseline = _strip_panels(state.panels)
            undo_history.clear()
            await event_bus.broadcast({"type": "panels_changed", "payload": {"panels": state.panels_as_dicts()}})
        await event_bus.send_to_local(notice)


async def _flush_layout_written() -> None:
    """Nach _write_active_layout() (Showfile speichern): die Konsole hat ihr aktives Layout ueberschrieben."""
    global _layout_written, _host_baseline
    filename, _layout_written = _layout_written, None
    if not filename:
        return
    _host_baseline = _strip_panels(state.panels)
    await _propagate_layout_update(filename, state.last_active_layout or filename, state.panels, None)
    await _announce_layouts_changed()


def _write_active_layout() -> None:
    """Schreibt die Panels in die aktive Layout-Datei. Nur bei einem expliziten
    Speichern aufrufen (Strg+S, Speichern-Button, Beenden mit Speichern) -
    Panel-Aenderungen selbst bleiben bis dahin nur im Speicher.
    No-op, falls kein Layout aktiv ist."""
    if not state.last_active_layout:
        return
    try:
        filename = _safe_layout_filename(state.last_active_layout) + ".json"
        if state.last_active_layout_path:
            path = Path(state.last_active_layout_path)
        else:
            path = _paths.LAYOUTS_DIR / filename
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
        else:
            data = {
                "name": state.last_active_layout,
                "created_at": _dt.now().isoformat(timespec="seconds"),
                "is_favorite": False,
            }
        data["panels"] = state.panels_as_dicts()
        data.pop("remote", None)   # Rest des frueheren Remote-Geometrie-Modells
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        global _layout_written
        _layout_written = path.name
    except Exception as exc:
        logger.warning("Layout-Auto-Save fehlgeschlagen: %s", exc)


# ---- Mitgelieferte Beispiel-Layouts: JSON-Dateien in defaults/layouts (siehe defaults/README.md) --------------------
def _load_default_layouts() -> List[Dict[str, Any]]:
    """Die Layout-Vorlagen aus defaults/layouts, nach Dateiname sortiert; unlesbare oder leere Dateien werden uebersprungen."""
    templates: List[Dict[str, Any]] = []
    directory = _paths.default_layouts_dir()
    if not directory.is_dir():
        return templates
    for path in sorted(directory.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            logger.warning("Layout-Vorlage nicht lesbar: %s", path.name)
            continue
        panels = data.get("panels") if isinstance(data, dict) else None
        if isinstance(panels, list) and any(isinstance(p, dict) and p.get("type") for p in panels):
            templates.append(data)
        else:
            logger.warning("Layout-Vorlage ohne Panels uebersprungen: %s", path.name)
    return templates


def _default_layout_name(template: Dict[str, Any], language: str, fallback: str) -> str:
    """Anzeigename der Vorlage: Text, oder je Sprache (fehlt sie: en, sonst der erste Eintrag)."""
    name = template.get("name")
    if isinstance(name, dict):
        name = name.get(language) or name.get("en") or next(iter(name.values()), "")
    return name.strip() if isinstance(name, str) and name.strip() else fallback


def seed_example_layouts() -> List[str]:
    """Legt die Layouts aus defaults/layouts einmalig an (nicht ueberschreibend; danach wie jedes Layout loesch- und
    aenderbar). Gibt die neuen Dateien zurueck. Fehlen die Vorlagen (unvollstaendiger Build), wird nichts angelegt und
    beim naechsten Start erneut versucht."""
    if state.example_layouts_seeded:
        return []
    templates = _load_default_layouts()
    if not templates:
        return []
    created: List[str] = []
    defaults = state.panel_defaults
    known = set(Panel.__dataclass_fields__)
    now = _dt.now().isoformat(timespec="seconds")
    for index, template in enumerate(templates, start=1):
        name = _default_layout_name(template, state.language, f"Layout {index}")
        path = _paths.LAYOUTS_DIR / (_safe_layout_filename(name) + ".json")
        if path.exists():
            continue
        panels = []
        for number, item in enumerate(template["panels"]):
            if not isinstance(item, dict) or not item.get("type"):
                continue
            fields = {k: v for k, v in item.items() if k in known and k != "id"}
            fields.setdefault("z_index", 10 + number)
            fields.setdefault("background_color", defaults["background_color"])
            fields.setdefault("text_color", defaults["text_color"])
            fields.setdefault("header_background_color", defaults["header_background_color"])
            fields.setdefault("drop_shadow", bool(defaults["shadow_enabled"]))
            fields.setdefault("corner_style", defaults.get("corner_style", "global"))
            panels.append(asdict(Panel(id=str(uuid.uuid4()), **fields)))
        data = {"name": name, "created_at": now, "is_favorite": False, "panels": panels}
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        created.append(path.name)
    state.example_layouts_seeded = True
    state.save_app_config()
    return created


def open_first_start_demo() -> Optional[str]:
    """Frische Installation (keine app_config.json): die mitgelieferte Demo-Show (defaults/showfiles, nach dem Anlegen im Showfile-Ordner) wird gleich geoeffnet, damit das Programm
    nicht leer startet. Danach nie wieder (Flag first_start_done); wer schon eine Konfiguration hat, bekommt nichts geoeffnet. Gibt den Namen der geoeffneten Show zurueck."""
    if state.first_start_done:
        return None
    state.first_start_done = True
    opened: Optional[str] = None
    if not state.showfile_path and not state.fixtures:
        templates = sorted(_paths.default_shows_dir().glob("*.json")) if _paths.default_shows_dir().is_dir() else []
        for template in templates:
            candidate = _paths.SHOWFILES_DIR / template.name
            if candidate.is_file():
                try:
                    state.load_showfile(candidate)
                    opened = candidate.stem
                    break
                except Exception:
                    logger.exception("Demo-Show %s konnte nicht geoeffnet werden", candidate.name)
    state.save_app_config()
    return opened


def _adopt_startup_layout() -> None:
    """Die Konsole startet mit ihrem zuletzt geladenen Layout (Name in der app_config.json, Panels aus layouts/). Gibt es das nicht mehr
    (frische Installation, Layout geloescht oder verschoben), wird das erste Layout der Liste geladen - Favoriten zuerst, sonst nach
    Anlagedatum -, damit die Oberflaeche nicht leer startet. Ohne jedes Layout bleibt sie leer."""
    name = _host_layout_filename()
    if name and (_paths.LAYOUTS_DIR / name).is_file():
        return
    state.last_active_layout = None
    state.last_active_layout_path = None
    candidates = []
    for path in _paths.LAYOUTS_DIR.glob("*.json") if _paths.LAYOUTS_DIR.is_dir() else []:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        candidates.append((not bool(data.get("is_favorite", False)), str(data.get("created_at", "")), path.name, path, data))
    if not candidates:
        return
    candidates.sort(key=lambda c: c[:3])
    _, _, _, path, data = candidates[0]
    state.panels = panels_from_dicts(data.get("panels", []))
    state.last_active_layout = data.get("name", path.stem)
    state.last_active_layout_path = str(path)
    state.save_app_config()
    logger.info("[LAYOUT] Start-Layout: %s", state.last_active_layout)


_app_loop: Optional[asyncio.AbstractEventLoop] = None
_last_save_ok = False


def _apply_panels_ui(panels_ui: Any, cid: Optional[str] = None) -> None:
    """Uebernimmt den UI-Zustand der Panels - beim Host oder im Layout des externen Clients."""
    if cid:
        remote.apply_panels_ui(remote.session_for(cid), panels_ui)
    elif isinstance(panels_ui, dict):
        for panel_id, ui_state in panels_ui.items():
            state.set_panel_ui_state(panel_id, ui_state)


def _save_workspace(name: Optional[str] = None) -> Path:
    """Gebuendeltes manuelles Speichern: Showfile (inkl. Fixture-Werte, DMX-
    Stand und aktiver Cues), aktives Layout mit Panel-Eigenschaften und
    Scroll-/Eingabe-Zustand, sowie die globale app_config.json (ohne Panels)."""
    path = state.save_showfile(name=name)
    _write_active_layout()
    state.save_app_config()
    return path


def request_close_prompt() -> bool:
    """Wird aus main.py im UI-Thread aufgerufen, wenn das Fenster geschlossen
    werden soll. Schickt den Dialog "Beenden mit/ohne Speichern/Abbrechen" an
    die verbundenen Clients. Gibt True zurueck, wenn ein Client den Dialog
    anzeigt (Schliessen dann abbrechen); False, wenn keiner verbunden ist."""
    if _app_loop is None or not event_bus._connections:
        return False
    asyncio.run_coroutine_threadsafe(
        event_bus.broadcast({"type": "close_requested", "payload": {}}), _app_loop
    )
    return True


def _safe_layout_filename(name: str) -> str:
    """Konvertiert einen Layout-Anzeigenamen in einen sicheren Dateinamen (ohne Extension)."""
    safe = re.sub(r'[\\/:*?"<>|]', '_', name.strip())[:60]
    return safe or "layout"


@app.get("/api/layouts")
async def list_layouts() -> JSONResponse:
    layouts = []

    directory = _paths.LAYOUTS_DIR
    if directory.is_dir():
        for p in sorted(directory.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True):
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                layouts.append({
                    "name": data.get("name", p.stem),
                    "filename": p.name,
                    "is_favorite": bool(data.get("is_favorite", False)),
                    "created_at": data.get("created_at", ""),
                })
            except Exception:
                layouts.append({"name": p.stem, "filename": p.name, "is_favorite": False, "created_at": ""})

    layouts.sort(key=lambda x: (not x["is_favorite"], x.get("created_at", "")))
    return JSONResponse(layouts)


@app.post("/api/layouts/save")
async def save_layout(request: Request) -> JSONResponse:
    body = await request.json()
    name = str(body.get("name", "")).strip()
    if not name:
        return JSONResponse({"error": "name required"}, status_code=400)
    cid = request.state.cid
    directory = _paths.LAYOUTS_DIR
    filename = _safe_layout_filename(name) + ".json"
    path = directory / filename
    # Eine andere Layout-Datei wird nie stillschweigend ueberschrieben (nur das gerade geladene Layout darf es, oder
    # der Aufrufer bestaetigt ausdruecklich mit overwrite).
    if path.exists() and filename != _layout_status_for(cid)["filename"] and not body.get("overwrite"):
        return JSONResponse({"ok": False, "error": "exists", "name": name, "filename": filename}, status_code=409)
    _apply_panels_ui(body.get("panels_ui"), cid)
    now = _dt.now().isoformat(timespec="seconds")
    data: Dict[str, Any] = {
        "name": name,
        "created_at": now,
        "is_favorite": False,
        "panels": remote.session_for(cid).panels_as_dicts() if cid else state.panels_as_dicts(),
    }
    if path.exists():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
            data["is_favorite"] = existing.get("is_favorite", False)
            data["created_at"] = existing.get("created_at", now)
        except Exception:
            pass
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    global _host_baseline
    if cid:  # das gespeicherte Layout ist jetzt das Layout dieses Geraets
        sess = remote.session_for(cid)
        sess.layout = {"filename": filename, "name": name}
        sess.baseline = _strip_panels(sess.panels)
        saved_panels = sess.panels
    else:    # das aktive Layout des Hosts gehoert nur dem Host
        state.last_active_layout = name
        state.last_active_layout_path = str(path)
        state.save_app_config()
        _host_baseline = _strip_panels(state.panels)
        saved_panels = state.panels
    # Live-Sync: andere Geraete, die genau dieses Layout zeigen, uebernehmen die neue Version (oder bekommen einen Hinweis)
    await _propagate_layout_update(filename, name, saved_panels, cid)
    await _announce_layouts_changed()
    return JSONResponse({"ok": True, "filename": filename})


@app.post("/api/layouts/load")
async def load_layout(request: Request) -> JSONResponse:
    body = await request.json()
    filename = str(body.get("filename", "")).strip()
    if not filename:
        return JSONResponse({"error": "filename required"}, status_code=400)
    path = _paths.LAYOUTS_DIR / filename
    if not path.exists():
        return JSONResponse({"error": "not found"}, status_code=404)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return JSONResponse({"error": "invalid file"}, status_code=400)
    panels_list = panels_from_dicts(data.get("panels", []))
    cid = request.state.cid
    if cid:  # externer Client: nur das eigene Layout wechseln
        sess = remote.session_for(cid)
        sess.panels = panels_list
        sess.undo.clear()
        sess.layout = {"filename": path.name, "name": data.get("name", path.stem)}
        sess.baseline = _strip_panels(panels_list)
        await event_bus.send_to_client(cid, {"type": "panels_changed", "payload": {"panels": sess.panels_as_dicts()}})
        return JSONResponse({"ok": True})
    global _host_baseline
    state.panels = panels_list
    state.last_active_layout = data.get("name", filename.removesuffix(".json"))
    state.last_active_layout_path = str(path)
    _host_baseline = _strip_panels(panels_list)
    undo_history.clear()
    await event_bus.broadcast({"type": "panels_changed", "payload": {"panels": state.panels_as_dicts()}})
    return JSONResponse({"ok": True})


@app.post("/api/layouts/delete")
async def delete_layout(request: Request) -> JSONResponse:
    body = await request.json()
    filename = str(body.get("filename", "")).strip()
    if not filename:
        return JSONResponse({"error": "filename required"}, status_code=400)
    path = _paths.LAYOUTS_DIR / filename
    if path.exists():
        path.unlink()
    if _host_layout_filename() == filename:
        state.last_active_layout = None
        state.last_active_layout_path = None
        state.save_app_config()
    for sess in remote.sessions.values():
        if sess.layout and sess.layout.get("filename") == filename:
            sess.layout, sess.baseline = None, None
    await _announce_layouts_changed()
    return JSONResponse({"ok": True})


@app.get("/api/layouts/status")
async def layout_status(request: Request) -> JSONResponse:
    """Welches Layout hat das anfragende Geraet geladen, und gibt es ungespeicherte Aenderungen?"""
    return JSONResponse(_layout_status_for(request.state.cid))


@app.post("/api/layouts/rename")
async def rename_layout(request: Request) -> JSONResponse:
    body = await request.json()
    filename = str(body.get("filename", "")).strip()
    new_name = str(body.get("new_name", "")).strip()
    old_path = _local_layout_path(filename)
    if old_path is None:
        return JSONResponse({"error": "not found"}, status_code=404)
    if not new_name:
        return JSONResponse({"error": "name required"}, status_code=400)
    new_file = _safe_layout_filename(new_name) + ".json"
    new_path = _paths.LAYOUTS_DIR / new_file
    same_file = new_path.exists() and old_path.samefile(new_path)     # nur Gross-/Kleinschreibung geaendert
    if new_path.exists() and not same_file and not body.get("overwrite"):
        return JSONResponse({"ok": False, "error": "exists", "name": new_name, "filename": new_file}, status_code=409)
    try:
        data = json.loads(old_path.read_text(encoding="utf-8"))
    except Exception:
        return JSONResponse({"error": "invalid file"}, status_code=400)
    data["name"] = new_name
    final_file = old_path.name if same_file else new_file
    target = old_path if same_file else new_path
    target.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    if not same_file:
        old_path.unlink()
    # Geraete, die dieses Layout geladen haben, behalten es unter dem neuen Namen (Panels/Stand bleiben unberuehrt).
    if _host_layout_filename() == filename:
        state.last_active_layout = new_name
        state.last_active_layout_path = str(_paths.LAYOUTS_DIR / final_file)
        state.save_app_config()
    for sess in remote.sessions.values():
        if sess.layout and sess.layout.get("filename") == filename:
            sess.layout = {"filename": final_file, "name": new_name}
    await _announce_layouts_changed()
    return JSONResponse({"ok": True, "filename": final_file, "name": new_name})


def _copy_name(base: str, directory: Optional[Path] = None) -> str:
    """Freier Name fuer eine Kopie: "X (Kopie)", "X (Kopie 2)" ... (bzw. "(copy)")."""
    directory = directory or _paths.LAYOUTS_DIR
    word = "Kopie" if state.language == "de" else "copy"
    n = 1
    while True:
        candidate = f"{base} ({word})" if n == 1 else f"{base} ({word} {n})"
        if not (directory / (_safe_layout_filename(candidate) + ".json")).exists():
            return candidate
        n += 1


@app.post("/api/layouts/duplicate")
async def duplicate_layout(request: Request) -> JSONResponse:
    """Legt eine lokale Kopie einer gespeicherten Layout-Datei an Laedt sie nicht."""
    body = await request.json()
    filename = str(body.get("filename", "")).strip()
    if not filename or Path(filename).name != filename:
        return JSONResponse({"error": "filename required"}, status_code=400)
    src = _paths.LAYOUTS_DIR / filename
    if not src.is_file():
        return JSONResponse({"error": "not found"}, status_code=404)
    try:
        data = json.loads(src.read_text(encoding="utf-8"))
    except Exception:
        return JSONResponse({"error": "invalid file"}, status_code=400)
    new_name = _copy_name(str(data.get("name", src.stem)))
    new_file = _safe_layout_filename(new_name) + ".json"
    # Panels bekommen neue Ids (zwei Layouts teilen sich keine Panel-Ids)
    panels = panels_from_dicts(data.get("panels", []))
    for panel in panels:
        panel.id = str(uuid.uuid4())
    out = {"name": new_name, "created_at": _dt.now().isoformat(timespec="seconds"), "is_favorite": False,
           "panels": [asdict(p) for p in panels]}
    (_paths.LAYOUTS_DIR / new_file).parent.mkdir(parents=True, exist_ok=True)
    (_paths.LAYOUTS_DIR / new_file).write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    await _announce_layouts_changed()
    return JSONResponse({"ok": True, "filename": new_file, "name": new_name})


@app.post("/api/layouts/new")
async def new_layout(request: Request) -> JSONResponse:
    """Legt ein leeres Layout unter einem Namen an (Datei sofort) und laedt es auf dem anfragenden Geraet."""
    body = await request.json()
    name = str(body.get("name", "")).strip()
    if not name:
        return JSONResponse({"error": "name required"}, status_code=400)
    filename = _safe_layout_filename(name) + ".json"
    path = _paths.LAYOUTS_DIR / filename
    if path.exists() and not body.get("overwrite"):
        return JSONResponse({"ok": False, "error": "exists", "name": name, "filename": filename}, status_code=409)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"name": name, "created_at": _dt.now().isoformat(timespec="seconds"),
                                "is_favorite": False, "panels": []}, indent=2, ensure_ascii=False), encoding="utf-8")
    cid = request.state.cid
    global _host_baseline
    if cid:
        sess = remote.session_for(cid)
        sess.panels = []
        sess.undo.clear()
        sess.layout = {"filename": filename, "name": name}
        sess.baseline = []
        await event_bus.send_to_client(cid, {"type": "panels_changed", "payload": {"panels": []}})
    else:
        state.panels = []
        state.last_active_layout = name
        state.last_active_layout_path = str(path)
        state.save_app_config()
        _host_baseline = []
        undo_history.clear()
        await event_bus.broadcast({"type": "panels_changed", "payload": {"panels": []}})
    await _announce_layouts_changed()
    return JSONResponse({"ok": True, "filename": filename, "name": name})


@app.post("/api/layouts/favorite")
async def toggle_favorite_layout(request: Request) -> JSONResponse:
    body = await request.json()
    filename = str(body.get("filename", "")).strip()
    if not filename:
        return JSONResponse({"error": "filename required"}, status_code=400)
    path = _paths.LAYOUTS_DIR / filename
    if not path.exists():
        return JSONResponse({"error": "not found"}, status_code=404)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        data["is_favorite"] = not bool(data.get("is_favorite", False))
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        await _announce_layouts_changed()
        return JSONResponse({"ok": True, "is_favorite": data["is_favorite"]})
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    host = websocket.client.host if websocket.client else None
    local = remote.is_local(host)
    websocket.state.is_local = local
    websocket.state.cid = None
    websocket.state.client_id = uuid.uuid4().hex[:10]
    websocket.state.ip = host or "?"
    websocket.state.ua = websocket.headers.get("user-agent", "")
    websocket.state.connected_at = time.time()
    websocket.state.token = websocket.cookies.get(remote.SESSION_COOKIE)
    websocket.state.kicked = False
    if not local:
        # Ablehnung erst nach accept(), damit der Client den Close-Code (4401/4403) sieht.
        origin = websocket.headers.get("origin")
        same_origin = origin is None or origin.split("://", 1)[-1] == websocket.headers.get("host")
        cid = remote.validate(websocket.cookies.get(remote.SESSION_COOKIE))
        if not state.remote_enabled or not same_origin:
            await websocket.accept()
            await websocket.close(code=4403)
            return
        if cid is None:
            await websocket.accept()
            await websocket.close(code=4401)
            return
        websocket.state.cid = cid
    await websocket.accept()
    await event_bus.connect(websocket)
    if not local:
        logger.info("[Remote] Client %s verbunden (%s)", websocket.state.ip, remote.device_label(websocket.state.ua))

    # Beim Verbindungsaufbau sofort den kompletten aktuellen State schicken
    await event_bus.send_to(websocket, _snapshot_for(websocket))
    for message in _live_state_messages():
        await event_bus.send_to(websocket, message)
    if not local:
        await _broadcast_remote_clients()

    ping_task = asyncio.create_task(_keep_alive(websocket))

    try:
        while True:
            raw_message = await websocket.receive_text()
            await _handle_client_message(websocket, raw_message)
    except WebSocketDisconnect:
        pass
    finally:
        ping_task.cancel()
        event_bus.disconnect(websocket)
        if not local:
            if not websocket.state.kicked:
                logger.info("[Remote] Client %s getrennt", websocket.state.ip)
            try:
                await _broadcast_remote_clients()
            except Exception:
                pass


async def _keep_alive(websocket: WebSocket) -> None:
    """Sendet periodisch ein Ping, damit die Verbindung (z.B. ueber Proxys) offen bleibt."""
    try:
        while True:
            await asyncio.sleep(PING_INTERVAL_SECONDS)
            await event_bus.send_to(websocket, {"type": "ping"})
    except asyncio.CancelledError:
        pass


async def _enttec_watchdog() -> None:
    """Prueft alle 5 Sekunden den USB-DMX-Adapter (Hotplug: connect + disconnect).
    Broadcastet enttec_status_changed bei jeder Statusaenderung."""
    try:
        while True:
            await asyncio.sleep(ENTTEC_WATCHDOG_INTERVAL)
            event = dmx_engine.check_enttec_health()
            if event:
                status = dmx_engine.get_enttec_status()
                await event_bus.broadcast({
                    "type": "enttec_status_changed",
                    "payload": {"status": status},
                })
    except asyncio.CancelledError:
        pass


PANEL_EDIT_MESSAGES = {
    "add_panel", "update_panel", "delete_panel", "clear_panels",
    "bring_panel_to_front", "send_panel_to_back", "move_panel_layer",
    "duplicate_panels", "paste_panels", "delete_panels",
}


async def _apply_undo_redo(message_type: str) -> None:
    current = state.panels_as_dicts()
    previous = undo_history.undo(current) if message_type == "undo" else undo_history.redo(current)
    if previous is None:
        return
    state.panels = panels_from_dicts(previous)
    await event_bus.broadcast({"type": "panels_changed", "payload": {"panels": state.panels_as_dicts()}})


async def _broadcast_fixture_groups() -> None:
    await event_bus.broadcast({"type": "fixture_groups_changed",
                               "payload": {"groups": state.groups, "is_dirty": state.is_dirty}})


async def _handle_client_message(websocket: WebSocket, raw_message: str) -> None:
    """Zentraler Eingangspunkt fuer alle Client-zu-Server-Befehle. Protokolliert
    Panel-Aenderungen fuer Undo/Redo."""
    try:
        message = json.loads(raw_message)
    except json.JSONDecodeError:
        logger.warning("Ungueltiges JSON empfangen: %s", raw_message)
        return

    message_type = message.get("type")
    payload = message.get("payload", {})
    if not isinstance(payload, dict):
        payload = {}

    if not event_bus.is_local(websocket):
        if message_type in remote.LOCAL_ONLY_MESSAGES:
            return  # Fenster, Beenden und Remote-Einstellungen nur an der Konsole selbst
        if message_type in PANEL_EDIT_MESSAGES or message_type in ("undo", "redo"):
            cid = websocket.state.cid
            sess = remote.session_for(cid)
            if message_type == "clear_panels":
                name = payload.get("new_layout_name") or None   # neues, noch nicht gespeichertes Layout dieses Geraets
                sess.layout = {"filename": _safe_layout_filename(name) + ".json", "name": name} if name else None
                sess.baseline = None
            if remote.apply_panel_message(sess, message_type, payload):
                await event_bus.send_to_client(cid, {"type": "panels_changed",
                                                     "payload": {"panels": sess.panels_as_dicts()}})
                if message_type in ("duplicate_panels", "paste_panels"):
                    await event_bus.send_to_client(cid, {"type": "panels_pasted", "payload": {"ids": list(state.last_pasted_ids)}})
            return

    if message_type in ("undo", "redo"):
        await _apply_undo_redo(message_type)
        return

    before = state.panels_as_dicts() if message_type in PANEL_EDIT_MESSAGES else None
    await _process_client_message(websocket, message_type, payload)
    if before is not None and before != state.panels_as_dicts():
        undo_history.record(before)


async def _process_client_message(websocket: WebSocket, message_type: str, payload: Dict[str, Any]) -> None:
    global _last_save_ok
    if message_type == "pong":
        return  # Antwort auf unser Ping, nichts weiter zu tun

    if message_type == "command_value_updated":
        # Fader/Button mit zugewiesenem Befehl wurde bewegt: Wert merken und an alle
        # anderen Clients verteilen (der Absender hat sich selbst schon aktualisiert).
        pattern = str(payload.get("pattern", ""))[:200]
        kind = "button" if payload.get("kind") == "button" else "fader"
        if not pattern:
            return
        message: Dict[str, Any] = {"pattern": pattern, "kind": kind}
        if kind == "fader":
            try:
                value = float(payload.get("value"))
            except (TypeError, ValueError):
                return
            if pattern in _command_values or len(_command_values) < MAX_COMMAND_PATTERNS:
                _command_values[pattern] = value
            message["value"] = value
        await event_bus.broadcast({"type": "command_value_updated", "payload": message}, exclude=websocket)
        return

    if message_type == "ping":
        # Heartbeat des Clients: haelt die Verbindung offen (Safari/iPad, Proxys) und
        # erlaubt dem Client, einen toten Socket am fehlenden Pong zu erkennen.
        await event_bus.send_to(websocket, {"type": "pong"})
        return

    if message_type in ("get_state_snapshot", "request_full_state"):
        await event_bus.send_to(websocket, _snapshot_for(websocket))
        for live_message in _live_state_messages():
            await event_bus.send_to(websocket, live_message)
        return

    if message_type == "set_remote_enabled":
        enabled = state.set_remote_enabled(payload.get("enabled", False))
        if not enabled:
            remote.revoke_all()
            await event_bus.close_remote(4403)
        await lan.sync(enabled)             # Netzwerk-Listener sofort ein-/ausschalten (kein Neustart)
        await _broadcast_remote_clients()   # Toolbar-Icon ein-/ausblenden
        await event_bus.broadcast({"type": "remote_changed", "payload": remote.remote_info(True)})
        return

    if message_type == "remote_refresh":
        # "Aktualisieren" im Remote-Bereich: die Netzwerk-Adressen neu erkennen (WLAN gewechselt, Adapter dazugekommen)
        await lan.sync(state.remote_enabled)
        await event_bus.broadcast({"type": "remote_changed", "payload": remote.remote_info(True)})
        return

    if message_type == "set_remote_password":
        if state.set_remote_password(payload.get("password", "")):
            remote.revoke_all()  # alte Sitzungen verlieren den Zugriff
            await event_bus.close_remote(4401)
        await event_bus.broadcast({"type": "remote_changed", "payload": remote.remote_info(True)})
        return

    if message_type == "set_gui_scale":
        # Die GUI-Skalierung ist pro Geraet (localStorage). Die Konsole sichert hier nur
        # ihren eigenen Standard - kein Broadcast, damit andere Geraete unberuehrt bleiben.
        state.set_gui_scale(payload.get("scale", 1.0))
        return

    if message_type == "set_server_port":
        state.set_server_port(payload.get("port"))
        await event_bus.broadcast({"type": "remote_changed", "payload": remote.remote_info(True)})
        return

    if message_type == "remote_kick":
        await _kick_client(str(payload.get("id", "")))
        return

    if message_type == "set_language":
        language = state.set_language(payload.get("language", "en"))
        await event_bus.broadcast({"type": "language_changed", "payload": {"language": language}})
        return

    if message_type == "set_artnet_enabled":
        enabled = state.set_artnet_enabled(payload.get("enabled", True))
        dmx_engine.set_artnet_enabled(enabled)
        _log_dmx_driver("Art-Net", enabled, state.artnet_ip)
        await event_bus.broadcast({"type": "artnet_enabled_changed", "payload": {"enabled": enabled}})
        return

    if message_type == "set_artnet_ip":
        ip = state.set_artnet_ip(payload.get("ip", ""))
        dmx_engine.set_artnet_target_ip(ip)
        logger.info("[DMX] Art-Net target → %s", ip)
        await event_bus.broadcast({"type": "artnet_ip_changed", "payload": {"ip": ip}})
        return

    if message_type == "set_artnet_bind_ip":
        ip = state.set_artnet_bind_ip(payload.get("ip", ""))
        dmx_engine.set_artnet_bind_ip(ip)
        logger.info("[DMX] Art-Net bind → %s", ip or "auto")
        await event_bus.broadcast({"type": "artnet_bind_ip_changed", "payload": {"ip": ip}})
        return

    if message_type == "set_sacn_enabled":
        enabled = state.set_sacn_enabled(payload.get("enabled", True))
        dmx_engine.set_sacn_enabled(enabled)
        _log_dmx_driver("sACN", enabled, "Multicast")
        await event_bus.broadcast({"type": "sacn_enabled_changed", "payload": {"enabled": enabled}})
        return

    if message_type == "set_enttec_enabled":
        enabled = state.set_enttec_enabled(payload.get("enabled", False))
        error = dmx_engine.set_enttec_enabled(enabled)
        status = dmx_engine.get_enttec_status()
        _port = state.enttec_port or "?"
        if enabled:
            _log_dmx_driver("USB DMX", True,
                            f"{_port} ({'✓' if status['connected'] else '✗ ' + (error or 'error')})")
        else:
            _log_dmx_driver("USB DMX", False)
        await event_bus.broadcast({"type": "artnet_enabled_changed", "payload": {"enabled": state.artnet_enabled}})
        await event_bus.broadcast({"type": "sacn_enabled_changed",   "payload": {"enabled": state.sacn_enabled}})
        await event_bus.broadcast({"type": "enttec_enabled_changed", "payload": {"enabled": enabled}})
        await event_bus.broadcast({"type": "enttec_status_changed",  "payload": {"status": status}})
        return

    if message_type == "set_enttec_port":
        port = state.set_enttec_port(payload.get("port", ""))
        error = dmx_engine.set_enttec_port(port)
        status = dmx_engine.get_enttec_status()
        if state.enttec_enabled:
            logger.info("[DMX] USB DMX port → %s %s", port or "?",
                        "✓" if status["connected"] else f"✗ {error or 'error'}")
        await event_bus.broadcast({"type": "enttec_port_changed",   "payload": {"port": port}})
        await event_bus.broadcast({"type": "enttec_status_changed", "payload": {"status": status}})
        return

    if message_type == "set_enttec_universe":
        universe = state.set_enttec_universe(payload.get("universe", 1))
        dmx_engine.set_enttec_universe(universe)
        logger.info("[DMX] USB DMX universe → %d", universe)
        await event_bus.broadcast({"type": "enttec_universe_changed", "payload": {"universe": universe}})
        return

    if message_type == "reconnect_enttec":
        ok = dmx_engine.reconnect_enttec()
        status = dmx_engine.get_enttec_status()
        _log_dmx_driver("USB DMX", ok, status.get("port", "") if ok else status.get("error", ""))
        await event_bus.broadcast({"type": "enttec_status_changed", "payload": {"status": status}})
        return

    if message_type == "reinitialize_dmx":
        # Globaler DMX-Neustart ohne Anwendungs-Neustart: baut Art-Net-Sockets
        # neu auf, reconnectet Enttec USB und sendet danach den aktuellen
        # Puffer-Inhalt sofort aus (kein sichtbarer Blackout).
        result = dmx_engine.reinitialize_outputs()
        status = result["enttec_status"]
        await event_bus.broadcast({"type": "enttec_status_changed", "payload": {"status": status}})
        # Toast-Feedback an alle Clients (key DMX_REINIT_OK in locale files)
        await event_bus.broadcast({"type": "dmx_reinit_done", "payload": {"ok": result["artnet"]}})
        return

    if message_type == "set_default_universe":
        universe = state.set_default_universe(payload.get("universe", 1))
        await event_bus.broadcast({"type": "default_universe_changed", "payload": {"universe": universe}})
        return

    if message_type == "set_theme":
        theme = state.set_theme(payload)
        await event_bus.broadcast({"type": "theme_changed", "payload": {"theme": theme}})
        return

    if message_type in ("save_theme_profile", "rename_theme_profile", "duplicate_theme_profile",
                        "delete_theme_profile"):
        if message_type == "save_theme_profile":
            state.save_theme_profile(payload.get("name"), payload.get("theme"))
        elif message_type == "rename_theme_profile":
            state.rename_theme_profile(payload.get("name"), payload.get("new_name"))
        elif message_type == "duplicate_theme_profile":
            state.duplicate_theme_profile(payload.get("name"))
        else:
            state.delete_theme_profile(payload.get("name"))
        await event_bus.broadcast({"type": "theme_profiles_changed",
                                   "payload": {"profiles": state.theme_profiles_payload()}})
        return

    if message_type == "set_panel_defaults":
        panel_defaults = state.set_panel_defaults(**{k: v for k, v in payload.items()})
        await event_bus.broadcast({"type": "panel_defaults_changed", "payload": {"panel_defaults": panel_defaults}})
        return

    if message_type == "reset_settings":
        # Settings-Modal -> "Reset Defaults" (nach Bestaetigung im Sub-Dialog).
        # Scoped auf die im Modal editierbaren Felder - Panels/Showfile
        # bleiben unangetastet, siehe reset_settings_to_defaults()'s Docstring.
        defaults = state.reset_settings_to_defaults()
        # configure() ist nur fuer den Start gedacht (siehe dmx_engine.py) und
        # wuerde laufende Sender nicht sauber umschalten - dieselben Live-
        # Setter wie die einzelnen set_artnet_*/set_sacn_enabled-Handler oben.
        dmx_engine.set_artnet_enabled(defaults["artnet_enabled"])
        dmx_engine.set_artnet_target_ip(defaults["artnet_ip"])
        dmx_engine.set_artnet_bind_ip(defaults["artnet_bind_ip"])
        dmx_engine.set_sacn_enabled(defaults["sacn_enabled"])
        dmx_engine.set_enttec_enabled(defaults["enttec_enabled"])
        dmx_engine.set_enttec_port(defaults["enttec_port"])
        dmx_engine.set_enttec_universe(defaults["enttec_universe"])
        defaults["enttec_status"] = dmx_engine.get_enttec_status()
        logger.info("[DMX] reset defaults")
        await event_bus.broadcast({"type": "settings_reset", "payload": defaults})
        return

    if message_type == "add_panel":
        panel_type = payload.get("panel_type")
        if panel_type:
            state.add_panel(panel_type)
            await event_bus.broadcast({"type": "panels_changed", "payload": {"panels": state.panels_as_dicts()}})
        return

    if message_type in ("duplicate_panels", "paste_panels"):
        # Kopien (neue IDs, Versatz, oberste Ebene); der Absender markiert die neuen Panels anschliessend
        created = (state.duplicate_panels(payload.get("ids")) if message_type == "duplicate_panels"
                   else state.paste_panels(payload.get("panels")))
        if created:
            await event_bus.broadcast({"type": "panels_changed", "payload": {"panels": state.panels_as_dicts()}})
            await event_bus.send_to(websocket, {"type": "panels_pasted", "payload": {"ids": [p.id for p in created]}})
        return

    if message_type == "delete_panels":
        if state.delete_panels(payload.get("ids")):
            await event_bus.broadcast({"type": "panels_changed", "payload": {"panels": state.panels_as_dicts()}})
        return

    if message_type == "update_panel":
        panel_id = payload.get("id")
        if panel_id:
            fields = {k: v for k, v in payload.items() if k != "id"}
            state.update_panel(panel_id, **fields)
            await event_bus.broadcast({"type": "panels_changed", "payload": {"panels": state.panels_as_dicts()}})
        return

    if message_type == "delete_panel":
        panel_id = payload.get("id")
        if panel_id:
            state.delete_panel(panel_id)
            await event_bus.broadcast({"type": "panels_changed", "payload": {"panels": state.panels_as_dicts()}})
        return

    if message_type == "clear_panels":
        new_layout_name = payload.get("new_layout_name") or None
        global _host_baseline
        state.panels = []
        state.last_active_layout = new_layout_name
        state.last_active_layout_path = None
        _host_baseline = None
        undo_history.clear()
        await event_bus.broadcast({"type": "panels_changed", "payload": {"panels": []}})
        return

    if message_type == "bring_panel_to_front":
        panel_id = payload.get("id")
        if panel_id:
            state.bring_panel_to_front(panel_id)
            await event_bus.broadcast({"type": "panels_changed", "payload": {"panels": state.panels_as_dicts()}})
        return

    if message_type == "send_panel_to_back":
        panel_id = payload.get("id")
        if panel_id:
            state.send_panel_to_back(panel_id)
            await event_bus.broadcast({"type": "panels_changed", "payload": {"panels": state.panels_as_dicts()}})
        return

    if message_type == "move_panel_layer":
        panel_id = payload.get("id")
        if panel_id:
            state.move_panel_layer(panel_id, payload.get("delta", 0))
            await event_bus.broadcast({"type": "panels_changed", "payload": {"panels": state.panels_as_dicts()}})
        return

    if message_type == "toggle_fullscreen":
        # Dummy-Container-Prinzip, wie bei exit_app: nur ein Flag setzen,
        # main.py's Watcher-Thread ruft window.toggle_fullscreen() Thread-sicher auf.
        fullscreen_toggle_requested.set()
        return

    if message_type == "exit_app":
        # Wie das Schliessen-X: erst der Abfrage-Dialog, Beenden erst nach Entscheidung. Der Dialog
        # erscheint auf dem Geraet, das "Beenden" gewaehlt hat (Konsole: im Fenster, Remote: am Remote-Geraet).
        # Beenden stoppt den Serverprozess - fuer alle Geraete.
        if event_bus.is_local(websocket):
            await event_bus.broadcast({"type": "close_requested", "payload": {}})
        else:
            await event_bus.send_to(websocket, {"type": "close_requested", "payload": {}})
        return

    if message_type == "add_fx" or message_type == "update_fx":
        fx_id = payload.get("id") if message_type == "update_fx" else None
        wanted = str(payload.get("name") or "").strip()
        if wanted and fx_engine.name_taken(wanted, fx_id):          # Effektnamen sind eindeutig
            await EventBus._send(websocket, json.dumps({"type": "error", "payload": {"code": "FX_DUPE", "name": wanted}}))
            return
        saved = fx_engine.save_definition(fx_id, payload)
        if saved is not None:
            state.mark_dirty()
            await event_bus.broadcast(_fx_changed_message())
        return

    if message_type == "preset_apply":
        # Variable auf Fixtures anwenden UND verknuepfen (Platzhalter): Wert und Verknuepfung liegen auf dem Server, Dropdown/Fader folgen daraus
        preset = state.presets.get(str(payload.get("preset_id", "")))
        if preset is not None:
            await _apply_preset_to_fixtures([str(f) for f in payload.get("fixture_ids", [])], preset)
        return

    if message_type == "preset_release":
        # Zurueck auf "Manuell": die Verknuepfung entfaellt, die Werte bleiben, wie sie sind
        ptype = str(payload.get("type", ""))
        changed = False
        for fid in [str(f) for f in payload.get("fixture_ids", [])]:
            changed = state.drop_programmer_refs(fid, types=[ptype]) or changed
        if changed:
            await event_bus.broadcast(_refs_message())
        return

    if message_type == "delete_fx":
        await _release_fixtures(fx_engine.delete_definition(str(payload.get("id", ""))))
        state.mark_dirty()
        await event_bus.broadcast(_fx_changed_message())
        return

    if message_type == "add_fx_group":
        fx_engine.add_group(payload.get("name", ""))
        state.mark_dirty()
        await event_bus.broadcast(_fx_changed_message())
        return

    if message_type == "delete_fx_group":
        fx_engine.delete_group(payload.get("name", ""))
        state.mark_dirty()
        await event_bus.broadcast(_fx_changed_message())
        return

    if message_type == "fx_assign":
        # Vom Programmer-Dropdown: fx_id=None gibt die Attribute wieder frei (Manuell).
        fixture_ids = [fid for fid in payload.get("fixture_ids", []) if fid in state.fixtures]
        fx_id = payload.get("fx_id") or None
        released = fx_engine.assign(fixture_ids, str(payload.get("category", "")), fx_id)
        if fx_id and any([state.drop_programmer_refs(fid, types=[str(payload.get("category", ""))]) for fid in fixture_ids]):
            await event_bus.broadcast(_refs_message())                          # der Effekt gibt diese Kategorie jetzt vor, nicht mehr eine Variable
        await _release_fixtures(released)
        if fixture_ids:
            state.mark_dirty()
        await event_bus.broadcast(_fx_changed_message())
        return

#3D-AUS#     if message_type == "stage_op":
#3D-AUS#         await stage_api.handle_op(payload, websocket)
        return

    if message_type == "fx_script_list":
        await event_bus.send_to(websocket, _fx_script_list_message())
        return

    if message_type == "fx_script_favorite":
        # Lieblings-Stern im Effekt-Studio: gilt fuer alle Geraete (steht in der app_config.json), alle offenen Studios und Dateimanager aktualisieren sich
        name = _script_file_name(payload.get("name", ""))
        if name:
            state.toggle_fx_favorite(name)
            await event_bus.broadcast(_fx_script_list_message())
        return

    if message_type == "fx_script_load":
        name = _script_file_name(payload.get("name", ""))
        registry.load(_effect_sources())
        known = next((f for f in registry.files() if f["name"] == name), None)
        text = Path(known["path"]).read_text(encoding="utf-8") if known else ""
        await event_bus.send_to(websocket, {"type": "fx_script_source", "payload": {"name": name, "text": text}})
        return

    if message_type == "fx_script_save":
        name = _script_file_name(payload.get("name", ""))
        text = str(payload.get("text", ""))
        if not name:
            await event_bus.send_to(websocket, {"type": "fx_script_result", "payload": {
                "ok": False, "name": "", "line": None, "message": "Dateiname fehlt", "active": 0}})
            return
        target = _paths.effects_dir() / f"{name}.fx"
        if target.exists() and not payload.get("overwrite"):
            # eine andere Datei dieses Namens wird nie stillschweigend ersetzt: das Studio fragt nach (overwrite = true)
            await event_bus.send_to(websocket, {"type": "fx_script_result", "payload": {
                "ok": False, "exists": True, "saved": False, "name": name, "line": None, "message": "exists", "active": 0}})
            return
        try:
            _paths.effects_dir().mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8")
        except OSError as exc:
            await event_bus.send_to(websocket, {"type": "fx_script_result", "payload": {
                "ok": False, "name": name, "line": None, "message": f"Speichern fehlgeschlagen: {exc}",
                "active": 0}})
            return
        registry.load(_effect_sources())
        if any(fx.get("kind") == name for fx in state.fx_effects.values()):
            state.is_dirty = True                   # die Show speichert das Skript mit: die neue Fassung gehoert in die Showfile
        result = _compile_result(name, text)
        result["active"] = fx_engine.count_active(name)
        result["saved"] = True                      # die Datei ist geschrieben, auch wenn das Skript noch Fehler hat
        await event_bus.send_to(websocket, {"type": "fx_script_result", "payload": result})
        await event_bus.send_to(websocket, _fx_script_list_message())
        await event_bus.broadcast(_fx_changed_message())
        return

    if message_type == "fx_script_preview":
        # Effekt-Studio: Pruefung + Probelauf + Kurven ohne Scheinwerfer (die Antwort tragt die Anfrage-Nummer `seq`)
        name = _script_file_name(payload.get("name", "")) or "vorschau"
        reply: Dict[str, Any] = {"seq": payload.get("seq"), "ok": False, "line": None, "message": ""}
        try:
            reply.update(await asyncio.to_thread(
                preview_script, name, str(payload.get("text", "")), payload.get("params"), payload.get("count", 3),
                payload.get("duration", 4.0)))
            reply["ok"] = True
        except FxScriptError as exc:
            reply.update({"line": exc.line, "message": exc.message})
        except (FxScriptRuntimeError, ValueError, TypeError) as exc:
            reply["message"] = str(exc)
        await event_bus.send_to(websocket, {"type": "fx_script_preview", "payload": reply})
        return

    if message_type == "close_decision":
        # Vom Dialog "Programm beenden": "save" nur, wenn das Speichern gerade
        # erfolgreich war (Nachrichten kommen in Reihenfolge an). Danach schliesst
        # main.py das Fenster ueber den Watcher-Thread (exit_requested).
        choice = payload.get("choice")
        if choice == "discard" or (choice == "save" and _last_save_ok):
            logger.info("Programm beenden (%s).", choice)
            exit_requested.set()
        return

    # ---- Showfile-Management ----

    if message_type == "new_show":
        state.new_show()
        cue_engine.reset()
        fx_engine.reset_runtime()
        timecode.reset()
        await _broadcast_timecode()
        # Reihenfolge: erst "Show gewechselt" + Snapshot, dann der Live-Zustand (Baseline-Reset,
        # Programmer, Master). So sieht jeder Client zuerst die neue Show und danach ihren Stand.
        await event_bus.broadcast({"type": "show_loaded", "payload": {}})
        await event_bus.broadcast(state.get_snapshot())
        await _restore_showfile_state()
        return

    if message_type == "save_show":
        _apply_panels_ui(payload.get("panels_ui"), websocket.state.cid)
        try:
            path = _save_workspace()
            _last_save_ok = True
            await _flush_layout_written()
            await event_bus.broadcast({
                "type": "show_saved",
                "payload": {
                    "showfile_name": state.showfile_name,
                    "path": str(path),
                    "is_dirty": False,
                },
            })
        except Exception as exc:
            _last_save_ok = False
            logger.error("save_show fehlgeschlagen: %s", exc)
        return

    if message_type == "save_show_as":
        name = str(payload.get("name", "")).strip()
        if not name:
            return
        try:
            _apply_panels_ui(payload.get("panels_ui"), websocket.state.cid)
            path = _save_workspace(name=name)
            await _flush_layout_written()
            _last_save_ok = True
            await event_bus.broadcast({
                "type": "show_saved",
                "payload": {
                    "showfile_name": state.showfile_name,
                    "path": str(path),
                    "is_dirty": False,
                },
            })
        except Exception as exc:
            _last_save_ok = False
            logger.error("save_show_as fehlgeschlagen: %s", exc)
        return

    if message_type == "load_show":
        path = payload.get("path", "")
        if path:
            try:
                state.load_showfile(path)
                cue_engine.reset()
                fx_engine.reset_runtime()
                timecode.reset()
                await _broadcast_timecode()
                # Erst Snapshot der neuen Show (inkl. aktivem Cue, Fortschritt), danach
                # der wiederhergestellte Live-Zustand - alle Clients sind danach konsistent.
                await event_bus.broadcast({"type": "show_loaded", "payload": {}})
                await event_bus.broadcast(state.get_snapshot())
                await _restore_showfile_state()
            except Exception as exc:
                logger.error("load_show fehlgeschlagen: %s", exc)
        return

    # ---- Fixture-Management ----

    if message_type == "add_fixtures":
        try:
            state.add_fixtures_batch(
                fixture_type_id=payload["fixture_type_id"],
                fixture_type_name=payload.get("fixture_type_name", ""),
                channel_count=int(payload["channel_count"]),
                mode=payload.get("mode", "default"),
                name_prefix=str(payload.get("name_prefix", "Fixture")),
                quantity=max(1, int(payload.get("quantity", 1))),
                universe=int(payload.get("universe", 1)),
                start_channel=int(payload.get("start_channel", 1)),
                name_start_index=max(1, int(payload.get("name_start_index", 1))),
            )
            await event_bus.broadcast({
                "type": "fixtures_changed",
                "payload": {"fixtures": state.fixtures_as_dicts(), "is_dirty": state.is_dirty},
            })
        except Exception as exc:
            logger.error("add_fixtures fehlgeschlagen: %s", exc)
        return

    if message_type == "delete_fixtures":
        ids = payload.get("ids", [])
        if ids:
            state.delete_fixtures_bulk(ids)
            await event_bus.broadcast({
                "type": "fixtures_changed",
                "payload": {"fixtures": state.fixtures_as_dicts(), "is_dirty": state.is_dirty},
            })
            await _broadcast_fixture_groups()
        return

    if message_type == "update_fixture":
        fx_id = payload.get("id")
        if fx_id:
            state.update_fixture_patch(
                fixture_id=fx_id,
                universe=int(payload.get("universe", 1)),
                start_channel=int(payload.get("start_channel", 1)),
            )
            await event_bus.broadcast({
                "type": "fixtures_changed",
                "payload": {"fixtures": state.fixtures_as_dicts(), "is_dirty": state.is_dirty},
            })
        return

    if message_type == "set_fixture_sort_index":
        if state.set_fixture_sort_index(payload.get("id"), payload.get("value")) is not None:
            await event_bus.broadcast({
                "type": "fixtures_changed",
                "payload": {"fixtures": state.fixtures_as_dicts(), "is_dirty": state.is_dirty},
            })
        return

    if message_type in ("add_fixture_group", "rename_fixture_group", "delete_fixture_group", "assign_fixture_group"):
        if message_type == "add_fixture_group":
            ok = state.add_fixture_group(payload.get("name")) is not None
        elif message_type == "rename_fixture_group":
            ok = state.rename_fixture_group(payload.get("name"), payload.get("new_name"))
        elif message_type == "delete_fixture_group":
            ok = state.delete_fixture_group(payload.get("name"))
        else:
            ids = payload.get("ids") if isinstance(payload.get("ids"), list) else [payload.get("id")]
            ok = state.assign_fixture_group(ids, payload.get("group"))
        if ok:
            await _broadcast_fixture_groups()
        else:
            await event_bus.send_to(websocket, {"type": "fixture_group_result", "payload": {
                "ok": False, "code": "duplicate" if message_type in ("add_fixture_group", "rename_fixture_group") else "invalid"}})
        return

    if message_type == "rename_fixture":
        fx_id = payload.get("id")
        new_name = str(payload.get("name", "")).strip()
        if fx_id and new_name:
            state.rename_fixture(fx_id, new_name)
            await event_bus.broadcast({
                "type": "fixtures_changed",
                "payload": {"fixtures": state.fixtures_as_dicts(), "is_dirty": state.is_dirty},
            })
        return

    if message_type == "set_fixture_values":
        # Live-Fader-Werte aus dem Programmer-Panel: Das Frontend schickt
        # ABSTRAKTE Werte (dimmer/pan/tilt/color), nicht rohe DMX-Kanal-
        # namen - die sind je nach GDTF-Profil unterschiedlich benannt
        # (additive RGB-Fixtures nutzen "ColorAdd_R/G/B", CMY-Mischer wie
        # die Eurolite TMH-S400 dagegen "ColorSub_C/M/Y"; ein hartcodierter
        # "Red"/"Green"/"Blue"-Name passt auf KEIN reales GDTF-Profil).
        # Werte kommen hier bereits als 0-255-Byte an (Frontend konvertiert
        # vor dem Senden) - siehe apply_abstract_values(pct_values=False)
        # in app/dmx_resolve.py.
        ids = payload.get("ids", [])
        abstract = {
            "dimmer": payload.get("dimmer"),
            "pan": payload.get("pan"),
            "tilt": payload.get("tilt"),
            "pan16": payload.get("pan16"),     # optional: 16-Bit-Wert (0-65535) fuer Fixtures mit Fein-Kanal
            "tilt16": payload.get("tilt16"),
            "color": payload.get("color"),  # {"r":0-255, "g":0-255, "b":0-255}
        }
        for attr in BEAM_ATTRS:
            abstract[attr] = payload.get(attr)
        abstract = {k: v for k, v in abstract.items() if v is not None}

        # Fuer die Command Line ("Store Cue") UND jeden anderen Verbraucher
        # von state.programmer_values im 0-100%-Speicherformat nachfuehren
        # (color bleibt 0-255 RGB) - die hier ankommenden Werte sind sonst
        # ausschliesslich 0-255-Byte (siehe pct_values=False unten).
        pct_abstract: Dict[str, Any] = {}
        for attr in ("dimmer", "pan", "tilt", *BEAM_ATTRS):
            if attr in abstract:
                pct_abstract[attr] = byte_to_pct(abstract[attr])
        for attr in ("pan", "tilt"):          # praezisester Programmer-Wert: 16 Bit, wenn mitgeschickt
            if attr in abstract and abstract.get(attr + "16") is not None:
                pct_abstract[attr] = max(0.0, min(100.0, float(abstract[attr + "16"]) / 655.35))
        if "color" in abstract:
            pct_abstract["color"] = abstract["color"]

        affected_universes: Set[int] = set()
        changed_programmer: Dict[str, Dict[str, Any]] = {}
        # Sammle alle Kanal-Schreiboperationen pro Universum und sende je
        # einen einzigen Frame pro Universum statt pro Kanal (Enttec-Effizienz).
        universe_batches: Dict[int, Dict[int, int]] = {}

        refs_before = {fid: dict(r) for fid, r in state.programmer_refs.items() if fid in ids}
        for fx_id in ids:
            fx = state.fixtures.get(fx_id)
            if fx is None:
                continue
            offsets = fixture_channel_offsets(fx)
            state.release_layers(fx_id, list(pct_abstract))     # der Programmer uebernimmt: Cue-Listen mischen diese Attribute nicht mehr
            resolved = apply_abstract_values(
                fx, abstract, offsets, universe_batches,
                pct_values=False, grand_master=state.effective_master(fx_id),
            )
            if resolved:
                state.set_fixture_values(fx_id, resolved)
                state.set_programmer_values(fx_id, pct_abstract)
                affected_universes.add(fx.universe)
                changed_programmer[fx_id] = dict(pct_abstract)

        # Einmaliger DMX-Frame pro Universum (statt einem Frame pro Kanal).
        # commit_batch() aktualisiert den Snapshot sofort und reiht die Ausgabe
        # non-blocking im dedizierten Ausgabe-Thread (opencue-dmx-output) ein.
        for universe, ch_map in universe_batches.items():
            dmx_engine.commit_batch(universe, ch_map)

        for universe in affected_universes:
            await event_bus.broadcast({
                "type": "dmx_universe_changed",
                "payload": {"universe": universe, "values": dmx_engine.get_universe_snapshot(universe)},
            })
        # Fader, Kacheln und Werteanzeigen aller anderen Clients nachfuehren.
        if changed_programmer:
            await event_bus.broadcast(
                {"type": "programmer_command_update", "payload": {"values": changed_programmer}},
                exclude=websocket,
            )
        if refs_before != {fid: dict(r) for fid, r in state.programmer_refs.items() if fid in ids}:
            await event_bus.broadcast(_refs_message())          # ein fester Wert hat eine Variable abgeloest
        return

    if message_type == "set_fixture_raw_channel":
        # DMX-Direkt-Fader und Rad-Knoepfe/-Fader (Gobo, Prisma, Farbrad, Shutter-Knoepfe, Frost, Iris ...): ein roher Kanalwert. Alles wird im Programmer festgehalten, damit
        # ein Cue (Speichern/Aktualisieren) es uebernimmt: Kanaele mit abstraktem Attribut (Dimmer, Pan, Tilt, Strobe, Gobo, Prisma, Fokus, Zoom) als dieses Attribut (0-100 %),
        # alle anderen als "ch<Offset>" (Byte). Der Absender bekommt dieselbe Rueckmeldung wie die anderen Clients: sie markiert die Werte als angefasst.
        ids = payload.get("ids", [])
        channel_offset = payload.get("channel_offset")
        value = payload.get("value")
        if channel_offset is None or value is None:
            return
        affected_universes2: Set[int] = set()
        raw_changed: Dict[str, Dict[str, Any]] = {}
        for fx_id in ids:
            fx = state.fixtures.get(fx_id)
            if fx is None:
                continue
            channel_offsets = fixture_channel_offsets(fx)
            channel_name = next((name for name, off in channel_offsets.items() if off == int(channel_offset)), None)
            abstract_by_channel = {"Dimmer": "dimmer", "Pan": "pan", "Tilt": "tilt", **beam_attr_by_channel(channel_offsets)}
            raw_value = max(0, min(255, int(round(value))))
            out_value = raw_value
            if channel_name == "Dimmer":
                out_value = int(round(raw_value * state.effective_master(fx_id) / 100.0))
            dmx_engine.commit_batch(fx.universe, {fx.start_channel + int(channel_offset): out_value})
            attr = abstract_by_channel.get(channel_name)
            key = attr if attr else f"ch{int(channel_offset)}"
            state.release_layers(fx_id, [key])                  # der Programmer uebernimmt: Cue-Listen mischen diesen Wert nicht mehr
            if attr:
                state.set_fixture_values(fx_id, {channel_name: raw_value})
                shown = byte_to_pct(raw_value)
            else:
                shown = raw_value
            state.set_programmer_values(fx_id, {key: shown})
            raw_changed.setdefault(fx_id, {})[key] = shown
            affected_universes2.add(fx.universe)
        for universe in affected_universes2:
            await event_bus.broadcast({
                "type": "dmx_universe_changed",
                "payload": {"universe": universe, "values": dmx_engine.get_universe_snapshot(universe)},
            })
        if raw_changed:
            await event_bus.broadcast({"type": "programmer_command_update", "payload": {"values": raw_changed}})
        return

    if message_type == "add_preset":
        new_preset = state.add_preset(
            name=payload.get("name", "Preset"),
            preset_type=payload.get("type", "dimmer"),
            group=payload.get("group", ""),
            values=payload.get("values", {}),
        )
        if new_preset is None:
            await EventBus._send(websocket, json.dumps({
                "type": "error",
                "payload": {"code": "PRESET_DUPE", "name": payload.get("name", "")},
            }))
            return
        await event_bus.broadcast({
            "type": "presets_changed",
            "payload": {
                "presets": {pid: asdict(p) for pid, p in state.presets.items()},
                "preset_groups": list(state.preset_groups),
                "is_dirty": state.is_dirty,
            },
        })
        return

    if message_type == "update_preset":
        preset_id = payload.get("id", "")
        preset = state.update_preset(
            preset_id=preset_id,
            name=payload.get("name"),
            type=payload.get("type"),
            group=payload.get("group"),
            values=payload.get("values"),
        )
        if preset is None:
            # Nur PRESET_DUPE senden wenn das Preset existiert (sonst: unbekannte ID → silent ignore)
            if preset_id in state.presets:
                await EventBus._send(websocket, json.dumps({
                    "type": "error",
                    "payload": {"code": "PRESET_DUPE", "name": payload.get("name", "")},
                }))
            return
        await event_bus.broadcast({
            "type": "presets_changed",
            "payload": {
                "presets": {pid: asdict(p) for pid, p in state.presets.items()},
                "preset_groups": list(state.preset_groups),
                "is_dirty": state.is_dirty,
            },
        })
        await _reapply_preset(preset.id)                  # Platzhalter: Programmer und aktive Cues folgen dem neuen Wert sofort
        return

    if message_type == "delete_preset":
        gone = str(payload.get("id", ""))
        ok = state.delete_preset(gone)
        if ok:
            for fid in list(state.programmer_refs):
                refs = state.programmer_refs[fid]
                for t in [t for t, pid in refs.items() if pid == gone]:
                    refs.pop(t, None)
                if not refs:
                    state.programmer_refs.pop(fid, None)
            await event_bus.broadcast(_refs_message())
            await event_bus.broadcast({
                "type": "presets_changed",
                "payload": {
                    "presets": {pid: asdict(p) for pid, p in state.presets.items()},
                    "preset_groups": list(state.preset_groups),
                    "is_dirty": state.is_dirty,
                },
            })
        return

    if message_type == "add_preset_group":
        state.add_preset_group(payload.get("name", "Group"))
        await event_bus.broadcast({
            "type": "presets_changed",
            "payload": {
                "presets": {pid: asdict(p) for pid, p in state.presets.items()},
                "preset_groups": list(state.preset_groups),
                "is_dirty": state.is_dirty,
            },
        })
        return

    if message_type == "delete_preset_group":
        ok = state.delete_preset_group(payload.get("name", ""))
        if ok:
            await event_bus.broadcast({
                "type": "presets_changed",
                "payload": {
                    "presets": {pid: asdict(p) for pid, p in state.presets.items()},
                    "preset_groups": list(state.preset_groups),
                    "is_dirty": state.is_dirty,
                },
            })
        return

    # ---- CueList-Management (Anlegen/Verwalten/weiches Abfeuern via CueEngine) ----

    if message_type == "add_cuelist":
        name = str(payload.get("name") or "").strip()
        if state.add_cuelist(name) is None:
            await EventBus._send(websocket, json.dumps({"type": "error", "payload": {"code": "CUELIST_DUPE", "name": name}}))
            return
        await _broadcast_cuelists_changed()
        return

    if message_type == "duplicate_cuelist":
        name = str(payload.get("name") or "").strip()
        if state.duplicate_cuelist(str(payload.get("id", "")), name or None) is None:
            if name:
                await EventBus._send(websocket, json.dumps({"type": "error", "payload": {"code": "CUELIST_DUPE", "name": name}}))
            return
        await _broadcast_cuelists_changed()
        return

    if message_type == "reorder_cuelists":
        order = payload.get("order")
        if isinstance(order, list) and state.reorder_cuelists(order):
            await _broadcast_cuelists_changed()
        return

    if message_type == "delete_cuelist":
        cuelist_id = payload.get("id", "")
        if cuelist_id in state.cuelists:
            await delete_cuelist_command(cuelist_id, _broadcast_generic)       # Aufraeumen (Ueberblendung, Executor-Zuordnung) und Broadcast: app/command_line.py
        return

    if message_type == "rename_cuelist":
        cl_id = str(payload.get("id", ""))
        name = str(payload.get("name", "")).strip()
        if cl_id in state.cuelists and name and state.cuelist_name_taken(name, cl_id):
            await EventBus._send(websocket, json.dumps({"type": "error", "payload": {"code": "CUELIST_DUPE", "name": name}}))
            return
        if state.rename_cuelist(cl_id, name):
            await _broadcast_cuelists_changed()
        return

    if message_type == "set_active_cuelist":
        if state.set_active_cuelist(payload.get("id", "")):
            await _broadcast_cuelists_changed()
        return

    if message_type == "save_cue":
        fixture_values = payload.get("fixture_values", {}) or {}
        fx_map = fx_engine.cue_effects()
        if not fixture_values and not fx_map:
            await _cue_result(websocket, ok=False, code="empty")
            return
        status, data = state.store_cue(
            payload.get("cuelist_id", ""),
            fixture_values,
            number=payload.get("number"),
            mode=payload.get("mode"),
            position=payload.get("position"),
            after_cue_id=payload.get("after_cue_id"),
            fx=fx_map,
            fx_order=fx_engine.cue_effect_order(),
            name=payload.get("name"),
            fx_fade_in=payload.get("fx_fade_in", 0.0),
            fx_fade_out=payload.get("fx_fade_out", 0.0),
            fade=payload.get("fade", 0.0),
            delay=payload.get("delay", 0.0),
            trigger=payload.get("trigger", "go"),
            timecode_ms=payload.get("timecode_ms"),
            mib=payload.get("mib", "Off"),
            cmd=payload.get("cmd", ""),
            fade_color=payload.get("fade_color"),
            delay_color=payload.get("delay_color"),
            fade_pos=payload.get("fade_pos"),
            delay_pos=payload.get("delay_pos"),
            fade_beam=payload.get("fade_beam"),
            delay_beam=payload.get("delay_beam"),
            fade_zoom=payload.get("fade_zoom"),
            delay_zoom=payload.get("delay_zoom"),
        )
        if status in ("created", "merged", "overwritten"):
            await _broadcast_cuelists_changed()
            await _cue_result(websocket, ok=True, code=status, number=data.number, name=data.name, cue_id=data.id)
        elif status == "conflict":
            # Die Nummer gibt es schon: nichts wird veraendert, der Client fragt nach (Zusammenfuehren / Ueberschreiben)
            await _cue_result(websocket, ok=False, code="conflict", number=data.number, name=data.name, cue_id=data.id)
        elif status == "out_of_bounds":
            await _cue_result(websocket, ok=False, code="out_of_bounds", **data)
        else:
            await _cue_result(websocket, ok=False, code=status)
        return

    if message_type == "update_active_cue":
        # "Aktualisieren": aktuelle Werte in den AKTIVEN Cue uebernehmen (ohne Store-Dialog). mode "normal" | "only"
        mode = "only" if payload.get("mode") == "only" else "normal"
        status, cue = state.update_active_cue(
            payload.get("cuelist_id", ""), payload.get("fixture_values", {}) or {},
            fx=fx_engine.cue_effects(), fx_order=fx_engine.cue_effect_order(), mode=mode,
        )
        if status == "updated":
            await _broadcast_cuelists_changed()
            await _cue_result(websocket, ok=True, code="updated", mode=mode, number=cue.number, name=cue.name, cue_id=cue.id)
        else:
            await _cue_result(websocket, ok=False, code=status)
        return

    if message_type == "set_cuelist_master":
        # Executor-Fader: Gesamthelligkeit einer Cue-Liste (multiplikativ, nicht destruktiv)
        await set_cuelist_master(payload.get("cuelist_id", ""), payload.get("value", 100.0), _broadcast_generic)
        return

    if message_type == "update_cues":
        # Mehrere Cues einer Liste auf einmal (Wischgeste auf mehreren markierten Zeilen): ein Broadcast fuer alle
        changed = False
        for item in (payload.get("updates") or [])[:500]:
            if isinstance(item, dict) and "delay" in item:
                changed = bool(state.update_cue(payload.get("cuelist_id", ""), str(item.get("cue_id", "")), delay=item["delay"])) or changed
        if changed:
            await _broadcast_cuelists_changed()
        return

    if message_type == "update_cue":
        cuelist_id = payload.get("cuelist_id", "")
        cue_id = payload.get("cue_id", "")
        number = payload.get("number")
        skip_fields = False
        cl = state.cuelists.get(cuelist_id)
        current = next((c for c in cl.cues if c.id == cue_id), None) if cl else None
        if number is not None and current is not None:
            n = state.parse_cue_number(number)
            if n is None:
                await _cue_result(websocket, ok=False, code="invalid")
                number = None
            elif abs(current.number - n) >= 1e-6:
                status, data = state.renumber_cue(cuelist_id, cue_id, n, payload.get("on_conflict"))
                if status == "conflict":
                    await _cue_result(websocket, ok=False, code="renumber_conflict", number=n, name=data.name,
                                      cue_id=cue_id, other_cue_id=data.id)
                elif status == "merged":
                    skip_fields = True       # der verschobene Cue ist im bestehenden aufgegangen
                number = None                # Nummer ist hier erledigt (oder wartet auf die Rueckfrage)
                await _broadcast_cuelists_changed()
            else:
                number = None
        cue = None if skip_fields else state.update_cue(
            cuelist_id,
            cue_id,
            name=payload.get("name"),
            number=None,
            fade=payload.get("fade"),
            delay=payload.get("delay"),
            trigger=payload.get("trigger"),
            timecode_ms=payload.get("timecode_ms"),
            mib=payload.get("mib"),
            cmd=payload.get("cmd"),
            **{k: payload[k] for k in (
                "fade_color", "delay_color", "fade_pos", "delay_pos", "fade_beam", "delay_beam", "fade_zoom", "delay_zoom",
                "fx_fade_in", "fx_fade_out"
            ) if k in payload},
        )
        if cue:
            await _broadcast_cuelists_changed()
        return

    if message_type == "delete_cues":
        # Sammel-Loeschen (mehrere markierte Cues): ein Broadcast fuer alle
        removed = [state.delete_cue(payload.get("cuelist_id", ""), str(cid)) for cid in (payload.get("cue_ids") or [])[:500]]
        if any(removed):
            await _broadcast_cuelists_changed()
        return

    if message_type == "delete_cue":
        if state.delete_cue(payload.get("cuelist_id", ""), payload.get("cue_id", "")):
            await _broadcast_cuelists_changed()
        return

    if message_type in ("cue_go", "cue_back"):
        # Die CueEngine uebernimmt das Abfeuern inkl. weicher Ueberblendung
        # (Cue.fade) - sie committed DMX-Schreibvorgaenge und den
        # abstrakten Live-Zustand selbst ueber ihren Update-Callback
        # (_cue_engine_update, siehe oben). Hier wird nur SOFORT der neue
        # aktive-Cue-Status gebroadcastet, damit die Status-Anzeige im
        # CueList-Panel nicht auf den Fade warten muss.
        cuelist_id = payload.get("cuelist_id", "")
        direction = 1 if message_type == "cue_go" else -1
        new_cue = await cue_engine.trigger(cuelist_id, direction)
        if new_cue is not None:
            await _broadcast_cuelists_changed()
        return

    if message_type in ("cue_stop", "cue_pause", "cue_resume"):
        # Wiedergabe-Steuerung der laufenden Ueberblendung (kein Wechsel des aktiven Cues). Das Ergebnis
        # erreicht alle Clients ueber das Playback-Callback der Engine (cuelist_progress).
        cuelist_id = payload.get("cuelist_id", "")
        action = {"cue_stop": cue_engine.stop, "cue_pause": cue_engine.pause, "cue_resume": cue_engine.resume}
        action[message_type](cuelist_id)
        if message_type == "cue_stop":
            # Stopp beendet auch alle laufenden Effekte. Definition wie bei "Clear Clear": die Zuweisungen
            # entfallen, die zuletzt ausgegebenen Werte bleiben stehen (nichts springt auf 0 oder Default).
            if fx_engine.clear_all():
                await event_bus.broadcast(_fx_changed_message())
        return

    if message_type == "jump_to_cue":
        # Rechtsklick -> "Diesen Cue abspringen / Hierhin faden": feuert
        # einen beliebigen Cue direkt ab (mit dessen eigener Fade-Zeit),
        # unabhaengig vom aktuell aktiven Cue.
        new_cue = await cue_engine.jump_to(payload.get("cuelist_id", ""), payload.get("cue_id", ""))
        if new_cue is not None:
            await _broadcast_cuelists_changed()
        return

    # ---- Globaler Timecode (siehe app/timecode.py) ----

    if message_type in ("timecode_play", "timecode_pause", "timecode_stop", "timecode_seek", "timecode_rate"):
        if message_type == "timecode_play":
            if payload.get("position_ms") is not None:
                timecode.seek(payload.get("position_ms"))
            snapshot = timecode.play(-1 if str(payload.get("direction", 1)).lstrip("+") in ("-1", "-1.0") else 1)
        elif message_type == "timecode_pause":
            snapshot = timecode.pause()
        elif message_type == "timecode_stop":
            snapshot = timecode.stop()
        elif message_type == "timecode_seek":
            snapshot = timecode.seek(payload.get("position_ms"))
        else:
            snapshot = timecode.set_rate(payload.get("rate"))
        await _broadcast_timecode(snapshot)
        return

    # ---- Command Line (dot2-/MA-Stil, siehe app/command_line.py) ----

    if message_type == "set_selection":
        # Maus-Klick-Selektion (Scheinwerferliste/Programmer-Tilegrid) wird
        # server-autoritativ gemacht (state.selected_fixture_ids), damit ein
        # anschliessender Command-Line-Befehl ("At 80") dieselbe Selektion
        # sieht wie das UI - und umgekehrt wirkt ein "Fixture 1"-Befehl
        # sofort auf allen verbundenen Clients (selection_changed-Broadcast).
        ids = state.set_selection(payload.get("ids", []))
        await event_bus.broadcast({"type": "selection_changed", "payload": {"selected_ids": ids}})
        return

    if message_type == "run_command":
        command_text = str(payload.get("command", ""))
        result = await execute_command(command_text, _broadcast_generic)
        # log_to_history: Button/Fader-Panels koennen das Logging pro Panel
        # deaktivieren (Standard: True). Die Befehlszeile selbst sendet
        # keinen log_to_history-Key → defaults to True.
        if payload.get("log_to_history", True):
            await _broadcast_command_log(command_text, result)
        return

    if message_type == "set_blackout":
        # Blackout-Knopf (Werkzeugleiste, Befehlstasten) - dieselbe Funktion wie der Befehl "Blackout"; enabled fehlt = umschalten
        enabled = payload.get("enabled")
        await set_blackout(None if enabled is None else bool(enabled), _broadcast_generic)
        return

    if message_type == "set_cmd_suggestions":
        # Schalter "Vorschlaege" neben der Befehlszeile: wird in der App-Config gespeichert und auf allen Geraeten uebernommen
        enabled = state.set_cmd_suggestions(payload.get("enabled"))
        await event_bus.broadcast({"type": "cmd_suggestions_changed", "payload": {"enabled": enabled}})
        return

    if message_type == "autocomplete":
        # Tab-Vorschlaege der Befehlszeile (Grammatik und Zustand: app/command_line.py get_suggestions); nur an den Absender, und nur wenn sie eingeschaltet sind
        text = str(payload.get("text", ""))[:500]
        await EventBus._send(websocket, json.dumps({
            "type": "autocomplete_result",
            "payload": {"text": text, "suggestions": get_suggestions(text) if state.cmd_suggestions else []},
        }))
        return

    logger.info("Unbekannter Nachrichtentyp empfangen: %s", message_type)
