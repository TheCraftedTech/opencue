# Copyright (C) 2026 Samuel Zenker
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.



"""
main.py
Einstiegspunkt von OpenCue.

Version und Programm-Metadaten stehen an EINER Stelle: app/version.py (APP_VERSION = "1.0.0", Anzeige "v1.0.0"). `python main.py --version` gibt sie aus. Alle Startparameter (--no-ui / --server-only fuer den Betrieb ohne Fenster, --show, --new-show, --port, --remote, --data-dir, --fullscreen, --priority, --no-splash ...) stehen in app/cli.py und in `--help`.

START-PRUEFUNGEN UND FEHLER (immer in dieser Reihenfolge, bevor etwas anderes startet):
1. app/single_instance.py: laeuft schon ein OpenCue mit demselben Datenordner? -> dessen Fenster nach vorn, Fehlerfenster OC-1001, Ende.
2. app/logsetup.py: Protokolldatei <Datenordner>/logs/opencue.log (vorige: opencue.previous.log), Konsole wird gespiegelt, faulthandler.
3. app/crash.py: unbehandelte Fehler (Hauptthread, Hintergrund-Threads, Server-Thread) -> Log + Fehlerfenster (OC-2001..OC-2004).
4. Startbild; danach (in main()) WebView2-Pruefung (OC-1003) und Port-Pruefung (OC-1002) VOR dem Start des Servers.
Fehlerfenster und Codes: app/error_window.py, app/errors.py (immer Englisch, nicht konfigurierbar).


THREADING-MODELL (wichtig):
Uvicorn laeuft ausschliesslich in einem Hintergrund-Thread.
`webview.create_window()` und `webview.start()` laufen zwingend im
Haupt-Thread. pywebviews Windows-Backend (WebView2/CoreWebView2) darf nur
vom UI-Thread aus angesprochen werden - Zugriffe aus einem anderen Thread
bzw. eine reentrante js_api-Bruecke fuehren zu Fehlern wie
"CoreWebView2 members can only be accessed from the UI thread" oder zu
"maximum recursion depth exceeded" in der pywebview-JS-Bridge.

DUMMY-CONTAINER-PRINZIP:
Deshalb bekommt das Fenster hier bewusst KEIN `js_api`-Objekt, und es wird
nie per `evaluate_js` vom Server aus in die Seite hineinregiert. Es ist ein
reiner, passiver Container fuer die UI. Jegliche Kommunikation zwischen
Frontend und Backend - Events, Befehle, auch ein "Exit"-Request oder der
F11-Fullscreen-Shortcut aus dem Frontend - laeuft ausschliesslich ueber den
WebSocket-Kanal (/ws).

Ein Exit- oder Fullscreen-Toggle-Request kommt dadurch im Uvicorn-Thread an
(app/server.py) und wird dort nur als Flag gesetzt (threading.Event in
app/window_signals.py, keine pywebview-Abhaengigkeit in server.py). Kleine
Watcher-Threads unten reagieren darauf und rufen `window.destroy()` bzw.
`window.toggle_fullscreen()` auf. Anders als ein js_api-Aufruf (der
reentrant auf dem UI-Thread selbst landen kann) sind diese pywebview-
Methoden fuer Cross-Thread-Aufrufe ausgelegt: pywebviews Windows-Backend
marshalt sie intern sicher ueber WinForms' Control.Invoke auf den UI-Thread.

Sauberes Beenden ist von drei Seiten abgesichert:
  - Klick auf "X": window.events.closing wird ausgeloest und bricht das
    Schliessen ab; der Server schickt dem Frontend "close_requested", dort
    erscheint der Dialog (mit Speichern / ohne Speichern / Abbrechen).
  - File -> Exit im Frontend: WebSocket exit_app -> denselben Dialog. Nach
    "mit/ohne Speichern" setzt der Server exit_requested -> Watcher-Thread ->
    close_allowed + window.destroy() -> window.events.closed.
  - Strg+C im Terminal: pywebviews Windows-Backend faengt SIGINT bereits
    intern ab und schliesst das Fenster programmatisch - ebenfalls ueber
    window.events.closed.
In allen drei Faellen laeuft exakt derselbe _shutdown()-Pfad: DMX-Engine
stoppen, Uvicorn-Server stoppen und auf dessen Thread warten, damit beim
Prozessende keine Hintergrund-Threads oder Sockets zurueckbleiben.

FENSTER-GEOMETRIE UEBER MEHRERE MONITORE:
pywebviews winforms-Backend setzt beim Erzeugen des Fensters erst die
Position (`Location`), dann - falls gewuenscht - den maximierten
WindowState (siehe platforms/winforms.py). Windows maximiert ein Fenster
immer auf den Monitor, auf dem sich sein `Location`-Punkt befindet. Das
heisst: um nach einem Neustart auf dem RICHTIGEN Monitor zu maximieren,
muessen x/y auch dann uebergeben werden, wenn `maximized=True` ist - nicht
nur im normalen (nicht maximierten) Fall. Deshalb trackt window_geometry
x/y **sowohl im normalen als auch im maximierten Zustand** (nur nicht
minimiert, dort meldet Windows Sentinel-Koordinaten wie -32000), waehrend
width/height nur im normalen Zustand sinnvoll sind (eine maximierte
Groesse waere als "wiederherzustellende" Normalgroesse bedeutungslos) und
entsprechend nur dort mitgeschrieben werden.

Ist die gespeicherte Position auf keinem aktuell angeschlossenen Monitor
mehr sichtbar (z.B. 2. Monitor abgesteckt), werden x/y beim Start komplett
weggelassen - pywebview zentriert dann selbst auf dem Hauptmonitor
(FormStartPosition.CenterScreen), maximiert-Status bleibt davon unberuehrt.

F11 UND ECHTER FULLSCREEN:
`window.toggle_fullscreen()` durchlaeuft intern denselben
WindowState.Maximized-Uebergang wie ein normales Maximieren (siehe
winforms.py) - loest also dieselben moved/resized/maximized/restored-
Events aus, obwohl es kein vom Nutzer gewaehlter Fenster-Zustand ist. Waehrend
`window_geometry["is_fullscreen"]` gesetzt ist, ignorieren alle Event-
Handler unten diese Events komplett, damit ein F11-Ausflug die eigentliche
normale/maximierte Geometrie nicht überschreibt. Das Flag wird VOR dem
Betreten und NACH dem Verlassen von toggle_fullscreen() gesetzt/geloescht,
sodass auch die synchron beim Verlassen ausgeloesten Events noch sicher
unterdrueckt werden. Zusaetzlich hat pywebviews eigene
toggle_fullscreen()-Implementierung einen Quirk beim Verlassen: sie setzt
den WindowState IMMER auf Normal zurueck, selbst wenn das Fenster vorher
echt maximiert war (siehe _watch_fullscreen_toggle). Das wird dort explizit
per window.maximize() nachkorrigiert.

Der exklusive Fullscreen-Zustand selbst wird NIE in app_config.json
persistiert (siehe app/state_manager.py) - nach jedem Neustart landet
OpenCue immer im normalen bzw. Fenster-Vollbild-Modus, nie automatisch im
exklusiven Fullscreen.
"""

from __future__ import annotations

import os
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path

_T0 = time.monotonic()                          # Zeitnullpunkt fuer die Start-Messung im Protokoll

# Der Ausgabe-Prozess der DMX-Ausgabe (app/dmx_output.py): ein zweiter, schlanker Prozess - vor ALLEM anderen, ohne Fenster, Server, Protokoll und Einzelstart-Pruefung.
if len(sys.argv) > 2 and sys.argv[1] == "--dmx-output":
    from app.dmx_output import child_main
    sys.exit(child_main(sys.argv[2:]))

# Hilfsprozess fuer grosse GDTF-Dateien (app/fixture_manager.py): liest eine Datei und gibt die Typdaten als JSON aus - so steht der Server beim Einlesen nie still.
if len(sys.argv) > 3 and sys.argv[1] == "--gdtf-worker":
    from app.fixture_manager import worker_main
    sys.exit(worker_main(sys.argv[2:]))


from app.version import APP_NAME, APP_VERSION_LABEL, WEBVIEW2_URL  # noqa: E402  (leicht: nur Konstanten)

# Startparameter (app/cli.py: --no-ui, --show, --port, --remote, --data-dir ...). --help / --version / ein Fehler beenden hier. Setzt auch Umgebungsvariablen (Datenordner,
# Start-Show), die erst die spaeteren Importe lesen - deshalb VOR ihnen.
from app import cli  # noqa: E402  (leicht)

OPTIONS = cli.parse()

# Nur ein OpenCue je Datenordner: als ERSTES pruefen, noch vor Protokoll, Startbild, Server und Port (app/single_instance.py). Laeuft schon eines, kommt dessen
# Fenster in den Vordergrund und das Fehlerfenster OC-1001 (app/error_window.py); dieses Programm beendet sich, ohne etwas anzufassen.
from app import errors, single_instance  # noqa: E402


def _check_data_folder() -> None:
    """Der Datenordner muss sich anlegen und beschreiben lassen (OC-1004) - sonst gaebe es weder Einstellungen noch Log; ohne Pruefung kaeme nur ein stummer Absturz."""
    try:
        from app import paths
        probe = paths.default_data_root() / "config" / ".write-test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
    except Exception as exc:
        folder = os.environ.get("OPENCUE_DATA_DIR") or os.path.join(os.environ.get("LOCALAPPDATA", "~"), "OpenCue")
        errors.present("OC-1004", details=f"Folder: {folder}\n{type(exc).__name__}: {exc}")
        sys.exit(1)


_check_data_folder()
if not single_instance.acquire():                                   # nie warten: das Startbild soll sofort kommen, ein Fehler ist besser als eine Pause ohne Rueckmeldung
    _running = single_instance.read_runfile()
    _raised = single_instance.raise_running_window()
    print(f"[{APP_NAME}] another instance is already running (its window was raised: {_raised})")
    if OPTIONS.show and _running.get("port") and single_instance.forward_show(_running["port"], os.environ.get("OPENCUE_START_SHOW") or OPTIONS.show):         # Doppelklick auf eine Show-Datei: das laufende OpenCue oeffnet sie
        print(f"[{APP_NAME}] the file was handed to the running instance")
        sys.exit(0)
    if _running.get("headless") and _running.get("port"):                    # ein Server ohne Fenster laeuft: kein Fehler, sondern gleich die Konsole im Browser zeigen
        webbrowser.open(f"http://127.0.0.1:{int(_running['port'])}")
        sys.exit(0)
    errors.present("OC-1001")
    sys.exit(1)

# Protokolldatei (opencue.log, vorige als opencue.previous.log) und Absturz-Haken - vor allen Importen, die Logging einrichten (uvicorn, app.server).
from app import crash, logsetup  # noqa: E402

logsetup.prepare()
crash.install()

from app import windows_env  # noqa: E402

windows_env.set_priority(OPTIONS.priority)                      # stabileres Zeitverhalten der DMX-Ausgabe bei ausgelastetem Rechner (kein Administrator noetig)
windows_env.precise_timers(True)                                # Zeitgeber 1 ms statt ~15,6 ms: gleichmaessigere 40-Hz-Schleifen
print(f"[{APP_NAME}] {windows_env.describe()} | priority {OPTIONS.priority}" + (" | mode: server only (no window)" if OPTIONS.no_ui else ""))
if windows_env.is_admin():
    print(f"[{APP_NAME}] NOTE: OpenCue runs as administrator. That is not needed (only the firewall rule needs it) and Windows then blocks drag & drop of files from Explorer into the window.")

# Startbild SOFORT zeigen, noch vor den schweren Importen unten (uvicorn, webview, Server ~2 s); es schliesst sich erst, wenn die Oberflaeche
# im Programmfenster fertig aufgebaut ist (siehe main(): ui_ready). Rein ctypes, Details in app/splash.py.
from app.splash import Splash, logo_path  # noqa: E402
from app.version import APP_DESCRIPTION  # noqa: E402

splash = Splash(logo_path(), APP_DESCRIPTION, APP_VERSION_LABEL)
splash.start()
from app import startup_progress  # noqa: E402  (winzig)
from app.error_window import Button  # noqa: E402
crash.install(before_dialog=lambda: splash.close(wait=0.3), cleanup=lambda: _emergency_cleanup())      # Startbild weg, bevor ein Fehlerfenster kommt
startup_progress.set_callback(splash.progress)        # Stationen (hier und im Server) melden Prozent + Text; Ablauf siehe app/startup_progress.py

# Medien-Player: Video/Audio sollen auch ohne vorherigen Klick starten koennen (Timecode-gesteuerte Wiedergabe an der Konsole).
# Muss gesetzt sein, bevor WebView2 startet.
os.environ.setdefault("WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS", "--autoplay-policy=no-user-gesture-required")

startup_progress.report(4, "Loading libraries")
import uvicorn
import webview

startup_progress.report(14, "Loading network and camera modules")
from app import host_cameras, remote
from app.paths import APP_CONFIG_PATH, get_data_root, project_root
startup_progress.report(22, "Loading DMX engine")
from app.dmx_engine import dmx_engine
from app.lan_listener import lan
startup_progress.report(26, "Loading console server")
from app.server import app, request_close_prompt
from app.state_manager import state
if not state.first_start_done and (not OPTIONS.no_ui or os.environ.get("OPENCUE_ONBOARDING")) and not os.environ.get("OPENCUE_NO_ONBOARDING"):          # frische Installation: der Willkommens-Dialog fuehrt durch die ersten Einstellungen (static/js/welcome.js)
    state.onboarding_pending = True
startup_progress.report(40, "Checking display component")
from app.window_signals import close_allowed, exit_requested, file_dialog, fullscreen_toggle_requested, ui_ready

HOST = "127.0.0.1"  # Adresse, unter der der lokale PyWebView-Client den Server erreicht
PORT = OPTIONS.port or state.server_port   # Einstellung 'server_port'; Aenderungen gelten ab dem naechsten Start; --port gilt nur fuer diesen Lauf
# Der Server lauscht immer nur lokal; der Netzwerk-Zugriff (Remote) haengt zur Laufzeit je Netzwerk-Adresse weitere Listener dazu und wieder ab
# (app/lan_listener.py) - ein-/ausschalten in den Einstellungen wirkt sofort, ohne Neustart. Nur ein geaenderter Port gilt ab dem naechsten Start.
BIND_HOST = "127.0.0.1"
remote.bound_host = BIND_HOST
remote.bound_port = PORT
if OPTIONS.remote and not state.remote_enabled:                       # --remote: Netzwerk-Zugriff (Fernzugriff) einschalten und in den Einstellungen merken
    if not state.remote_password:                                     # es gibt kein Standardpasswort: ohne eigenes Passwort bleibt der Fernzugriff aus
        print(f"[{APP_NAME}] --remote ignored: no password set yet. Open OpenCue on this computer and set one (Settings -> Security), then start again.")
    else:
        state.set_remote_enabled(True)
        print(f"[{APP_NAME}] --remote: network access switched on (saved in the settings)")
MIN_WINDOW_SIZE = (1024, 600)


# Grenzwerte, innerhalb derer eine von moved() gemeldete Position als "echt"
# gilt - filtert Windows' Off-Screen-Sentinel-Koordinaten (typischerweise
# rund -32000) beim Minimieren heraus, ohne legitime Multi-Monitor-Setups
# mit gemaessigt negativen Koordinaten (z.B. ein Monitor links der primaeren
# Anzeige) faelschlich zu verwerfen.
_PLAUSIBLE_COORD_RANGE = (-10000, 100000)


def _port_is_open(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.25)
        return sock.connect_ex((host, port)) == 0


def _wait_for_server(timeout_seconds: float = 10.0) -> None:
    """Blockiert, bis der Server erreichbar ist (oder das Timeout ablaeuft)."""
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if _port_is_open(HOST, PORT):
            return
        time.sleep(0.1)


def _run_server(server: uvicorn.Server) -> None:
    """Rumpf des Server-Threads: ein Absturz (oder ein Start, der scheitert - uvicorn beendet sich dann mit SystemExit) ist schwer, aber nie stumm (OC-2003)."""
    try:
        server.run()
    except BaseException:
        if not server.should_exit:                                       # nicht beim normalen Beenden
            crash.fatal("OC-2003", sys.exc_info())


def _emergency_cleanup() -> None:
    """Vor dem harten Ende nach einem schweren Fehler: Kameras freigeben, DMX sauber beenden (so weit schon geladen)."""
    for step in (lambda: host_cameras.stop_all(), lambda: dmx_engine.shutdown()):
        try:
            step()
        except Exception:
            pass


def _start_server() -> tuple[uvicorn.Server, threading.Thread]:
    """Startet Uvicorn in einem Hintergrund-Thread und gibt Server + Thread zurueck.

    Die Server-Instanz wird bewusst nicht gekapselt: main() braucht sie, um
    per `should_exit` einen sauberen Shutdown auszuloesen und den Thread
    danach zu joinen, statt sich auf das Daemon-Flag allein zu verlassen.
    """
    # ws_per_message_deflate=False: keine WebSocket-Kompression. Im lokalen Netz bringt sie nichts, kostete aber ~35 % der Rechenzeit des Servers bei starker Bedienung (je Nachricht zlib).
    config = uvicorn.Config(app, host=BIND_HOST, port=PORT, log_level="info", ws_per_message_deflate=False)
    server = uvicorn.Server(config)
    lan.attach(server)                                   # Netzwerk-Listener (Remote) richtet der Lifespan-Start ein, sobald der Server laeuft
    thread = threading.Thread(target=_run_server, args=(server,), name="uvicorn", daemon=True)
    thread.start()
    return server, thread


def _stop_everything(server: uvicorn.Server, server_thread: threading.Thread) -> None:
    """Gemeinsamer Rest des Beendens (mit und ohne Fenster): DMX stoppen, ungespeicherte Aenderungen sichern, Server anhalten, Markierungen loeschen, ein vorgemerktes Update starten."""
    dmx_engine.shutdown()

    from app import backups
    try:
        backups.manager.take_now_blocking("exit")                    # ungespeicherte Aenderungen noch einmal sichern (Datei -> Sicherung wiederherstellen); doppelt wird nichts geschrieben
    except Exception as exc:                                         # noqa: BLE001 - das Beenden darf daran nie haengen
        print(f"[OpenCue] Sicherung beim Beenden nicht geschrieben: {exc}")

    server.should_exit = True
    server_thread.join(timeout=5)
    backups.manager.end_session()                                    # sauber beendet: beim naechsten Start kein Angebot "Wiederherstellen" (nach einem Absturz bleibt die Markierung liegen)
    single_instance.clear_runfile()
    windows_env.precise_timers(False)

    print("[OpenCue] Shutdown complete.")
    try:
        from app import updater
        if updater.launch_pending_installer():              # Update vorgemerkt ("Jetzt installieren"): das Setup startet erst jetzt, nach dem Beenden
            print("[OpenCue] Update-Setup gestartet.")
    except Exception as exc:
        print(f"[OpenCue] Update-Setup konnte nicht gestartet werden: {exc}")


def _open_close_dialog_in_page(window: "webview.Window") -> None:
    """Beenden-Dialog direkt in der Seite oeffnen (ohne den Umweg ueber den Server). Fehler sind hier egal: der Server schickt denselben Befehl noch einmal."""
    try:
        window.evaluate_js("if (typeof _openCloseDialog === 'function') { _pendingCloseAfterSave = false; _closeSaveInFlight = false; _openCloseDialog(); }")
    except Exception:                                                            # noqa: BLE001
        pass


def _watch_exit_signal(window: webview.Window, stop_watching: threading.Event) -> None:
    """Eigener Daemon-Thread, der auf einen per WebSocket ausgeloesten
    Exit-Request wartet (app/window_signals.py) und dann das Fenster
    schliesst. Laeuft NICHT auf dem UI-Thread - das ist fuer
    window.destroy() unproblematisch (siehe Moduldocstring), im Gegensatz zu
    einer js_api-Bruecke.
    """
    while not stop_watching.is_set():
        if exit_requested.wait(timeout=0.25):
            close_allowed.set()
            window.destroy()
            return


def _watch_fullscreen_toggle(
    window: webview.Window, window_geometry: dict, stop_watching: threading.Event
) -> None:
    """Eigener Daemon-Thread fuer den F11-Shortcut/View-Menu-Toggle: laeuft
    die ganze Sitzung ueber (im Gegensatz zum einmaligen Exit-Watcher), da
    Fullscreen beliebig oft umgeschaltet werden kann.

    Setzt `window_geometry["is_fullscreen"]` VOR dem Aufruf beim Betreten
    und loescht es ERST NACH dem Aufruf beim Verlassen - so sind auch die
    synchron innerhalb von toggle_fullscreen() ausgeloesten
    moved/resized/maximized/restored-Events sicher als "kein echter
    Nutzer-Fensterwechsel" markiert (siehe Moduldocstring).

    BEKANNTER PYWEBVIEW-QUIRK BEIM VERLASSEN: toggle_fullscreen() setzt beim
    Verlassen IMMER `WindowState = Normal` (siehe platforms/winforms.py),
    selbst wenn das Fenster davor echt maximiert war - es vergroessert dann
    nur ein "normales" Fenster auf die alten maximierten Bounds, ohne
    jemals wieder in den echten Maximized-Zustand zu wechseln. Das Fenster
    SIEHT dadurch maximiert aus, verhaelt sich aber nicht so (z.B.
    Doppelklick auf die Titelleiste oder der Wiederherstellen-Button
    funktionieren dann nicht mehr richtig). Da `window_geometry["maximized"]`
    waehrend der gesamten Fullscreen-Sitzung eingefroren bleibt (s.o.), gibt
    dessen Wert direkt VOR dem Verlassen zuverlaessig wieder, ob das Fenster
    vorher echt maximiert war - falls ja, wird hier explizit noch einmal
    `window.maximize()` nachgeschoben, um den echten WindowState wieder
    korrekt herzustellen. War es vorher nicht maximiert, restauriert
    toggle_fullscreen() Position/Groesse bereits korrekt selbst.
    """
    while not stop_watching.is_set():
        if fullscreen_toggle_requested.wait(timeout=0.25):
            fullscreen_toggle_requested.clear()
            entering_fullscreen = not window_geometry["is_fullscreen"]
            if entering_fullscreen:
                window_geometry["is_fullscreen"] = True
                window.toggle_fullscreen()
            else:
                was_maximized = window_geometry["maximized"]  # eingefroren seit dem Betreten
                window.toggle_fullscreen()
                window_geometry["is_fullscreen"] = False
                if was_maximized:
                    window.maximize()


def _position_is_visible(x: int, y: int, width: int, height: int) -> bool:
    """Best-effort-Pruefung, ob eine gespeicherte Fensterposition noch auf
    einem aktuell angeschlossenen Monitor liegt (z.B. wurde der 2. Monitor
    von der letzten Sitzung inzwischen abgesteckt). Kann die Bildschirmliste
    nicht ermittelt werden, wird im Zweifel "sichtbar" angenommen - lieber
    eine ungenutzte Pruefung als ein faelschlich verworfenes, echtes Fenster.
    """
    try:
        screens = webview.screens
    except Exception:
        return True

    center_x = x + width // 2
    center_y = y + height // 2
    return any(
        screen.x <= center_x <= screen.x + screen.width and screen.y <= center_y <= screen.y + screen.height
        for screen in screens
    )


def _resolve_window_geometry() -> dict:
    """Baut die create_window()-kwargs aus der zuletzt gespeicherten
    Fenstergeometrie (app_config.json).

    x/y werden IMMER mitgegeben, wenn sie noch auf einem angeschlossenen
    Monitor liegen - auch wenn das Fenster maximiert startet, denn Windows
    maximiert auf den Monitor, auf dem `Location` liegt (siehe
    Moduldocstring). width/height kommen nur dazu, wenn NICHT maximiert
    gestartet wird (eine maximierte Groesse ist keine sinnvolle
    "Normalgroesse"). Ohne gueltige Position (erster Start oder Monitor
    nicht mehr vorhanden) laesst pywebview das Fenster selbst auf dem
    Hauptmonitor zentrieren.
    """
    has_position = (
        state.window_x is not None
        and state.window_y is not None
        and _position_is_visible(
            state.window_x,
            state.window_y,
            state.window_width or MIN_WINDOW_SIZE[0],
            state.window_height or MIN_WINDOW_SIZE[1],
        )
    )

    geometry: dict = {"maximized": state.window_maximized}

    if has_position:
        geometry["x"] = state.window_x
        geometry["y"] = state.window_y
        if not state.window_maximized and state.window_width and state.window_height:
            geometry["width"] = max(state.window_width, MIN_WINDOW_SIZE[0])
            geometry["height"] = max(state.window_height, MIN_WINDOW_SIZE[1])

    return geometry


# Eigene Programmkennung: Windows ordnet das Fenster und seine Taskleisten-Gruppe damit OpenCue zu (nicht python.exe) und nimmt das Programm-Icon.
APP_USER_MODEL_ID = "OpenCue.Console"
_WEBVIEW2_CLIENT_GUID = "{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}"


def _set_app_user_model_id() -> None:
    if sys.platform != "win32":
        return
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)
    except Exception:
        pass                                    # rein kosmetisch (Taskleiste)


def _webview2_installed() -> bool:
    """Ist die Edge-WebView2-Laufzeit installiert? (Registry wie von Microsoft beschrieben, danach der Programmordner als Rueckfall.) Auf anderen Systemen immer True."""
    if sys.platform != "win32":
        return True
    import winreg
    suffix = "\\Microsoft\\EdgeUpdate\\Clients\\" + _WEBVIEW2_CLIENT_GUID
    keys = [
        (winreg.HKEY_LOCAL_MACHINE, "SOFTWARE\\WOW6432Node" + suffix),     # systemweit, 64 Bit
        (winreg.HKEY_LOCAL_MACHINE, "SOFTWARE" + suffix),
        (winreg.HKEY_CURRENT_USER, "Software" + suffix),                    # nur fuer den Benutzer
    ]
    for hive, path in keys:
        try:
            with winreg.OpenKey(hive, path) as key:
                value, _kind = winreg.QueryValueEx(key, "pv")
            if value and str(value) != "0.0.0.0":
                return True
        except OSError:
            continue
    for variable in ("ProgramFiles(x86)", "ProgramFiles"):
        base = os.environ.get(variable)
        if base and os.path.isdir(os.path.join(base, "Microsoft", "EdgeWebView", "Application")):
            return True
    return False


def _ensure_webview2() -> bool:
    """Ohne WebView2 oeffnet sich kein Fenster. Statt eines stillen Abbruchs das Fehlerfenster OC-1003 (Windows 10 ohne Edge-Laufzeit): Download-Seite oeffnen und beenden,
    oder trotzdem versuchen zu starten (falls die Erkennung irrt; Esc/X = beenden). True = weiter."""
    if _webview2_installed():
        return True
    splash.close(wait=0.3)
    answer = errors.present("OC-1003", details=WEBVIEW2_URL, buttons=[Button("continue", "Start anyway"), Button("download", "Open download page", primary=True)])
    if answer == "continue":
        return True
    if answer == "download":
        webbrowser.open(WEBVIEW2_URL)
    return False


def _window_icon() -> str | None:
    """Pfad der .ico fuer die Fensterleiste (Build: OpenCue.ico im Programmordner; Quelltext: packaging/OpenCue.ico). Ohne Datei nimmt pywebview das Icon der .exe."""
    root = project_root()
    for candidate in (root / "OpenCue.ico", root / "packaging" / "OpenCue.ico"):
        if candidate.is_file():
            return str(candidate)
    return None


def _tray_labels() -> dict:
    """Menuetexte des Tray-Symbols in der Sprache der Konsole."""
    from app.languages import tr
    language = getattr(state, "language", "en")
    return {"open": tr("SRV_TRAY_OPEN", language), "logs": tr("SRV_TRAY_LOGS", language), "quit": tr("SRV_TRAY_QUIT", language)}


def _confirm_quit_headless() -> bool:
    """Beenden ueber das Tray-Symbol: hat die Show ungespeicherte Aenderungen, einmal nachfragen (eine Sicherung wird in jedem Fall geschrieben)."""
    if not state.is_dirty:
        return True
    from app.languages import tr
    text = tr("SRV_QUIT_CONFIRM", getattr(state, "language", "en"))
    try:
        import ctypes
        return ctypes.windll.user32.MessageBoxW(None, text, "OpenCue", 0x00000004 | 0x00000030 | 0x00010000) == 6          # Ja/Nein, Warnsymbol, in den Vordergrund; 6 = Ja
    except Exception:
        return True


def _main_headless() -> None:
    """Server ohne Programmfenster (--no-ui / --server-only): alles laeuft wie gewohnt, bedient wird im Browser (http://127.0.0.1:<Port>) oder per Fernzugriff. Tray-Symbol zum Beenden."""
    import signal
    print(f"[{APP_NAME}] {APP_VERSION_LABEL} starting (server only) ...")
    if _port_is_open(HOST, PORT):
        errors.present("OC-1002", details=f"Address: {HOST}:{PORT}\nSettings file: {APP_CONFIG_PATH}", port=PORT)
        sys.exit(1)
    server, server_thread = _start_server()
    _wait_for_server()
    ui_ready.set()                                                       # (kein Fenster, das fertig werden muesste: Fehler ab jetzt sind Laufzeitfehler, kein Startfehler)
    url = f"http://{HOST}:{PORT}"
    single_instance.write_runfile(PORT, True)
    print(f"[{APP_NAME}] Server only - open {url} in a browser" + ("" if state.remote_enabled else "  (network access is off: only this computer; start with --remote or switch it on in Settings -> Remote access)"))

    def _open_browser() -> None:
        webbrowser.open(url)

    def _open_logs() -> None:
        try:
            os.startfile(str(logsetup.log_dir()))                        # noqa: S606 - Windows
        except Exception as exc:                                         # noqa: BLE001
            print(f"[{APP_NAME}] log folder: {exc}")

    def _quit() -> None:
        if _confirm_quit_headless():
            exit_requested.set()

    def _tray_info() -> dict:
        """Kopfzeilen des Tray-Menues: Show (mit Warnung bei ungespeicherten Aenderungen) und die Adressen, unter denen die Konsole erreichbar ist."""
        from app.languages import tr
        language = getattr(state, "language", "en")
        name = state.showfile_name or tr("SRV_TRAY_UNTITLED", language)
        urls = [url]
        if state.remote_enabled:
            urls += [f"http://{ip}:{PORT}" for ip in remote.lan_addresses()[:4]]
        return {"title": tr("SRV_TRAY_SHOW", language, name=name), "urls": urls, "warning": tr("SRV_TRAY_UNSAVED", language) if state.is_dirty else ""}

    def _tray_tooltip() -> str:
        from app.languages import tr
        extra = tr("SRV_TRAY_TIP_UNSAVED", getattr(state, "language", "en")) if state.is_dirty else ""
        return f"OpenCue {APP_VERSION_LABEL} - {url}{extra}"

    from app.tray import Tray
    tray = Tray(_tray_tooltip(), _tray_labels, _open_browser, _open_logs, _quit, on_end_session=exit_requested.set, icon_path=_window_icon(), info=_tray_info, on_url=lambda address: webbrowser.open(address))
    if not tray.start():
        print(f"[{APP_NAME}] WARNING: the tray icon is not available - quit with Ctrl+C, from the web interface (File -> Exit) or by ending the process")
    for sig in ("SIGINT", "SIGBREAK", "SIGTERM"):                        # Ctrl+C / Konsole schliessen / beenden
        try:
            signal.signal(getattr(signal, sig), lambda *_a: exit_requested.set())
        except (AttributeError, ValueError, OSError):
            pass
    if OPTIONS.open_browser:
        _open_browser()
    try:
        last_tip = ""
        while not exit_requested.is_set() and server_thread.is_alive():
            exit_requested.wait(timeout=0.5)
            tip = _tray_tooltip()                                        # das Symbol warnt bei ungespeicherten Aenderungen (Hinweistext)
            if tip != last_tip:
                last_tip = tip
                tray.set_tooltip(tip)
    except KeyboardInterrupt:
        pass
    finally:
        crash.dialogs_enabled = False
        print(f"[{APP_NAME}] Shutting down ...")
        host_cameras.stop_all()
        tray.stop()
        _stop_everything(server, server_thread)


def main() -> None:
    _set_app_user_model_id()
    if OPTIONS.no_ui:
        _main_headless()
        return
    if not _ensure_webview2():
        splash.close()
        return
    print(f"[{APP_NAME}] {APP_VERSION_LABEL} starting ...")
    if _port_is_open(HOST, PORT):                                        # belegt (anderes Programm): klare Meldung statt dessen Seite im eigenen Fenster
        splash.close(wait=0.3)
        errors.present("OC-1002", details=f"Address: {HOST}:{PORT}\nSettings file: {APP_CONFIG_PATH}", port=PORT)
        sys.exit(1)
    startup_progress.report(43, "Starting server")
    server, server_thread = _start_server()
    _wait_for_server()
    single_instance.write_runfile(PORT, False)

    initial_geometry = _resolve_window_geometry()

    # Laufend durch moved/resized/maximized/restored/minimized aktualisiert,
    # beim Schliessen persistiert (siehe Moduldocstring fuer die genauen
    # Regeln, wann welches Feld mitgeschrieben wird).
    window_geometry = {
        "x": initial_geometry.get("x"),
        "y": initial_geometry.get("y"),
        "width": initial_geometry.get("width"),
        "height": initial_geometry.get("height"),
        "maximized": initial_geometry["maximized"],
        "mode": "maximized" if initial_geometry["maximized"] else "normal",  # "normal" | "maximized" | "minimized"
        "is_fullscreen": False,
    }

    # Kein js_api-Parameter (Dummy-Container-Prinzip) - das Fenster ist ein
    # reiner Viewport auf die WebSocket-getriebene UI.
    startup_progress.report(68, "Opening window")
    window = webview.create_window(
        "OpenCue",
        url=f"http://{HOST}:{PORT}",
        resizable=True,
        min_size=MIN_WINDOW_SIZE,
        confirm_close=False,
        hidden=splash.shown.is_set(),           # erst zeigen, wenn die Oberflaeche fertig ist (Startbild laeuft darueber); ohne Startbild sofort
        **initial_geometry,
    )

    def _reveal_when_ready() -> None:
        """Startbild-Ablauf. Das Programmfenster wird sofort "sichtbar, aber durchsichtig" (Opacity 0) gemacht: ein wirklich verborgenes Fenster
        laedt seine Seite nur sehr langsam (Chromium drosselt Netzwerk und Timer verdeckter Seiten, die Oberflaeche wurde nie fertig). Sobald die
        Oberflaeche fertig ist (ui_ready), wird es eingeblendet, waehrend das Startbild ausblendet."""
        form = None
        if splash.shown.is_set():
            try:
                from webview.platforms import winforms          # laedt pythonnet (clr); erst danach gibt es das Modul System
                from System import Func, Type
                winforms._main_window_created.wait(20)
                form = winforms.BrowserView.instances.get(window.uid)

                def _hold():
                    form.Opacity = 0.0
                    form.Show()

                form.Invoke(Func[Type](_hold))
            except Exception as exc:
                print(f"[{APP_NAME}] Fenster vorbereiten: {exc}")
                form = None
                try:
                    window.show()                       # Rueckfall: Fenster normal zeigen, das Startbild schliesst sich gleich
                except Exception:
                    pass
        got = ui_ready.wait(timeout=30)
        print(f"[{APP_NAME}] UI ready after {time.monotonic() - _T0:.1f} s" if got else f"[{APP_NAME}] UI not reported ready after 30 s - showing window anyway")
        if form is not None:
            time.sleep(0.3)                     # der Balken erreicht 100 %, bevor es einblendet
            try:
                from webview.platforms import winforms  # noqa: F401
                from System import Func, Type
                for step in range(1, 7):
                    form.Invoke(Func[Type](lambda k=step: setattr(form, "Opacity", k / 6.0)))
                    time.sleep(0.03)
                form.Invoke(Func[Type](form.Activate))
            except Exception as exc:
                print(f"[{APP_NAME}] Fenster einblenden: {exc}")
                try:
                    window.show()
                except Exception:
                    pass
        splash.close()
        if OPTIONS.fullscreen:
            fullscreen_toggle_requested.set()                           # --fullscreen: der Beobachter-Thread schaltet das Fenster in den Vollbildmodus

    threading.Thread(target=_reveal_when_ready, name="reveal", daemon=True).start()

    def _on_moved(x: int, y: int) -> None:
        if window_geometry["is_fullscreen"] or window_geometry["mode"] not in ("normal", "maximized"):
            return
        low, high = _PLAUSIBLE_COORD_RANGE
        if low < x < high and low < y < high:
            window_geometry["x"] = x
            window_geometry["y"] = y

    def _on_resized(width: int, height: int) -> None:
        if window_geometry["is_fullscreen"] or window_geometry["mode"] != "normal":
            return
        window_geometry["width"] = width
        window_geometry["height"] = height

    def _on_maximized() -> None:
        if window_geometry["is_fullscreen"]:
            return
        window_geometry["mode"] = "maximized"
        window_geometry["maximized"] = True

    def _on_restored() -> None:
        if window_geometry["is_fullscreen"]:
            return
        window_geometry["mode"] = "normal"
        window_geometry["maximized"] = False

    def _on_minimized() -> None:
        if window_geometry["is_fullscreen"]:
            return
        window_geometry["mode"] = "minimized"

    window.events.moved += _on_moved
    window.events.resized += _on_resized
    window.events.maximized += _on_maximized
    window.events.restored += _on_restored
    window.events.minimized += _on_minimized

    shutdown_started = threading.Event()
    stop_watching = threading.Event()

    shutdown_done = threading.Event()

    def shutdown(*_args) -> None:
        """Zentraler Cleanup-Pfad - idempotent, damit mehrfaches Ausloesen
        (Fenster-Event + finally-Block) keine doppelte Arbeit macht. Wer ihn zum zweiten Mal
        aufruft (der Hauptthread nach dem Schliessen des Fensters), wartet, bis der erste fertig ist:
        sonst endet der Prozess mitten im Aufraeumen (Sicherung beim Beenden, Sitzungsmarkierung)."""
        if shutdown_started.is_set():
            shutdown_done.wait(timeout=20)
            return
        shutdown_started.set()
        try:
            _shutdown_work()
        finally:
            shutdown_done.set()

    def _shutdown_work() -> None:
        stop_watching.set()
        crash.dialogs_enabled = False                                    # Fehler beim Beenden: nur ins Log, kein Fenster mehr

        print("[OpenCue] Shutting down...")
        host_cameras.stop_all()          # Kameras am Hauptgeraet sofort freigeben (Kamera-LED aus), bevor irgendetwas anderes passiert

        state.save_window_geometry(
            x=window_geometry["x"],
            y=window_geometry["y"],
            width=window_geometry["width"],
            height=window_geometry["height"],
            maximized=window_geometry["maximized"],
        )
        _stop_everything(server, server_thread)

    def _on_closing() -> bool:
        # Ein Schliessen (X, Ctrl+Q, Datei > Beenden, Strg+C) wird abgebrochen und
        # stattdessen der Beenden-Dialog im Frontend gezeigt. Ohne verbundenen
        # Client gibt es niemanden, der fragen kann - dann schliessen wir direkt.
        if close_allowed.is_set():
            return True
        # Der Dialog soll SOFORT da sein, auch wenn der Server gerade beschaeftigt ist: die Seite oeffnet ihn selbst (eigener Thread, damit das Schliessen-Ereignis nicht wartet);
        # request_close_prompt() meldet es zusaetzlich an alle verbundenen Geraete (Fernzugriff, und als Rueckfall, falls die Seite nicht antwortet).
        threading.Thread(target=_open_close_dialog_in_page, args=(window,), name="close-dialog", daemon=True).start()
        return not request_close_prompt()

    # pywebview bricht das Schliessen ab, sobald ein Handler False zurueckgibt.
    window.events.closing += _on_closing
    # Feuert nach dem tatsaechlichen Schliessen (siehe _watch_exit_signal) und
    # gibt die Geometrie frei.
    window.events.closed += shutdown

    exit_watcher = threading.Thread(
        target=_watch_exit_signal, args=(window, stop_watching), daemon=True
    )
    exit_watcher.start()

    fullscreen_watcher = threading.Thread(
        target=_watch_fullscreen_toggle, args=(window, window_geometry, stop_watching), daemon=True
    )
    fullscreen_watcher.start()

    def _pick_media_file():
        """Datei-Dialog fuer 'Medium verknuepfen' (Video/Audio-Player): Pfad oder None."""
        picked = window.create_file_dialog(
            webview.OPEN_DIALOG,
            allow_multiple=False,
            file_types=("Video/Audio (*.mp4;*.m4v;*.webm;*.ogg;*.ogv;*.wav;*.mp3;*.flac;*.aac;*.m4a;*.mov)", "Alle Dateien (*.*)"),
        )
        return str(picked[0]) if picked else None

    threading.Thread(target=file_dialog.serve, args=(_pick_media_file, stop_watching), daemon=True).start()

    try:
        # Edge/Chromium-Renderer explizit, ohne GUI-API-Bindung.
        # private_mode=False + storage_path: localStorage der Konsole ueberlebt den Neustart
        # (Spaltenbreiten der Cue-Liste, GUI-Skalierung). pywebview startet sonst im
        # Privatmodus und verwirft alles beim Beenden.
        storage_dir = get_data_root() / "webview"
        storage_dir.mkdir(parents=True, exist_ok=True)
        startup_progress.report(70, "Starting display engine")
        webview.start(
            gui="edgechromium",
            private_mode=False,
            storage_path=str(storage_dir),
            icon=_window_icon(),
        )
    finally:
        splash.close(wait=0.3)
        # Sicherheitsnetz, falls "closed" aus irgendeinem Grund nicht feuert
        # (z.B. Abbruch waehrend des Fenster-Aufbaus).
        shutdown()


if __name__ == "__main__":
    crash.run(main, startup_done=ui_ready.is_set)
