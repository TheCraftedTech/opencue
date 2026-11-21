# Copyright (C) 2026 Samuel Zenker
# SPDX-License-Identifier: GPL-3.0-or-later
"""
DMX-Eingang: OpenCue empfaengt Art-Net und sACN (E1.31) - von einem Lichtpult, einer Software oder einem Geraet im Netzwerk - und kann die Werte

  * WEITERLEITEN / MISCHEN (Quelle -> Ausgabe): ein Eingangs-Universum wird in ein Ausgabe-Universum von OpenCue gemischt,
      "Hoechster gewinnt" (HTP: je Kanal gilt der groessere Wert von OpenCue und Eingang - Standard) oder "Ersetzt" (der Eingang gilt, solange die Quelle da ist),
      optional nur fuer einen Kanalbereich. Ist ein Ausgabe-Universum nicht gepatcht, wird es trotzdem ausgegeben (reine Weiterleitung, z. B. Art-Net -> sACN oder -> USB).
  * als AUSLOESER nutzen: ein Kanal startet einen Befehl der Befehlszeile (Cue springen, Go, Blackout, Master ...):
      "Taste": Wert steigt ueber die Schwelle -> Befehl "an", faellt wieder darunter -> Befehl "aus" (optional);
      "Fader": jeder neue Wert laeuft als Befehl, `{value}` im Befehl ist der Wert, auf einen Bereich umgerechnet (Standard 0-100).

Wo es laeuft: der EMPFANG und das MISCHEN laufen im Prozess der DMX-Ausgabe (app/dmx_output.py) - die Weiterleitung laeuft also unveraendert weiter, auch wenn der Server haengt.
Dieses Modul enthaelt die reine Logik (Pakete lesen, Einstellungen pruefen, `InputHub`) und auf der Server-Seite den `DmxInManager` (Einstellungen -> Prozess, Ausloeser -> Befehle,
Anzeige) samt Schnittstelle. Faellt der Ausgabe-Prozess aus (Rueckfall: Ausgabe im Hauptprogramm), laeuft der Hub im Server: Ausloeser und Anzeige gehen weiter, das Mischen
in die Ausgabe nicht (die Anzeige sagt es).

Eigene Pakete werden ignoriert: Art-Net an der Absende-Portnummer der eigenen Ausgabe, sACN an der eigenen Quellkennung (CID) - sonst haette eine Weiterleitung eine Rueckkopplung.

Art-Net-Universum = "Port-Address" (so wie OpenCue es auch sendet: Universum 1 = Port-Address 1), sACN-Universum = Universum.

SICHERHEIT: DMX hat kein Passwort - jeder im Netzwerk kann senden. AUS ist der Standard; optional eine Liste erlaubter Absender (IP-Adresse oder Anfang davon). Ausloeser fuehren
nur die Befehle aus, die der Nutzer selbst eingetragen hat.

  GET  /api/dmx-in           Einstellungen, Zustand, gesehene Quellen (?watch=1 haelt die Live-Anzeige der Werte an)
  POST /api/dmx-in/config    Einstellungen speichern (nur lokal)
  POST /api/dmx-in/learn     {"on": true|false}: der naechste sich aendernde Kanal fuellt die Zuordnung ("Einlernen")
"""
from __future__ import annotations

import base64
import collections
import logging
import re
import socket
import struct
import threading
import time
import uuid
from typing import Any, Callable, Deque, Dict, List, Optional, Tuple

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger("opencue.dmxin")
router = APIRouter()

ARTNET_PORT = 6454
SACN_PORT = 5568
UNIVERSE_SIZE = 512
MAX_MERGE = 32
MAX_TRIGGERS = 64
MAX_UNIVERSE = 63999
MAX_OUT_UNIVERSE = 64
_ALLOW = re.compile(r"^[0-9a-fA-F:.]{1,45}$")
_HOLD_PER_LEVEL = 0.05                       # Fader-Ausloeser: hoechstens alle 50 ms ein Befehl (der neueste Wert zaehlt)


# ------------------------------------------------------------------------------------------------------------------ Pakete lesen
def parse_artnet(data: bytes) -> Optional[Dict[str, Any]]:
    """ArtDmx (Opcode 0x5000): {universe (Port-Address), seq, dmx} - sonst None (ArtPoll, ArtSync ... gehen uns nichts an)."""
    if len(data) < 19 or data[:8] != b"Art-Net\x00" or data[8] != 0x00 or data[9] != 0x50:
        return None
    length = (data[16] << 8) | data[17]
    if length < 1 or length > UNIVERSE_SIZE or len(data) < 18 + length:
        return None
    return {"universe": data[14] | ((data[15] & 0x7F) << 8), "seq": data[12], "dmx": bytes(data[18:18 + length])}


def parse_sacn(data: bytes) -> Optional[Dict[str, Any]]:
    """E1.31-Datenpaket: {universe, priority, cid, name, seq, terminated, dmx} - sonst None (Universe Discovery, Sync, falscher Startcode)."""
    if len(data) < 126 or data[4:16] != b"ASC-E1.17\x00\x00\x00" or data[18:22] != b"\x00\x00\x00\x04" or data[40:44] != b"\x00\x00\x00\x02":
        return None
    count = (data[123] << 8) | data[124]
    if data[117] != 0x02 or data[118] != 0xA1 or count < 1 or data[125] != 0x00:
        return None                                                      # Startcode 0 = DMX; alles andere (RDM, Text ...) ignorieren
    slots = min(UNIVERSE_SIZE, count - 1, len(data) - 126)
    if slots < 1:
        return None
    return {"universe": (data[113] << 8) | data[114], "priority": data[108], "cid": bytes(data[22:38]), "seq": data[111], "terminated": bool(data[112] & 0x40),
            "name": data[44:108].split(b"\x00", 1)[0].decode("utf-8", "replace").strip(), "dmx": bytes(data[126:126 + slots])}


def build_poll_reply(ip: str, universes: List[int], live: set, index: int = 1, mac: bytes = b"\x00" * 6, name: str = "OpenCue") -> bytes:
    """ArtPollReply (Opcode 0x2100, 239 Byte): meldet OpenCue als Art-Net-Geraet, das die Universen `universes` (hoechstens 4, alle mit derselben Net / Sub-Net) empfaengt und ausgibt.
    `live` = Universen, aus denen gerade Daten kommen (Zeichen "Daten werden ausgegeben")."""
    packet = bytearray(239)
    packet[0:8] = b"Art-Net\x00"
    packet[8], packet[9] = 0x00, 0x21
    try:
        packet[10:14] = bytes(int(part) & 0xFF for part in ip.split("."))
    except ValueError:
        pass
    packet[14], packet[15] = 0x36, 0x19                                         # Port 6454 (niederwertiges Byte zuerst)
    packet[16], packet[17] = 0x00, 0x01                                          # Version der Firmware
    first = universes[0] if universes else 0
    packet[18], packet[19] = (first >> 8) & 0x7F, (first >> 4) & 0x0F          # Net / Sub-Net
    packet[20], packet[21] = 0x00, 0xFF                                          # OEM: unbekannt
    packet[23] = 0xF0                                                            # Anzeige normal, Port-Adresse nicht vom Geraet selbst eingestellt
    packet[24], packet[25] = 0xF0, 0x7F                                          # ESTA-Hersteller 0x7FF0 (frei fuer Prototypen / Freie Software)
    packet[26:44] = name.encode("ascii", "replace")[:17].ljust(18, b"\x00")
    packet[44:108] = f"{name} - DMX input".encode("ascii", "replace")[:63].ljust(64, b"\x00")
    packet[108:172] = f"#0001 [{len(universes):04d}] {name} receives {len(universes)} universe(s)".encode("ascii", "replace")[:63].ljust(64, b"\x00")
    ports = universes[:4]
    packet[172], packet[173] = 0, len(ports)
    for slot, universe in enumerate(ports):
        packet[174 + slot] = 0x80                                                # DMX512 wird aus Art-Net ausgegeben (= empfangen)
        packet[182 + slot] = 0x80 if universe in live else 0x00                  # GoodOutput: Daten laufen
        packet[190 + slot] = universe & 0x0F                                     # SwOut: unterste 4 Bit des Universums
    packet[200] = 0x00                                                           # Style: StNode
    packet[201:207] = (mac + b"\x00" * 6)[:6]
    try:
        packet[207:211] = bytes(int(part) & 0xFF for part in ip.split("."))
    except ValueError:
        pass
    packet[211] = max(1, min(255, index))                                        # BindIndex: mehrere Antworten desselben Geraets
    packet[212] = 0x08                                                           # Status2: 15-Bit Port-Address
    return bytes(packet)


def _poll_groups(universes: set) -> List[List[int]]:
    """Universen nach (Net, Sub-Net) gruppieren, je Antwort hoechstens 4."""
    groups: Dict[Tuple[int, int], List[int]] = {}
    for universe in sorted(universes):
        groups.setdefault(((universe >> 8) & 0x7F, (universe >> 4) & 0x0F), []).append(universe)
    out: List[List[int]] = []
    for items in groups.values():
        out.extend(items[i:i + 4] for i in range(0, len(items), 4))
    return out or [[]]


# ------------------------------------------------------------------------------------------------------------------ Einstellungen
def _int(value: Any, default: int, low: int, high: int) -> int:
    try:
        number = int(float(value))
    except (TypeError, ValueError):
        return default
    return max(low, min(high, number))


def _float(value: Any, default: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if number == number and abs(number) < 1e9 else default


def default_config() -> Dict[str, Any]:
    return {"enabled": False, "artnet": True, "sacn": True, "bind": "", "announce": True, "timeout": 3.0, "allow": [], "merge": [], "triggers": []}


def normalize(raw: Any) -> Dict[str, Any]:
    """Einstellungen pruefen: Unbekanntes und Ungueltiges wird verworfen oder auf Standardwerte gesetzt."""
    out = default_config()
    if not isinstance(raw, dict):
        return out
    out["enabled"] = raw.get("enabled") is True
    out["artnet"] = raw.get("artnet", True) is not False
    out["sacn"] = raw.get("sacn", True) is not False
    out["announce"] = raw.get("announce", True) is not False                    # auf die Art-Net-Suche (ArtPoll) antworten
    bind = str(raw.get("bind") or "").strip()
    out["bind"] = bind if re.fullmatch(r"\d{1,3}(\.\d{1,3}){3}", bind) else ""
    out["timeout"] = max(0.5, min(30.0, _float(raw.get("timeout"), 3.0)))
    allow = raw.get("allow")
    if isinstance(allow, str):
        allow = re.split(r"[,;\s]+", allow)
    out["allow"] = [a.strip() for a in (allow or []) if isinstance(a, str) and _ALLOW.match(a.strip())][:20]
    seen: set = set()

    def ident(item: Dict[str, Any]) -> str:
        key = str(item.get("id", "")).strip()[:40]
        if not key or key in seen:
            key = uuid.uuid4().hex[:12]
        seen.add(key)
        return key

    def protocol(item: Dict[str, Any]) -> str:
        return item.get("protocol") if item.get("protocol") in ("artnet", "sacn") else "any"

    for item in (raw.get("merge") if isinstance(raw.get("merge"), list) else [])[:MAX_MERGE]:
        if not isinstance(item, dict):
            continue
        first = _int(item.get("first"), 1, 1, UNIVERSE_SIZE)
        last = _int(item.get("last"), UNIVERSE_SIZE, 1, UNIVERSE_SIZE)
        out["merge"].append({"id": ident(item), "enabled": item.get("enabled", True) is not False, "name": str(item.get("name", "")).strip()[:60], "protocol": protocol(item),
                             "universe": _int(item.get("universe"), 1, 0, MAX_UNIVERSE), "target": _int(item.get("target"), 1, 1, MAX_OUT_UNIVERSE),
                             "mode": "replace" if item.get("mode") == "replace" else "htp", "first": min(first, last), "last": max(first, last)})
    for item in (raw.get("triggers") if isinstance(raw.get("triggers"), list) else [])[:MAX_TRIGGERS]:
        if not isinstance(item, dict):
            continue
        out["triggers"].append({"id": ident(item), "enabled": item.get("enabled", True) is not False, "name": str(item.get("name", "")).strip()[:60], "protocol": protocol(item),
                                "universe": _int(item.get("universe"), 1, 0, MAX_UNIVERSE), "channel": _int(item.get("channel"), 1, 1, UNIVERSE_SIZE),
                                "kind": "level" if item.get("kind") == "level" else "button", "threshold": _int(item.get("threshold"), 128, 1, 255),
                                "command": " ".join(str(item.get("command", "")).split())[:1000], "command_off": " ".join(str(item.get("command_off", "")).split())[:1000],
                                "min": _float(item.get("min"), 0.0), "max": _float(item.get("max"), 100.0), "log": item.get("log") is True})
    return out


def _allowed(allow: List[str], ip: str) -> bool:
    return not allow or any(ip.startswith(prefix) for prefix in allow)


# ------------------------------------------------------------------------------------------------------------------ Hub (Empfang + Mischen + Ausloeser)
class InputHub:
    """Empfaengt Art-Net / sACN in eigenen Threads und haelt je Quelle den letzten Stand. `merge()` ist der schnelle Weg fuer die Ausgabe (je Takt, ohne Sperre im Normalfall).
    Laeuft im Ausgabe-Prozess (Mischen + Ausloeser) oder, als Rueckfall, im Server (nur Ausloeser + Anzeige)."""

    def __init__(self, on_event: Callable[[Dict[str, Any]], None], log: Optional[Callable[[str, str], None]] = None, merging: bool = True) -> None:
        self.on_event = on_event
        self.log = log or (lambda level, text: None)
        self.merging = merging
        self.cfg: Dict[str, Any] = default_config()
        self.lock = threading.RLock()
        self.sources: Dict[Tuple[str, int, str], Dict[str, Any]] = {}
        self.resolved: Dict[str, Optional[bytes]] = {}                          # Zuordnung -> der gemischte Eingang (512 Byte) oder None (keine lebende Quelle)
        self.by_target: Dict[int, List[Dict[str, Any]]] = {}
        self.own_ports: set = set()
        self.own_cid: bytes = b""
        self.local_ips: set = {"127.0.0.1"}
        self.errors: Dict[str, str] = {}
        self.sock_art: Optional[socket.socket] = None
        self.sock_sacn: Optional[socket.socket] = None
        self.joined: set = set()
        self.generation = 0
        self.stop_event = threading.Event()
        self.watch_until = 0.0
        self.learning_until = 0.0
        self.last_data: Dict[Tuple[str, int], bytes] = {}                       # fuer "Einlernen": der vorige Stand je Universum
        self.state: Dict[str, Dict[str, Any]] = {}                              # Ausloeser -> {on, level, sent, pending, ...}
        self.counters = {"artnet": 0, "sacn": 0, "ignored": 0, "own": 0, "poll": 0}
        self.poll_last: Dict[str, float] = {}                                   # Absender -> Zeitpunkt der letzten Antwort (hoechstens eine je Sekunde)
        threading.Thread(target=self._sweeper, daemon=True, name="dmxin-sweeper").start()

    # ---------------------------------------------------------------- Einstellungen
    @property
    def active(self) -> bool:
        return bool(self.cfg["enabled"])

    def configure(self, raw: Any) -> None:
        cfg = normalize(raw)
        with self.lock:
            self.cfg = cfg
            self.by_target = {}
            for item in cfg["merge"]:
                if item["enabled"]:
                    self.by_target.setdefault(item["target"], []).append(item)
            self.state = {k: v for k, v in self.state.items() if k in {t["id"] for t in cfg["triggers"]}}
            self.generation += 1
            gen = self.generation
            self._refresh_all()
        if cfg["enabled"]:
            self._open(gen)
        else:
            self._close()

    def _universes(self, protocol: str) -> set:
        """Eingangs-Universen, die gebraucht werden (Zuordnungen + Ausloeser) - fuer den sACN-Multicast."""
        wanted = set()
        for item in list(self.cfg["merge"]) + list(self.cfg["triggers"]):
            if item.get("enabled", True) and item["protocol"] in ("any", protocol):
                wanted.add(int(item["universe"]))
        return wanted

    # ---------------------------------------------------------------- Netzwerk
    def _open(self, gen: int) -> None:
        self._refresh_local_ips()
        cfg = self.cfg
        if cfg["artnet"] and self.sock_art is None:
            self.sock_art = self._bind(ARTNET_PORT, "artnet", broadcast=True)
            if self.sock_art is not None:
                threading.Thread(target=self._loop, args=(self.sock_art, "artnet"), daemon=True, name="dmxin-artnet").start()
        elif not cfg["artnet"]:
            self._drop("artnet")
        if cfg["sacn"] and self.sock_sacn is None:
            self.sock_sacn = self._bind(SACN_PORT, "sacn")
            if self.sock_sacn is not None:
                threading.Thread(target=self._loop, args=(self.sock_sacn, "sacn"), daemon=True, name="dmxin-sacn").start()
        elif not cfg["sacn"]:
            self._drop("sacn")
        self._join_groups()

    def _bind(self, port: int, name: str, broadcast: bool = False) -> Optional[socket.socket]:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            if broadcast:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            s.bind((self.cfg["bind"] or "", port))
            s.settimeout(0.5)
            self.errors.pop(name, None)
            return s
        except OSError as exc:
            self.errors[name] = f"{exc.__class__.__name__}: {exc}"
            self.log("warning", f"DMX-Eingang {name}: Port {port} nicht verfuegbar ({exc})")
            return None

    def _drop(self, name: str) -> None:
        sock = self.sock_art if name == "artnet" else self.sock_sacn
        if name == "artnet":
            self.sock_art = None
        else:
            self.sock_sacn = None
            self.joined = set()
        if sock is not None:
            try:
                sock.close()
            except OSError:
                pass
        with self.lock:
            for key in [k for k in self.sources if k[0] == name]:
                del self.sources[key]
            self._refresh_all()

    def _close(self) -> None:
        self._drop("artnet")
        self._drop("sacn")
        with self.lock:
            self.sources.clear()
            self._refresh_all()

    def _refresh_local_ips(self) -> None:
        ips = {"127.0.0.1"}
        try:
            from app import artnet_discovery
            ips.update(artnet_discovery.local_addresses())
        except Exception:
            pass
        self.local_ips = ips

    def _join_groups(self) -> None:
        sock = self.sock_sacn
        if sock is None:
            return
        want = self._universes("sacn")
        interfaces = [self.cfg["bind"]] if self.cfg["bind"] else sorted(self.local_ips - {"127.0.0.1"}) or [""]
        for universe in want - self.joined:
            group = socket.inet_aton(f"239.255.{(universe >> 8) & 0xFF}.{universe & 0xFF}")
            for iface in interfaces:
                try:
                    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, group + (socket.inet_aton(iface) if iface else b"\x00\x00\x00\x00"))
                except OSError as exc:
                    self.errors["sacn_join"] = f"Universum {universe}: {exc}"
            self.joined.add(universe)
        for universe in self.joined - want:
            group = socket.inet_aton(f"239.255.{(universe >> 8) & 0xFF}.{universe & 0xFF}")
            for iface in interfaces:
                try:
                    sock.setsockopt(socket.IPPROTO_IP, socket.IP_DROP_MEMBERSHIP, group + (socket.inet_aton(iface) if iface else b"\x00\x00\x00\x00"))
                except OSError:
                    pass
            self.joined.discard(universe)

    def _loop(self, sock: socket.socket, name: str) -> None:
        while not self.stop_event.is_set():
            current = self.sock_art if name == "artnet" else self.sock_sacn
            if current is not sock:
                return                                                   # umgebaut oder geschlossen
            try:
                data, addr = sock.recvfrom(1500)
            except socket.timeout:
                continue
            except OSError:
                if current is not sock:
                    return
                time.sleep(0.2)
                continue
            try:
                if name == "artnet" and len(data) >= 12 and data[:8] == b"Art-Net\x00" and data[8] == 0x00 and data[9] == 0x20:
                    self._poll_reply(sock, addr)                         # ArtPoll: andere Geraete suchen Art-Net-Knoten
                else:
                    self._packet(name, data, addr)
            except Exception as exc:                                     # nie den Empfang beenden
                self.log("debug", f"DMX-Eingang: Paket verworfen ({exc})")

    def _poll_reply(self, sock: socket.socket, addr: Tuple[str, int]) -> None:
        """ArtPollReply an den Suchenden (nur wenn 'Als Art-Net-Geraet melden' an ist, der Absender erlaubt ist und hoechstens einmal je Sekunde)."""
        ip = addr[0]
        if not (self.cfg["enabled"] and self.cfg["announce"]) or not _allowed(self.cfg["allow"], ip):
            return
        now = time.monotonic()
        if now - self.poll_last.get(ip, -99.0) < 1.0:
            return
        self.poll_last[ip] = now
        if len(self.poll_last) > 200:
            for old in sorted(self.poll_last, key=self.poll_last.get)[:100]:
                self.poll_last.pop(old, None)
        mine = self._address_towards(ip)
        with self.lock:
            live = {k[1] for k in self.sources if k[0] == "artnet"}
        universes = self._universes("artnet")
        try:
            mac = uuid.getnode().to_bytes(6, "big")
        except OverflowError:
            mac = b"\x00" * 6
        for index, group in enumerate(_poll_groups(universes), start=1):
            try:
                sock.sendto(build_poll_reply(mine, group, live, index, mac), (ip, ARTNET_PORT))
                self.counters["poll"] += 1
            except OSError:
                break

    def _address_towards(self, ip: str) -> str:
        """Eigene Adresse, ueber die der Absender erreichbar ist (die Betriebssystem-Wahl; sonst die erste bekannte)."""
        try:
            probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                probe.connect((ip, ARTNET_PORT))
                return probe.getsockname()[0]
            finally:
                probe.close()
        except OSError:
            others = sorted(self.local_ips - {"127.0.0.1"})
            return others[0] if others else "127.0.0.1"

    # ---------------------------------------------------------------- Pakete
    def _packet(self, name: str, data: bytes, addr: Tuple[str, int]) -> None:
        ip, port = addr[0], addr[1]
        if not self.cfg["enabled"]:
            return
        parsed = parse_artnet(data) if name == "artnet" else parse_sacn(data)
        if parsed is None:
            return
        if name == "artnet" and port in self.own_ports and ip in self.local_ips:
            self.counters["own"] += 1                                    # die eigene Ausgabe (Broadcast kommt am eigenen Rechner an)
            return
        if name == "sacn" and self.own_cid and parsed["cid"] == self.own_cid:
            self.counters["own"] += 1
            return
        if not _allowed(self.cfg["allow"], ip):
            self.counters["ignored"] += 1
            return
        self.counters[name] += 1
        now = time.monotonic()
        universe = parsed["universe"]
        sid = ip if name == "artnet" else parsed["cid"].hex()
        key = (name, universe, sid)
        dmx = parsed["dmx"]
        with self.lock:
            src = self.sources.get(key)
            if parsed.get("terminated"):                                 # sACN: "Stream beendet" - die Quelle ist sofort weg
                if src is not None:
                    del self.sources[key]
                    self._refresh_universe(name, universe)
                return
            if src is None:
                src = self.sources[key] = {"protocol": name, "universe": universe, "sid": sid, "ip": ip, "name": parsed.get("name", ""), "priority": parsed.get("priority", 100),
                                           "data": bytearray(UNIVERSE_SIZE), "len": 0, "last": now, "packets": 0, "window": [now, 0], "pps": 0.0}
            src["priority"] = parsed.get("priority", src["priority"])
            src["ip"] = ip
            if parsed.get("name"):
                src["name"] = parsed["name"]
            previous = bytes(src["data"][:len(dmx)]) if src["packets"] else None
            src["data"][:len(dmx)] = dmx
            if len(dmx) < UNIVERSE_SIZE and src["len"] > len(dmx):
                src["data"][len(dmx):src["len"]] = bytes(src["len"] - len(dmx))
            src["len"] = len(dmx)
            src["last"] = now
            src["packets"] += 1
            window = src["window"]
            window[1] += 1
            if now - window[0] >= 1.0:
                src["pps"] = window[1] / (now - window[0])
                window[0], window[1] = now, 0
            self._refresh_universe(name, universe)
            self._learn(name, universe, dmx, previous)
            triggers = [t for t in self.cfg["triggers"] if t["enabled"] and t["universe"] == universe and t["protocol"] in ("any", name)]
        if triggers:
            self._triggers(triggers, dmx, now)

    # ---------------------------------------------------------------- Mischen
    def _alive(self, now: float) -> List[Dict[str, Any]]:
        limit = self.cfg["timeout"]
        return [s for s in self.sources.values() if now - s["last"] <= limit]

    def _resolve(self, item: Dict[str, Any], now: float) -> Optional[bytes]:
        group = [s for s in self._alive(now) if s["universe"] == item["universe"] and item["protocol"] in ("any", s["protocol"])]
        if not group:
            return None
        top = max((s["priority"] for s in group if s["protocol"] == "sacn"), default=None)
        if top is not None:                                              # sACN: nur die Quellen mit der hoechsten Prioritaet zaehlen (Art-Net hat keine)
            group = [s for s in group if s["protocol"] != "sacn" or s["priority"] == top]
        acc = bytes(group[0]["data"])
        for src in group[1:]:
            acc = bytes(map(max, acc, src["data"]))                      # mehrere Quellen: Hoechster gewinnt
        return acc

    def _refresh_all(self) -> None:
        now = time.monotonic()
        self.resolved = {item["id"]: self._resolve(item, now) for item in self.cfg["merge"] if item["enabled"]}

    def _refresh_universe(self, protocol: str, universe: int) -> None:
        now = time.monotonic()
        for item in self.cfg["merge"]:
            if item["enabled"] and item["universe"] == universe and item["protocol"] in ("any", protocol):
                self.resolved[item["id"]] = self._resolve(item, now)

    def merge(self, universe: int, data: bytes) -> bytes:
        """Der Ausgabe-Takt: die gemischten Eingaenge in das Bild eines Universums einrechnen (HTP / Ersetzen). Ohne Zuordnung kommt `data` unveraendert zurueck."""
        if not self.merging or not self.cfg["enabled"]:
            return data
        items = self.by_target.get(universe)
        if not items:
            return data
        out = data
        for item in items:
            res = self.resolved.get(item["id"])
            if res is None:
                continue
            a, b = item["first"] - 1, item["last"]
            if item["mode"] == "replace":
                seg = res[a:b]
            else:
                seg = bytes(map(max, out[a:b], res[a:b]))
            out = out[:a] + seg + out[b:]
        return out

    def target_universes(self) -> List[int]:
        return sorted(self.by_target) if self.cfg["enabled"] else []

    # ---------------------------------------------------------------- Ausloeser
    def _triggers(self, triggers: List[Dict[str, Any]], dmx: bytes, now: float) -> None:
        with self.lock:
            self._triggers_locked(triggers, dmx, now)

    def _triggers_locked(self, triggers: List[Dict[str, Any]], dmx: bytes, now: float) -> None:
        for trig in triggers:
            value = dmx[trig["channel"] - 1] if trig["channel"] <= len(dmx) else 0
            st = self.state.setdefault(trig["id"], {"seen": False, "on": False, "level": 0, "sent": -1, "pending": None, "at": 0.0})
            if not st["seen"]:                                           # erster Stand: nur merken, nichts ausloesen (kein Sprung beim Verbinden)
                st.update(seen=True, on=value >= trig["threshold"], level=value, sent=value)
                continue
            if trig["kind"] == "button":
                on = value >= trig["threshold"]
                if on != st["on"]:
                    st["on"] = on
                    self.on_event({"type": "trigger", "id": trig["id"], "edge": "on" if on else "off", "value": value})
            else:
                if value != st["sent"]:
                    if now - st["at"] >= _HOLD_PER_LEVEL:
                        st["sent"], st["at"], st["pending"] = value, now, None
                        self.on_event({"type": "trigger", "id": trig["id"], "edge": "level", "value": value})
                    else:
                        st["pending"] = value                            # der Sweeper liefert den neuesten Wert nach

    def _flush_pending(self, now: float) -> None:
        with self.lock:
            due = [(tid, st) for tid, st in self.state.items() if st["pending"] is not None and now - st["at"] >= _HOLD_PER_LEVEL]
            for tid, st in due:
                value, st["pending"] = st["pending"], None
                st["sent"], st["at"] = value, now
                self.on_event({"type": "trigger", "id": tid, "edge": "level", "value": value})

    # ---------------------------------------------------------------- Einlernen
    def learn(self, on: bool, seconds: float = 20.0) -> None:
        with self.lock:
            self.learning_until = time.monotonic() + seconds if on else 0.0
            self.last_data = {}

    def _learn(self, protocol: str, universe: int, dmx: bytes, previous: Optional[bytes]) -> None:
        if not self.learning_until:
            return
        if time.monotonic() > self.learning_until:
            self.learning_until = 0.0
            return
        if previous is None or len(previous) != len(dmx):
            return
        best, delta = -1, 0
        for index, (old, new) in enumerate(zip(previous, dmx)):
            d = abs(new - old)
            if d > delta:
                best, delta = index, d
        if best >= 0 and delta >= 16:
            self.learning_until = 0.0
            self.on_event({"type": "learn", "protocol": protocol, "universe": universe, "channel": best + 1, "value": dmx[best]})

    # ---------------------------------------------------------------- Zustand
    def watch(self, on: bool) -> None:
        self.watch_until = time.monotonic() + 6.0 if on else 0.0

    def status(self, with_data: bool = False) -> Dict[str, Any]:
        now = time.monotonic()
        with self.lock:
            sources = []
            for s in sorted(self.sources.values(), key=lambda x: (x["universe"], x["protocol"], x["ip"])):
                age = now - s["last"]
                row = {"protocol": s["protocol"], "universe": s["universe"], "ip": s["ip"], "name": s["name"], "priority": s["priority"] if s["protocol"] == "sacn" else None,
                       "pps": round(s["pps"], 1) if age < 2.5 else 0.0, "age": round(age, 1), "alive": age <= self.cfg["timeout"], "slots": s["len"],
                       "nonzero": sum(1 for v in s["data"][:s["len"]] if v)}
                if with_data:
                    row["data"] = base64.b64encode(bytes(s["data"][:s["len"]])).decode("ascii")
                sources.append(row)
            return {"listening": {"artnet": self.sock_art is not None, "sacn": self.sock_sacn is not None}, "errors": dict(self.errors), "sources": sources,
                    "counters": dict(self.counters), "joined": sorted(self.joined), "merging": self.merging, "targets": self.target_universes()}

    def _sweeper(self) -> None:
        last_status = 0.0
        while not self.stop_event.is_set():
            time.sleep(0.05)
            now = time.monotonic()
            if self.cfg["enabled"]:
                self._flush_pending(now)
                with self.lock:
                    changed = False
                    for item in self.cfg["merge"]:
                        if item["enabled"] and self.resolved.get(item["id"]) is not None and self._resolve(item, now) is None:
                            self.resolved[item["id"]] = None
                            changed = True
                    for key in [k for k, s in self.sources.items() if now - s["last"] > max(self.cfg["timeout"] * 4, 15.0)]:
                        del self.sources[key]                            # lange verschwunden: aus der Liste nehmen
                    _ = changed
                watching = now < self.watch_until
                if now - last_status >= (0.25 if watching else 1.0):
                    last_status = now
                    self.on_event({"type": "status", "snap": self.status(with_data=watching)})        # (nicht "status": der Prozess liest diesen Schluessel als Taktzustand)

    def shutdown(self) -> None:
        self.stop_event.set()
        self._close()


# ------------------------------------------------------------------------------------------------------------------ Server: Manager
def _fmt(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else f"{value:.2f}".rstrip("0").rstrip(".")


class DmxInManager:
    """Server-Seite: Einstellungen an den Ausgabe-Prozess schicken (oder im Rueckfall den lokalen Hub betreiben), Ausloeser in Befehle umsetzen, Zustand fuer die Oberflaeche."""

    def __init__(self) -> None:
        self.config: Dict[str, Any] = default_config()
        self.dmx: Any = None
        self.loop: Optional[Any] = None
        self.runner: Optional[Callable[[str, bool], Any]] = None
        self.status_cache: Dict[str, Any] = {}
        self.status_at = 0.0
        self.recent: Deque[Dict[str, Any]] = collections.deque(maxlen=60)
        self.seq = 0
        self.learned: Optional[Dict[str, Any]] = None
        self.local: Optional[InputHub] = None
        self.where = "off"                                                     # "process" | "server" | "off"
        self._watch_sent = 0.0

    # ---------------------------------------------------------------- Anbindung
    def attach(self, dmx_engine: Any, loop: Any, runner: Callable[[str, bool], Any]) -> None:
        self.dmx, self.loop, self.runner = dmx_engine, loop, runner
        previous = dmx_engine.on_output_event

        def on_event(message: Dict[str, Any]) -> None:
            if message.get("event") == "dmxin":
                self.handle(message)
            elif previous is not None:
                previous(message)

        dmx_engine.on_output_event = on_event

    def _process(self) -> Any:
        proc = getattr(self.dmx, "_proc", None) if self.dmx is not None else None
        return proc if proc is not None and proc.alive else None

    def configure_sync(self, raw: Any) -> None:
        self.config = normalize(raw)
        cfg = self.config
        proc = self._process()
        if cfg["enabled"] and self.dmx is not None:
            for universe in sorted({m["target"] for m in cfg["merge"] if m["enabled"]}):      # ein Ziel-Universum ohne gepatchte Geraete wird trotzdem ausgegeben (reine Weiterleitung)
                try:
                    with self.dmx._lock:
                        self.dmx._ensure_universe(universe)
                except Exception as exc:
                    logger.warning("DMX-Eingang: Universum %s konnte nicht angelegt werden: %s", universe, exc)
        if proc is not None:
            if self.local is not None:
                self.local.shutdown()
                self.local = None
            proc.dmxin_last = {"cmd": "dmxin", "cfg": cfg}
            proc.send(proc.dmxin_last)
            self.where = "process" if cfg["enabled"] else "off"
        else:
            if self.local is None:
                self.local = InputHub(self._local_event, lambda level, text: logger.log(logging.WARNING if level == "warning" else logging.DEBUG, text), merging=False)
            self.local.configure(cfg)
            self.where = "server" if cfg["enabled"] else "off"
        if not cfg["enabled"]:
            self.status_cache = {}

    async def configure(self, raw: Any) -> None:
        await __import__("asyncio").to_thread(self.configure_sync, raw)

    # ---------------------------------------------------------------- Ereignisse
    def _local_event(self, message: Dict[str, Any]) -> None:
        self.handle({"event": "dmxin", **message})

    def handle(self, message: Dict[str, Any]) -> None:
        kind = message.get("type")
        if kind == "status":
            self.status_cache = message.get("snap") or {}
            self.status_at = time.monotonic()
        elif kind == "learn":
            self.seq += 1
            self.learned = {"n": self.seq, **{k: message.get(k) for k in ("protocol", "universe", "channel", "value")}}
        elif kind == "trigger":
            self._run_trigger(str(message.get("id", "")), str(message.get("edge", "")), int(message.get("value", 0)))

    def _note(self, text: str) -> None:
        self.seq += 1
        self.recent.append({"n": self.seq, "t": time.strftime("%H:%M:%S"), "text": text})

    def _run_trigger(self, tid: str, edge: str, value: int) -> None:
        trig = next((t for t in self.config["triggers"] if t["id"] == tid and t["enabled"]), None)
        if trig is None:
            return
        command = trig["command"] if edge in ("on", "level") else trig["command_off"]
        if not command:
            return
        if edge == "level":
            if "{value}" not in command:
                command = command                                                    # ohne Platzhalter: der Befehl laeuft bei jeder Aenderung
            else:
                command = command.replace("{value}", _fmt(trig["min"] + value / 255.0 * (trig["max"] - trig["min"])))
        self._note(f"{trig['name'] or 'U' + str(trig['universe']) + '.' + str(trig['channel'])} = {value}: {command}")
        if self.runner is not None and self.loop is not None:
            import asyncio
            try:
                asyncio.run_coroutine_threadsafe(self.runner(command, trig["log"]), self.loop)
            except Exception:
                logger.exception("DMX-Eingang: Befehl konnte nicht gestartet werden: %s", command)

    # ---------------------------------------------------------------- Anzeige / Steuerung
    def request_watch(self) -> None:
        now = time.monotonic()
        if now - self._watch_sent < 2.0:
            return
        self._watch_sent = now
        proc = self._process()
        if proc is not None:
            proc.send({"cmd": "dmxin_watch", "on": True})
        elif self.local is not None:
            self.local.watch(True)

    def learn(self, on: bool) -> None:
        self.learned = None
        proc = self._process()
        if proc is not None:
            proc.send({"cmd": "dmxin_learn", "on": bool(on)})
        elif self.local is not None:
            self.local.learn(bool(on))

    def status(self) -> Dict[str, Any]:
        stale = self.status_at and time.monotonic() - self.status_at > 4.0
        base = self.status_cache if self.config["enabled"] and not stale else {}
        return {"enabled": self.config["enabled"], "where": self.where, "merge_available": self.where == "process", **{k: base.get(k) for k in ("listening", "errors", "sources", "counters", "joined", "targets")}}

    def stop(self) -> None:
        if self.local is not None:
            self.local.shutdown()


manager = DmxInManager()


def _local(request: Request) -> bool:
    from app import remote
    return remote.is_local(request.client.host if request.client else None)


@router.get("/api/dmx-in")
async def get_dmx_in(watch: int = 0) -> JSONResponse:
    if watch:
        manager.request_watch()
    return JSONResponse({"ok": True, "config": manager.config, "status": manager.status(), "recent": list(manager.recent), "learned": manager.learned})


@router.post("/api/dmx-in/config")
async def set_dmx_in(request: Request) -> JSONResponse:
    from app.state_manager import state
    cfg = normalize(await request.json())
    state.dmx_in_config = cfg
    state.save_app_config()
    await manager.configure(cfg)
    return JSONResponse({"ok": True, "config": manager.config, "status": manager.status()})


@router.post("/api/dmx-in/learn")
async def learn_dmx_in(request: Request) -> JSONResponse:
    body = await request.json()
    manager.learn(bool(isinstance(body, dict) and body.get("on")))
    return JSONResponse({"ok": True})
