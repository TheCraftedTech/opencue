# Copyright (C) 2026 Samuel Zenker
# SPDX-License-Identifier: GPL-3.0-or-later
"""
dmx_engine.py
DMX-Ausgabe-Engine von OpenCue.

Sendet DMX-Werte fuer beliebig viele Universen parallel ueber drei komplett
entkoppelte Protokolle ins Lichtnetzwerk:
  - sACN (E1.31)   ueber die Bibliothek "sacn"
  - Art-Net        ueber die Bibliothek "stupidArtnet"
  - USB DMX        ueber pyserial direkt an Enttec DMX USB Pro kompatible
                   Hardware (FTDI-basiert, COM-Port / /dev/ttyUSB*)

HINWEIS zur Art-Net-Bibliothek:
Die urspruenglich angefragte Bibliothek "python-artnet" ist auf PyPI
ausschliesslich ein Art-Net *Empfaenger* (Node-Discovery/Receiver) und kann
keine DMX-Daten senden. Fuer den Sende-Pfad wird daher "stupidArtnet"
verwendet - der gaengige Standard fuer Art-Net-Output in Python.

Beide Netzwerk-Backend-Bibliotheken unterhalten pro Universum einen eigenen
Hintergrund-Thread, der die Daten mit fester Framerate zyklisch erneut
aussendet (Keep-Alive gemaess E1.31- / Art-Net-Spezifikation).
set_channel() / set_channels() aktualisieren nur den Puffer - den
eigentlichen Netzwerkversand uebernehmen die Bibliotheken selbst.

ENTTEC DMX USB PRO (USB-serial):
Nutzt direkt pyserial mit dem dokumentierten Widget-Protokoll des
Enttec DMX USB Pro (Label 6: Output Only Send DMX Packet Request).
set_channels() sendet nach jedem Puffer-Update synchron einen Serial-Frame
an das Geraet - kein eigener Hintergrund-Thread noetig, da die Bibliothek
stupidArtnet / sacn bereits den 40-Hz-Takt vorgeben.
Verbindungsfehler (getrenntes Kabel, falscher Port) werden abgefangen und
im Fehler-String _enttec_error gespeichert, der Server-Absturz wird vermieden.

ENTKOPPELUNG & LAUFZEIT-KONFIGURATION (Settings-Modal -> DMX/Network):
Art-Net und sACN haben je einen eigenen Enable-Schalter (`artnet_enabled`,
`sacn_enabled`) - ist ein Protokoll deaktiviert, wird es beim Schreiben
eines Kanalwerts einfach uebersprungen (die Puffer/Sender-Objekte bleiben
bestehen, es wird nur nichts mehr *gesendet*). Beim Deaktivieren wird
einmalig ein Blackout an das jeweilige Protokoll geschickt, damit
angeschlossene Geraete nicht auf dem zuletzt gesendeten (ggf. nicht
schwarzen) Wert haengen bleiben; beim Wieder-Aktivieren wird der aktuelle
Puffer-Inhalt sofort nachgeholt. Art-Net's Ziel-Adresse ("Target IP") kann
jederzeit direkt umgeschrieben werden (stupidArtnet liest sie bei jedem
Sendezyklus neu). Die lokale Sende-Interface-Adresse ("Bind IP") ist dagegen
nur beim Socket-Aufbau wirksam - ein Wechsel baut deshalb alle aktiven
Art-Net-Sender neu auf (mit demselben Puffer-Inhalt, damit der Wechsel
keinen sichtbaren Blackout verursacht).
"""

from __future__ import annotations

import logging
import os
import queue
import sys
import socket
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("opencue.dmx")

import sacn
from stupidArtnet import StupidArtnet

try:
    import serial
    import serial.tools.list_ports
    _SERIAL_AVAILABLE = True
except ImportError:
    _SERIAL_AVAILABLE = False

FTDI_VENDOR_ID = 0x0403                                      # Enttec DMX USB Pro / Open DMX und kompatible Adapter (FTDI) - Erkennung fuer "Automatisch"
AUTO = "auto"                                                # Art-Net-Ziel "Automatisch": gefundene Geraete direkt bedienen (app/artnet_discovery.py)
ARTNET_FALLBACK_TARGETS = ("2.255.255.255", "255.255.255.255")


class _MultiArtnet(StupidArtnet):
    """Art-Net-Sender, der dasselbe Paket ausser an `target_ip` auch an weitere Adressen schickt (Ziel "Automatisch": ein Paket je gefundenem Geraet)."""

    extra_targets: Tuple[str, ...] = ()

    def start(self):                                                  # noqa: D401 - KEIN eigener Takt-Thread mehr
        """Die Bibliothek startete je Universum einen Zeitgeber, der pro Bild einen NEUEN Thread erzeugte, ohne Ausgleich der Verzoegerung: ~37 statt 40 Bilder je Sekunde,
        unter Last ~33 und Luecken bis ueber 180 ms. Jetzt sendet EIN Takt-Thread der DMXEngine (DMXEngine._clock_loop) alle Universen mit festem, driftfreiem Zeitplan."""
        self.running = True

    def show(self):                                                   # noqa: D401 - ersetzt StupidArtnet.show (dieselbe Arbeit, mehrere Ziele)
        packet = bytearray()
        packet.extend(self.packet_header)
        packet.extend(self.buffer)
        try:
            self.socket_client.sendto(packet, (self.target_ip, self.port))
            for ip in self.extra_targets:
                self.socket_client.sendto(packet, (ip, self.port))
            if self.if_sync:
                self.send_artsync()
        except socket.error as error:
            logger.debug("[DMX] Art-Net socket error: %s", error)
        finally:
            self.sequence = (self.sequence + 1) % 256


# Enttec DMX USB Pro Widget-Protokoll: Label 6 = Output Only Send DMX Packet
_ENTTEC_MSG_START = 0x7E
_ENTTEC_MSG_END = 0xE7
_ENTTEC_LABEL_SEND_DMX = 6
_ENTTEC_DMX_START_CODE = 0x00


def _build_enttec_frame(dmx_data: bytes) -> bytes:
    """Baut einen Enttec DMX USB Pro Serial-Frame (Label 6)."""
    body = bytes([_ENTTEC_DMX_START_CODE]) + dmx_data[:DMX_UNIVERSE_SIZE]
    length = len(body)
    return (
        bytes([_ENTTEC_MSG_START, _ENTTEC_LABEL_SEND_DMX, length & 0xFF, (length >> 8) & 0xFF])
        + body
        + bytes([_ENTTEC_MSG_END])
    )

DMX_UNIVERSE_SIZE = 512
OUTPUT_FPS = 40  # Hz - innerhalb der DMX512/Art-Net-Spezifikation (max. ~44Hz)
DEFAULT_ARTNET_TARGET_IP = "255.255.255.255"  # Broadcast; im Settings-Modal aenderbar
DEFAULT_ARTNET_BIND_IP = ""  # leer = Betriebssystem waehlt das Sende-Interface

_BLACKOUT_BYTES = bytes(DMX_UNIVERSE_SIZE)



def _raise_thread_priority() -> None:
    """Der DMX-Ausgabe-Thread bekommt unter Windows eine etwas hoehere Prioritaet (ABOVE_NORMAL): Bilder, WebSocket-Strom und Analysen duerfen ihn nie ausbremsen. Ohne Windows / bei Fehlern passiert nichts."""
    try:
        import ctypes
        kernel = ctypes.windll.kernel32                                   # type: ignore[attr-defined]
        kernel.SetThreadPriority(kernel.GetCurrentThread(), 1)
    except Exception:
        pass

class DMXEngine:
    """Haelt DMX-Puffer pro Universum und streamt sie via sACN + Art-Net + USB."""

    def __init__(self) -> None:
        self._buffers: Dict[int, bytearray] = {}
        self._sacn_sender: Optional[sacn.sACNsender] = None      # wird ERST angelegt, wenn sACN eingeschaltet ist (siehe _ensure_sacn_locked)
        self._sacn_active: set = set()                           # Universen mit aktivem sACN-Ausgang
        self._artnet_senders: Dict[int, StupidArtnet] = {}
        self._lock = threading.Lock()
        self._started = False

        # Dynamisch zur Laufzeit umschaltbar (siehe configure() / set_*).
        self._artnet_enabled = True
        self._sacn_enabled = False
        self._artnet_target_ip = DEFAULT_ARTNET_TARGET_IP
        self._artnet_bind_ip = DEFAULT_ARTNET_BIND_IP
        self._artnet_auto_targets: List[str] = list(ARTNET_FALLBACK_TARGETS)       # Betrieb "Automatisch": gefundene Geraete (oder Broadcast, solange keines antwortet)

        # Enttec USB DMX Pro
        self._enttec_enabled: bool = False
        self._enttec_port: str = ""                                                # "" = Automatisch (FTDI-Adapter erkennen)
        self._enttec_active_port: str = ""                                         # der Port, der im Automatik-Betrieb gerade benutzt wird
        self._enttec_universe: int = 1
        self._enttec_serial: Optional[object] = None  # serial.Serial
        self._enttec_error: str = ""
        self._enttec_connected_remote = False                                       # Zustand des USB-Adapters im Ausgabe-Prozess

        # Dedizierter Ausgabe-Thread - entkoppelt alle DMX-Schreiboperationen
        # vollstaendig vom asyncio-Event-Loop des WebSocket-Servers, damit
        # hohe UI-Last oder Netzwerk-Schwankungen niemals die DMX-Aussendung
        # stoeren. Der Thread laeuft als Daemon und beendet sich mit dem Prozess.
        # Kapazitaet 200 Items: bei 40 Hz bleiben 5 s Puffer; bei Ueberlauf
        # gewinnt der neueste Wert (Real-Time-DMX kennt keinen "alten" Wert).
        self._clock_stop = threading.Event()
        self._clock_thread: Optional[threading.Thread] = None
        # Ausgabe als eigener Prozess (app/dmx_output.py): wird vom Programm eingeschaltet (enable_process_output); Tests und Skripte bleiben bei der Ausgabe im selben Prozess
        self._use_process = os.environ.get("OPENCUE_DMX_PROCESS") == "1"
        self._proc: Optional[Any] = None
        self.output_mode = "in-process"                                           # "process" | "in-process" (Anzeige / Test)
        self.on_output_event: Optional[Any] = None                                # fn(dict): Ereignisse des Ausgabe-Prozesses (z. B. USB-Adapter getrennt)
        self._artnet_quiet_until = 0.0                                          # nach dem Ausschalten von Art-Net noch kurz Nullen senden (sauber verstummen), danach Stille
        self.clock_stats = {"ticks": 0, "late_ticks": 0, "max_late_ms": 0.0}    # Messwerte des Takts (Selbstkontrolle / Test)
        self._output_queue: queue.Queue = queue.Queue(maxsize=200)
        self._output_thread = threading.Thread(
            target=self._output_loop,
            daemon=True,
            name="opencue-dmx-output",
        )
        self._output_thread.start()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def configure(
        self,
        artnet_enabled: bool = True,
        artnet_target_ip: str = DEFAULT_ARTNET_TARGET_IP,
        artnet_bind_ip: str = DEFAULT_ARTNET_BIND_IP,
        sacn_enabled: bool = True,
        enttec_enabled: bool = False,
        enttec_port: str = "",
        enttec_universe: int = 1,
    ) -> None:
        """Uebernimmt die persistierten Einstellungen aus app_config.json
        (StateManager) - von server.py vor start() aufgerufen, damit die
        Engine gleich in der zuletzt vom Nutzer gewaehlten Konfiguration
        hochfaehrt statt immer mit den Werkseinstellungen."""
        self._artnet_enabled = bool(artnet_enabled)
        self._sacn_enabled = bool(sacn_enabled)
        self._artnet_target_ip = artnet_target_ip or DEFAULT_ARTNET_TARGET_IP
        self._artnet_bind_ip = artnet_bind_ip
        self._enttec_enabled = bool(enttec_enabled)
        self._enttec_port = enttec_port or ""
        self._enttec_universe = max(1, int(enttec_universe))

    def _ensure_sacn_locked(self) -> None:
        """Legt den sACN-Sender an (bindet UDP 0.0.0.0:5568 - dabei fragt die Windows-Firewall beim ersten Mal nach der Freigabe). Deshalb passiert das nur,
        wenn sACN eingeschaltet ist, nie schon beim Programmstart. Muss unter self._lock laufen."""
        if self._sacn_sender is None:
            self._sacn_sender = sacn.sACNsender()
            self._sacn_sender.start()
            self._sacn_active = set()
        for universe in self._buffers:
            if universe not in self._sacn_active:
                self._sacn_sender.activate_output(universe)          # Multicast, spec-konform
                self._sacn_sender[universe].multicast = True
                self._sacn_active.add(universe)

    def start(self) -> None:
        """Startet die Ausgabe (sACN-Sender nur bei eingeschaltetem sACN) und ggf. die Enttec-Verbindung."""
        if self._started:
            return
        if self._sacn_enabled:
            with self._lock:
                self._ensure_sacn_locked()
        self._started = True
        if self._use_process and self._start_process():
            if self._enttec_enabled:
                pass                                                                # der Ausgabe-Prozess oeffnet den USB-Adapter selbst (Einstellungen gehen mit config)
            return
        # Art-Net-Takt: ein Thread, driftfreier Zeitplan. Ein kurzes GIL-Umschaltintervall (1 ms statt 5 ms) laesst ihn auch dann rechtzeitig laufen, wenn der Server
        # gerade viel rechnet (Bedienung, Effekte, Anzeige).
        try:
            sys.setswitchinterval(0.001)
        except Exception:
            pass
        self._clock_stop.clear()
        self._clock_thread = threading.Thread(target=self._clock_loop, daemon=True, name="opencue-dmx-clock")
        self._clock_thread.start()
        # Enttec sofort oeffnen, wenn beim Start aktiviert (ohne gewaehlten Port: einen angesteckten Adapter automatisch suchen).
        if self._enttec_enabled:
            self._open_enttec()

    def shutdown(self) -> None:
        """Faehrt alle Sender (sACN + Art-Net + Enttec) sauber herunter."""
        if not self._started:
            return
        # Ausgabe-Thread zuerst stoppen, damit keine neuen set_channels_batch()-
        # Aufrufe mehr eintreffen, waehrend die Sockets geschlossen werden.
        self._output_queue.put(None)  # Sentinel stoppt _output_loop()
        self._output_thread.join(timeout=2.0)
        self._clock_stop.set()
        if self._clock_thread is not None:
            self._clock_thread.join(timeout=2.0)
        if self._proc is not None:
            self._proc.stop()
            self._proc = None
            self.output_mode = "in-process"
        with self._lock:
            for artnet_sender in self._artnet_senders.values():
                artnet_sender.stop()
            # stupidArtnet's Hintergrund-Thread prueft sein "running"-Flag nur
            # zwischen zwei Sendezyklen - kurz warten, bevor die Sockets
            # geschlossen werden, verhindert ein "Sende auf geschlossenem
            # Socket"-Fehler im letzten, bereits laufenden Zyklus.
            time.sleep(2.0 / OUTPUT_FPS)
            for artnet_sender in self._artnet_senders.values():
                artnet_sender.close()
            self._artnet_senders.clear()
            if self._sacn_sender is not None:
                self._sacn_sender.stop()
                self._sacn_sender = None
                self._sacn_active = set()
            self._close_enttec_locked()
        self._started = False

    # ------------------------------------------------------------------
    # Dedizierter Ausgabe-Thread & Non-Blocking-Post-API
    # ------------------------------------------------------------------
    def _output_loop(self) -> None:
        """Kernschleife des dedizierten DMX-Ausgabe-Threads.

        Laeuft als Daemon ausserhalb des asyncio-Event-Loops und verarbeitet
        alle DMX-Schreiboperationen sequenziell. Entkopplung von asyncio
        verhindert, dass hohe UI-Last oder WebSocket-Ticks jemals zu
        Unterbrechungen im DMX-Signal (30–44 Hz) fuehren.
        """
        _raise_thread_priority()
        while True:
            item = self._output_queue.get()
            if item is None:
                break  # Shutdown-Sentinel
            op, universe, data = item
            try:
                if op == "batch":
                    self.set_channels_batch(universe, data)
                elif op == "blackout":
                    self.blackout(universe)
            except Exception as exc:
                logger.error("[DMX] OC-3101 output thread error (op=%s): %s", op, exc)

    # ------------------------------------------------------------------
    # Ausgabe als eigener Prozess
    # ------------------------------------------------------------------
    def enable_process_output(self, on: bool = True) -> None:
        """Vor start(): die Ausgabe (Art-Net, sACN, USB) laeuft in einem eigenen Prozess (app/dmx_output.py). Ohne diesen Aufruf bleibt sie im selben Prozess."""
        self._use_process = bool(on)

    def _proc_config(self) -> Dict[str, Any]:
        primary, extras = self._artnet_targets()
        return {
            "artnet": {"enabled": self._artnet_enabled, "target": primary, "extras": list(extras), "bind": self._artnet_bind_ip},
            "sacn": self._sacn_enabled,
            "enttec": {"enabled": self._enttec_enabled, "port": self._enttec_port, "universe": self._enttec_universe},
        }

    def _sync_proc(self, wait: bool = False) -> Optional[Dict[str, Any]]:
        """Einstellungen an den Ausgabe-Prozess schicken. wait=True (nur ausserhalb der Sperre!): auf die Antwort warten - sie nennt den Zustand des USB-Adapters."""
        proc = self._proc
        if proc is None:
            return None
        config = self._proc_config()
        proc.config = config
        if not wait:
            proc.send({"cmd": "config", **config})
            return None
        reply = proc.request({"cmd": "config", **config}, timeout=3.0)
        if reply and "enttec" in reply:
            self._proc_enttec(reply["enttec"])
        return reply

    def _proc_enttec(self, status: Dict[str, Any]) -> None:
        self._enttec_error = str(status.get("error") or "")
        self._enttec_active_port = str(status.get("port") or "") if not self._enttec_port else self._enttec_active_port
        self._enttec_connected_remote = bool(status.get("connected"))

    def _start_process(self) -> bool:
        try:
            from app.dmx_output import OutputProcess
        except Exception as exc:
            logger.error("[DMX] Ausgabe-Prozess nicht verfuegbar: %s", exc)
            return False

        def log(level: str, text: str) -> None:
            getattr(logger, level if level in ("debug", "info", "warning", "error") else "info")("[DMX/out] %s", text)

        def event(message: Dict[str, Any]) -> None:
            if message.get("event") == "output_failed":                             # der Prozess stirbt immer wieder: die Ausgabe laeuft im Hauptprogramm weiter
                threading.Thread(target=self._fallback_inprocess, daemon=True).start()
            elif self.on_output_event is not None:
                try:
                    self.on_output_event(message)
                except Exception:
                    logger.exception("[DMX] output event handler failed")

        proc = OutputProcess(on_log=log, on_event=event)
        if not proc.start(self._proc_config()):
            logger.error("[DMX] Der Ausgabe-Prozess startet nicht - die Ausgabe laeuft im Hauptprogramm (OC-3105)")
            try:
                proc.stop()
            except Exception:
                pass
            return False
        with self._lock:
            self._proc = proc
            self._enttec_connected_remote = False
            for universe, buf in self._buffers.items():                            # schon angelegte Universen sofort bereitstellen
                proc.publish(universe, bytes(buf))
        self.output_mode = "process"
        logger.info("[DMX] Ausgabe im eigenen Prozess (PID %s)", proc.proc.pid if proc.proc else "?")
        self._sync_proc(wait=True)
        return True

    def fx_process(self) -> Optional[Any]:
        """Der Ausgabe-Prozess, in dem die Effekte rechnen (None: die Ausgabe laeuft im Hauptprogramm, dann rechnen die Effekte dort). Waehrend eines Neustarts des Prozesses bleibt er der
        Ansprechpartner (die Konfiguration geht nach dem Neustart erneut raus)."""
        proc = self._proc
        if self.output_mode == "process" and proc is not None and proc.fx_ok is not False:
            return proc
        return None                                                              # der Prozess kann die Effekte nicht rechnen (fx_ok False): sie laufen im Hauptprogramm

    def mirror_overlay(self, universe: int, values: bytes, mask: bytes) -> bool:
        """Uebernimmt die Kanalwerte, die der Effekt-Rechenkern im Ausgabe-Prozess ueber das Bild legt (Maske 1), in den Puffer: der Puffer bleibt die Wahrheit (DMX-Monitor, Live-Anzeige), und beim
        Ende eines Effekts bleibt sein letzter Wert stehen. Gibt True zurueck, wenn sich etwas geaendert hat."""
        changed = False
        with self._lock:
            if not any(mask) and universe not in self._buffers:
                return False
            self._ensure_universe(universe)
            buf = self._buffers[universe]
            for index in range(DMX_UNIVERSE_SIZE):
                if mask[index] and buf[index] != values[index]:
                    buf[index] = values[index]
                    changed = True
            if changed:
                self._push_universe_locked(universe)
        if changed:
            self._notify(universe)
        return changed

    def _fallback_inprocess(self) -> None:
        """Der Ausgabe-Prozess ist nicht mehr zu halten: Sender und Takt im Hauptprogramm aufbauen (der letzte Stand der Universen steht in den Puffern)."""
        with self._lock:
            proc, self._proc = self._proc, None
            self.output_mode = "in-process"
            self._use_process = False
            for universe in list(self._buffers):
                if universe not in self._artnet_senders:
                    self._artnet_senders[universe] = self._create_artnet_sender(universe)
                    self._artnet_senders[universe].set(bytearray(self._buffers[universe]))
            if self._sacn_enabled:
                self._ensure_sacn_locked()
            if self._enttec_enabled:
                self._open_enttec_locked()
        if proc is not None:
            try:
                proc.stop()
            except Exception:
                pass
        self._clock_stop.clear()
        self._clock_thread = threading.Thread(target=self._clock_loop, daemon=True, name="opencue-dmx-clock")
        self._clock_thread.start()
        logger.warning("[DMX] Ausgabe laeuft jetzt im Hauptprogramm")

    def _clock_loop(self) -> None:
        """Der Takt der Art-Net-Ausgabe: alle Universen mit OUTPUT_FPS, nach einem festen Zeitplan (naechster Zeitpunkt = vorheriger + Periode, kein Auflaufen von Verzoegerungen).
        Grob schlafen, die letzte Millisekunde abgeben und nachpruefen. Liegt der Takt mehr als drei Perioden zurueck (Standby, Debugger), beginnt der Zeitplan neu."""
        _raise_thread_priority()
        period = 1.0 / OUTPUT_FPS
        perf = time.perf_counter
        next_t = perf()
        while not self._clock_stop.is_set():
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
            self.clock_stats["ticks"] += 1
            if late > period * 1000.0 / 2:
                self.clock_stats["late_ticks"] += 1
            if late > self.clock_stats["max_late_ms"]:
                self.clock_stats["max_late_ms"] = late
            t_tick = perf()
            try:
                self._clock_tick()
            except Exception as exc:                                             # nie den Takt beenden
                logger.error("[DMX] OC-3104 clock tick error: %s", exc)
            spent = (perf() - t_tick) * 1000.0
            if late > 40.0 or spent > 40.0:                                      # ein Hakeln des Takts steht im Protokoll (Ursache suchen: Aufwachen verspaetet = Rechenzeit anderer Threads, Senden dauerte = Sperre / Netzwerk)
                logger.warning("[DMX] clock stall: woke %.0f ms late, tick took %.0f ms", late, spent)
                if os.environ.get("OPENCUE_DEBUG_STALL"):                       # Diagnose: wo stehen die anderen Threads gerade (der Verursacher hat den Interpreter eben erst abgegeben)
                    try:
                        for ident, frame in sys._current_frames().items():
                            if ident != threading.get_ident():
                                logger.warning("[DMX]   thread %s: %s:%s in %s", ident, frame.f_code.co_filename.split("OpenCue")[-1], frame.f_lineno, frame.f_code.co_name)
                    except Exception:
                        pass

    def _clock_tick(self) -> None:
        """Ein Takt: der aktuelle Stand jedes Universums geht raus. OHNE die Sperre `self._lock`: haelt ein Schreiber sie gerade (und wartet selbst auf den Interpreter, weil der
        Server rechnet), wuerde der Takt mit ihm stehen - gemessen bis zu 140 ms. Die Zugriffe unten sind einzelne, unteilbare Lese-Operationen (Wahrheitswert, Kopie der Sender-Liste, Puffer-Zuweisung
        im Sender); ein Sender, der gerade ersetzt wird, schickt hoechstens ein Bild mit dem alten Stand."""
        if not (self._artnet_enabled or time.monotonic() < self._artnet_quiet_until):
            return
        for sender in tuple(self._artnet_senders.values()):
            sender.show()

    def set_change_callback(self, fn) -> None:
        """fn(universe) wird aufgerufen, wenn sich ein Wert im Puffer eines Universums wirklich geaendert hat (aus jedem
        Thread, ausserhalb der Sperre). Der Server leitet daraus die Live-Anzeige ab: der Puffer ist die Wahrheit."""
        self._on_change = fn

    def _notify(self, universe: int) -> None:
        fn = getattr(self, "_on_change", None)
        if fn is not None:
            try:
                fn(universe)
            except Exception as exc:                      # nie die Ausgabe stoeren
                logger.error("[DMX] change callback failed: %s", exc)

    def update_buffer(self, universe: int, channels: Dict[int, int]) -> None:
        """Updates the internal snapshot buffer synchronously WITHOUT hardware output.
        Call before get_universe_snapshot() to guarantee a correct read-back.
        Hardware output must be scheduled separately via post_batch()."""
        changed = False
        with self._lock:
            self._ensure_universe(universe)
            buf = self._buffers[universe]
            for channel, value in channels.items():
                idx = channel - 1
                if 0 <= idx < DMX_UNIVERSE_SIZE:
                    new = max(0, min(255, int(value)))
                    if buf[idx] != new:
                        buf[idx] = new
                        changed = True
        if changed:
            self._notify(universe)

    def commit_batch(self, universe: int, channels: Dict[int, int]) -> None:
        """Snapshot-Puffer sofort aktualisieren UND Hardware-Ausgabe einreihen -
        das Standard-Paar fuer alle Befehls- und Wiederanlauf-Pfade, damit
        get_universe_snapshot() direkt danach den angewandten Zustand liefert."""
        self.update_buffer(universe, channels)
        self.post_batch(universe, channels)

    def post_batch(self, universe: int, channels: Dict[int, int]) -> None:
        """Non-blockierender DMX-Batch-Update fuer den Ausgabe-Thread.

        Ersetzt set_channels_batch() in allen asyncio-Kontexten (server.py,
        cue_engine.py), damit kein I/O den asyncio-Loop blockiert. Bei vollem
        Queue gewinnt der neueste Wert (aeltester wird verworfen).
        """
        item = ("batch", universe, dict(channels))
        try:
            self._output_queue.put_nowait(item)
        except queue.Full:
            # Aeltesten Eintrag verwerfen und neuen einreihen
            try:
                self._output_queue.get_nowait()
            except queue.Empty:
                pass
            try:
                self._output_queue.put_nowait(item)
            except queue.Full:
                pass

    def reinitialize_outputs(self) -> Dict[str, object]:
        """Initialisiert alle DMX-Ausgaben neu ohne Neustart der Anwendung.

        - Art-Net: baut alle aktiven Sender mit der aktuellen bind_ip neu auf
          (identisch zu set_artnet_bind_ip - wiederverwendet Pufferinhalte)
        - sACN: keine Aktion noetig (Sender-Thread laeuft ununterbrochen)
        - Enttec: schliesst und oeffnet den seriellen Port neu

        Rueckgabe: {"artnet": ok_bool, "enttec_status": {...}}
        """
        artnet_ok = True
        if self._proc is not None:
            reply = self._proc.request({"cmd": "reinit"}, timeout=5.0) or {}
            if "enttec" in reply:
                self._proc_enttec(reply["enttec"])
            enttec_ok = bool(reply.get("enttec_ok")) if self._enttec_enabled else False
            logger.info("[DMX] Re-init (Ausgabe-Prozess): Art-Net ok | USB %s", "ok" if enttec_ok else "aus / Fehler")
            return {"artnet": True, "enttec_status": self.get_enttec_status()}
        try:
            # Art-Net-Sender mit aktueller Konfiguration neu aufbauen
            with self._lock:
                old_senders: Dict[int, StupidArtnet] = dict(self._artnet_senders)
                if old_senders:
                    for sender in old_senders.values():
                        sender.stop()
                    time.sleep(2.0 / OUTPUT_FPS)
                    for universe, old_sender in old_senders.items():
                        old_sender.close()
                        new_sender = self._create_artnet_sender(universe)
                        new_sender.set(bytearray(self._buffers[universe]))
                        self._artnet_senders[universe] = new_sender
        except Exception as exc:
            logger.error("[DMX] OC-3102 reinit Art-Net error: %s", exc)
            artnet_ok = False

        # Enttec neu verbinden
        enttec_ok = self.reconnect_enttec() if self._enttec_enabled else False

        artnet_part = "Art-Net ✓" if artnet_ok else "Art-Net ✗"
        if not self._enttec_enabled:
            enttec_part = "USB DMX disabled"
        elif enttec_ok:
            enttec_part = f"USB DMX ✓ {self._effective_enttec_port()}"
        else:
            enttec_part = f"USB DMX ✗ {self._effective_enttec_port() or 'auto'} ({self._enttec_error or 'unknown error'})"
        logger.info("[DMX] Re-init: %s | %s", artnet_part, enttec_part)
        return {"artnet": artnet_ok, "enttec_status": self.get_enttec_status()}

    # ------------------------------------------------------------------
    # Enttec USB DMX - private Hilfsmethoden
    # ------------------------------------------------------------------
    def _open_enttec(self) -> bool:
        """Oeffnet die serielle Verbindung zum Enttec-Adapter. Gibt True zurueck wenn OK.
        Darf nur unter self._lock aufgerufen werden oder waehrend es sicher ist."""
        with self._lock:
            return self._open_enttec_locked()

    @staticmethod
    def _clean_serial_error(exc: Exception) -> str:
        """Compact single-line description of a pyserial/serial error.
        Strips [Errno N] / [Error N] prefixes and Python exception repr suffixes
        (e.g. 'FileNotFoundError(2, "...", None, 2)') from the raw exception string."""
        import re as _re
        msg = str(exc)
        msg = _re.sub(r"\[Errno\s+\d+\]\s*", "", msg)
        msg = _re.sub(r"\[Error\s+\d+\]\s*", "", msg, flags=_re.IGNORECASE)
        msg = _re.sub(r"\[Win[Ee]rror[^\]]*\]\s*", "", msg)
        # Strip trailing ": SomePythonError(...)" — Windows pyserial repr
        msg = _re.sub(r":\s*\w+(?:Error|Exception)\s*\(.*", "", msg)
        msg = msg.strip(" :;,")
        return msg or str(exc)

    @staticmethod
    def detect_usb_dmx() -> List[Dict[str, object]]:
        """USB-DMX-Adapter, die wie ein Enttec DMX USB Pro aussehen (FTDI-Chip oder "DMX" / "Enttec" im Namen): [{device, description, vid, pid}] - fuer "Automatisch"."""
        if not _SERIAL_AVAILABLE:
            return []
        found: List[Dict[str, object]] = []
        try:
            for p in serial.tools.list_ports.comports():  # type: ignore[name-defined]
                text = " ".join(str(x or "") for x in (p.description, p.manufacturer, p.product)).lower()
                if p.vid == FTDI_VENDOR_ID or "dmx" in text or "enttec" in text:
                    found.append({"device": p.device, "description": str(p.description or p.device), "vid": p.vid, "pid": p.pid})
        except Exception:
            return []
        return sorted(found, key=lambda d: str(d["device"]))

    def _effective_enttec_port(self) -> str:
        return self._enttec_port or self._enttec_active_port

    def _pick_auto_port_locked(self) -> str:
        """Automatik: der erste erkannte Adapter ("" = keiner angesteckt)."""
        candidates = self.detect_usb_dmx()
        return str(candidates[0]["device"]) if candidates else ""

    def _open_enttec_locked(self) -> bool:
        """Oeffnet die serielle Verbindung (muss bereits unter _lock laufen). Ohne gewaehlten Port ("Automatisch") wird ein angesteckter Adapter selbst gesucht."""
        self._close_enttec_locked()
        if not _SERIAL_AVAILABLE:
            self._enttec_error = "pyserial is not installed (pip install pyserial)"
            return False
        if not self._enttec_port:
            self._enttec_active_port = self._pick_auto_port_locked()
            if not self._enttec_active_port:
                self._enttec_error = "No USB DMX interface found - plug it in, it connects by itself"
                return False
        port = self._effective_enttec_port()
        try:
            ser = serial.Serial(  # type: ignore[name-defined]
                port=port,
                baudrate=250000,
                bytesize=serial.EIGHTBITS,  # type: ignore[name-defined]
                parity=serial.PARITY_NONE,  # type: ignore[name-defined]
                stopbits=serial.STOPBITS_TWO,  # type: ignore[name-defined]
                timeout=0.1,
            )
            self._enttec_serial = ser
            self._enttec_error = ""
            return True
        except Exception as exc:
            self._enttec_serial = None
            self._enttec_error = self._clean_serial_error(exc)
            return False

    def _close_enttec_locked(self) -> None:
        """Schliesst die serielle Verbindung (muss bereits unter _lock laufen)."""
        if self._enttec_serial is not None:
            try:
                self._enttec_serial.close()  # type: ignore[union-attr]
            except Exception:
                pass
            self._enttec_serial = None

    def reconnect_enttec(self) -> bool:
        """Manueller Reconnect: schliesst und oeffnet den seriellen Port neu (ohne gewaehlten Port: sucht den Adapter neu)."""
        if not self._enttec_enabled:
            return False
        if self._proc is not None:
            reply = self._proc.request({"cmd": "enttec_reconnect"}, timeout=4.0) or {}
            if "enttec" in reply:
                self._proc_enttec(reply["enttec"])
            return bool(reply.get("ok"))
        return self._open_enttec()

    def check_enttec_health(self) -> "str | None":
        """Prueft Verbindungsstatus und reconnectet automatisch bei Hotplug.
        Rueckgabe:
          'disconnected' - Port verschwunden, Verbindung geschlossen
          'connected'    - Port wieder erschienen, Verbindung aufgebaut
          None           - keine Aenderung
        """
        if not _SERIAL_AVAILABLE or not self._enttec_enabled:
            return None
        if self._proc is not None:
            reply = self._proc.request({"cmd": "enttec_health"}, timeout=3.0) or {}
            if "enttec" in reply:
                self._proc_enttec(reply["enttec"])
            return reply.get("event")
        try:
            available = {p.device for p in serial.tools.list_ports.comports()}  # type: ignore[name-defined]
        except Exception:
            return None
        with self._lock:
            was_connected = self._enttec_serial is not None
            if not self._enttec_port:                                         # Automatisch: Adapter kommt und geht ("Plug and Play")
                active = self._enttec_active_port
                if was_connected and active not in available:
                    self._close_enttec_locked()
                    self._enttec_active_port = ""
                    self._enttec_error = "USB DMX interface unplugged - plug it in again, it connects by itself"
                    logger.warning("[DMX] OC-3103 USB DMX: %s unplugged", active)
                    return "disconnected"
                if not was_connected and self._pick_auto_port_locked():
                    if self._open_enttec_locked():
                        logger.info("[DMX] USB DMX: %s found and connected automatically", self._enttec_active_port)
                        return "connected"
                return None
            port_available = self._enttec_port in available
            if was_connected and not port_available:
                self._close_enttec_locked()
                self._enttec_error = f"Port {self._enttec_port} is no longer available"
                logger.warning("[DMX] OC-3103 USB DMX: %s getrennt", self._enttec_port)
                return "disconnected"
            if not was_connected and port_available:
                ok = self._open_enttec_locked()
                if ok:
                    logger.info("[DMX] USB DMX: %s auto-reconnect OK", self._enttec_port)
                    return "connected"
        return None

    def _send_enttec_frame_locked(self, dmx_data: bytes) -> None:
        """Sendet einen DMX-Frame ueber USB (muss bereits unter _lock laufen)."""
        if self._enttec_serial is None:
            return
        try:
            frame = _build_enttec_frame(dmx_data)
            self._enttec_serial.write(frame)  # type: ignore[union-attr]
            self._enttec_error = ""
        except Exception as exc:
            self._enttec_error = self._clean_serial_error(exc)
            logger.warning("[DMX] OC-3103 USB DMX: Send error on %s — %s", self._effective_enttec_port(), self._enttec_error)
            # Verbindung als verloren markieren; naechster set_enttec_enabled
            # oder manueller Refresh oeffnet sie neu.
            self._close_enttec_locked()

    # ------------------------------------------------------------------
    # Universe-Verwaltung
    # ------------------------------------------------------------------
    def _artnet_targets(self) -> Tuple[str, Tuple[str, ...]]:
        """(Hauptziel, weitere Ziele): bei "Automatisch" die gefundenen Geraete (oder der Broadcast, solange keines antwortet), sonst die eingestellte Adresse."""
        if self._artnet_target_ip == AUTO:
            targets = self._artnet_auto_targets or list(ARTNET_FALLBACK_TARGETS)
            return targets[0], tuple(targets[1:])
        return self._artnet_target_ip, ()

    def _apply_artnet_targets_locked(self) -> None:
        primary, extras = self._artnet_targets()
        for sender in self._artnet_senders.values():
            sender.target_ip = primary
            sender.extra_targets = extras

    def set_artnet_auto_targets(self, ips: List[str]) -> None:
        """Betrieb "Automatisch": die Liste der gefundenen Geraete hat sich geaendert (app/artnet_discovery.py) - sofort uebernehmen."""
        with self._lock:
            self._artnet_auto_targets = list(ips) or list(ARTNET_FALLBACK_TARGETS)
            if self._artnet_target_ip == AUTO:
                self._apply_artnet_targets_locked()
                if self._proc is not None:
                    self._sync_proc()

    def get_artnet_status(self) -> dict:
        primary, extras = self._artnet_targets()
        return {"enabled": self._artnet_enabled, "auto": self._artnet_target_ip == AUTO, "targets": [primary, *extras]}

    def _create_artnet_sender(self, universe: int) -> StupidArtnet:
        primary, extras = self._artnet_targets()
        kwargs: Dict[str, object] = dict(
            target_ip=primary,
            universe=universe,
            packet_size=DMX_UNIVERSE_SIZE,
            fps=OUTPUT_FPS,
            even_packet_size=True,
            broadcast=True,
        )
        if self._artnet_bind_ip:
            kwargs["source_address"] = (self._artnet_bind_ip, 0)
        sender = _MultiArtnet(**kwargs)  # type: ignore[arg-type]
        sender.extra_targets = extras
        sender.start()
        return sender

    def _ensure_universe(self, universe: int) -> None:
        """Legt Puffer + Sender fuer ein Universum an, falls noch nicht vorhanden."""
        if universe in self._buffers:
            return

        self._buffers[universe] = bytearray(DMX_UNIVERSE_SIZE)
        if self._proc is not None:                                                  # Ausgabe-Prozess: nur den Platz im gemeinsamen Speicher anlegen
            self._proc.publish(universe, bytes(self._buffers[universe]))
            return

        # sACN-Ausgang aktivieren (Multicast, spec-konform) - bleibt bestehen
        # auch wenn sACN gerade deaktiviert ist, damit ein spaeteres
        # Wieder-Aktivieren ohne Neuaufbau sofort funktioniert. Ist sACN noch nie
        # eingeschaltet worden, gibt es den Sender gar nicht (kein Netzwerk-Socket).
        if self._sacn_enabled or self._sacn_sender is not None:
            self._ensure_sacn_locked()

        self._artnet_senders[universe] = self._create_artnet_sender(universe)

    def _push_universe_locked(self, universe: int) -> None:
        """Sendet den aktuellen Puffer eines Universums an alle gerade
        aktivierten Protokolle. Muss unter self._lock aufgerufen werden."""
        payload = bytes(self._buffers[universe])
        if self._proc is not None:
            self._proc.publish(universe, payload)
            return
        if self._sacn_enabled:
            self._ensure_sacn_locked()
            self._sacn_sender[universe].dmx_data = payload
        if self._artnet_enabled:
            self._artnet_senders[universe].set(bytearray(payload))
        if self._enttec_enabled and universe == self._enttec_universe:
            self._send_enttec_frame_locked(payload)

    # ------------------------------------------------------------------
    # Schreib-API
    # ------------------------------------------------------------------
    def set_channel(self, universe: int, channel: int, value: int) -> None:
        """Setzt einen einzelnen DMX-Kanal. channel ist 1-indiziert (1-512)."""
        self.set_channels(universe, channel, [value])

    def set_channels(self, universe: int, start_channel: int, values: List[int]) -> None:
        """Setzt einen Kanalblock ab start_channel (1-indiziert) und sendet ihn raus."""
        if not self._started:
            self.start()

        changed = False
        with self._lock:
            self._ensure_universe(universe)
            buf = self._buffers[universe]
            for offset, value in enumerate(values):
                index = start_channel - 1 + offset
                if 0 <= index < DMX_UNIVERSE_SIZE:
                    new = max(0, min(255, int(value)))
                    if buf[index] != new:
                        buf[index] = new
                        changed = True
            self._push_universe_locked(universe)
        if changed:
            self._notify(universe)

    def set_channels_batch(self, universe: int, channels: Dict[int, int]) -> None:
        """Setzt mehrere Kanaele in einem Batch (channel 1-indiziert -> Wert 0-255)
        und sendet den Frame EINMALIG am Ende - effizienter als wiederholtes set_channel()."""
        if not self._started:
            self.start()
        changed = False
        with self._lock:
            self._ensure_universe(universe)
            buf = self._buffers[universe]
            for channel, value in channels.items():
                idx = channel - 1
                if 0 <= idx < DMX_UNIVERSE_SIZE:
                    new = max(0, min(255, int(value)))
                    if buf[idx] != new:
                        buf[idx] = new
                        changed = True
            self._push_universe_locked(universe)
        if changed:
            self._notify(universe)

    def blackout(self, universe: Optional[int] = None) -> None:
        """Setzt alle Kanaele (oder nur ein einzelnes Universum) auf 0."""
        notified = []
        with self._lock:
            targets = [universe] if universe is not None else list(self._buffers.keys())
            for uni in targets:
                if uni not in self._buffers:
                    continue
                self._buffers[uni] = bytearray(DMX_UNIVERSE_SIZE)
                self._push_universe_locked(uni)
                notified.append(uni)
        for uni in notified:
            self._notify(uni)

    def universe_numbers(self) -> List[int]:
        with self._lock:
            return sorted(self._buffers.keys())

    def get_universe_snapshot(self, universe: int) -> List[int]:
        """Aktuelle Kanalwerte eines Universums - z.B. fuer Level-Meter im UI."""
        with self._lock:
            buf = self._buffers.get(universe)
            return list(buf) if buf is not None else [0] * DMX_UNIVERSE_SIZE

    # ------------------------------------------------------------------
    # Dynamische Konfiguration (Settings-Modal -> DMX/Network, live)
    # ------------------------------------------------------------------
    def set_artnet_enabled(self, enabled: bool) -> None:
        enabled = bool(enabled)
        with self._lock:
            if enabled == self._artnet_enabled:
                return
            if self._proc is not None:
                self._artnet_enabled = enabled                                     # der Ausgabe-Prozess verstummt selbst sauber (eine Sekunde Nullen, dann Stille)
                self._sync_proc()
                return
            if not enabled:
                # sauber verstummen statt einfach aufzuhoeren zu senden -
                # sonst bleibt bei den Empfaengern der zuletzt gesendete,
                # ggf. nicht-schwarze Wert dauerhaft stehen.
                for sender in self._artnet_senders.values():
                    sender.set(bytearray(_BLACKOUT_BYTES))
                self._artnet_enabled = False
                self._artnet_quiet_until = time.monotonic() + 1.0                # eine Sekunde lang Nullen, dann Stille (frueher: dauerhaft Nullen)
            else:
                self._artnet_enabled = True
                for universe, sender in self._artnet_senders.items():
                    sender.set(bytearray(self._buffers[universe]))

    def set_sacn_enabled(self, enabled: bool) -> None:
        enabled = bool(enabled)
        with self._lock:
            if enabled == self._sacn_enabled:
                return
            if self._proc is not None:
                self._sacn_enabled = enabled
                self._sync_proc()
                return
            if not enabled:
                if self._sacn_sender is not None:
                    for universe in self._buffers:
                        self._sacn_sender[universe].dmx_data = _BLACKOUT_BYTES
                self._sacn_enabled = False
            else:
                self._sacn_enabled = True
                if self._started:
                    self._ensure_sacn_locked()                       # erst jetzt entsteht der Sender (und die Firewall-Frage, falls sie noch nie kam)
                    for universe, buf in self._buffers.items():
                        self._sacn_sender[universe].dmx_data = bytes(buf)

    def set_artnet_target_ip(self, ip: str) -> None:
        """Wirkt sofort - stupidArtnet liest target_ip bei jedem Sendezyklus
        neu, ein Neuaufbau der Sender/Sockets ist nicht noetig."""
        with self._lock:
            self._artnet_target_ip = ip
            self._apply_artnet_targets_locked()
            if self._proc is not None:
                self._sync_proc()

    # ------------------------------------------------------------------
    # Enttec USB DMX - oeffentliche API
    # ------------------------------------------------------------------
    def set_enttec_enabled(self, enabled: bool) -> str:
        """Aktiviert/deaktiviert den Enttec-USB-Ausgang. Gibt Fehlerstring zurueck (leer = OK)."""
        enabled = bool(enabled)
        if self._proc is not None:
            self._enttec_enabled = enabled
            if not enabled:
                self._enttec_error = ""
            self._sync_proc(wait=True)
            return self._enttec_error if enabled else ""
        with self._lock:
            self._enttec_enabled = enabled
            if enabled:
                self._open_enttec_locked()                                    # ohne gewaehlten Port: Automatik (angesteckten Adapter suchen)
            else:
                self._close_enttec_locked()
                self._enttec_error = ""
        return self._enttec_error

    def set_enttec_port(self, port: str) -> str:
        """Setzt den COM-Port und reconnectet. Gibt Fehlerstring zurueck (leer = OK)."""
        if self._proc is not None:
            self._enttec_port = port or ""
            self._enttec_active_port = ""
            self._sync_proc(wait=True)
            return self._enttec_error
        with self._lock:
            self._enttec_port = port or ""
            self._enttec_active_port = ""
            if self._enttec_enabled:
                self._open_enttec_locked()
            else:
                self._enttec_error = ""
        return self._enttec_error

    def set_enttec_universe(self, universe: int) -> None:
        """Setzt das DMX-Universum, das an den USB-Adapter gesendet wird."""
        with self._lock:
            self._enttec_universe = max(1, int(universe))
            if self._proc is not None:
                self._sync_proc()

    def get_enttec_status(self) -> dict:
        """Gibt den aktuellen Verbindungsstatus des Enttec-Adapters zurueck."""
        connected = (self._enttec_serial is not None) if self._proc is None else bool(getattr(self, "_enttec_connected_remote", False))
        return {
            "available": _SERIAL_AVAILABLE,
            "enabled": self._enttec_enabled,
            "port": self._effective_enttec_port(),
            "auto": not self._enttec_port,
            "detected": [str(d["device"]) for d in self.detect_usb_dmx()],
            "universe": self._enttec_universe,
            "connected": connected,
            "error": self._enttec_error,
        }

    @staticmethod
    def scan_enttec_ports() -> List[str]:
        """Gibt alle verfuegbaren seriellen Ports zurueck (fuer COM-Port-Dropdown)."""
        if not _SERIAL_AVAILABLE:
            return []
        try:
            return sorted(p.device for p in serial.tools.list_ports.comports())  # type: ignore[name-defined]
        except Exception:
            return []

    def set_artnet_bind_ip(self, ip: str) -> None:
        """Die Bind-/Sende-Interface-Adresse ist nur beim Socket-Aufbau
        wirksam - ein Wechsel baut deshalb alle aktiven Art-Net-Sender neu
        auf. Der aktuelle Pufferinhalt wird sofort auf die neuen Sender
        uebertragen, damit der Wechsel keinen sichtbaren Blackout verursacht.
        """
        with self._lock:
            self._artnet_bind_ip = ip
            if self._proc is not None:
                self._sync_proc()
                return
            old_senders: Dict[int, StupidArtnet] = dict(self._artnet_senders)
            if not old_senders:
                return
            for sender in old_senders.values():
                sender.stop()
            time.sleep(2.0 / OUTPUT_FPS)  # siehe shutdown() fuer die Begruendung
            for universe, old_sender in old_senders.items():
                old_sender.close()
                new_sender = self._create_artnet_sender(universe)
                new_sender.set(bytearray(self._buffers[universe]))
                self._artnet_senders[universe] = new_sender


# Einzige, global geteilte Instanz - von server.py importiert und gestartet
dmx_engine = DMXEngine()
