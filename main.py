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

Version und Programm-Metadaten stehen an EINER Stelle: app/version.py (APP_VERSION = "1.0.0", Anzeige "v1.0.0"). `python main.py --version` gibt sie aus.


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


def _prepare_frozen_streams() -> None:
    """PyInstaller-Build ohne Konsole (--windowed): sys.stdout/sys.stderr sind None, uvicorns Logging ruft aber isatty() darauf auf und bricht ab. Deshalb gehen beide in
    eine Protokolldatei (%LOCALAPPDATA%\\OpenCue\\logs\\opencue.log, bei jedem Start neu; ab 2 MB wird die alte als opencue.log.1 behalten). Im Quelltext-Betrieb passiert nichts."""
    if not getattr(sys, "frozen", False) or (sys.stdout is not None and sys.stderr is not None):
        return
    base = os.environ.get("LOCALAPPDATA", "")
    folder = os.path.join(base if base else os.path.expanduser("~"), "OpenCue" if base else ".opencue", "logs")
    try:
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, "opencue.log")
        if os.path.isfile(path) and os.path.getsize(path) > 2 * 1024 * 1024:
            os.replace(path, path + ".1")
        stream = open(path, "w", buffering=1, encoding="utf-8", errors="replace")
    except OSError:
        stream = open(os.devnull, "w", encoding="utf-8")
    if sys.stdout is None:
        sys.stdout = stream
    if sys.stderr is None:
        sys.stderr = stream


_prepare_frozen_streams()                       # vor allen Importen, die Logging einrichten (uvicorn, app.server)

from app.version import APP_NAME, APP_VERSION_LABEL, WEBVIEW2_URL  # noqa: E402  (leicht: nur Konstanten)

if "--version" in sys.argv[1:]:
    print(f"{APP_NAME} {APP_VERSION_LABEL}")
    sys.exit(0)

# Medien-Player: Video/Audio sollen auch ohne vorherigen Klick starten koennen (Timecode-gesteuerte Wiedergabe an der Konsole).
# Muss gesetzt sein, bevor WebView2 startet.
os.environ.setdefault("WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS", "--autoplay-policy=no-user-gesture-required")

import uvicorn
import webview

from app import host_cameras, remote
from app.paths import get_data_root, project_root
from app.dmx_engine import dmx_engine
from app.lan_listener import lan
from app.server import app, request_close_prompt
from app.state_manager import state
from app.window_signals import close_allowed, exit_requested, file_dialog, fullscreen_toggle_requested

HOST = "127.0.0.1"  # Adresse, unter der der lokale PyWebView-Client den Server erreicht
PORT = state.server_port   # Einstellung 'server_port'; Aenderungen gelten ab dem naechsten Start
# Der Server lauscht immer nur lokal; der Netzwerk-Zugriff (Remote) haengt zur Laufzeit je Netzwerk-Adresse weitere Listener dazu und wieder ab
# (app/lan_listener.py) - ein-/ausschalten in den Einstellungen wirkt sofort, ohne Neustart. Nur ein geaenderter Port gilt ab dem naechsten Start.
BIND_HOST = "127.0.0.1"
remote.bound_host = BIND_HOST
remote.bound_port = PORT
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


def _start_server() -> tuple[uvicorn.Server, threading.Thread]:
    """Startet Uvicorn in einem Hintergrund-Thread und gibt Server + Thread zurueck.

    Die Server-Instanz wird bewusst nicht gekapselt: main() braucht sie, um
    per `should_exit` einen sauberen Shutdown auszuloesen und den Thread
    danach zu joinen, statt sich auf das Daemon-Flag allein zu verlassen.
    """
    config = uvicorn.Config(app, host=BIND_HOST, port=PORT, log_level="info")
    server = uvicorn.Server(config)
    lan.attach(server)                                   # Netzwerk-Listener (Remote) richtet der Lifespan-Start ein, sobald der Server laeuft
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    return server, thread


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
    """Ohne WebView2 oeffnet sich kein Fenster. Statt eines stillen Abbruchs eine verstaendliche Meldung (Windows 10 ohne Edge-Laufzeit): Ja = Download-Seite oeffnen und beenden,
    Nein = trotzdem versuchen zu starten (falls die Erkennung irrt). True = weiter."""
    if _webview2_installed():
        return True
    try:
        import ctypes
        text = ("OpenCue needs the Microsoft Edge WebView2 Runtime to show its window, but it was not found on this computer.\n\n"
                "Yes: open the download page and close OpenCue.\nNo: try to start anyway.\n\n" + WEBVIEW2_URL)
        answer = ctypes.windll.user32.MessageBoxW(0, text, APP_NAME, 0x04 | 0x30)         # MB_YESNO | MB_ICONWARNING
    except Exception:
        return True
    if answer == 6:                                                                        # IDYES
        webbrowser.open(WEBVIEW2_URL)
        return False
    return True


def _window_icon() -> str | None:
    """Pfad der .ico fuer die Fensterleiste (Build: OpenCue.ico im Programmordner; Quelltext: packaging/OpenCue.ico). Ohne Datei nimmt pywebview das Icon der .exe."""
    root = project_root()
    for candidate in (root / "OpenCue.ico", root / "packaging" / "OpenCue.ico"):
        if candidate.is_file():
            return str(candidate)
    return None


def main() -> None:
    _set_app_user_model_id()
    if not _ensure_webview2():
        return
    print(f"[{APP_NAME}] {APP_VERSION_LABEL} starting ...")
    server, server_thread = _start_server()
    _wait_for_server()

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
    window = webview.create_window(
        "OpenCue",
        url=f"http://{HOST}:{PORT}",
        resizable=True,
        min_size=MIN_WINDOW_SIZE,
        confirm_close=False,
        **initial_geometry,
    )

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

    def shutdown(*_args) -> None:
        """Zentraler Cleanup-Pfad - idempotent, damit mehrfaches Ausloesen
        (Fenster-Event + finally-Block) keine doppelte Arbeit macht."""
        if shutdown_started.is_set():
            return
        shutdown_started.set()
        stop_watching.set()

        print("[OpenCue] Shutting down...")
        host_cameras.stop_all()          # Kameras am Hauptgeraet sofort freigeben (Kamera-LED aus), bevor irgendetwas anderes passiert

        state.save_window_geometry(
            x=window_geometry["x"],
            y=window_geometry["y"],
            width=window_geometry["width"],
            height=window_geometry["height"],
            maximized=window_geometry["maximized"],
        )
        dmx_engine.shutdown()

        server.should_exit = True
        server_thread.join(timeout=5)

        print("[OpenCue] Shutdown complete.")
        try:
            from app import updater
            if updater.launch_pending_installer():              # Update vorgemerkt ("Jetzt installieren"): das Setup startet erst jetzt, nach dem Beenden
                print("[OpenCue] Update-Setup gestartet.")
        except Exception as exc:
            print(f"[OpenCue] Update-Setup konnte nicht gestartet werden: {exc}")

    def _on_closing() -> bool:
        # Ein Schliessen (X, Ctrl+Q, Datei > Beenden, Strg+C) wird abgebrochen und
        # stattdessen der Beenden-Dialog im Frontend gezeigt. Ohne verbundenen
        # Client gibt es niemanden, der fragen kann - dann schliessen wir direkt.
        if close_allowed.is_set():
            return True
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
        webview.start(
            gui="edgechromium",
            private_mode=False,
            storage_path=str(storage_dir),
            icon=_window_icon(),
        )
    finally:
        # Sicherheitsnetz, falls "closed" aus irgendeinem Grund nicht feuert
        # (z.B. Abbruch waehrend des Fenster-Aufbaus).
        shutdown()


if __name__ == "__main__":
    main()
