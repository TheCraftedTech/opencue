# Copyright (C) 2026 Samuel Zenker
# SPDX-License-Identifier: GPL-3.0-or-later
"""
OSC (Open Sound Control): OpenCue wird per Netzwerk von anderen Programmen und Geraeten gesteuert (TouchOSC, QLab, Ableton, Pulte ...) und kann selbst Nachrichten senden.

Empfangen (UDP, Standard-Port 9000, standardmaessig AUS): jede Nachricht wird mit der Tabelle des Nutzers ("Steuerung -> OSC") verglichen:
  * Zuordnungen: Adresse (auch mit * und ?) -> Befehl der Befehlszeile. `{value}` im Befehl ist der erste Wert der Nachricht, auf einen Bereich umgerechnet (Standard: 0..1 -> 0..100).
    "Nur Druecken": der Befehl laeuft nur, wenn der Wert > 0 ist (Tasten schicken 1 beim Druecken und 0 beim Loslassen); "Immer": bei jeder Nachricht (Fader).
  * Eingebaute Adressen (immer, wenn OSC an ist): /opencue/go, /back, /pause, /resume, /stop, /blackout [0|1], /master <0..1>, /fader <0..1>, /cue/<nummer> (springt zu Cue).
  * /opencue/cmd "<Befehl>" fuehrt einen beliebigen Befehl aus - nur, wenn "Beliebige Befehle erlauben" eingeschaltet ist.
Senden: Befehl `Osc <adresse> [werte ...]` schickt eine Nachricht an das Ziel aus den Einstellungen (Host / Port).
Rueckkanal (Einstellung "feedback", standardmaessig AUS): OpenCue meldet seinen Zustand von selbst an das Ziel (und auf Wunsch an jeden Absender, der gerade Nachrichten schickt), z. B. fuer die
  Anzeigen und Tasten-LEDs von TouchOSC. Gemeldet wird nur, was sich aendert (alle 100 ms geprueft), zusaetzlich alles auf einmal beim Einschalten, bei einem neuen Absender und auf Knopfdruck:
  <Vorsilbe>/cue <Nummer>, /cuename <Name>, /cuelist <Name>, /state running|paused|stopped|done|idle, /fader 0..1, /master 0..1, /blackout 0|1, /cue/<Nummer> 1 (aktiver Cue; 0 beim Verlassen).

SICHERHEIT: OSC kennt kein Passwort - jeder im Netzwerk kann senden. Deshalb: AUS ist der Standard, optional eine Liste erlaubter Absender (IP-Adresse oder Anfang davon), eine Bremse
(300 Nachrichten / s) und beliebige Befehle nur auf ausdruecklichen Wunsch. Rein Python (struct), keine neue Bibliothek.

  GET  /api/osc          Einstellungen, Zustand (lauscht, Adressen, Fehler), die letzten Nachrichten (?since=<Nr>), eingebaute Adressen
  POST /api/osc/config   Einstellungen speichern (nur lokal)
  POST /api/osc/send     eine Nachricht an das Ziel schicken (nur lokal): {address, args}
"""
from __future__ import annotations

import asyncio
import collections
import fnmatch
import logging
import re
import socket
import struct
import time
import uuid
from typing import Any, Awaitable, Callable, Deque, Dict, List, Optional, Tuple

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger("opencue.osc")
router = APIRouter()

DEFAULT_PORT = 9000
MAX_PACKET = 8192
MAX_ARGS = 32
MAX_BINDINGS = 200
RATE_LIMIT = 300                                     # Nachrichten je Sekunde (darueber werden sie verworfen)

Message = Tuple[str, List[Any]]


# ---------------------------------------------------------------------------------------------------------------- Format
def _pad(n: int) -> int:
    return (n + 3) & ~3


def _read_string(data: bytes, pos: int) -> Tuple[str, int]:
    end = data.index(b"\x00", pos)
    return data[pos:end].decode("utf-8", "replace"), _pad(end + 1)


def parse_packet(data: bytes, depth: int = 0) -> List[Message]:
    """Ein OSC-Paket (Nachricht oder Bundle) -> Liste (Adresse, Werte). Beschaedigtes wird ausgelassen, nie ein Fehler."""
    out: List[Message] = []
    if not data or len(data) > MAX_PACKET or depth > 4:
        return out
    try:
        if data.startswith(b"#bundle\x00"):
            pos = 16                                                      # "#bundle" + Zeitmarke
            while pos + 4 <= len(data):
                (size,) = struct.unpack_from(">i", data, pos)
                pos += 4
                if size <= 0 or pos + size > len(data):
                    break
                out.extend(parse_packet(data[pos:pos + size], depth + 1))
                pos += size
            return out
        address, pos = _read_string(data, 0)
        if not address.startswith("/"):
            return out
        args: List[Any] = []
        if pos < len(data) and data[pos:pos + 1] == b",":
            tags, pos = _read_string(data, pos)
            for tag in tags[1:][:MAX_ARGS]:
                if tag == "i":
                    args.append(struct.unpack_from(">i", data, pos)[0]); pos += 4
                elif tag == "f":
                    args.append(struct.unpack_from(">f", data, pos)[0]); pos += 4
                elif tag == "s" or tag == "S":
                    value, pos = _read_string(data, pos); args.append(value)
                elif tag == "b":
                    (size,) = struct.unpack_from(">i", data, pos)
                    args.append(bytes(data[pos + 4:pos + 4 + size])); pos += 4 + _pad(size)
                elif tag == "h":
                    args.append(struct.unpack_from(">q", data, pos)[0]); pos += 8
                elif tag == "d":
                    args.append(struct.unpack_from(">d", data, pos)[0]); pos += 8
                elif tag == "t":
                    pos += 8
                elif tag == "c":
                    args.append(chr(struct.unpack_from(">I", data, pos)[0])); pos += 4
                elif tag in ("r", "m"):
                    pos += 4
                elif tag == "T":
                    args.append(True)
                elif tag == "F":
                    args.append(False)
                elif tag in ("N", "I"):
                    args.append(None)
                else:
                    break                                                 # unbekannte Art: was bis hier gelesen ist, gilt
        out.append((address, args))
    except (ValueError, struct.error, IndexError):
        pass
    return out


def build_message(address: str, args: List[Any]) -> bytes:
    """Eine OSC-Nachricht bauen. Werte: int -> i, float -> f, bool -> T/F, None -> N, sonst Text (s)."""
    def pad_str(text: str) -> bytes:
        raw = text.encode("utf-8") + b"\x00"
        return raw + b"\x00" * (_pad(len(raw)) - len(raw))
    tags, body = ",", b""
    for value in args[:MAX_ARGS]:
        if isinstance(value, bool):
            tags += "T" if value else "F"
        elif isinstance(value, int) and -2**31 <= value < 2**31:
            tags += "i"; body += struct.pack(">i", value)
        elif isinstance(value, (int, float)):
            tags += "f"; body += struct.pack(">f", float(value))
        elif value is None:
            tags += "N"
        else:
            tags += "s"; body += pad_str(str(value))
    return pad_str(address) + pad_str(tags) + body


def guess_value(text: str) -> Any:
    """Wert aus einem Befehl ("Osc /x 0.5 1 hello"): ganze Zahl, Zahl, true/false, sonst Text."""
    low = text.strip().lower()
    if low in ("true", "on"):
        return True
    if low in ("false", "off"):
        return False
    try:
        return int(low)
    except ValueError:
        pass
    try:
        return float(low.replace(",", "."))
    except ValueError:
        return text


# ---------------------------------------------------------------------------------------------------------------- Einstellungen
DEFAULT_PREFIX = "/opencue"
BUILTIN_NAMES = ("go", "back", "pause", "resume", "stop", "blackout", "master", "fader", "cue", "cmd")
FEEDBACK_NAMES = ("cue", "cuename", "cuelist", "state", "fader", "master", "blackout", "leds")             # was der Rueckkanal melden kann (einzeln abschaltbar)
FEEDBACK_INTERVAL = 0.1
_PREFIX = re.compile(r"^/[A-Za-z0-9_\-]{1,40}(?:/[A-Za-z0-9_\-]{1,40}){0,3}$")
DEFAULTS: Dict[str, Any] = {"enabled": False, "port": DEFAULT_PORT, "allow": [], "raw": False, "send": {"host": "", "port": 9001}, "bindings": [],
                            "builtin": {"enabled": True, "prefix": DEFAULT_PREFIX, "off": []},
                            "feedback": {"enabled": False, "senders": True, "off": []}}
_ADDRESS = re.compile(r"^/[^\s]{0,119}$")
_ALLOW = re.compile(r"^[0-9a-fA-F:.]{1,45}$")
_HOST = re.compile(r"^[A-Za-z0-9._\-:]{1,120}$")


def _port(value: Any, default: int) -> int:
    try:
        number = int(float(value))
    except (TypeError, ValueError, OverflowError):
        return default
    return number if 1 <= number <= 65535 else default


def _number(value: Any, default: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if number == number and abs(number) < 1e9 else default


def normalize(raw: Any) -> Dict[str, Any]:
    """Einstellungen pruefen: Unbekanntes und Ungueltiges wird verworfen."""
    out: Dict[str, Any] = {"enabled": False, "port": DEFAULT_PORT, "allow": [], "raw": False, "send": {"host": "", "port": 9001}, "bindings": [],
                           "builtin": {"enabled": True, "prefix": DEFAULT_PREFIX, "off": []}, "feedback": {"enabled": False, "senders": True, "off": []}}
    if not isinstance(raw, dict):
        return out
    feedback = raw.get("feedback")
    if isinstance(feedback, dict):                                           # Rueckkanal: an/aus, auch an Absender, einzelne Meldungen abschalten
        off = feedback.get("off")
        out["feedback"] = {"enabled": feedback.get("enabled") is True, "senders": feedback.get("senders", True) is not False,
                           "off": sorted({str(n) for n in (off if isinstance(off, list) else []) if str(n) in FEEDBACK_NAMES})}
    builtin = raw.get("builtin")
    if isinstance(builtin, dict):                                            # eingebaute Adressen: ganz aus, Vorsilbe aendern, einzelne abschalten
        prefix = str(builtin.get("prefix", DEFAULT_PREFIX)).strip().rstrip("/")
        off = builtin.get("off")
        out["builtin"] = {"enabled": builtin.get("enabled", True) is not False, "prefix": prefix if _PREFIX.match(prefix) else DEFAULT_PREFIX,
                          "off": sorted({str(n) for n in (off if isinstance(off, list) else []) if str(n) in BUILTIN_NAMES})}
    out["enabled"] = raw.get("enabled") is True
    out["port"] = _port(raw.get("port"), DEFAULT_PORT)
    out["raw"] = raw.get("raw") is True
    allow = raw.get("allow")
    if isinstance(allow, str):
        allow = re.split(r"[,;\s]+", allow)
    out["allow"] = [a.strip() for a in (allow or []) if isinstance(a, str) and _ALLOW.match(a.strip())][:20]
    send = raw.get("send")
    if isinstance(send, dict):
        host = str(send.get("host", "")).strip()
        out["send"] = {"host": host if _HOST.match(host) else "", "port": _port(send.get("port"), 9001)}
    seen = set()
    bindings = raw.get("bindings")
    for item in (bindings if isinstance(bindings, list) else [])[:MAX_BINDINGS]:
        if not isinstance(item, dict):
            continue
        address = str(item.get("address", "")).strip()
        if not _ADDRESS.match(address):
            continue
        key = str(item.get("id", "")).strip()[:40]
        if not key or key in seen:
            key = uuid.uuid4().hex[:12]
        seen.add(key)
        out["bindings"].append({
            "id": key, "enabled": item.get("enabled", True) is not False, "address": address, "command": " ".join(str(item.get("command", "")).split())[:1000],
            "mode": "always" if item.get("mode") == "always" else "press", "scale": item.get("scale", True) is not False,
            "min": _number(item.get("min"), 0.0), "max": _number(item.get("max"), 100.0), "log": item.get("log") is True,
        })
    return out


def _glob(address: str) -> "re.Pattern[str]":
    """OSC-Muster (* ? [..] {a,b}) -> regulaerer Ausdruck."""
    out, i = "", 0
    while i < len(address):
        c = address[i]
        if c == "*":
            out += "[^/]*"
        elif c == "?":
            out += "[^/]"
        elif c == "{":
            j = address.find("}", i)
            if j < 0:
                out += re.escape(c)
            else:
                out += "(?:" + "|".join(re.escape(p) for p in address[i + 1:j].split(",")) + ")"
                i = j
        elif c == "[":
            j = address.find("]", i)
            if j < 0:
                out += re.escape(c)
            else:
                out += "[" + address[i + 1:j].replace("\\", "\\\\") + "]"
                i = j
        else:
            out += re.escape(c)
        i += 1
    return re.compile("^" + out + "$")


def _fmt(value: float) -> str:
    return f"{value:.2f}".rstrip("0").rstrip(".") or "0"


# eingebaute Adressen: (Name, Adresse hinter der Vorsilbe, Befehl, Beschreibung)
BUILTIN = (
    ("go", "/go", "Go", "Go (next cue of the active list)"), ("back", "/back", "Back", "Back"), ("pause", "/pause", "Pause", "Pause"), ("resume", "/resume", "Resume", "Resume"),
    ("stop", "/stop", "Stop", "Stop"), ("blackout", "/blackout", "Blackout", "Blackout: 1 = on, 0 = off, no value = toggle"),
    ("master", "/master", "Master {value}", "Grand master: 0..1"), ("fader", "/fader", "Fader {value}", "Executor fader of the active list: 0..1"),
    ("cue", "/cue/<number>", "Goto Cue <number>", "Jump to this cue of the active list"),
)


class OscEngine:
    def __init__(self) -> None:
        self.config: Dict[str, Any] = normalize(None)
        self.transport: Optional[asyncio.DatagramTransport] = None
        self.error = ""
        self.recent: Deque[Dict[str, Any]] = collections.deque(maxlen=60)
        self.seq = 0
        self.runner: Optional[Callable[[str, bool], Awaitable[Any]]] = None          # server: Befehl ausfuehren (mit / ohne Eintrag im Befehlsverlauf)
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._window_start = 0.0
        self._window_count = 0
        self._pending: Dict[str, Tuple[str, bool]] = {}                              # Zuordnung -> juengster Befehl (Fader-Strom: nur der neueste zaehlt)
        self._draining = False
        self._compiled: List[Tuple[Dict[str, Any], "re.Pattern[str]"]] = []
        self._senders: Dict[str, float] = {}                                         # Absender (IP) -> zuletzt gehoert (monotonic): Ziele des Rueckkanals
        self._fb_task: Optional["asyncio.Task[None]"] = None
        self._fb_last: Dict[str, List[Any]] = {}                                     # zuletzt gemeldeter Zustand (Adresse -> Werte)
        self._fb_known: set = set()                                                  # Ziele, die den vollen Zustand schon bekommen haben
        self._fb_sock: Optional[socket.socket] = None
        self.fb_sent = 0

    # ---------------------------------------------------------------- Lebenszyklus
    async def configure(self, raw: Any) -> None:
        """Einstellungen uebernehmen; Socket je nach Bedarf oeffnen, umbinden oder schliessen."""
        old = self.config
        self.config = normalize(raw)
        self._compiled = [(b, _glob(b["address"])) for b in self.config["bindings"]]
        self._loop = asyncio.get_running_loop()
        if self.transport is not None and (not self.config["enabled"] or old.get("port") != self.config["port"]):
            self.stop_socket()
        if self.config["enabled"] and self.transport is None:
            await self._open()
        if not self.config["enabled"]:
            self.error = ""
        if old.get("feedback") != self.config["feedback"] or old.get("send") != self.config["send"]:
            self.resend()                                                              # neue Einstellungen: allen Zielen den vollen Zustand schicken
        self._sync_feedback_task()

    async def _open(self) -> None:
        loop = asyncio.get_running_loop()
        try:
            transport, _protocol = await loop.create_datagram_endpoint(lambda: _Protocol(self), local_addr=("0.0.0.0", self.config["port"]), allow_broadcast=True)
            self.transport = transport                                                # type: ignore[assignment]
            self.error = ""
            logger.info("[OSC] Listening on UDP port %d", self.config["port"])
        except OSError as exc:
            self.transport = None
            self.error = str(exc)
            logger.warning("[OSC] OC-3801 Could not open UDP port %s: %s", self.config["port"], exc)

    def stop_socket(self) -> None:
        if self.transport is not None:
            try:
                self.transport.close()
            except Exception:                                                         # noqa: BLE001
                pass
            self.transport = None

    async def stop(self) -> None:
        self.stop_socket()
        if self._fb_task is not None:
            self._fb_task.cancel()
            self._fb_task = None
        if self._fb_sock is not None:
            self._fb_sock.close()
            self._fb_sock = None

    # ---------------------------------------------------------------- Empfang
    def _allowed(self, host: str) -> bool:
        allow = self.config["allow"]
        return not allow or any(host == a or host.startswith(a) for a in allow)

    def datagram(self, data: bytes, addr: Tuple[str, int]) -> None:
        now = time.monotonic()
        if now - self._window_start >= 1.0:
            self._window_start, self._window_count = now, 0
        self._window_count += 1
        if self._window_count > RATE_LIMIT:                                           # Flut: verwerfen
            return
        host = addr[0]
        for address, args in parse_packet(data):
            if not self._allowed(host):
                self._note(host, address, args, "blocked (sender not allowed)")
                continue
            self._senders[host] = time.monotonic()
            self._handle(host, address, args)

    def _note(self, host: str, address: str, args: List[Any], result: str) -> None:
        self.seq += 1
        shown = [a if not isinstance(a, (bytes, bytearray)) else f"<{len(a)} bytes>" for a in args][:8]
        self.recent.append({"n": self.seq, "t": int(time.time() * 1000), "from": host, "address": address[:120], "args": shown, "result": result})

    @staticmethod
    def _value_of(args: List[Any]) -> Optional[float]:
        for a in args:
            if isinstance(a, bool):
                return 1.0 if a else 0.0
            if isinstance(a, (int, float)):
                return float(a)
        return None

    def _handle(self, host: str, address: str, args: List[Any]) -> None:
        value = self._value_of(args)
        commands: List[Tuple[str, str, bool, str, bool]] = []                         # (Schluessel, Befehl, in den Verlauf?, Anzeige, nur der neueste zaehlt?)
        low = address.lower()
        press = value is None or value > 0
        builtin = self.config["builtin"]
        prefix = builtin["prefix"].lower()
        name = low[len(prefix) + 1:] if builtin["enabled"] and low.startswith(prefix + "/") else ""
        base = name.split("/", 1)[0]
        if base and base not in builtin["off"]:
            if name in ("go", "back", "pause", "resume", "stop"):
                if press:
                    commands.append((low, name.capitalize(), True, "built-in", False))
            elif name == "blackout":
                commands.append((low, "Blackout" if value is None else ("Blackout On" if value > 0 else "Blackout Off"), True, "built-in", False))
            elif name in ("master", "fader") and value is not None:
                commands.append((low, ("Master " if name == "master" else "Fader ") + _fmt(max(0.0, min(1.0, value)) * 100), False, "built-in", True))
            elif base == "cue" and press:
                number = address[len(prefix) + len("/cue/"):]
                if re.fullmatch(r"\d+(\.\d+)?", number):
                    commands.append((low, f"Goto Cue {number}", True, "built-in", False))
            elif name == "cmd" and args and isinstance(args[0], str):
                if self.config["raw"]:
                    commands.append((low, " ".join(args[0].split())[:1000], True, "raw command", False))
                else:
                    self._note(host, address, args, "ignored (raw commands are off)")
                    return
        for binding, pattern in self._compiled:
            if not binding["enabled"] or not binding["command"] or not pattern.match(address):
                continue
            if binding["mode"] == "press" and not press:
                continue
            command = binding["command"]
            if "{value}" in command:
                if value is None:
                    continue
                shown = value if not binding["scale"] else binding["min"] + max(0.0, min(1.0, value)) * (binding["max"] - binding["min"])
                command = command.replace("{value}", _fmt(shown))
            commands.append((binding["id"], command, binding["log"], "mapping", "{value}" in binding["command"]))
        if not commands:
            self._note(host, address, args, "no mapping")
            return
        for key, command, log, kind, coalesce in commands:
            self._note(host, address, args, f"{kind}: {command}")
            self._pending[key if coalesce else f"{key}#{self.seq}"] = (command, log)          # Fader-Strom: nur der neueste Wert; Tasten: jeder Druck zaehlt
        if not self._draining and self._loop is not None:
            self._draining = True
            self._loop.call_soon(lambda: self._loop.create_task(self._drain()))

    async def _drain(self) -> None:
        try:
            while self._pending:
                batch, self._pending = self._pending, {}
                for command, log in batch.values():
                    if self.runner is not None:
                        try:
                            await self.runner(command, log)
                        except Exception:                                                # noqa: BLE001
                            logger.exception("[OSC] Command failed: %s", command)
        finally:
            self._draining = False

    # ---------------------------------------------------------------- Senden
    def send(self, address: str, args: List[Any]) -> str:
        """Nachricht an das Ziel aus den Einstellungen schicken. Gibt eine Meldung zurueck; wirft ValueError bei fehlendem Ziel / falscher Adresse."""
        if not _ADDRESS.match(address or ""):
            raise ValueError("The OSC address must start with / and contain no spaces (e.g. /opencue/go)")
        target = self.config["send"]
        if not target["host"]:
            raise ValueError("No OSC target set (Controls -> OSC -> Send to)")
        packet = build_message(address, args)
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            try:
                sock.sendto(packet, (target["host"], target["port"]))
            except OSError as exc:
                raise ValueError(f"OSC send failed: {exc}") from None
        return f"OSC {address} {' '.join(str(a) for a in args)} -> {target['host']}:{target['port']}".rstrip()

    # ---------------------------------------------------------------- Rueckkanal
    def _sync_feedback_task(self) -> None:
        wanted = self.config["feedback"]["enabled"] and self._loop is not None
        if wanted and (self._fb_task is None or self._fb_task.done()):
            self._fb_task = self._loop.create_task(self._feedback_loop())            # type: ignore[union-attr]
        elif not wanted and self._fb_task is not None:
            self._fb_task.cancel()
            self._fb_task = None

    def resend(self) -> None:
        """Beim naechsten Durchlauf allen Zielen den vollen Zustand schicken (Einschalten, neue Einstellungen, Knopf "Jetzt alles senden")."""
        self._fb_known.clear()

    def feedback_targets(self) -> List[Tuple[str, int]]:
        """Ziele des Rueckkanals: das Ziel aus den Einstellungen und - wenn gewuenscht - jeder Absender der letzten Stunde (an den Sende-Port)."""
        port = self.config["send"]["port"]
        hosts: List[str] = []
        if self.config["send"]["host"]:
            hosts.append(self.config["send"]["host"])
        if self.config["feedback"]["senders"]:
            now = time.monotonic()
            for host, seen in list(self._senders.items()):
                if now - seen > 3600:
                    del self._senders[host]
                elif host not in hosts:
                    hosts.append(host)
        return [(h, port) for h in hosts]

    @staticmethod
    def _number_text(number: float) -> str:
        return f"{number:g}"

    def snapshot(self) -> Dict[str, List[Any]]:
        """Der Zustand, den der Rueckkanal meldet: Adresse -> Werte (nur eingeschaltete Meldungen)."""
        from app.state_manager import state                                         # deferred: Zirkelimport
        from app.cue_engine import cue_engine
        fb = self.config["feedback"]
        prefix = self.config["builtin"]["prefix"]
        on = lambda name: name not in fb["off"]                                      # noqa: E731
        cl = state.cuelists.get(state.active_cuelist_id) if state.active_cuelist_id else None
        cue = None
        if cl is not None:
            cue_id = state.active_cue_ids.get(cl.id)
            cue = next((c for c in cl.cues if c.id == cue_id), None) if cue_id else None
        out: Dict[str, List[Any]] = {}
        if on("cuelist"):
            out[prefix + "/cuelist"] = [cl.name if cl is not None else ""]
        if on("cue"):
            out[prefix + "/cue"] = [float(cue.number) if cue is not None else -1.0]
        if on("cuename"):
            out[prefix + "/cuename"] = [cue.name if cue is not None else ""]
        if on("leds") and cue is not None:
            out[prefix + "/cue/" + self._number_text(cue.number)] = [1]
        if on("state"):
            payload = cue_engine._playback_payload(cl.id) if cl is not None else None       # noqa: SLF001
            out[prefix + "/state"] = [payload["state"] if payload else "idle"]
        if on("fader") and cl is not None:
            out[prefix + "/fader"] = [round(state.cuelist_master(cl.id) / 100.0, 3)]
        if on("master"):
            out[prefix + "/master"] = [round(state.grand_master / 100.0, 3)]
        if on("blackout"):
            out[prefix + "/blackout"] = [1 if state.blackout else 0]
        return out

    def _send_to(self, targets: List[Tuple[str, int]], address: str, args: List[Any]) -> None:
        if not targets:
            return
        if self._fb_sock is None:
            self._fb_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._fb_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            self._fb_sock.setblocking(False)
        packet = build_message(address, args)
        for target in targets:
            try:
                self._fb_sock.sendto(packet, target)
                self.fb_sent += 1
            except (OSError, ValueError):                                              # Ziel weg / Name nicht aufloesbar: still weiter, nie stoeren
                pass

    def feedback_step(self) -> None:
        """Ein Durchlauf: Aenderungen an alle Ziele; Ziele, die noch nichts haben, bekommen den vollen Zustand."""
        targets = self.feedback_targets()
        if not targets:
            self._fb_last = {}
            return
        current = self.snapshot()
        previous = self._fb_last
        fresh = [t for t in targets if t not in self._fb_known]
        if fresh:
            for address, args in current.items():
                self._send_to(fresh, address, args)
            self._fb_known.update(fresh)
        old = [t for t in targets if t not in fresh]
        for address, args in current.items():
            if previous.get(address) != args:
                self._send_to(old, address, args)
        for address in previous:                                                       # Taste/LED, die nicht mehr aktiv ist: "0" melden
            if address not in current and "/cue/" in address:
                self._send_to(old, address, [0])
        self._fb_last = current

    async def _feedback_loop(self) -> None:
        while True:
            try:
                self.feedback_step()
            except Exception:                                                          # noqa: BLE001 - der Rueckkanal darf nie stoeren
                logger.exception("[OSC] Feedback failed")
            await asyncio.sleep(FEEDBACK_INTERVAL)

    def status(self) -> Dict[str, Any]:
        from app.remote import lan_addresses
        return {"enabled": self.config["enabled"], "listening": self.transport is not None, "port": self.config["port"], "error": self.error,
                "addresses": lan_addresses() if self.transport is not None else [], "seq": self.seq,
                "feedback": {"active": self._fb_task is not None, "targets": [f"{h}:{p}" for h, p in self.feedback_targets()] if self._fb_task is not None else [], "sent": self.fb_sent}}


class _Protocol(asyncio.DatagramProtocol):
    def __init__(self, engine: OscEngine) -> None:
        self.engine = engine

    def datagram_received(self, data: bytes, addr) -> None:                          # noqa: ANN001
        try:
            self.engine.datagram(data, addr)
        except Exception:                                                            # noqa: BLE001 - eine schlechte Nachricht darf nie stoeren
            logger.exception("[OSC] Message failed")


osc = OscEngine()


# ---------------------------------------------------------------------------------------------------------------- HTTP
def _local(request: Request) -> bool:
    from app import remote
    return remote.is_local(request.client.host if request.client else None)


@router.get("/api/osc")
async def get_osc(since: int = 0) -> JSONResponse:
    return JSONResponse({"ok": True, "config": osc.config, "status": osc.status(), "recent": [m for m in osc.recent if m["n"] > since],
                         "builtin": [{"name": n, "address": osc.config["builtin"]["prefix"] + a, "command": c, "about": d} for n, a, c, d in BUILTIN]})


@router.post("/api/osc/config")
async def set_osc(request: Request) -> JSONResponse:
    from app.state_manager import state
    cfg = normalize(await request.json())
    state.osc_config = cfg
    state.save_app_config()
    await osc.configure(cfg)
    return JSONResponse({"ok": True, "config": osc.config, "status": osc.status()})


@router.post("/api/osc/feedback/resend")
async def resend_feedback(request: Request) -> JSONResponse:
    osc.resend()
    return JSONResponse({"ok": True})


@router.post("/api/osc/send")
async def send_osc(request: Request) -> JSONResponse:
    body = await request.json()
    args = [guess_value(a) if isinstance(a, str) else a for a in (body.get("args") or [])] if isinstance(body, dict) else []
    try:
        return JSONResponse({"ok": True, "message": osc.send(str((body or {}).get("address", "")), args)})
    except ValueError as exc:
        return JSONResponse({"ok": False, "error": "bad_request", "message": str(exc)}, status_code=400)
