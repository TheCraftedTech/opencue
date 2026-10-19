"""
window_signals.py
Duenne Kopplung zwischen Frontend-Requests, die das native pywebview-Fenster
selbst betreffen (schliessen, Fullscreen umschalten, ...), und main.py.

Das pywebview-Fenster ist laut "Dummy-Container-Prinzip" ein rein passiver
UI-Container: es bekommt kein `js_api`-Objekt und wird nie per `evaluate_js`
angesprochen (das war frueher die Fehlerquelle fuer
"CoreWebView2 members can only be accessed from the UI thread" bzw.
Rekursionsfehler in der JS-Bridge). Jeder Request, der das Fenster selbst
betrifft (File -> Exit, F11-Fullscreen), laeuft deshalb wie jede andere
Kommunikation ganz normal ueber den WebSocket-Kanal zum Server
(app/server.py) und landet hier nur als threading.Event.

main.py haelt kleine Watcher-Threads, die bei gesetztem Event auf das
pywebview-Fenster einwirken (window.destroy() / window.toggle_fullscreen()
marshalen intern sicher auf den UI-Thread). So braucht server.py selbst
keinerlei Abhaengigkeit von pywebview und bleibt eigenstaendig lauffaehig/
testbar (z.B. per `uvicorn app.server:app`).
"""

import threading

exit_requested = threading.Event()
fullscreen_toggle_requested = threading.Event()
# Gesetzt, sobald der Nutzer im Beenden-Dialog entschieden hat - der native
# closing-Handler laesst das Schliessen dann durch, statt erneut zu fragen.
close_allowed = threading.Event()


class FileDialogBridge:
    """Datei-Auswahldialog des nativen Fensters fuer den Server (gleiches Prinzip wie die Events oben: der Server kennt pywebview
    nicht). main.py meldet mit serve() einen Dienst an; der Server ruft request() und wartet auf den gewaehlten Pfad. Ohne
    Dienst (reiner Browser-Betrieb, Tests) ist available False."""

    def __init__(self) -> None:
        self.available = False
        self._requested = threading.Event()
        self._done = threading.Event()
        self._lock = threading.Lock()
        self._result = None

    def request(self, timeout: float = 300.0):
        """Oeffnet den Dialog und wartet auf die Auswahl. Rueckgabe: Pfad oder None (abgebrochen / nicht verfuegbar)."""
        if not self.available:
            return None
        with self._lock:                        # immer nur ein Dialog zur Zeit
            self._result = None
            self._done.clear()
            self._requested.set()
            self._done.wait(timeout)
            return self._result

    def serve(self, picker, stop: threading.Event) -> None:
        """Laeuft in einem Daemon-Thread von main.py: wartet auf Anfragen und ruft picker() -> Pfad oder None."""
        self.available = True
        try:
            while not stop.is_set():
                if self._requested.wait(timeout=0.25):
                    self._requested.clear()
                    try:
                        self._result = picker()
                    except Exception:
                        self._result = None
                    self._done.set()
        finally:
            self.available = False


file_dialog = FileDialogBridge()
