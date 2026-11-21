# Copyright (C) 2026 Samuel Zenker
# SPDX-License-Identifier: GPL-3.0-or-later
"""Welche Scheinwerfer meint die KI? Eine Angabe wie "all", "1-5", "1, 3, 7", "1-3 + 7", der Name einer Gruppe oder eines Scheinwerfers wird zu einer Liste von Scheinwerfern -
fuer das Lesen (`read_fixtures`) und das Aendern (`set_fixtures`). Fehler sagen, was es gibt, damit die KI es korrigieren kann."""
from __future__ import annotations

import re
from typing import Any, List, Optional, Tuple

ALL_WORDS = {"all", "alle", "alles", "everything", "every", "*", "all fixtures", "alle scheinwerfer", "all lights", "alle lampen", "alle geräte", "alle geraete", "every fixture"}
RANGE = re.compile(r"^(\d{1,5})\s*(?:-|–|—|bis|thru|through|to)\s*(\d{1,5})$", re.IGNORECASE)
NUMBERS = re.compile(r"^\d{1,5}(?:\s+\d{1,5})+$")
GROUP_WORD = re.compile(r"^(?:(?:the\s+)?(?:groups?|gruppen?)\s+(.+?)|(.+?)\s+(?:groups?|gruppe))$", re.IGNORECASE)         # "Group Wash" / "Gruppe Front" / "Wash group": ein Modell schreibt das Wort mit
PREFIX = re.compile(r"^(?:fixtures?|scheinwerfer|geräte|geraete|lampen?|lights?|fid|nr\.?|no\.?|nummer|number|#)\s*", re.IGNORECASE)
SPLIT = re.compile(r"\s*(?:,|;|\+|&|\bund\b|\band\b)\s*", re.IGNORECASE)
MAX_RANGE = 2000


def as_text(value: Any) -> str:
    """Die Angabe der KI als Text: auch eine Zahl oder eine Liste ([1, 2, 3]) ist erlaubt."""
    if value is None or isinstance(value, bool):
        return ""
    if isinstance(value, (list, tuple, set)):
        return ", ".join(as_text(v) for v in value)
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def fid_text(fids: List[int]) -> str:
    """[1, 2, 3, 5] -> "1-3, 5"."""
    out: List[str] = []
    ordered = sorted(set(fids))
    i = 0
    while i < len(ordered):
        j = i
        while j + 1 < len(ordered) and ordered[j + 1] == ordered[j] + 1:
            j += 1
        out.append(str(ordered[i]) if i == j else f"{ordered[i]}-{ordered[j]}" if j > i + 1 else f"{ordered[i]}, {ordered[j]}")
        i = j + 1
    return ", ".join(out)


def _existing(state) -> str:
    fids = [f.fid for f in state.fixtures.values() if f.fid]
    return f"The show has fixtures {fid_text(fids)}." if fids else "The show has no numbered fixtures."


def resolve(spec: Any, state, notes: Optional[List[str]] = None) -> Tuple[List[Any], Optional[str]]:
    """(Scheinwerfer sortiert nach Nummer, Fehlertext). Fehler: eine Zahl, die es nicht gibt, ein unbekannter Name, eine leere Angabe.
    Mit `notes` (eine Liste) ist eine fehlende Nummer KEIN Fehler, solange mindestens ein Scheinwerfer uebrig bleibt: der Hinweis kommt in die Liste ('6, 11' bei 10 Scheinwerfern -> Nummer 6 und ein Hinweis)."""
    text = as_text(spec)
    if not text:
        return [], "Say which fixtures: \"all\", a range such as \"1-5\", numbers such as \"1, 3, 7\" or the name of a group."
    everyone = sorted(state.fixtures.values(), key=lambda f: (f.fid if f.fid else 10 ** 9, f.start_channel))
    if not everyone:
        return [], "The show has no fixtures."
    if text.lower() in ALL_WORDS:
        return everyone, None
    by_fid: dict = {}
    for fx in everyone:
        if fx.fid:
            by_fid.setdefault(int(fx.fid), []).append(fx)
    picked: dict = {}
    missing: List[int] = []
    unknown: List[str] = []

    def take_fid(number: int) -> None:
        if number in by_fid:
            for fx in by_fid[number]:
                picked[fx.id] = fx
        elif number not in missing:
            missing.append(number)

    for part in SPLIT.split(text):
        part = part.strip().strip('"\'')
        low = part.lower()
        if low in ALL_WORDS:
            return everyone, None
        group = next((ids for name, ids in state.groups.items() if name.strip().lower() == low), None)       # zuerst Namen (eine Gruppe darf "Scheinwerfer hinten" heissen)
        if group is not None:
            for fixture_id in group:
                if fixture_id in state.fixtures:
                    picked[fixture_id] = state.fixtures[fixture_id]
            continue
        named = [fx for fx in everyone if fx.name.strip().lower() == low]
        if named:
            for fx in named:
                picked[fx.id] = fx
            continue
        worded = GROUP_WORD.match(part)
        if worded:
            wanted = (worded.group(1) or worded.group(2) or "").strip().strip('"\'').lower()
            group = next((ids for name, ids in state.groups.items() if name.strip().lower() == wanted), None)
            if group is not None:
                for fixture_id in group:
                    if fixture_id in state.fixtures:
                        picked[fixture_id] = state.fixtures[fixture_id]
                continue
        part = PREFIX.sub("", part).strip()                          # "Scheinwerfer 3" / "fixture 3" / "#3" -> "3"
        if not part:
            continue
        found = RANGE.match(part)
        if found:
            low_n, high_n = sorted((int(found.group(1)), int(found.group(2))))
            if high_n - low_n > MAX_RANGE:
                return [], "That range is far too large."
            for number in range(low_n, high_n + 1):
                if number in by_fid:
                    take_fid(number)                                     # Luecken im Bereich (1-5, aber 3 fehlt) sind kein Fehler
            if not any(n in by_fid for n in range(low_n, high_n + 1)):
                missing.extend(n for n in (low_n, high_n) if n not in missing)
            continue
        if part.isdigit():
            take_fid(int(part))
            continue
        if NUMBERS.match(part):
            for number in part.split():
                take_fid(int(number))
            continue
        unknown.append(part)
    if unknown:
        groups = ", ".join(f'"{name}"' for name in list(state.groups)[:12]) or "(none)"
        return [], f"I do not know '{', '.join(unknown)}'. Use fixture numbers, a range such as \"1-5\", \"all\", or the name of a group. Groups: {groups}. {_existing(state)}"
    if missing:
        problem = f"There is no fixture with the number {', '.join(str(n) for n in sorted(missing))}. {_existing(state)} Tell the user; do not use a different fixture instead."
        if notes is None or not picked:
            return [], problem
        notes.append(problem.replace(" Tell the user; do not use a different fixture instead.", "") + " It was left out - tell the user.")
    if not picked:
        return [], "No fixture matches. " + _existing(state)
    return sorted(picked.values(), key=lambda f: (f.fid if f.fid else 10 ** 9, f.start_channel)), None


def command_clause(fixtures: List[Any]) -> str:
    """Die Auswahl im Befehl der Kommandozeile: 'Fixture 1 Thru 5 + 7' (Scheinwerfer ohne Nummer ueber ihren Namen)."""
    fids = sorted({int(f.fid) for f in fixtures if f.fid})
    parts: List[str] = []
    i = 0
    while i < len(fids):
        j = i
        while j + 1 < len(fids) and fids[j + 1] == fids[j] + 1:
            j += 1
        parts.append(str(fids[i]) if j == i else f"{fids[i]} Thru {fids[j]}" if j > i + 1 else f"{fids[i]} + {fids[j]}")
        i = j + 1
    for fx in fixtures:
        if not fx.fid and '"' not in fx.name:
            parts.append(f'"{fx.name}"')
    return "Fixture " + " + ".join(parts)
