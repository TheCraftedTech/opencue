# Copyright (C) 2026 Samuel Zenker
# SPDX-License-Identifier: GPL-3.0-or-later
"""
io_overview.py
Uebersicht ALLER Ein- und Ausgaenge, die OpenCue gerade benutzt - und wofuer (Einstellungen -> "Ein- & Ausgaenge"): DMX-Ausgabe (Art-Net, sACN, Enttec, Universen), Netzwerk
(Konsole, Fernzugriff http / https, Netzwerk-Name, REST-API, verbundene Geraete), Audio-Eingaenge (Mikrofon fuer das Triggerwort, Mikrofon zum Diktieren, Quelle der Audio-Analyse),
Tastaturen (welche Tastatur welche Kuerzel ausloest), KI-Server, Stream-Quellen und Update-Pruefung. Reine Anzeige - nichts davon wird hier eingestellt.

  GET /api/io-overview   (nur an der Konsole selbst)
      {"groups": [{"id", "rows": [{"role", "name", "state", "reach", "link", "extra"}]}]}
  state: "ok" (laeuft / verbunden) | "off" (ausgeschaltet) | "warn" (eingeschaltet, aber Fehler) | "info" (nur zur Kenntnis)
  reach: wie weit die Verbindung reicht - "local" (nur dieser PC) | "lan" (lokales Netzwerk) | "internet" | "none" (ausgeschaltet / nichts im Spiel)
  link:  Kategorie der Einstellungen, in der man es aendert (data-settings-category), "" = keine
  Die Oberflaeche setzt aus "role" und "extra" den Satz in der gewaehlten Sprache zusammen (Schluessel IOV_*).
Mikrofone heissen in beiden Zeilen (Triggerwort, Diktieren) gleich: ist keins gewaehlt, steht "default" = True und `name` ist das aktuelle Standard-Mikrofon von Windows.
"""
from __future__ import annotations

import asyncio
import ipaddress
import logging
import time
from typing import Any, Dict, List
from urllib.parse import urlparse

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger("opencue.io")
router = APIRouter()

_MIC_TTL_S = 30.0
_mic_cache: Dict[str, Any] = {"at": 0.0, "mics": []}


def _row(role: str, name: str, state: str, reach: str = "none", link: str = "", **extra: Any) -> Dict[str, Any]:
    return {"role": role, "name": name, "state": state, "reach": reach if state != "off" else "none", "link": link, "extra": extra}


def _reach_of_host(host: str) -> str:
    """Wohin eine Adresse fuehrt: dieser PC, ein Rechner im lokalen Netz oder das Internet."""
    host = (host or "").strip().strip("[]").lower()
    if not host or host == "localhost":
        return "local"
    try:
        ip = ipaddress.ip_address(host)
        if ip.is_loopback:
            return "local"
        return "lan" if (ip.is_private or ip.is_link_local) else "internet"
    except ValueError:
        pass
    return "lan" if ("." not in host or host.endswith((".local", ".lan", ".home", ".internal"))) else "internet"


def _reach_of_url(url: str) -> str:
    try:
        return _reach_of_host(urlparse(url if "://" in url else "//" + url).hostname or "")
    except Exception:
        return "internet"


def _microphones() -> List[Dict[str, Any]]:
    """Eingaenge des Computers; kurz zwischengespeichert, weil die Uebersicht alle paar Sekunden neu fragt."""
    now = time.monotonic()
    if now - _mic_cache["at"] > _MIC_TTL_S:
        try:
            from app import voice
            _mic_cache["mics"] = voice.list_microphones()
        except Exception:
            logger.debug("Mikrofone nicht lesbar", exc_info=True)
        _mic_cache["at"] = now
    return _mic_cache["mics"]


def _mic_name(device_id: str, fallback: str = "") -> str:
    """Name des Mikrofons zu einer Kennung; ohne Kennung (= Standard von Windows) der Name des aktuellen Standard-Mikrofons."""
    mics = _microphones()
    if not device_id:
        for mic in mics:
            if mic.get("default"):
                return str(mic.get("name") or "")
        return fallback
    for mic in mics:
        if mic.get("id") == device_id:
            return str(mic.get("name") or "")
    return device_id.replace("input:", "")


def _dmx(state, dmx_engine) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    universes: Dict[int, int] = {}
    for fx in state.fixtures.values():
        universes[fx.universe] = universes.get(fx.universe, 0) + 1
    artnet_reach = _reach_of_host(state.artnet_ip) if state.artnet_ip and not str(state.artnet_ip).endswith(".255") else "lan"
    rows.append(_row("artnet", state.artnet_ip or "-", "ok" if state.artnet_enabled else "off", artnet_reach, "dmx-network", bind=state.artnet_bind_ip or ""))
    rows.append(_row("sacn", "Multicast", "ok" if state.sacn_enabled else "off", "lan", "dmx-network"))
    enttec = dmx_engine.get_enttec_status()
    if state.enttec_enabled:
        rows.append(_row("enttec", enttec.get("port") or "-", "ok" if enttec.get("connected") else "warn", "local", "dmx-network", universe=state.enttec_universe, error=str(enttec.get("error") or "")))
    else:
        rows.append(_row("enttec", state.enttec_port or "-", "off", "none", "dmx-network", universe=state.enttec_universe))
    from app import dmx_in
    cfg = state.dmx_in_config
    status = dmx_in.manager.status()
    listening = status.get("listening") or {}
    errors = status.get("errors") or {}
    if not cfg.get("enabled"):
        din = "off"
    elif errors or not (listening.get("artnet") or listening.get("sacn")):
        din = "warn"
    else:
        din = "ok"
    rows.append(_row("dmx_in", "Art-Net / sACN", din, "lan", "", error="; ".join(str(v) for v in errors.values())))
    for number in sorted(universes):
        rows.append(_row("universe", str(number), "info", "none", "", fixtures=universes[number]))
    return rows


def _network(state, remote, mdns, clients: int) -> List[Dict[str, Any]]:
    from app.api_v1 import store as api_store
    info = remote.remote_info(False)
    remote_on = bool(state.http_enabled or state.https_enabled)
    rows = [_row("local_server", f"127.0.0.1:{info['port']}", "ok", "local", "")]
    http = [u for u in info["urls"] if u.startswith("http://")]
    https = info["https_urls"]
    rows.append(_row("remote_http", ", ".join(http) if http else f":{state.server_port}", "ok" if state.http_enabled and http else ("warn" if state.http_enabled else "off"), "lan", "remote",
                     error=" ".join(str(v) for k, v in info["listen_errors"].items() if k != "https")))
    rows.append(_row("remote_https", ", ".join(https) if https else f":{state.https_port}", "ok" if state.https_enabled and https else ("warn" if state.https_enabled else "off"), "lan", "remote",
                     error=str(info["listen_errors"].get("https", ""))))
    rows.append(_row("mdns", mdns.host or "opencue.local", "ok" if state.mdns_enabled and mdns.host else ("warn" if state.mdns_enabled and remote_on else "off"), "lan", "remote", error=str(mdns.error or "")))
    api_on = api_store.is_enabled()
    api_net = api_store.is_network()
    if not api_on:
        rows.append(_row("rest_api", "/api/v1", "off", "none", "api", network=api_net))
    elif api_net and not remote_on:
        rows.append(_row("rest_api", "/api/v1", "warn", "local", "api", network=True, needs_remote=True))             # fuers Netzwerk gedacht, aber der Fernzugriff ist aus
    else:
        rows.append(_row("rest_api", f"/api/v1  (:{info['port']})", "ok", "lan" if api_net else "local", "api", network=api_net))
    rows.append(_row("clients", str(clients), "info", "none", "", count=clients))
    return rows


def _audio(state, voice, audio_engine) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    cfg = voice.engine.config
    wake_on = bool(cfg.get("enabled"))
    wake_device = str(cfg.get("device") or "")
    rows.append(_row("wake_mic", _mic_name(wake_device, voice.engine.device_name or ""), "ok" if voice.engine.running else ("warn" if wake_on else "off"), "local", "voice",
                     default=not wake_device, word=cfg.get("wake_word", ""), error=voice.engine.error if wake_on else ""))
    dictation_device = str((getattr(state, "voice_config", {}) or {}).get("dictation_device") or "")
    rows.append(_row("dictation_mic", _mic_name(dictation_device), "info", "local", "dictation", default=not dictation_device))
    analysis_device = str((audio_engine.config or {}).get("device") or "")
    running = bool(getattr(audio_engine, "running", False))
    if running or analysis_device:                                  # ohne Quelle waere die Zeile nur Rauschen
        rows.append(_row("audio_analysis", getattr(audio_engine, "device_name", "") or analysis_device.split(":", 1)[-1], "ok" if running else "off", "local", "",
                         configured=analysis_device.split(":", 1)[-1]))
    return rows


def _timecode(state, server_module) -> List[Dict[str, Any]]:
    """Timecode: wer fuehrt die globale Uhr (dieser Computer / MIDI Timecode / LTC), LTC lesen und senden, MIDI Timecode in / out. Link: Einstellungen -> Timecode bzw. MIDI."""
    import sys
    from app.timecode import timecode
    rows: List[Dict[str, Any]] = []
    leader = "ltc" if server_module._ltc_driving else ("midi" if server_module._mtc_driving else ("internal" if timecode.running else "stopped"))
    rows.append(_row("clock", leader, "ok" if timecode.running else "info", "local", "timecode", running=bool(timecode.running)))
    cfg = state.ltc_config or {}
    ltc_module = sys.modules.get("app.ltc")                                      # numpy / PortAudio nicht nur fuer diese Anzeige laden
    live_in = ltc_module.ltc if ltc_module else None
    live_out = ltc_module.ltc_out if ltc_module else None
    in_on = bool(cfg.get("enabled"))
    in_name = (live_in.device_name if live_in and live_in.device_name else str(cfg.get("device") or "").split(":", 1)[-1]) or "-"
    in_error = live_in.error if (live_in and in_on) else ""
    rows.append(_row("ltc_in", in_name, "warn" if in_error else ("ok" if (live_in and live_in.locked) else ("info" if (in_on and live_in and live_in.running) else "off")), "local", "timecode",
                     locked=bool(live_in and live_in.locked), error=in_error, timecode=(live_in.status().get("timecode") if live_in else "")))
    out_cfg = cfg.get("out") or {}
    out_on = bool(out_cfg.get("enabled"))
    out_name = (live_out.device_name if live_out and live_out.device_name else str(out_cfg.get("device") or "").split(":", 1)[-1]) or "-"
    out_error = live_out.error if (live_out and out_on) else ""
    rows.append(_row("ltc_out", out_name, "warn" if out_error else ("ok" if (live_out and live_out.sending) else ("info" if (out_on and live_out and live_out.running) else "off")), "local", "timecode",
                     fps=out_cfg.get("fps", 25), error=out_error))
    midi_cfg = state.midi or {}
    rows.append(_row("mtc_in", "MIDI", "info" if midi_cfg.get("mtc") else "off", "local", "midi"))
    rows.append(_row("mtc_out", "MIDI", "info" if midi_cfg.get("mtc_out") else "off", "local", "midi"))
    return rows


def _keyboards(state, rawkeys) -> List[Dict[str, Any]]:
    by_device: Dict[str, Dict[str, Any]] = {}
    all_count = 0
    for entry in state.hotkeys:
        if not entry.get("enabled", True) or not entry.get("keys"):
            continue
        device = str(entry.get("device") or "")
        if not device:
            all_count += 1
            continue
        item = by_device.setdefault(device, {"name": entry.get("device_name") or device, "count": 0})
        item["count"] += 1
    rows = [_row("keyboard_all", "", "ok" if all_count else "info", "local", "", count=all_count)]
    known = {}
    try:
        known = {d["id"]: d["name"] for d in rawkeys.devices()}
    except Exception:
        logger.debug("Tastaturen nicht lesbar", exc_info=True)
    shown = set()
    for device, item in by_device.items():
        if item["name"] in shown:
            continue
        shown.add(item["name"])
        connected = (not known or device in known)
        rows.append(_row("keyboard_device", item["name"], "ok" if connected else "warn", "local", "", count=item["count"], connected=connected))
    for device, name in known.items():
        label = name or device                                  # manche Tastaturen melden keinen Namen: dann die Kennung
        if device not in by_device and label not in shown:      # ein Geraet mit mehreren Schnittstellen erscheint mehrmals in der Liste von Windows: nur einmal zeigen
            shown.add(label)
            rows.append(_row("keyboard_idle", label, "info", "local", ""))
    return rows


def _midi(state, midi) -> List[Dict[str, Any]]:
    """MIDI-Eingaenge (offen = ein Eintrag braucht sie, sonst nur vorhanden), der Ausgang und die Zahl der Belegungen. Link: der Dialog "MIDI-Belegung"."""
    rows: List[Dict[str, Any]] = []
    status = midi.refresh_ports()
    link = "midi-dialog"
    if not status["available"]:
        return [_row("midi_map", "", "warn", "local", link, count=0, error=status["error"] or "python-rtmidi")]
    enabled = status["enabled"]
    rows.append(_row("midi_map", "", "ok" if (enabled and status["bindings"]) else ("off" if not enabled else "info"), "local", link, count=status["bindings"], enabled=enabled))
    for port in status["inputs"]:
        state_name = "warn" if port["error"] else ("ok" if port["open"] else "info")
        rows.append(_row("midi_in", port["name"], state_name, "local", link, error=port["error"], open=port["open"]))
    if not status["inputs"]:
        rows.append(_row("midi_in_none", "", "info", "none", link))
    if status["output"]:
        rows.append(_row("midi_out", status["output"], "info", "local", link, count=len(status["outputs"])))
    return rows


def _other(state, ai_assistant, stream_sources) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    ai = ai_assistant.config
    ai_url = str(ai.get("base_url") or "")
    rows.append(_row("ai_server", ai_url, "ok" if ai.get("enabled") else "off", _reach_of_url(ai_url), "ai", model=str(ai.get("model") or "")))
    from app import fixture_library, net_diag, updater
    from urllib.parse import urlparse
    seen = net_diag.last("update")
    if not state.update_check_enabled:
        rows.append(_row("update", urlparse(updater.api_url()).hostname or "GitHub", "off", "internet", "general"))
    else:                                                       # letzter echter Versuch: fehlgeschlagen = gelb mit Ursache
        rows.append(_row("update", urlparse(updater.api_url()).hostname or "GitHub", "warn" if seen and not seen["ok"] else "ok", "internet", "general",
                         error_code=(seen or {}).get("code", ""), detail=(seen or {}).get("detail", ""), tried=bool(seen)))
    share = net_diag.last("gdtf")
    rows.append(_row("gdtf", urlparse(fixture_library.SHARE_BASE).hostname or "GDTF Share", "warn" if share and not share["ok"] else ("ok" if fixture_library.share.logged_in else "info"), "internet", "general",
                     error_code=(share or {}).get("code", ""), detail=(share or {}).get("detail", ""), logged_in=bool(fixture_library.share.logged_in)))
    try:
        for source in stream_sources.public_list():
            url = source.get("url", "")
            rows.append(_row("stream", source.get("name") or url, "info", _reach_of_url(url), "", type=source.get("resolved_type", ""), url=url))
    except Exception:
        logger.debug("Stream-Quellen nicht lesbar", exc_info=True)
    return rows


@router.post("/api/net-check")
async def api_net_check(request: Request) -> JSONResponse:
    """Verbindungstest: Update-Server und GDTF Share (DNS -> TCP -> TLS -> HTTP). Nur an der Konsole selbst."""
    from app import net_diag, remote
    return JSONResponse(await asyncio.to_thread(net_diag.run_check), headers={"Cache-Control": "no-store"})


@router.get("/api/io-overview")
async def api_overview(request: Request) -> JSONResponse:
    from app import audio_engine as audio_module, remote, server, stream_sources, voice
    from app.ai.agent import assistant
    from app.dmx_engine import dmx_engine
    from app.mdns import mdns
    from app.midi_engine import midi
    from app.rawkeys import rawkeys
    from app.state_manager import state
    await asyncio.to_thread(_microphones)                           # die (langsame) Geraeteliste nicht im Ereignis-Thread holen
    groups = [
        {"id": "dmx", "rows": _dmx(state, dmx_engine)},
        {"id": "network", "rows": _network(state, remote, mdns, len(server.event_bus._connections))},
        {"id": "audio", "rows": _audio(state, voice, audio_module.audio_engine)},
        {"id": "timecode", "rows": _timecode(state, server)},
        {"id": "keyboards", "rows": _keyboards(state, rawkeys)},
        {"id": "midi", "rows": await asyncio.to_thread(_midi, state, midi)},
        {"id": "other", "rows": _other(state, assistant, stream_sources)},
    ]
    return JSONResponse({"groups": groups})
