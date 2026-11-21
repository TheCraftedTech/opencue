# Copyright (C) 2026 Samuel Zenker
# SPDX-License-Identifier: GPL-3.0-or-later
"""
dmx_output.py
Die DMX-Ausgabe als EIGENER PROZESS (Windows-Taskmanager: ein zweiter OpenCue-Prozess).

Warum: Die Ausgabe darf nie von der Oberflaeche, vom Server oder von einer Analyse abhaengen. Im selben Prozess teilt sich der Takt den Interpreter (GIL) mit allem anderen - schon ein
einzelner schwerer Schritt (ein Geraet verbindet sich, ein Cue wird gespeichert, ein Effekt startet) hielt den Takt bis zu 250 ms an. Ein eigener Prozess hat seinen eigenen Interpreter:
er sendet weiter, auch wenn der Server haengt oder gerade etwas Schweres rechnet.

Aufbau:
  Hauptprogramm (DMXEngine)  --  Gemeinsamer Speicher  -->  Ausgabe-Prozess  -->  Art-Net / sACN / USB (Enttec)
                                  <-- Ueberlagerung (Effekte) --
    * rechnet wie bisher alle Kanalwerte und schreibt die fertigen Universen (512 Byte) in den gemeinsamen Speicher (je Universum ein Platz, mit Zaehler gegen halb geschriebene Bilder),
    * schickt Einstellungen (Ziel, Schnittstelle, Protokolle, USB-Port) als JSON-Zeilen an den Prozess (stdin) und liest Antworten / Zustand zurueck (stdout),
    * startet den Prozess neu, falls er stirbt, und faellt auf die Ausgabe im eigenen Prozess zurueck, wenn er gar nicht startet.
  Ausgabe-Prozess (`OpenCue.exe --dmx-output ...`, siehe main.py / child_main)
    * ein Takt (40 Hz, driftfreier Zeitplan, 1-ms-Zeitgeber, hoehere Prioritaet) liest alle Universen und sendet sie,
    * USB-Schreiben in einem eigenen Thread (ein langsamer Adapter haelt den Art-Net-Takt nicht auf),
    * EFFEKTE laufen ebenfalls hier (app/fx_runner.py, eigener Thread): der Server schickt nur die Konfiguration (Zuweisungen, Skripte, Geraete), der Rechenkern liefert die Kanalwerte als
      "Ueberlagerung" - sie liegen in der Ausgabe ueber dem Bild des Servers und stehen im gemeinsamen Speicher zum Spiegeln zurueck. Haengt der Server, laufen die Effekte weiter,
    * endet, sobald das Hauptprogramm weg ist (kein verwaister Sender, der mit einer neuen Instanz kollidiert) - beim ABSTURZ des Hauptprogramms haelt das Netz das letzte Bild kurz,
      danach entscheidet das Geraet; solange das Hauptprogramm nur HAENGT, laeuft die Ausgabe unveraendert weiter.
"""

from __future__ import annotations

import json
import os
import socket
import struct
import subprocess
import sys
import threading
import time
from collections import deque
from typing import Any, Callable, Dict, List, Optional, Tuple

OUTPUT_FPS = 40
DMX_UNIVERSE_SIZE = 512
SLOTS = 128                         # so viele Universen koennen gleichzeitig ausgegeben werden (Programm: 1-64)
SLOT_SIZE = 528                     # 4 Byte Universum, 4 Byte Reserve, 8 Byte Zaehler, 512 Byte Daten
HEADER_SIZE = 64
OV_SLOT_SIZE = 16 + DMX_UNIVERSE_SIZE * 2                       # 4 Byte Universum, 4 Byte Reserve, 8 Byte Zaehler, 512 Byte Werte, 512 Byte Maske (1 = der Effekt-Rechenkern besitzt den Kanal)
OV_BASE = HEADER_SIZE + SLOTS * SLOT_SIZE
SHM_SIZE = OV_BASE + SLOTS * OV_SLOT_SIZE
APPLIED_OFFSET = 16                                              # Kopf: Nummer der Effekt-Konfiguration, die der Rechenkern zuletzt uebernommen hat
MAGIC = b"OCDMX002"
ARTNET_PORT = 6454
BLACKOUT = bytes(DMX_UNIVERSE_SIZE)
FLAG_ARG = "--dmx-output"

# ---- Enttec DMX USB Pro (Label 6: DMX senden) ---------------------------------------------------------------------------
_ENTTEC_START, _ENTTEC_END, _ENTTEC_LABEL_SEND = 0x7E, 0xE7, 6
FTDI_VENDOR_ID = 0x0403


def enttec_frame(data: bytes) -> bytes:
    body = bytes([0]) + data[:DMX_UNIVERSE_SIZE]
    n = len(body)
    return bytes([_ENTTEC_START, _ENTTEC_LABEL_SEND, n & 0xFF, (n >> 8) & 0xFF]) + body + bytes([_ENTTEC_END])


# ---- Gemeinsamer Speicher ---------------------------------------------------------------------------------------------------
class Frames:
    """Die Universen im gemeinsamen Speicher. Der Schreiber (Hauptprogramm) setzt den Zaehler eines Platzes auf ungerade, schreibt, setzt ihn auf gerade; der Leser (Ausgabe-Prozess) kopiert
    nur, wenn der Zaehler davor und danach gleich und gerade ist - so sieht die Ausgabe nie ein halb geschriebenes Bild (z. B. Pan grob neu, fein alt)."""

    def __init__(self, buf: memoryview) -> None:
        self.buf = buf

    def init(self) -> None:
        self.buf[0:8] = MAGIC
        struct.pack_into("<I", self.buf, 8, SLOTS)
        for slot in range(SLOTS):
            struct.pack_into("<iiQ", self.buf, HEADER_SIZE + slot * SLOT_SIZE, -1, 0, 0)

    # --- Schreiber
    def slot_for(self, universe: int, table: Dict[int, int]) -> Optional[int]:
        slot = table.get(universe)
        if slot is None:
            used = set(table.values())
            slot = next((s for s in range(SLOTS) if s not in used), None)
            if slot is None:
                return None
            table[universe] = slot
            struct.pack_into("<i", self.buf, HEADER_SIZE + slot * SLOT_SIZE, int(universe))
        return slot

    def publish(self, slot: int, payload: bytes) -> None:
        base = HEADER_SIZE + slot * SLOT_SIZE
        (seq,) = struct.unpack_from("<Q", self.buf, base + 8)
        struct.pack_into("<Q", self.buf, base + 8, seq + 1)                      # ungerade: wird geschrieben
        self.buf[base + 16: base + 16 + DMX_UNIVERSE_SIZE] = payload[:DMX_UNIVERSE_SIZE].ljust(DMX_UNIVERSE_SIZE, b"\0")
        struct.pack_into("<Q", self.buf, base + 8, seq + 2)                      # gerade: fertig

    # --- Leser
    def read_all(self) -> List[Tuple[int, bytes]]:
        out: List[Tuple[int, bytes]] = []
        for slot in range(SLOTS):
            base = HEADER_SIZE + slot * SLOT_SIZE
            (universe,) = struct.unpack_from("<i", self.buf, base)
            if universe < 0:
                continue
            for _ in range(4):
                (s1,) = struct.unpack_from("<Q", self.buf, base + 8)
                if s1 & 1:
                    time.sleep(0)
                    continue
                data = bytes(self.buf[base + 16: base + 16 + DMX_UNIVERSE_SIZE])
                (s2,) = struct.unpack_from("<Q", self.buf, base + 8)
                if s1 == s2:
                    out.append((universe, data))
                    break
            else:                                                                   # vier Versuche ohne ruhigen Zaehler (der Schreiber steht mitten im Schreiben): lieber ein Bild mit Kanten als gar keins
                out.append((universe, bytes(self.buf[base + 16: base + 16 + DMX_UNIVERSE_SIZE])))
        return out


class Overlay:
    """Die Effekt-Ueberlagerung im gemeinsamen Speicher (Schreiber: Ausgabe-Prozess, Leser: Hauptprogramm). Je Universum: Werte (512 Byte) und Maske (512 Byte, 1 = Kanal gehoert einem Effekt),
    mit demselben Zaehler-Verfahren wie Frames. Der Kopf traegt die Nummer der zuletzt uebernommenen Effekt-Konfiguration: nur wenn sie zur aktuellen passt, ist die Ueberlagerung aktuell."""

    def __init__(self, buf: memoryview) -> None:
        self.buf = buf

    def init(self) -> None:
        struct.pack_into("<Q", self.buf, APPLIED_OFFSET, 0)
        for slot in range(SLOTS):
            struct.pack_into("<iiQ", self.buf, OV_BASE + slot * OV_SLOT_SIZE, -1, 0, 0)

    # --- Schreiber (Ausgabe-Prozess)
    def set_applied(self, cfg_id: int) -> None:
        struct.pack_into("<Q", self.buf, APPLIED_OFFSET, int(cfg_id))

    def slot_for(self, universe: int, table: Dict[int, int]) -> Optional[int]:
        slot = table.get(universe)
        if slot is None:
            used = set(table.values())
            slot = next((s for s in range(SLOTS) if s not in used), None)
            if slot is None:
                return None
            table[universe] = slot
            struct.pack_into("<i", self.buf, OV_BASE + slot * OV_SLOT_SIZE, int(universe))
        return slot

    def publish(self, slot: int, values: bytes, mask: bytes) -> None:
        base = OV_BASE + slot * OV_SLOT_SIZE
        (seq,) = struct.unpack_from("<Q", self.buf, base + 8)
        struct.pack_into("<Q", self.buf, base + 8, seq + 1)
        self.buf[base + 16: base + 16 + DMX_UNIVERSE_SIZE] = values
        self.buf[base + 16 + DMX_UNIVERSE_SIZE: base + 16 + 2 * DMX_UNIVERSE_SIZE] = mask
        struct.pack_into("<Q", self.buf, base + 8, seq + 2)

    # --- Leser (Hauptprogramm)
    def applied(self) -> int:
        return struct.unpack_from("<Q", self.buf, APPLIED_OFFSET)[0]

    def read_all(self) -> Dict[int, Tuple[bytes, bytes]]:
        out: Dict[int, Tuple[bytes, bytes]] = {}
        for slot in range(SLOTS):
            base = OV_BASE + slot * OV_SLOT_SIZE
            (universe,) = struct.unpack_from("<i", self.buf, base)
            if universe < 0:
                continue
            for _ in range(4):
                (s1,) = struct.unpack_from("<Q", self.buf, base + 8)
                if s1 & 1:
                    time.sleep(0)
                    continue
                values = bytes(self.buf[base + 16: base + 16 + DMX_UNIVERSE_SIZE])
                mask = bytes(self.buf[base + 16 + DMX_UNIVERSE_SIZE: base + 16 + 2 * DMX_UNIVERSE_SIZE])
                (s2,) = struct.unpack_from("<Q", self.buf, base + 8)
                if s1 == s2:
                    out[universe] = (values, mask)
                    break
        return out


# ===============================================================================================================================
# Ausgabe-Prozess (Kindseite)
# ===============================================================================================================================
class _Child:
    def __init__(self, shm_name: str, parent_pid: int) -> None:
        from multiprocessing import shared_memory
        self.shm = shared_memory.SharedMemory(name=shm_name)
        self.frames = Frames(self.shm.buf)
        self.ov = Overlay(self.shm.buf)
        self.parent_pid = parent_pid
        self.lock = threading.Lock()
        self.out_lock = threading.Lock()
        # Ausgang zum Hauptprogramm: ein eigener Thread schreibt, damit ein Hauptprogramm, das nicht liest (haengt), den Takt nie aufhaelt (volle Pipe blockiert nur diesen Thread)
        self.outq: deque = deque(maxlen=500)
        self.live_box: Optional[list] = None
        self.out_cond = threading.Condition()
        # Effekte (Rechenkern app/fx_runner.py, eigener Thread)
        self.fx_lock = threading.Lock()
        self.fx_pending: Optional[Tuple[int, Dict[str, Any]]] = None
        self.fx_master = 100.0
        self.fx_audio: Optional[Dict[str, float]] = None
        self.fade_pending: Optional[Tuple[List[Dict[str, Any]], float, Dict[str, Any]]] = None
        self.levels_pending: Optional[Dict[str, float]] = None
        self.fade_overlay_now: Dict[int, Dict[int, int]] = {}                  # Ueberlagerung durch laufende Cue-Ueberblendungen (liegt ueber den Effekten)
        self.overlay_now: Dict[int, Dict[int, int]] = {}                       # Universum -> {Kanal (1-512): Wert}; wird als Ganzes ausgetauscht (der Takt liest ohne Sperre)
        self.fx_stats = {"ticks": 0, "max_ms": 0.0, "assign": 0}
        self.stop = threading.Event()
        # Einstellungen (vom Hauptprogramm)
        self.artnet = {"enabled": True, "target": "255.255.255.255", "extras": [], "bind": ""}
        self.sacn_enabled = False
        self.enttec = {"enabled": False, "port": "", "universe": 1}
        # Zustand
        self.sock: Optional[socket.socket] = None
        self.sock_bind = None
        self.seq: Dict[int, int] = {}
        self.artnet_quiet_until = 0.0
        self.sacn_sender: Any = None
        self.sacn_active: set = set()
        self.enttec_serial: Any = None
        self.enttec_active_port = ""
        self.enttec_error = ""
        self.enttec_box: Optional[bytes] = None
        self.enttec_cond = threading.Condition()
        self.stats = {"ticks": 0, "late_ticks": 0, "max_late_ms": 0.0, "sent": 0}
        # DMX-Eingang (app/dmx_in.py): Empfang + Mischen laufen hier, damit die Weiterleitung auch bei haengendem Server weiterlaeuft
        from app.dmx_in import InputHub
        self.own_cid = __import__("uuid").uuid4().bytes                         # Quellkennung der eigenen sACN-Ausgabe: eigene Pakete werden im Eingang ignoriert
        self.dmxin = InputHub(lambda m: self.say(event="dmxin", **m), self.log)
        self.dmxin.own_cid = self.own_cid

    # ---- Ausgabe nach aussen
    def say(self, **message: Any) -> None:
        try:
            line = json.dumps(message) + "\n"
        except Exception:
            return
        with self.out_cond:
            self.outq.append(line)
            self.out_cond.notify()

    def say_live(self, live: list) -> None:
        with self.out_cond:
            self.live_box = live                                               # nur der neueste Stand zaehlt
            self.out_cond.notify()

    def _writer_loop(self) -> None:
        while not self.stop.is_set():
            with self.out_cond:
                if not self.outq and self.live_box is None:
                    self.out_cond.wait(0.5)
                lines = list(self.outq)
                self.outq.clear()
                live, self.live_box = self.live_box, None
            try:
                for line in lines:
                    sys.stdout.write(line)
                if live is not None:
                    sys.stdout.write(json.dumps({"fxlive": live}) + "\n")
                if lines or live is not None:
                    sys.stdout.flush()
            except Exception:
                pass                                                           # Hauptprogramm weg oder haengt: der Takt laeuft trotzdem weiter

    def log(self, level: str, text: str) -> None:
        self.say(log=level, msg=text)

    # ---- Art-Net
    def _socket(self) -> socket.socket:
        bind = self.artnet.get("bind") or ""
        if self.sock is None or self.sock_bind != bind:
            if self.sock is not None:
                try:
                    self.sock.close()
                except Exception:
                    pass
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            if bind:
                try:
                    s.bind((bind, 0))
                except OSError as exc:
                    self.log("warning", f"Art-Net bind {bind}: {exc}")
            self.sock, self.sock_bind = s, bind
        return self.sock

    def _send_artnet(self, universe: int, data: bytes) -> None:
        seq = self.seq.get(universe, 0) % 255 + 1                              # 1-255 (0 hiesse "keine Reihenfolge")
        self.seq[universe] = seq
        packet = b"Art-Net\x00\x00\x50\x00\x0e" + bytes([seq, 0, universe & 0xFF, (universe >> 8) & 0xFF, 0x02, 0x00]) + data
        sock = self._socket()
        targets = [self.artnet["target"]] + list(self.artnet.get("extras") or [])
        for ip in targets:
            try:
                sock.sendto(packet, (ip, ARTNET_PORT))
                self.stats["sent"] += 1
            except OSError as exc:
                if self.stats["ticks"] % (OUTPUT_FPS * 10) == 0:
                    self.log("debug", f"Art-Net send {ip}: {exc}")

    # ---- sACN
    def _ensure_sacn(self, universes: List[int]) -> None:
        import sacn
        if self.sacn_sender is None:
            self.sacn_sender = sacn.sACNsender(fps=OUTPUT_FPS, cid=tuple(self.own_cid))
            self.sacn_sender.start()
            self.sacn_active = set()
        for u in universes:
            if u not in self.sacn_active:
                self.sacn_sender.activate_output(u)
                self.sacn_sender[u].multicast = True
                self.sacn_active.add(u)

    # ---- Enttec (eigener Thread: ein langsamer Adapter darf den Takt nie aufhalten)
    def _detect_usb(self) -> List[str]:
        try:
            import serial.tools.list_ports as lp
        except Exception:
            return []
        found = []
        try:
            for p in lp.comports():
                text = " ".join(str(x or "") for x in (p.description, p.manufacturer, p.product)).lower()
                if p.vid == FTDI_VENDOR_ID or "dmx" in text or "enttec" in text:
                    found.append(str(p.device))
        except Exception:
            return []
        return sorted(found)

    def _open_enttec(self) -> bool:
        self._close_enttec()
        try:
            import serial
        except Exception:
            self.enttec_error = "pyserial is not installed (pip install pyserial)"
            return False
        port = self.enttec["port"]
        if not port:
            found = self._detect_usb()
            self.enttec_active_port = found[0] if found else ""
            if not self.enttec_active_port:
                self.enttec_error = "No USB DMX interface found - plug it in, it connects by itself"
                return False
            port = self.enttec_active_port
        try:
            self.enttec_serial = serial.Serial(port=port, baudrate=250000, bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_TWO, timeout=0.1)
            self.enttec_error = ""
            return True
        except Exception as exc:
            self.enttec_serial = None
            self.enttec_error = _clean_serial_error(exc)
            return False

    def _close_enttec(self) -> None:
        ser, self.enttec_serial = self.enttec_serial, None
        if ser is not None:
            try:
                ser.close()
            except Exception:
                pass

    def _enttec_loop(self) -> None:
        while not self.stop.is_set():
            with self.enttec_cond:
                if self.enttec_box is None:
                    self.enttec_cond.wait(0.5)
                data, self.enttec_box = self.enttec_box, None
            ser = self.enttec_serial
            if data is None or ser is None:
                continue
            try:
                ser.write(enttec_frame(data))
                self.enttec_error = ""
            except Exception as exc:
                self.enttec_error = _clean_serial_error(exc)
                self.log("warning", f"USB DMX send error on {self.enttec_active_port or self.enttec['port']}: {self.enttec_error}")
                with self.lock:
                    self._close_enttec()
                self.say(event="enttec", state="disconnected")

    def enttec_health(self) -> Optional[str]:
        """Wie DMXEngine.check_enttec_health: Hotplug erkennen und selbst wieder verbinden. 'connected' | 'disconnected' | None."""
        with self.lock:
            if not self.enttec["enabled"]:
                return None
            try:
                import serial.tools.list_ports as lp
                available = {p.device for p in lp.comports()}
            except Exception:
                return None
            was = self.enttec_serial is not None
            if not self.enttec["port"]:
                if was and self.enttec_active_port not in available:
                    self._close_enttec()
                    self.enttec_active_port = ""
                    self.enttec_error = "USB DMX interface unplugged - plug it in again, it connects by itself"
                    return "disconnected"
                if not was and self._detect_usb():
                    if self._open_enttec():
                        return "connected"
                return None
            port_ok = self.enttec["port"] in available
            if was and not port_ok:
                self._close_enttec()
                self.enttec_error = f"Port {self.enttec['port']} is no longer available"
                return "disconnected"
            if not was and port_ok:
                return "connected" if self._open_enttec() else None
        return None

    def enttec_status(self) -> Dict[str, Any]:
        return {"connected": self.enttec_serial is not None, "port": self.enttec["port"] or self.enttec_active_port, "error": self.enttec_error}

    # ---- Befehle vom Hauptprogramm
    def handle(self, message: Dict[str, Any]) -> None:
        cmd = message.get("cmd")
        reply: Dict[str, Any] = {}
        if cmd == "config":
            with self.lock:
                art = message.get("artnet") or {}
                was_enabled = self.artnet["enabled"]
                self.artnet.update({k: art[k] for k in ("enabled", "target", "extras", "bind") if k in art})
                if was_enabled and not self.artnet["enabled"]:
                    self.artnet_quiet_until = time.monotonic() + 1.0              # eine Sekunde lang Nullen senden (sauber verstummen), danach Stille
                sacn_on = bool(message.get("sacn", self.sacn_enabled))
                if self.sacn_sender is not None and self.sacn_enabled and not sacn_on:
                    for u in self.sacn_active:
                        self.sacn_sender[u].dmx_data = tuple(BLACKOUT)
                self.sacn_enabled = sacn_on
                ent = message.get("enttec") or {}
                changed = False
                if ent:
                    changed = (ent.get("enabled") != self.enttec["enabled"]) or (ent.get("port") != self.enttec["port"])
                    self.enttec.update({k: ent[k] for k in ("enabled", "port", "universe") if k in ent})
                    if changed:
                        self.enttec_active_port = ""
                        if self.enttec["enabled"]:
                            self._open_enttec()
                        else:
                            self._close_enttec()
                            self.enttec_error = ""
            reply = {"enttec": self.enttec_status()}
        elif cmd == "reinit":
            with self.lock:
                if self.sock is not None:
                    try:
                        self.sock.close()
                    except Exception:
                        pass
                    self.sock = None
                ok = True
                if self.enttec["enabled"]:
                    ok = self._open_enttec()
            reply = {"enttec_ok": ok, "enttec": self.enttec_status()}
        elif cmd == "enttec_reconnect":
            with self.lock:
                ok = self._open_enttec() if self.enttec["enabled"] else False
            reply = {"ok": ok, "enttec": self.enttec_status()}
        elif cmd == "enttec_health":
            reply = {"event": self.enttec_health(), "enttec": self.enttec_status()}
        elif cmd == "fx":
            with self.fx_lock:
                self.fx_pending = (int(message.get("cfg_id", 0)), message.get("cfg") or {})
        elif cmd == "fades":
            with self.fx_lock:
                self.fade_pending = (message.get("jobs") or [], time.monotonic(), message.get("types") or {})
        elif cmd == "fadelvl":
            with self.fx_lock:
                self.levels_pending = message.get("l") or {}
        elif cmd == "dmxin":
            self.dmxin.configure(message.get("cfg") or {})
        elif cmd == "dmxin_watch":
            self.dmxin.watch(bool(message.get("on", True)))
        elif cmd == "dmxin_learn":
            self.dmxin.learn(bool(message.get("on", True)))
        elif cmd == "fxgm":
            self.fx_master = float(message.get("gm", 100.0))
        elif cmd == "fxaudio":
            self.fx_audio = message.get("a")
        elif cmd == "status":
            reply = {"enttec": self.enttec_status(), "stats": dict(self.stats), "fx": dict(self.fx_stats)}
        elif cmd == "quit":
            self.stop.set()
        if "id" in message:
            self.say(reply_to=message["id"], **reply)

    def stdin_loop(self) -> None:
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                self.handle(json.loads(line))
            except Exception as exc:
                self.log("error", f"command failed: {exc}")
        self.stop.set()                                                        # stdin zu = Hauptprogramm weg

    # ---- Effekte
    def _publish_overlay(self, overlay: Dict[int, Dict[int, int]], table: Dict[int, int], previous: Dict[int, bytes]) -> None:
        for universe in set(overlay) | set(table):
            channels = overlay.get(universe) or {}
            values = bytearray(DMX_UNIVERSE_SIZE)
            mask = bytearray(DMX_UNIVERSE_SIZE)
            for channel, value in channels.items():
                if 1 <= channel <= DMX_UNIVERSE_SIZE:
                    values[channel - 1] = value
                    mask[channel - 1] = 1
            key = bytes(values) + bytes(mask)
            if previous.get(universe) == key:
                continue
            slot = self.ov.slot_for(universe, table)
            if slot is None:
                continue
            self.ov.publish(slot, bytes(values), bytes(mask))
            previous[universe] = key

    def _fx_loop(self) -> None:
        """Der Rechenkern fuer Effekte und Cue-Ueberblendungen in einem eigenen Thread: 40 Hz, uebernimmt neue Konfigurationen, rechnet und legt das Ergebnis als Ueberlagerung ueber das Bild des
        Servers (Effekte: zusaetzlich im gemeinsamen Speicher zum Spiegeln)."""
        try:
            from app.fx_runner import FXRunner
            from app.cue_fade import FadePlayer
        except Exception as exc:
            self.log("error", f"effects unavailable in the output process: {exc}")
            self.say(event="fx_failed")                                         # das Hauptprogramm rechnet die Effekte dann selbst
            return
        self.say(event="fx_ready")
        runner: Optional[FXRunner] = None
        player = FadePlayer()
        table: Dict[int, int] = {}
        previous: Dict[int, bytes] = {}
        period = 1.0 / OUTPUT_FPS
        next_t = time.perf_counter()
        last_live = 0.0
        while not self.stop.is_set():
            next_t += period
            wait = next_t - time.perf_counter()
            if wait < -3 * period:
                next_t = time.perf_counter()
            elif wait > 0:
                time.sleep(wait)
            with self.fx_lock:
                pending, self.fx_pending = self.fx_pending, None
                fades, self.fade_pending = self.fade_pending, None
                levels, self.levels_pending = self.levels_pending, None
            if levels is not None:
                player.set_levels(levels)
            if fades is not None:
                try:
                    jobs, t_recv, types = fades
                    for job in jobs:
                        job["types"] = types
                    player.set_jobs(jobs, t_recv)
                except Exception as exc:
                    self.log("error", f"fade configuration failed: {exc}")
            cfg_id = None
            if pending is not None:
                cfg_id, cfg = pending
                try:
                    if runner is None:
                        runner = FXRunner()
                    runner.apply_config(cfg)
                except Exception as exc:
                    self.log("error", f"effect configuration failed: {exc}")
            started = time.perf_counter()
            try:
                if player.jobs:
                    self.fade_overlay_now = player.tick(time.monotonic(), self.fx_master)
                elif self.fade_overlay_now:
                    self.fade_overlay_now = {}
            except Exception as exc:
                self.log("error", f"fade tick failed: {exc}")
            if runner is None:
                continue
            try:
                runner.master = self.fx_master
                _batches, live = runner.tick(time.monotonic(), self.fx_audio if runner.uses_audio() else None) if runner.assign else ({}, {})
                overlay = runner.overlay()
            except Exception as exc:
                self.log("error", f"effect tick failed: {exc}")
                continue
            self.overlay_now = overlay
            self._publish_overlay(overlay, table, previous)
            if cfg_id is not None:
                self.ov.set_applied(cfg_id)                                     # erst NACH dem Veroeffentlichen: das Hauptprogramm spiegelt nur eine zur Konfiguration passende Ueberlagerung
            spent = (time.perf_counter() - started) * 1000.0
            self.fx_stats["ticks"] += 1
            self.fx_stats["assign"] = len(runner.assign)
            self.fx_stats["fades"] = len(player.jobs)
            if spent > self.fx_stats["max_ms"]:
                self.fx_stats["max_ms"] = spent
            now = time.monotonic()
            if live and now - last_live >= 0.05:                                # Vorschau fuer die Oberflaeche: 20 Hz genuegen
                last_live = now
                self.say_live([[fid, cat, abstract] for (fid, cat), abstract in live.items()])

    def watch_parent(self) -> None:
        if sys.platform != "win32":
            while not self.stop.is_set():
                if os.getppid() != self.parent_pid:
                    break
                time.sleep(1.0)
            self.stop.set()
            return
        import ctypes
        kernel = ctypes.windll.kernel32
        SYNCHRONIZE = 0x00100000
        handle = kernel.OpenProcess(SYNCHRONIZE, False, self.parent_pid)
        while not self.stop.is_set():
            if not handle or kernel.WaitForSingleObject(handle, 0) == 0:       # 0 = Prozess beendet
                break
            time.sleep(0.5)
        self.stop.set()

    # ---- Takt
    def run(self) -> None:
        _prepare_process()
        for target in (self.stdin_loop, self.watch_parent, self._enttec_loop, self._writer_loop, self._fx_loop):
            threading.Thread(target=target, daemon=True).start()
        self.say(event="ready", pid=os.getpid())
        period = 1.0 / OUTPUT_FPS
        perf = time.perf_counter
        next_t = perf()
        last_status = time.monotonic()
        while not self.stop.is_set():
            next_t += period
            now = perf()
            if now - next_t > 3 * period:
                next_t = now
            else:
                wait = next_t - now
                if wait > 0.0025:
                    time.sleep(wait - 0.0015)
                while perf() < next_t:
                    time.sleep(0)
            late = (perf() - next_t) * 1000.0
            self.stats["ticks"] += 1
            if late > period * 500:
                self.stats["late_ticks"] += 1
            if late > self.stats["max_late_ms"]:
                self.stats["max_late_ms"] = late
            try:
                frames = self.frames.read_all()
                overlay, fades = self.overlay_now, self.fade_overlay_now
                if overlay or fades:
                    patched = []
                    for universe, data in frames:
                        merged = None
                        for layer in (overlay, fades):                          # Effekte zuerst, darueber die Cue-Ueberblendung (ein ausdruecklicher Befehl)
                            owned = layer.get(universe)
                            if owned:
                                if merged is None:
                                    merged = bytearray(data)
                                for channel, value in owned.items():
                                    if 1 <= channel <= DMX_UNIVERSE_SIZE:
                                        merged[channel - 1] = value
                        patched.append((universe, bytes(merged) if merged is not None else data))
                    frames = patched
                if self.dmxin.active:                                                   # DMX-Eingang: Weiterleiten / Mischen (zuletzt: der Eingang liegt ueber allem)
                    if self.sock is not None and not self.dmxin.own_ports:
                        try:
                            self.dmxin.own_ports = {self.sock.getsockname()[1]}      # die Absende-Portnummer unserer Art-Net-Ausgabe (eigene Pakete ignorieren)
                        except OSError:
                            pass
                    frames = [(u, self.dmxin.merge(u, d)) for u, d in frames]
                mono = time.monotonic()
                with self.lock:
                    art_on = self.artnet["enabled"] or mono < self.artnet_quiet_until
                    sacn_on = self.sacn_enabled
                    ent_on = self.enttec["enabled"] and self.enttec_serial is not None
                    ent_universe = self.enttec["universe"]
                if sacn_on:
                    self._ensure_sacn([u for u, _ in frames])
                muted = not self.artnet["enabled"] and mono < self.artnet_quiet_until
                for universe, data in frames:
                    if art_on:
                        self._send_artnet(universe, BLACKOUT if muted else data)
                    if sacn_on:
                        self.sacn_sender[universe].dmx_data = tuple(data)
                    if ent_on and universe == ent_universe:
                        with self.enttec_cond:
                            self.enttec_box = data
                            self.enttec_cond.notify()
                if mono - last_status >= 1.0:
                    last_status = mono
                    self.say(status=dict(self.stats), enttec=self.enttec_status(), fx=dict(self.fx_stats))
                    self.stats["late_ticks"] = 0
                    self.stats["max_late_ms"] = 0.0
            except Exception as exc:
                self.log("error", f"OC-3104 output tick error: {exc}")
        # Ende
        with self.lock:
            self._close_enttec()
            if self.sacn_sender is not None:
                try:
                    self.sacn_sender.stop()
                except Exception:
                    pass
        try:
            self.shm.close()
        except Exception:
            pass


def _clean_serial_error(exc: Exception) -> str:
    import re
    msg = str(exc)
    msg = re.sub(r"\[Errno\s+\d+\]\s*", "", msg)
    msg = re.sub(r"\[Error\s+\d+\]\s*", "", msg, flags=re.IGNORECASE)
    msg = re.sub(r"\[Win[Ee]rror[^\]]*\]\s*", "", msg)
    msg = re.sub(r":\s*\w+(?:Error|Exception)\s*\(.*", "", msg)
    return msg.strip(" :;,") or str(exc)


def _prepare_process() -> None:
    """Zeitgeber 1 ms und hoehere Prioritaet fuer diesen Prozess (der Takt soll nie hinter anderen Programmen warten)."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        ctypes.windll.winmm.timeBeginPeriod(1)
        sys.setswitchinterval(0.001)                                                # Der Takt bekommt den Interpreter auch dann rasch, wenn der Effekt-Thread rechnet
        kernel = ctypes.windll.kernel32
        kernel.SetPriorityClass(kernel.GetCurrentProcess(), 0x00008000)           # ABOVE_NORMAL
        kernel.SetThreadPriority(kernel.GetCurrentThread(), 2)                    # HIGHEST (relativ im Prozess)
    except Exception:
        pass


def child_main(argv: List[str]) -> int:
    """Einstieg des Ausgabe-Prozesses: main.py --dmx-output <Speichername> <PID des Hauptprogramms>."""
    shm_name, parent_pid = argv[0], int(argv[1])
    child = _Child(shm_name, parent_pid)
    child.run()
    return 0


# ===============================================================================================================================
# Hauptprogramm-Seite
# ===============================================================================================================================
class OutputProcess:
    """Startet und betreut den Ausgabe-Prozess. Alle Methoden sind aus jedem Thread aufrufbar."""

    def __init__(self, on_log: Optional[Callable[[str, str], None]] = None, on_event: Optional[Callable[[Dict[str, Any]], None]] = None) -> None:
        self.on_log = on_log or (lambda level, text: None)
        self.on_event = on_event or (lambda event: None)
        self.shm = None
        self.frames: Optional[Frames] = None
        self.ov: Optional[Overlay] = None
        self.slots: Dict[int, int] = {}
        self.fx_last_time = 0.0
        self.fx_ok: Optional[bool] = None                                       # Rechenkern der Effekte im Prozess: None = noch unbekannt, True = bereit, False = nicht verfuegbar
        self.fx_last: Optional[Dict[str, Any]] = None                            # zuletzt geschickte Effekt-Konfiguration (geht nach einem Neustart des Prozesses erneut raus)
        self.fades_last: Optional[Tuple[Dict[str, Any], float]] = None           # zuletzt geschickte Cue-Ueberblendungen (mit Zeitpunkt) und Pegel
        self.levels_last: Optional[Dict[str, Any]] = None
        self.dmxin_last: Optional[Dict[str, Any]] = None                         # zuletzt geschickte Einstellungen des DMX-Eingangs
        self.fx_live: List[Any] = []
        self.fx_live_seq = 0
        self.proc: Optional[subprocess.Popen] = None
        self.config: Dict[str, Any] = {}
        self.status: Dict[str, Any] = {"enttec": {"connected": False, "port": "", "error": ""}, "stats": {}}
        self.ready = threading.Event()
        self._stopping = False
        self._write_lock = threading.Lock()
        # Nachrichten an den Prozess gehen ueber einen eigenen Schreiber-Thread: ein Kind, das nicht liest (haengt, Debugger), fuellt die Pipe - das blockiert nur diesen Thread, nie den Server
        self._sendq: deque = deque(maxlen=4000)
        self._send_cond = threading.Condition()
        self._next_id = 0
        self._waiters: Dict[int, Tuple[threading.Event, Dict[str, Any]]] = {}
        self._restarts: List[float] = []

    # ---- Start / Ende
    def start(self, config: Dict[str, Any], timeout: float = 6.0) -> bool:
        from multiprocessing import shared_memory
        try:
            self.shm = shared_memory.SharedMemory(create=True, size=SHM_SIZE)
        except Exception as exc:
            self.on_log("error", f"shared memory not available: {exc}")
            return False
        self.frames = Frames(self.shm.buf)
        self.frames.init()
        self.ov = Overlay(self.shm.buf)
        self.ov.init()
        self.config = config
        if not self._spawn():
            return False
        if not self.ready.wait(timeout):
            self.on_log("error", "output process does not respond")
            self.stop()
            return False
        threading.Thread(target=self._monitor, daemon=True, name="opencue-dmx-output-watch").start()
        threading.Thread(target=self._writer_loop, daemon=True, name="opencue-dmx-output-send").start()
        self.send({"cmd": "config", **self.config})
        return True

    def _command(self) -> List[str]:
        if getattr(sys, "frozen", False):
            return [sys.executable, FLAG_ARG]
        return [sys.executable, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "main.py"), FLAG_ARG]

    def _spawn(self) -> bool:
        self.ready.clear()
        self.fx_ok = None
        with self._send_cond:
            self._sendq.clear()                                                  # was an den toten Prozess ging, ist hinfaellig (Konfiguration geht nach dem Start erneut raus)
        if self.ov is not None:
            self.ov.init()                                                       # der alte Prozess ist tot: seine Ueberlagerung und Quittung gelten nicht mehr
        command = self._command() + [self.shm.name, str(os.getpid())]
        flags = 0x08000000 if sys.platform == "win32" else 0                       # CREATE_NO_WINDOW
        try:
            self.proc = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1, creationflags=flags)
        except Exception as exc:
            self.on_log("error", f"output process does not start: {exc}")
            return False
        threading.Thread(target=self._read_stdout, args=(self.proc,), daemon=True, name="opencue-dmx-output-out").start()
        threading.Thread(target=self._read_stderr, args=(self.proc,), daemon=True, name="opencue-dmx-output-err").start()
        return True

    def stop(self) -> None:
        self._stopping = True
        proc = self.proc
        if proc is not None:
            try:
                with self._write_lock:
                    proc.stdin.write(json.dumps({"cmd": "quit"}) + "\n")
                    proc.stdin.flush()
            except Exception:
                pass
            try:
                proc.stdin.close()
            except Exception:
                pass
            try:
                proc.wait(timeout=2.0)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
        self.proc = None
        shm, self.shm = self.shm, None
        self.frames = None
        self.ov = None
        if shm is not None:
            try:
                shm.close()
                shm.unlink()
            except Exception:
                pass

    @property
    def alive(self) -> bool:
        return self.proc is not None and self.proc.poll() is None

    # ---- Lesen
    def _read_stdout(self, proc: subprocess.Popen) -> None:
        for line in proc.stdout:
            try:
                message = json.loads(line)
            except Exception:
                continue
            if message.get("event") == "ready":
                self.ready.set()
            elif "log" in message:
                self.on_log(str(message["log"]), str(message.get("msg", "")))
            elif "reply_to" in message:
                waiter = self._waiters.get(message["reply_to"])
                if waiter:
                    waiter[1].update(message)
                    waiter[0].set()
                if "enttec" in message:
                    self.status["enttec"] = message["enttec"]
            elif "fxlive" in message:
                self.fx_live = message["fxlive"]
                self.fx_live_seq += 1
            elif "status" in message:
                self.status["stats"] = message["status"]
                if "fx" in message:
                    self.status["fx"] = message["fx"]
                if "enttec" in message:
                    self.status["enttec"] = message["enttec"]
            elif message.get("event") in ("fx_ready", "fx_failed"):
                self.fx_ok = message["event"] == "fx_ready"
            elif message.get("event"):
                self.on_event(message)

    def _read_stderr(self, proc: subprocess.Popen) -> None:
        for line in proc.stderr:
            if line.strip():
                self.on_log("error", "output process: " + line.strip())

    def _monitor(self) -> None:
        while not self._stopping:
            time.sleep(1.0)
            proc = self.proc
            if self._stopping or proc is None or proc.poll() is None:
                continue
            now = time.monotonic()
            self._restarts = [t for t in self._restarts if now - t < 60.0]
            if len(self._restarts) >= 5:
                self.on_log("error", "OC-3105 Ausgabe-Prozess stirbt immer wieder - die Ausgabe laeuft im Hauptprogramm weiter")
                self.on_event({"event": "output_failed"})
                return
            self._restarts.append(now)
            self.on_log("warning", f"OC-3105 Ausgabe-Prozess beendet (Code {proc.returncode}) - wird neu gestartet")
            if self._spawn() and self.ready.wait(6.0):
                self.send({"cmd": "config", **self.config})
                if self.dmxin_last is not None:
                    self.send(self.dmxin_last)
                again = self.fx_message_again()
                if again is not None:
                    self.send(again)
                if self.levels_last is not None:
                    self.send(self.levels_last)
                if self.fades_last is not None:                                  # laufende Ueberblendungen weiterspielen: die Zeit seit dem Senden zaehlt dazu
                    message, sent = self.fades_last
                    late = time.monotonic() - sent
                    self.send({**message, "jobs": [{**j, "elapsed": j["elapsed"] + (late if j.get("running") else 0.0)} for j in message["jobs"]]})

    # ---- Senden
    def send(self, message: Dict[str, Any]) -> bool:
        """Reiht die Nachricht ein (der Schreiber-Thread schickt sie); gibt False zurueck, wenn der Prozess nicht laeuft."""
        proc = self.proc
        if proc is None or proc.poll() is not None or proc.stdin is None:
            return False
        try:
            line = json.dumps(message) + "\n"
        except Exception:
            return False
        with self._send_cond:
            self._sendq.append(line)
            self._send_cond.notify()
        return True

    def _writer_loop(self) -> None:
        while not self._stopping:
            with self._send_cond:
                if not self._sendq:
                    self._send_cond.wait(0.5)
                lines = list(self._sendq)
                self._sendq.clear()
            proc = self.proc
            if not lines or proc is None or proc.stdin is None:
                continue
            with self._write_lock:
                try:
                    proc.stdin.write("".join(lines))
                    proc.stdin.flush()
                except Exception:
                    pass

    def request(self, message: Dict[str, Any], timeout: float = 2.0) -> Optional[Dict[str, Any]]:
        self._next_id += 1
        key = self._next_id
        waiter: Tuple[threading.Event, Dict[str, Any]] = (threading.Event(), {})
        self._waiters[key] = waiter
        try:
            if not self.send({**message, "id": key}):
                return None
            return waiter[1] if waiter[0].wait(timeout) else None
        finally:
            self._waiters.pop(key, None)

    def send_fx(self, cfg_id: int, cfg: Dict[str, Any]) -> bool:
        """Neue Effekt-Konfiguration an den Rechenkern (Nummer cfg_id; er quittiert sie im gemeinsamen Speicher)."""
        message = {"cmd": "fx", "cfg_id": cfg_id, "cfg": cfg}
        self.fx_last = message
        self.fx_last_time = time.monotonic()
        return self.send(message)

    def fx_message_again(self) -> Optional[Dict[str, Any]]:
        """Die zuletzt geschickte Effekt-Konfiguration fuer eine Wiederholung: die Ein-/Ausblendungen sind inzwischen entsprechend aelter."""
        if self.fx_last is None:
            return None
        late = time.monotonic() - self.fx_last_time
        cfg = dict(self.fx_last["cfg"])
        cfg["ramps"] = [[r[0], r[1], r[2], r[3], r[4] + late, *r[5:]] for r in cfg.get("ramps") or []]
        return {**self.fx_last, "cfg": cfg}

    def send_fades(self, jobs: List[Dict[str, Any]], types: Dict[str, Any]) -> bool:
        """Die laufenden Cue-Ueberblendungen (vollstaendige Menge) an den Ausgabe-Prozess; er spielt sie mit eigener Uhr ab."""
        message = {"cmd": "fades", "jobs": jobs, "types": types}
        self.fades_last = (message, time.monotonic())
        return self.send(message)

    def send_fade_levels(self, levels: Dict[str, float]) -> bool:
        message = {"cmd": "fadelvl", "l": levels}
        self.levels_last = message
        return self.send(message)

    def read_overlay(self) -> Tuple[int, Dict[int, Tuple[bytes, bytes]]]:
        """(Nummer der uebernommenen Konfiguration, Ueberlagerung je Universum: (Werte, Maske))."""
        ov = self.ov
        if ov is None:
            return 0, {}
        return ov.applied(), ov.read_all()

    def set_config(self, config: Dict[str, Any]) -> None:
        self.config = config
        self.send({"cmd": "config", **config})

    def publish(self, universe: int, payload: bytes) -> bool:
        frames = self.frames
        if frames is None:
            return False
        slot = frames.slot_for(universe, self.slots)
        if slot is None:
            return False
        frames.publish(slot, payload)
        return True
