# Copyright (C) 2026 Samuel Zenker
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Uhrzeit-Hilfen fuer den Zeitplan und den Cue-Ausloeser "Uhrzeit" (clock): Uhrzeit und Wochentage lesen, anzeigen und pruefen, ob eine Uhrzeit zwischen zwei Zeitpunkten liegt.

  Uhrzeit:     "19:30", "19:30:15", "7:05", "1930", "19.30" -> "19:30" / "19:30:15" (Sekunden nur, wenn sie nicht 0 sind); ungueltig -> None.
  Wochentage:  Liste 0-6 (Montag = 0), leer = jeden Tag. Eingabe auch als Text: "mon-fri", "sat,sun", "weekdays", "weekend", "daily", "Mo-Fr", "Sa,So".
  crossed():   liegt eine Ausfuehrung in (prev, now]? Der Zeitplan fragt das alle halbe Sekunde; so feuert jede Uhrzeit genau einmal, auch ueber Mitternacht, und eine Systemuhr, die springt,
               loest keine Flut aus (grosse Spruenge wertet der Aufrufer als "verpasst").
"""
from __future__ import annotations

import datetime as _dt
import re
from typing import Any, List, Optional

DAY_NAMES = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
_DAY_ALIASES = {"mon": 0, "monday": 0, "mo": 0, "montag": 0, "tue": 1, "tuesday": 1, "tu": 1, "di": 1, "dienstag": 1, "wed": 2, "wednesday": 2, "mi": 2, "mittwoch": 2,
                "thu": 3, "thursday": 3, "th": 3, "do": 3, "donnerstag": 3, "fri": 4, "friday": 4, "fr": 4, "freitag": 4, "sat": 5, "saturday": 5, "sa": 5, "samstag": 5,
                "sun": 6, "sunday": 6, "su": 6, "so": 6, "sonntag": 6}
_GROUPS = {"daily": [], "everyday": [], "all": [], "taeglich": [], "täglich": [], "weekdays": [0, 1, 2, 3, 4], "workdays": [0, 1, 2, 3, 4], "werktags": [0, 1, 2, 3, 4],
           "weekend": [5, 6], "weekends": [5, 6], "wochenende": [5, 6]}
_TIME = re.compile(r"^(\d{1,2})[:.]?(\d{2})(?:[:.](\d{2}))?$")
_DATE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")


def clean_time(value: Any) -> Optional[str]:
    """Uhrzeit als "HH:MM" oder "HH:MM:SS" (Sekunden nur, wenn nicht 0); None, wenn keine gueltige Uhrzeit."""
    match = _TIME.match(str(value if value is not None else "").strip())
    if not match:
        return None
    hour, minute, second = int(match.group(1)), int(match.group(2)), int(match.group(3) or 0)
    if hour > 23 or minute > 59 or second > 59:
        return None
    return f"{hour:02d}:{minute:02d}" + (f":{second:02d}" if second else "")


def clean_days(value: Any) -> List[int]:
    """Wochentage (Montag = 0) als sortierte Liste; leer = jeden Tag. Nimmt Listen, Zahlen und Text ("Mon-Fri", "Sa,So", "weekdays")."""
    if value is None or value == "":
        return []
    days = set()
    if isinstance(value, (list, tuple, set)):
        for item in value:
            if isinstance(item, bool):
                continue
            if isinstance(item, (int, float)) and 0 <= int(item) <= 6:
                days.add(int(item))
            elif isinstance(item, str):
                days.update(clean_days(item))
        return [] if len(days) == 7 else sorted(days)
    text = str(value).strip().lower()
    if text in _GROUPS:
        return list(_GROUPS[text])
    for part in re.split(r"[,;\s]+", text):
        if not part:
            continue
        if part in _GROUPS:
            days.update(_GROUPS[part])
        elif "-" in part:
            low, _, high = part.partition("-")
            if low in _DAY_ALIASES and high in _DAY_ALIASES:
                a, b = _DAY_ALIASES[low], _DAY_ALIASES[high]
                days.update(range(a, b + 1) if a <= b else list(range(a, 7)) + list(range(0, b + 1)))
        elif part in _DAY_ALIASES:
            days.add(_DAY_ALIASES[part])
        elif part.isdigit() and 0 <= int(part) <= 6:
            days.add(int(part))
    return [] if len(days) == 7 else sorted(days)


def clean_date(value: Any) -> str:
    """Einmaliges Datum "JJJJ-MM-TT" (gueltig) oder ""."""
    match = _DATE.match(str(value if value is not None else "").strip())
    if not match:
        return ""
    try:
        _dt.date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
    except ValueError:
        return ""
    return match.group(0)


def days_label(days: List[int]) -> str:
    """"daily", "Mon-Fri", "Sat, Sun", "Mon, Wed, Fri" - fuer die Anzeige."""
    if not days:
        return "daily"
    if days == [0, 1, 2, 3, 4]:
        return "Mon-Fri"
    if days == [5, 6]:
        return "Sat, Sun"
    runs, start = [], days[0]
    for i, day in enumerate(days):
        if i + 1 == len(days) or days[i + 1] != day + 1:
            runs.append((start, day))
            if i + 1 < len(days):
                start = days[i + 1]
    return ", ".join(DAY_NAMES[a] if a == b else (DAY_NAMES[a] + "-" + DAY_NAMES[b] if b > a + 1 else DAY_NAMES[a] + ", " + DAY_NAMES[b]) for a, b in runs)


def label(time_text: str, days: List[int], date: str = "") -> str:
    """"19:30 (Mon-Fri)", "19:30 (daily)", "19:30 on 2026-12-24"."""
    return f"{time_text} on {date}" if date else f"{time_text} ({days_label(days)})"


def _time_of(time_text: str) -> _dt.time:
    parts = [int(x) for x in time_text.split(":")]
    return _dt.time(parts[0], parts[1], parts[2] if len(parts) > 2 else 0)


def crossed(time_text: str, days: List[int], date: str, prev: _dt.datetime, now: _dt.datetime) -> bool:
    """Liegt eine Ausfuehrung dieser Uhrzeit (an den Wochentagen bzw. dem einen Datum) in (prev, now]?"""
    if not time_text or now <= prev:
        return False
    when = _time_of(time_text)
    day = prev.date()
    while day <= now.date():
        if (date and day.isoformat() == date) or (not date and (not days or day.weekday() in days)):
            moment = _dt.datetime.combine(day, when)
            if prev < moment <= now:
                return True
        day += _dt.timedelta(days=1)
    return False


def next_run(time_text: str, days: List[int], date: str, now: _dt.datetime) -> Optional[_dt.datetime]:
    """Naechste Ausfuehrung nach `now` (fuer die Anzeige "naechster Start"); None, wenn es keine mehr gibt (einmaliges Datum in der Vergangenheit)."""
    if not time_text:
        return None
    when = _time_of(time_text)
    if date:
        moment = _dt.datetime.combine(_dt.date.fromisoformat(date), when)
        return moment if moment > now else None
    for offset in range(0, 9):
        day = now.date() + _dt.timedelta(days=offset)
        if days and day.weekday() not in days:
            continue
        moment = _dt.datetime.combine(day, when)
        if moment > now:
            return moment
    return None
