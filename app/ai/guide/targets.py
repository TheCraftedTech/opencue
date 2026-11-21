# Copyright (C) 2026 Samuel Zenker
# SPDX-License-Identifier: GPL-3.0-or-later
"""Dialoge und Landkarte des Wegweisers. Beschriftungen und Menuepfade werden zur Laufzeit aus den Sprachdateien (static/locales) gebaut - so stimmen sie immer mit der Oberflaeche
ueberein (die KI darf keine Menuepunkte erfinden). Die Dialoge stehen in static/help/guide/targets.json, die Landkarte in landmap.json."""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple

from app.ai.guide import snippets
from app import languages, paths

_data: Dict[str, Any] = {}
_locales: Dict[str, Dict[str, str]] = {}
ARROW = " → "


def _json(name: str) -> Dict[str, Any]:
    try:
        return json.loads((snippets.folder() / name).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def frame(lang: str) -> str:
    """Sprache der Rahmentexte, Stichwoerter und Beschreibungen (Anleitungen gibt es auf Deutsch und Englisch); die BESCHRIFTUNGEN der Oberflaeche kommen immer in der gewaehlten Sprache."""
    return "de" if lang == "de" else "en"


def locale(lang: str) -> Dict[str, str]:
    return languages.locale(lang)


def text_of(key: str, lang: str) -> str:
    """Eine Beschriftung der Oberflaeche ohne die '...' am Ende (Menuepunkte heissen 'Show oeffnen...')."""
    value = locale(lang).get(key) or locale("en").get(key) or key
    return str(value).rstrip(".").rstrip("…").strip() if str(value).endswith(("...", "…")) else str(value)


def targets() -> List[Dict[str, Any]]:
    if "targets" not in _data:
        _data["targets"] = [t for t in _json("targets.json").get("targets", []) if isinstance(t, dict) and t.get("id")]
    return _data["targets"]


def get(target_id: str) -> Optional[Dict[str, Any]]:
    return next((t for t in targets() if t["id"] == target_id), None)


def path_of(target: Dict[str, Any], lang: str) -> str:
    """'Bibliothek → Shows' (aus den Schluesseln der Sprachdatei)."""
    return ARROW.join(text_of(key, lang) for key in target.get("path", []))


def describe(target: Dict[str, Any], lang: str) -> Dict[str, Any]:
    return {"id": target["id"], "label": path_of(target, lang), "kind": target.get("kind", "dialog"), "click": target.get("click", {}), "about": (target.get("about") or {}).get(frame(lang), "")}


def resolve(query: Any, lang: str) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, Any]]]:
    """(Ziel, Kandidaten): genau eine Id (auch 'Settings/Appearance') -> das Ziel; sonst die Stichwoerter und Beschriftungen vergleichen. Ist nichts eindeutig, kommen die besten Kandidaten zurueck."""
    text = " ".join(str(query or "").lower().split())
    if not text:
        return None, []
    direct = get(text.replace("/", ":").replace(" ", "-")) or get(text)
    if direct:
        return direct, []
    scored: List[Tuple[int, Dict[str, Any]]] = []
    for t in targets():
        words = [w.lower() for w in (t.get("keywords") or {}).get(frame(lang), [])] + [w.lower() for w in (t.get("keywords") or {}).get("en", [])]
        label = path_of(t, lang).lower()
        s = 0
        for w in words:
            if w and (w == text or w in text):
                s += 3 + len(w.split())
        if label and (label in text or text in label):
            s += 5
        for part in label.split(ARROW.strip()):
            part = part.strip()
            if part and len(part) > 3 and part in text:
                s += 2
        if s:
            scored.append((s, t))
    scored.sort(key=lambda item: -item[0])
    if scored and (len(scored) == 1 or scored[0][0] > scored[1][0]):
        return scored[0][1], []
    return None, [t for _, t in scored[:4]]


def search(question: str, lang: str, limit: int = 2) -> List[Dict[str, Any]]:
    """Dialoge, die zur Frage passen (damit die KI eine Schaltflaeche anbieten kann)."""
    low = question.lower()
    found: List[Tuple[int, Dict[str, Any]]] = []
    for t in targets():
        hits = sum(1 for w in (t.get("keywords") or {}).get(frame(lang), []) if w and w.lower() in low)
        if hits:
            found.append((hits, t))
    found.sort(key=lambda item: -item[0])
    return [t for _, t in found[:limit]]


def landmap(lang: str) -> str:
    """Die Landkarte fuer den System-Prompt: Menues mit ihren Punkten, Einstellungs-Kategorien und Panels - alles aus den Beschriftungen der Oberflaeche."""
    de = frame(lang) == "de"
    data = _json("landmap.json")
    lines: List[str] = []
    menus = [f"{text_of(m['menu'], lang)} ({', '.join(text_of(k, lang) for k in m.get('items', []))})" for m in data.get("menus", [])]
    lines.append(("Menüs oben links: " if de else "Menus at the top left: ") + "; ".join(menus))
    lines.append(("Einstellungen (Zahnrad oben rechts): " if de else "Settings (gear at the top right): ") + ", ".join(text_of(k, lang) for k in data.get("settings", [])))
    lines.append(("Panels (Bearbeiten → Panel hinzufügen…): " if de else "Panels (Edit → Add Panel...): ") + ", ".join(text_of(k, lang) for k in data.get("panels", [])))
    return "\n".join(lines)
