"""
cue_engine.py
Cue-Execution-Engine von OpenCue.

Verarbeitet "Go"/"Back"-Trigger (sowie den direkten Sprung zu einem
beliebigen Cue, siehe jump_to()) und berechnet weiche Ueberblendungen
(Fades) zwischen dem zuletzt aktiven Fixture-Zustand und dem neuen
Ziel-Cue - statt hart umzuschalten. Laeuft als eigener asyncio-Task mit
fester Tick-Rate (FADE_FPS), unabhaengig vom DMX-Sendetakt der DMXEngine
(dmx_engine.py OUTPUT_FPS), steuert diese aber ueber dieselbe Instanz an
(set_channels_batch()) - die Kopplung an dmx_engine ist damit bewusst
einseitig (cue_engine -> dmx_engine), um einen Zirkelimport zu vermeiden
(dmx_engine.py kennt cue_engine.py nicht).

ATTRIBUT-ZEITEN (dot2-Stil): Ein Cue traegt eine allgemeine `fade`/`delay`-
Zeit (= Dimmer-Zeit) sowie optional eigene Zeiten je Attributgruppe
(fade_color/delay_color, fade_pos/delay_pos, fade_beam/delay_beam, fade_zoom/delay_zoom). Ist
eine gruppenspezifische Zeit nicht gesetzt (None), wird die allgemeine
fade/delay-Zeit verwendet (siehe _group_timing()). `delay` + `trigger`
steuern daneben weiterhin die automatische Cue-Verkettung: ist der auf
einen fertig gefadeten Cue FOLGENDE Cue in der Liste mit trigger ==
"follow" markiert, wartet die Engine dessen `delay` Sekunden ab und loest
ihn danach automatisch selbst aus (_maybe_follow).

MIB (Move In Black): Das MIB-Feld steht an dem Cue, in dem die Fixture sichtbar an ihre neue Position
kommt - gefahren wird aber schon VORHER, im Dunkeln:
  1. Vorlauf (Hauptfall): Beim Start eines Cues schaut die Engine auf den FOLGENDEN Cue der Liste. Hat dieser
     mib "Auto" (Fixture geht dort von dunkel auf an) oder "On" und ist die Fixture am Ende des laufenden Cues
     dunkel (Dimmer ~0 %), werden Position/Farbe/Beam/Rad-Kanaele des Folge-Cues schon jetzt angefahren: sofort,
     wenn die Fixture ohnehin dunkel ist, sonst sobald ihr Dimmer in diesem Cue (Delay + Fade) auf 0 angekommen
     ist. Beim Go auf den Folge-Cue steht sie dann schon dort und nur noch der Dimmer faedet auf.
  2. Fallback im Cue selbst: Kam der Vorlauf nicht zum Zug (Sprung auf den Cue, Go vor dem Dunkelwerden), werden
     Position/Farbe/Beam beim Einschalten SOFORT (ohne Fade) gesetzt, waehrend der Dimmer regulaer hochfaedet.
     "On" erzwingt das immer (auch wenn der Dimmer schon an war), "Off" deaktiviert beides.
Laeuft auf der Fixture ein Effekt der jeweiligen Kategorie, wird sie nicht vorpositioniert.

Kopplung zu server.py: Die Engine kennt StateManager (state) und DMXEngine
(dmx_engine) direkt, aber NICHT den WebSocket-EventBus (sonst zirkulaerer
Import). server.py registriert stattdessen zwei async Callbacks:
  - set_update_callback(): nach jedem Fade-Tick (DMX-Output + Live-Werte)
  - set_cuelists_changed_callback(): wann immer sich der aktive-Cue-Status
    aendert (Go/Back/jump_to UND der automatische Follow-Trigger) - damit
    auch ein von der Engine selbst ausgeloester Folge-Cue sofort sichtbar wird.

Interpoliert wird im ABSTRAKTEN Werteraum (dimmer/pan/tilt/beam 0-100%,
color 0-255 RGB) statt auf rohem DMX-Byte-Level - das ist exakt das
Format, das das Frontend fuer die Live-Fader-/Color-Picker-
Synchronisation braucht (siehe dmx_resolve.py), und wird pro Tick ueber
apply_abstract_values() in DMX-Kanalschreibvorgaenge aufgeloest.
"""

from __future__ import annotations

import asyncio
import copy
import time
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, Optional, Set, Tuple

from app.fx_engine import ATTR_CATEGORY, CATEGORY_ATTRS, fx_engine
from app.dmx_resolve import (
    DISCRETE_ATTRS,
    apply_abstract_values,
    current_abstract_values,
    fixture_channel_offsets,
    preset_to_abstract,
    raw_offset,
)

FADE_FPS = 40  # Hz - unabhaengig vom DMX-Output-Takt (siehe dmx_engine.OUTPUT_FPS)
FADE_INTERVAL = 1.0 / FADE_FPS

_SCALAR_ATTRS = ("dimmer", "pan", "tilt", "strobe", "gobo", "gobo_spin", "gobo2", "gobo2_spin", "prism", "focus", "zoom")

# Abstraktes Attribut -> Attributgruppe (bestimmt, welche Cue-Fade/Delay-
# Zeit gilt - siehe _group_timing()). "color" wird separat behandelt
# (kein Eintrag in _SCALAR_ATTRS), gehoert aber ebenfalls zur "color"-Gruppe.
_ATTR_GROUPS: Dict[str, str] = {
    "dimmer": "dimmer",
    "pan": "pos",
    "tilt": "pos",
    "strobe": "beam",
    "gobo": "beam",
    "gobo_spin": "beam",
    "gobo2": "beam",
    "gobo2_spin": "beam",
    "prism": "beam",
    "focus": "beam",
    "zoom": "zoom",
}

_MIB_DARK_THRESHOLD = 1.0  # % - Schwellwert fuer "praktisch dunkel" (MIB "Auto")


def _default_scalar(attr: str) -> float:
    """Default-Startwert fuer ein Attribut ohne bisherige Fixture.values-
    Historie - identisch zu den Defaults in preset_to_abstract()."""
    return 50.0 if attr in ("pan", "tilt") else 0.0


def _should_apply_mib(mib: str, current_dimmer: float, target_dimmer: Optional[float]) -> bool:
    """"On" erzwingt MIB immer, "Auto" nur beim Einschalten aus (praktisch)
    dunklem Zustand, "Off" nie."""
    mib = (mib or "Off").strip().lower()
    if mib == "on":
        return True
    if mib == "auto":
        return (
            current_dimmer <= _MIB_DARK_THRESHOLD
            and target_dimmer is not None
            and target_dimmer > _MIB_DARK_THRESHOLD
        )
    return False


@dataclass
class _FixtureFade:
    """Start- und Zielwerte EINER Fixture fuer die laufende Ueberblendung."""

    scalars_from: Dict[str, float] = field(default_factory=dict)
    scalars_to: Dict[str, float] = field(default_factory=dict)
    color_from: Optional[Dict[str, float]] = None
    color_to: Optional[Dict[str, float]] = None
    # Rohe Kanaele ("ch<Offset>", Byte): werden nie ueberblendet, sondern mit dem Beginn der Beam-Zeit (nach dem Delay) umgeschaltet
    raw_from: Dict[str, float] = field(default_factory=dict)
    raw_to: Dict[str, float] = field(default_factory=dict)
    # MIB-Snap: Position/Farbe/Beam dieser Fixture werden sofort (t=1.0)
    # angewandt statt ueber die Gruppen-Fade-Zeit zu interpolieren - der
    # Dimmer selbst ist davon NICHT betroffen (faedet weiterhin regulaer).
    mib_snap: bool = False
    # MIB-Vorlauf: Werte des FOLGENDEN Cues, die ab `premove_after` Sekunden (nach Start dieses Cues) sofort angefahren werden,
    # weil die Fixture dann dunkel ist.
    premove_to: Dict[str, Any] = field(default_factory=dict)
    premove_after: float = 0.0


@dataclass
class _Transition:
    cuelist_id: str
    cue_id: str
    started_at: float
    total_duration: float  # max(delay+duration) ueber alle Gruppen - fuer Fortschrittsanzeige/Abschluss
    group_timing: Dict[str, Tuple[float, float]]  # Gruppe -> (delay, duration) in Sekunden
    fixtures: Dict[str, _FixtureFade]
    allow_follow: bool  # False bei "Back" - Rueckwaertsspringen verkettet nicht automatisch weiter
    paused_at: Optional[float] = None  # monotonic-Zeitpunkt der Pause; None = laeuft


class CueEngine:
    """Fuehrt pro CueList maximal eine laufende Ueberblendung gleichzeitig aus."""

    def __init__(self, state, dmx_engine) -> None:
        self._state = state
        self._dmx = dmx_engine
        self._transitions: Dict[str, _Transition] = {}  # cuelist_id -> laufende Transition
        # cuelist_id -> (cue_id, Fortschritt): per Stop angehaltene Ueberblendung. Der Balken bleibt dort
        # stehen (statt auf "vollstaendig geladen" zu springen), bis ein neuer Cue gestartet wird.
        self._stopped: Dict[str, Tuple[str, float]] = {}
        self._follow_tasks: Dict[str, asyncio.Task] = {}  # cuelist_id -> wartender Follow-Trigger
        # cuelist_id -> (Follow-Cue, Start monotonic, Delay s): laeuft gerade der Follow-Delay vor dem naechsten Cue
        self._follow_wait: Dict[str, Tuple[str, float, float]] = {}
        self._task: Optional[asyncio.Task] = None
        self._on_playback: Optional[Callable[[Dict[str, Any]], None]] = None
        self._on_update: Optional[Callable[[Dict[str, Any]], Any]] = None
        self._on_cuelists_changed: Optional[Callable[[], Awaitable[None]]] = None
        self._on_broadcast: Optional[Callable[[str, Dict[str, Any]], Awaitable[None]]] = None
        self._on_command_log: Optional[Callable[[str, Dict[str, Any]], Awaitable[None]]] = None

    def set_update_callback(self, fn: Callable[[Dict[str, Any]], Any]) -> None:
        """fn({"universes": set[int], "values": {fx_id: abstract}}) wird nach jedem Tick einer
        laufenden Transition aufgerufen (die Live-Werte fuer Fader/Monitor der Oberflaeche).
        fn MUSS schnell zurueckkehren: Das DMX-Signal hat Vorrang, die Engine wartet nicht auf
        Netzwerk-Clients (der Server reicht die Daten nur an einen eigenen Sender-Task weiter).
        Ein Coroutine-Callback wird weiterhin awaited."""
        self._on_update = fn

    def set_playback_callback(self, fn: Callable[[Dict[str, Any]], None]) -> None:
        """fn(payload) bei jedem Wechsel des Wiedergabezustands einer Liste (Start, Pause, Weiter,
        Stopp, Ende): {"cuelist_id", "cue_id", "progress", "remaining", "state"}. Die Oberflaeche
        animiert den Ladebalken allein daraus (eine CSS-Transition ueber "remaining" Sekunden) -
        es sind keine Fortschritts-Ticks mehr noetig. Synchron und nicht blockierend."""
        self._on_playback = fn

    def set_cuelists_changed_callback(self, fn: Callable[[], Awaitable[None]]) -> None:
        """fn() wird awaited, wann immer die Engine selbststaendig (ohne
        direkten WS-Request) den aktiven Cue wechselt - aktuell nur der
        automatische Follow-Trigger (siehe _maybe_follow)."""
        self._on_cuelists_changed = fn

    def set_broadcast_callback(self, fn: Callable[[str, Dict[str, Any]], Awaitable[None]]) -> None:
        """fn(message_type, payload) - generischer Broadcast-Kanal, den die
        automatische CMD-Ausfuehrung eines Cues (siehe _run_cue_cmd) an
        app.command_line.execute_command() durchreicht (identische Signatur
        wie der "run_command"-WS-Handler in server.py)."""
        self._on_broadcast = fn

    def set_command_log_callback(self, fn: Callable[[str, Dict[str, Any]], Awaitable[None]]) -> None:
        """fn(command, result) - meldet das Ergebnis einer automatischen
        CMD-Ausfuehrung (Cue.cmd) an denselben Log-Broadcast wie ein manuell
        in der Command Line eingegebener Befehl (siehe server.py)."""
        self._on_command_log = fn

    def start(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._run())

    def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            self._task = None

    async def _run(self) -> None:
        # Feste Zielzeiten statt "sleep nach jeder Arbeit": die Dauer eines Ticks addiert sich
        # nicht mehr auf den Takt (vorher ~47 ms statt 25 ms zwischen zwei DMX-Frames).
        try:
            next_tick = time.monotonic()
            while True:
                next_tick += FADE_INTERVAL
                delay = next_tick - time.monotonic()
                if delay < -0.25:            # nach einem langen Stillstand nicht im Eiltempo aufholen
                    next_tick = time.monotonic()
                    delay = 0.0
                await asyncio.sleep(max(0.0, delay))
                await self._tick()
        except asyncio.CancelledError:
            pass

    # ------------------------------------------------------------------
    async def trigger(self, cuelist_id: str, direction: int):
        """direction=+1 (Go) oder -1 (Back). Berechnet den neuen aktiven Cue
        ueber state.step_cue() und startet eine Ueberblendung dorthin - mit
        dessen eigenen Attribut-Zeiten, unabhaengig von der Richtung. Gibt
        den neuen aktiven Cue zurueck (oder None, falls kein Schritt
        moeglich war) - der Aufrufer broadcastet darauf cuelists_changed."""
        cue = self._state.step_cue(cuelist_id, direction)
        if cue is None:
            return None
        await self._start(cuelist_id, cue, allow_follow=(direction >= 0))
        return cue

    async def jump_to(self, cuelist_id: str, cue_id: str):
        """Springt direkt zu einem beliebigen Cue der Liste (Rechtsklick ->
        "Hierhin faden") - unabhaengig vom aktuell aktiven Cue, mit dessen
        eigenen Attribut-Zeiten. Gibt den Cue zurueck (oder None, falls
        CueList/Cue nicht existiert)."""
        cl = self._state.cuelists.get(cuelist_id)
        if cl is None:
            return None
        cue = next((c for c in cl.cues if c.id == cue_id), None)
        if cue is None:
            return None
        self._state.active_cue_ids[cuelist_id] = cue.id
        await self._start(cuelist_id, cue, allow_follow=True)
        return cue

    def reset(self) -> None:
        """Verwirft laufende Ueberblendungen (Show wurde gewechselt). Ohne das schreibt eine
        Transition der alten Show weiter in die DMX-Ausgabe der neuen."""
        self._transitions.clear()
        self._stopped.clear()
        self._follow_wait.clear()
        for task in self._follow_tasks.values():
            task.cancel()
        self._follow_tasks.clear()

    # ------------------------------------------------------------------
    # Wiedergabezustand (Fortschritt, Pause, Stopp)
    # ------------------------------------------------------------------
    def _playback_payload(self, cuelist_id: str) -> Optional[Dict[str, Any]]:
        """Zustand der Liste: running | paused | stopped | done. "remaining" ist die Restzeit der
        Ueberblendung in Sekunden (0 bei done/stopped/paused-ohne-Fortsetzung); der Client rechnet
        daraus eine einzige lineare Animation, die auch ohne weitere Nachrichten fluessig laeuft."""
        cue_id = self._state.active_cue_ids.get(cuelist_id)
        if cue_id is None:
            return None
        transition = self._transitions.get(cuelist_id)
        if transition is not None and transition.cue_id == cue_id:
            now = transition.paused_at if transition.paused_at is not None else time.monotonic()
            elapsed = max(0.0, now - transition.started_at)
            total = transition.total_duration
            progress = 1.0 if total <= 0 else max(0.0, min(1.0, elapsed / total))
            remaining = max(0.0, total - elapsed)
            state = "paused" if transition.paused_at is not None else "running"
            return {"cuelist_id": cuelist_id, "cue_id": cue_id, "progress": progress,
                    "remaining": remaining, "state": state}
        stopped = self._stopped.get(cuelist_id)
        if stopped is not None and stopped[0] == cue_id:
            return {"cuelist_id": cuelist_id, "cue_id": cue_id, "progress": stopped[1],
                    "remaining": 0.0, "state": "stopped"}
        payload = {"cuelist_id": cuelist_id, "cue_id": cue_id, "progress": 1.0, "remaining": 0.0, "state": "done"}
        wait = self._follow_wait.get(cuelist_id)
        if wait is not None:
            # Follow-Delay des unmittelbar folgenden Cues laeuft: Restzeit fuer dessen Zeile (eine Stufe voraus)
            remaining = max(0.0, wait[2] - (time.monotonic() - wait[1]))
            payload["follow"] = {"cue_id": wait[0], "remaining": remaining, "duration": wait[2]}
        return payload

    def _emit_playback(self, cuelist_id: str) -> None:
        if self._on_playback is None:
            return
        payload = self._playback_payload(cuelist_id)
        if payload is not None:
            self._on_playback(payload)

    def playback_snapshot(self) -> Dict[str, Dict[str, Any]]:
        """cuelist_id -> Wiedergabezustand aller Listen mit aktivem Cue (neue/wiederverbundene Clients,
        cuelists_changed): der Balken steht sofort richtig und laeuft an der richtigen Stelle weiter."""
        result: Dict[str, Dict[str, Any]] = {}
        for cuelist_id in list(self._state.active_cue_ids):
            payload = self._playback_payload(cuelist_id)
            if payload is not None:
                result[cuelist_id] = payload
        return result

    def progress_snapshot(self) -> Dict[str, float]:
        """cue_id -> Fortschritt (0.0-1.0) der aktiven Cues (Kompatibilitaet; siehe playback_snapshot)."""
        return {p["cue_id"]: p["progress"] for p in self.playback_snapshot().values()}

    # ------------------------------------------------------------------
    # Pause / Weiter / Stopp
    # ------------------------------------------------------------------
    def pause(self, cuelist_id: str) -> bool:
        """Friert die laufende Ueberblendung auf dem aktuellen Wert ein (die zuletzt gesendeten DMX-Werte
        bleiben stehen). Mit resume() geht es an derselben Stelle weiter."""
        transition = self._transitions.get(cuelist_id)
        if transition is None or transition.paused_at is not None:
            return False
        transition.paused_at = time.monotonic()
        self._emit_playback(cuelist_id)
        return True

    def resume(self, cuelist_id: str) -> bool:
        transition = self._transitions.get(cuelist_id)
        if transition is None or transition.paused_at is None:
            return False
        transition.started_at += time.monotonic() - transition.paused_at   # Pausenzeit zaehlt nicht mit
        transition.paused_at = None
        self._emit_playback(cuelist_id)
        return True

    def stop(self, cuelist_id: str) -> bool:
        """Bricht die laufende (oder pausierte) Ueberblendung ab: die Werte bleiben auf dem erreichten
        Stand stehen, der Cue bleibt aktiv, ein wartender Follow-Trigger entfaellt. Mit Go geht es zum
        naechsten Cue weiter. Gibt False zurueck, wenn nichts lief."""
        stopped_something = False
        transition = self._transitions.pop(cuelist_id, None)
        if transition is not None:
            now = transition.paused_at if transition.paused_at is not None else time.monotonic()
            total = transition.total_duration
            progress = 1.0 if total <= 0 else max(0.0, min(1.0, (now - transition.started_at) / total))
            self._stopped[cuelist_id] = (transition.cue_id, progress)
            stopped_something = True
        task = self._follow_tasks.pop(cuelist_id, None)
        self._follow_wait.pop(cuelist_id, None)
        if task is not None and not task.done():
            task.cancel()
            stopped_something = True
        if stopped_something:
            self._emit_playback(cuelist_id)
        return stopped_something

    def forget(self, cuelist_id: str) -> None:
        """Die Liste wird geloescht: Ueberblendung, Stopp-Merker und wartender Follow-Trigger entfallen. Die zuletzt
        ausgegebenen DMX-Werte bleiben stehen (nichts springt)."""
        self._transitions.pop(cuelist_id, None)
        self._stopped.pop(cuelist_id, None)
        self._cancel_follow(cuelist_id)

    def _cancel_follow(self, cuelist_id: str) -> None:
        self._follow_wait.pop(cuelist_id, None)
        task = self._follow_tasks.pop(cuelist_id, None)
        if task is not None and not task.done() and task is not asyncio.current_task():
            task.cancel()

    @staticmethod
    def _group_timing(cue) -> Dict[str, Tuple[float, float]]:
        """(delay, duration) je Attributgruppe - attributspezifische Zeiten
        (fade_color/_pos/_beam/_zoom, delay_color/_pos/_beam/_zoom) werden bevorzugt,
        sonst faellt die Gruppe auf die allgemeine fade/delay-Zeit zurueck.
        "dimmer" hat keine eigene Override-Option und nutzt daher immer
        die allgemeinen Zeiten direkt."""

        def _pick(fade_override: Optional[float], delay_override: Optional[float]) -> Tuple[float, float]:
            fade = fade_override if fade_override is not None else cue.fade
            delay = delay_override if delay_override is not None else cue.delay
            return (max(0.0, float(delay)), max(0.0, float(fade)))

        return {
            "dimmer": _pick(None, None),
            "pos": _pick(cue.fade_pos, cue.delay_pos),
            "color": _pick(cue.fade_color, cue.delay_color),
            "beam": _pick(cue.fade_beam, cue.delay_beam),
            "zoom": _pick(cue.fade_zoom, cue.delay_zoom),
        }

    async def _start(self, cuelist_id: str, cue, *, allow_follow: bool) -> None:
        """Baut die Fade-Ziele fuer alle Fixtures eines Cues (inkl. Live-
        Aufloesung von Preset-UUIDs, Attribut-Gruppen-Zeiten und MIB) und
        startet die Ueberblendung. Fuehrt sofort den ersten Tick aus - bei
        einer Gesamtdauer von 0s ist der Cue damit beim Rueckgabezeitpunkt
        bereits vollstaendig angewandt, sonst ist das der erste (kaum
        wahrnehmbare) Frame, den der Hintergrund-Loop fortsetzt."""
        # Cue.cmd IMMER ausfuehren (auch wenn der Cue keine Fixture-Werte
        # traegt, z.B. ein reiner "Store Cue 5"-Trigger-Cue) - deshalb VOR
        # dem "keine Fixtures" Fruehausstieg weiter unten.
        await self._run_cue_cmd(cue)

        # Neuer Cue: eine angehaltene/wartende Wiedergabe der Liste ist damit erledigt.
        self._stopped.pop(cuelist_id, None)
        self._cancel_follow(cuelist_id)

        group_timing = self._group_timing(cue)
        fixtures: Dict[str, _FixtureFade] = {}
        released_any = False
        cue_fx = cue.fx or {}

        # 1) Ziele bestimmen und laufende Effekte der Cue-Attribute genau JETZT einfrieren.
        #    Der eingefrorene Wert (fade_start_value) ist der Startpunkt der Ueberblendung.
        #    Das muss vor Schritt 2 passieren: dort wird sonst der Effekt ohne Wert beendet.
        pending: Dict[str, Tuple[Any, Dict[str, Any], Dict[str, Any]]] = {}
        refs_dropped = False
        for fx_id, step in cue.fixture_values.items():
            fx = self._state.fixtures.get(fx_id)
            if fx is None:
                continue
            target = self._state.step_values(step)               # feste Werte + live aufgeloeste Variablen
            # Kategorien mit Cue-Effekt werden nicht zusaetzlich statisch ueberblendet.
            fx_blocked = fx_engine.attrs_of_effects(cue_fx.get(fx_id, {}))          # nur Attribute, die der Effekt wirklich steuert (pan-Effekt: tilt bleibt statisch)
            target = {k: v for k, v in target.items() if k not in fx_blocked}
            if not target:
                continue
            fade_start_value, fx_released = fx_engine.release_for_cue(fx_id, target.keys())
            released_any = released_any or fx_released
            refs_dropped = self._state.drop_programmer_refs(fx_id, target.keys()) or refs_dropped       # der Cue gibt diese Attribute jetzt vor, nicht mehr eine Variable im Programmer
            pending[fx_id] = (fx, target, fade_start_value)

        if refs_dropped and self._on_broadcast is not None:
            await self._on_broadcast("programmer_refs", {"refs": self._state.programmer_refs_payload()})

        # 2) Kategorien ohne Cue-Effekt verlieren ihre laufenden Effekte sofort.
        #    Cue-Effekte starten erst nach dem Ueberblend-Setup.
        for fid in set(cue.fixture_values) | set(cue_fx):
            missing = set(CATEGORY_ATTRS) - set(cue_fx.get(fid, {}))
            released_any = fx_engine.release_categories(fid, missing, fade_out=cue.fx_fade_out) or released_any

        # 3) Ueberblendungs-Ziele aufbauen, Start = eingefrorener Effektwert.
        for fx_id, (fx, target, fade_start_value) in pending.items():
            current = {**current_abstract_values(fx), **fade_start_value}
            raw_now = self._raw_current(fx, target)
            current.update(raw_now)
            # Executor-Fader (Mix): die Liste "besitzt" diese Attribute. Der manuelle Wert (Programmer-Wert, sonst der Stand
            # vor dem ersten Cue) bleibt als Basis, auf die der Fader bei 0 % faellt; ueberblendet wird die Cue-SCHICHT
            # (ungemischt), die Ausgabe ist Mix(Basis, Cue-Schicht, Fader).
            layer = self._state.cue_layer.setdefault(cuelist_id, {}).setdefault(fx_id, {})
            base = self._state.cue_base.setdefault(cuelist_id, {}).setdefault(fx_id, {})
            programmer = self._state.programmer_values.get(fx_id, {})
            for attr in target:
                if attr not in layer:
                    manual = programmer.get(attr)
                    if manual is None:
                        manual = current.get(attr)
                    base[attr] = copy.deepcopy(manual) if manual is not None else self._state._neutral_value(attr)
            fade = _FixtureFade()
            for attr in _SCALAR_ATTRS:
                if attr in target:
                    fade.scalars_to[attr] = float(target[attr])
                    fade.scalars_from[attr] = float(layer[attr] if attr in layer else current.get(attr, _default_scalar(attr)))
            for attr in target:
                if raw_offset(attr) is not None:
                    fade.raw_to[attr] = float(target[attr])
                    fade.raw_from[attr] = float(layer[attr] if attr in layer else raw_now.get(attr, 0.0))
            if "color" in target:
                to_c = target["color"]
                from_c = layer.get("color") or current.get("color") or {"r": 0, "g": 0, "b": 0}
                fade.color_to = {"r": float(to_c.get("r", 0)), "g": float(to_c.get("g", 0)), "b": float(to_c.get("b", 0))}
                fade.color_from = {"r": float(from_c.get("r", 0)), "g": float(from_c.get("g", 0)), "b": float(from_c.get("b", 0))}

            # MIB: Pan/Tilt/Farbe/Beam im Dunkeln vorpositionieren, bevor
            # der Dimmer hochfaehrt (siehe Moduldoc).
            if "dimmer" in fade.scalars_to:
                current_dimmer = fade.scalars_from.get("dimmer", 0.0)
                target_dimmer = fade.scalars_to.get("dimmer")
                fade.mib_snap = _should_apply_mib(cue.mib, current_dimmer, target_dimmer)

            fixtures[fx_id] = fade

        self._plan_premove(cuelist_id, cue, fixtures, group_timing)

        released_any = fx_engine.apply_cue_effects(cue_fx, cue.fx_order, cue.fx_fade_in) or released_any
        if released_any and self._on_broadcast is not None:
            await self._on_broadcast("fx_changed", fx_engine.state_payload())
        if not fixtures:
            self._emit_playback(cuelist_id)   # reiner Effekt-/Befehls-Cue: sofort "fertig", kein Rest-Balken
            return

        total_duration = max((delay + duration for delay, duration in group_timing.values()), default=0.0)
        self._transitions[cuelist_id] = _Transition(
            cuelist_id=cuelist_id,
            cue_id=cue.id,
            started_at=time.monotonic(),
            total_duration=total_duration,
            group_timing=group_timing,
            fixtures=fixtures,
            allow_follow=allow_follow,
        )
        await self._tick_transition(cuelist_id)
        if cuelist_id in self._transitions:
            self._emit_playback(cuelist_id)   # laeuft noch: Balken ab jetzt per CSS ueber "remaining"

    def _plan_premove(self, cuelist_id: str, cue, fixtures: Dict[str, "_FixtureFade"], group_timing: Dict[str, Tuple[float, float]]) -> None:
        """MIB-Vorlauf (siehe Moduldoc): Position/Farbe/Beam des FOLGENDEN Cues fuer alle Fixtures vormerken, die am Ende
        dieses Cues dunkel sind. Fixtures, die dieser Cue gar nicht anfasst, bekommen dafuer einen eigenen Eintrag."""
        cl = self._state.cuelists.get(cuelist_id)
        if cl is None:
            return
        idx = next((i for i, c in enumerate(cl.cues) if c.id == cue.id), None)
        if idx is None or idx + 1 >= len(cl.cues):
            return
        nxt = cl.cues[idx + 1]
        mode = (nxt.mib or "Off").strip().lower()
        if mode not in ("auto", "on"):
            return
        dim_delay, dim_fade = group_timing["dimmer"]
        nxt_fx = nxt.fx or {}
        for fx_id, step in nxt.fixture_values.items():
            fx = self._state.fixtures.get(fx_id)
            if fx is None:
                continue
            full = self._state.step_values(step)
            blocked = fx_engine.attrs_of_effects(nxt_fx.get(fx_id, {})) | fx_engine.attrs_of_effects(
                {cat: a["fx_id"] for cat, a in self._state.fx_assignments.get(fx_id, {}).items()})
            target = {
                k: v for k, v in full.items()
                if k != "dimmer" and (k == "color" or k in _ATTR_GROUPS or raw_offset(k) is not None)
                and k not in blocked
            }
            if not target:
                continue
            fade = fixtures.get(fx_id)
            layer = self._state.cue_layer.setdefault(cuelist_id, {}).setdefault(fx_id, {})
            current = current_abstract_values(fx)
            now_dim = float(fade.scalars_from["dimmer"]) if fade and "dimmer" in fade.scalars_from                 else float(layer["dimmer"]) if "dimmer" in layer else float(current.get("dimmer", 0.0) or 0.0)
            end_dim = float(fade.scalars_to["dimmer"]) if fade and "dimmer" in fade.scalars_to else now_dim
            if end_dim > _MIB_DARK_THRESHOLD:
                continue                                          # bleibt hell: Bewegung waere sichtbar
            next_dim = full.get("dimmer")
            if mode == "auto" and not (next_dim is not None and float(next_dim) > _MIB_DARK_THRESHOLD):
                continue                                          # Auto: nur wo der Folge-Cue die Fixture einschaltet
            after = 0.0 if now_dim <= _MIB_DARK_THRESHOLD else dim_delay + dim_fade
            if fade is None:
                fade = fixtures[fx_id] = _FixtureFade()
            current.update(self._raw_current(fx, target))
            base = self._state.cue_base.setdefault(cuelist_id, {}).setdefault(fx_id, {})
            programmer = self._state.programmer_values.get(fx_id, {})
            for attr in target:
                if attr not in layer and attr not in base:
                    manual = programmer.get(attr)
                    if manual is None:
                        manual = current.get(attr)
                    base[attr] = copy.deepcopy(manual) if manual is not None else self._state._neutral_value(attr)
            fade.premove_to = copy.deepcopy(target)
            fade.premove_after = after

    def _raw_current(self, fx, target: Dict[str, Any]) -> Dict[str, float]:
        """Aktuelle DMX-Bytes der rohen Kanaele ("ch<Offset>") im Ziel - Startwert der Cue-Schicht und manueller Wert, auf den der Executor-Fader zurueckfaellt."""
        wanted = {attr: raw_offset(attr) for attr in target if raw_offset(attr) is not None}
        if not wanted:
            return {}
        snapshot = self._dmx.get_universe_snapshot(fx.universe)
        out: Dict[str, float] = {}
        for attr, offset in wanted.items():
            index = fx.start_channel - 1 + offset
            out[attr] = float(snapshot[index]) if 0 <= index < len(snapshot) else 0.0
        return out

    async def _tick(self) -> None:
        if not self._transitions:
            return
        for cuelist_id in list(self._transitions):
            transition = self._transitions.get(cuelist_id)
            if transition is not None and transition.paused_at is None:
                await self._tick_transition(cuelist_id)

    async def _tick_transition(self, cuelist_id: str) -> None:
        transition = self._transitions.get(cuelist_id)
        if transition is None:
            return
        elapsed = time.monotonic() - transition.started_at

        def _group_progress(group: str) -> float:
            delay, duration = transition.group_timing.get(group, (0.0, 0.0))
            if elapsed < delay:
                return 0.0
            if duration <= 0.0:
                return 1.0
            return min(1.0, (elapsed - delay) / duration)

        universe_batches: Dict[int, Dict[int, int]] = {}
        live_values: Dict[str, Any] = {}
        affected_universes: Set[int] = set()

        for fx_id, fade in transition.fixtures.items():
            fx = self._state.fixtures.get(fx_id)
            if fx is None:
                continue
            abstract_now: Dict[str, Any] = {}
            for attr, to_v in fade.scalars_to.items():
                from_v = fade.scalars_from.get(attr, to_v)
                group = _ATTR_GROUPS.get(attr, "dimmer")
                t_attr = 1.0 if (fade.mib_snap and group != "dimmer") else _group_progress(group)
                if attr in DISCRETE_ATTRS:                       # Gobo-/Prismenrad, Strobe-Bereich: umschalten, nicht durch die Slots fahren
                    abstract_now[attr] = to_v if t_attr > 0.0 else from_v
                else:
                    abstract_now[attr] = from_v + (to_v - from_v) * t_attr
            for attr, to_v in fade.raw_to.items():               # rohe Kanaele: Umschalten am Beginn der Beam-Zeit
                abstract_now[attr] = to_v if (fade.mib_snap or _group_progress("beam") > 0.0) else fade.raw_from.get(attr, to_v)
            if fade.color_to is not None:
                from_c = fade.color_from or {"r": 0, "g": 0, "b": 0}
                t_color = 1.0 if fade.mib_snap else _group_progress("color")
                abstract_now["color"] = {
                    k: from_c.get(k, 0) + (fade.color_to.get(k, 0) - from_c.get(k, 0)) * t_color
                    for k in ("r", "g", "b")
                }
            if fade.premove_to and elapsed >= fade.premove_after:       # MIB-Vorlauf: die Fixture ist dunkel, jetzt auf die Position des Folge-Cues
                for attr, value in fade.premove_to.items():
                    abstract_now[attr] = copy.deepcopy(value)
            layer = self._state.cue_layer.setdefault(cuelist_id, {}).setdefault(fx_id, {})
            for attr, value in abstract_now.items():
                layer[attr] = copy.deepcopy(value)
            mixed = self._state.mix_abstract(self._state.cue_base.get(cuelist_id, {}).get(fx_id, {}), abstract_now,
                                             self._state.mix_level(cuelist_id))
            offsets = fixture_channel_offsets(fx)
            resolved = apply_abstract_values(
                fx, mixed, offsets, universe_batches,
                pct_values=True, grand_master=self._state.effective_master(fx_id),
            )
            if resolved:
                self._state.set_fixture_values(fx_id, resolved)
                affected_universes.add(fx.universe)
                live_values[fx_id] = mixed

        # post_batch() ist non-blocking (dedizierter Ausgabe-Thread in dmx_engine.py),
        # damit die 40-Hz-Fade-Schleife der CueEngine den asyncio-Loop nie blockiert.
        for universe, ch_map in universe_batches.items():
            self._dmx.post_batch(universe, ch_map)

        overall_t = 1.0 if transition.total_duration <= 0.0 else min(1.0, elapsed / transition.total_duration)
        finished = overall_t >= 1.0
        if finished:
            del self._transitions[cuelist_id]

        if self._on_update is not None and (affected_universes or live_values):
            result = self._on_update({"universes": affected_universes, "values": live_values})
            if asyncio.iscoroutine(result):
                await result

        if finished:
            self._emit_playback(cuelist_id)   # "done": Balken voll, ohne Animation (auch bei 0 s)
            if transition.allow_follow:
                self._follow_tasks[cuelist_id] = asyncio.create_task(
                    self._maybe_follow(cuelist_id, transition.cue_id))

    async def refresh_preset(self, preset_id: str) -> None:
        """Eine Variable wurde geaendert: alle AKTIVEN Cues, die sie verwenden, geben den neuen Wert sofort aus (ohne neues Go). Laeuft gerade eine
        Ueberblendung auf diese Fixture, ist der neue Wert deren Ziel; sonst wird die Cue-Schicht aktualisiert und neu gemischt."""
        from app.state_manager import PRESET_TYPE_ATTRS
        preset = self._state.presets.get(preset_id)
        if preset is None:
            return
        new_values = preset_to_abstract(preset)
        attrs = set(PRESET_TYPE_ATTRS.get(preset.type, ())) | set(new_values)
        remix_lists: Set[str] = set()
        for cuelist_id, cue_id in list(self._state.active_cue_ids.items()):
            cl = self._state.cuelists.get(cuelist_id)
            cue = next((c for c in cl.cues if c.id == cue_id), None) if cl else None
            if cue is None:
                continue
            transition = self._transitions.get(cuelist_id)
            for fx_id, step in cue.fixture_values.items():
                if self._state.step_refs(step).get(preset.type) != preset_id or fx_id not in self._state.fixtures:
                    continue
                if fx_id in self._state.programmer_values and any(a in self._state.programmer_values[fx_id] for a in new_values):
                    continue                                                  # der Programmer hat diese Fixture uebernommen (er gewinnt bis zum naechsten Go)
                layer = self._state.cue_layer.setdefault(cuelist_id, {}).setdefault(fx_id, {})
                fade = transition.fixtures.get(fx_id) if transition is not None else None
                for attr, value in new_values.items():
                    if fade is not None and attr in fade.scalars_to:
                        fade.scalars_to[attr] = float(value)
                    elif fade is not None and attr == "color" and fade.color_to is not None:
                        fade.color_to = {k: float(value.get(k, 0)) for k in ("r", "g", "b")}
                    elif fade is not None and attr in fade.raw_to:
                        fade.raw_to[attr] = float(value)
                    else:
                        layer[attr] = copy.deepcopy(value)
                        remix_lists.add(cuelist_id)
        for cuelist_id in remix_lists:
            await self.remix(cuelist_id)

    async def remix(self, cuelist_id: str) -> None:
        """Executor-Fader bewegt: Ausgabe aller Attribute, die diese Liste steuert, aus Cue-Schicht und manuellem Wert neu
        mischen (linear, fuer jeden Kanaltyp). Die gespeicherten Cue-Werte bleiben unveraendert."""
        layers = self._state.cue_layer.get(cuelist_id) or {}
        if not layers:
            return
        level = self._state.mix_level(cuelist_id)
        batches: Dict[int, Dict[int, int]] = {}
        live_values: Dict[str, Any] = {}
        universes: Set[int] = set()
        for fx_id, attrs in layers.items():
            fx = self._state.fixtures.get(fx_id)
            if fx is None or not attrs:
                continue
            mixed = self._state.mix_abstract(self._state.cue_base.get(cuelist_id, {}).get(fx_id, {}), attrs, level)
            resolved = apply_abstract_values(fx, mixed, fixture_channel_offsets(fx), batches,
                                             pct_values=True, grand_master=self._state.effective_master(fx_id))
            if resolved:
                self._state.set_fixture_values(fx_id, resolved)
                universes.add(fx.universe)
                live_values[fx_id] = mixed
        for universe, channels in batches.items():
            self._dmx.commit_batch(universe, channels)
        if self._on_update is not None and (universes or live_values):
            result = self._on_update({"universes": universes, "values": live_values})
            if asyncio.iscoroutine(result):
                await result

    async def _maybe_follow(self, cuelist_id: str, completed_cue_id: str) -> None:
        """Automatische Cue-Verkettung: wird nach jeder abgeschlossenen
        Ueberblendung (ausser "Back") als eigener Task gestartet. Faehrt nur
        fort, wenn der auf completed_cue_id FOLGENDE Cue trigger == "follow"
        traegt, und bricht ab, falls der Benutzer in der Zwischenzeit
        (waehrend des delay) einen anderen Cue ausgeloest hat."""
        cl = self._state.cuelists.get(cuelist_id)
        if cl is None:
            return
        idx = next((i for i, c in enumerate(cl.cues) if c.id == completed_cue_id), None)
        if idx is None or idx + 1 >= len(cl.cues):
            return
        next_cue = cl.cues[idx + 1]
        if next_cue.trigger != "follow":
            self._follow_tasks.pop(cuelist_id, None)
            return

        delay = max(0.0, float(next_cue.delay))
        if delay > 0:
            # Der Delay beginnt, wenn die Ueberblendung des aktiven Cues fertig ist. Die Oberflaeche
            # bekommt Cue und Restzeit und zeichnet den Countdown in dessen Zeile (eine Stufe voraus).
            self._follow_wait[cuelist_id] = (next_cue.id, time.monotonic(), delay)
            self._emit_playback(cuelist_id)
            try:
                await asyncio.sleep(delay)
            finally:
                self._follow_wait.pop(cuelist_id, None)

        # Zwischenzeitlicher manueller Eingriff (Go/Back/jump_to) hat
        # bereits einen anderen Cue aktiv gemacht - nicht blind ueberschreiben.
        if self._state.active_cue_ids.get(cuelist_id) != completed_cue_id:
            return

        new_cue = await self.trigger(cuelist_id, 1)
        if new_cue is not None and self._on_cuelists_changed is not None:
            await self._on_cuelists_changed()

    async def _run_cue_cmd(self, cue) -> None:
        """Fuehrt den im Cue hinterlegten Konsolen-Befehl (Cue.cmd) automatisch
        aus, sobald der Cue getriggert wird (Go/Follow/jump_to) - z.B.
        "Store Cue 5" oder "Fixture 1 At 0". Nutzt denselben Parser wie die
        Command Line (app/command_line.py); das Ergebnis geht ueber
        set_command_log_callback() in dieselbe gemeinsame Befehls-Historie
        wie ein manuell eingegebener Befehl."""
        cmd = (getattr(cue, "cmd", "") or "").strip()
        if not cmd or self._on_broadcast is None:
            return
        from app.command_line import execute_command  # deferred: vermeidet Zirkelimport beim Modul-Laden
        result = await execute_command(cmd, self._on_broadcast)
        if self._on_command_log is not None:
            await self._on_command_log(cmd, result)


# Einzige, global geteilte Instanz - von server.py importiert und gestartet.
# Der Import von state/dmx_engine hier ist unidirektional: weder
# state_manager.py noch dmx_engine.py importieren cue_engine.py zurueck.
from app.state_manager import state  # noqa: E402
from app.dmx_engine import dmx_engine  # noqa: E402

cue_engine = CueEngine(state, dmx_engine)
