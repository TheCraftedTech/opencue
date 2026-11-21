# Copyright (C) 2026 Samuel Zenker
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Standardwerte der Konsole (Einstellungen -> "Standardwerte"): gelten fuer das ganze Programm, ueber alle Shows hinweg (stehen in der app_config.json, nicht in der Show).

  Neue Cues:   Abspielart (relativ / absolut), Ausloeser (Go / Follow), Verzoegerung, Ueberblendzeit, Effekt-Ein-/Ausblendzeit, MIB - fuer jeden Cue, bei dem der
               Speichernde nichts anderes angibt (Speichern-Dialog, Befehl `Store Cue`, REST-API).
  Aktualisieren: was `Update` / der Knopf "Aktualisieren" tut - fragen, nur diesen Cue aendern oder in die Folge-Cues durchlaufen lassen (Tracking).
  Clear Clear: Grundzustand der Scheinwerfer - Dimmer, Farbe, Position (auch beim Programmstart).
  Programmstart: Grand Master (aus der Show oder ein fester Wert) und Blackout.
  Executor:    Stand des Faders fuer Cue-Listen, fuer die die Show noch keinen eigenen Stand gespeichert hat (neue Listen).

  GET  /api/defaults   die Werte (und die Werkseinstellungen)
  POST /api/defaults   Werte uebernehmen und speichern (nur lokal)
"""
from __future__ import annotations

import re
from typing import Any, Dict, Optional

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

DEFAULTS: Dict[str, Any] = {
    "cue_play_mode": "tracking",          # "tracking" (relativ: nur die Aenderungen) | "absolute" (genau der gespeicherte Zustand)
    "cue_trigger": "go",                  # "go" (manuell) | "follow" (folgt dem vorigen Cue selbst)
    "cue_delay": 0.0,                     # Sekunden
    "cue_fade": 0.0,                      # Sekunden
    "cue_fx_fade_in": 0.0,                # Sekunden
    "cue_fx_fade_out": 0.0,               # Sekunden
    "cue_mib": "Off",                     # "Off" | "Auto" | "On"
    "clear_dimmer": 0.0,                  # Prozent; Geraete ohne Dimmer-Kanal bleiben dunkel
    "clear_color": "#ffffff",             # Farbe nach Clear Clear (Geraete OHNE Dimmer-Kanal, bei denen die Farbe die Helligkeit ist, bleiben schwarz)
    "clear_position": "zero",             # "zero" = 0 Grad (wie bisher) | "center" = Mitte des Bereichs (50 %)
    "update_mode": "ask",                 # "ask" = der Knopf fragt | "normal" = Tracking (Folge-Cues laufen mit) | "only" = nur dieser Cue (auch fuer den Befehl `Update`)
    "start_master_mode": "show",          # Grand Master beim Programmstart: "show" = wie in der Show gespeichert | "fixed" = start_grand_master
    "start_grand_master": 100.0,          # Prozent
    "start_blackout": False,              # Blackout beim Programmstart an
    "executor_start": 100.0,              # Prozent
    "confirm_delete_cues": True,          # Sicherheitsfrage vor dem Loeschen (True) oder sofort loeschen (False), je Kategorie:
    "confirm_delete_fixtures": True,      #   Scheinwerfer und Gruppen
    "confirm_delete_library": True,       #   Variablen, Effekte, Effekt-Skripte, Scheinwerfer-Bibliothek
    "confirm_delete_files": True,         #   Dateien: Shows, Layouts, Buehnen, Modelle, Medien, Farbprofile
    "confirm_delete_other": True,         #   Sonstiges: KI-Chats, API-Tokens, 3D-Objekte
}
BOOL_KEYS = ("confirm_delete_cues", "confirm_delete_fixtures", "confirm_delete_library", "confirm_delete_files", "confirm_delete_other")
TIME_KEYS = ("cue_delay", "cue_fade", "cue_fx_fade_in", "cue_fx_fade_out")
PERCENT_KEYS = ("clear_dimmer", "start_grand_master", "executor_start")
HEX = re.compile(r"^#[0-9a-fA-F]{6}$")

router = APIRouter()


def normalize(raw: Any, base: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """`base` (sonst die Werkseinstellungen) mit den gueltigen Angaben aus `raw` ueberschrieben; Unbekanntes und Ungueltiges wird verworfen."""
    out = {key: (base or DEFAULTS).get(key, default) for key, default in DEFAULTS.items()}
    if not isinstance(raw, dict):
        return out
    if raw.get("cue_play_mode") in ("tracking", "absolute"):
        out["cue_play_mode"] = raw["cue_play_mode"]
    if raw.get("cue_mib") in ("Off", "Auto", "On"):
        out["cue_mib"] = raw["cue_mib"]
    if raw.get("cue_trigger") in ("go", "follow"):
        out["cue_trigger"] = raw["cue_trigger"]
    if raw.get("update_mode") in ("ask", "normal", "only"):
        out["update_mode"] = raw["update_mode"]
    if raw.get("start_master_mode") in ("show", "fixed"):
        out["start_master_mode"] = raw["start_master_mode"]
    if "start_blackout" in raw:
        out["start_blackout"] = raw["start_blackout"] is True or str(raw["start_blackout"]).lower() in ("1", "true", "on")
    for key in BOOL_KEYS:
        if key in raw:
            out[key] = raw[key] is True or str(raw[key]).lower() in ("1", "true", "on")
    if raw.get("clear_position") in ("zero", "center"):
        out["clear_position"] = raw["clear_position"]
    for key in TIME_KEYS:
        if key in raw:
            try:
                value = float(raw[key])
            except (TypeError, ValueError):
                continue
            if value == value and abs(value) != float("inf"):
                out[key] = round(max(0.0, min(3600.0, value)), 3)
    for key in PERCENT_KEYS:
        if key in raw:
            try:
                value = float(raw[key])
            except (TypeError, ValueError):
                continue
            if value == value and abs(value) != float("inf"):
                out[key] = round(max(0.0, min(100.0, value)), 2)
    if isinstance(raw.get("clear_color"), str) and HEX.match(raw["clear_color"].strip()):
        out["clear_color"] = raw["clear_color"].strip().lower()
    return out


def clear_rgb(config: Dict[str, Any]) -> Dict[str, int]:
    """Die Farbe nach Clear Clear als {r, g, b} (0-255)."""
    text = str(config.get("clear_color") or DEFAULTS["clear_color"])
    if not HEX.match(text):
        text = DEFAULTS["clear_color"]
    return {"r": int(text[1:3], 16), "g": int(text[3:5], 16), "b": int(text[5:7], 16)}


def _state():
    from app.state_manager import state
    return state


@router.get("/api/defaults")
async def api_get() -> JSONResponse:
    return JSONResponse({"config": dict(_state().console_defaults), "defaults": dict(DEFAULTS)})


@router.post("/api/defaults")
async def api_set(request: Request) -> JSONResponse:
    from app import remote                                            # erst hier: remote importiert den Zustand, der dieses Modul braucht
    try:
        body = await request.json()
    except ValueError:
        body = {}
    state = _state()
    state.console_defaults = normalize(body, state.console_defaults)
    state.save_app_config()
    from app import server                                            # erst hier: server importiert dieses Modul
    await server.event_bus.broadcast({"type": "console_defaults_changed", "payload": dict(state.console_defaults)})
    return JSONResponse({"ok": True, "config": dict(state.console_defaults)})
