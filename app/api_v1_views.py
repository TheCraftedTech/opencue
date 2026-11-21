# Copyright (C) 2026 Samuel Zenker
# SPDX-License-Identifier: GPL-3.0-or-later
"""
api_v1_views.py
REST-API (Teil 5): schlichte **Status-Ansichten** fuer einfache Geraete - ein ESP32 mit Display, ein altes Tablet, ein Browser-Tab an der Wand, ein Mikrocontroller, der nur ein
Bild abholen kann. Jede Ansicht ist ein kleines Anzeigemodell (app/view_render.py), das als Bild (PNG / BMP / rohes RGB565), als Web-Seite (aktualisiert sich selbst) oder als JSON
geliefert wird:

  GET /api/v1/views                      Liste der Ansichten mit Parametern
  GET /api/v1/views/{name}               Web-Seite (HTML), aktualisiert sich selbst (?refresh=2)
  GET /api/v1/views/{name}.png|.bmp|.rgb565|.json    dieselbe Ansicht als Bild / Modell (?w=320&h=240&theme=dark|light)

Ansichten: status (Show, Blackout, Master, Timecode, aktive Cues, Tempo), timecode (grosse Uhr), dmx (Raster der 512 Kanaele eines Universums, ?universe=1), cue (der aktive Cue einer
Liste, ?list=Name), audio (Pegel, acht Baender, Tempo). Anmeldung wie sonst (Token; `?access_token=` fuer Geraete, die keinen Kopf senden koennen); Berechtigung "Status",
die DMX-Ansicht "DMX". Nur Lesen: es gibt keine Bedienung. Der Schalter "Status-Ansichten" in den Einstellungen (REST-API) schaltet alles aus.
Die DMX-Ausgabe hat immer Vorrang: Bilder werden hoechstens alle 0,4 s je Ansicht neu gerechnet (Zwischenspeicher), in einem Hintergrund-Thread, und der Server rechnet nie mehr als 4 Bilder zugleich.
"""
from __future__ import annotations

import asyncio
import json
import re
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from fastapi import Request
from fastapi.responses import HTMLResponse, JSONResponse, Response

from app import view_render
from app.api_v1 import ApiError, _route, _srv, _timecode_dict, store
from app.timecode import format_timecode

CACHE_SECONDS = 0.4
MAX_CACHE = 60
MAX_PARALLEL = 4
_cache: Dict[Tuple, Tuple[float, bytes]] = {}
_slots = asyncio.Semaphore(MAX_PARALLEL)

_LABELS = {
    "de": {"show": "Show", "blackout": "Blackout", "master": "Master", "timecode": "Timecode", "bpm": "Tempo", "on": "AN", "off": "AUS", "running": "LAEUFT", "stopped": "GESTOPPT",
           "rate": "Tempo-Faktor", "direction": "Richtung", "fwd": "VOR", "back": "RUECK", "none": "-", "level": "Pegel", "universe": "Universum", "fixtures": "Scheinwerfer", "audio": "Audio",
           "cue": "Cue", "next": "Danach", "no_signal": "KEIN SIGNAL", "offline": "Keine Verbindung zu OpenCue"},
    "en": {"show": "Show", "blackout": "Blackout", "master": "Master", "timecode": "Timecode", "bpm": "Tempo", "on": "ON", "off": "OFF", "running": "RUNNING", "stopped": "STOPPED",
           "rate": "Rate", "direction": "Direction", "fwd": "FORWARD", "back": "BACKWARD", "none": "-", "level": "Level", "universe": "Universe", "fixtures": "Fixtures", "audio": "Audio",
           "cue": "Cue", "next": "Next", "no_signal": "NO SIGNAL", "offline": "No connection to OpenCue"},
}


def _t(key: str) -> str:
    lang = getattr(_srv().state, "language", "en")
    return _LABELS.get(lang if lang in _LABELS else "en")[key]


def _cue_text(cue: Any) -> str:
    if cue is None:
        return _t("none")
    number = ("%g" % cue.number) if isinstance(cue.number, (int, float)) else str(cue.number)
    return f"{number} {cue.name or ''}".strip()


def _status(params: Dict[str, Any]) -> Dict[str, Any]:
    st = _srv().state
    srv = _srv()
    from app.audio_engine import audio_engine
    tc = _timecode_dict()
    parts: List[Dict[str, Any]] = [{"t": "title", "text": "OpenCue"},
                                   {"t": "kv", "k": _t("show"), "v": str(st.showfile_name or _t("none"))[:24]},
                                   {"t": "kv", "k": _t("blackout"), "v": _t("on") if st.blackout else _t("off"), "state": "warn" if st.blackout else "ok"},
                                   {"t": "kv", "k": _t("master"), "v": "%g %%" % round(float(st.grand_master), 1)},
                                   {"t": "kv", "k": _t("timecode"), "v": tc["position"], "state": "ok" if tc["running"] else "off"}]
    for cl in list(st.cuelists.values())[:4]:
        cue = next((c for c in cl.cues if c.id == st.active_cue_ids.get(cl.id)), None)
        parts.append({"t": "kv", "k": str(cl.name)[:14], "v": _cue_text(cue)[:20]})
    values = audio_engine.values() if audio_engine.running else {}
    if values.get("a_active"):
        parts.append({"t": "kv", "k": _t("bpm"), "v": "%d" % round(float(values.get("a_bpm", 0))), "state": "ok"})
    return {"view": "status", "parts": parts}


def _timecode(params: Dict[str, Any]) -> Dict[str, Any]:
    tc = _timecode_dict()
    return {"view": "timecode", "parts": [{"t": "title", "text": _t("timecode")},
                                          {"t": "big", "text": tc["position"], "sub": _t("running") if tc["running"] else _t("stopped"), "sub_state": "ok" if tc["running"] else "off"},
                                          {"t": "kv", "k": _t("rate"), "v": "x%g" % tc["rate"]},
                                          {"t": "kv", "k": _t("direction"), "v": _t("fwd") if tc["direction"] >= 0 else _t("back")}]}


def _dmx(params: Dict[str, Any]) -> Dict[str, Any]:
    universe = max(1, min(63999, int(params.get("universe", 1))))
    values = list(_srv().dmx_engine.get_universe_snapshot(universe))[:512]
    return {"view": "dmx", "universe": universe, "parts": [{"t": "title", "text": f"DMX {universe}"}, {"t": "grid", "cols": 32, "values": [v / 255.0 for v in values]}]}


def _cue(params: Dict[str, Any]) -> Dict[str, Any]:
    st = _srv().state
    wanted = str(params.get("list", "")).strip().lower()
    cl = next((c for c in st.cuelists.values() if wanted and (c.name.lower() == wanted or c.id == wanted)), None) or st.cuelists.get(st.active_cuelist_id) or next(iter(st.cuelists.values()), None)
    if cl is None:
        return {"view": "cue", "parts": [{"t": "title", "text": _t("cue")}, {"t": "big", "text": _t("none")}]}
    cues = list(cl.cues)
    index = next((i for i, c in enumerate(cues) if c.id == st.active_cue_ids.get(cl.id)), None)
    cue = cues[index] if index is not None else None
    following = cues[(index + 1) % len(cues)] if index is not None and len(cues) > 1 else None
    number = ("%g" % cue.number) if cue is not None and isinstance(cue.number, (int, float)) else (str(cue.number) if cue is not None else _t("none"))
    return {"view": "cue", "parts": [{"t": "title", "text": str(cl.name)[:24]}, {"t": "big", "text": number, "sub": (cue.name if cue is not None else "") or ""},
                                     {"t": "kv", "k": _t("next"), "v": _cue_text(following)[:22]}]}


def _audio(params: Dict[str, Any]) -> Dict[str, Any]:
    from app.audio_engine import audio_engine
    values = audio_engine.values() if audio_engine.running else {}
    active = bool(values.get("a_active"))
    parts: List[Dict[str, Any]] = [{"t": "title", "text": _t("audio")}]
    if not active:
        parts.append({"t": "big", "text": _t("no_signal"), "state": "off"})
        return {"view": "audio", "parts": parts}
    parts.append({"t": "bars", "values": [float(values.get(f"a_b{i}", 0)) for i in range(1, 9)], "labels": [str(i) for i in range(1, 9)]})
    parts.append({"t": "kv", "k": _t("level"), "v": "%d %%" % round(float(values.get("a_level", 0)) * 100)})
    parts.append({"t": "kv", "k": _t("bpm"), "v": "%d" % round(float(values.get("a_bpm", 0))), "state": "ok"})
    return {"view": "audio", "parts": parts}


# name -> (Funktion, Berechtigung, Parameter, Beschreibung)
VIEWS: Dict[str, Tuple[Callable[[Dict[str, Any]], Dict[str, Any]], str, List[str], str]] = {
    "status": (_status, "read.status", [], "Show, blackout, master, timecode, active cue of every list, tempo"),
    "timecode": (_timecode, "read.status", [], "The timecode as a big clock with running / stopped"),
    "dmx": (_dmx, "read.dmx", ["universe"], "The 512 channels of a universe as a grid of cells (brightness = value)"),
    "cue": (_cue, "read.status", ["list"], "The active cue of a list (number, name) and the next one"),
    "audio": (_audio, "read.status", [], "Level, the eight frequency bands and the tempo"),
}
FORMATS = {"png": "image/png", "bmp": "image/bmp", "rgb565": "application/octet-stream", "json": "application/json"}


def _params(request: Request) -> Dict[str, Any]:
    q = request.query_params
    out: Dict[str, Any] = {}
    for key in ("universe", "w", "h"):
        if key in q:
            try:
                out[key] = int(q[key])
            except ValueError:
                raise ApiError(400, "bad_request", f"{key} must be a whole number.")
    for key in ("list", "theme"):
        if key in q:
            out[key] = q[key][:60]
    if "color" in q:
        if view_render.parse_color(q["color"]) is None:
            raise ApiError(400, "bad_request", "color: a name (amber, green, red, blue, cyan, white, magenta, violet, orange, yellow) or #rrggbb.")
        out["color"] = q["color"]
    if "refresh" in q:
        try:
            out["refresh"] = max(0.5, min(60.0, float(q["refresh"])))
        except ValueError:
            raise ApiError(400, "bad_request", "refresh must be a number of seconds.")
    return out


def _check(request: Request, name: str) -> Tuple[Callable, Dict[str, Any]]:
    if not store.is_views():
        raise ApiError(403, "views_disabled", "The status views are switched off in the OpenCue settings (REST API).")
    entry = VIEWS.get(name)
    if entry is None:
        raise ApiError(404, "not_found", f"No view '{name}' (views: {', '.join(VIEWS)}).")
    token = getattr(request.state, "api_token", None) or {}
    if entry[1] not in token.get("capabilities", []):
        raise ApiError(403, "forbidden", f"This token does not have the permission '{entry[1]}' (needed for the view '{name}').")
    return entry[0], _params(request)


DEFAULT_ACCENT = {"dmx": "green"}                 # der DMX-Monitor ist standardmaessig gruen; ?color= ueberschreibt


def _accent(name: str, params: Dict[str, Any]) -> Any:
    return view_render.parse_color(params.get("color") or DEFAULT_ACCENT.get(name))


def _render_bytes(model: Dict[str, Any], fmt: str, width: int, height: int, theme: str, accent: Any = None) -> bytes:
    pixels = view_render.draw(model, width, height, theme, accent)
    if fmt == "png":
        return view_render.to_png(pixels)
    if fmt == "bmp":
        return view_render.to_bmp(pixels)
    return view_render.to_rgb565(pixels)


@_route("/views", "read.status", "List the status views")
async def list_views() -> Dict[str, Any]:
    """The status views for simple devices (an ESP32 display, a wall tablet): the name, the permission, the parameters and the URLs of each format."""
    return {"enabled": store.is_views(),
            "formats": ["html", *FORMATS],
            "common_parameters": {"w": "image width in pixels (64-800, default 320)", "h": "image height (48-600, default 240)", "theme": "dark (default) | light", "refresh": "seconds between updates of the web page (0.5-60, default 2)"},
            "views": [{"name": name, "capability": cap, "parameters": params, "description": about, "html": f"/api/v1/views/{name}", "png": f"/api/v1/views/{name}.png", "bmp": f"/api/v1/views/{name}.bmp",
                       "rgb565": f"/api/v1/views/{name}.rgb565", "json": f"/api/v1/views/{name}.json"} for name, (_fn, cap, params, about) in VIEWS.items()]}


# Reihenfolge: zuerst die Route mit Endung - sonst faengt "/views/{name}" auch "dmx.png" ab
@_route("/views/{name}.{fmt}", "read.status", "A status view as an image (png, bmp, rgb565) or as JSON", query_token=True)
async def view_image(request: Request, name: str, fmt: str) -> Response:
    """`png` / `bmp` (24 bit) / `rgb565` (raw 16 bit pixels, high byte first, for a TFT; the size is in the headers `X-Width`, `X-Height`) / `json` (the display model). `?w=320&h=240&theme=dark`.
    The picture is rendered at most every 0.4 s per view and size; many devices share it."""
    if fmt not in FORMATS:
        raise ApiError(404, "not_found", f"No format '{fmt}' (png, bmp, rgb565, json).")
    builder, params = _check(request, name)
    if fmt == "json":
        return JSONResponse(builder(params), headers={"Cache-Control": "no-store"})
    width, height = max(64, min(view_render.MAX_W, params.get("w", 320))), max(48, min(view_render.MAX_H, params.get("h", 240)))
    theme = params.get("theme", "dark")
    accent = _accent(name, params)
    key = (name, fmt, width, height, theme, accent, json.dumps({k: v for k, v in params.items() if k in ("universe", "list")}, sort_keys=True))
    now = time.monotonic()
    hit = _cache.get(key)
    if hit is None or now - hit[0] > CACHE_SECONDS:
        model = builder(params)
        async with _slots:                                                       # nie mehr als 4 Bilder zugleich; in einem Thread, damit die Ereignisschleife (Cues, DMX-Takt) frei bleibt
            data = await asyncio.to_thread(_render_bytes, model, fmt, width, height, theme, accent)
        if len(_cache) >= MAX_CACHE:
            for stale in sorted(_cache, key=lambda k: _cache[k][0])[:MAX_CACHE // 2]:
                _cache.pop(stale, None)
        _cache[key] = (now, data)
    else:
        data = hit[1]
    return Response(data, media_type=FORMATS[fmt], headers={"Cache-Control": "no-store", "X-Width": str(width), "X-Height": str(height)})


@_route("/views/{name}", "read.status", "A status view as a self-updating web page", query_token=True)
async def view_page(request: Request, name: str) -> HTMLResponse:
    """HTML page that refreshes itself every `refresh` seconds (default 2). Browsers cannot send headers from the address bar: use `?access_token=<token>`. Read-only."""
    builder, params = _check(request, name)
    theme = params.get("theme", "dark")
    refresh = params.get("refresh", 2.0)
    model = builder(params)
    accent = _accent(name, params)
    if request.query_params.get("fragment"):                                       # nur der Inhalt (fuer die Aktualisierung der Seite)
        return HTMLResponse(view_render.to_html_fragment(model, theme, accent), headers={"Cache-Control": "no-store"})
    query = request.url.query + ("&" if request.url.query else "") + "fragment=1"
    return HTMLResponse(view_render.to_html_page(model, theme, refresh, f"{request.url.path}?{query}", accent, _t("offline")), headers={"Cache-Control": "no-store"})


# ------------------------------------------------------------------------------------------------------------------ Fehler als Bild / Seite
_ERRORS = {
    "de": {"unauthorized_missing": "TOKEN FEHLT IN DER ADRESSE (?access_token=)", "unauthorized_invalid": "TOKEN UNGUELTIG ODER GELOESCHT", "forbidden": "KEINE BERECHTIGUNG", "views_disabled": "STATUS-ANSICHTEN SIND AUS", "api_disabled": "API IST AUS", "api_local_only": "API NUR AUF DIESEM PC",
           "token_disabled": "TOKEN IST AUSGESCHALTET", "rate_limited": "ZU VIELE VERSUCHE", "not_found": "ANSICHT NICHT GEFUNDEN", "bad_request": "FALSCHER PARAMETER"},
    "en": {"unauthorized_missing": "TOKEN MISSING IN THE ADDRESS (?access_token=)", "unauthorized_invalid": "TOKEN INVALID OR DELETED", "forbidden": "NO PERMISSION", "views_disabled": "STATUS VIEWS ARE OFF", "api_disabled": "API IS OFF", "api_local_only": "API ONLY ON THIS PC",
           "token_disabled": "TOKEN IS SWITCHED OFF", "rate_limited": "TOO MANY ATTEMPTS", "not_found": "VIEW NOT FOUND", "bad_request": "WRONG PARAMETER"},
}
_PATH = re.compile(r"^/api/v1/views/(?P<name>[^/.]+)(?:\.(?P<fmt>[a-z0-9]+))?$")


def error_response(request: Request, status: int, code: str, message: str, headers: Optional[Dict[str, str]] = None) -> Optional[Response]:
    """Fehler der Ansichten sichtbar machen: ein Bild-Abruf (png / bmp / rgb565) bekommt ein BILD mit der Meldung (ein ESP32 zeigt es einfach an), die Web-Seite eine Seite mit der Meldung.
    Der Statuscode bleibt der des Fehlers. JSON und alle anderen Routen bleiben bei der gewohnten JSON-Antwort (None)."""
    match = _PATH.match(request.url.path)
    if not match or request.method != "GET":
        return None
    fmt = match.group("fmt")
    if fmt in ("json",) or (fmt is not None and fmt not in ("png", "bmp", "rgb565")):
        return None
    try:
        lang = getattr(_srv().state, "language", "en")
    except Exception:
        lang = "en"
    table = _ERRORS.get(lang) or _ERRORS["en"]
    key = ("unauthorized_missing" if message.startswith("Missing") else "unauthorized_invalid") if code == "unauthorized" else code
    title = table.get(key, code.upper().replace("_", " "))
    model = {"parts": [{"t": "title", "text": "OpenCue"}, {"t": "big", "text": "!", "state": "warn", "sub": title + ". " + message if code not in ("not_found",) else title}]}
    out_headers = {**(headers or {}), "Cache-Control": "no-store"}
    if fmt is None:
        body = view_render.to_html_page(model, "dark", 5.0, request.url.path, None, _t("offline")).replace("<noscript>", "<meta http-equiv=\"refresh\" content=\"5\"><noscript>", 1)
        return HTMLResponse(body, status_code=status, headers=out_headers)
    try:
        width, height = max(64, min(view_render.MAX_W, int(request.query_params.get("w", 320)))), max(48, min(view_render.MAX_H, int(request.query_params.get("h", 240))))
    except ValueError:
        width, height = 320, 240
    return Response(_render_bytes(model, fmt, width, height, "dark"), status_code=status, media_type=FORMATS[fmt], headers={**out_headers, "X-Width": str(width), "X-Height": str(height)})
