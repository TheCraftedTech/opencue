# Copyright (C) 2026 Samuel Zenker
# SPDX-License-Identifier: GPL-3.0-or-later
"""
errors.py
Fehlercodes und Fehlermeldungen von OpenCue - die EINE Stelle dafuer. Jeder Fehler, den das Programm dem Nutzer zeigt, traegt einen Code `OC-xxxx`; der Code
steht im Fehlerfenster (app/error_window.py), im Log und in den kopierten Angaben, damit man (und eine KI) beim Melden eines Fehlers sofort weiss, worum es geht.

Nummernkreise:  1xxx = Start-Pruefungen (Programm kann so nicht starten)   2xxx = unerwartete Fehler (Absturz, Hintergrundaufgabe, Server)
                3xxx = Probleme in einer Funktion (nur im Log; OpenCue laeuft weiter): 30xx Einstellungen, 31xx DMX-Ausgabe, 32xx Audio / Mikrofon, 33xx MIDI,
                       34xx Netzwerk (mDNS, Remote), 35xx Updates. Diese Codes stehen als "OC-3xxx" vorn in der Log-Zeile (Suche im Log: OC-3).
Die Erklaerung zu JEDEM Code (Bedeutung und Loesung) steht in static/help/error-codes.en.md und .de.md - bei neuen Codes dort ergaenzen.
Neuer Fehler: Eintrag in CATALOG (Titel, Text, Schwere "info" | "warning" | "error"; {Platzhalter} werden mit den Werten aus present(...) gefuellt), dann
`errors.present("OC-xxxx", ...)` aufrufen. Fenster-Codes (1xxx, 2xxx) zusaetzlich in app/errors_i18n.py in den fuenf anderen Sprachen ergaenzen: das Fenster erscheint in der
Sprache von OpenCue (Einstellungsdatei; Englisch, wenn nicht lesbar). Log-Zeilen und der Text von "Copy details" bleiben immer Englisch.

  OC-1001  Another OpenCue is already running (one instance per data folder)
  OC-1002  The network port of the built-in server is already used by another program
  OC-1003  The Microsoft Edge WebView2 Runtime was not found
  OC-1004  The data folder cannot be created or written
  OC-2001  An unexpected error stopped OpenCue while starting
  OC-2002  A background task failed (OpenCue keeps running)
  OC-2003  The built-in server stopped or did not start
  OC-2004  An unexpected error stopped OpenCue while running
  OC-3001  The settings file was unreadable (backup or defaults used)
  OC-3101  DMX output thread error            OC-3102  Art-Net output could not be re-initialised      OC-3103  USB DMX port lost or send error
  OC-3104  DMX output clock error             OC-3105  DMX output process ended / did not start
  OC-3201  Audio capture / source not available                                                       OC-3202  Microphone could not be opened
  OC-3301  A MIDI input could not be opened
  OC-3401  mDNS (opencue.local) not available  OC-3402  Remote access could not be made reachable on an address
  OC-3501  Update download failed              OC-3502  The update setup could not be started
  OC-3801  OSC port could not be opened
  OC-3601  JavaScript error in the user interface                                                      OC-3701  A background backup of the show could not be written
"""
from __future__ import annotations

import datetime
import platform
import sys
from typing import Dict, List, Optional, Tuple

from app.version import APP_NAME, APP_VERSION_LABEL

CATALOG: Dict[str, Tuple[str, str, str]] = {
    "OC-1001": ("OpenCue is already running",
                "Only one OpenCue can run at the same time on this computer. If a window is open, it has been brought to the front. "
                "If you have just closed OpenCue, it may still be shutting down: wait a few seconds and start it again. "
                "If you see no window at all, end a leftover OpenCue process in the Task Manager.", "info"),
    "OC-1002": ("Network port {port} is already in use",
                "OpenCue needs this port for its built-in server, but another program is using it. Close that program and start OpenCue again. "
                "To use a different port, change \"server_port\" in the settings file shown below.", "error"),
    "OC-1003": ("Microsoft Edge WebView2 Runtime not found",
                "OpenCue needs the free Microsoft Edge WebView2 Runtime to show its window, but it was not found on this computer. "
                "You can open the download page, or try to start anyway if you think this is a mistake.", "warning"),
    "OC-1004": ("The OpenCue data folder cannot be used",
                "OpenCue could not create or write to its data folder, so it cannot store settings, shows or logs. Check that the folder exists, that the drive is not full "
                "or read-only, and that your account may write there.", "error"),
    "OC-2001": ("OpenCue could not start",
                "An unexpected error stopped OpenCue while it was starting. Please copy the details and include them in a bug report.", "error"),
    "OC-2002": ("A background task failed",
                "OpenCue is still running, but something went wrong in the background. If anything behaves strangely, save your show and restart OpenCue. "
                "Please copy the details for a bug report.", "warning"),
    "OC-2003": ("The OpenCue server stopped",
                "The built-in server of OpenCue stopped unexpectedly or did not start, so the window cannot work. OpenCue will close. "
                "Please copy the details and include them in a bug report.", "error"),
    "OC-2004": ("OpenCue stopped unexpectedly",
                "An unexpected error occurred and OpenCue has to close. Unsaved changes may be lost. Please copy the details and include them in a bug report.", "error"),
    # --- 3xxx: nur im Log (severity "log"), kein Fenster; Erklaerung in static/help/error-codes.*.md
    "OC-3001": ("Settings file unreadable", "app_config.json could not be read; the backup (.bak) or the defaults are used.", "log"),
    "OC-3101": ("DMX output thread error", "An error occurred while sending DMX data.", "log"),
    "OC-3102": ("Art-Net output could not be re-initialised", "The Art-Net sender could not be set up with the current settings.", "log"),
    "OC-3103": ("USB DMX port lost or send error", "The USB DMX interface was unplugged or reported an error.", "log"),
    "OC-3104": ("DMX output clock error", "An error occurred in the clock that sends the DMX frames (Art-Net, sACN, USB).", "log"),
    "OC-3105": ("DMX output process ended or did not start", "The separate DMX output process stopped (it is restarted) or could not be started (output continues inside the main program).", "log"),
    "OC-3201": ("Audio capture not available", "The audio analysis could not open its input or source.", "log"),
    "OC-3202": ("Microphone could not be opened", "Voice control could not open the selected microphone.", "log"),
    "OC-3301": ("MIDI input could not be opened", "A MIDI device could not be opened (often in use by another program).", "log"),
    "OC-3401": ("mDNS not available", "The name opencue.local could not be announced on the network.", "log"),
    "OC-3402": ("Remote access address not reachable", "OpenCue could not listen on a network address for remote devices.", "log"),
    "OC-3501": ("Update download failed", "The new version could not be downloaded or verified.", "log"),
    "OC-3502": ("Update setup could not be started", "The downloaded setup could not be launched.", "log"),
    "OC-3601": ("JavaScript error in the interface", "The user interface reported a script error (the line in the log says where).", "log"),
    "OC-3801": ("OSC port not available", "OSC could not listen on its UDP port (another program uses it).", "log"),
    "OC-3701": ("Backup could not be written", "A background backup of the show could not be saved (disk full, folder not writable or protected).", "log"),
}


def _log_path_text(logsetup) -> str:
    try:
        return str(logsetup.log_path())
    except Exception:
        return "(not available)"


def diagnostics(code: str, title: str, message: str, details: str = "", log_lines: int = 40) -> str:
    """Der Text, den "Copy details" in die Zwischenablage legt: alles, was zum Melden eines Fehlers gebraucht wird (auch fuer eine KI lesbar)."""
    from app import logsetup, windows_env
    parts: List[str] = [
        f"{APP_NAME} {APP_VERSION_LABEL} - " + (f"error {code}" if code else "problem report"),
        f"Time: {datetime.datetime.now().isoformat(timespec='seconds')}",
        f"System: {platform.platform()} | Python {platform.python_version()} | {'packaged build' if getattr(sys, 'frozen', False) else 'run from source'} | {windows_env.describe()}",
        f"Log file: {_log_path_text(logsetup)}",
        "",
        f"{title}",
        f"{message}",
    ]
    if details.strip():
        parts += ["", "Details:", logsetup.redact(details.rstrip())]
    tail = logsetup.read_tail(log_lines)
    if tail:
        parts += ["", f"--- last {len(tail)} log lines ---"] + tail
    return "\n".join(parts) + "\n"


def _log_path_or_none(logsetup):
    try:
        return logsetup.log_path()
    except Exception:                                                    # z. B. Datenordner unbenutzbar (OC-1004)
        return None


def present(code: str, details: str = "", buttons=None, block: bool = True, **values) -> Optional[str]:
    """Fehlerfenster fuer `code` zeigen. `values` fuellen die {Platzhalter} im Text. Rueckgabe: Schluessel des gedrueckten Knopfes (oder None)."""
    title, message, severity = CATALOG[code]
    title, message = title.format(**values), message.format(**values)             # Englisch: Log und "Copy details"
    shown_title, shown_message = title, message
    try:
        from app import errors_i18n
        shown_title, shown_message = errors_i18n.code_text(code, *CATALOG[code][:2])
        shown_title, shown_message = shown_title.format(**values), shown_message.format(**values)
    except Exception:
        shown_title, shown_message = title, message
    try:
        from app import error_window, logsetup
        return error_window.show(
            code=code, title=shown_title, message=shown_message, details=details, severity=severity, buttons=buttons, block=block,
            clipboard=lambda: diagnostics(code, title, message, details), log_path=_log_path_or_none(logsetup),
        )
    except Exception as exc:                                             # das Melden eines Fehlers darf nicht selbst scheitern
        print(f"[{APP_NAME}] {code}: {title} - {message}\n{details}\n(error window failed: {exc})", file=sys.stderr)
        return None
