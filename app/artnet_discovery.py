# Copyright (C) 2026 Samuel Zenker
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Art-Net-Geraete im Netzwerk finden (ArtPoll / ArtPollReply) - damit "einstecken und es geht": Knoten (Nodes, Gateways, Dimmer-Packs ...) antworten auf eine Suchanfrage mit Namen, Adresse
und ihren Universen.

  poll()          schickt ArtPoll an alle Netzwerkkarten des Rechners und sammelt die Antworten (etwa 1 s); gibt die gefundenen Geraete zurueck.
  parse_reply()   ein ArtPollReply-Paket -> Geraet {ip, name, short_name, mac, universes_out, universes_in, ...}.
  NodeRegistry    merkt sich Geraete mit "zuletzt gesehen" (Betrieb "Automatisch": alle paar Sekunden suchen; ein Geraet, das 15 s nicht antwortet, gilt als abgezogen).

Betrieb "Automatisch" (Einstellungen -> DMX-Ausgabe -> Art-Net -> Ziel "Automatisch"): OpenCue sendet an JEDES gefundene Geraet direkt (Unicast) - das geht auch, wenn das Geraet in einem
anderen Adressbereich steht als der Broadcast des Rechners. Solange noch nichts gefunden ist, wird per Broadcast gesendet (wie bisher).

Hinweis: Das Empfangen der Antworten bindet UDP 6454 (Art-Net); beim ersten Mal fragt die Windows-Firewall (siehe Einstellungen -> Fernzugriff -> Windows-Firewall). Rein Python (socket, struct).
"""
from __future__ import annotations

import logging
import socket
import struct
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger("opencue.artnet")

PORT = 6454
OP_POLL = 0x2000
OP_POLL_REPLY = 0x2100
FALLBACK_TARGETS = ("2.255.255.255", "255.255.255.255")      # bis ein Geraet antwortet: Art-Net-Standard-Broadcast und allgemeiner Broadcast
LOST_AFTER = 15.0                                            # Sekunden ohne Antwort, dann gilt ein Geraet als abgezogen
MAX_NODES = 16                                               # soviele Geraete werden hoechstens direkt bedient


def build_poll() -> bytes:
    """ArtPoll: "Art-Net\\0", OpCode 0x2000 (little endian), Protokollversion 14, TalkToMe 0, Prioritaet 0."""
    return b"Art-Net\x00" + struct.pack("<H", OP_POLL) + struct.pack(">H", 14) + bytes([0, 0])


def _text(raw: bytes) -> str:
    return raw.split(b"\x00", 1)[0].decode("latin-1", "replace").strip()


def parse_reply(data: bytes, source_ip: str = "") -> Optional[Dict[str, Any]]:
    """Ein ArtPollReply-Paket lesen; None, wenn es keines ist."""
    if len(data) < 207 or not data.startswith(b"Art-Net\x00") or struct.unpack_from("<H", data, 8)[0] != OP_POLL_REPLY:
        return None
    ip = ".".join(str(b) for b in data[10:14])
    if ip in ("0.0.0.0", ""):
        ip = source_ip
    net, sub = data[18], data[19]
    num_ports = min(4, struct.unpack_from(">H", data, 172)[0])
    port_types = data[174:178]
    sw_in, sw_out = data[186:190], data[190:194]
    outputs = [(net << 8) | (sub << 4) | (sw_out[i] & 0x0F) for i in range(num_ports) if port_types[i] & 0x80]      # Bit 7: Ausgang (DMX aus dem Netzwerk)
    inputs = [(net << 8) | (sub << 4) | (sw_in[i] & 0x0F) for i in range(num_ports) if port_types[i] & 0x40]         # Bit 6: Eingang
    mac = ":".join(f"{b:02x}" for b in data[201:207])
    return {"ip": ip, "short_name": _text(data[26:44]), "name": _text(data[44:108]) or _text(data[26:44]), "report": _text(data[108:172]), "mac": mac if mac != "00:00:00:00:00:00" else "",
            "universes_out": outputs, "universes_in": inputs, "oem": struct.unpack_from(">H", data, 20)[0], "firmware": struct.unpack_from(">H", data, 16)[0]}


def local_addresses() -> List[str]:
    """IPv4-Adressen dieses Rechners (ohne 127.x)."""
    found: List[str] = []
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ip = info[4][0]
            if not ip.startswith("127.") and not ip.startswith("169.254.") and ip not in found:
                found.append(ip)
    except OSError:
        pass
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:                     # die Karte der Standardroute
            probe.connect(("203.0.113.1", 9))
            ip = probe.getsockname()[0]
            if ip not in found and not ip.startswith("127."):
                found.append(ip)
    except OSError:
        pass
    return found


def _directed(ip: str) -> str:
    a = ip.split(".")
    return ".".join(a[:3] + ["255"]) if len(a) == 4 else "255.255.255.255"


def poll(timeout: float = 1.0, interfaces: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """Suche: ArtPoll von jeder Netzwerkkarte, Antworten `timeout` Sekunden lang sammeln. Blockiert (in einem Thread aufrufen)."""
    interfaces = interfaces if interfaces is not None else local_addresses()
    nodes: Dict[str, Dict[str, Any]] = {}
    receiver: Optional[socket.socket] = None
    try:
        receiver = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        receiver.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        receiver.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        try:
            receiver.bind(("0.0.0.0", PORT))
        except OSError as exc:                                                     # 6454 belegt (anderes Programm): auf einem freien Port antworten lassen
            logger.info("[ARTNET] Port 6454 busy (%s) - listening on a free port", exc)
            receiver.bind(("0.0.0.0", 0))
        receiver.settimeout(0.15)
        packet = build_poll()
        for ip in interfaces or [""]:
            for target in (_directed(ip) if ip else "255.255.255.255", "255.255.255.255", "2.255.255.255"):
                try:
                    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sender:
                        sender.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                        if ip:
                            sender.bind((ip, 0))                                    # ueber genau diese Karte senden
                        sender.sendto(packet, (target, PORT))
                except OSError:
                    continue
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                data, addr = receiver.recvfrom(1500)
            except socket.timeout:
                continue
            except OSError:
                break
            node = parse_reply(data, addr[0])
            if node and node["ip"] not in interfaces:                            # die eigenen Antworten (andere Programme auf diesem Rechner) zaehlen nicht
                nodes[node["ip"]] = node
    except OSError as exc:
        logger.warning("[ARTNET] Scan failed: %s", exc)
    finally:
        if receiver is not None:
            receiver.close()
    return sorted(nodes.values(), key=lambda n: tuple(int(x) for x in n["ip"].split(".")))


class NodeRegistry:
    """Geraete mit "zuletzt gesehen"; `update()` nimmt das Ergebnis einer Suche und sagt, ob sich die Liste der Adressen geaendert hat."""

    def __init__(self) -> None:
        self.nodes: Dict[str, Dict[str, Any]] = {}
        self.seen: Dict[str, float] = {}

    def update(self, found: List[Dict[str, Any]], now: Optional[float] = None) -> bool:
        now = time.monotonic() if now is None else now
        before = set(self.nodes)
        for node in found:
            self.nodes[node["ip"]] = node
            self.seen[node["ip"]] = now
        for ip in [ip for ip, t in self.seen.items() if now - t > LOST_AFTER]:
            self.nodes.pop(ip, None)
            self.seen.pop(ip, None)
        return set(self.nodes) != before

    def targets(self) -> List[str]:
        """Adressen, an die gesendet wird: die gefundenen Geraete, sonst die Broadcast-Rueckfallebene."""
        ips = sorted(self.nodes, key=lambda x: tuple(int(p) for p in x.split(".")))[:MAX_NODES]
        return ips or list(FALLBACK_TARGETS)

    def list(self) -> List[Dict[str, Any]]:
        return [self.nodes[ip] for ip in sorted(self.nodes, key=lambda x: tuple(int(p) for p in x.split(".")))]


registry = NodeRegistry()


# ---------------------------------------------------------------------------------------------------------------- HTTP / Hintergrundsuche
from fastapi import APIRouter, Request  # noqa: E402
from fastapi.responses import JSONResponse  # noqa: E402

router = APIRouter()


@router.get("/api/artnet/nodes")
async def scan_nodes(request: Request) -> JSONResponse:
    """Jetzt suchen (Einstellungen -> DMX-Ausgabe -> "Netzwerk absuchen"): nur an der Konsole selbst, weil dabei vom Server aus ins Netzwerk gefragt wird."""
    import asyncio
    from app import remote
    found = await asyncio.to_thread(poll, 1.2)
    registry.update(found)
    from app.dmx_engine import dmx_engine
    dmx_engine.set_artnet_auto_targets(registry.targets())
    return JSONResponse({"ok": True, "nodes": found, "targets": registry.targets()})
