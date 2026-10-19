"""
panel_registry.py
Zentrale Registry aller Panel-Typen von OpenCue.

Jeder Panel-Typ beschreibt sich durch:
  - panel_type     : interner Schlüssel (z.B. "dmx_monitor")
  - panel_name     : i18n-Schlüssel oder Anzeigename für die UI
  - default_width  : Standard-Breite in % des Viewports
  - default_height : Standard-Höhe in % des Viewports
  - default_module_config : Starteinstellungen für die Panel-Instanz
  - get_module_properties_schema() : Felder für das Einstellungs-Pane

CSS, JS und i18n-Strings werden ausschließlich im Frontend verwaltet
(static/js/app.js, static/css/style.css, static/locales/*.json).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Type


# ---------------------------------------------------------------------------
# Einordnung fuer den Dialog "Panel hinzufuegen": Kategorie + Symbol (Name aus static/js/icons.js); die Beschreibung steht unter
# dem i18n-Schluessel PANEL_DESC_<TYPE> in den Sprachdateien.
# ---------------------------------------------------------------------------
PANEL_META = {
    "dmx_monitor": ("programming", "dmx"), "fixtures": ("programming", "fixtures"), "programmer": ("programming", "programmer"),
    "presets": ("programming", "presets"), "fx_studio": ("programming", "fx"),
    "cuelist": ("cues", "cuelist"), "executor": ("cues", "executor"),
    "command_line": ("input", "terminal"), "command_numpad": ("input", "keypad"), "command_buttons": ("input", "keys"),
    "button": ("input", "button"), "fader": ("input", "fader"),
    "sim3d": ("other", "cube"),
    "timecode": ("media", "clock"), "media_player": ("media", "film"), "stream": ("media", "camera"),
#3D-AUS#     "stage3d": ("stage", "stage"),
}


# ---------------------------------------------------------------------------
# Basisklasse
# ---------------------------------------------------------------------------

class BasePanel:
    """Basisklasse für alle Panel-Typen.

    Unterklassen setzen Klassenattribute und überschreiben optional
    get_module_properties_schema(). Instanzen werden von PanelRegistry
    verwaltet; alle Laufzeitdaten leben im state_manager.Panel-Dataclass.
    """

    panel_type: str = ""
    panel_name: str = ""
    default_width: float = 32.0
    default_height: float = 46.0
    default_show_header: bool = True

    @property
    def default_module_config(self) -> Dict[str, Any]:
        return {}

    def get_info(self) -> Dict[str, Any]:
        category, icon = PANEL_META.get(self.panel_type, ("other", "panel"))
        return {
            "type": self.panel_type,
            "name": self.panel_name,
            "category": category,
            "icon": icon,
            "description": f"PANEL_DESC_{self.panel_type.upper()}",
            "default_width": self.default_width,
            "default_height": self.default_height,
            "default_show_header": self.default_show_header,
        }

    def get_module_properties_schema(self) -> List[Dict[str, Any]]:
        """Deklarative Feldliste für das Modul-Einstellungs-Pane.
        Wird nur ausgewertet, wenn das JS-Plugin kein buildPropertiesPane
        bereitstellt.
        """
        return []


# ---------------------------------------------------------------------------
# Konkrete Panel-Typen
# ---------------------------------------------------------------------------

class DmxMonitorPanel(BasePanel):
    panel_type = "dmx_monitor"
    panel_name = "PANEL_DMX_MONITOR"
    default_width = 44.0
    default_height = 65.0

    @property
    def default_module_config(self) -> Dict[str, Any]:
        return {
            "universe": 1,
            "highlight_color": "#00ff00",
            "color_mode": "signal",
            "border_mode": "uniform",
            "border_color": "#888888",
        }

    def get_module_properties_schema(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": "universe",
                "type": "number",
                "label_key": "DMX_UNIVERSE",
                "min": 1,
                "max": 64,
                "step": 1,
            },
            {
                "id": "highlight_color",
                "type": "color",
                "label_key": "DMX_MONITOR_HIGHLIGHT_COLOR",
            },
            {
                "id": "color_mode",
                "type": "boolean",
                "label_key": "DMX_MONITOR_CHANNEL_COLORS",
                "default": False,
            },
            {
                "id": "border_mode",
                "type": "select",
                "label_key": "DMX_MONITOR_BORDER_MODE",
                "options": [
                    {"value": "individual", "label_key": "DMX_MONITOR_BORDER_INDIVIDUAL"},
                    {"value": "uniform",    "label_key": "DMX_MONITOR_BORDER_UNIFORM"},
                    {"value": "by_type",    "label_key": "DMX_MONITOR_BORDER_BY_TYPE"},
                ],
                "default": "individual",
            },
            {
                "id": "border_color",
                "type": "color",
                "label_key": "DMX_MONITOR_BORDER_COLOR",
                "default": "#888888",
            },
        ]


class FixturesPanel(BasePanel):
    panel_type = "fixtures"
    panel_name = "PANEL_FIXTURES"
    default_width = 60.0
    default_height = 55.0

    @property
    def default_module_config(self) -> Dict[str, Any]:
        return {}

    def get_module_properties_schema(self) -> List[Dict[str, Any]]:
        return []


class ProgrammerPanel(BasePanel):
    panel_type = "programmer"
    panel_name = "PANEL_PROGRAMMER"
    default_width = 70.0
    default_height = 65.0

    @property
    def default_module_config(self) -> Dict[str, Any]:
        return {
            "view_mode": "combined",
            "sel_color": "#ffe600",
            "sel_glow": True,
            "fader_color": "#00ff00",
            "dimmer_width_pct": 0,
            "pan_width_pct": 0,
            "tilt_width_pct": 0,
            "show_hsv": True,
            "show_cmy": True,
            "show_rgb": True,
            "show_picker": True,
            # Standard-Unteransicht je Kategorie: Farbe fader|picker, Position coarse|fine, Beam shutter|gobo|prism
            "default_view_color": "fader",
            "default_view_position": "coarse",
            "default_view_beam": "shutter",
        }

    def get_module_properties_schema(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": "view_mode",
                "type": "select",
                "label_key": "FXPROG_PROP_VIEW_MODE",
                "options": [
                    {"value": "combined", "label_key": "FXPROG_VIEW_COMBINED"},
                    {"value": "fixtures", "label_key": "FXPROG_VIEW_FIXTURES"},
                    {"value": "dimmer",   "label_key": "FXPROG_VIEW_DIMMER"},
                    {"value": "position", "label_key": "FXPROG_VIEW_POSITION"},
                    {"value": "color",    "label_key": "FXPROG_VIEW_COLOR"},
                    {"value": "beam",     "label_key": "FXPROG_VIEW_BEAM"},
                    {"value": "focus",    "label_key": "FXPROG_VIEW_FOCUS"},
                ],
            },
            {
                "id": "default_view_color",
                "type": "select",
                "label_key": "FXPROG_PROP_DEFAULT_VIEW_COLOR",
                "options": [
                    {"value": "fader",  "label_key": "FXPROG_SUBTAB_FADER"},
                    {"value": "picker", "label_key": "FXPROG_SUBTAB_PICKER"},
                ],
            },
            {
                "id": "default_view_position",
                "type": "select",
                "label_key": "FXPROG_PROP_DEFAULT_VIEW_POSITION",
                "options": [
                    {"value": "coarse", "label_key": "FXPROG_POS_COARSE"},
                    {"value": "fine",   "label_key": "FXPROG_POS_FINE"},
                ],
            },
            {
                "id": "default_view_beam",
                "type": "select",
                "label_key": "FXPROG_PROP_DEFAULT_VIEW_BEAM",
                "options": [
                    {"value": "shutter", "label_key": "FXPROG_BEAM_SUBTAB_SHUTTER"},
                    {"value": "gobo",    "label_key": "FXPROG_BEAM_SUBTAB_GOBO"},
                    {"value": "prism",   "label_key": "FXPROG_BEAM_SUBTAB_PRISM"},
                ],
            },
            {
                "id": "sel_color",
                "type": "color",
                "label_key": "FXPROG_PROP_SEL_COLOR",
                "default": "#ffe600",
            },
            {
                "id": "fader_color",
                "type": "color",
                "label_key": "FXPROG_PROP_FADER_COLOR",
                "default": "#00ff00",
            },
            {
                "id": "sel_glow",
                "type": "boolean",
                "label_key": "FXPROG_PROP_SEL_GLOW",
                "default": True,
            },
            {
                "id": "dimmer_width_pct",
                "type": "range",
                "label_key": "FXPROG_PROP_DIMMER_WIDTH_PCT",
                "min": 0,
                "max": 100,
                "step": 5,
                "default": 0,
            },
            {
                "id": "pan_width_pct",
                "type": "range",
                "label_key": "FXPROG_PROP_PAN_WIDTH_PCT",
                "min": 0,
                "max": 100,
                "step": 5,
                "default": 0,
            },
            {
                "id": "tilt_width_pct",
                "type": "range",
                "label_key": "FXPROG_PROP_TILT_WIDTH_PCT",
                "min": 0,
                "max": 100,
                "step": 5,
                "default": 0,
            },
            {
                "id": "show_hsv",
                "type": "boolean",
                "label_key": "FXPROG_PROP_SHOW_HSV",
                "default": True,
            },
            {
                "id": "show_cmy",
                "type": "boolean",
                "label_key": "FXPROG_PROP_SHOW_CMY",
                "default": True,
            },
            {
                "id": "show_rgb",
                "type": "boolean",
                "label_key": "FXPROG_PROP_SHOW_RGB",
                "default": True,
            },
            {
                "id": "show_picker",
                "type": "boolean",
                "label_key": "FXPROG_PROP_SHOW_PICKER",
                "default": True,
            },
        ]


class PresetsPanel(BasePanel):
    panel_type = "presets"
    panel_name = "PANEL_PRESETS"
    default_width = 50.0
    default_height = 55.0

    @property
    def default_module_config(self) -> Dict[str, Any]:
        return {"filter": "all"}

    def get_module_properties_schema(self) -> List[Dict[str, Any]]:
        return []


class CueListPanel(BasePanel):
    panel_type = "cuelist"
    panel_name = "PANEL_CUELIST"
    default_width = 60.0
    default_height = 55.0

    @property
    def default_module_config(self) -> Dict[str, Any]:
        return {"show_progress_bar": True, "show_list_select": True, "cuelist_id": ""}

    def get_module_properties_schema(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": "show_progress_bar",
                "type": "boolean",
                "label_key": "CUELIST_PROP_SHOW_PROGRESS",
                "default": True,
            },
            {
                "id": "show_list_select",
                "type": "boolean",
                "label_key": "CUELIST_PROP_SHOW_SELECT",
                "default": True,
            },
        ]


class CommandLinePanel(BasePanel):
    panel_type = "command_line"
    panel_name = "PANEL_COMMAND_LINE"
    default_width = 44.0
    default_height = 32.0

    @property
    def default_module_config(self) -> Dict[str, Any]:
        return {
            "text_color": "#e6e6e6",
            "success_color": "#00ff66",
            "error_color": "#ff5555",
        }

    def get_module_properties_schema(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": "text_color",
                "type": "color",
                "label_key": "CMDLINE_PROP_TEXT_COLOR",
                "default": "#e6e6e6",
            },
            {
                "id": "success_color",
                "type": "color",
                "label_key": "CMDLINE_PROP_SUCCESS_COLOR",
                "default": "#00ff66",
            },
            {
                "id": "error_color",
                "type": "color",
                "label_key": "CMDLINE_PROP_ERROR_COLOR",
                "default": "#ff5555",
            },
        ]


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

class PanelRegistry:
    """Single source of truth für alle registrierten Panel-Typen."""

    _registry: Dict[str, BasePanel] = {}

    @classmethod
    def register(cls, panel_class: Type[BasePanel]) -> Type[BasePanel]:
        instance = panel_class()
        cls._registry[instance.panel_type] = instance
        return panel_class

    @classmethod
    def get_all_info(cls) -> List[Dict[str, Any]]:
        return [p.get_info() for p in cls._registry.values()]

    @classmethod
    def get(cls, panel_type: str) -> Optional[BasePanel]:
        return cls._registry.get(panel_type)

    @classmethod
    def is_known(cls, panel_type: str) -> bool:
        return panel_type in cls._registry


class FxStudioPanel(BasePanel):
    """Editor fuer Effekt-Skripte (.fx) mit Speichern und Probelauf."""
    panel_type = "fx_studio"
    panel_name = "PANEL_FX_STUDIO"
    default_width = 44.0
    default_height = 62.0

    @property
    def default_module_config(self) -> Dict[str, Any]:
        return {}

    def get_module_properties_schema(self) -> List[Dict[str, Any]]:
        return []


class ExecutorPanel(BasePanel):
    """Executor (dot2-Stil): Fader (Gesamthelligkeit der zugeordneten Cue-Liste) plus Go / Pause / Zurueck / Stopp.
    Die Cue-Liste dient nur der Verwaltung der Cues, die Wiedergabe laeuft ueber den Executor. Welche Cue-Liste, steht in
    module_config["cuelist_id"] (leer = die im Cue-Listen-Panel gewaehlte, aktive Liste)."""
    panel_type = "executor"
    panel_name = "PANEL_EXECUTOR"
    default_width = 10.0
    default_height = 55.0

    @property
    def default_module_config(self) -> Dict[str, Any]:
        return {"cuelist_id": "", "show_fader": True, "show_go": True, "show_pause": True, "show_back": True,
                "show_stop": True, "size_go": "normal", "size_pause": "normal", "size_back": "normal", "size_stop": "normal",
                "show_title": True, "compact": False, "smart": True, "fader_color": ""}

    def get_module_properties_schema(self) -> List[Dict[str, Any]]:
        return []


class CommandNumpadPanel(BasePanel):
    """Kompaktes 4x5-Ziffernblock-Panel (Zahlen/Syntax + Please) fuer die
    Command Line - eigenstaendig, skaliert proportional mit der Panel-
    Groesse (siehe .cnp in style.css)."""
    panel_type = "command_numpad"
    panel_name = "PANEL_COMMAND_NUMPAD"
    default_width = 22.0
    default_height = 38.0

    @property
    def default_module_config(self) -> Dict[str, Any]:
        return {}

    def get_module_properties_schema(self) -> List[Dict[str, Any]]:
        return []


class CommandButtonsPanel(BasePanel):
    """Responsives Panel mit allen Keyword-Tasten (Fixture/Group/.../Off)
    fuer die Command Line - bricht per CSS-Grid auto-fit sauber in mehrere
    Spalten/Zeilen um (siehe .cbtn in style.css)."""
    panel_type = "command_buttons"
    panel_name = "PANEL_COMMAND_BUTTONS"
    default_width = 32.0
    default_height = 42.0

    @property
    def default_module_config(self) -> Dict[str, Any]:
        return {}

    def get_module_properties_schema(self) -> List[Dict[str, Any]]:
        return []


class TimecodePanel(BasePanel):
    """Steuerung des globalen Timecodes (die interne Uhr): Anzeige, Start/Pause/Stopp, rueckwaerts, Springen, Geschwindigkeit.
    Es gibt nur EINEN Timecode je Show; jedes Timecode-Panel auf jedem Geraet bedient denselben."""
    panel_type = "timecode"
    panel_name = "PANEL_TIMECODE"
    default_width = 30.0
    default_height = 46.0

    @property
    def default_module_config(self) -> Dict[str, Any]:
        return {"show_goto": True, "show_speed": True, "show_step": True}

    def get_module_properties_schema(self) -> List[Dict[str, Any]]:
        return []


class MediaPlayerPanel(BasePanel):
    """Video-/Audio-Player. Das Medium gehoert zur Show (siehe app/media_store.py), das Panel verweist nur darauf.
    sync "timecode": laeuft synchron zum globalen Timecode (ab tc_start_ms); sync "free": normaler Player mit eigenen Bedienelementen."""
    panel_type = "media_player"
    panel_name = "PANEL_MEDIA_PLAYER"
    default_width = 36.0
    default_height = 40.0

    @property
    def default_module_config(self) -> Dict[str, Any]:
        return {"media_id": "", "sync": "timecode", "tc_start_ms": 0, "muted": False, "volume": 100, "loop": False, "fit": "contain", "show_tc": False}

    def get_module_properties_schema(self) -> List[Dict[str, Any]]:
        return []


class StreamPanel(BasePanel):
    """Livestream (Kamera): eine Quelle aus der Quellenliste (URL: MJPEG, Video, HLS, WebRTC/WHEP - der Server leitet auf Wunsch mit den
    Zugangsdaten weiter, siehe app/stream_sources.py) oder eine Kamera am Hauptgeraet (der Computer mit dem Programm; app/host_cameras.py -
    das Bild wird von dort zu jedem Geraet gestreamt). source: "" | "cam:<id>" | <Quellen-ID>; paused: Pause (wird mit dem
    Layout gespeichert); quality: low | medium | high | max (nur Kameras am Hauptgeraet)."""
    panel_type = "stream"
    panel_name = "PANEL_STREAM"
    default_width = 36.0
    default_height = 40.0

    @property
    def default_module_config(self) -> Dict[str, Any]:
        return {"source": "", "camera_label": "", "muted": True, "fit": "contain", "reconnect": True, "paused": False, "quality": "medium"}

    def get_module_properties_schema(self) -> List[Dict[str, Any]]:
        return []


#3D-AUS# class Stage3DPanel(BasePanel):
#3D-AUS#     """3D-Buehne: Raum, Traversen und Scheinwerfer in 3D mit Live-Beleuchtung (Farbe, Helligkeit, Pan/Tilt aus dem DMX-Stand), frei bewegliche
#3D-AUS#     Kamera mit gespeicherten Ansichten und ein Editor ("Raum bauen" / "Scheinwerfer positionieren"). Die Buehne selbst gehoert zur Show
#3D-AUS#     (siehe app/stage3d.py); das Panel speichert nur seine Darstellung: quality (auto | low | medium | high), beams (Lichtkegel zeigen)."""
#3D-AUS#     panel_type = "stage3d"
#3D-AUS#     panel_name = "PANEL_STAGE3D"
#3D-AUS#     default_width = 52.0
#3D-AUS#     default_height = 56.0

#3D-AUS#     @property
#3D-AUS#     def default_module_config(self) -> Dict[str, Any]:
#3D-AUS#         return {"quality": "auto", "beams": True}

#3D-AUS#     def get_module_properties_schema(self) -> List[Dict[str, Any]]:
#3D-AUS#         return []


class Sim3DPanel(BasePanel):
    """3D-Simulation: Buehne in 3D (Schritt 1: leere Buehne mit Boden, Raster und Koordinatensystem, bewegliche Kamera per Maus und Touch).
    Die Darstellung steckt komplett im Client (static/js/sim3d.js); das Panel speichert noch keine Einstellungen."""
    panel_type = "sim3d"
    panel_name = "PANEL_SIM3D"
    default_width = 50.0
    default_height = 55.0

    @property
    def default_module_config(self) -> Dict[str, Any]:
        return {}

    def get_module_properties_schema(self) -> List[Dict[str, Any]]:
        return []


class ButtonPanel(BasePanel):
    panel_type = "button"
    panel_name = "PANEL_BUTTON"
    default_width = 8.0
    default_height = 8.0
    default_show_header = False


class FaderPanel(BasePanel):
    panel_type = "fader"
    panel_name = "PANEL_FADER"
    default_width = 6.0
    default_height = 30.0
    default_show_header = False


# Alle eingebauten Panel-Typen direkt beim Import registrieren
PanelRegistry.register(DmxMonitorPanel)
PanelRegistry.register(FixturesPanel)
PanelRegistry.register(ProgrammerPanel)
PanelRegistry.register(PresetsPanel)
PanelRegistry.register(CueListPanel)
PanelRegistry.register(ExecutorPanel)
PanelRegistry.register(CommandLinePanel)
PanelRegistry.register(CommandNumpadPanel)
PanelRegistry.register(CommandButtonsPanel)
PanelRegistry.register(FxStudioPanel)
PanelRegistry.register(ButtonPanel)
PanelRegistry.register(TimecodePanel)
PanelRegistry.register(MediaPlayerPanel)
PanelRegistry.register(StreamPanel)
#3D-AUS# PanelRegistry.register(Stage3DPanel)
PanelRegistry.register(Sim3DPanel)
PanelRegistry.register(FaderPanel)
