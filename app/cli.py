# Copyright (C) 2026 Samuel Zenker
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Startparameter von OpenCue (`OpenCue.exe` / `python main.py`). Leichtes Modul: wird als allererstes ausgewertet, noch vor allen anderen Importen - einige Parameter setzen
Umgebungsvariablen, die erst beim Import des Datenordners / der Zustandsverwaltung gelesen werden.

  --no-ui, --server-only   Server ohne Programmfenster: alles laeuft wie gewohnt (DMX, Cues, Remote, REST-API), bedient wird im Browser (dieser Rechner:
                           http://127.0.0.1:<Port>) oder per Fernzugriff. Ein Symbol im Infobereich der Taskleiste (Tray) bietet "Im Browser oeffnen", "Log-Ordner", "Beenden".
  --open-browser           (mit --no-ui) beim Start den Standard-Browser auf die Konsole oeffnen.
  --show DATEI | DATEI     diese Show laden statt der zuletzt benutzten (auch: Doppelklick-Zuordnung / Startparameter von Verknuepfungen).
  --new-show               mit einer leeren Show starten statt mit der zuletzt benutzten (nichts wird geloescht).
  --port N                 Server-Port nur fuer diesen Lauf (gespeichert wird nichts).
  --remote                 Netzwerk-Zugriff (Fernzugriff) einschalten - wird gespeichert (Einstellungen -> Fernzugriff).
  --data-dir ORDNER        eigener Datenordner nur fuer diesen Lauf (tragbar / Tests; wie OPENCUE_DATA_DIR).
  --fullscreen             Programmfenster im Vollbild starten.
  --priority STUFE         Prozess-Prioritaet: normal | above (Standard) | high. Hoehere Prioritaet haelt das Zeitverhalten der DMX-Ausgabe stabil, wenn der Rechner ausgelastet ist.
  --no-splash              kein Startbild (auch OPENCUE_NO_SPLASH=1).
  --version, --help

Ein Programm ohne Konsole (die gebaute OpenCue.exe) haengt sich fuer die Ausgabe von --help / --version / Fehlern an die Konsole an, aus der es gestartet wurde.
"""
from __future__ import annotations

import argparse
import ctypes
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from app.version import APP_DESCRIPTION, APP_NAME, APP_VERSION_LABEL

PRIORITIES = ("normal", "above", "high")


@dataclass
class Options:
    no_ui: bool = False
    open_browser: bool = False
    show: Optional[str] = None
    new_show: bool = False
    port: Optional[int] = None
    remote: bool = False
    data_dir: Optional[str] = None
    fullscreen: bool = False
    priority: str = "above"
    no_splash: bool = False


def attach_console() -> None:
    """Die gebaute OpenCue.exe hat keine eigene Konsole: fuer --help / --version / Fehlermeldungen an die Konsole des Aufrufers anhaengen (cmd, PowerShell), falls es eine gibt."""
    if sys.platform != "win32":
        return
    try:
        if ctypes.windll.kernel32.AttachConsole(-1):                      # ATTACH_PARENT_PROCESS
            for name, mode, device in (("stdout", "w", "CONOUT$"), ("stderr", "w", "CONOUT$")):
                stream = getattr(sys, name, None)
                if stream is None or not hasattr(stream, "fileno") or _bad_fileno(stream):
                    setattr(sys, name, open(device, mode, encoding="utf-8", errors="replace"))
    except Exception:
        pass


def _bad_fileno(stream) -> bool:
    try:
        stream.fileno()
        return False
    except Exception:
        return True


class _Parser(argparse.ArgumentParser):
    def _print_message(self, message, file=None):
        """Ausgabe von --help / --version / Fehlern: erst an die Konsole des Aufrufers anhaengen (die gebaute .exe hat keine eigene), dann schreiben."""
        if message:
            attach_console()
            try:
                (sys.stderr if file is sys.stderr else sys.stdout).write(message)
            except Exception:
                pass


def build_parser() -> argparse.ArgumentParser:
    parser = _Parser(prog="OpenCue", description=f"{APP_NAME} - {APP_DESCRIPTION}", formatter_class=argparse.RawDescriptionHelpFormatter,
                                     epilog="Without options OpenCue starts normally (window, start screen, last show).\n"
                                            "Examples:\n  OpenCue.exe --no-ui --open-browser\n  OpenCue.exe \"D:\\Shows\\Concert.json\"\n  OpenCue.exe --no-ui --remote --port 8080")
    parser.add_argument("show_file", nargs="?", metavar="SHOWFILE", help="show file to load instead of the last one")
    parser.add_argument("--no-ui", "--server-only", dest="no_ui", action="store_true", help="run as a server without a program window (use a browser or a remote device); tray icon to quit")
    parser.add_argument("--open-browser", action="store_true", help="with --no-ui: open the default browser on the console at start")
    parser.add_argument("--show", metavar="FILE", help="show file to load instead of the last one")
    parser.add_argument("--new-show", action="store_true", help="start with an empty show instead of the last one (nothing is deleted)")
    parser.add_argument("--port", type=int, metavar="N", help="server port for this run only (1-65535)")
    parser.add_argument("--remote", action="store_true", help="switch network access (remote control) on (saved in the settings)")
    parser.add_argument("--data-dir", metavar="FOLDER", help="data folder for this run only (portable use, tests)")
    parser.add_argument("--fullscreen", action="store_true", help="start the program window in full screen")
    parser.add_argument("--priority", choices=PRIORITIES, default="above", help="process priority (default: above = above normal)")
    parser.add_argument("--no-splash", action="store_true", help="no start screen (also OPENCUE_NO_SPLASH=1)")
    parser.add_argument("--version", action="version", version=f"{APP_NAME} {APP_VERSION_LABEL}")
    return parser


def parse(argv: Optional[List[str]] = None, apply: bool = True) -> Options:
    """Parameter lesen. --help / --version / ein Fehler beenden das Programm hier (Ausgabe an der Konsole des Aufrufers). Mit apply=True werden die noetigen Umgebungsvariablen gesetzt."""
    argv = list(sys.argv[1:] if argv is None else argv)
    ns = build_parser().parse_args(argv)
    port = ns.port
    if port is not None and not (1 <= port <= 65535):
        build_parser().error("--port must be between 1 and 65535")
    show = ns.show or ns.show_file
    if show and ns.new_show:
        build_parser().error("--show and --new-show exclude each other")
    options = Options(no_ui=ns.no_ui, open_browser=ns.open_browser, show=show, new_show=ns.new_show, port=port, remote=ns.remote, data_dir=ns.data_dir,
                      fullscreen=ns.fullscreen, priority=ns.priority, no_splash=ns.no_splash)
    if apply:
        apply_environment(options)
    return options


def apply_environment(options: Options) -> None:
    """Umgebungsvariablen fuer die spaeteren Importe (Datenordner, Start-Show). Muss vor `app.paths` / `app.state_manager` laufen."""
    if options.data_dir:
        os.environ["OPENCUE_DATA_DIR"] = str(Path(options.data_dir).expanduser().resolve())
    if options.no_splash or options.no_ui:
        os.environ["OPENCUE_NO_SPLASH"] = "1"
    if options.no_ui:
        os.environ["OPENCUE_HEADLESS"] = "1"                              # die Oberflaeche zeigt dann z. B. keine Fenster-Funktionen an
    if options.new_show:
        os.environ["OPENCUE_START_SHOW"] = "-"
    elif options.show:
        os.environ["OPENCUE_START_SHOW"] = str(Path(options.show).expanduser().resolve())
