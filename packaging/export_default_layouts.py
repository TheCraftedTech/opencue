"""Macht aus selbst gebauten Layouts die mitgelieferten Beispiel-Layouts (defaults/layouts/*.json). Nur Entwicklung, gehoert nicht ins Programm.

Ablauf: Layouts in OpenCue zusammenstellen und speichern (z. B. Standard_1, Standard_2 ...; sie liegen unter %LOCALAPPDATA%\\OpenCue\\layouts), dann

    venv\\Scripts\\python.exe packaging\\export_default_layouts.py                       # zeigt nur, was passieren wuerde
    venv\\Scripts\\python.exe packaging\\export_default_layouts.py --write --replace     # schreibt defaults\\layouts\\01_Standard_1.json ... und loescht die alten Vorlagen

Optionen:  --prefix Standard_   welche Layouts (Namensanfang, Standard "Standard_")
           --out <Ordner>       Zielordner (Standard: defaults\\layouts im Projekt)
           --rename ALT=NEU     Anzeigename statt "Standard 1" (mehrfach moeglich), z. B. --rename Standard_1=Default_1 (der Name bleibt woertlich, auch mit Unterstrich)
           --replace            vorhandene Vorlagen im Zielordner vorher entfernen
           --write              wirklich schreiben (ohne das nur Vorschau)

Je Layout entsteht eine Vorlage {"name": {"de": ..., "en": ...}, "panels": [...]}: Panel-Id, Fensterzustand (ui_state) und Standardwerte werden weggelassen, nur Typ, Lage/Groesse
und bewusst geaenderte Einstellungen (Titel, Farben, module_config ...) bleiben. Der Anzeigename ist der Layoutname mit Leerzeichen statt Unterstrichen ("Standard_1" -> "Standard 1");
danach in der JSON-Datei nach Wunsch je Sprache aendern. Wer schon Layouts in seinem Datenordner hat, bekommt die neuen Vorlagen nur bei einer frischen Installation (die Vorlagen
werden einmal pro Datenordner angelegt, siehe defaults/README.md).
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from app import paths  # noqa: E402
from app.state_manager import Panel  # noqa: E402

KEEP_ALWAYS = ("type", "x", "y", "width", "height")
SKIP = {"id", "ui_state", "z_index"}
DEFAULTS = {f.name: f.default for f in dataclasses.fields(Panel) if f.default is not dataclasses.MISSING}


def natural(text: str):
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", text)]


def clean_panel(panel: dict) -> dict:
    out = {key: panel[key] for key in KEEP_ALWAYS if key in panel}
    for key, value in panel.items():
        if key in out or key in SKIP:
            continue
        if key == "module_config":
            if value:
                out[key] = value
        elif key not in DEFAULTS or value != DEFAULTS[key]:
            out[key] = value
    return out


def display_name(name: str) -> str:
    return re.sub(r"\s+", " ", name.replace("_", " ")).strip()


def slug(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("_") or "layout"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--prefix", default="Standard_")
    parser.add_argument("--out", default=str(paths.default_layouts_dir()))
    parser.add_argument("--replace", action="store_true")
    parser.add_argument("--rename", action="append", default=[], metavar="ALT=NEU")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    source = paths.get_data_root() / "layouts"
    renames = dict(item.split("=", 1) for item in args.rename if "=" in item)
    files = sorted((p for p in source.glob("*.json") if p.stem.lower().startswith(args.prefix.lower())), key=lambda p: natural(p.stem))
    if not files:
        print(f"Keine Layouts mit dem Anfang '{args.prefix}' in {source} gefunden.")
        return 1
    out = Path(args.out)
    print(f"{len(files)} Layout(s) aus {source} -> {out}")
    templates = []
    for number, path in enumerate(files, start=1):
        data = json.loads(path.read_text(encoding="utf-8"))
        name = str(data.get("name") or path.stem)
        panels = [clean_panel(p) for p in data.get("panels", []) if isinstance(p, dict) and p.get("type")]
        shown = renames.get(path.stem) or renames.get(name) or display_name(name)
        target = f"{number:02d}_{slug(shown)}.json"
        templates.append((target, {"name": {"de": shown, "en": shown}, "panels": panels}))
        print(f"  {target:34s} {shown!r}: {len(panels)} Panels ({', '.join(p['type'] for p in panels)})")
    if not args.write:
        print("\nNur Vorschau - mit --write wirklich schreiben (mit --replace werden die alten Vorlagen vorher entfernt).")
        return 0
    out.mkdir(parents=True, exist_ok=True)
    if args.replace:
        for old in out.glob("*.json"):
            old.unlink()
            print("  entfernt:", old.name)
    for target, template in templates:
        (out / target).write_text(json.dumps(template, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{len(templates)} Vorlage(n) geschrieben.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
