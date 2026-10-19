"""
state_manager.py
Zentraler State-Master von OpenCue.

Haelt den kompletten Show-Zustand (Fixtures, Gruppen, Cues) im Arbeitsspeicher
und ist die einzige "Source of Truth". Server (server.py) und DMX-Engine
(dmx_engine.py) lesen und schreiben ausschliesslich ueber diese Klasse - so
bleibt der State an einer einzigen Stelle konsistent und kann jederzeit als
vollstaendiger JSON-Snapshot an Clients gesendet werden.

WICHTIG - Trennung von App- und Show-Daten:
Globale Anwendungs-Einstellungen (gui_scale, language, DMX/Netzwerk-Settings,
Panel-Layout des Edit-Mode-Desktops) sind bewusst vom Showfile getrennt und
leben in einer eigenen `app_config.json` im Hauptverzeichnis. Sie gehoeren
zur Anwendung/zum Arbeitsplatz selbst, nicht zu einer bestimmten Show, und
bleiben deshalb auch beim Laden eines anderen Showfiles unveraendert
erhalten.
"""

from __future__ import annotations

import copy
import ipaddress
import json
import math
import re
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from app import fx_categories
from app import legacy_show
from app import media_store
from app.dmx_resolve import DISCRETE_ATTRS, raw_offset
#3D-AUS# from app import stage3d
from app import sim_stages
from app import paths as _paths

APP_CONFIG_PATH = _paths.APP_CONFIG_PATH

MIN_GUI_SCALE = 0.5
MAX_GUI_SCALE = 2.0
DEFAULT_SERVER_PORT = 8000
MIN_SERVER_PORT = 1024
MAX_SERVER_PORT = 65535
DEFAULT_LANGUAGE = "en"
SUPPORTED_LANGUAGES = {"en", "de"}

MIN_UNIVERSE = 1
MAX_UNIVERSE = 64
DEFAULT_REMOTE_PASSWORD = "12345678"
DEFAULT_ARTNET_IP = "2.255.255.255"  # Ziel-/Broadcast-Adresse ("Target IP")
DEFAULT_ARTNET_BIND_IP = ""  # leer = Betriebssystem waehlt das Interface

# Theme: ein flaches Token-Objekt. Gespeichert wird nur die Abweichung von der Basis:
#   {"base": "dark" | "light", "tokens": {tokenName: "#rrggbb"}, "radius": 0-16}
# "Eigenes" ist abgeleitet (es gibt Ueberschreibungen), keine dritte Basis: die Basis bleibt Ausgangspunkt.
# Die Palette der Basis-Themes (Dark/Light) liegt im Frontend (static/js/app.js, THEME_BASES) und
# in static/css/theme.css. Der Server kennt nur die erlaubten Token-Namen und prueft die Werte.
THEME_TOKEN_KEYS = (
    "bg", "toolbar-bg", "menu-bg",
    "panel-bg", "panel-border", "panel-header-bg",
    "surface-1", "surface-2", "surface-3",
    "border", "border-strong",
    "text-1", "text-2", "text-3",
    "accent",
    "ok", "warn", "error", "live",
)
THEME_BASES = ("dark", "light")
DEFAULT_RADIUS = 0  # Standard: eckig. --radius-md in px; sm und lg werden proportional abgeleitet
OLD_DEFAULT_RADIUS = 7  # bis Schritt 4b der Standard: gilt in aelteren Konfigurationen als "nicht angepasst"
THEME_SCHEMA = 2  # 2 = Standard-Rundung eckig; aeltere Konfigurationen werden beim Laden angehoben
MAX_RADIUS = 16
MAX_THEME_PROFILES = 200
OLD_DEFAULT_ACCENTS = ("#00ff66", "#ffb000")  # fruehere Standard-Akzente: kein "eigener" Wert


def default_theme() -> Dict[str, Any]:
    return {"base": "dark", "tokens": {}, "radius": DEFAULT_RADIUS}


def normalize_theme(raw: Any) -> Dict[str, Any]:
    """Prueft ein Theme-Objekt (aus dem Netz oder der Konfiguration) und gibt ein bereinigtes zurueck."""
    theme = default_theme()
    if not isinstance(raw, dict):
        return theme
    base = raw.get("base")
    theme["base"] = base if base in THEME_BASES else "dark"
    tokens = raw.get("tokens")
    if isinstance(tokens, dict):
        for key, value in tokens.items():
            if key in THEME_TOKEN_KEYS and _is_valid_hex_color(value):
                theme["tokens"][key] = str(value).lower()
    try:
        theme["radius"] = max(0, min(MAX_RADIUS, int(raw.get("radius", DEFAULT_RADIUS))))
    except (TypeError, ValueError):
        pass
    return theme


def migrate_legacy_theme(saved: Dict[str, Any]) -> Dict[str, Any]:
    """Alte Konfiguration (Schluessel wie accent_color, bg_color ...): nur ein bewusst gewaehlter
    Akzent bleibt erhalten; die frueheren Standardwerte sind kein "eigener" Wert."""
    theme = default_theme()
    accent = saved.get("accent_color")
    if _is_valid_hex_color(accent) and str(accent).lower() not in OLD_DEFAULT_ACCENTS:
        theme["tokens"]["accent"] = str(accent).lower()
    return theme


# "Panel Defaults" (Settings -> Panel Defaults): NOT CSS-theme variables -
# these are plain values read once by add_panel() when a NEW panel is
# created, so an admin can set a house style for future panels without
# retroactively touching any panel that already exists.
DEFAULT_PANEL_DEFAULTS = {
    "background_color": "#151517",
    "text_color": "#ededf0",
    "header_background_color": "#151517",
    "shadow_enabled": True,
    "corner_style": "global",   # "global" | "round" | "square" - wie Panel.corner_style
}
PANEL_CORNER_STYLES = ("global", "round", "square")
# Fruehere Standardwerte: gespeicherte Panel-Defaults mit genau diesen Werten werden auf die neuen
# Standards gehoben, bewusst gewaehlte Abweichungen bleiben erhalten.
LEGACY_PANEL_DEFAULTS = {
    "background_color": "#1a1a1a",
    "text_color": "#e6e6e6",
    "header_background_color": "#141414",
}

MIN_PANEL_SIZE = 5.0         # Prozent der Arbeitsflaeche - Untergrenze fuer Breite/Hoehe
MIN_COMPACT_PANEL_SIZE = 0.5 # Button/Fader duerfen sehr klein skaliert werden
COMPACT_PANEL_TYPES = {"button", "fader", "executor"}
MIN_PANEL_SCALE = 0.5
MAX_PANEL_SCALE = 2.0
HEX_COLOR_PATTERN = re.compile(r"^#[0-9a-fA-F]{6}$")
_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.ASCII | re.IGNORECASE,
)


def _is_valid_hex_color(value: Any) -> bool:
    return isinstance(value, str) and bool(HEX_COLOR_PATTERN.match(value))


def _is_valid_uuid(value: Any) -> bool:
    """Prueft ob value ein gültiges UUID4-String-Format hat (mit Bindestrichen)."""
    return isinstance(value, str) and bool(_UUID_RE.match(value))


def migrate_fx_definition(fx: Dict[str, Any]) -> Dict[str, Any]:
    """Aeltere Effekt-Definitionen (feste speed/size/phase/Farben) in das Parameter-
    Format der Skripte ueberfuehren. Die Art (kind) heisst weiterhin wie das Skript."""
    if isinstance(fx.get("params"), dict):
        params = dict(fx["params"])
    else:
        params = {
            "speed": fx.get("speed", 0.5),
            "size": fx.get("size", 100.0),
            "spread": fx.get("phase", 0.0),
            "color_a": fx.get("color_a", {"r": 255, "g": 0, "b": 0}),
            "color_b": fx.get("color_b", {"r": 0, "g": 0, "b": 255}),
        }
    return {
        "name": str(fx.get("name", "")),
        "group": str(fx.get("group", "") or ""),
        "kind": str(fx.get("kind", "")),
        "params": params,
    }


def _clamp_percent(value: Any) -> float:
    try:
        return max(0.0, min(100.0, float(value)))
    except (TypeError, ValueError):
        return 100.0


CUE_TRIGGERS = ("go", "follow", "timecode")
MAX_TIMECODE_MS = 100 * 3600 * 1000        # wie timecode.MAX_MS (hier ohne Import, damit der Zustand ohne die Uhr auskommt)


def _parse_timecode_ms(value: Any) -> Optional[int]:
    """Cue-Ausloesezeit in Millisekunden (0 .. 100 h); None/leer/ungueltig = keine."""
    if value is None or value == "" or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number or number < 0 or number > MAX_TIMECODE_MS:
        return None
    return int(round(number))


def _normalize_cue_trigger(cue: "Cue") -> "Cue":
    """Beim Laden: unbekannter Ausloeser oder 'timecode' ohne gueltige Zeit (beschaedigte/handgemachte Datei) wird zu 'go' -
    ein Cue ohne Zeit darf nie unbemerkt bei 0 oder gar nicht feuern."""
    if cue.trigger not in CUE_TRIGGERS:
        cue.trigger = "go"
    cue.timecode_ms = _parse_timecode_ms(cue.timecode_ms) if cue.trigger == "timecode" else None
    if cue.trigger == "timecode" and cue.timecode_ms is None:
        cue.trigger = "go"
    return cue


def _parse_optional_float(value: Any) -> Optional[float]:
    """Fuer die dot2-Stil Attribut-Zeiten (Cue.fade_color/_pos/_beam etc.):
    None/leer = "nutzt die allgemeine fade/delay-Zeit dieser Gruppe"
    (siehe cue_engine.py), ansonsten ein nicht-negativer Sekundenwert."""
    if value is None or value == "":
        return None
    try:
        return max(0.0, float(value))
    except (TypeError, ValueError):
        return None


@dataclass
class Fixture:
    """Ein einzelnes Lichtgeraet (Moving Head, Dimmer, LED-Bar, ...)."""

    id: str
    name: str
    fixture_type: str
    universe: int
    start_channel: int
    channel_count: int
    fid: int = 0  # user-facing sequential number (FID)
    mode: str = "default"
    values: Dict[str, int] = field(default_factory=dict)  # Kanalname -> 0..255
    # Freier Sortierwert (aufsteigend) fuer die Reihenfolge in der Scheinwerfer-Liste, unabhaengig von FID und DMX-Adresse;
    # None = nicht gesetzt (zaehlt wie 0, Gleichstand -> nach Adresse wie bisher).
    sort_index: Optional[float] = None


@dataclass
class Cue:
    """Eine einzelne Lichtstimmung innerhalb einer CueList.

    fixture_values: fixture_id (UUID) -> entweder
      {"preset_uuid": "<uuid>"}                      - Verweis auf ein Preset (aelteres Format, = refs mit dem Typ des Presets),
                                                         wird beim Abfeuern live aufgeloest
      {"values": {...}, "refs": {"color": "<preset-uuid>", ...}}
                                                       - feste Werte PLUS Verweise je Variablen-Typ (dimmer, position, color,
                                                         focus, zoom, gobo): die Variable ist ein Platzhalter und wird bei jedem
                                                         Abspielen live aufgeloest - aendert man sie, aendert sich die ganze Show
      {"values": {dimmer?, color?, pan?, tilt?,
                   strobe?, gobo?, prism?, focus?, zoom?}} - feste relative Werte,
                                                              identisches Format wie
                                                              Preset.values / der Programmer
                                                              (dimmer/pan/tilt/beam 0-100%,
                                                              color als {r,g,b} 0-255)
    Nur die aktuell im Programmer gesetzten (relativen) Werte werden gespeichert -
    kein voller DMX-Snapshot.
    """

    id: str
    number: float
    name: str
    fade: float = 0.0       # Haupt-/Dimmer-Einblendzeit in Sekunden
    delay: float = 0.0      # Haupt-/Dimmer-Verzoegerung in Sekunden (siehe auch trigger == "follow")
    trigger: str = "go"     # "go" (manueller Start) | "follow" (automatischer Folgestart) | "timecode" (feuert zur Zeit timecode_ms)
    timecode_ms: Optional[int] = None   # nur bei trigger == "timecode": Zeit in ms auf dem globalen Timecode
    # dot2-Stil Attribut-Zeiten: pro Gruppe optional eine eigene Fade-/
    # Delay-Zeit, die VOR der allgemeinen fade/delay bevorzugt wird (siehe
    # cue_engine.py). None = "nutzt die allgemeine Zeit dieser Gruppe".
    fade_color: Optional[float] = None
    delay_color: Optional[float] = None
    fade_pos: Optional[float] = None
    delay_pos: Optional[float] = None
    fade_beam: Optional[float] = None
    delay_beam: Optional[float] = None
    fade_zoom: Optional[float] = None
    delay_zoom: Optional[float] = None
    mib: str = "Off"        # Move In Black: "Off" | "Auto" | "On" (siehe cue_engine.py)
    cmd: str = ""           # Freitext-Kommandozeile fuer spaetere Konsolen-Kommando-Ausfuehrung
    fixture_values: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    # Effekt-Zuweisungen des Cues: fixture_id -> {kategorie: fx_id}
    fx: Dict[str, Dict[str, str]] = field(default_factory=dict)
    # Auswahl-Reihenfolge der Effekt-Zuweisungen: fixture_id -> {kategorie: index}
    fx_order: Dict[str, Dict[str, int]] = field(default_factory=dict)
    # Amplituden-Ein-/Ausblendzeit der Effekte dieses Cues in Sekunden (0 = sofort)
    fx_fade_in: float = 0.0
    fx_fade_out: float = 0.0


@dataclass
class CueList:
    """Eine benannte, sortierte Liste von Cues (Fliesskomma-Nummerierung)."""

    id: str
    name: str
    cues: List[Cue] = field(default_factory=list)


PRESET_TYPES = ("dimmer", "position", "color", "focus", "zoom", "gobo")
# Welche abstrakten Attribute eine Variable (Preset) dieses Typs setzt - die Grenze einer Verknuepfung im Programmer und im Cue
PRESET_TYPE_ATTRS = {
    "dimmer": ("dimmer",), "position": ("pan", "tilt"), "color": ("color",),
    "focus": ("focus",), "zoom": ("zoom",), "gobo": ("gobo", "gobo_spin", "gobo2", "gobo2_spin"),
}


@dataclass
class Preset:
    """Ein gespeicherter Preset-Wert (Dimmer, Position oder Farbe)."""

    id: str
    name: str
    type: str          # siehe PRESET_TYPES
    group: str = ""    # group name; empty = ungrouped
    values: Dict[str, Any] = field(default_factory=dict)
    # dimmer: {"level": 75}  (0-100 float)
    # position: {"pan": 50.0, "tilt": 50.0}  (0-100 float)
    # color: {"r": 255, "g": 0, "b": 0}
    # focus / zoom / gobo: {"level": 50}  (0-100 float)


@dataclass
class Panel:
    """Ein frei platzierbares Modul auf dem Edit-Mode-Desktop.

    Position/Groesse sind relativ zur Arbeitsflaeche in Prozent (0-100)
    gespeichert, nicht in Pixeln - damit die Anordnung unabhaengig von der
    tatsaechlichen Fenstergroesse und von --gui-scale stabil bleibt.
    """

    id: str
    type: str
    x: float = 8.0
    y: float = 8.0
    width: float = 32.0
    height: float = 46.0
    title: str = ""  # empty = fall back to the type's i18n default title (e.g. PANEL_SETTINGS)
    show_header: bool = True  # False hides the panel__header bar entirely
    panel_scale: float = 1.0  # independent of the global --gui-scale; scoped to this panel's own content only
    # Standardwerte = Design-Tokens aus theme.css (--border, --surface-1, --text-1). Das Frontend
    # erkennt diese Werte UND die frueheren Standards (#ffffff, #1a1a1a, #e6e6e6, #141414) als
    # "Standard" und nutzt dann die Tokens; nur bewusst abweichende Farben werden inline gesetzt.
    border_color: str = "#323237"
    background_color: str = "#151517"
    text_color: str = "#ededf0"
    header_background_color: str = "#151517"
    accent_color: str = "#ffb000"  # nur wirksam bei use_custom_accent; gilt nur im Teilbaum dieses Panels
    use_custom_accent: bool = False  # False = inherit the global Appearance accent color instead of accent_color
    drop_shadow: bool = True  # toggles the panel's box-shadow (Panel Properties -> Appearance & Colors)
    corner_style: str = "global"  # "global" (Rundungsgrad aus dem Theme) | "round" (abgerundet) | "square" (eckig, 0px)
    z_index: int = 10  # stacking order - higher draws on top of lower
    module_config: Dict[str, Any] = field(default_factory=dict)  # panel-type-specific settings (e.g. DMX universe, highlight color)
    # Laufender UI-Zustand des Panel-Inhalts (Scrollpositionen, Eingabefelder),
    # vom Frontend gemeldet und mit dem Layout gespeichert - siehe app.js
    # collectPanelUiState()/applyPanelUiState().
    ui_state: Dict[str, Any] = field(default_factory=dict)


class StateManager:
    """Zentraler State-Master fuer die aktuell geladene Show + globale App-Settings."""

    def __init__(self) -> None:
        # Show-Daten
        self.showfile_name: str = "Untitled"
        self.showfile_path: Optional[str] = None
        # Medien (Video/Audio) der Show: nur Metadaten (id = SHA-256), die Dateien liegen in media_store; siehe dort
        self.media: Dict[str, Dict[str, Any]] = {}
        self.fixtures: Dict[str, Fixture] = {}
        self.groups: Dict[str, List[str]] = {}
        self.cues: List[Cue] = []
        self.presets: Dict[str, Preset] = {}
        self.preset_groups: List[str] = []
        # FX-Bibliothek (wie Presets): Definitionen im Showfile, Gruppen wie Preset-Gruppen.
        self.fx_effects: Dict[str, Dict[str, Any]] = {}
        self.fx_groups: List[str] = []
        # Lieblings-Effekte (Skriptnamen): eine Einstellung der Konsole fuer alle Geraete, nicht Teil der Show (steht in der app_config.json)
        self.fx_favorites: List[str] = []
        self.cmd_suggestions: bool = True          # Autocomplete-Vorschlaege der Befehlszeile (Schalter neben der Eingabe, gilt fuer alle Geraete)
#3D-AUS#         # 3D-Buehne (app/stage3d.py): RAUM (Geometrie) und RIG (Scheinwerfer-Positionen) sind getrennte Einheiten mit eigener Bibliothek; beide stecken
#3D-AUS#         # immer vollstaendig in der Show. *_source = Dateiname in der jeweiligen Bibliothek, aus der sie stammen (Anzeige "weicht ab"), None = nur in der Show
#3D-AUS#         self.room: Dict[str, Any] = stage3d.default_room()
#3D-AUS#         self.room_source: Optional[str] = None
#3D-AUS#         self.rig: Dict[str, Any] = stage3d.default_rig()
#3D-AUS#         self.rig_source: Optional[str] = None
        # Programmer-Zuweisungen: fixture_id -> {kategorie: {fx_id, index, count}}.
        # Transient wie programmer_values, wird im runtime_state gespeichert.
        self.fx_assignments: Dict[str, Dict[str, Dict[str, Any]]] = {}

        # Cue-Execution-System (Phase 1: Anlegen/Verwalten/hartes Abfeuern,
        # siehe save_cue()/step_cue() weiter unten). active_cue_ids wird im
        # Showfile unter "runtime_state" mitgespeichert, damit der Wiederanlauf
        # die zuletzt aktiven Cues wiederherstellt (siehe server.py).
        self.cuelists: Dict[str, CueList] = {}
        self.active_cuelist_id: Optional[str] = None
        self.active_cue_ids: Dict[str, str] = {}  # cuelist_id -> aktuell aktiver cue_id

        # Gesamthelligkeit (Grand Master, 0-100 %) - skaliert alle Dimmer-
        # Kanaele, siehe dmx_resolve.apply_abstract_values(). Persistiert im
        # Showfile unter "runtime_state".
        self.grand_master: float = 100.0
        self.blackout: bool = False                 # Blackout: alle Helligkeiten auf 0, ohne die Werte zu veraendern (Umschalter, nicht Teil der Show)
        # Executor-Fader je Cue-Liste (0-100 %): MISCHT je Fixture und Attribut (Dimmer, Farbe, Position, Beam ...) linear
        # zwischen dem manuellen Wert (0 %) und dem Cue-Wert (100 %). Mit dem Grand Master hat er nichts zu tun. Die
        # gespeicherten Cue-Werte bleiben unveraendert. Persistiert im Showfile unter "runtime_state".
        self.cuelist_masters: Dict[str, float] = {}
        # Laufzeit-Schichten je Cue-Liste: cuelist -> fixture -> attr -> Wert
        self.cue_layer: Dict[str, Dict[str, Dict[str, Any]]] = {}   # aktueller Cue-Wert (ungemischt, inkl. Ueberblendung)
        self.cue_base: Dict[str, Dict[str, Dict[str, Any]]] = {}    # manueller Wert, auf den der Fader bei 0 % faellt
        # True, sobald das geladene Showfile einen "runtime_state"-Block hat -
        # steuert beim Wiederanlauf, ob der gespeicherte Ausgabezustand
        # wiederhergestellt oder der Baseline-Reset angewandt wird.
        self.runtime_state_loaded: bool = False
        # Gespeicherter DMX-Ausgang je Universum (Kanal -> Wert, nur Kanaele
        # != 0) aus dem Showfile; None = Datei ohne DMX-Block (Altformat).
        self.restored_dmx_universes: Optional[Dict[int, Dict[int, int]]] = None
        # Liefert den aktuellen DMX-Ausgang je Universum (512 Werte) fuer das
        # Speichern. Wird von server.py gesetzt, damit state_manager den
        # DMX-Engine-Modul nicht importieren muss.
        self.dmx_state_provider: Optional[Callable[[], Dict[int, List[int]]]] = None

        # Server-autoritative Programmer-Selektion + "touched"-Werte (Command
        # Line, siehe app/command_line.py). Transient wie active_cue_ids oben -
        # nicht im Showfile persistiert. Wird von der Command Line direkt
        # geschrieben UND vom bestehenden set_fixture_values-WS-Handler
        # (Maus-/Fader-Bedienung) nachgefuehrt, damit "Store Cue" ueber die
        # Befehlszeile unabhaengig vom Eingabeweg denselben Programmer-Inhalt
        # sieht wie das Frontend (ProgrammerState.touchedAttrs/activeValues).
        self.selected_fixture_ids: List[str] = []
        self.programmer_values: Dict[str, Dict[str, Any]] = {}
        # fixture_id -> {Variablen-Typ: preset_id}: welche Variable (Platzhalter) gerade welchen Teil der Fixture im Programmer vorgibt.
        # Aendert man die Variable, folgt die Fixture live; ein manueller Wert, ein Effekt oder ein Cue loest die Verknuepfung.
        self.programmer_refs: Dict[str, Dict[str, str]] = {}

        # Globale App-Einstellungen (persistiert in app_config.json)
        self.gui_scale: float = 1.0
        self.language: str = DEFAULT_LANGUAGE
        self.panels: List[Panel] = []
        self.last_pasted_ids: List[str] = []      # IDs der zuletzt eingefuegten/duplizierten Panels (Antwort an den Absender)

        # Remote-Zugriff aus dem Netzwerk (persistiert in app_config.json). Standard: aus.
        # Der Server-Bind (0.0.0.0 / 127.0.0.1) wird beim Start gewaehlt (siehe main.py).
        self.remote_enabled: bool = False
        self.remote_password: str = DEFAULT_REMOTE_PASSWORD
        # Port des Servers; eine Aenderung wirkt erst nach einem Neustart (siehe main.py).
        self.server_port: int = DEFAULT_SERVER_PORT
        # True waehrend ein Remote-Client seine eigene Panel-Liste bearbeitet:
        # unterdrueckt das Schreiben der Host-Konfiguration (siehe app/remote.py).
        self._panel_scope_active: bool = False

        # DMX/Netzwerk - Art-Net und sACN sind bewusst vollstaendig
        # entkoppelt: jedes Protokoll hat seinen eigenen Enable-Schalter,
        # sACN hat sonst keine weitere Konfiguration (Multicast, siehe
        # dmx_engine.py), Art-Net zusaetzlich Ziel- ("Target") und
        # Sende-Interface- ("Bind") Adresse.
        self.artnet_enabled: bool = True
        self.artnet_ip: str = DEFAULT_ARTNET_IP  # "Target IP"
        self.artnet_bind_ip: str = DEFAULT_ARTNET_BIND_IP
        self.sacn_enabled: bool = False                  # aus: der sACN-Sender bindet einen UDP-Port, dafuer fragt die Windows-Firewall - das soll erst kommen, wenn man sACN einschaltet
        self.default_universe: int = MIN_UNIVERSE

        # USB DMX Output via Enttec DMX USB Pro (pyserial)
        self.enttec_enabled: bool = False
        self.enttec_port: str = ""
        self.enttec_universe: int = MIN_UNIVERSE

        # Appearance/Theme (siehe THEME_TOKEN_KEYS oben) und beliebig viele gespeicherte Profile
        self.theme: Dict[str, Any] = default_theme()
        self.theme_profiles: Dict[str, Dict[str, Any]] = {}
        self._theme_files: Dict[str, str] = {}             # Profilname -> Dateiname im Ordner themes/

        # "Panel Defaults" (Settings -> Panel Defaults) - siehe
        # DEFAULT_PANEL_DEFAULTS oben; nur von add_panel() gelesen, kein
        # CSS-Theme, betrifft nie bereits existierende Panels.
        self.panel_defaults: Dict[str, Any] = dict(DEFAULT_PANEL_DEFAULTS)

        # Fenster-Geometrie (main.py/pywebview) - None solange nie gespeichert
        # (erster Start: main.py faellt dann auf sein eigenes Default zurueck).
        self.window_x: Optional[int] = None
        self.window_y: Optional[int] = None
        self.window_width: Optional[int] = None
        self.window_height: Optional[int] = None
        self.window_maximized: bool = True

        # Letzter geoeffneter Showfile-Pfad (persistiert in app_config.json)
        self.last_showfile_path: Optional[str] = None

        # Zuletzt aktives Panel-Layout (Anzeigename, persistiert in app_config.json)
        self.last_active_layout: Optional[str] = None
        # Vollstaendiger Pfad der aktiven Layout-Datei (nicht persistiert; nur zur Laufzeit,
        # damit Auto-Save den korrekten Speicherort verwendet)
        self.last_active_layout_path: Optional[str] = None
        # Die mitgelieferten Beispiel-Layouts werden nur ein einziges Mal angelegt (persistiert),
        # damit ein vom Nutzer geloeschtes Beispiel nicht bei jedem Start wiederkommt.
        self.example_layouts_seeded: bool = False
        self.update_check_enabled: bool = True           # beim Start nach einer neuen Version suchen (GitHub; ohne Netz passiert nichts)
        self.update_skipped_version: str = ""           # 'Diese Version nicht mehr anzeigen': Kennung der uebersprungenen Version
        self.first_start_done: bool = False              # frische Installation: beim ersten Start wird die Demo-Show geoeffnet (server.open_first_start_demo); eine vorhandene Konfiguration gilt als 'schon gestartet'

        # Benutzerdefinierter Datenpfad (leer = Standard %LOCALAPPDATA%\OpenCue)
        self.custom_data_path: str = ""

        # Raum-Einstellungen der 3D-Simulation (Licht, Reflexion, ...; Normalisierung in sim_stages.normalize_room)
        self.sim_room: Dict[str, Any] = {}

        # Dirty-Flag: True sobald Show-Daten (Fixtures) seit dem letzten
        # Speichern geaendert wurden. Wird im Snapshot mitgeschickt und vom
        # Frontend als "unsaved changes"-Guard verwendet.
        self.is_dirty: bool = False

        # app_config.json wird sowohl vom asyncio-Event-Loop-Thread (WS-
        # Handler in server.py) als auch vom pywebview-UI-Thread (main.py's
        # Fenster-Events) beschrieben - dieser Lock verhindert, dass zwei
        # gleichzeitige Schreibvorgaenge die Datei gegenseitig zerreissen.
        self._config_lock = threading.Lock()

        self.load_app_config()
        try:
            self.reload_theme_profiles()      # Farbprofile = Dateien im Ordner themes/ (auch ohne vorhandene Konfiguration)
        except OSError:
            pass

        # Auto-load letztes Showfile beim Start
        if self.last_showfile_path:
            try:
                self.load_showfile(self.last_showfile_path)
            except Exception:
                self.last_showfile_path = None
                self.save_app_config()  # clear stale path so we don't retry on next start

    # ------------------------------------------------------------------
    # Snapshot - wird bei jedem neuen WebSocket-Connect komplett gesendet
    # ------------------------------------------------------------------
    def get_snapshot(self) -> Dict[str, Any]:
        from app.panel_registry import PanelRegistry  # deferred to avoid circular import
        return {
            "type": "state_snapshot",
            "payload": {
                "showfile_name": self.showfile_name,
                "is_dirty": self.is_dirty,
                "grand_master": self.grand_master,
                "cuelist_masters": dict(self.cuelist_masters),
                "gui_scale": self.gui_scale,
                "language": self.language,
                "artnet_enabled": self.artnet_enabled,
                "artnet_ip": self.artnet_ip,
                "artnet_bind_ip": self.artnet_bind_ip,
                "sacn_enabled": self.sacn_enabled,
                "default_universe": self.default_universe,
                "enttec_enabled": self.enttec_enabled,
                "enttec_port": self.enttec_port,
                "enttec_universe": self.enttec_universe,
                "theme": self.theme_payload(),
                "theme_profiles": self.theme_profiles_payload(),
                "panel_defaults": dict(self.panel_defaults),
                "panel_types": PanelRegistry.get_all_info(),
                "panels": self.panels_as_dicts(),
                "last_active_layout": self.last_active_layout,
                "fixtures": {fid: asdict(fx) for fid, fx in self.fixtures.items()},
                "groups": self.groups,
                "cues": [asdict(cue) for cue in self.cues],
                "presets": {pid: asdict(p) for pid, p in self.presets.items()},
                "preset_groups": list(self.preset_groups),
                "cuelists": self.cuelists_as_dicts(),
                "active_cuelist_id": self.active_cuelist_id,
                "active_cue_ids": dict(self.active_cue_ids),
#3D-AUS#                 "room": self.room,
#3D-AUS#                 "rig": self.rig,
#3D-AUS#                 "room_library": stage3d.library_status("room", self.room, self.room_source),
#3D-AUS#                 "rig_library": stage3d.library_status("rig", self.rig, self.rig_source),
                "media": self.media_payload(),
                "media_dir": str(media_store.store_dir()),
                "media_max_bytes": media_store.MAX_FILE_BYTES,
                "selected_fixture_ids": list(self.selected_fixture_ids),
                "custom_data_path": self.custom_data_path,
                "data_root": str(_paths.get_data_root()),
                "cmd_suggestions": self.cmd_suggestions,
                "update_check_enabled": self.update_check_enabled,
                "update_skipped_version": self.update_skipped_version,
                "blackout": self.blackout,
            },
        }

    # ------------------------------------------------------------------
    # Fixtures
    # ------------------------------------------------------------------
    def mark_dirty(self) -> None:
        """Markiert die Show als ungespeichert (Fixture-Aenderungen)."""
        self.is_dirty = True

    def _next_fid(self) -> int:
        if not self.fixtures:
            return 1
        return max(fx.fid for fx in self.fixtures.values()) + 1

    def add_fixture(
        self,
        name: str,
        fixture_type: str,
        universe: int,
        start_channel: int,
        channel_count: int,
        mode: str = "default",
    ) -> Fixture:
        fixture = Fixture(
            id=str(uuid.uuid4()),
            fid=self._next_fid(),
            name=name,
            fixture_type=fixture_type,
            universe=universe,
            start_channel=start_channel,
            channel_count=channel_count,
            mode=mode,
        )
        self.fixtures[fixture.id] = fixture
        return fixture

    def add_fixtures_batch(
        self,
        fixture_type_id: str,
        fixture_type_name: str,
        channel_count: int,
        mode: str,
        name_prefix: str,
        quantity: int,
        universe: int,
        start_channel: int,
        name_start_index: int = 1,
    ) -> List[Fixture]:
        created: List[Fixture] = []
        ch = start_channel
        for i in range(quantity):
            idx = name_start_index + i
            name = f"{name_prefix} {idx}" if (quantity > 1 or name_start_index > 1) else name_prefix
            fx = Fixture(
                id=str(uuid.uuid4()),
                fid=self._next_fid(),
                name=name,
                fixture_type=fixture_type_id,
                universe=universe,
                start_channel=ch,
                channel_count=channel_count,
                mode=mode,
            )
            self.fixtures[fx.id] = fx
            created.append(fx)
            ch += channel_count
            if ch > 512:
                break  # stop if we'd exceed the universe
        self.mark_dirty()
        return created

    def remove_fixture(self, fixture_id: str) -> bool:
        self.fx_assignments.pop(fixture_id, None)
        self.programmer_refs.pop(fixture_id, None)
        return self.fixtures.pop(fixture_id, None) is not None

    def delete_fixtures_bulk(self, fixture_ids: List[str]) -> int:
        removed = 0
        for fx_id in fixture_ids:
            self.fx_assignments.pop(fx_id, None)
            if self.fixtures.pop(fx_id, None) is not None:
                removed += 1
        if removed:
            self.prune_groups()
            self.mark_dirty()
        return removed

    def set_fixture_sort_index(self, fixture_id: str, value: Any) -> Optional[Fixture]:
        """Setzt den freien Sortier-Index (leer/ungueltig = nicht gesetzt)."""
        fx = self.fixtures.get(fixture_id)
        if fx is None:
            return None
        try:
            number = float(str(value).replace(",", ".")) if value not in (None, "") else None
        except (TypeError, ValueError):
            number = None
        if number is not None:
            if number != number or abs(number) == float("inf"):
                number = None
            else:
                number = max(-100000.0, min(100000.0, number))
                if number == int(number):
                    number = int(number)
        if fx.sort_index != number:
            fx.sort_index = number
            self.mark_dirty()
        return fx

    # ---- Scheinwerfer-Gruppen (rein organisatorisch: Sortierung und Sammelauswahl) ----------------------------------
    # self.groups: Gruppenname -> [Fixture-IDs] (Reihenfolge = Anzeigereihenfolge; "Group N" der Befehlszeile zaehlt dieselbe
    # Reihenfolge). Ein Scheinwerfer gehoert hoechstens einer Gruppe an, wenn er ueber den Dialog zugewiesen wird.
    MAX_GROUP_NAME = 40

    @classmethod
    def clean_group_name(cls, name: Any) -> str:
        return " ".join(str(name or "").split())[: cls.MAX_GROUP_NAME]

    def _group_name_taken(self, name: str, ignore: Optional[str] = None) -> bool:
        return any(g.lower() == name.lower() and g != ignore for g in self.groups)

    def add_fixture_group(self, name: Any) -> Optional[str]:
        """Legt eine leere Gruppe an. None bei leerem oder bereits vergebenem Namen (Gross-/Kleinschreibung egal)."""
        clean = self.clean_group_name(name)
        if not clean or self._group_name_taken(clean):
            return None
        self.groups[clean] = []
        self.mark_dirty()
        return clean

    def rename_fixture_group(self, old: Any, new: Any) -> bool:
        clean = self.clean_group_name(new)
        if old not in self.groups or not clean or self._group_name_taken(clean, ignore=old):
            return False
        if clean == old:
            return True
        self.groups = {(clean if g == old else g): ids for g, ids in self.groups.items()}      # Reihenfolge bleibt
        self.mark_dirty()
        return True

    def delete_fixture_group(self, name: Any) -> bool:
        if name not in self.groups:
            return False
        del self.groups[name]
        self.mark_dirty()
        return True

    def assign_fixture_group(self, fixture_ids: Any, group: Any) -> bool:
        """Ordnet Scheinwerfer genau einer Gruppe zu ("" = keine Gruppe). False bei unbekannter Gruppe/ohne gueltige Scheinwerfer."""
        ids = [str(i) for i in fixture_ids] if isinstance(fixture_ids, list) else []
        ids = [i for i in ids if i in self.fixtures]
        group = str(group or "")
        if not ids or (group and group not in self.groups):
            return False
        before = {g: list(v) for g, v in self.groups.items()}
        for name, members in self.groups.items():
            self.groups[name] = [m for m in members if m not in ids]
        if group:
            self.groups[group] = self.groups[group] + [i for i in ids if i not in self.groups[group]]
        if before != self.groups:
            self.mark_dirty()
        return True

    def prune_groups(self) -> bool:
        """Entfernt Verweise auf nicht (mehr) vorhandene Scheinwerfer aus allen Gruppen (die Gruppen selbst bleiben)."""
        changed = False
        for name, members in list(self.groups.items()):
            kept = [m for m in members if m in self.fixtures]
            if kept != members:
                self.groups[name] = kept
                changed = True
        return changed

    def update_fixture_patch(self, fixture_id: str, universe: int, start_channel: int) -> Optional[Fixture]:
        fx = self.fixtures.get(fixture_id)
        if fx is None:
            return None
        fx.universe = max(MIN_UNIVERSE, min(MAX_UNIVERSE, int(universe)))
        fx.start_channel = max(1, min(512, int(start_channel)))
        self.mark_dirty()
        return fx

    def rename_fixture(self, fixture_id: str, new_name: str) -> Optional[Fixture]:
        fx = self.fixtures.get(fixture_id)
        if fx is None:
            return None
        fx.name = str(new_name).strip()[:80]
        self.mark_dirty()
        return fx

    def set_fixture_values(self, fixture_id: str, values: Dict[str, int]) -> Optional[Fixture]:
        """Live-Kanalwerte eines Fixtures setzen (Programmer-Panel). Nicht
        dirty-markierend, da es sich um transiente Live-Steuerung handelt,
        nicht um eine zu speichernde Patch-Aenderung."""
        fx = self.fixtures.get(fixture_id)
        if fx is None:
            return None
        for ch_name, val in values.items():
            fx.values[ch_name] = max(0, min(255, int(val)))
        return fx

    def fixtures_as_dicts(self) -> Dict[str, Any]:
        return {fx_id: asdict(fx) for fx_id, fx in self.fixtures.items()}

    # ------------------------------------------------------------------
    # Medien
    # ------------------------------------------------------------------
    def media_payload(self) -> Dict[str, Any]:
        return {mid: {**meta, "missing": not media_store.exists(meta)} for mid, meta in self.media.items()}
    def add_media(self, meta: Dict[str, Any]) -> Dict[str, Any]:
        """Medium der Show hinzufuegen (gleiche Datei = derselbe Eintrag)."""
        existing = self.media.get(meta["id"])
        if existing is not None:
            return existing
        self.media[meta["id"]] = meta
        self.mark_dirty()
        return meta
    def update_media(self, media_id: str, name: Any = None) -> Optional[Dict[str, Any]]:
        meta = self.media.get(media_id)
        if meta is None:
            return None
        if isinstance(name, str) and name.strip():
            meta["name"] = media_store.clean_name(name)
        self.mark_dirty()
        return meta
    def remove_media(self, media_id: str) -> Optional[Dict[str, Any]]:
        """Medium aus der Show nehmen. Rueckgabe: seine Metadaten (None = gab es nicht). Die Datei loescht der Aufrufer."""
        meta = self.media.pop(media_id, None)
        if meta is None:
            return None
        self.mark_dirty()
        return meta

    def new_show(self) -> None:
        sim_stages.store.reset()
        self.showfile_name = "Untitled"
        self.showfile_path = None
        self.last_showfile_path = None
        self.media = {}
        self.fixtures = {}
        self.groups = {}
        self.cues = []
        self.presets = {}
        self.preset_groups = []
        self.fx_effects = {}
        self.fx_groups = []
        self.fx_assignments = {}
#3D-AUS#         self.room, self.room_source = stage3d.default_room(), None
#3D-AUS#         self.rig, self.rig_source = stage3d.default_rig(), None
        self.cuelists = {}
        self.active_cuelist_id = None
        self.active_cue_ids = {}
        # Live-Zustand der alten Show verwerfen: sonst bleiben Master, Programmer-Werte,
        # Selektion und der gespeicherte DMX-Stand in der neuen, leeren Show haengen.
        self.grand_master = 100.0
        self.cuelist_masters = {}
        self.cue_layer, self.cue_base = {}, {}
        self.programmer_values = {}
        self.programmer_refs = {}
        self.selected_fixture_ids = []
        self.runtime_state_loaded = False
        self.restored_dmx_universes = None
        self.is_dirty = False
        self.save_app_config()

    def set_fixture_value(self, fixture_id: str, channel_name: str, value: int) -> Optional[Fixture]:
        fixture = self.fixtures.get(fixture_id)
        if fixture is None:
            return None
        fixture.values[channel_name] = max(0, min(255, value))
        return fixture

    # ------------------------------------------------------------------
    # Cues
    # ------------------------------------------------------------------
    def add_cue(self, number: float, name: str, fade: float = 0.0, delay: float = 0.0, trigger: str = "go") -> Cue:
        cue = Cue(id=str(uuid.uuid4()), number=number, name=name, fade=fade, delay=delay, trigger=trigger)
        self.cues.append(cue)
        self.cues.sort(key=lambda c: c.number)
        return cue

    def remove_cue(self, cue_id: str) -> bool:
        before = len(self.cues)
        self.cues = [cue for cue in self.cues if cue.id != cue_id]
        return len(self.cues) != before

    # ------------------------------------------------------------------
    # Presets
    # ------------------------------------------------------------------
    def add_preset(self, name: str, preset_type: str, group: str, values: Dict[str, Any]) -> "Optional[Preset]":
        norm_type = preset_type if preset_type in PRESET_TYPES else "dimmer"
        norm_group = str(group).strip()[:60]
        norm_name = str(name).strip()[:80]
        if not norm_name:                                    # kein Name: Typ_1, Typ_2 ... (in der ganzen Show eindeutig)
            taken = {p.name.lower() for p in self.presets.values()}
            n = 1
            while f"{norm_type.capitalize()}_{n}".lower() in taken:
                n += 1
            norm_name = f"{norm_type.capitalize()}_{n}"
        # Variablennamen sind in der ganzen Show eindeutig (Gross-/Kleinschreibung egal): Cues und Programmer verweisen ueber die ID, der Name ist nur die Anzeige
        if any(p.name.lower() == norm_name.lower() for p in self.presets.values()):
            return None
        p = Preset(
            id=str(uuid.uuid4()),
            name=norm_name,
            type=norm_type,
            group=norm_group,
            values=dict(values),
        )
        self.presets[p.id] = p
        self.mark_dirty()
        return p

    def update_preset(self, preset_id: str, **fields: Any) -> "Optional[Preset]":
        p = self.presets.get(preset_id)
        if p is None:
            return None
        # Berechne den zukuenftigen Zustand fuer den Duplikats-Check
        new_name = str(fields["name"]).strip()[:80] or p.name if ("name" in fields and fields["name"] is not None) else p.name
        new_type = p.type                                    # der Typ einer vorhandenen Variable laesst sich nicht aendern (die Werte gehoeren zum Typ)
        new_group = str(fields["group"]).strip()[:60] if ("group" in fields and fields["group"] is not None) else p.group
        # Duplikats-Check (sich selbst ausschliessen): der Name ist in der ganzen Show eindeutig
        if any(pid != preset_id and other.name.lower() == new_name.lower() for pid, other in self.presets.items()):
            return None
        p.name = new_name
        p.type = new_type
        p.group = new_group
        if "values" in fields and isinstance(fields["values"], dict):
            p.values = dict(fields["values"])
        self.mark_dirty()
        return p

    def delete_preset(self, preset_id: str) -> bool:
        removed = self.presets.pop(preset_id, None) is not None
        if removed:
            self.mark_dirty()
        return removed

    def add_preset_group(self, name: str) -> str:
        name = str(name).strip()[:60]
        if name and name not in self.preset_groups:
            self.preset_groups.append(name)
            self.mark_dirty()
        return name

    def delete_preset_group(self, name: str) -> bool:
        if name not in self.preset_groups:
            return False
        self.preset_groups.remove(name)
        # unassign from presets
        for p in self.presets.values():
            if p.group == name:
                p.group = ""
        self.mark_dirty()
        return True

    # ------------------------------------------------------------------
    # CueLists & Cues (Phase 1: Anlegen/Verwalten/hartes Abfeuern)
    # ------------------------------------------------------------------
    def cuelists_as_dicts(self) -> Dict[str, Any]:
        return {cl_id: asdict(cl) for cl_id, cl in self.cuelists.items()}

    def cuelist_name_taken(self, name: str, exclude_id: Optional[str] = None) -> bool:
        """Gibt es schon eine Cue-Liste dieses Namens (Gross-/Kleinschreibung egal)? Eine Liste zaehlt nicht gegen sich selbst."""
        wanted = str(name).strip().lower()
        return any(cid != exclude_id and cl.name.strip().lower() == wanted for cid, cl in self.cuelists.items())

    def _unique_cuelist_name(self, base: str) -> str:
        """base, sonst base 2, base 3 ... (erste freie Zahl)."""
        base = str(base).strip()[:70] or "Cue List"
        if not self.cuelist_name_taken(base):
            return base
        n = 2
        while self.cuelist_name_taken(f"{base} {n}"):
            n += 1
        return f"{base} {n}"

    def add_cuelist(self, name: str) -> Optional[CueList]:
        """Legt eine Liste an. Namen sind eindeutig: ein vergebener Name wird abgelehnt (None), ein leerer bekommt 'Cue List 1', 'Cue List 2' ..."""
        name = str(name or "").strip()[:80]
        if name:
            if self.cuelist_name_taken(name):
                return None
        else:
            n = 1
            while self.cuelist_name_taken(f"Cue List {n}"):
                n += 1
            name = f"Cue List {n}"
        cl = CueList(id=str(uuid.uuid4()), name=name)
        self.cuelists[cl.id] = cl
        if self.active_cuelist_id is None:
            self.active_cuelist_id = cl.id
        self.mark_dirty()
        return cl

    def duplicate_cuelist(self, cuelist_id: str, name: Optional[str] = None) -> Optional[CueList]:
        """Kopiert eine Liste mit allen Cues (neue IDs fuer Liste und Cues; Effekte, Variablen-Verweise, Zeiten bleiben). Die Kopie steht direkt hinter dem Original,
        heisst standardmaessig '<Name> (Kopie)' (bei Bedarf mit Zahl) und wird NICHT aktiv. Gibt None zurueck, wenn die Liste fehlt oder der Wunschname vergeben ist."""
        src = self.cuelists.get(cuelist_id)
        if src is None:
            return None
        name = str(name or "").strip()[:80]
        if name:
            if self.cuelist_name_taken(name):
                return None
        else:
            name = self._unique_cuelist_name(f"{src.name} (Kopie)")
        copy_ = copy.deepcopy(src)
        copy_.id = str(uuid.uuid4())
        copy_.name = name
        for cue in copy_.cues:
            cue.id = str(uuid.uuid4())
        ordered: Dict[str, CueList] = {}
        for cid, cl in self.cuelists.items():
            ordered[cid] = cl
            if cid == cuelist_id:
                ordered[copy_.id] = copy_
        self.cuelists = ordered
        self.mark_dirty()
        return copy_

    def reorder_cuelists(self, order: List[str]) -> bool:
        """Neue Reihenfolge der Listen (Dropdown, Executor-Auswahl ...): unbekannte IDs entfallen, nicht genannte Listen folgen am Ende in ihrer bisherigen Reihenfolge."""
        seen = [cid for cid in dict.fromkeys(str(i) for i in order) if cid in self.cuelists]
        seen += [cid for cid in self.cuelists if cid not in seen]
        if seen == list(self.cuelists):
            return False
        self.cuelists = {cid: self.cuelists[cid] for cid in seen}
        self.mark_dirty()
        return True

    def delete_cuelist(self, cuelist_id: str) -> bool:
        removed = self.cuelists.pop(cuelist_id, None) is not None
        if removed:
            self.active_cue_ids.pop(cuelist_id, None)
            self.cuelist_masters.pop(cuelist_id, None)
            self.cue_layer.pop(cuelist_id, None)
            self.cue_base.pop(cuelist_id, None)
            if self.active_cuelist_id == cuelist_id:
                self.active_cuelist_id = next(iter(self.cuelists), None)
            self.mark_dirty()
        return removed

    def rename_cuelist(self, cuelist_id: str, new_name: str) -> Optional[CueList]:
        cl = self.cuelists.get(cuelist_id)
        if cl is None:
            return None
        new_name = str(new_name).strip()[:80]
        if new_name and self.cuelist_name_taken(new_name, cuelist_id):
            return None                                     # Namen sind eindeutig
        cl.name = new_name or cl.name
        self.mark_dirty()
        return cl

    def set_active_cuelist(self, cuelist_id: str) -> bool:
        """Die im Dropdown der Cue-Listen-Panels gewaehlte Liste. Sie gehoert zum Show-Zustand (wird mit der Show gespeichert
        und geladen); eine Aenderung macht die Show 'ungespeichert'."""
        if cuelist_id not in self.cuelists:
            return False
        if self.active_cuelist_id != cuelist_id:
            self.active_cuelist_id = cuelist_id
            self.mark_dirty()
        return True

    def save_cue(
        self,
        cuelist_id: str,
        fixture_values: Dict[str, Dict[str, Any]],
        number: Optional[float] = None,
        name: Optional[str] = None,
        fade: float = 0.0,
        delay: float = 0.0,
        trigger: str = "go",
        mib: str = "Off",
        cmd: str = "",
        fade_color: Optional[float] = None,
        delay_color: Optional[float] = None,
        fade_pos: Optional[float] = None,
        delay_pos: Optional[float] = None,
        fade_beam: Optional[float] = None,
        delay_beam: Optional[float] = None,
        fade_zoom: Optional[float] = None,
        delay_zoom: Optional[float] = None,
        fx: Optional[Dict[str, Dict[str, str]]] = None,
        fx_order: Optional[Dict[str, Dict[str, int]]] = None,
        fx_fade_in: float = 0.0,
        fx_fade_out: float = 0.0,
        timecode_ms: Any = None,
    ) -> Optional[Cue]:
        """Uebernimmt die aktuell im Programmer gesetzten (relativen) Werte
        als neuen Cue - KEIN voller DMX-Snapshot, nur was tatsaechlich
        angefasst wurde (siehe Cue-Docstring)."""
        cl = self.cuelists.get(cuelist_id)
        if cl is None:
            return None
        if number is None:
            number = (max((c.number for c in cl.cues), default=0.0)) + 1.0
        try:
            number = round(float(number), 3)
        except (TypeError, ValueError):
            number = (max((c.number for c in cl.cues), default=0.0)) + 1.0
        if not name or not str(name).strip():
            name = f"Cue {number:g}"
        cue = Cue(
            id=str(uuid.uuid4()),
            number=number,
            name=str(name).strip()[:80],
            fade=max(0.0, float(fade)),
            delay=max(0.0, float(delay)),
            trigger=trigger if trigger in CUE_TRIGGERS else "go",
            timecode_ms=(_parse_timecode_ms(timecode_ms) or 0) if trigger == "timecode" else None,
            mib=mib if mib in ("Off", "Auto", "On") else "Off",
            cmd=str(cmd).strip()[:200],
            fade_color=_parse_optional_float(fade_color),
            delay_color=_parse_optional_float(delay_color),
            fade_pos=_parse_optional_float(fade_pos),
            delay_pos=_parse_optional_float(delay_pos),
            fade_beam=_parse_optional_float(fade_beam),
            delay_beam=_parse_optional_float(delay_beam),
            fade_zoom=_parse_optional_float(fade_zoom),
            delay_zoom=_parse_optional_float(delay_zoom),
            fixture_values={fid: dict(step) for fid, step in fixture_values.items()},
            fx={fid: dict(cats) for fid, cats in (fx or {}).items() if cats},
            fx_order={fid: dict(cats) for fid, cats in (fx_order or {}).items() if cats},
            fx_fade_in=max(0.0, _parse_optional_float(fx_fade_in) or 0.0),
            fx_fade_out=max(0.0, _parse_optional_float(fx_fade_out) or 0.0),
        )
        cl.cues.append(cue)
        cl.cues.sort(key=lambda c: c.number)
        self.mark_dirty()
        return cue

    def update_cue(self, cuelist_id: str, cue_id: str, **fields: Any) -> Optional[Cue]:
        cl = self.cuelists.get(cuelist_id)
        if cl is None:
            return None
        cue = next((c for c in cl.cues if c.id == cue_id), None)
        if cue is None:
            return None
        if "name" in fields and fields["name"] is not None:
            cue.name = str(fields["name"]).strip()[:80] or cue.name
        if "number" in fields and fields["number"] is not None:
            try:
                cue.number = round(float(fields["number"]), 3)
            except (TypeError, ValueError):
                pass
        if "fade" in fields and fields["fade"] is not None:
            try:
                cue.fade = max(0.0, float(fields["fade"]))
            except (TypeError, ValueError):
                pass
        if "delay" in fields and fields["delay"] is not None:
            try:
                cue.delay = max(0.0, float(fields["delay"]))
            except (TypeError, ValueError):
                pass
        if "trigger" in fields and fields["trigger"] in CUE_TRIGGERS:
            cue.trigger = fields["trigger"]
        if "timecode_ms" in fields and fields["timecode_ms"] is not None:
            parsed_tc = _parse_timecode_ms(fields["timecode_ms"])
            if parsed_tc is not None:
                cue.timecode_ms = parsed_tc
        if cue.trigger == "timecode":
            if cue.timecode_ms is None:
                cue.timecode_ms = 0
        else:
            cue.timecode_ms = None
        if "mib" in fields and fields["mib"] in ("Off", "Auto", "On"):
            cue.mib = fields["mib"]
        if "cmd" in fields and fields["cmd"] is not None:
            cue.cmd = str(fields["cmd"]).strip()[:200]
        # Attribut-spezifische Fade/Delay-Zeiten: ein explizites None im
        # Payload setzt gezielt "nutzt wieder die allgemeine Zeit" zurueck,
        # ein fehlender Schluessel laesst das Feld unveraendert.
        for attr_field in ("fade_color", "delay_color", "fade_pos", "delay_pos", "fade_beam", "delay_beam", "fade_zoom", "delay_zoom"):
            if attr_field in fields:
                setattr(cue, attr_field, _parse_optional_float(fields[attr_field]))
        for fx_field in ("fx_fade_in", "fx_fade_out"):
            if fx_field in fields:
                setattr(cue, fx_field, max(0.0, _parse_optional_float(fields[fx_field]) or 0.0))
        cl.cues.sort(key=lambda c: c.number)
        self.mark_dirty()
        return cue

    def delete_cue(self, cuelist_id: str, cue_id: str) -> bool:
        cl = self.cuelists.get(cuelist_id)
        if cl is None:
            return False
        before = len(cl.cues)
        cl.cues = [c for c in cl.cues if c.id != cue_id]
        removed = len(cl.cues) != before
        if removed:
            if self.active_cue_ids.get(cuelist_id) == cue_id:
                self.active_cue_ids.pop(cuelist_id, None)
            self.mark_dirty()
        return removed

    # ------------------------------------------------------------------
    # Executor-Master (Fader je Cue-Liste)
    # ------------------------------------------------------------------
    def effective_master(self, fixture_id: str) -> float:
        """Faktor in Prozent fuer den Dimmer-Kanal: der Grand Master, bei Blackout 0 (der Executor-Fader mischt Werte, er skaliert nicht)."""
        return 0.0 if self.blackout else self.grand_master

    def set_cuelist_master(self, cuelist_id: str, value: Any) -> Optional[float]:
        if cuelist_id not in self.cuelists:
            return None
        self.cuelist_masters[cuelist_id] = _clamp_percent(value)
        return self.cuelist_masters[cuelist_id]

    def mix_level(self, cuelist_id: str) -> float:
        """Executor-Fader der Liste als Faktor 0..1 (1 = voller Cue-Wert)."""
        return self.cuelist_masters.get(cuelist_id, 100.0) / 100.0

    @classmethod
    def mix_abstract(cls, base: Dict[str, Any], layer: Dict[str, Any], f: float) -> Dict[str, Any]:
        """Mischt die Cue-Werte (layer) linear mit den manuellen Werten (base): f = 1 -> Cue, f = 0 -> manuell. Gilt fuer
        jedes Attribut (Skalare und Farbe je Kanal); fehlt ein manueller Wert, gilt der Neutralwert."""
        out: Dict[str, Any] = {}
        for attr, cue_value in layer.items():
            if f >= 1.0:
                out[attr] = copy.deepcopy(cue_value)
                continue
            manual = base.get(attr)
            if manual is None:
                manual = cls._neutral_value(attr)
            if attr in DISCRETE_ATTRS or raw_offset(attr) is not None:
                out[attr] = copy.deepcopy(cue_value if f >= 0.5 else manual)           # Raeder/rohe Kanaele: umschalten statt ueberblenden
            elif attr == "color":
                out[attr] = {k: float(manual.get(k, 0)) + (float(cue_value.get(k, 0)) - float(manual.get(k, 0))) * f
                             for k in ("r", "g", "b")}
            else:
                out[attr] = float(manual) + (float(cue_value) - float(manual)) * f
        return out

    def release_layers(self, fixture_id: str, attrs: Any = None) -> None:
        """Der Programmer uebernimmt diese Attribute der Fixture: die Cue-Listen mischen sie nicht mehr (bis zum naechsten Go)."""
        for table in (self.cue_layer, self.cue_base):
            for fixtures in table.values():
                entry = fixtures.get(fixture_id)
                if entry is None:
                    continue
                if attrs is None:
                    fixtures.pop(fixture_id, None)
                else:
                    for attr in attrs:
                        entry.pop(attr, None)

    def rebuild_layers(self) -> None:
        """Nach dem Laden einer Show: der Stand der aktiven Cues (inkl. Tracking) bildet je Liste die Cue-Schicht; der
        manuelle Wert ist der Programmer-Wert, sonst der Neutralwert."""
        self.cue_layer, self.cue_base = {}, {}
        for cl_id, cue_id in self.active_cue_ids.items():
            cl = self.cuelists.get(cl_id)
            idx = next((i for i, c in enumerate(cl.cues) if c.id == cue_id), None) if cl else None
            if idx is None:
                continue
            tracked = self._tracked_values(cl, idx)
            self.cue_layer[cl_id] = {fid: copy.deepcopy(vals) for fid, vals in tracked.items() if fid in self.fixtures}
            self.cue_base[cl_id] = {fid: {a: copy.deepcopy(self.programmer_values[fid][a]) for a in vals
                                           if a in self.programmer_values.get(fid, {})}
                                     for fid, vals in self.cue_layer[cl_id].items()}

    # ------------------------------------------------------------------
    # Cue-Nummern (Dezimalwerte), Speichern auf bestehende Nummer, Update der aktiven Cue
    # ------------------------------------------------------------------
    @staticmethod
    def parse_cue_number(value: Any) -> Optional[float]:
        try:
            number = round(float(str(value).strip().replace(",", ".")), 3)
        except (TypeError, ValueError):
            return None
        return number if math.isfinite(number) and number >= 0 else None

    @staticmethod
    def find_cue_by_number(cl: CueList, number: float, exclude_id: Optional[str] = None) -> Optional[Cue]:
        return next((c for c in cl.cues if c.id != exclude_id and abs(c.number - number) < 1e-6), None)

    def step_refs(self, step: Dict[str, Any]) -> Dict[str, str]:
        """Die Variablen-Verweise eines Cue-Eintrags: {Typ: preset_id} (aelteres Format {"preset_uuid": id} = der Typ dieses Presets)."""
        refs = {t: str(pid) for t, pid in (step.get("refs") or {}).items() if t in PRESET_TYPES and pid}
        legacy = step.get("preset_uuid")
        if legacy:
            preset = self.presets.get(legacy)
            if preset is not None:
                refs.setdefault(preset.type, legacy)
        return refs

    def step_values(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """Ein Cue-Eintrag als Dict abstrakter Werte: feste Werte, darueber die LIVE aufgeloesten Variablen (fehlt eine Variable, entfallen ihre Werte)."""
        from app.dmx_resolve import preset_to_abstract
        values = copy.deepcopy(step.get("values", {})) if isinstance(step.get("values"), dict) else {}
        for ptype, pid in self.step_refs(step).items():
            preset = self.presets.get(pid)
            if preset is None:
                continue
            for attr in PRESET_TYPE_ATTRS.get(ptype, ()):
                values.pop(attr, None)
            values.update(copy.deepcopy(preset_to_abstract(preset)))
        return values

    _step_values = step_values            # alter Name (Aufrufer in diesem Modul)

    def _merge_step(self, old: Optional[Dict[str, Any]], new: Dict[str, Any]) -> Dict[str, Any]:
        """Nur das, was `new` enthaelt, ueberschreibt den bisherigen Eintrag; der Rest bleibt wie er war. Variablen bleiben dabei Verweise:
        eine neue Variable ersetzt die alte desselben Typs, ein fester Wert loest eine betroffene alte Variable auf (ihre uebrigen Werte bleiben fest)."""
        if old is None:
            return copy.deepcopy(new)
        refs = self.step_refs(old)
        values = copy.deepcopy(old.get("values", {})) if isinstance(old.get("values"), dict) else {}
        new_refs = self.step_refs(new)
        new_values = copy.deepcopy(new.get("values", {})) if isinstance(new.get("values"), dict) else {}
        # feste Werte ueberschreiben: eine alte Variable, die so ein Attribut abdeckt, wird zu festen Werten (nur ihre uebrigen bleiben erhalten)
        for attr in list(new_values):
            for ptype in [t for t in refs if attr in PRESET_TYPE_ATTRS.get(t, ())]:
                preset = self.presets.get(refs.pop(ptype))
                if preset is not None:
                    from app.dmx_resolve import preset_to_abstract
                    for key, val in preset_to_abstract(preset).items():
                        values.setdefault(key, copy.deepcopy(val))
        values.update(new_values)
        for ptype, pid in new_refs.items():
            refs[ptype] = pid
            for attr in PRESET_TYPE_ATTRS.get(ptype, ()):
                values.pop(attr, None)
        merged: Dict[str, Any] = {"values": values}
        if refs:
            merged["refs"] = refs
        return merged

    def _merge_content(self, cue: Cue, fixture_values: Dict[str, Dict[str, Any]],
                       fx: Optional[Dict[str, Dict[str, str]]], fx_order: Optional[Dict[str, Dict[str, int]]]) -> None:
        for fid, step in fixture_values.items():
            cue.fixture_values[fid] = self._merge_step(cue.fixture_values.get(fid), step)
        for fid, cats in (fx or {}).items():
            if cats:
                cue.fx.setdefault(fid, {}).update(cats)
        for fid, cats in (fx_order or {}).items():
            if cats:
                cue.fx_order.setdefault(fid, {}).update(cats)

    def store_cue(self, cuelist_id: str, fixture_values: Dict[str, Dict[str, Any]], number: Any = None,
                  mode: Optional[str] = None, position: Optional[str] = None, after_cue_id: Optional[str] = None,
                  fx: Optional[Dict[str, Dict[str, str]]] = None,
                  fx_order: Optional[Dict[str, Dict[str, int]]] = None, name: Optional[str] = None, **fields: Any):
        """Speichert den Programmer-Stand als Cue. Liefert (status, daten):
        "created" | "merged" | "overwritten" (daten = Cue), "conflict" (die Nummer gibt es schon, kein mode angegeben;
        daten = der bestehende Cue), "out_of_bounds" (daten = {"lower", "upper"}), "invalid" | "error".
        mode "merge": nur die gesendeten Kanaele/Effekte kommen in den bestehenden Cue, der Rest bleibt;
        mode "overwrite": der Inhalt des bestehenden Cues wird komplett ersetzt (Zeiten/Trigger/CMD bleiben)."""
        cl = self.cuelists.get(cuelist_id)
        if cl is None:
            return "error", None
        if number is None or str(number).strip() == "":
            cue = self.save_cue(cuelist_id, fixture_values, number=None, name=name, fx=fx, fx_order=fx_order, **fields)
            return ("created", cue) if cue else ("error", None)
        n = self.parse_cue_number(number)
        if n is None:
            return "invalid", None
        existing = self.find_cue_by_number(cl, n)
        if existing is None:
            # Einfuegen: Position "end" = hinter dem letzten Cue, "after" = zwischen dem Cue und seinem Nachfolger
            if position == "end" and cl.cues and n <= cl.cues[-1].number:
                return "out_of_bounds", {"lower": cl.cues[-1].number, "upper": None}
            if position == "after":
                idx = next((i for i, c in enumerate(cl.cues) if c.id == after_cue_id), None)
                if idx is None:
                    return "error", None
                lower = cl.cues[idx].number
                upper = cl.cues[idx + 1].number if idx + 1 < len(cl.cues) else None
                if not (lower < n and (upper is None or n < upper)):
                    return "out_of_bounds", {"lower": lower, "upper": upper}
            cue = self.save_cue(cuelist_id, fixture_values, number=n, name=name, fx=fx, fx_order=fx_order, **fields)
            return ("created", cue) if cue else ("error", None)
        if mode == "merge":
            self._merge_content(existing, fixture_values, fx, fx_order)
        elif mode == "overwrite":
            existing.fixture_values = {fid: copy.deepcopy(step) for fid, step in fixture_values.items()}
            existing.fx = {fid: dict(cats) for fid, cats in (fx or {}).items() if cats}
            existing.fx_order = {fid: dict(cats) for fid, cats in (fx_order or {}).items() if cats}
        else:
            return "conflict", existing
        if name and str(name).strip():
            existing.name = str(name).strip()[:80]
        self.mark_dirty()
        return ("merged" if mode == "merge" else "overwritten"), existing

    def _tracked_values(self, cl: CueList, upto_index: int) -> Dict[str, Dict[str, Any]]:
        """Stand (fixture -> Attribute), den die Cues 0..upto_index hinterlassen: jeder Cue ueberschreibt nur die
        Attribute, die er enthaelt (Tracking)."""
        state: Dict[str, Dict[str, Any]] = {}
        for cue in cl.cues[:upto_index + 1]:
            for fid, step in cue.fixture_values.items():
                state.setdefault(fid, {}).update(self._step_values(step))
        return state

    def update_active_cue(self, cuelist_id: str, fixture_values: Dict[str, Dict[str, Any]],
                          fx: Optional[Dict[str, Dict[str, str]]] = None,
                          fx_order: Optional[Dict[str, Dict[str, int]]] = None, mode: str = "normal"):
        """Uebernimmt die aktuellen Programmer-Werte in den AKTIVEN Cue der Liste (nur die angefassten Attribute, der
        Rest des Cues bleibt). Liefert (status, cue): "updated" | "no_active_cue" | "empty" | "error".

        mode "normal": nur dieser Cue wird geaendert. OpenCue verfolgt Werte von Cue zu Cue (ein Cue enthaelt nur,
        was er aendert, alles andere bleibt stehen) - Folge-Cues, die ein Attribut nicht selbst setzen, uebernehmen
        den neuen Wert daher beim Abspielen automatisch (Tracking).
        mode "only": wie "normal", zusaetzlich wird der Folge-Cue so ergaenzt, dass er weiterhin den bisherigen Wert
        erreicht: fuer jedes geaenderte Attribut, das der Folge-Cue nicht selbst enthaelt, bekommt er den Wert, den
        die Cue-Liste davor hatte (bei noch nie gesetzten Attributen den Neutralwert)."""
        cl = self.cuelists.get(cuelist_id)
        if cl is None:
            return "error", None
        cue_id = self.active_cue_ids.get(cuelist_id)
        idx = next((i for i, c in enumerate(cl.cues) if c.id == cue_id), None)
        if idx is None:
            return "no_active_cue", None
        if not fixture_values and not fx:
            return "empty", None
        cue = cl.cues[idx]
        before = self._tracked_values(cl, idx)                 # Stand NACH diesem Cue, vor der Aenderung
        self._merge_content(cue, fixture_values, fx, fx_order)
        if mode == "only" and idx + 1 < len(cl.cues):
            nxt = cl.cues[idx + 1]
            for fid, step in fixture_values.items():
                new_vals = self._step_values(step)
                old_vals = before.get(fid, {})
                changed = {a: v for a, v in new_vals.items() if old_vals.get(a) != v}
                if not changed:
                    continue
                nxt_vals = self._step_values(nxt.fixture_values[fid]) if fid in nxt.fixture_values else {}
                blocked = {}
                for attr in changed:
                    if attr in nxt_vals:
                        continue                                # der Folge-Cue setzt das Attribut selbst
                    blocked[attr] = copy.deepcopy(old_vals[attr]) if attr in old_vals else self._neutral_value(attr)
                if blocked:
                    nxt_vals.update(blocked)
                    nxt.fixture_values[fid] = {"values": nxt_vals}
        self.mark_dirty()
        return "updated", cue

    @staticmethod
    def _neutral_value(attr: str) -> Any:
        if attr == "color":
            return {"r": 0, "g": 0, "b": 0}
        return 50.0 if attr in ("pan", "tilt") else 0.0

    def renumber_cue(self, cuelist_id: str, cue_id: str, number: Any, on_conflict: Optional[str] = None):
        """Gibt einem Cue eine neue Nummer. Liefert (status, daten): "ok" (daten = Cue), "conflict" (daten = der
        Cue, der die Nummer schon hat), "merged" / "overwritten" (daten = verbleibender Cue), "invalid" | "error".
        on_conflict "merge": der Inhalt des verschobenen Cues wird in den bestehenden uebernommen (nur dessen
        Kanaele ueberschreiben), der verschobene Cue entfaellt; "overwrite": der bestehende Cue entfaellt, der
        verschobene bekommt die Nummer."""
        cl = self.cuelists.get(cuelist_id)
        cue = next((c for c in cl.cues if c.id == cue_id), None) if cl else None
        if cue is None:
            return "error", None
        n = self.parse_cue_number(number)
        if n is None:
            return "invalid", None
        other = self.find_cue_by_number(cl, n, exclude_id=cue_id)
        if other is None:
            cue.number = n
            cl.cues.sort(key=lambda c: c.number)
            self.mark_dirty()
            return "ok", cue
        if on_conflict == "merge":
            self._merge_content(other, cue.fixture_values, cue.fx, cue.fx_order)
            survivor, removed = other, cue
        elif on_conflict == "overwrite":
            survivor, removed = cue, other
            cue.number = n
        else:
            return "conflict", other
        cl.cues = [c for c in cl.cues if c.id != removed.id]
        cl.cues.sort(key=lambda c: c.number)
        if self.active_cue_ids.get(cuelist_id) == removed.id:
            self.active_cue_ids[cuelist_id] = survivor.id
        self.mark_dirty()
        return ("merged" if on_conflict == "merge" else "overwritten"), survivor

    @staticmethod
    def first_cue(cl) -> Optional[Cue]:
        """Erster Cue einer Liste: die kleinste Cue-Nummer > 0 (Nummern koennen Dezimalzahlen sein);
        gibt es keine positive Nummer, der erste Eintrag."""
        if not cl.cues:
            return None
        positive = [c for c in cl.cues if c.number > 0]
        return min(positive, key=lambda c: c.number) if positive else cl.cues[0]

    def step_cue(self, cuelist_id: str, direction: int) -> Optional[Cue]:
        """"Go" (direction=+1) oder "Stop/Back" (direction=-1): wechselt den
        aktiven Cue der CueList zum naechsten/vorherigen in sortierter
        Reihenfolge. Ohne aktiven Cue startet Go beim ersten, Back beim
        letzten Cue. Am Listenende laeuft Go zum ersten Cue um, Zurueck am Listenanfang zur letzten.
        Markiert die Show NICHT als dirty - reine Wiedergabe-Position."""
        cl = self.cuelists.get(cuelist_id)
        if cl is None or not cl.cues:
            return None
        current_id = self.active_cue_ids.get(cuelist_id)
        if current_id is None:
            new_cue = cl.cues[0] if direction >= 0 else cl.cues[-1]
        else:
            idx = next((i for i, c in enumerate(cl.cues) if c.id == current_id), None)
            if idx is None:
                new_cue = cl.cues[0] if direction >= 0 else cl.cues[-1]
            else:
                new_idx = idx + (1 if direction >= 0 else -1)
                if new_idx >= len(cl.cues) and direction >= 0:
                    # Go am Listenende: Umlauf zum ersten Cue (kleinste Nummer > 0). Bei nur einem Cue
                    # startet dieser einfach neu. Zurueck am Listenanfang bleibt wirkungslos.
                    new_cue = self.first_cue(cl)
                elif new_idx < 0:
                    # Zurueck am Listenanfang: Umlauf zur letzten Cue (wie Go nach der letzten Cue zur ersten springt)
                    new_cue = cl.cues[-1]
                else:
                    new_cue = cl.cues[new_idx]
        self.active_cue_ids[cuelist_id] = new_cue.id
        return new_cue

    # ------------------------------------------------------------------
    # Server-autoritative Programmer-Selektion + "touched"-Werte
    # (Command Line, siehe app/command_line.py; auch von server.py's
    # set_fixture_values-Handler fuer Maus-/Fader-Bedienung nachgefuehrt)
    # ------------------------------------------------------------------
    def set_selection(self, ids: List[str]) -> List[str]:
        """Setzt die serverseitige Fixture-Selektion - unbekannte IDs werden
        stillschweigend verworfen. Rueckgabe ist die tatsaechlich
        uebernommene, gefilterte Liste."""
        self.selected_fixture_ids = [i for i in ids if i in self.fixtures]
        return self.selected_fixture_ids

    def set_programmer_value(self, fixture_id: str, attr: str, value: Any) -> None:
        if fixture_id not in self.fixtures:
            return
        self.drop_programmer_refs(fixture_id, [attr])
        self.programmer_values.setdefault(fixture_id, {})[attr] = value

    def set_programmer_values(self, fixture_id: str, values: Dict[str, Any]) -> None:
        """Manuelle Programmer-Werte (Fader, Befehlszeile): ein fester Wert loest die Variable ab, die dieses Attribut vorgab.
        Das Anwenden einer Variable selbst setzt ihre Verknuepfung danach mit set_programmer_ref()."""
        if fixture_id not in self.fixtures or not values:
            return
        self.drop_programmer_refs(fixture_id, values.keys())
        self.programmer_values.setdefault(fixture_id, {}).update(values)

    def set_programmer_ref(self, fixture_id: str, preset_type: str, preset_id: str) -> None:
        if fixture_id in self.fixtures and preset_type in PRESET_TYPES:
            self.programmer_refs.setdefault(fixture_id, {})[preset_type] = preset_id

    def drop_programmer_refs(self, fixture_id: str, attrs: Any = None, types: Any = None) -> bool:
        """Entfernt die Variablen-Verknuepfungen einer Fixture, die eines der Attribute `attrs` (oder einen der Typen `types`) abdecken.
        attrs und types leer = alle. Gibt zurueck, ob sich etwas geaendert hat."""
        refs = self.programmer_refs.get(fixture_id)
        if not refs:
            return False
        attrs = set(attrs) if attrs is not None else None
        types = set(types) if types is not None else None
        changed = False
        for ptype in list(refs):
            hit = (types is not None and ptype in types) or (attrs is not None and any(a in attrs for a in PRESET_TYPE_ATTRS.get(ptype, ())))
            if (attrs is None and types is None) or hit:
                refs.pop(ptype, None)
                changed = True
        if not refs:
            self.programmer_refs.pop(fixture_id, None)
        return changed

    def programmer_refs_payload(self) -> Dict[str, Dict[str, str]]:
        return {fid: dict(refs) for fid, refs in self.programmer_refs.items() if refs and fid in self.fixtures}

    def clear_programmer(self, fixture_ids: Optional[List[str]] = None) -> List[str]:
        """Leert NUR die programmer_values-Tracking-Struktur (reine
        State-Schicht - kennt kein DMX/keine GDTF-Kanalaufloesung). Der
        tatsaechliche Blackout/Reset der DMX-Ausgabe (Dimmer/Farbe/Position/
        Beam auf Neutralwerte) passiert VOR diesem Aufruf im jeweiligen
        Aufrufer (siehe app/command_line.py's "Clear Clear"-Handler,
        apply_full_baseline_reset) - dort ist dmx_resolve/dmx_engine verfuegbar.

        fixture_ids=None leert den GESAMTEN Programmer (dot2 "Clear
        Clear"). Gibt die tatsaechlich betroffenen Fixture-IDs zurueck -
        der Aufrufer broadcastet das als programmer_cleared, damit alle
        Clients auch ihre lokale "touched"-Markierung (rote Punkte) aufraeumen."""
        if fixture_ids is None:
            affected = list(self.programmer_values.keys())
            self.programmer_values = {}
            self.programmer_refs = {}
            return affected
        affected = [fid for fid in fixture_ids if fid in self.programmer_values]
        for fid in affected:
            self.programmer_values.pop(fid, None)
            self.programmer_refs.pop(fid, None)
        return affected

    def get_programmer_snapshot(self) -> Dict[str, Dict[str, Any]]:
        """Serverseitiges Aequivalent zu ProgrammerState.getCueSnapshot() im
        Frontend - baut das fuer Cue.fixture_values erwartete Format
        {fixture_id: {"values": {...}}} aus den aktuell getrackten
        "touched" Werten. Variablen, die im Programmer anliegen, werden als Verweise gespeichert (refs), alles andere als feste Werte."""
        out: Dict[str, Dict[str, Any]] = {}
        for fid, vals in self.programmer_values.items():
            if not vals:
                continue
            refs = {t: pid for t, pid in self.programmer_refs.get(fid, {}).items()
                    if pid in self.presets and any(a in vals for a in PRESET_TYPE_ATTRS.get(t, ()))}
            covered = {a for t in refs for a in PRESET_TYPE_ATTRS.get(t, ())}
            step: Dict[str, Any] = {"values": {a: v for a, v in vals.items() if a not in covered}}
            if refs:
                step["refs"] = refs
            out[fid] = step
        return out

    # ------------------------------------------------------------------
    # Panels (Edit-Mode-Desktop)
    # ------------------------------------------------------------------
    def panels_as_dicts(self) -> List[Dict[str, Any]]:
        return [asdict(panel) for panel in self.panels]

    def _find_panel(self, panel_id: str) -> Optional[Panel]:
        return next((p for p in self.panels if p.id == panel_id), None)

    def add_panel(self, panel_type: str) -> Panel:
        from app.panel_registry import PanelRegistry  # deferred to avoid circular import
        # New panels must always land on top of everything already on the
        # desktop - default=9 so an empty workspace's first panel still
        # gets the Panel dataclass's own default of 10, same as before.
        highest = max((p.z_index for p in self.panels), default=9)
        # background_color/text_color/header_background_color/drop_shadow
        # come from the configurable "Panel Defaults" (Settings modal)
        # rather than the Panel dataclass's own hardcoded defaults - lets an
        # admin set a house style for future panels. width/height and
        # module_config come from the PanelRegistry (type-specific defaults).
        panel_info = PanelRegistry.get(panel_type)
        panel = Panel(
            id=str(uuid.uuid4()),
            type=panel_type,
            z_index=highest + 1,
            width=panel_info.default_width if panel_info else 32.0,
            height=panel_info.default_height if panel_info else 46.0,
            background_color=self.panel_defaults["background_color"],
            text_color=self.panel_defaults["text_color"],
            header_background_color=self.panel_defaults["header_background_color"],
            drop_shadow=bool(self.panel_defaults["shadow_enabled"]),
            corner_style=self.panel_defaults.get("corner_style", "global"),
            show_header=panel_info.default_show_header if panel_info else True,
            module_config=dict(panel_info.default_module_config) if panel_info else {},
        )
        self.panels.append(panel)
        self.save_app_config()
        return panel

    def set_panel_ui_state(self, panel_id: str, ui_state: Dict[str, Any]) -> bool:
        panel = self._find_panel(panel_id)
        if panel is None or not isinstance(ui_state, dict):
            return False
        panel.ui_state = ui_state
        return True

    def update_panel(self, panel_id: str, **fields: Any) -> Optional[Panel]:
        panel = self._find_panel(panel_id)
        if panel is None:
            return None

        _min_size = MIN_COMPACT_PANEL_SIZE if panel.type in COMPACT_PANEL_TYPES else MIN_PANEL_SIZE
        if "x" in fields and fields["x"] is not None:
            panel.x = max(0.0, min(100.0 - _min_size, float(fields["x"])))
        if "y" in fields and fields["y"] is not None:
            panel.y = max(0.0, min(100.0 - _min_size, float(fields["y"])))
        if "width" in fields and fields["width"] is not None:
            panel.width = max(_min_size, min(100.0, float(fields["width"])))
        if "height" in fields and fields["height"] is not None:
            panel.height = max(_min_size, min(100.0, float(fields["height"])))
        if "title" in fields and fields["title"] is not None:
            panel.title = str(fields["title"]).strip()[:60]
        if "show_header" in fields and fields["show_header"] is not None:
            panel.show_header = bool(fields["show_header"])
        if "panel_scale" in fields and fields["panel_scale"] is not None:
            try:
                panel.panel_scale = max(MIN_PANEL_SCALE, min(MAX_PANEL_SCALE, float(fields["panel_scale"])))
            except (TypeError, ValueError):
                pass
        if "border_color" in fields and _is_valid_hex_color(fields["border_color"]):
            panel.border_color = fields["border_color"]
        if "background_color" in fields and _is_valid_hex_color(fields["background_color"]):
            panel.background_color = fields["background_color"]
        if "text_color" in fields and _is_valid_hex_color(fields["text_color"]):
            panel.text_color = fields["text_color"]
        if "header_background_color" in fields and _is_valid_hex_color(fields["header_background_color"]):
            panel.header_background_color = fields["header_background_color"]
        if "accent_color" in fields and _is_valid_hex_color(fields["accent_color"]):
            panel.accent_color = fields["accent_color"]
        if "use_custom_accent" in fields and fields["use_custom_accent"] is not None:
            panel.use_custom_accent = bool(fields["use_custom_accent"])
        if "drop_shadow" in fields and fields["drop_shadow"] is not None:
            panel.drop_shadow = bool(fields["drop_shadow"])
        if fields.get("corner_style") in ("global", "round", "square"):
            panel.corner_style = fields["corner_style"]
        if "z_index" in fields and fields["z_index"] is not None:
            try:
                panel.z_index = int(fields["z_index"])
            except (TypeError, ValueError):
                pass
        if "module_config" in fields and isinstance(fields.get("module_config"), dict):
            panel.module_config = {**panel.module_config, **fields["module_config"]}

        self.save_app_config()
        return panel

    def delete_panel(self, panel_id: str) -> bool:
        before = len(self.panels)
        self.panels = [p for p in self.panels if p.id != panel_id]
        changed = len(self.panels) != before
        if changed:
            self.save_app_config()
        return changed

    # ---- Layer-Reihenfolge (Rechtsklick-Kontextmenue / Properties-Modal) --
    def bring_panel_to_front(self, panel_id: str) -> Optional[Panel]:
        panel = self._find_panel(panel_id)
        if panel is None:
            return None
        highest = max((p.z_index for p in self.panels), default=panel.z_index)
        panel.z_index = highest + 1
        self.save_app_config()
        return panel

    def send_panel_to_back(self, panel_id: str) -> Optional[Panel]:
        panel = self._find_panel(panel_id)
        if panel is None:
            return None
        lowest = min((p.z_index for p in self.panels), default=panel.z_index)
        panel.z_index = lowest - 1
        self.save_app_config()
        return panel

    def move_panel_layer(self, panel_id: str, delta: int) -> Optional[Panel]:
        """delta is typically +1 ("Move Layer Up") or -1 ("Move Layer Down")."""
        panel = self._find_panel(panel_id)
        if panel is None:
            return None
        try:
            panel.z_index += int(delta)
        except (TypeError, ValueError):
            pass
        self.save_app_config()
        return panel

    # ---- Duplizieren / Kopieren / Einfuegen (Bearbeitungsmodus) -----------
    PASTE_OFFSET = (2.0, 3.0)   # Versatz je Schritt in Prozent der Arbeitsflaeche
    PASTE_LIMIT = 50

    def paste_panels(self, items: Any) -> List[Panel]:
        """Legt Kopien der uebergebenen Panel-Beschreibungen an (Gruppe bleibt zusammen, neue IDs, oberste Ebene).
        Position: das Original bzw. die Gruppe um einen Versatz verschoben, an die naechste Stelle, an der kein Panel
        mit derselben linken oberen Ecke liegt und alles innerhalb der Arbeitsflaeche bleibt. Gibt die neuen Panels
        zurueck (leer, wenn nichts Gueltiges uebergeben wurde)."""
        from app.panel_registry import PanelRegistry  # deferred to avoid circular import
        self.last_pasted_ids = []
        if not isinstance(items, list):
            return []
        sources = [dict(i) for i in items[: self.PASTE_LIMIT]
                   if isinstance(i, dict) and PanelRegistry.get(str(i.get("type", ""))) is not None]
        if not sources:
            return []
        for item in sources:
            item["module_config"] = copy.deepcopy(item.get("module_config")) if isinstance(item.get("module_config"), dict) else {}
            item["ui_state"] = {}
        copies = panels_from_dicts(sources)
        min_x = min(p.x for p in copies)
        min_y = min(p.y for p in copies)
        max_x = max(p.x + p.width for p in copies)
        max_y = max(p.y + p.height for p in copies)
        taken = [(p.x, p.y) for p in self.panels]

        def fits(dx: float, dy: float) -> bool:
            if min_x + dx < 0 or min_y + dy < 0 or max_x + dx > 100.0 or max_y + dy > 100.0:
                return False
            return not any(abs(p.x + dx - tx) < 1.0 and abs(p.y + dy - ty) < 1.0 for p in copies for tx, ty in taken)

        step_x, step_y = self.PASTE_OFFSET
        chosen = None
        for k in range(1, 21):
            for sx, sy in ((1, 1), (-1, 1), (1, -1), (-1, -1)):
                if fits(sx * k * step_x, sy * k * step_y):
                    chosen = (sx * k * step_x, sy * k * step_y)
                    break
            if chosen:
                break
        if chosen is None:                      # nichts frei: Versatz festhalten, aber im sichtbaren Bereich bleiben
            chosen = (max(-min_x, min(step_x, 100.0 - max_x)), max(-min_y, min(step_y, 100.0 - max_y)))
        highest = max((p.z_index for p in self.panels), default=9)
        for index, panel in enumerate(copies):
            panel.id = str(uuid.uuid4())
            panel.x = round(max(0.0, min(100.0 - panel.width, panel.x + chosen[0])), 2)
            panel.y = round(max(0.0, min(100.0 - panel.height, panel.y + chosen[1])), 2)
            panel.z_index = highest + 1 + index
            self.panels.append(panel)
        self.last_pasted_ids = [p.id for p in copies]
        self.save_app_config()
        return copies

    def duplicate_panels(self, panel_ids: Any) -> List[Panel]:
        wanted = [str(i) for i in panel_ids] if isinstance(panel_ids, list) else []
        return self.paste_panels([asdict(p) for p in self.panels if p.id in wanted])

    def delete_panels(self, panel_ids: Any) -> int:
        wanted = {str(i) for i in panel_ids} if isinstance(panel_ids, list) else set()
        before = len(self.panels)
        self.panels = [p for p in self.panels if p.id not in wanted]
        removed = before - len(self.panels)
        if removed:
            self.save_app_config()
        return removed

    # ------------------------------------------------------------------
    # Globale App-Einstellungen (gui_scale, language, DMX/Netzwerk)
    # ------------------------------------------------------------------
    def set_gui_scale(self, scale: float) -> float:
        self.gui_scale = max(MIN_GUI_SCALE, min(MAX_GUI_SCALE, float(scale)))
        self.save_app_config()
        return self.gui_scale

    def set_language(self, language: str) -> str:
        self.language = language if language in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE
        self.save_app_config()
        return self.language

    def set_remote_enabled(self, enabled: bool) -> bool:
        self.remote_enabled = bool(enabled)
        self.save_app_config()
        return self.remote_enabled

    def set_server_port(self, port: Any) -> bool:
        """Speichert den Server-Port (1024-65535). Wirksam erst nach einem Neustart."""
        try:
            port = int(port)
        except (TypeError, ValueError):
            return False
        if not (MIN_SERVER_PORT <= port <= MAX_SERVER_PORT):
            return False
        self.server_port = port
        self.save_app_config()
        return True

    def set_remote_password(self, password: str) -> bool:
        """Setzt das Remote-Passwort (mind. 4 Zeichen, max. 64). False bei ungueltigem Wert."""
        password = str(password)
        if not (4 <= len(password) <= 64):
            return False
        self.remote_password = password
        self.save_app_config()
        return True

    def set_artnet_enabled(self, enabled: bool) -> bool:
        self.artnet_enabled = bool(enabled)
        self.save_app_config()
        return self.artnet_enabled

    def set_artnet_ip(self, ip: str) -> str:
        """Setzt die Art-Net "Target IP" (Ziel-/Broadcast-Adresse)."""
        try:
            ipaddress.ip_address(ip)
            self.artnet_ip = ip
        except (ValueError, TypeError):
            pass  # ungueltige Eingabe - vorherigen Wert beibehalten
        self.save_app_config()
        return self.artnet_ip

    def set_artnet_bind_ip(self, ip: str) -> str:
        """Setzt die lokale Sende-Interface-Adresse ("Bind IP"). Ein
        leerer String ist gueltig und bedeutet "Betriebssystem waehlt"."""
        if ip == "":
            self.artnet_bind_ip = ""
        else:
            try:
                ipaddress.ip_address(ip)
                self.artnet_bind_ip = ip
            except (ValueError, TypeError):
                pass
        self.save_app_config()
        return self.artnet_bind_ip

    def set_sacn_enabled(self, enabled: bool) -> bool:
        self.sacn_enabled = bool(enabled)
        self.save_app_config()
        return self.sacn_enabled

    def set_enttec_enabled(self, enabled: bool) -> bool:
        self.enttec_enabled = bool(enabled)
        self.save_app_config()
        return self.enttec_enabled

    def set_enttec_port(self, port: str) -> str:
        self.enttec_port = str(port).strip()[:64]
        self.save_app_config()
        return self.enttec_port

    def set_enttec_universe(self, universe: Any) -> int:
        try:
            universe = int(universe)
        except (TypeError, ValueError):
            universe = self.enttec_universe
        self.enttec_universe = max(MIN_UNIVERSE, min(MAX_UNIVERSE, universe))
        self.save_app_config()
        return self.enttec_universe

    def set_default_universe(self, universe: Any) -> int:
        try:
            universe = int(universe)
        except (TypeError, ValueError):
            universe = self.default_universe
        self.default_universe = max(MIN_UNIVERSE, min(MAX_UNIVERSE, universe))
        self.save_app_config()
        return self.default_universe

    # ------------------------------------------------------------------
    # Appearance / Theme
    # ------------------------------------------------------------------
    def theme_payload(self) -> Dict[str, Any]:
        return {"base": self.theme["base"], "tokens": dict(self.theme["tokens"]), "radius": self.theme["radius"]}

    def theme_profiles_payload(self) -> Dict[str, Dict[str, Any]]:
        return {name: {"base": t["base"], "tokens": dict(t["tokens"]), "radius": t["radius"]}
                for name, t in self.theme_profiles.items()}

    def set_theme(self, theme: Any = None, **fields: Any) -> Dict[str, Any]:
        """Ersetzt das aktive Theme durch ein (geprueftes) Theme-Objekt und speichert es."""
        self.theme = normalize_theme(theme if theme is not None else fields)
        self.save_app_config()
        return self.theme_payload()

    @staticmethod
    def _clean_profile_name(name: Any) -> str:
        return re.sub(r"\s+", " ", str(name or "")).strip()[:60]

    # ---- Farbprofile als Dateien: themes/<Name>.json = {"opencue_theme": 1, "name": ..., "theme": {base, tokens, radius}} ----------------------------------
    # self.theme_profiles (Name -> Theme) ist der Arbeitsstand im Speicher; jede Aenderung schreibt/loescht/benennt die Datei, und reload_theme_profiles() liest den
    # Ordner neu ein (Start, Dateimanager: Upload/ZIP). Dateiname = Profilname ohne verbotene Zeichen; bei gleichem Dateinamen kommt " (2)" dazu.
    _THEME_FILE_FORBIDDEN = re.compile(r'[\\/:*?"<>|\x00-\x1f]')

    def _theme_filename(self, name: str, own: Optional[str] = None) -> str:
        """Freier Dateiname fuer das Profil `name` (own = sein bisheriger Dateiname zaehlt nicht als belegt)."""
        stem = self._THEME_FILE_FORBIDDEN.sub("_", name).strip(". ")[:60] or "Profil"
        taken = {f.lower() for n, f in self._theme_files.items() if f != own}
        candidate, index = stem + ".json", 2
        while candidate.lower() in taken:
            candidate = f"{stem} ({index}).json"
            index += 1
        return candidate

    def _write_theme_file(self, name: str) -> None:
        directory = _paths.themes_dir()
        filename = self._theme_files.get(name) or self._theme_filename(name)
        self._theme_files[name] = filename
        payload = {"opencue_theme": 1, "name": name, "theme": self.theme_profiles[name]}
        target = directory / filename
        partial = directory / ("." + filename + ".part")
        partial.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        partial.replace(target)

    def _remove_theme_file(self, name: str) -> None:
        filename = self._theme_files.pop(name, None)
        if filename:
            try:
                (_paths.themes_dir() / filename).unlink(missing_ok=True)
            except OSError:
                pass

    def reload_theme_profiles(self) -> None:
        """Ordner themes/ neu einlesen: Dateien sind die Wahrheit (neu = dazu, geloescht = weg, geaendert = uebernommen)."""
        found: Dict[str, Dict[str, Any]] = {}
        files: Dict[str, str] = {}
        directory = _paths.themes_dir()
        for path in sorted(directory.glob("*.json"), key=lambda p: p.name.lower()):
            if path.name.startswith("."):
                continue
            try:
                content = json.loads(path.read_text(encoding="utf-8-sig"))
            except (OSError, ValueError):
                continue
            if not isinstance(content, dict):
                continue
            raw = content.get("theme") if isinstance(content.get("theme"), dict) else content
            if not isinstance(raw, dict) or not ("tokens" in raw or "base" in raw):
                continue
            name = self._clean_profile_name(content.get("name") or path.stem)
            if not name or name in found or len(found) >= MAX_THEME_PROFILES:
                continue
            found[name] = normalize_theme(raw)
            files[name] = path.name
        self.theme_profiles = found
        self._theme_files = files

    def _migrate_theme_profiles_to_files(self) -> None:
        """Beim Laden der Konfiguration: Profile, die dort noch stehen (aeltere Version), werden Dateien; was schon als Datei existiert, bleibt (Datei gewinnt)."""
        legacy = dict(self.theme_profiles)
        self.reload_theme_profiles()
        for name, theme in legacy.items():
            if name not in self.theme_profiles and len(self.theme_profiles) < MAX_THEME_PROFILES:
                self.theme_profiles[name] = theme
                self._write_theme_file(name)

    def save_theme_profile(self, name: Any, theme: Any = None) -> Optional[str]:
        """Speichert (oder ueberschreibt) ein Profil. Ohne `theme` wird das aktive Theme gesichert."""
        clean = self._clean_profile_name(name)
        if not clean or (clean not in self.theme_profiles and len(self.theme_profiles) >= MAX_THEME_PROFILES):
            return None
        self.theme_profiles[clean] = normalize_theme(theme if theme is not None else self.theme_payload())
        self._write_theme_file(clean)
        return clean

    def rename_theme_profile(self, name: Any, new_name: Any) -> Optional[str]:
        clean = self._clean_profile_name(new_name)
        if name not in self.theme_profiles or not clean or (clean != name and clean in self.theme_profiles):
            return None
        if clean == name:
            return clean
        own = self._theme_files.pop(name, None)
        self.theme_profiles = {(clean if key == name else key): value for key, value in self.theme_profiles.items()}
        self._theme_files[clean] = self._theme_filename(clean, own=own)      # die Datei bekommt den neuen Namen (der Inhalt traegt ihn ebenfalls)
        self._write_theme_file(clean)
        if own and own != self._theme_files[clean]:
            try:
                (_paths.themes_dir() / own).unlink(missing_ok=True)
            except OSError:
                pass
        return clean

    def duplicate_theme_profile(self, name: Any) -> Optional[str]:
        if name not in self.theme_profiles or len(self.theme_profiles) >= MAX_THEME_PROFILES:
            return None
        index = 2
        while f"{name} {index}"[:60] in self.theme_profiles:
            index += 1
        copy_name = f"{name} {index}"[:60]
        source = self.theme_profiles[name]
        self.theme_profiles[copy_name] = {"base": source["base"], "tokens": dict(source["tokens"]), "radius": source["radius"]}
        self._write_theme_file(copy_name)
        return copy_name

    def delete_theme_profile(self, name: Any) -> bool:
        if name not in self.theme_profiles:
            return False
        del self.theme_profiles[name]
        self._remove_theme_file(name)
        return True

    def import_theme_profile(self, name: str, theme: Any) -> Dict[str, Any]:
        """Profil aus einer Datei (Upload/ZIP): gleicher Name + gleicher Inhalt = uebersprungen, gleicher Name + anderer Inhalt = Kopie 'Name (2)', sonst neu.
        Rueckgabe {name, file, status: created|identical|copy, original}."""
        original = self._clean_profile_name(name) or "Profil"
        normalized = normalize_theme(theme)
        candidate, index = original, 1
        while candidate in self.theme_profiles:
            if self.theme_profiles[candidate] == normalized:
                return {"name": candidate, "file": self._theme_files.get(candidate, ""), "status": "identical", "original": None}
            index += 1
            candidate = f"{original} ({index})"[:60]
        if len(self.theme_profiles) >= MAX_THEME_PROFILES:
            raise ValueError("too_many")
        self.theme_profiles[candidate] = normalized
        self._write_theme_file(candidate)
        return {"name": candidate, "file": self._theme_files[candidate], "status": "created" if candidate == original else "copy", "original": original if candidate != original else None}

    def set_panel_defaults(self, **fields: Any) -> Dict[str, Any]:
        """Wie set_theme(), nur fuer die "Panel Defaults" - drei Hex-Farben
        plus ein Bool (shadow_enabled). Wirkt sich ausschliesslich auf
        zukuenftig via add_panel() erstellte Panels aus."""
        for key in ("background_color", "text_color", "header_background_color"):
            if key in fields and _is_valid_hex_color(fields[key]):
                self.panel_defaults[key] = fields[key]
        if "shadow_enabled" in fields and fields["shadow_enabled"] is not None:
            self.panel_defaults["shadow_enabled"] = bool(fields["shadow_enabled"])
        if fields.get("corner_style") in PANEL_CORNER_STYLES:
            self.panel_defaults["corner_style"] = fields["corner_style"]
        self.save_app_config()
        return dict(self.panel_defaults)

    def reset_settings_to_defaults(self) -> Dict[str, Any]:
        """Setzt ausschliesslich die im Settings-Modal editierbaren Felder
        (General/DMX-Network/Appearance) auf ihre Werkseinstellungen zurueck
        - bewusst ohne Panels/Showfile, das ist "Reset Defaults" fuer die
        App-Einstellungen, kein Zuruecksetzen des kompletten Arbeitsplatzes."""
        self.gui_scale = 1.0
        self.language = DEFAULT_LANGUAGE
        self.artnet_enabled = True
        self.artnet_ip = DEFAULT_ARTNET_IP
        self.artnet_bind_ip = DEFAULT_ARTNET_BIND_IP
        self.sacn_enabled = False
        self.default_universe = MIN_UNIVERSE
        self.enttec_enabled = False
        self.enttec_port = ""
        self.enttec_universe = MIN_UNIVERSE
        self.theme = default_theme()   # gespeicherte Profile bleiben bewusst erhalten
        self.panel_defaults = dict(DEFAULT_PANEL_DEFAULTS)
        self.save_app_config()
        return {
            "gui_scale": self.gui_scale,
            "language": self.language,
            "artnet_enabled": self.artnet_enabled,
            "artnet_ip": self.artnet_ip,
            "artnet_bind_ip": self.artnet_bind_ip,
            "sacn_enabled": self.sacn_enabled,
            "default_universe": self.default_universe,
            "enttec_enabled": self.enttec_enabled,
            "enttec_port": self.enttec_port,
            "enttec_universe": self.enttec_universe,
            "theme": self.theme_payload(),
            "panel_defaults": dict(self.panel_defaults),
        }

    # ------------------------------------------------------------------
    # Fenster-Geometrie (Position/Groesse/Maximiert-Status)
    # ------------------------------------------------------------------
    def save_window_geometry(
        self,
        x: Optional[int],
        y: Optional[int],
        width: Optional[int],
        height: Optional[int],
        maximized: bool,
    ) -> None:
        """Wird von main.py beim Schliessen des Fensters aufgerufen.

        x/y/width/height duerfen None sein (z.B. wenn das Fenster die ganze
        Sitzung ueber maximiert war und nie eine "normale" Geometrie hatte) -
        beim naechsten Start startet main.py dann einfach maximiert.

        WICHTIG: Es gibt bewusst KEINEN `is_fullscreen`-Parameter. Der
        exklusive F11-Fullscreen ist ein rein temporaerer, manuell
        ausgeloester Ansichtsmodus, kein dauerhaft gewuenschter Fenster-
        Zustand - main.py haelt/persistiert diesen Zustand deshalb nirgends
        (siehe main.py's window_geometry["is_fullscreen"]). Nach jedem
        Neustart landet OpenCue immer im normalen Fenster- bzw.
        Fenster-Vollbild-Modus (maximized), nie automatisch im exklusiven
        Fullscreen - auch dann nicht, wenn die App waehrend eines aktiven
        F11-Ausflugs geschlossen wurde.
        """
        self.window_x = x
        self.window_y = y
        self.window_width = width
        self.window_height = height
        self.window_maximized = bool(maximized)
        self.save_app_config()

    def load_app_config(self) -> None:
        """Laedt globale App-Settings aus app_config.json, falls vorhanden.

        Fehlt die Datei (erster Start) oder ist sie beschaedigt, bleiben die
        bereits gesetzten Default-Werte unveraendert - kein Absturz.
        """
        if not APP_CONFIG_PATH.exists():
            return

        try:
            data = json.loads(APP_CONFIG_PATH.read_text(encoding="utf-8-sig"))
        except (json.JSONDecodeError, OSError):
            return

        self.gui_scale = max(MIN_GUI_SCALE, min(MAX_GUI_SCALE, float(data.get("gui_scale", self.gui_scale))))

        language = data.get("language", self.language)
        self.language = language if language in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE

        self.artnet_enabled = bool(data.get("artnet_enabled", self.artnet_enabled))

        self.remote_enabled = bool(data.get("remote_enabled", self.remote_enabled))
        password = data.get("remote_password", self.remote_password)
        self.remote_password = password if isinstance(password, str) and password else DEFAULT_REMOTE_PASSWORD
        try:
            port = int(data.get("server_port", self.server_port))
            if MIN_SERVER_PORT <= port <= MAX_SERVER_PORT:
                self.server_port = port
        except (TypeError, ValueError):
            pass

        try:
            ipaddress.ip_address(data.get("artnet_ip", self.artnet_ip))
            self.artnet_ip = data.get("artnet_ip", self.artnet_ip)
        except (ValueError, TypeError):
            pass

        bind_ip = data.get("artnet_bind_ip", self.artnet_bind_ip)
        if bind_ip == "":
            self.artnet_bind_ip = ""
        else:
            try:
                ipaddress.ip_address(bind_ip)
                self.artnet_bind_ip = bind_ip
            except (ValueError, TypeError):
                pass

        self.sacn_enabled = bool(data.get("sacn_enabled", self.sacn_enabled))

        try:
            universe = int(data.get("default_universe", self.default_universe))
            self.default_universe = max(MIN_UNIVERSE, min(MAX_UNIVERSE, universe))
        except (TypeError, ValueError):
            pass

        self.enttec_enabled = bool(data.get("enttec_enabled", self.enttec_enabled))
        self.enttec_port = str(data.get("enttec_port", self.enttec_port)).strip()[:64]
        try:
            eu = int(data.get("enttec_universe", self.enttec_universe))
            self.enttec_universe = max(MIN_UNIVERSE, min(MAX_UNIVERSE, eu))
        except (TypeError, ValueError):
            pass

        saved_theme = data.get("theme", {})
        if isinstance(saved_theme, dict) and "accent_color" in saved_theme and "tokens" not in saved_theme:
            self.theme = migrate_legacy_theme(saved_theme)   # Konfiguration aus der Zeit vor den Tokens
        else:
            self.theme = normalize_theme(saved_theme)
        # Alte Konfiguration (vor Schema 2): der frühere Standard-Rundungsgrad 7 gilt als "nicht angepasst"
        # und wird auf den neuen Standard (eckig) gehoben. Ein anderer Wert war eine bewusste Wahl und bleibt.
        legacy_theme_schema = int(data.get("theme_schema", 1) or 1) < THEME_SCHEMA
        if legacy_theme_schema and self.theme["radius"] == OLD_DEFAULT_RADIUS:
            self.theme["radius"] = DEFAULT_RADIUS
        saved_profiles = data.get("theme_profiles", {})
        if isinstance(saved_profiles, dict):
            for profile_name, profile in saved_profiles.items():
                clean = self._clean_profile_name(profile_name)
                if clean:
                    loaded = normalize_theme(profile)
                    if legacy_theme_schema and loaded["radius"] == OLD_DEFAULT_RADIUS:
                        loaded["radius"] = DEFAULT_RADIUS
                    self.theme_profiles[clean] = loaded

        self._migrate_theme_profiles_to_files()           # Profile, die noch in der Konfiguration standen, werden Dateien (Ordner themes/)
        saved_panel_defaults = data.get("panel_defaults", {})
        if isinstance(saved_panel_defaults, dict):
            for key in ("background_color", "text_color", "header_background_color"):
                value = saved_panel_defaults.get(key)
                if _is_valid_hex_color(value):
                    if value.lower() == LEGACY_PANEL_DEFAULTS[key]:
                        continue  # alter Standard -> neuer Standard
                    self.panel_defaults[key] = value
            if "shadow_enabled" in saved_panel_defaults:
                self.panel_defaults["shadow_enabled"] = bool(saved_panel_defaults["shadow_enabled"])
            if saved_panel_defaults.get("corner_style") in PANEL_CORNER_STYLES:
                self.panel_defaults["corner_style"] = saved_panel_defaults["corner_style"]

        # Die Panels selbst stehen NICHT in der app_config.json, sondern nur im Layout (layouts/*.json). Ein alter Schluessel "panels"
        # wird ignoriert und beim naechsten Speichern entfernt.

        # (frueherer Schluessel "remote_layouts_seeded" gilt weiter)
        self.example_layouts_seeded = bool(data.get("example_layouts_seeded", data.get("remote_layouts_seeded", False)))
        self.first_start_done = bool(data.get("first_start_done", True))
        self.update_check_enabled = bool(data.get("update_check_enabled", True))
        self.update_skipped_version = str(data.get("update_skipped_version", "") or "")[:40]

        # Zuletzt geladenes Layout der Konsole laden (Name in der Config, Panels aus der Layout-Datei). Fehlt die Datei, waehlt
        # server._adopt_startup_layout() beim Start ein anderes. panels_from_dicts filtert auf bekannte Panel-Felder
        # (alte/kuenftige Schluessel loesen keinen TypeError aus) und stellt sicher, dass module_config immer ein dict ist.
        last_layout = data.get("last_active_layout")
        if last_layout and isinstance(last_layout, str):
            self.last_active_layout = last_layout
            _safe = re.sub(r'[\\/:*?"<>|]', '_', last_layout.strip())[:60] or "layout"
            _lpath = _paths.LAYOUTS_DIR / f"{_safe}.json"
            if _lpath.exists():
                try:
                    _ldata = json.loads(_lpath.read_text(encoding="utf-8"))
                    self.panels = panels_from_dicts(_ldata.get("panels", []))
                except Exception:
                    pass

        self.window_x = data.get("window_x", self.window_x)
        self.window_y = data.get("window_y", self.window_y)
        self.window_width = data.get("window_width", self.window_width)
        self.window_height = data.get("window_height", self.window_height)
        self.window_maximized = bool(data.get("window_maximized", self.window_maximized))

        last = data.get("last_showfile_path")
        if last:
            p = Path(last)
            if p.exists():
                self.last_showfile_path = last
            else:
                # Fallback: gleicher Dateiname im aktuellen SHOWFILES_DIR suchen
                # (z.B. nach Pfad-Migration oder Ordner-Verschiebung)
                candidate = _paths.SHOWFILES_DIR / p.name
                if candidate.exists():
                    self.last_showfile_path = str(candidate)

        cdp = data.get("custom_data_path", "")
        self.custom_data_path = str(cdp).strip() if cdp else ""

        raw_room = data.get("sim_room")
        if isinstance(raw_room, dict):
            self.sim_room = raw_room
        self.cmd_suggestions = bool(data.get("cmd_suggestions", True))
        raw_favorites = data.get("fx_favorites")
        if isinstance(raw_favorites, list):
            self.fx_favorites = list(dict.fromkeys(str(x) for x in raw_favorites if isinstance(x, str)))

    def set_cmd_suggestions(self, enabled: Any) -> bool:
        self.cmd_suggestions = enabled is True or str(enabled).lower() in ("1", "true", "on")
        self.save_app_config()
        return self.cmd_suggestions

    def toggle_fx_favorite(self, name: str) -> bool:
        """Effekt-Skript als Liebling markieren/entmarkieren. Gibt zurueck, ob er jetzt ein Liebling ist."""
        if name in self.fx_favorites:
            self.fx_favorites.remove(name)
            favorite = False
        else:
            self.fx_favorites.append(name)
            favorite = True
        self.save_app_config()
        return favorite

    def forget_fx_favorite(self, name: str, new_name: str = "") -> None:
        """Skript wurde geloescht (new_name leer) oder umbenannt: die Lieblingsmarke folgt."""
        if name not in self.fx_favorites:
            return
        index = self.fx_favorites.index(name)
        self.fx_favorites.remove(name)
        if new_name and new_name not in self.fx_favorites:
            self.fx_favorites.insert(index, new_name)
        self.save_app_config()

    def save_app_config(self) -> None:
        """Schreibt die globalen App-Settings auf Disk (ohne Panels: die gehoeren ins Layout, siehe layouts/*.json)."""
        if self._panel_scope_active:
            return  # Remote-Client bearbeitet sein eigenes Layout: Host-Config unberuehrt
        data = {
            "gui_scale": self.gui_scale,
            "language": self.language,
            "artnet_enabled": self.artnet_enabled,
            "artnet_ip": self.artnet_ip,
            "artnet_bind_ip": self.artnet_bind_ip,
            "sacn_enabled": self.sacn_enabled,
            "default_universe": self.default_universe,
            "enttec_enabled": self.enttec_enabled,
            "enttec_port": self.enttec_port,
            "enttec_universe": self.enttec_universe,
            "remote_enabled": self.remote_enabled,
            "remote_password": self.remote_password,
            "server_port": self.server_port,
            "theme_schema": THEME_SCHEMA,
            "theme": self.theme_payload(),
            "panel_defaults": dict(self.panel_defaults),
            "window_x": self.window_x,
            "window_y": self.window_y,
            "window_width": self.window_width,
            "window_height": self.window_height,
            "window_maximized": self.window_maximized,
            "last_showfile_path": self.last_showfile_path,
            "last_active_layout": self.last_active_layout,
            "example_layouts_seeded": self.example_layouts_seeded,
            "first_start_done": self.first_start_done,
            "update_check_enabled": self.update_check_enabled,
            "update_skipped_version": self.update_skipped_version,
            "custom_data_path": self.custom_data_path,
            "sim_room": self.sim_room,
            "fx_favorites": list(self.fx_favorites),
            "cmd_suggestions": self.cmd_suggestions,
        }
        with self._config_lock:
            APP_CONFIG_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")

    # ------------------------------------------------------------------
    # Showfile-Persistenz (JSON auf Disk unter /showfiles)
    # Enthaelt ausschliesslich Show-Daten - keine globalen App-Einstellungen.
    # ------------------------------------------------------------------
    def _showfile_dict(self) -> Dict[str, Any]:
        return {
            "showfile_name": self.showfile_name,
            "saved_at": datetime.now().isoformat(timespec="seconds"),
            "fixtures": {fx_id: asdict(fx) for fx_id, fx in self.fixtures.items()},
            # Die Show enthaelt nur ihre eigenen Daten (Scheinwerfer, Cues, Presets, Effekt-Definitionen ...). Dateien (GDTF, Effekt-Skripte, Buehnen, Medien) liegen in den
            # lokalen Ordnern; beim Weitergeben packt der Export (ZIP, app/file_manager.py) sie dazu.
            "fx_effects": {fx_id: dict(fx) for fx_id, fx in self.fx_effects.items()},
            "sim_stage": sim_stages.store.reference(),     # aktive Buehne der 3D-Simulation: Verweis auf die Buehnen-Datei, Raum-Einstellungen, Scheinwerfer-Positionen
#3D-AUS#             # Raum und Rig der 3D-Buehne immer als vollstaendige Kopie (Export/Import ohne die lokalen Bibliotheksdateien); *_source = Herkunft in der Bibliothek
#3D-AUS#             "room3d": self.room,
#3D-AUS#             "room3d_source": self.room_source,
#3D-AUS#             "rig3d": self._rig_for_file(),
#3D-AUS#             "rig3d_source": self.rig_source,
            "groups": self.groups,
            "cues": [asdict(cue) for cue in self.cues],
            "presets": {pid: asdict(p) for pid, p in self.presets.items()},
            "preset_groups": list(self.preset_groups),
            "fx_groups": list(self.fx_groups),
            "cuelists": self.cuelists_as_dicts(),
            "active_cuelist_id": self.active_cuelist_id,
            "media": {mid: media_store.public_meta(meta) for mid, meta in self.media.items()},
            "runtime_state": {
                "grand_master": self.grand_master,
                "cuelist_masters": dict(self.cuelist_masters),
                "active_cue_ids": dict(self.active_cue_ids),
                "fx_assignments": {
                    fid: {cat: dict(a) for cat, a in cats.items()}
                    for fid, cats in self.fx_assignments.items() if cats
                },
                "programmer_values": {
                    fx_id: dict(vals) for fx_id, vals in self.programmer_values.items() if vals
                },
                "programmer_refs": self.programmer_refs_payload(),
                "dmx_universes": self._dmx_universes_for_file(),
            },
        }

#3D-AUS#     def _rig_for_file(self) -> Dict[str, Any]:
#3D-AUS#         stage3d.stamp_fixture_info(self.rig, self.fixtures)           # FID/Name zu den Positionen: Grundlage zum Wiederverwenden in anderen Shows
#3D-AUS#         stage3d.refresh_world(self.rig, self.room)                    # Weltstand: das Rig findet auch ohne seine Traverse zurueck
#3D-AUS#         return self.rig

    def owned_dmx_channels(self) -> Dict[int, set]:
        """Universum -> Menge der DMX-Kanaele (ab 1), die Scheinwerfer DIESER Show belegen. Alles andere im Ausgabepuffer ist Ueberbleibsel einer frueheren Show
        (der Puffer wird beim Showwechsel nicht geleert) und gehoert nicht in die Show-Datei - und wird beim Laden nicht wiederhergestellt."""
        owned: Dict[int, set] = {}
        for fx in self.fixtures.values():
            count = max(1, int(getattr(fx, "channel_count", 1) or 1))
            owned.setdefault(int(fx.universe), set()).update(range(int(fx.start_channel), int(fx.start_channel) + count))
        return owned

    def _dmx_universes_for_file(self) -> Dict[str, Dict[str, int]]:
        if self.dmx_state_provider is None:
            return {}
        owned = self.owned_dmx_channels()
        universes: Dict[str, Dict[str, int]] = {}
        for universe, values in self.dmx_state_provider().items():
            mine = owned.get(int(universe), set())
            nonzero = {str(ch + 1): int(v) for ch, v in enumerate(values) if v and (ch + 1) in mine}
            if nonzero:
                universes[str(universe)] = nonzero
        return universes

    def save_showfile(self, name: Optional[str] = None, save_dir: Optional[Path] = None) -> Path:
        if name:
            self.showfile_name = name

        sim_stages.store.persist()                      # die Buehne gehoert zur Show: ungespeicherte Aenderungen kommen mit in ihre Datei
        data = self._showfile_dict()

        if save_dir is not None:
            directory = save_dir
        elif self.showfile_path and not name:
            # Overwrite: keep original location
            directory = Path(self.showfile_path).parent
        else:
            directory = _paths.SHOWFILES_DIR
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{self.showfile_name}.json"
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        self.showfile_path = str(path)
        self.last_showfile_path = str(path)
        self.is_dirty = False
        self.save_app_config()
        return path

    def load_showfile(self, path: str | Path) -> None:
        path = Path(path)
        data = json.loads(path.read_text(encoding="utf-8"))
        legacy_show.unpack(data)                                      # Altformat (Dateien in der Showfile): einmalig in die lokalen Ordner legen

        self.showfile_name = data.get("showfile_name", "Untitled")

        known_fx_fields = set(Fixture.__dataclass_fields__)
        loaded_fixtures: Dict[str, Fixture] = {}
        for fx_id, fx_data in data.get("fixtures", {}).items():
            filtered = {k: v for k, v in fx_data.items() if k in known_fx_fields}
            loaded_fixtures[fx_id] = Fixture(**filtered)
        # backfill fid for old showfiles that don't have it
        if any(fx.fid == 0 for fx in loaded_fixtures.values()):
            for i, fx in enumerate(loaded_fixtures.values(), start=1):
                fx.fid = i

        # UUID-Migration: Fixtures mit ungültigem ID-Format erhalten eine neue UUID.
        # Die Scheinwerfer-Referenzen in Gruppen werden mitgenommen.
        fx_id_remap: Dict[str, str] = {}
        for old_id in list(loaded_fixtures):
            fx = loaded_fixtures[old_id]
            if not _is_valid_uuid(old_id) or not _is_valid_uuid(fx.id) or old_id != fx.id:
                new_id = str(uuid.uuid4())
                fx_id_remap[old_id] = new_id
                fx.id = new_id
                loaded_fixtures[new_id] = fx
                del loaded_fixtures[old_id]

        self.fixtures = loaded_fixtures

        raw_groups = data.get("groups", {})
        if fx_id_remap:
            # Gruppen-Referenzen auf neue UUIDs anpassen
            raw_groups = {
                grp: [fx_id_remap.get(fid, fid) for fid in ids]
                for grp, ids in raw_groups.items()
            }
        self.groups = {str(g): [str(i) for i in ids] for g, ids in raw_groups.items() if isinstance(ids, list)}
        self.prune_groups()

        self.cues = [_normalize_cue_trigger(Cue(**{k: v for k, v in cue.items() if k in Cue.__dataclass_fields__})) for cue in data.get("cues", [])]

        # Load presets
        known_preset_fields = set(Preset.__dataclass_fields__)
        loaded_presets: Dict[str, Preset] = {}
        for pid, pdata in data.get("presets", {}).items():
            filtered = {k: v for k, v in pdata.items() if k in known_preset_fields}
            try:
                loaded_presets[pid] = Preset(**filtered)
            except (TypeError, KeyError):
                pass

        # UUID-Migration: Presets mit ungültigem ID-Format erhalten eine neue UUID.
        preset_migrated = False
        for old_pid in list(loaded_presets):
            p = loaded_presets[old_pid]
            if not _is_valid_uuid(old_pid) or not _is_valid_uuid(p.id) or old_pid != p.id:
                new_pid = str(uuid.uuid4())
                p.id = new_pid
                loaded_presets[new_pid] = p
                del loaded_presets[old_pid]
                preset_migrated = True

        self.presets = loaded_presets
        self.preset_groups = [str(g) for g in data.get("preset_groups", []) if isinstance(g, str)]
        self.fx_groups = [str(g) for g in data.get("fx_groups", []) if isinstance(g, str)]
        self.fx_effects = {
            str(fx_id): migrate_fx_definition(fx)
            for fx_id, fx in (data.get("fx_effects") or {}).items() if isinstance(fx, dict)
        }

        # Load cuelists (Cue-Execution-System)
        known_cue_fields = set(Cue.__dataclass_fields__)
        loaded_cuelists: Dict[str, CueList] = {}
        cuelist_migrated = False
        for cl_id, cl_data in data.get("cuelists", {}).items():
            cues: List[Cue] = []
            for cue_data in cl_data.get("cues", []):
                # Altformat-Migration: frueheres fade_in/fade_out-Paar wurde
                # durch ein einzelnes `fade`-Feld ersetzt (fade_out entfaellt
                # ersatzlos) - den alten Einblendwert nicht stillschweigend
                # verwerfen, falls noch kein `fade` vorhanden ist.
                if "fade" not in cue_data and "fade_in" in cue_data:
                    cue_data = {**cue_data, "fade": cue_data["fade_in"]}
                filtered = {k: v for k, v in cue_data.items() if k in known_cue_fields}
                try:
                    cue = Cue(**filtered)
                except (TypeError, KeyError):
                    continue
                if not _is_valid_uuid(cue.id):
                    cue.id = str(uuid.uuid4())
                    cuelist_migrated = True
                cues.append(_normalize_cue_trigger(cue))
            cl = CueList(id=str(cl_data.get("id", cl_id)), name=str(cl_data.get("name", "Cue List")), cues=cues)
            if not _is_valid_uuid(cl.id) or cl.id != cl_id:
                cl.id = str(uuid.uuid4())
                cuelist_migrated = True
            loaded_cuelists[cl.id] = cl

        self.cuelists = loaded_cuelists
        active_cl = data.get("active_cuelist_id")
        self.active_cuelist_id = active_cl if active_cl in self.cuelists else next(iter(self.cuelists), None)

        sim_stages.store.restore(data.get("sim_stage"))          # 3D-Simulation: die eingebettete Buehne gilt; Show ohne Buehne = leere Buehne

#3D-AUS#         # 3D-Buehne: die eingebettete gilt (nicht eine gleichnamige lokale Datei); alte Shows ohne 3D-Daten = Standard-Buehne
#3D-AUS#         legacy_room, legacy_rig = stage3d.split_legacy(data["stage3d"]) if isinstance(data.get("stage3d"), dict) else (None, None)     # erste, kombinierte Fassung
#3D-AUS#         self.room = stage3d.normalize_room(data["room3d"]) if isinstance(data.get("room3d"), dict) else (legacy_room or stage3d.default_room())
#3D-AUS#         self.rig = stage3d.normalize_rig(data["rig3d"]) if isinstance(data.get("rig3d"), dict) else (legacy_rig or stage3d.default_rig())
#3D-AUS#         room_source, rig_source = data.get("room3d_source"), data.get("rig3d_source")
#3D-AUS#         if room_source is None and legacy_room is not None:
#3D-AUS#             room_source = data.get("stage3d_source")
#3D-AUS#         self.room_source = room_source if isinstance(room_source, str) and stage3d.valid_filename(room_source) else None
#3D-AUS#         self.rig_source = rig_source if isinstance(rig_source, str) and stage3d.valid_filename(rig_source) else None

        # Medien: nur Metadaten; fehlt die Datei im Medien-Ordner, bleibt der Eintrag als 'fehlt' sichtbar
        self.media = {}
        for entry in (data.get("media") or {}).values():
            meta = media_store.clean_entry(entry)
            if meta is not None:
                self.media[meta["id"]] = meta

        runtime = data.get("runtime_state")
        self.runtime_state_loaded = isinstance(runtime, dict)
        runtime = runtime if isinstance(runtime, dict) else {}
        self.grand_master = _clamp_percent(runtime.get("grand_master", 100.0))
        self.cuelist_masters = {
            str(cl_id): _clamp_percent(v)
            for cl_id, v in (runtime.get("cuelist_masters") or {}).items() if cl_id in self.cuelists
        }
        self.cue_layer, self.cue_base = {}, {}
        self.active_cue_ids = {
            cl_id: cue_id
            for cl_id, cue_id in (runtime.get("active_cue_ids") or {}).items()
            if cl_id in self.cuelists and any(c.id == cue_id for c in self.cuelists[cl_id].cues)
        }
        self.fx_assignments = {}
        for fid, cats in (runtime.get("fx_assignments") or {}).items():
            if fid not in self.fixtures or not isinstance(cats, dict):
                continue
            kept = {
                cat: dict(a) for cat, a in cats.items()
                if cat in fx_categories.CATEGORIES and isinstance(a, dict)
                and a.get("fx_id") in self.fx_effects
            }
            if kept:
                self.fx_assignments[fid] = kept
        self.programmer_values = {
            fx_id: dict(vals)
            for fx_id, vals in (runtime.get("programmer_values") or {}).items()
            if fx_id in self.fixtures and isinstance(vals, dict)
        }
        self.programmer_refs = {
            fx_id: {t: pid for t, pid in refs.items() if t in PRESET_TYPES and pid in self.presets}
            for fx_id, refs in (runtime.get("programmer_refs") or {}).items()
            if fx_id in self.fixtures and isinstance(refs, dict)
        }
        self.programmer_refs = {fid: refs for fid, refs in self.programmer_refs.items() if refs}
        self.rebuild_layers()          # Cue-Schicht der aktiven Cues (Executor-Fader) nach dem Laden
        dmx_saved = runtime.get("dmx_universes")
        owned = self.owned_dmx_channels()
        self.restored_dmx_universes = (
            {
                int(universe): {int(ch): int(v) for ch, v in chans.items() if int(ch) in owned.get(int(universe), set())}      # nur Kanaele der Scheinwerfer dieser Show (aeltere Dateien tragen Ueberbleibsel anderer Shows)
                for universe, chans in dmx_saved.items()
            }
            if isinstance(dmx_saved, dict) else None
        )

        # Panels leben ausschliesslich in Panel-Layout-Dateien (panel_layouts/).
        # Showfiles enthalten keine Panel-Strukturdaten mehr - die Panel-
        # Anordnung bleibt beim Laden eines Showfiles unveraendert erhalten.

        self.showfile_path = str(path)
        self.last_showfile_path = str(path)
        self.is_dirty = False

        # Migrierte Showfiles werden NICHT automatisch zurueckgeschrieben - die
        # Migration bleibt im Speicher, die Show gilt als ungespeichert und wird
        # erst durch ein ausdruecklich gewaehltes Speichern auf Disk geschrieben.
        if fx_id_remap or preset_migrated or cuelist_migrated:
            self.is_dirty = True


def panels_from_dicts(items: List[Dict[str, Any]]) -> List[Panel]:
    known = set(Panel.__dataclass_fields__)
    panels: List[Panel] = []
    for item in items:
        if item.get("type") == "stage3d":                   # 3D-Buehne ist (vorerst) entfernt: alte Layouts mit diesem Panel laden ohne es (siehe _old/3d_buehne/)
            continue
        filtered = {k: v for k, v in item.items() if k in known}
        if "module_config" in filtered and not isinstance(filtered["module_config"], dict):
            filtered["module_config"] = {}
        panels.append(Panel(**filtered))
    return panels


class PanelUndoHistory:
    """Undo/Redo fuer Panel-Aenderungen (Anordnung, Groesse, Eigenschaften,
    Regler-Werte). Gespeichert werden Snapshots der Panel-Liste vor einer
    Aenderung. Live-Zustand (DMX, Programmer, UI-Scroll) ist nicht Teil davon."""

    LIMIT = 100

    def __init__(self) -> None:
        self._undo: List[List[Dict[str, Any]]] = []
        self._redo: List[List[Dict[str, Any]]] = []

    def record(self, before: List[Dict[str, Any]]) -> None:
        self._undo.append(before)
        del self._undo[:-self.LIMIT]
        self._redo.clear()

    def undo(self, current: List[Dict[str, Any]]) -> Optional[List[Dict[str, Any]]]:
        if not self._undo:
            return None
        self._redo.append(current)
        return self._undo.pop()

    def redo(self, current: List[Dict[str, Any]]) -> Optional[List[Dict[str, Any]]]:
        if not self._redo:
            return None
        self._undo.append(current)
        return self._redo.pop()

    def clear(self) -> None:
        self._undo.clear()
        self._redo.clear()


# Einzige, global geteilte Instanz - von server.py und dmx_engine.py importiert
state = StateManager()
undo_history = PanelUndoHistory()
