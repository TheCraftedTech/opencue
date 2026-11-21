# Copyright (C) 2026 Samuel Zenker
# SPDX-License-Identifier: GPL-3.0-or-later
"""
hotkeys.py
Eigene Tastaturbelegung: Eine Taste oder Tastenkombination (z. B. "Ctrl+H", "Space", "Num1") loest einen Befehl der Befehlszeile aus.

Die Liste gehoert dem Programm (nicht der Show): sie steht in der App-Config und gilt auf allen Geraeten, an denen eine Tastatur haengt (auch ein iPad mit
Tastatur). Aufgenommen und ausgeloest wird im Browser (static/js/hotkeys.js); der Server prueft und speichert die Liste nur und verteilt sie (WS `set_hotkeys`
-> `hotkeys_changed`). Ein Eintrag:

    {id, enabled, keys, command, run, log, device, device_name}

* keys     - die Taste; Modifikatoren in der Reihenfolge Ctrl, Alt, Shift, Meta, dann die Taste ("Ctrl+Shift+F5", "A", "Num1", "Space").
* run      - true: der Befehl wird direkt ausgefuehrt; false: er wird nur in die Befehlszeile geschrieben.
* log      - true: der Befehl erscheint im Verlauf der Befehlszeile.
* device   - "" = jede Tastatur (der Browser loest aus); sonst der Modell-Schluessel einer bestimmten Tastatur (app/rawkeys.py loest aus, nur Windows),
             device_name = ihr Anzeigename (nur zur Anzeige).
* keys     - Kombinationen koennen mehrere Haupttasten haben ("Ctrl+H+J"): die Haupttasten stehen alphabetisch sortiert.
"""

from __future__ import annotations

import re
import uuid
from typing import Any, Dict, List

MAX_HOTKEYS = 500
MAX_COMMAND_LENGTH = 1000
_KEYS = re.compile(r"^[A-Za-z0-9+\-=\[\]\\;',./`<*]{1,60}$")
_DEVICE = re.compile(r"^[A-Za-z0-9&_#.{}\- ]{1,160}$")


# ---- Eingebaute Tastenkuerzel des Programms (Strg+S, F11 ...): der Nutzer kann sie umbelegen oder abschalten ("Tastenkuerzel" -> Bearbeiten). Die Standardtasten und die
# Ausfuehrung stehen im Browser (static/js/shortcuts.js); der Server kennt nur die Kennungen, prueft die Eingabe und speichert sie in der App-Config.
BUILTIN_ACTIONS = ("new", "open", "save", "save_as", "exit", "help", "fullscreen", "scale_up", "scale_down", "scale_reset", "cmd_window", "edit_mode", "undo", "redo", "language", "file_manager", "lock", "reload_layout", "reload_ui")


def normalize_overrides(raw: Any) -> Dict[str, str]:
    """{Kennung: Tastenkombination}: nur bekannte Kennungen; "" = Kuerzel abgeschaltet; ungueltige Kombinationen werden verworfen (die Standardtaste gilt dann weiter)."""
    out: Dict[str, str] = {}
    if not isinstance(raw, dict):
        return out
    for action in BUILTIN_ACTIONS:
        if action not in raw:
            continue
        keys = str(raw[action] if raw[action] is not None else "").strip()
        if keys == "" or _KEYS.match(keys):
            out[action] = keys
    seen = set()
    for action in BUILTIN_ACTIONS:                                      # zwei Aktionen mit derselben Taste: die spaetere in der Liste verliert (bleibt ohne Taste)
        keys = out.get(action)
        if keys:
            if keys in seen:
                out[action] = ""
            seen.add(keys)
    return out


def normalize(raw: Any) -> List[Dict[str, Any]]:
    """Bereinigt die Liste vom Client: nur bekannte Felder, begrenzte Laengen, eindeutige Ids. Unbrauchbares wird weggelassen."""
    out: List[Dict[str, Any]] = []
    seen = set()
    if not isinstance(raw, list):
        return out
    for item in raw[:MAX_HOTKEYS]:
        if not isinstance(item, dict):
            continue
        keys = str(item.get("keys", "")).strip()
        if keys and not _KEYS.match(keys):
            keys = ""
        command = " ".join(str(item.get("command", "")).split())[:MAX_COMMAND_LENGTH]
        device = str(item.get("device", "")).strip()
        if not _DEVICE.match(device):
            device = ""
        device_name = " ".join(str(item.get("device_name", "")).split())[:120] if device else ""
        key_id = str(item.get("id", "")).strip()[:40]
        if not key_id or key_id in seen:
            key_id = uuid.uuid4().hex[:12]
        seen.add(key_id)
        out.append({
            "id": key_id,
            "enabled": item.get("enabled", True) is not False,
            "keys": keys,
            "command": command,
            "run": item.get("run", True) is not False,
            "log": item.get("log", True) is not False,
            "device": device,
            "device_name": device_name,
        })
    return out
