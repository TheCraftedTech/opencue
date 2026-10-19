"""
fx_script.py
Effekt-Skripte (.fx): Kopfzeilen (#NAME, #CATEGORY, #RATE, #DESCRIPTION, #VAR), Uebersetzung, Probelauf/Vorschau und die Registry der gefundenen Dateien.

Die Sprache selbst (C++/Arduino-aehnlich: Variablen, if/for/while, Funktionen, setup()/loop()) steckt in app/fxlang.py; dieses Modul kennt nur den Rahmen:
`#RATE` legt fest, wie oft pro Sekunde loop() ausgefuehrt wird (1 bis 40, Vorgabe 40 = Takt der DMX-Ausgabe). Ausgaben sind dimmer (0-100 %), r/g/b (0-255)
und pan/tilt (0-100 %), je nach #CATEGORY. Skripte liegen als Klartext in defaults/effects (mitgeliefert) und im Benutzerordner (paths.effects_dir()).
"""

from __future__ import annotations

import logging
import math
import re
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from app import paths as _paths
from app import fxlang
from app.fx_categories import CATEGORIES as _CATEGORY_TABLE
from app.fx_categories import OUTPUT_NAMES, OUTPUTS_BY_CATEGORY
from app.fxlang import (  # noqa: F401  (Namen bleiben hier erreichbar)
    BUILTINS, CONSTANTS, RESERVED_NAMES, SPECIAL_FUNCTIONS, SYSTEM_VARS,
    FxScriptError, FxScriptRuntimeError, Program, compile_program,
)

logger = logging.getLogger("opencue.fx_script")

_RESERVED = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}
_FORBIDDEN_NAME = re.compile(r'[\\/:*?"<>|\x00-\x1f]')


def valid_script_name(name: Any) -> bool:
    """Skriptname = Dateiname ohne Endung; nur ein einfacher Dateiname (kein Pfad), kein reservierter Windows-Name."""
    if not isinstance(name, str) or not name or len(name) > 80 or name != name.strip() or name.endswith(".") or name.startswith("."):
        return False
    return not _FORBIDDEN_NAME.search(name) and name.split(".")[0].upper() not in _RESERVED


CATEGORIES = tuple(_CATEGORY_TABLE)          # Kategorien und ihre Ausgaben: app/fx_categories.py
ALL_OUTPUTS = OUTPUT_NAMES
RATE_MIN, RATE_MAX, RATE_DEFAULT = 1, 40, 40
UI_KINDS = ("Slider", "ColorPicker", "NumberInput")
VAR_KINDS = UI_KINDS + ("Internal",)


# ---- Kopfzeilen und uebersetztes Skript -------------------------------------------

@dataclass
class FxVariable:
    name: str
    kind: str                 # Slider | ColorPicker | NumberInput | Internal
    default: Any
    minimum: float = 0.0
    maximum: float = 1.0
    step: float = 0.01
    line: int = 0


@dataclass
class FxScript:
    name: str                 # Dateiname ohne .fx - Schluessel in der Registry
    label: str                # #NAME
    category: str             # #CATEGORY
    rate: int = RATE_DEFAULT  # #RATE: loop()-Aufrufe pro Sekunde
    description: str = ""     # #DESCRIPTION
    variables: List[FxVariable] = field(default_factory=list)
    program: Optional[Program] = None
    source: str = ""
    path: str = ""
    origin: str = ""

    @property
    def ui_variables(self) -> List[FxVariable]:
        return [v for v in self.variables if v.kind != "Internal"]

    @property
    def used_outputs(self) -> Tuple[str, ...]:
        """Ausgaben, die das Skript wirklich setzt (nur diese schreibt die Engine, nur diese werden im Programmer gesperrt)."""
        return _CATEGORY_TABLE[self.category].used(self.program.assigned_outputs if self.program else None)

    @property
    def used_attrs(self) -> Tuple[str, ...]:
        return _CATEGORY_TABLE[self.category].attrs_of(self.used_outputs)

    def default_params(self) -> Dict[str, Any]:
        return {v.name: v.default for v in self.ui_variables}


def _parse_header(name: str, lineno: int, parts: List[str], raw: str, script: Dict[str, Any]) -> None:
    keyword = parts[0].upper()
    if keyword == "#NAME":
        script["label"] = " ".join(parts[1:]).strip() or name
    elif keyword == "#DESCRIPTION":
        script["description"] = raw.strip()[len("#DESCRIPTION"):].strip()[:300]
    elif keyword == "#CATEGORY":
        if len(parts) < 2 or parts[1] not in CATEGORIES:
            raise FxScriptError(lineno, "#CATEGORY erwartet " + ", ".join(CATEGORIES[:-1]) + " oder " + CATEGORIES[-1])
        script["category"] = parts[1]
    elif keyword == "#RATE":
        try:
            rate = float(parts[1]) if len(parts) > 1 else math.nan
        except ValueError:
            rate = math.nan
        if not (RATE_MIN <= rate <= RATE_MAX) or rate != int(rate):
            raise FxScriptError(lineno, f"#RATE erwartet eine ganze Zahl von {RATE_MIN} bis {RATE_MAX} (Durchlaeufe pro Sekunde)")
        script["rate"] = int(rate)
    elif keyword == "#VAR":
        if len(parts) < 4 or parts[2] not in VAR_KINDS:
            raise FxScriptError(lineno, "#VAR erwartet: #VAR name Slider|ColorPicker|NumberInput|Internal wert ...")
        var_name, kind = parts[1], parts[2]
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", var_name):
            raise FxScriptError(lineno, f"Ungueltiger Variablenname '{var_name}'")
        if var_name in RESERVED_NAMES:
            raise FxScriptError(lineno, f"'{var_name}' ist reserviert")
        if any(v.name == var_name for v in script["variables"]):
            raise FxScriptError(lineno, f"'{var_name}' ist schon als #VAR deklariert")
        if kind == "ColorPicker":
            hexval = parts[3].lstrip("#")
            if not re.fullmatch(r"[0-9a-fA-F]{6}", hexval):
                raise FxScriptError(lineno, "ColorPicker erwartet einen Hex-Wert wie #ff8800")
            default: Any = {"r": int(hexval[0:2], 16), "g": int(hexval[2:4], 16), "b": int(hexval[4:6], 16)}
            var = FxVariable(var_name, kind, default, line=lineno)
        else:
            try:
                default = float(parts[3])
                lo = float(parts[4]) if len(parts) > 4 else 0.0
                hi = float(parts[5]) if len(parts) > 5 else 1.0
                step = float(parts[6]) if len(parts) > 6 else 0.01
            except ValueError:
                raise FxScriptError(lineno, "Zahlenwert in #VAR erwartet") from None
            var = FxVariable(var_name, kind, default, lo, hi, step, line=lineno)
        script["variables"].append(var)
    else:
        raise FxScriptError(lineno, f"Unbekannter Header '{parts[0]}'")


def compile_script(name: str, text: str) -> FxScript:
    """Parst und prueft ein Skript. Wirft FxScriptError mit Zeilenangabe."""
    header: Dict[str, Any] = {"label": name, "category": None, "variables": [], "rate": RATE_DEFAULT, "description": ""}
    body_lines: List[str] = []
    for lineno, raw in enumerate(text.splitlines(), start=1):
        stripped = raw.strip()
        if stripped.startswith("#"):
            _parse_header(name, lineno, stripped.split(), raw, header)
            body_lines.append("")                      # Zeilennummern bleiben gleich
        else:
            body_lines.append(raw)
    if header["category"] is None:
        raise FxScriptError(1, "#CATEGORY fehlt (" + ", ".join(CATEGORIES[:-1]) + " oder " + CATEGORIES[-1] + ")")
    variables: List[FxVariable] = header["variables"]
    params: Dict[str, Any] = {}
    for var in variables:
        if var.kind == "ColorPicker":
            params.update({f"{var.name}_{c}": 0 for c in "rgb"})
        elif var.kind != "Internal":
            params[var.name] = var.default
    internals = {v.name: float(v.default) for v in variables if v.kind == "Internal"}
    program = compile_program("\n".join(body_lines), params, internals, OUTPUTS_BY_CATEGORY[header["category"]])
    return FxScript(name=name, label=header["label"], category=header["category"], rate=header["rate"], description=header["description"],
                    variables=variables, program=program, source=text)


PREVIEW_SLOTS = 8          # ohne Scheinwerfer (Vorschau) gelten acht gleichmaessig verteilte Gobo-Slots


def even_slots(count: int) -> List[float]:
    """`count` Slots gleichmaessig ueber 0-100 % verteilt (Mitte jedes Bereichs)."""
    return [round((i + 0.5) * 100.0 / count, 3) for i in range(count)]


def system_vars(script: FxScript, params: Dict[str, Any], index: int, count: int, t: float, tick: int,
                info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Alle Werte, die loop() lesen darf: Systemvariablen und die Regler (#VAR). `info` = Angaben zum Geraet (`slots`: Liste der Gobo-Slots in Prozent)."""
    values: Dict[str, float] = {}
    for var in script.ui_variables:
        raw = params.get(var.name, var.default)
        if var.kind == "ColorPicker":
            color = raw if isinstance(raw, dict) else var.default
            for channel in "rgb":
                values[f"{var.name}_{channel}"] = float(color.get(channel, 0))
        else:
            values[var.name] = float(raw)
    rate = float(script.rate)
    values.update({
        "t": float(t), "elapsed": tick / rate, "dt": 1.0 / rate, "tick": float(tick), "loop_count": float(tick), "rate": rate,
        "index": float(index), "count": float(count), "phase": (index / count) if count > 0 else 0.0,
    })
    slots = list((info or {}).get("slots") or [])
    slots2 = list((info or {}).get("slots2") or [])
    values["slots"] = float(len(slots))
    values["slots2"] = float(len(slots2))
    values["__slot_list"] = slots
    values["__slot_list2"] = slots2
    return values


def run_script(script: FxScript, state: Dict[str, Any], params: Dict[str, Any],
               index: int, count: int, t: float, tick: int, info: Optional[Dict[str, Any]] = None) -> Dict[str, float]:
    """Fuehrt loop() einmal aus. `state` ist der persistente Speicher dieser Instanz (Fixture x Kategorie x Effekt); ein leerer `state` startet den Effekt neu.
    `t` ist die gemeinsame Systemzeit, `tick` die Nummer des Durchlaufs (elapsed = tick / rate). Gibt die Ausgaben der Kategorie zurueck (0-100 % bzw. 0-255)."""
    return fxlang.execute(script.program, state, system_vars(script, params, index, count, t, tick, info), OUTPUTS_BY_CATEGORY[script.category], seed=index)


# ---- Vorschau (Effekt-Studio) ------------------------------------------------

PREVIEW_MAX_RUNS = 24000            # Obergrenze fuer loop()-Aufrufe je Vorschau (Scheinwerfer x Durchlaeufe)
PREVIEW_MAX_SECONDS = 2.0           # Rechenzeit-Grenze: ein langsames Skript soll den Server nicht festhalten


def _clean_preview_params(script: FxScript, params: Any) -> Dict[str, Any]:
    """Parameter der Vorschau: nur bekannte UI-Variablen, Zahlen auf ihren Bereich begrenzt, Farben als r/g/b 0-255; alles andere = Standardwert."""
    values = script.default_params()
    if not isinstance(params, dict):
        return values
    for var in script.ui_variables:
        raw = params.get(var.name)
        if var.kind == "ColorPicker":
            if isinstance(raw, dict):
                try:
                    values[var.name] = {c: max(0, min(255, int(float(raw.get(c, 0))))) for c in "rgb"}
                except (TypeError, ValueError):
                    pass
        elif isinstance(raw, (int, float)) and not isinstance(raw, bool) and math.isfinite(raw):
            low, high = min(var.minimum, var.maximum), max(var.minimum, var.maximum)
            values[var.name] = max(low, min(high, float(raw)))
    return values


def preview_script(name: str, text: str, params: Any = None, count: Any = 1, duration: Any = 2.0) -> Dict[str, Any]:
    """Rechnet ein Skript ohne Scheinwerfer durch: je Scheinwerfer (index 0..count-1, phase = index/count) die Ausgaben ueber `duration` Sekunden, und zwar genau
    so oft pro Sekunde wie im Betrieb (#RATE): Zeitpunkt des n-ten Durchlaufs = n / rate. Wirft FxScriptError (Zeile) oder FxScriptRuntimeError.
    Antwort: category, label, description, rate, count, duration, times, series = {ausgabe: [je Scheinwerfer: Werte]}, params (verwendet), variables (UI-Parameter)."""
    script = compile_script(name, text)
    count = max(1, min(16, int(count)))
    duration = max(0.5, min(20.0, float(duration)))
    rate = script.rate
    steps = int(duration * rate) + 1
    if steps * count > PREVIEW_MAX_RUNS:
        raise FxScriptRuntimeError("Vorschau zu gross: weniger Scheinwerfer oder kuerzere Dauer waehlen")
    values = _clean_preview_params(script, params)
    outputs = OUTPUTS_BY_CATEGORY[script.category]
    series: Dict[str, List[List[float]]] = {out: [] for out in outputs}
    started = time.monotonic()
    info = {"slots": even_slots(PREVIEW_SLOTS), "slots2": even_slots(PREVIEW_SLOTS)} if script.category == "gobo" else None
    for index in range(count):
        state: Dict[str, Any] = {}
        rows: Dict[str, List[float]] = {out: [] for out in outputs}
        for step in range(steps):
            result = run_script(script, state, values, index, count, step / rate, step, info)
            for out in outputs:
                number = float(result.get(out, 0.0))
                rows[out].append(round(number, 3) if math.isfinite(number) else 0.0)
            if time.monotonic() - started > PREVIEW_MAX_SECONDS:
                raise FxScriptRuntimeError("Die Vorschau braucht zu lange (Skript zu rechenintensiv?)")
        for out in outputs:
            series[out].append(rows[out])
    return {
        "category": script.category, "label": script.label, "description": script.description, "count": count, "rate": rate, "duration": duration,
        "times": [round(step / rate, 4) for step in range(steps)],
        "series": series, "params": values,
        "variables": [{"name": v.name, "kind": v.kind, "default": v.default, "min": v.minimum, "max": v.maximum, "step": v.step}
                      for v in script.ui_variables],
    }


# ---- Registry ----------------------------------------------------------------

def seed_default_effects(source: Path, target: Path) -> None:
    """Erstbefuellung: kopiert die mitgelieferten Effekte einmal in den Benutzerordner.
    Danach gehoert der Ordner dem Benutzer - geloeschte Effekte kommen nicht zurueck.
    Bereits vorhandene Dateien werden nie ueberschrieben."""
    target.mkdir(parents=True, exist_ok=True)
    marker = target / ".defaults_seeded"
    if marker.exists():
        return
    for path in sorted(source.glob("*.fx")):
        dest = target / path.name
        if not dest.exists():
            shutil.copyfile(path, dest)
    marker.write_text("Standardeffekte uebernommen\n", encoding="utf-8")


def restore_default_effects(source: Path, target: Path) -> Dict[str, List[str]]:
    """Legt jeden mitgelieferten Effekt, der im Benutzerordner fehlt, wieder an. Nie ueberschreiben: vorhandene Dateien bleiben, auch geaenderte
    (`modified` nennt sie nur). Antwort: restored (neu angelegt), present (schon da, gleicher Inhalt), modified (schon da, vom Standard abweichend)."""
    target.mkdir(parents=True, exist_ok=True)
    out: Dict[str, List[str]] = {"restored": [], "present": [], "modified": []}
    for path in sorted(source.glob("*.fx")):
        dest = target / path.name
        if not dest.exists():
            shutil.copyfile(path, dest)
            out["restored"].append(path.stem)
        elif dest.read_bytes() == path.read_bytes():
            out["present"].append(path.stem)
        else:
            out["modified"].append(path.stem)
    return out


class FxScriptRegistry:
    def __init__(self) -> None:
        self._scripts: Dict[str, FxScript] = {}
        self._files: Dict[str, Dict[str, Any]] = {}
        self._extra_sources: List[Tuple[str, Path]] = []

    def reload(self) -> None:
        """Liest mit denselben zusaetzlichen Quellen wie zuletzt neu (z. B. nachdem eine Show ihre Skripte bereitgelegt hat)."""
        self.load(self._extra_sources)

    @staticmethod
    def _default_scripts() -> Dict[str, bytes]:
        """Die mitgelieferten Effekte (Name -> Inhalt), um sie in der Liste als "Standard" zu kennzeichnen."""
        out: Dict[str, bytes] = {}
        try:
            for path in _paths.default_effects_dir().glob("*.fx"):
                out[path.stem] = path.read_bytes()
        except OSError:
            pass
        return out

    def load(self, extra_sources: Sequence[Tuple[str, Path]] = ()) -> None:
        """Liest alle .fx-Dateien aus dem Benutzerordner (%LOCALAPPDATA%\\OpenCue\\effects)
        und aus zusaetzlichen Quellen (derzeit keine). Skripte aus dem Programmordner (defaults/effects) werden nie geladen, nur ihre Namen dienen dazu,
        mitgelieferte Effekte in der Liste zu kennzeichnen (`default`, `default_modified`).
        Ein fehlerhaftes Skript ersetzt die zuletzt funktionierende Version NICHT -
        laufende Effekte bleiben erhalten.

        Die Show selbst enthaelt keine Skripte (nur Effekt-Definitionen mit dem Skriptnamen); beim Weitergeben packt der Export sie ins ZIP."""
        previous = self._scripts
        scripts: Dict[str, FxScript] = {}
        files: Dict[str, Dict[str, Any]] = {}
        self._extra_sources = list(extra_sources)
        sources = [("user", _paths.effects_dir())]
        sources.extend(extra_sources)
        for origin, directory in sources:
            for path in sorted(directory.glob("*.fx")):
                name = path.stem
                try:
                    script = compile_script(name, path.read_text(encoding="utf-8"))
                    script.path = str(path)
                    script.origin = origin
                    scripts[name] = script
                    files[name] = {"name": name, "origin": origin, "path": str(path), "ok": True,
                                   "line": None, "message": "OK", "category": script.category,
                                   "label": script.label, "description": script.description, "rate": script.rate}
                except (FxScriptError, OSError) as exc:
                    line = exc.line if isinstance(exc, FxScriptError) else None
                    message = exc.message if isinstance(exc, FxScriptError) else str(exc)
                    if name in previous:
                        scripts[name] = previous[name]
                    files[name] = {"name": name, "origin": origin, "path": str(path), "ok": False,
                                   "line": line, "message": message,
                                   "category": previous[name].category if name in previous else None,
                                   "label": previous[name].label if name in previous else name,
                                   "description": previous[name].description if name in previous else "",
                                   "rate": previous[name].rate if name in previous else None}
        defaults = self._default_scripts()
        for name, entry in files.items():
            entry["default"] = name in defaults
            try:
                entry["default_modified"] = name in defaults and Path(entry["path"]).read_bytes() != defaults[name]
            except OSError:
                entry["default_modified"] = False
        self._scripts = scripts
        self._files = files
        broken = [f["name"] for f in files.values() if not f["ok"]]
        if broken:
            logger.warning("FX-Skripte mit Fehlern uebersprungen: %s", ", ".join(broken))

    def get(self, name: str) -> Optional[FxScript]:
        return self._scripts.get(name)

    def has(self, name: str) -> bool:
        return name in self._scripts

    def category(self, name: str) -> Optional[str]:
        script = self._scripts.get(name)
        return script.category if script else None

    def files(self) -> List[Dict[str, Any]]:
        """Alle gefundenen Dateien, auch fehlerhafte - fuer den Effekt-Studio."""
        return [dict(f) for _, f in sorted(self._files.items())]

    def describe(self) -> List[Dict[str, Any]]:
        """Beschreibung fuer Dropdowns und Dialoge: Name, Datei, Kategorie, UI-Parameter."""
        out: List[Dict[str, Any]] = []
        for script in sorted(self._scripts.values(), key=lambda s: s.label.lower()):
            out.append({
                "name": script.name,
                "file": script.name + ".fx",
                "origin": script.origin,
                "label": script.label,
                "category": script.category,
                "rate": script.rate,
                "outputs": list(script.used_outputs),
                "attrs": list(script.used_attrs),
                "description": script.description,
                "variables": [
                    {"name": v.name, "kind": v.kind, "default": v.default,
                     "min": v.minimum, "max": v.maximum, "step": v.step}
                    for v in script.ui_variables
                ],
            })
        return out


registry = FxScriptRegistry()
