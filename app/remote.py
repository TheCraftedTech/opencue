"""
remote.py
Remote-Zugriff auf OpenCue aus dem lokalen Netzwerk (z.B. Safari auf dem iPad).

* Lokale Verbindungen (Loopback, also der PyWebView-Client) brauchen kein Passwort.
* Externe Verbindungen brauchen ein Passwort (Einstellung `remote_password`) und
  bekommen danach ein Session-Cookie, das HTTP und WebSocket freischaltet.
* Jeder externe Client hat sein eigenes Panel-Layout (ClientSession), waehrend
  Show-, Cue-, Programmer- und Ausgabedaten fuer alle gemeinsam bleiben.

Der Server lauscht immer auf 127.0.0.1; fuer den Netzwerk-Zugriff kommen zur Laufzeit je Netzwerk-Adresse weitere Listener dazu und wieder weg
(app/lan_listener.py) - ohne Neustart. Die Pruefungen hier gelten zusaetzlich sofort - auch wenn `remote_enabled` zur Laufzeit geaendert wird.
"""

from __future__ import annotations

import hmac
import secrets
import socket
import time
import uuid
from contextlib import contextmanager
from dataclasses import asdict
from typing import Any, Dict, Iterator, List, Optional

from pathlib import Path

from app import paths as _paths
from app import remote_pwa
from app.state_manager import DEFAULT_SERVER_PORT, PanelUndoHistory, panels_from_dicts, state

_STATIC_DIR = _paths.project_root() / "static"
DEFAULT_PORT = DEFAULT_SERVER_PORT
SESSION_COOKIE = "oc_session"
CLIENT_COOKIE = "oc_cid"
LEGACY_REMEMBER_COOKIE = "oc_remember"   # frueheres Remember-Token: wird nicht mehr ausgewertet, nur noch vom Geraet geloescht
SESSION_TTL = 12 * 3600
CLIENT_COOKIE_TTL = 365 * 24 * 3600
MAX_FAILURES = 5
LOCK_SECONDS = 60

# Remote-Geraete sind nach dem Login vollstaendig gleichberechtigt: es gibt keine Rechte-Trennung zwischen
# Konsole und Remote. Die einzige Ausnahme ist rein physisch: "toggle_fullscreen" schaltet das FENSTER der
# Konsole um - jedes Geraet hat sein eigenes Vollbild (Browser-API im Frontend), die Nachricht wird von
# Remote-Geraeten nie gesendet.
LOCAL_ONLY_MESSAGES = {"toggle_fullscreen"}
# Server -> Client Nachrichten, die nur an Konsolen-Fenster gehen: das Layout des Hauptrechners (panels_changed;
# jedes Remote-Geraet bekommt sein eigenes) und die Abfrage des Schliessen-X.
LOCAL_ONLY_EVENTS = {"panels_changed", "close_requested"}

# Beim Start gesetzt (main.py): an welche Adresse der Server tatsaechlich gebunden ist.
bound_host = "127.0.0.1"
bound_port = DEFAULT_PORT


def is_local(host: Optional[str]) -> bool:
    if not host:
        return False
    host = host.lower()
    if host.startswith("::ffff:"):
        host = host[7:]
    return host in ("127.0.0.1", "::1", "localhost") or host.startswith("127.")


def lan_addresses() -> List[str]:
    """IPv4-Adressen der Konsole im lokalen Netzwerk (beste Adresse zuerst)."""
    found: List[str] = []
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("10.255.255.255", 1))  # kein Paket wird gesendet
            found.append(sock.getsockname()[0])
    except OSError:
        pass
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            found.append(info[4][0])
    except OSError:
        pass
    result: List[str] = []
    for ip in found:
        if ip.startswith("127.") or ip.startswith("169.254.") or ip == "0.0.0.0":
            continue
        if ip not in result:
            result.append(ip)
    return result


def qr_svg(text: str) -> str:
    """QR-Code als SVG-Text (weisser Grund, schwarze Module, skalierbar; offline erzeugt mit segno)."""
    import io
    import segno
    buf = io.BytesIO()
    segno.make(text, error="m").save(buf, kind="svg", border=2, scale=1, xmldecl=False, svgns=True, nl=False, omitsize=True, light="#ffffff", dark="#000000")
    return buf.getvalue().decode("utf-8")


def remote_info(include_password: bool) -> Dict[str, Any]:
    """Zustand der Remote-Einstellungen fuer das Settings-Panel."""
    from app.lan_listener import lan
    active = lan.addresses                                   # Adressen, auf denen die Konsole gerade wirklich im Netzwerk lauscht
    candidates = [ip for ip in lan_addresses() if ip not in active]
    urls = [f"http://{ip}:{bound_port}" for ip in active]
    info: Dict[str, Any] = {
        "enabled": state.remote_enabled,
        "port": bound_port,                       # Port, auf dem der Server gerade laeuft
        "configured_port": state.server_port,     # gespeicherter Port (gilt nach dem Neustart)
        "local_url": f"http://127.0.0.1:{bound_port}",
        "urls": urls,                             # unter diesen Adressen ist die Konsole JETZT im Netzwerk erreichbar
        "candidate_urls": [f"http://{ip}:{bound_port}" for ip in candidates],   # erkannte Adressen, auf denen sie (noch) nicht lauscht
        "qr": {url: qr_svg(url) for url in urls},
        "listen_errors": dict(lan.errors),        # Adresse -> Fehlertext (z. B. Port belegt)
        "listening_on_network": bool(active),
        # Netzwerk-Zugriff ein-/ausschalten wirkt sofort; nur ein geaenderter Port braucht einen Neustart.
        "restart_required": state.server_port != bound_port,
    }
    if include_password:
        info["password"] = state.remote_password
    return info


def device_label(user_agent: str) -> str:
    """Kurze Geraetebezeichnung aus dem User-Agent (nur zur Anzeige in der Client-Liste)."""
    ua = (user_agent or "").lower()
    for needle, label in (("ipad", "iPad"), ("iphone", "iPhone"), ("android", "Android"),
                          ("windows", "Windows"), ("macintosh", "Mac"), ("linux", "Linux")):
        if needle in ua:
            return label
    return "?"


# ---- Passwort-Pruefung und Sessions -----------------------------------------------

_tokens: Dict[str, Dict[str, Any]] = {}
_failures: Dict[str, Dict[str, float]] = {}


def create_session(cid: str) -> str:
    """Neues Sitzungs-Token fuer ein Geraet (cid)."""
    token = secrets.token_urlsafe(32)
    _tokens[token] = {"cid": cid, "expires": time.time() + SESSION_TTL}
    return token


def login(ip: str, password: str, cid: Optional[str]) -> Dict[str, Any]:
    """Prueft das Passwort. Liefert {"ok": True, "token", "cid"} oder {"ok": False, "locked": s}."""
    now = time.monotonic()
    record = _failures.get(ip)
    if record and record.get("locked_until", 0) > now:
        return {"ok": False, "locked": int(record["locked_until"] - now) + 1}
    expected = state.remote_password.encode("utf-8")
    if state.remote_enabled and hmac.compare_digest(str(password).encode("utf-8"), expected):
        _failures.pop(ip, None)
        cid = cid if cid and len(cid) == 36 else str(uuid.uuid4())
        return {"ok": True, "token": create_session(cid), "cid": cid}
    record = _failures.setdefault(ip, {"count": 0, "locked_until": 0})
    record["count"] += 1
    if record["count"] >= MAX_FAILURES:
        record["count"] = 0
        record["locked_until"] = now + LOCK_SECONDS
        return {"ok": False, "locked": LOCK_SECONDS}
    return {"ok": False, "locked": 0}


def validate(token: Optional[str]) -> Optional[str]:
    """Gibt die Client-ID (cid) zurueck, wenn das Token gueltig ist, sonst None."""
    if not token:
        return None
    entry = _tokens.get(token)
    if entry is None:
        return None
    if entry["expires"] < time.time():
        _tokens.pop(token, None)
        return None
    return entry["cid"]


def logout(token: Optional[str]) -> None:
    """Meldet ein Geraet ab: die Sitzung wird ungueltig."""
    if token:
        _tokens.pop(token, None)


def revoke_all() -> None:
    """Alle Sitzungen verlieren die Gueltigkeit (Passwort geaendert, Remote aus)."""
    _tokens.clear()


# ---- Eigenes Layout je externem Client --------------------------------------------

class ClientSession:
    """Panel-Layout und Undo-Verlauf eines externen Clients (nur im Arbeitsspeicher)."""

    def __init__(self) -> None:
        self.panels = clone_host_panels()
        self.undo = PanelUndoHistory()
        # Zuletzt geladenes/gespeichertes Layout dieses Clients: {"filename", "name"} oder None
        # (nur zur Anzeige im Snapshot; die Wahrheit ueber das Layout steht in der Layout-Datei).
        self.layout: Optional[Dict[str, Any]] = None
        # Panel-Stand (ohne ui_state) beim Laden/Speichern dieses Layouts: Abweichung = ungespeicherte Aenderungen.
        self.baseline: Optional[List[Dict[str, Any]]] = None

    def panels_as_dicts(self) -> List[Dict[str, Any]]:
        return [asdict(p) for p in self.panels]


sessions: Dict[str, ClientSession] = {}


def clone_host_panels() -> list:
    """Kopie des Host-Layouts mit neuen Panel-IDs - der Client startet mit derselben
    Anordnung, aendert sie aber unabhaengig vom Host und von anderen Clients."""
    items = []
    for item in state.panels_as_dicts():
        item = dict(item)
        item["id"] = str(uuid.uuid4())
        items.append(item)
    return panels_from_dicts(items)


def session_for(cid: str) -> ClientSession:
    sess = sessions.get(cid)
    if sess is None:
        sess = sessions[cid] = ClientSession()
    return sess


@contextmanager
def panel_scope(sess: ClientSession) -> Iterator[None]:
    """Fuehrt die Panel-Methoden des StateManagers auf dem Layout des Clients aus, ohne
    das Host-Layout oder die Host-Konfiguration zu beruehren. Rein synchron benutzen."""
    saved = state.panels
    state.panels = sess.panels
    state._panel_scope_active = True
    try:
        yield
    finally:
        sess.panels = state.panels
        state.panels = saved
        state._panel_scope_active = False


def apply_panel_message(sess: ClientSession, message_type: str, payload: Dict[str, Any]) -> bool:
    """Panel-Bearbeitung eines externen Clients inkl. Undo/Redo. True, wenn sich etwas aenderte."""
    with panel_scope(sess):
        if message_type in ("undo", "redo"):
            current = state.panels_as_dicts()
            previous = sess.undo.undo(current) if message_type == "undo" else sess.undo.redo(current)
            if previous is None:
                return False
            state.panels = panels_from_dicts(previous)
            return True
        before = state.panels_as_dicts()
        panel_id = payload.get("id")
        if message_type == "add_panel" and payload.get("panel_type"):
            state.add_panel(payload["panel_type"])
        elif message_type == "update_panel" and panel_id:
            state.update_panel(panel_id, **{k: v for k, v in payload.items() if k != "id"})
        elif message_type == "delete_panel" and panel_id:
            state.delete_panel(panel_id)
        elif message_type == "duplicate_panels":
            state.duplicate_panels(payload.get("ids"))
        elif message_type == "paste_panels":
            state.paste_panels(payload.get("panels"))
        elif message_type == "delete_panels":
            state.delete_panels(payload.get("ids"))
        elif message_type == "clear_panels":
            state.panels = []
        elif message_type == "bring_panel_to_front" and panel_id:
            state.bring_panel_to_front(panel_id)
        elif message_type == "send_panel_to_back" and panel_id:
            state.send_panel_to_back(panel_id)
        elif message_type == "move_panel_layer" and panel_id:
            state.move_panel_layer(panel_id, payload.get("delta", 0))
        changed = before != state.panels_as_dicts()
        if changed:
            sess.undo.record(before)
        return changed


def apply_panels_ui(sess: ClientSession, panels_ui: Any) -> None:
    if isinstance(panels_ui, dict):
        with panel_scope(sess):
            for panel_id, ui_state in panels_ui.items():
                state.set_panel_ui_state(panel_id, ui_state)


# ---- Login-Seite -------------------------------------------------------------------

_LOGIN_TEXT = {
    "de": ("Anmelden", "Passwort", "Anmelden", "Falsches Passwort.", "Zu viele Versuche. Bitte {s} s warten.",
           "Remote-Zugriff ist deaktiviert.", "Passwort speichern"),
    "en": ("Sign in", "Password", "Sign in", "Wrong password.", "Too many attempts. Wait {s} s.",
           "Remote access is disabled.", "Save password"),
}


def _login_theme_css() -> str:
    """theme.css im Wortlaut: Die Login-Seite ist ausgeloggt, /static/ ist fuer sie gesperrt."""
    try:
        return (_STATIC_DIR / "css" / "theme.css").read_text(encoding="utf-8")
    except OSError:
        return ""


def _login_theme_vars() -> str:
    """Inline-Variablen des aktiven Themes (wie applyTheme in app.js): Tokens, Rundungsgrad, Akzent-Schrift."""
    theme = state.theme_payload()
    radius = int(theme["radius"])
    values = {f"--{name}": value for name, value in theme["tokens"].items()}
    values["--radius-md"] = f"{radius}px"
    values["--radius-sm"] = f"{round(radius * 4 / 7)}px"
    values["--radius-lg"] = f"{round(radius * 12 / 7)}px"
    accent = theme["tokens"].get("accent")
    if not accent:
        accent = "#a35f00" if theme["base"] == "light" else "#ffb000"
    values["--accent-ink"] = _accent_ink(accent)
    return "; ".join(f"{key}: {value}" for key, value in values.items())


def _accent_ink(hex_color: str) -> str:
    """Schriftfarbe auf der Akzentflaeche - dieselbe Formel wie accentInk() in app.js."""
    try:
        channels = [int(hex_color.lstrip("#")[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    except ValueError:
        return "#1a1200"
    r, g, b = (c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels)
    return "#14110a" if 0.2126 * r + 0.7152 * g + 0.0722 * b > 0.35 else "#ffffff"


def login_page() -> str:
    title, label, button, wrong, locked, disabled, remember = _LOGIN_TEXT.get(state.language, _LOGIN_TEXT["en"])
    base = state.theme["base"]
    return f"""<!doctype html>
<html lang="{state.language}" data-theme="{base}" style="{_login_theme_vars()}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no, viewport-fit=cover">
<meta name="color-scheme" content="{base}">
{remote_pwa.head_tags()}<title>OpenCue</title>
<style>
{_login_theme_css()}
</style>
<style>
  html, body {{ margin: 0; min-height: 100%; background: var(--bg); color: var(--text-1);
    font-family: var(--font-ui); font-size: 16px; }}
  body {{ min-height: 100dvh; display: flex; align-items: center; justify-content: center;
    padding: max(var(--sp-4), env(safe-area-inset-top)) max(var(--sp-4), env(safe-area-inset-right))
             max(var(--sp-4), env(safe-area-inset-bottom)) max(var(--sp-4), env(safe-area-inset-left));
    box-sizing: border-box; }}
  form {{ width: min(100%, 24rem); display: flex; flex-direction: column; gap: var(--sp-4);
    padding: var(--sp-6); background: var(--surface-1); border: 1px solid var(--border);
    border-radius: var(--radius-lg); }}
  h1 {{ margin: 0; font-size: var(--fs-xl); font-weight: 600; line-height: 1.2; }}
  label {{ font-size: var(--fs-md); color: var(--text-2); }}
  input, button {{ font: inherit; font-size: 1rem; min-height: 3rem; box-sizing: border-box;
    border-radius: var(--radius-sm); border: 1px solid var(--border); padding: 0 var(--sp-4); }}
  input {{ background: var(--surface-2); color: var(--text-1); }}
  input:focus-visible {{ outline: 2px solid var(--accent); outline-offset: 1px; border-color: var(--accent); }}
  button {{ background: var(--accent); border-color: var(--accent); color: var(--accent-ink);
    font-weight: 600; cursor: pointer; }}
  button:focus-visible {{ outline: 2px solid var(--text-1); outline-offset: 2px; }}
  button:active {{ filter: brightness(.92); }}
  .remember {{ display: flex; align-items: center; gap: var(--sp-3); min-height: 2.75rem; color: var(--text-1); cursor: pointer; }}
  .remember input {{ min-height: 0; width: 1.4rem; height: 1.4rem; padding: 0; accent-color: var(--accent); flex: none; }}
  #msg {{ min-height: 1.3em; font-size: var(--fs-md); color: var(--error); }}
  @media (min-width: 700px) {{ form {{ width: 28rem; }} html, body {{ font-size: 18px; }} }}   /* Tablet: groesser */
</style></head><body>
<form id="f" autocomplete="off">
  <h1>OpenCue · {title}</h1>
  <label for="p">{label}</label>
  <input id="p" type="password" autofocus autocapitalize="off" autocorrect="off" autocomplete="off">
  <label class="remember"><input id="rem" type="checkbox"><span>{remember}</span></label>
  <div id="msg"></div>
  <button type="submit">{button}</button>
</form>
<script>
  {remote_pwa.REGISTER_SCRIPT}
  const T = {{wrong: {wrong!r}, locked: {locked!r}, disabled: {disabled!r}}};
  // "Passwort speichern": das Passwort liegt nur im Browser-Speicher DIESES Geraets (localStorage) und dient ausschliesslich
  // dazu, das Feld vorauszufuellen - es geht nie in einem Cookie mit und es gibt keine automatische Anmeldung.
  const KEY = "opencue.rememberedPassword";
  const store = {{
    get() {{ try {{ return localStorage.getItem(KEY); }} catch (err) {{ return null; }} }},
    set(v) {{ try {{ localStorage.setItem(KEY, v); }} catch (err) {{ /* privat */ }} }},
    clear() {{ try {{ localStorage.removeItem(KEY); }} catch (err) {{ /* privat */ }} }},
  }};
  const pw = document.getElementById("p");
  const rem = document.getElementById("rem");
  const saved = store.get();
  if (saved) {{ pw.value = saved; rem.checked = true; }}
  rem.addEventListener("change", () => {{ if (!rem.checked) store.clear(); }});   // Haken weg: sofort vom Geraet loeschen
  document.getElementById("f").addEventListener("submit", async (e) => {{
    e.preventDefault();
    const msg = document.getElementById("msg");
    msg.textContent = "";
    try {{
      const res = await fetch("/auth/login", {{method: "POST", headers: {{"Content-Type": "application/json"}},
        body: JSON.stringify({{password: pw.value}})}});
      const data = await res.json();
      if (data.ok) {{
        if (rem.checked) store.set(pw.value); else store.clear();   // nur nach erfolgreichem Login merken
        location.reload();
        return;
      }}
      msg.textContent = data.locked ? T.locked.replace("{{s}}", data.locked)
                      : res.status === 403 ? T.disabled : T.wrong;
    }} catch (err) {{ msg.textContent = String(err); }}
  }});
</script></body></html>"""
