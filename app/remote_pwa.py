# Copyright (C) 2026 Samuel Zenker
# SPDX-License-Identifier: GPL-3.0-or-later
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

import base64
import hashlib
import json
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
ROOT_ICON_PATHS = ("/apple-touch-icon.png", "/apple-touch-icon-precomposed.png", "/apple-touch-icon-180x180.png")   # Safari fragt diese Adressen von sich aus ab
PUBLIC_PATHS = {
    "/remote/manifest.webmanifest", "/remote/sw.js", "/remote/offline.html", "/remote/ping", "/favicon.ico", *ROOT_ICON_PATHS,
    "/remote/zertifikat", "/remote/opencue.mobileconfig", "/remote/opencue-ca.crt",          # Zertifikat der eigenen Stelle (oeffentlich, ohne Geheimnis): muss VOR dem Vertrauen ladbar sein
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
        "lang": state.language,
        "dir": "ltr",
        "categories": ["utilities", "productivity"],
        "prefer_related_applications": False,
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

_data_uris: Dict[str, str] = {}


def icon_data_uri(name: str) -> str:
    """Ein Symbol als data:-Adresse (die Dateien sind nur ~1 KB gross). Grund: ueber HTTPS mit einem selbst erstellten Zertifikat holt iOS das Symbol fuer
    'Zum Home-Bildschirm' in einem eigenen Vorgang OHNE die vom Nutzer bestaetigte Zertifikats-Ausnahme - das Laden der Datei schlaegt dann still fehl
    und es erscheint ein graues Buchstaben-Symbol. Eine eingebettete Adresse braucht keinen Abruf, sie funktioniert in jedem Fall."""
    cached = _data_uris.get(name)
    if cached is None:
        try:
            cached = "data:image/png;base64," + base64.b64encode((ICON_DIR / name).read_bytes()).decode("ascii")
        except OSError:
            cached = ""
        _data_uris[name] = cached
    return cached


def head_tags() -> str:
    """Manifest, Theme-Farbe und die iPad/Safari-Tags: 'Zum Home-Bildschirm' startet eine eigenstaendige App. Die Symbole sind eingebettet (siehe icon_data_uri)."""
    # Dunkles Thema: schwarze Statusleiste ueber dem Inhalt; helles Thema: helle Leiste mit dunkler Schrift.
    status_bar = "default" if state.theme["base"] == "light" else "black"
    touch, small = icon_data_uri("apple-touch-icon.png"), icon_data_uri("icon-192.png")
    return (
        '<link rel="manifest" href="/remote/manifest.webmanifest">\n'
        f'<meta name="theme-color" content="{theme_color()}">\n'
        '<meta name="apple-mobile-web-app-capable" content="yes">\n'
        '<meta name="mobile-web-app-capable" content="yes">\n'
        '<meta name="apple-mobile-web-app-title" content="OpenCue">\n'
        '<meta name="application-name" content="OpenCue">\n'
        '<meta name="format-detection" content="telephone=no">\n'
        f'<meta name="apple-mobile-web-app-status-bar-style" content="{status_bar}">\n'
        f'<link rel="apple-touch-icon" sizes="180x180" href="{touch or "/remote/icons/apple-touch-icon.png"}">\n'
        f'<link rel="icon" type="image/png" sizes="192x192" href="{small or "/remote/icons/icon-192.png"}">\n'
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
const NAV_TIMEOUT_MS = 1500;    // so lange darf der Server auf eine Seite antworten, bevor die Offline-Seite erscheint
                                // (ohne diese Grenze bleibt der Bildschirm weiss, wenn das WLAN da ist, der Rechner aber nicht antwortet: die Verbindung "haengt" dann minutenlang).
                                // Antwortet der Server doch (nur langsam), blendet die Offline-Seite sich nach spaetestens ~1 s selbst wieder aus (sie fragt ihn ab).

const NAV_RETRY_TIMEOUT_MS = 20000;   // Aufruf "/remote/?r=1" (die Offline-Seite hat den Server gerade erreicht): hier darf die Seite laenger brauchen - sonst gaebe es bei einem langsamen Gebaeude-Netz eine Schleife

function withTimeout(promise, ms) {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error("timeout")), ms);
    promise.then((value) => { clearTimeout(timer); resolve(value); }, (error) => { clearTimeout(timer); reject(error); });
  });
}

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
    event.respondWith(withTimeout(fetch(request), url.searchParams.get("r") ? NAV_RETRY_TIMEOUT_MS : NAV_TIMEOUT_MS).catch(() => caches.match("/remote/offline.html").then((page) => page || new Response(
      "<!doctype html><meta name=viewport content='width=device-width,initial-scale=1'><body style='font-family:system-ui;padding:2rem;background:#111;color:#eee'>" +
      "<h2>OpenCue</h2><p>Server not reachable / nicht erreichbar.</p><p><a style='color:#fb0' href='/remote/'>Reload / Neu laden</a></p>",
      {status: 503, headers: {"Content-Type": "text/html; charset=utf-8"}}))));
    return;
  }
  if (cacheable(url)) {
    event.respondWith(networkFirst(request).catch(() => Response.error()));
  }
  // alles andere (API, Auth, Ping, ...): nicht anfassen -> direkt ins Netz
});
"""


def service_worker() -> str:
    """Der Kennwert enthaelt auch die (von Python erzeugte) Offline-Seite: aendern sich Sprache, Farben oder ihr Text, aendert sich der Service Worker, und der Browser
    installiert ihn neu und holt die Offline-Seite frisch in den Zwischenspeicher."""
    page_hash = hashlib.sha1(offline_page().encode("utf-8")).hexdigest()[:8]
    return SERVICE_WORKER.replace("__BUILD__", build_id() + "-" + page_hash)


# ---- Offline-Seite (auch Serverwahl) -----------------------------------------------------

OFFLINE_KEYS = (
    "SRV_OFFLINE_TITLE", "SRV_OFFLINE_RETRY", "OFFLINE_UNREACHABLE", "OFFLINE_RELOAD", "OFFLINE_OTHER", "OFFLINE_HOST", "OFFLINE_PORT", "OFFLINE_HTTPS", "OFFLINE_CONNECT",
    "OFFLINE_RECENT", "OFFLINE_CHECKING", "OFFLINE_NOT_FOUND", "OFFLINE_OPEN_ANYWAY", "OFFLINE_HINT", "OFFLINE_THIS", "OFFLINE_REMOVE", "OFFLINE_BAD_ADDRESS",
)


def offline_page() -> str:
    """Wird gezeigt, wenn der Server nicht erreichbar ist (der Service Worker liefert die Seite aus dem Zwischenspeicher). Neben dem automatischen Wiederholen
    kann man hier eine andere Adresse eintragen (IP oder Name, Port, HTTPS ja / nein): so bleibt die einmal installierte App dieselbe, auch wenn sich die
    Adresse des Rechners aendert. Die zuletzt benutzten Adressen merkt sich die Seite im Speicher dieses Geraets (localStorage)."""
    tokens = resolved_tokens()
    colors = {
        "bg": tokens.get("bg", "#0a0a0b"),
        "surface": tokens.get("surface-1", "#151517"),
        "surface2": tokens.get("surface-2", "#1d1d20"),
        "border": tokens.get("border", "#323237"),
        "text": tokens.get("text-1", "#ededf0"),
        "muted": tokens.get("text-2", "#a2a2aa"),
        "accent": tokens.get("accent", "#ffb000"),
        "ink": tokens.get("accent-ink", "#1a1200"),
        "error": tokens.get("error", "#ff6b6b"),
    }
    base = state.theme["base"]
    from app.languages import tr
    texts = json.dumps({key: tr(key, state.language) for key in OFFLINE_KEYS}, ensure_ascii=False)
    touch = icon_data_uri("apple-touch-icon.png")
    icon = icon_data_uri("icon-192.png")
    css = """
  * { box-sizing: border-box; }
  html, body { margin: 0; min-height: 100%; background: %(bg)s; color: %(text)s; font-family: -apple-system, "Segoe UI", system-ui, sans-serif; }
  body { min-height: 100dvh; display: flex; align-items: center; justify-content: center;
    padding: max(16px, env(safe-area-inset-top)) max(16px, env(safe-area-inset-right)) max(16px, env(safe-area-inset-bottom)) max(16px, env(safe-area-inset-left)); }
  main { width: min(100%%, 28rem); padding: 26px 22px; background: %(surface)s; border: 1px solid %(border)s; border-radius: 14px; }
  .head { display: flex; align-items: center; gap: 14px; margin-bottom: 14px; }
  .head img { width: 52px; height: 52px; border-radius: 12px; flex: none; }
  h1 { margin: 0; font-size: 1.25rem; line-height: 1.2; }
  h2 { margin: 22px 0 10px; font-size: .8rem; letter-spacing: .06em; text-transform: uppercase; color: %(muted)s; font-weight: 600; }
  p { margin: 0; color: %(muted)s; line-height: 1.45; font-size: .95rem; }
  .addr { margin-top: 10px; padding: 10px 12px; background: %(surface2)s; border: 1px solid %(border)s; border-radius: 10px; font-family: ui-monospace, Menlo, Consolas, monospace; font-size: .9rem; word-break: break-all; }
  .spin { width: 20px; height: 20px; border: 3px solid %(border)s; border-top-color: %(accent)s; border-radius: 50%%; animation: s 1s linear infinite; flex: none; }
  .status { display: flex; align-items: center; gap: 10px; margin-top: 14px; }
  button, input { font: inherit; font-size: 1rem; min-height: 3rem; border-radius: 10px; border: 1px solid %(border)s; }
  input[type=text], input[type=number] { width: 100%%; padding: 0 12px; background: %(surface2)s; color: %(text)s; }
  input:focus-visible, button:focus-visible { outline: 2px solid %(accent)s; outline-offset: 1px; }
  button { padding: 0 16px; background: %(surface2)s; color: %(text)s; cursor: pointer; }
  button.primary { background: %(accent)s; border-color: %(accent)s; color: %(ink)s; font-weight: 600; }
  button:active { filter: brightness(.92); }
  .row { display: grid; grid-template-columns: 1fr 6.5rem; gap: 10px; }
  .row label, .sw { display: block; font-size: .8rem; color: %(muted)s; margin-bottom: 4px; }
  .sw { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin: 12px 0; min-height: 2.75rem; font-size: 1rem; color: %(text)s; }
  .sw input { appearance: none; -webkit-appearance: none; width: 3rem; min-height: 0; height: 1.7rem; border-radius: 999px; background: %(surface2)s; border: 1px solid %(border)s; position: relative; flex: none; padding: 0; }
  .sw input::after { content: ""; position: absolute; top: 2px; left: 2px; width: calc(1.7rem - 6px); height: calc(1.7rem - 6px); border-radius: 50%%; background: %(muted)s; transition: transform .18s; }
  .sw input:checked { background: %(accent)s; border-color: %(accent)s; }
  .sw input:checked::after { background: #fff; transform: translateX(1.3rem); }
  .actions { display: flex; gap: 10px; margin-top: 14px; }
  .actions button { flex: 1; }
  .msg { min-height: 1.3em; margin-top: 10px; color: %(error)s; font-size: .9rem; }
  .msg button { min-height: 2.5rem; margin-top: 6px; }
  .recent { display: flex; flex-direction: column; gap: 8px; }
  .chip { display: flex; align-items: stretch; gap: 0; }
  .chip .go { flex: 1; text-align: left; font-family: ui-monospace, Menlo, Consolas, monospace; font-size: .9rem; border-radius: 10px 0 0 10px; overflow: hidden; text-overflow: ellipsis; }
  .chip .del { width: 3rem; padding: 0; border-left: 0; border-radius: 0 10px 10px 0; color: %(muted)s; }
  .hint { margin-top: 18px; font-size: .85rem; }
  @keyframes s { to { transform: rotate(360deg); } }
  @media (prefers-reduced-motion: reduce) { .spin { animation: none; } }
"""
    for name, value in colors.items():
        css = css.replace("%(" + name + ")s", value)
    css = css.replace("%%", "%")
    script = r"""
(function () {
  var T = __TEXTS__;
  var KEY = "opencue.servers";
  var here = {host: location.hostname, port: location.port || (location.protocol === "https:" ? "443" : "80"), https: location.protocol === "https:"};
  function $(id) { return document.getElementById(id); }
  function fmt(s) { return (s.https ? "https" : "http") + "://" + s.host + (s.port && s.port !== (s.https ? "443" : "80") ? ":" + s.port : ""); }
  function load() { try { var l = JSON.parse(localStorage.getItem(KEY) || "[]"); return Array.isArray(l) ? l.filter(function (s) { return s && s.host; }) : []; } catch (e) { return []; } }
  function save(l) { try { localStorage.setItem(KEY, JSON.stringify(l.slice(0, 6))); } catch (e) { /* privat */ } }
  function same(a, b) { return a.host === b.host && String(a.port) === String(b.port) && !!a.https === !!b.https; }
  function remember(s) { save([s].concat(load().filter(function (x) { return !same(x, s); }))); }

  $("t").textContent = T.OFFLINE_UNREACHABLE;
  $("m").textContent = T.SRV_OFFLINE_RETRY;
  $("here").textContent = fmt(here);
  $("hereLabel").textContent = T.OFFLINE_THIS;
  $("reload").textContent = T.OFFLINE_RELOAD;
  $("otherTitle").textContent = T.OFFLINE_OTHER;
  $("hostLabel").textContent = T.OFFLINE_HOST;
  $("portLabel").textContent = T.OFFLINE_PORT;
  $("httpsLabel").textContent = T.OFFLINE_HTTPS;
  $("connect").textContent = T.OFFLINE_CONNECT;
  $("recentTitle").textContent = T.OFFLINE_RECENT;
  $("hint").textContent = T.OFFLINE_HINT;
  $("host").value = "";
  $("port").value = here.port;
  $("https").checked = here.https;

  var pinging = false;
  function ping() {
    // eine Abfrage hoechstens 1,5 s lang (ein haengender Server soll sich nicht aufstauen)
    var ctl = ("AbortController" in window) ? new AbortController() : null;
    var timer = setTimeout(function () { if (ctl) ctl.abort(); }, 1500);
    return fetch("/remote/ping", {cache: "no-store", signal: ctl ? ctl.signal : undefined}).then(function (r) { clearTimeout(timer); return r.ok ? r.json() : null; })
      .then(function (d) { return !!(d && d.ok && d.enabled); }).catch(function () { clearTimeout(timer); return false; });
  }
  var manual = /[?&]change=1/.test(location.search);        // "Anderen Server waehlen": bewusst geoeffnet, auch wenn der Server antwortet - nicht automatisch zurueckspringen
  function check() {
    if (manual || pinging) return;
    pinging = true;
    ping().then(function (ok) { pinging = false; if (ok) location.replace("/remote/?r=1"); });
  }
  check();
  setInterval(check, 700);
  window.addEventListener("online", check);
  document.addEventListener("visibilitychange", function () { if (!document.hidden) check(); });
  $("reload").addEventListener("click", function () { $("status").textContent = T.OFFLINE_CHECKING; ping().then(function (ok) { if (ok) location.replace("/remote/?r=1"); else $("status").textContent = T.SRV_OFFLINE_RETRY; }); });

  function parse() {
    var raw = $("host").value.trim(), https = $("https").checked, port = $("port").value.trim();
    if (!raw) return null;
    if (/^[a-z]+:\/\//i.test(raw)) {                         // ganze Adresse eingegeben: Teile uebernehmen
      try { var u = new URL(raw); raw = u.hostname; https = u.protocol === "https:"; if (u.port) port = u.port; } catch (e) { return null; }
    }
    raw = raw.replace(/\/.*$/, "").replace(/:\d+$/, "");
    if (!/^[A-Za-z0-9.\-]+$/.test(raw) || +port < 0 || +port > 65535) return null;
    return {host: raw, port: port || (https ? "443" : "80"), https: https};
  }
  function go(s) { remember(s); location.href = fmt(s) + "/remote/"; }
  function showMsg(text, server) {
    var m = $("msg");
    m.textContent = text;
    if (server) {
      var b = document.createElement("button");
      b.type = "button"; b.textContent = T.OFFLINE_OPEN_ANYWAY;
      b.addEventListener("click", function () { go(server); });
      m.appendChild(document.createElement("br")); m.appendChild(b);
    }
  }
  function connect(s) {
    $("msg").textContent = "";
    if (same(s, here)) { $("reload").click(); return; }
    var sameProtocol = s.https === here.https;
    if (!sameProtocol) { go(s); return; }                   // ueber Protokollgrenzen laesst sich nicht vorab pruefen: direkt oeffnen
    $("status").textContent = T.OFFLINE_CHECKING;
    var ctl = ("AbortController" in window) ? new AbortController() : null;
    var timer = setTimeout(function () { if (ctl) ctl.abort(); }, 4500);
    fetch(fmt(s) + "/remote/ping", {mode: "no-cors", cache: "no-store", signal: ctl ? ctl.signal : undefined})
      .then(function () { clearTimeout(timer); go(s); })
      .catch(function () { clearTimeout(timer); $("status").textContent = T.SRV_OFFLINE_RETRY; showMsg(T.OFFLINE_NOT_FOUND, s); });
  }
  $("connect").addEventListener("click", function () {
    var s = parse();
    if (!s) { showMsg(T.OFFLINE_BAD_ADDRESS); return; }
    connect(s);
  });
  $("host").addEventListener("keydown", function (e) { if (e.key === "Enter") $("connect").click(); });
  $("https").addEventListener("change", function () {       // Standard-Port folgt dem Schalter, solange man ihn nicht selbst geaendert hat
    var p = $("port").value;
    if (p === "80" || p === "443" || p === "") $("port").value = $("https").checked ? "443" : "80";
  });

  function renderRecent() {
    var list = load(), box = $("recent");
    box.textContent = "";
    $("recentWrap").hidden = !list.length;
    list.forEach(function (s) {
      var row = document.createElement("div"); row.className = "chip";
      var go1 = document.createElement("button"); go1.type = "button"; go1.className = "go"; go1.textContent = fmt(s);
      go1.addEventListener("click", function () { connect(s); });
      var del = document.createElement("button"); del.type = "button"; del.className = "del"; del.textContent = "×"; del.setAttribute("aria-label", T.OFFLINE_REMOVE);
      del.addEventListener("click", function () { save(load().filter(function (x) { return !same(x, s); })); renderRecent(); });
      row.appendChild(go1); row.appendChild(del); box.appendChild(row);
    });
  }
  remember(here);
  renderRecent();
  if (/[?&]change=1/.test(location.search)) $("host").focus();
})();
""".replace("__TEXTS__", texts)
    return f"""<!doctype html>
<html lang="{state.language}" data-theme="{base}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="color-scheme" content="{base}">
<meta name="theme-color" content="{theme_color()}">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="OpenCue">
<link rel="apple-touch-icon" sizes="180x180" href="{touch}">
<link rel="icon" type="image/png" href="{icon}">
<title>OpenCue</title>
<style>{css}</style></head><body>
<main>
  <div class="head"><img src="{touch}" alt="" width="52" height="52"><div><h1 id="t">OpenCue</h1><p id="m"></p></div></div>
  <h2 id="hereLabel"></h2>
  <div class="addr" id="here"></div>
  <div class="status"><div class="spin"></div><span id="status"></span></div>
  <div class="actions"><button type="button" class="primary" id="reload"></button></div>
  <h2 id="otherTitle"></h2>
  <div class="row"><div><label for="host" id="hostLabel"></label><input id="host" type="text" inputmode="url" autocapitalize="off" autocorrect="off" spellcheck="false" placeholder="opencue.local"></div>
    <div><label for="port" id="portLabel"></label><input id="port" type="number" inputmode="numeric" min="1" max="65535"></div></div>
  <label class="sw"><span id="httpsLabel"></span><input id="https" type="checkbox"></label>
  <div class="actions"><button type="button" class="primary" id="connect"></button></div>
  <div class="msg" id="msg" role="alert"></div>
  <div id="recentWrap" hidden><h2 id="recentTitle"></h2><div class="recent" id="recent"></div></div>
  <p class="hint" id="hint"></p>
</main>
<script>{script}</script></body></html>"""
