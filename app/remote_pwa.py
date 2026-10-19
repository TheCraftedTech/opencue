"""
remote_pwa.py
PWA-Huelle der Remote-Control: Manifest, Service Worker, Offline-Seite, Icons und die Head-Tags fuer iPad/Safari.

Alles liegt unter /remote/ - der Service Worker hat genau diesen Scope und deckt die Hauptoberflaeche der
Konsole (/) nie ab. Live-Daten (WebSocket, /api/*, /auth/*) gehen NIE ueber den Cache: der Service Worker
fasst nur /static/ und die Icons an (immer zuerst das Netz) und liefert bei einem nicht erreichbaren Server
die Offline-Seite.

Hinweis: Service Worker und Manifest-Installation brauchen einen sicheren Kontext (HTTPS oder localhost).
Ueber http://<IP> im LAN gibt es keinen Service Worker - "Zum Home-Bildschirm" (Vollbild-App) funktioniert
in Safari trotzdem, nur die Offline-Seite fehlt dann.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Dict, Optional

from app import paths as _paths
from app.state_manager import state

BASE_DIR = _paths.project_root()          # mitgelieferte Dateien; im PyInstaller-Build sys._MEIPASS
STATIC_DIR = BASE_DIR / "static"
ICON_DIR = STATIC_DIR / "icons"
REMOTE_SCOPE = "/remote/"
ICON_FILES = {
    "icon-192.png": "image/png",
    "icon-512.png": "image/png",
    "icon-maskable-512.png": "image/png",       # Logo mit Rand in der sicheren Zone (maskierte Symbole, z. B. Android)
    "apple-touch-icon.png": "image/png",        # 180 x 180 fuer iOS
    "logo.svg": "image/svg+xml",
    "logo-64.png": "image/png",
}

# Pfade, die ohne Anmeldung ausgeliefert werden (nur die Huelle, keine Show-Daten).
PUBLIC_PATHS = {
    "/remote/manifest.webmanifest", "/remote/sw.js", "/remote/offline.html", "/remote/ping", "/favicon.ico",
}
PUBLIC_PREFIXES = ("/remote/icons/",)


def is_public(path: str) -> bool:
    return path in PUBLIC_PATHS or path.startswith(PUBLIC_PREFIXES)


# ---- Theme-Farben (aus den Tokens, nicht hart kodiert) ---------------------------------

_BLOCK_RE = {
    "dark": re.compile(r"^:root\s*\{(.*?)^\}", re.S | re.M),
    "light": re.compile(r'^:root\[data-theme="light"\]\s*\{(.*?)^\}', re.S | re.M),
}
_TOKEN_RE = re.compile(r"--([a-z0-9-]+)\s*:\s*([^;]+);")
_palette_cache: Dict[str, Dict[str, str]] = {}


def _base_palette(base: str) -> Dict[str, str]:
    """Token-Werte der Basis-Palette, direkt aus theme.css gelesen (eine Quelle)."""
    cached = _palette_cache.get(base)
    if cached is not None:
        return cached
    palette: Dict[str, str] = {}
    try:
        css = (STATIC_DIR / "css" / "theme.css").read_text(encoding="utf-8")
        match = _BLOCK_RE[base].search(css)
        if match:
            for name, value in _TOKEN_RE.findall(match.group(1)):
                palette[name] = value.strip()
    except OSError:
        pass
    _palette_cache[base] = palette
    return palette


def resolved_tokens() -> Dict[str, str]:
    """Aktuelle Token-Farben (#rrggbb): Basis-Palette + Abweichungen des Nutzer-Themes, Aliase aufgeloest."""
    base = state.theme["base"]
    values = dict(_base_palette("dark"))
    if base == "light":
        values.update(_base_palette("light"))
    values.update(state.theme["tokens"])

    def resolve(name: str, depth: int = 0) -> Optional[str]:
        value = values.get(name)
        if value is None or depth > 4:
            return None
        match = re.fullmatch(r"var\(--([a-z0-9-]+)\)", value)
        if match:
            return resolve(match.group(1), depth + 1)
        return value if re.fullmatch(r"#[0-9a-fA-F]{6}", value) else None

    return {name: color for name in values if (color := resolve(name))}


def theme_color() -> str:
    """Farbe der Statusleiste/Titelleiste der installierten App: wie die Toolbar."""
    tokens = resolved_tokens()
    return tokens.get("toolbar-bg") or tokens.get("surface-1") or "#151517"


def background_color() -> str:
    return resolved_tokens().get("bg") or "#0a0a0b"


# ---- Manifest ---------------------------------------------------------------------------

def manifest() -> Dict[str, object]:
    """Web App Manifest. Die Farben kommen bei jedem Abruf aus dem aktuellen Theme; ein bereits installiertes
    Symbol uebernimmt Aenderungen aber erst, wenn der Browser das Manifest neu prueft (Chrome: gelegentlich,
    iOS: erst nach erneutem Hinzufuegen zum Home-Bildschirm)."""
    return {
        "name": "OpenCue",
        "short_name": "OpenCue",
        "description": "OpenCue Remote Control",
        "id": REMOTE_SCOPE,
        "start_url": REMOTE_SCOPE,
        "scope": REMOTE_SCOPE,
        "display": "standalone",
        "orientation": "any",
        "background_color": background_color(),
        "theme_color": theme_color(),
        "icons": [
            {"src": "/remote/icons/logo.svg", "sizes": "any", "type": "image/svg+xml", "purpose": "any"},
            {"src": "/remote/icons/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any"},
            {"src": "/remote/icons/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any"},
            {"src": "/remote/icons/icon-maskable-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
            {"src": "/remote/icons/apple-touch-icon.png", "sizes": "180x180", "type": "image/png", "purpose": "any"},
        ],
    }


# ---- Head-Tags (Login-Seite und Remote-Hauptseite) ----------------------------------------

def head_tags() -> str:
    """Manifest, Theme-Farbe und die iPad/Safari-Tags: 'Zum Home-Bildschirm' startet eine eigenstaendige App."""
    # Dunkles Thema: schwarze Statusleiste ueber dem Inhalt; helles Thema: helle Leiste mit dunkler Schrift.
    status_bar = "default" if state.theme["base"] == "light" else "black"
    return (
        '<link rel="manifest" href="/remote/manifest.webmanifest">\n'
        f'<meta name="theme-color" content="{theme_color()}">\n'
        '<meta name="apple-mobile-web-app-capable" content="yes">\n'
        '<meta name="mobile-web-app-capable" content="yes">\n'
        '<meta name="apple-mobile-web-app-title" content="OpenCue">\n'
        f'<meta name="apple-mobile-web-app-status-bar-style" content="{status_bar}">\n'
        '<link rel="apple-touch-icon" href="/remote/icons/apple-touch-icon.png">\n'
        '<link rel="icon" type="image/svg+xml" href="/remote/icons/logo.svg">\n'
        '<link rel="icon" type="image/png" sizes="192x192" href="/remote/icons/icon-192.png">\n'
    )


REGISTER_SCRIPT = (
    'if ("serviceWorker" in navigator && location.pathname.indexOf("/remote/") === 0) {'
    'navigator.serviceWorker.register("/remote/sw.js", {scope: "/remote/"}).catch(function () {});}'
)


# ---- Service Worker -----------------------------------------------------------------------

_build_cache: Optional[str] = None


def build_id() -> str:
    """Kennwert des aktuellen Standes der Oberflaeche (Dateinamen, Groessen, Aenderungszeiten). Er steckt im
    Cache-Namen des Service Workers: ein neuer Stand = neuer Cache, alte Caches werden beim Aktivieren geloescht."""
    global _build_cache
    if _build_cache is None:
        digest = hashlib.sha1()
        files = [p for p in sorted(STATIC_DIR.rglob("*")) if p.is_file()]
        files.append(BASE_DIR / "templates" / "index.html")
        for path in files:
            try:
                stat = path.stat()
            except OSError:
                continue
            digest.update(f"{path.relative_to(BASE_DIR)}:{stat.st_size}:{int(stat.st_mtime)}".encode())
        digest.update(SERVICE_WORKER.encode())
        _build_cache = digest.hexdigest()[:12]
    return _build_cache


SERVICE_WORKER = r"""
/* OpenCue Remote - Service Worker (Scope /remote/).
 * Fasst nur /static/ und die Icons an, und zwar immer zuerst ueber das Netz (der Cache ist nur der Notnagel).
 * Live-Daten - WebSocket, /api/*, /auth/*, Seiten mit Zustand - laufen nie ueber den Cache. */
const BUILD = "__BUILD__";
const CACHE = "opencue-remote-" + BUILD;
const PRECACHE = [
  "/remote/offline.html",
  "/remote/icons/icon-192.png",
  "/remote/icons/icon-512.png",
  "/remote/icons/apple-touch-icon.png",
];
const NETWORK_WAIT_MS = 3000;   // so lange wartet eine zwischengespeicherte Datei auf das Netz

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE).then((cache) => cache.addAll(PRECACHE)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k.indexOf("opencue-remote-") === 0 && k !== CACHE)
                                      .map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

function cacheable(url) {
  return url.pathname.indexOf("/static/") === 0 || url.pathname.indexOf("/remote/icons/") === 0;
}

function networkFirst(request) {
  return caches.open(CACHE).then((cache) => {
    const network = fetch(request).then((response) => {
      if (response && response.ok && response.type === "basic") cache.put(request, response.clone());
      return response;
    });
    return cache.match(request).then((cached) => {
      if (!cached) return network;
      // Es gibt eine Kopie: bei langsamem oder fehlendem Netz diese nehmen, sonst die frische Antwort.
      const timeout = new Promise((resolve) => setTimeout(() => resolve(cached), NETWORK_WAIT_MS));
      return Promise.race([network.catch(() => cached), timeout]);
    });
  });
}

self.addEventListener("fetch", (event) => {
  const request = event.request;
  if (request.method !== "GET") return;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;
  if (request.mode === "navigate") {
    // Seiten kommen immer live vom Server; ist er nicht erreichbar, erscheint die Offline-Seite.
    event.respondWith(fetch(request).catch(() => caches.match("/remote/offline.html")));
    return;
  }
  if (cacheable(url)) {
    event.respondWith(networkFirst(request).catch(() => Response.error()));
  }
  // alles andere (API, Auth, Ping, ...): nicht anfassen -> direkt ins Netz
});
"""


def service_worker() -> str:
    return SERVICE_WORKER.replace("__BUILD__", build_id())


# ---- Offline-Seite ------------------------------------------------------------------------

def offline_page() -> str:
    tokens = resolved_tokens()
    colors = {
        "bg": tokens.get("bg", "#0a0a0b"),
        "surface": tokens.get("surface-1", "#151517"),
        "border": tokens.get("border", "#323237"),
        "text": tokens.get("text-1", "#ededf0"),
        "muted": tokens.get("text-2", "#a2a2aa"),
        "accent": tokens.get("accent", "#ffb000"),
    }
    base = state.theme["base"]
    return f"""<!doctype html>
<html lang="{state.language}" data-theme="{base}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="color-scheme" content="{base}">
<title>OpenCue</title>
<style>
  html, body {{ margin: 0; height: 100%; background: {colors['bg']}; color: {colors['text']};
    font-family: -apple-system, "Segoe UI", system-ui, sans-serif; }}
  body {{ display: flex; align-items: center; justify-content: center; padding: 16px; box-sizing: border-box; }}
  main {{ max-width: 26rem; width: 100%; text-align: center; padding: 28px 24px; background: {colors['surface']};
    border: 1px solid {colors['border']}; }}
  h1 {{ margin: 0 0 8px; font-size: 1.4rem; }}
  p {{ margin: 0; color: {colors['muted']}; line-height: 1.5; }}
  .spin {{ width: 28px; height: 28px; margin: 0 auto 16px; border: 3px solid {colors['border']};
    border-top-color: {colors['accent']}; border-radius: 50%; animation: s 1s linear infinite; }}
  @keyframes s {{ to {{ transform: rotate(360deg); }} }}
  @media (prefers-reduced-motion: reduce) {{ .spin {{ animation: none; }} }}
</style></head><body>
<main role="status" aria-live="polite">
  <div class="spin"></div>
  <h1 id="t">OpenCue</h1>
  <p id="m"></p>
</main>
<script>
  var de = (navigator.language || "{state.language}").toLowerCase().indexOf("de") === 0;
  document.getElementById("t").textContent = de ? "Keine Verbindung zu OpenCue" : "No connection to OpenCue";
  document.getElementById("m").textContent = de ? "Es wird automatisch erneut versucht." : "Retrying automatically.";
  // Sobald der Server wieder antwortet, zurueck zur Remote-Seite.
  function check() {{
    fetch("/remote/ping", {{cache: "no-store"}}).then(function (r) {{ return r.ok ? r.json() : null; }})
      .then(function (d) {{ if (d && d.ok && d.enabled) location.replace("/remote/"); }})
      .catch(function () {{}});
  }}
  setInterval(check, 2000);
  window.addEventListener("online", check);
  document.addEventListener("visibilitychange", function () {{ if (!document.hidden) check(); }});
</script></body></html>"""
