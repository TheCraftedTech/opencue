# Copyright (C) 2026 Samuel Zenker
# SPDX-License-Identifier: GPL-3.0-or-later
"""
voice_commands.py
Sprachbefehle: aus dem, was Whisper verstanden hat (ENGLISCH), wird eine Zeile der Befehlszeile - ohne KI, nach festen Regeln.

    "OpenCue, fixture five at seventy nine, color green."   ->   Fixture 5 At 79 Color Green
    "open cue blackout on"                                   ->   Blackout On
    "fixtures one true five add fifty percent"              ->   Fixture 1 Thru 5 At 50%        ("true" = Thru, "add" = At: haeufige Hoerfehler)

Was passiert (alles in `interpret`):
  1. Weckwort am Anfang entfernen (auch klangverwandte Schreibweisen: "open queue", "open Q", "OpenCue").
  2. Mehrwort-Ausdruecke zusammenfassen ("black out", "time code", "cue list", "go bo", "beats per minute" ...).
  3. Zahlwoerter -> Ziffern ("seventy nine" -> 79, "two point five" -> 2.5, "minus ten" -> -10, "fifty percent" -> 50%).
  4. Woerter -> Schluesselwoerter der Befehlszeile, in dieser Reihenfolge:
       - ZAHL-PLAETZE: wo eine Zahl stehen muss, sind "to / too / for / won / ate / tree" Zahlen ("fixture for at fifty" -> Fixture 4 At 50);
       - Synonyme ("light" -> Fixture, "brightness" -> At, "through" -> Thru);
       - typische HOERFEHLER mit Blick auf die Stelle im Befehl ("add / ad" -> At, "true / threw" -> Thru, "picture" -> Fixture, "collar" -> Color, "pen / ban" vor einer Zahl -> Pan);
       - Klang-Schluessel (`pkey`): ein unbekanntes Wort, das an einer Stelle steht, wo ein bestimmtes Schluesselwort stehen muss, und genauso klingt, wird dieses Wort;
       - Farben auf die Farben der Befehlszeile ("grin" -> Green); ein Farbname ohne "Color" bekommt das Wort;
       - kleine Schreibfehler -> aehnlichstes Schluesselwort ("blakout" -> Blackout).
     Namen (nach Group / Cuelist / Effect / Variable) bleiben unveraendert; mehrere Namenswoerter werden zusammen in Anfuehrungszeichen gesetzt.
  5. Kleine Abkuerzungen: "fixture 5 off" -> At 0, "fixture 5 on" / "out" -> At Full / At 0, "home / center" -> Pan 50% Tilt 50%.
  6. Muss mit einem Befehlswort beginnen (Vorgeplaenkel davor wird verworfen); gefaehrliche Befehle (Loeschen, Clear Clear, Overwrite) werden NICHT per Sprache ausgefuehrt.
Reine Rechnung ohne Server und Mikrofon - dadurch einzeln pruefbar. Die Befehlszeile selbst (app/command_line.py) prueft den Befehl danach noch einmal und meldet, was nicht passt.
`interpret` liefert ausser dem Befehl auch `notes`: jede Korrektur ("add -> At"), damit man sieht, was automatisch geaendert wurde.
"""
from __future__ import annotations

import difflib
import re
from typing import Any, Dict, List, Optional, Set

UNITS = {"zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13,
         "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19}
TENS = {"twenty": 20, "thirty": 30, "forty": 40, "fourty": 40, "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90}
SLOT_NUMBERS = {"won": 1, "wan": 1, "wun": 1, "to": 2, "too": 2, "tu": 2, "tree": 3, "free": 3, "for": 4, "fore": 4, "fife": 5, "sex": 6, "sicks": 6, "ate": 8, "niner": 9, "nein": 9,
                "oh": 0}      # nur dort, wo eine Zahl stehen muss

COLORS = ["red", "green", "blue", "white", "black", "yellow", "cyan", "magenta", "orange", "pink", "purple", "amber", "lime", "teal", "violet", "lightblue", "warm", "cool"]
COLOR_ALIASES = {"read": "red", "bred": "red", "rid": "red", "ride": "red", "ret": "red", "grin": "green", "greene": "green", "grain": "green", "screen": "green", "blew": "blue", "blu": "blue",
                 "bloom": "blue", "wight": "white", "wait": "white", "wide": "white", "right": "white", "whites": "white", "yello": "yellow", "yell": "yellow", "sign": "cyan", "sigh": "cyan",
                 "sayan": "cyan", "science": "cyan", "maroon": "red", "gold": "amber", "golden": "amber", "ember": "amber", "violent": "violet", "lila": "violet", "indigo": "violet",
                 "turquoise": "cyan", "aqua": "cyan", "pinkish": "pink", "mint": "lime", "till": "teal", "lightblue": "lightblue", "cold": "cool"}

# gesprochenes Wort -> Schluesselwort der Befehlszeile
WORDS = {
    "fixture": "Fixture", "fixtures": "Fixture", "fix": "Fixture", "light": "Fixture", "lights": "Fixture", "lamp": "Fixture", "lamps": "Fixture", "spot": "Fixture", "spots": "Fixture",
    "group": "Group", "groups": "Group",
    "at": "At", "dimmer": "At", "brightness": "At", "intensity": "At", "level": "At", "full": "Full", "half": "Half", "out": "Out",
    "thru": "Thru", "through": "Thru", "until": "Thru",
    "color": "Color", "colour": "Color", "rgb": "RGB",
    "pan": "Pan", "tilt": "Tilt", "zoom": "Zoom", "focus": "Focus", "gobo": "Gobo", "gobospin": "GoboSpin", "prism": "Prism", "strobe": "Strobe", "shutter": "Strobe",
    "master": "Master", "blackout": "Blackout", "on": "On", "off": "Off",
    "go": "Go", "next": "Go", "back": "Back", "previous": "Back", "pause": "Pause", "resume": "Resume", "stop": "Stop", "play": "Play", "reverse": "Reverse", "reset": "Reset",
    "cuelist": "Cuelist", "qlist": "Cuelist", "cue": "Cue", "queue": "Cue", "q": "Cue", "que": "Cue", "kew": "Cue", "cu": "Cue", "goto": "Goto", "exec": "Cuelist",
    "clear": "Clear", "effect": "Effect", "variable": "Variable", "manual": "Manual", "timecode": "Timecode", "tap": "Tap", "bpm": "BPM", "fader": "Fader", "audio": "Audio",
    "update": "Update", "store": "Store", "label": "Label", "delete": "Delete", "rate": "Rate", "start": "Start", "min": "Min", "minimum": "Min", "maximum": "Full",
    "merge": "Merge", "overwrite": "Overwrite", "absolute": "Absolute", "tracking": "Tracking", "demo": "Demo", "auto": "Auto", "double": "Double", "plus": "+", "minus": "-",
    "channel": "Channel", "ch": "CH", "fade": "Fade", "delay": "Delay", "home": "Home", "center": "Home", "centre": "Home", "duplicate": "Duplicate", "rename": "Rename", "new": "New",
    "nextfixture": "Next", "prevfixture": "Previous", "midi": "Midi", "note": "Note", "panic": "Panic", "cc": "CC", "pc": "PC",
}
NAME_TAKERS = {"Group", "Cuelist", "Effect", "Variable", "Label", "Store"}                    # danach folgt ein NAME (bleibt unveraendert)
CANON = set(WORDS.values()) | {c.capitalize() for c in COLORS}
HEADS = {"Fixture", "Group", "At", "Full", "Master", "Blackout", "Color", "RGB", "Pan", "Tilt", "Zoom", "Focus", "Gobo", "GoboSpin", "Prism", "Strobe", "Go", "Back", "Pause", "Resume", "Stop",
         "Cuelist", "Cue", "Clear", "Effect", "Variable", "Manual", "Timecode", "Tap", "BPM", "Fader", "Audio", "Update", "Store", "Goto", "Off", "Label", "Delete", "Channel", "CH", "Home", "Out", "Next", "Previous", "Midi"}
FILLERS = {"um", "uh", "uhm", "umm", "er", "erm", "ah", "eh", "hmm", "mm", "please", "the", "a", "an", "now", "just", "okay", "ok", "hey", "so", "well", "like", "kindly", "and", "to", "of",
           "set", "make", "turn", "put", "switch", "give", "me", "my", "is", "it", "that", "this", "for", "with", "all", "then", "select", "choose", "pick", "run", "execute", "do", "apply", "toggle", "command"}
PHRASES = [                                                    # mehrere Woerter -> ein Wort (vor der Zerlegung)
    (r"\bnext[\s-]+(?:fixture|light|lamp|spot)s?\b", "nextfixture"), (r"\b(?:previous|last|prev)[\s-]+(?:fixture|light|lamp|spot)s?\b", "prevfixture"),
    (r"\b(?:except|excluding|without|but[\s-]+not)\b", "minus"),
    (r"\bblack[\s-]+out\b", "blackout"), (r"\bblack[\s-]+art\b", "blackout"), (r"\bcue[\s-]+list\b", "cuelist"), (r"\bq[\s-]+list\b", "cuelist"), (r"\bqueue[\s-]+list\b", "cuelist"),
    (r"\bque[\s-]+list\b", "cuelist"), (r"\bgrand[\s-]+master\b", "master"), (r"\btime[\s-]+code\b", "timecode"), (r"\bgo[\s-]+back\b", "back"), (r"\bsound[\s-]+to[\s-]+light\b", "audio"),
    (r"\bnext[\s-]+(?:cue|queue)\b", "go"), (r"\b(?:previous|last)[\s-]+(?:cue|queue)\b", "back"), (r"\bgo[\s-]+(?:bo|boh|bow|beau)\b", "gobo"), (r"\bgobo[\s-]+spin\b", "gobospin"),
    (r"\bb[\s.-]*p[\s.-]*m\b", "bpm"), (r"\bbeats?[\s-]+per[\s-]+minute\b", "bpm"), (r"\bper[\s-]*cent\b", "percent"), (r"\bpercentage\b", "percent"), (r"\bdegrees?\b", ""),
    (r"\bgo[\s-]+to\b", "go"), (r"\bturn[\s-]+off\b", "off"), (r"\bturn[\s-]+on\b", "on"), (r"\bswitch[\s-]+off\b", "off"), (r"\bswitch[\s-]+on\b", "on"),
    (r"\b(?:everything|all(?:\s+(?:the\s+)?(?:lights?|fixtures?|lamps?))?)\s+on\b", "at at"), (r"\bfix[\s-]*(?:sure|chur|ture|tour)s?\b", "fixture"), (r"\bfull[\s-]+on\b", "full"), (r"\bcolou?rs?\b", "color"),
]
# typische Hoerfehler: Wort -> Schluesselwort. Gilt ueberall ausser an Namensstellen; "when" = nur wenn die Bedingung stimmt (siehe `_ctx`)
ALWAYS = {
    "At": ["add", "ad", "@", "att", "ats", "app"],
    "Thru": ["true", "threw", "thrue", "thro", "drew", "trew", "thrú", "truth", "throu"],
    "Full": ["fool", "ful", "foul", "fulll"],
    "Fixture": ["picture", "pictures", "pixture", "pitcher", "fixure", "fixer", "fixers", "fixtur", "fixtue", "fixchure", "fixtures"],
    "Color": ["collar", "caller", "colors", "colored", "calor", "kolor", "colur", "culor", "kalor", "colorr"],
    "Blackout": ["blackouts", "blackhat", "blockout", "blackup", "blackhawk", "blackhart"],
    "Master": ["muster", "mastered", "masters", "mustard"],
    "Zoom": ["zoomed", "zoon", "zooms"],
    "Prism": ["prison", "prisons", "prisms", "prisma"],
    "Gobo": ["gobos", "goebo", "gobbo", "gobow"],
    "Strobe": ["strove", "strobing", "strobes", "strope", "stroke", "strub", "stroub", "stroben"],
    "Pause": ["paws", "pours", "pose"],
    "Effect": ["effects", "affect", "affects"],
    "Variable": ["variables", "variabel"],
    "Manual": ["manuel", "manually"],
    "Timecode": ["timecodes", "timecoat"],
    "Tap": ["tab", "tapp", "taps", "tapped"],
    "BPM": ["bmp", "bpms", "bbm"],
    "Fader": ["feeder", "fada", "faders"],
    "Resume": ["resumed", "resumes"],
    "Stop": ["stopped", "stops"],
    "Cuelist": ["coolist", "cuelists", "cuelist", "cuelest", "qlist"],
    "Midi": ["middy", "midie", "midis", "mighty", "meaty"],
    "Channel": ["chanel", "channels", "chanal", "chanell", "chan"],
    "Clear": ["clair", "cleer", "clears", "cleared", "clearing"],
    "Half": ["halve", "halfe", "calf", "halves"],
    "Label": ["labels", "lable", "laber"],
    "Audio": ["audeo", "odio", "ordio", "audi"],
    "Resume": ["rezoom", "reasume", "resum"],
    "Demo": ["deemo", "demos", "dehmo"],
}
NEEDS_NUMBER_NEXT = {                                         # nur wenn dahinter eine Zahl folgt (sonst koennte es ein echtes Wort sein)
    "Pan": ["pen", "pun", "pam", "ban", "bun", "pin", "pann", "pans", "pawn", "pond", "pound", "bahn", "panned"],
    "Tilt": ["till", "tilted", "tilts", "teeth", "tilth", "tell", "tilde", "tilting"],
    "Cue": ["cute", "cube", "key", "kyu", "queue", "hugh", "cubes", "cues", "kew", "kue", "kyoo", "hue"],
    "Fade": ["fate", "faid", "fait", "fades", "faded"],
    "Delay": ["delight", "delayed", "dilay", "delays"],
    "Focus": ["folks", "focuss", "fokus"],
    "Fixture": ["fixed", "fixes", "fig", "fiction"],
    "Group": ["grub", "grouped", "groupe", "croup"],
    "Zoom": ["zoo", "zum", "doom", "soom", "zoomm"],
    "Gobo": ["goebo", "globo"],
    "Master": ["mass", "mast"],
}
BETWEEN_NUMBERS = {"Thru": ["till", "to", "too", "true", "through", "until", "thru"], "At": ["it", "at", "add", "ad", "app"], "+": ["and", "plus", "in", "n"]}
AFTER_ON_OFF_WORD = {"Off": ["of", "off", "awf", "oph"], "On": ["own", "an", "on", "own."]}      # nach Blackout & Co.
BLOCKED = {"delete": "Delete", "overwrite": "Overwrite"}          # nie per Sprache: Loeschen, Ueberschreiben; dazu "Clear Clear" (siehe unten)
MAX_TEXT = 300
NUMBER = re.compile(r"[+-]?\d+(?:\.\d+)?%?")
PLAIN_NUMBER = re.compile(r"\d+(?:\.\d+)?")


# ------------------------------------------------------------------------------------------------ Klang-Schluessel
def pkey(word: str) -> str:
    """Grober Klang-Schluessel: gleich klingende Woerter ergeben denselben Schluessel ("add" und "at": at; "true" und "thru": tr; "collar" und "color": klr). Selbstlaute (ausser am Anfang),
    h / w / y fallen weg, stimmhaft = stimmlos (b/p, d/t, g/k, v/f, z/s), doppelte Buchstaben werden einfach."""
    w = re.sub(r"[^a-z]", "", word.lower())
    for old, new in (("ph", "f"), ("th", "t"), ("ck", "k"), ("kn", "n"), ("wr", "r"), ("wh", "w"), ("ps", "s"), ("gh", ""), ("qu", "k")):
        w = w.replace(old, new)
    w = re.sub(r"c(?=[eiy])", "s", w).replace("c", "k")
    w = w.replace("q", "k").replace("x", "ks").replace("z", "s").replace("v", "f").replace("b", "p").replace("d", "t").replace("g", "k")
    out = ""
    for index, ch in enumerate(w):
        if ch in "aeiou" and index > 0:
            continue
        if ch in "hwy" and index > 0:
            continue
        if out and out[-1] == ch:
            continue
        out += ch
    return out


def _slot_table(words: List[str]) -> Dict[str, str]:
    table: Dict[str, str] = {}
    clash: Set[str] = set()
    for word in words:
        key = pkey(word)
        if key in table and table[key] != word:
            clash.add(key)
        table[key] = word
    return {k: v for k, v in table.items() if k not in clash}


AFTER_NUMBER = _slot_table(["At", "Thru", "Color", "Full", "Half", "Fixture"])                 # nach einer Zahl erwartet
BEFORE_NUMBER = _slot_table(["Fixture", "Group", "Cue", "Pan", "Tilt", "Zoom", "Focus", "Gobo", "Prism", "Strobe", "Master", "Fader", "BPM", "At", "Channel", "Rate"])       # vor einer Zahl erwartet
COLOR_KEYS = _slot_table(COLORS)
KEYWORD_LIST = sorted({w for w in WORDS if len(w) >= 4})


# ------------------------------------------------------------------------------------------------ Weckwort
def _wake_pattern(wake_words: List[str]) -> Optional["re.Pattern[str]"]:
    """Passt auf das Weckwort, wie Whisper es schreiben kann: 'open cue' auch als 'open queue', 'open q', 'opencue', 'okay open cue'."""
    if not wake_words:
        return None
    parts: List[str] = []
    for word in wake_words:
        if word in ("cue", "queue", "q"):
            parts.append(r"(?:cue|queue|que|q|kew|cu|kyu|cute|cube)")
        else:
            parts.append(re.escape(word))
    return re.compile(r"(?:\b(?:ok|okay|hey)[\s,.!-]+)?\b" + r"[\s,.!?-]*".join(parts) + r"\b[\s,.!?:;-]*")


def strip_wake(text: str, wake_words: List[str]) -> str:
    """Alles NACH dem letzten Weckwort im Text (steht keins darin, bleibt der Text, wie er ist)."""
    pattern = _wake_pattern(wake_words)
    if pattern is None:
        return text
    last = None
    for last in pattern.finditer(text):
        pass
    return text[last.end():] if last else text


def _clean(text: str) -> str:
    text = text.lower().replace("’", "'").replace("–", "-").replace("—", "-")
    text = re.sub(r"(\d)\s*%", r"\1 percent", text)                                # 79% -> 79 percent (wird unten wieder zu 79%)
    for pattern, replacement in PHRASES:
        text = re.sub(pattern, replacement, text)
    text = re.sub(r"(?<=[a-z])-(?=[a-z])", " ", text)                              # twenty-one -> twenty one
    text = re.sub(r"(?<=[a-z])-(?=\d)|(?<=\d)-(?=[a-z])", " ", text)               # fixture-5 -> fixture 5
    text = re.sub(r"#(?!(?:[0-9a-f]{6}|[0-9a-f]{3})\b)", " ", text)               # "fixture #5" -> fixture 5 (ein Farbwert wie #ff8800 bleibt)
    text = re.sub(r"[^\w\s.+#%-]", " ", text)                                      # Satzzeichen weg (Punkt, + # % - innerhalb von Zahlen / Farben bleiben)
    text = re.sub(r"\.(?!\d)", " ", text)                                         # Satzpunkte weg ("cue 3." -> "cue 3"); der Punkt in "2.5" bleibt
    text = re.sub(r"\s+", " ", text).strip()
    return text


# ------------------------------------------------------------------------------------------------ Zahlen
def _number_value(tokens: List[str], i: int) -> "tuple[Optional[float], int]":
    """Zahl aus Zahlwoertern ab Position i: (Wert, Anzahl verbrauchter Woerter) oder (None, 0). "seventy nine" -> 79, "one hundred and five" -> 105, "five five" -> nur das erste."""
    n = len(tokens)
    j = i
    current = 0
    seen = False
    last = ""                                                      # "unit" | "tens" | "hundred"
    while j < n:
        tok = tokens[j]
        if tok in UNITS and last != "unit" and not (last == "tens" and UNITS[tok] >= 10) and not (last == "tens" and UNITS[tok] == 0):
            current += UNITS[tok]
            last = "unit"
        elif tok in TENS and last not in ("unit", "tens"):
            current += TENS[tok]
            last = "tens"
        elif tok == "hundred" and last in ("unit", ""):
            current = (current or 1) * 100
            last = "hundred"
        elif tok == "and" and last == "hundred" and j + 1 < n and (tokens[j + 1] in UNITS or tokens[j + 1] in TENS):
            j += 1
            continue
        else:
            break
        seen = True
        j += 1
    return (float(current), j - i) if seen else (None, 0)


def _numbers(tokens: List[str]) -> List[str]:
    """Zahlwoerter -> Ziffern; "point" -> Dezimalpunkt; "percent" -> % an der Zahl; "plus" / "minus" als Vorzeichen. Hinter bpm / rgb / color gilt die Sprechweise
    "one twenty eight" = 128 und "two fifty five" = 255 (Ziffer + Zehnerzahl)."""
    out: List[str] = []
    i = 0
    n = len(tokens)
    triple = False                                                 # hinter bpm / rgb / color: Ziffer + Zehnerzahl zusammenziehen
    while i < n:
        tok = tokens[i]
        if tok in ("bpm", "rgb", "color", "tempo"):
            triple = True
        elif tok not in UNITS and tok not in TENS and tok not in ("hundred", "and", "point", "dot", "percent", "plus", "minus", "negative") and not tok.isdigit():
            triple = False
        value, used = _number_value(tokens, i)
        if value is not None and triple and used == 1 and 1 <= value <= 9:
            more, more_used = _number_value(tokens, i + 1)
            if more is not None and 20 <= more <= 99:
                value, used = value * 100 + more, 1 + more_used
        if value is None and tok in ("point", "dot") and i + 1 < n and (tokens[i + 1] in UNITS or tokens[i + 1].isdigit()):
            value, used = 0.0, 0                                    # ".5"
        if value is not None:
            text = str(int(value)) if value == int(value) else str(value)
            i += used
            if i < n and tokens[i] in ("point", "dot"):             # four point five -> 4.5 (jede Ziffer einzeln)
                digits = ""
                k = i + 1
                while k < n and (tokens[k] in UNITS and UNITS[tokens[k]] < 10 or re.fullmatch(r"\d", tokens[k] or "")):
                    digits += str(UNITS.get(tokens[k], tokens[k]))
                    k += 1
                if digits:
                    text += "." + digits
                    i = k
            out.append(text)
            continue
        out.append(tok)
        i += 1
    merged: List[str] = []
    for tok in out:                                                # plus / minus -> Vorzeichen, percent -> % an die vorige Zahl
        if tok in ("plus", "minus", "negative"):
            tok = "+" if tok == "plus" else "-"
        if tok == "percent" and merged and re.fullmatch(r"[+-]?\d+(?:\.\d+)?", merged[-1]):
            merged[-1] += "%"
        elif PLAIN_NUMBER.fullmatch(tok.rstrip("%")) and merged and merged[-1] in ("+", "-") and (len(merged) == 1 or not NUMBER.fullmatch(merged[-2])):
            merged[-1] += tok
        else:
            merged.append(tok)
    return merged


def _is_num(tok: str) -> bool:
    return bool(tok) and bool(NUMBER.fullmatch(tok))


# ------------------------------------------------------------------------------------------------ Woerter -> Schluesselwoerter
def _closest(word: str, choices: List[str], cutoff: float) -> Optional[str]:
    found = difflib.get_close_matches(word, choices, n=1, cutoff=cutoff)
    return found[0] if found else None


def _color(word: str) -> Optional[str]:
    if word in COLORS:
        return word
    if word in COLOR_ALIASES:
        return COLOR_ALIASES[word]
    if len(word) >= 3 and pkey(word) in COLOR_KEYS:
        return COLOR_KEYS[pkey(word)]
    return _closest(word, COLORS, 0.72) if len(word) >= 3 else None


class _Name(str):
    """Ein Wort, das zu einem NAMEN gehoert (Gruppe, Cue-Liste, Effekt ...): wird nicht korrigiert, nicht als Fuellwort entfernt."""


NO_PERCENT = {"Master", "Fader", "BPM", "Rate", "Cue", "Goto", "Go", "Delay", "Fade"}
NAME_END = {"at", "full", "half", "thru", "through", "until", "color", "colour", "go", "back", "pause", "resume", "stop", "on", "off", "fader", "rate", "fade", "delay", "rename", "duplicate",
            "delete", "new", "manual", "play", "reverse", "effect", "variable", "group", "cuelist", "cue", "fixture", "master", "blackout", "clear", "store", "update", "plus", "minus", "next", "previous"}
NUMBER_AFTER = {"Fixture", "Group", "Cue", "Thru", "+", "At", "Master", "Pan", "Tilt", "Zoom", "Focus", "Gobo", "GoboSpin", "Prism", "Strobe", "Fader", "BPM", "Channel", "CH", "Goto", "Rate", "Fade", "Delay"}
NUMBER_BEFORE = {"at", "thru", "through", "color", "full", "half", "and", "plus", "percent", "until"}


# Woerter, die zwischen ZWEI Zahlen praktisch immer "Thru" gemeint sind ("fixtures one threw five"); "to / too / two" siehe SLOT_NUMBERS und `_ranges`
THRU_SOUNDS = {"till", "until", "true", "through", "threw", "thru", "thrue", "thro", "throu", "throw", "throws", "thrown", "trough", "drew", "trew", "tru", "grew", "crew", "frew", "fru",
               "dru", "through.", "thruu", "thrū", "thrú", "truth", "trou", "trout", "tuh", "thro.", "tho", "though", "threw."}
RANGE_HEADS = ("Fixture", "Group", "Cue")


def _ranges(tokens: List[str], notes: List[str]) -> List[str]:
    """Whisper schreibt "thru" oft als die ZAHL 2 ("fixtures one two five" = 1 Thru 5). Steht in einer Auswahl (Fixture / Group / Cue-Bereich) eine 2 genau zwischen zwei Zahlen ohne Operator,
    ist es das Bindewort: eine Zahl-Zahl-Zahl-Folge ist dort sonst kein gueltiger Befehl."""
    out: List[str] = []
    for tok in tokens:                                             # "fixture 1-5" -> "1 Thru 5" (nur in einer Auswahl)
        match = re.fullmatch(r"(\d+)\s*[-–]\s*(\d+)", str(tok))
        if match and out and out[0] in RANGE_HEADS:
            out.extend([match.group(1), "Thru", match.group(2)])
            notes.append(f"{tok} -> Thru")
        else:
            out.append(tok)
    for index in range(1, len(out) - 1):
        if str(out[index]) not in ("2", "8") or isinstance(out[index], _Name):
            continue
        if not (PLAIN_NUMBER.fullmatch(str(out[index - 1])) and PLAIN_NUMBER.fullmatch(str(out[index + 1]))):
            continue
        back = index - 1                                           # zurueck bis zum Kopf: nur Zahlen, Thru, + und - duerfen dazwischen stehen
        while back >= 0 and (_is_num(out[back]) or out[back] in ("Thru", "+", "-")):
            back -= 1
        if back >= 0 and out[back] in RANGE_HEADS:
            if str(out[index]) == "2":
                out[index] = "Thru"
                notes.append("2 -> Thru")
            elif out[back] in ("Fixture", "Group"):                # "fixture five eight seventy": "at" als Zahl 8 verstanden
                out[index] = "At"
                notes.append("8 -> At")
    return out


def _keywords(tokens: List[str], notes: List[str]) -> List[str]:
    """Woerter -> Schluesselwoerter (Zahl-Plaetze, Synonyme, Hoerfehler mit Blick auf die Stelle, Klang, Farben, Schreibfehler); alles andere (Zahlen, Namen) bleibt."""
    out: List[str] = []
    in_name = False                                                # direkt nach Group / Cuelist / Effect ...: der Name (bleibt, wie gesprochen)
    always = {alias: key for key, aliases in ALWAYS.items() for alias in aliases}
    needs_number = {alias: key for key, aliases in NEEDS_NUMBER_NEXT.items() for alias in aliases}
    n = len(tokens)
    i = 0

    def put(word: str, original: str, note: bool = True) -> None:
        if note and word.lower() != original:
            notes.append(f"{original} -> {word}")
        out.append(word)

    while i < n:
        tok = tokens[i]
        previous = out[-1] if out else ""
        nxt = tokens[i + 1] if i + 1 < n else ""
        nxt_num = _is_num(nxt) or nxt in UNITS or nxt in TENS
        prev_num = _is_num(previous)
        if _is_num(tok) or tok in ("+", "-") or re.fullmatch(r"#[0-9a-f]{3,6}", tok):
            out.append(tok)
            in_name = False
            i += 1
            continue
        if in_name:                                                # Namenswoerter bis zum naechsten Schluesselwort oder zur Zahl
            if tok in NAME_END:
                in_name = False
            else:
                out.append(_Name(tok))
                i += 1
                continue
        # Farben, auch zweiteilig ("warm white", "light blue")
        if tok in ("warm", "cool", "cold") and nxt == "white":
            if previous != "Color":
                out.append("Color")
            put("Warm" if tok == "warm" else "Cool", tok, False)
            i += 2
            continue
        if tok == "light" and nxt == "blue":
            if previous != "Color":
                out.append("Color")
            put("Lightblue", tok, False)
            i += 2
            continue
        # Zahl-Plaetze: wo eine Zahl stehen muss (hinter Fixture / Group / Cue / At ...)
        if tok in SLOT_NUMBERS:
            if tok in ("to", "too", "tu") and prev_num and nxt_num:
                put("Thru", tok)                                  # "fixture one to five"
                i += 1
                continue
            if previous in NUMBER_AFTER and (nxt == "" or nxt in NUMBER_BEFORE or nxt in WORDS or nxt_num):
                put(str(SLOT_NUMBERS[tok]), tok)                  # "fixture for at fifty" -> Fixture 4 At 50
                in_name = False
                i += 1
                continue
        if tok == "and" and prev_num and nxt_num:
            put("+", tok, False)                                  # "fixture one and three"
            i += 1
            continue
        if tok in THRU_SOUNDS and prev_num and nxt_num:
            put("Thru", tok, tok not in ("through", "until"))
            i += 1
            continue
        if tok in ("it", "add", "ad") and prev_num and (nxt_num or nxt in ("full", "half")):
            put("At", tok)
            i += 1
            continue
        if previous in ("Blackout", "Effect", "Audio") and tok in ("of", "own", "an", "awf"):
            put("Off" if tok in ("of", "awf") else "On", tok)
            i += 1
            continue
        if tok in WORDS:
            word = WORDS[tok]
            put(word, tok, False)
            in_name = word in NAME_TAKERS
            i += 1
            continue
        if tok in always:
            word = always[tok]
            put(word, tok)
            in_name = word in NAME_TAKERS
            i += 1
            continue
        if tok in needs_number and (nxt_num or nxt in ("minus", "plus", "-", "+")):
            put(needs_number[tok], tok)
            i += 1
            continue
        colour = _color(tok) if previous == "Color" else None
        if colour is None and previous not in ("Cuelist", "Group", "Variable", "Effect", "Label"):
            colour = tok if tok in COLORS else COLOR_ALIASES.get(tok)                     # "fixture 5 green" -> "... Color Green"
        if colour:
            if previous != "Color":
                out.append("Color")
            put(colour.capitalize(), tok, tok != colour)
            i += 1
            continue
        if tok.isalpha():
            key = pkey(tok)                                        # Klang: an einer Stelle, wo ein bestimmtes Schluesselwort stehen muss
            if prev_num and key in AFTER_NUMBER and (nxt_num or nxt in WORDS or nxt == "" or nxt in COLORS):
                put(AFTER_NUMBER[key], tok)
                i += 1
                continue
            if nxt_num and key in BEFORE_NUMBER and len(key) >= 3 and len(tok) >= 4 and previous not in NAME_TAKERS:        # kurze Schluessel (go, some ...) waeren zu unscharf
                put(BEFORE_NUMBER[key], tok)
                in_name = False
                i += 1
                continue
            if len(tok) >= 4 and previous not in NAME_TAKERS:
                match = _closest(tok, KEYWORD_LIST, 0.82)           # Schreibfehler: "blakout" -> blackout
                if match:
                    put(WORDS[match], tok)
                    in_name = WORDS[match] in NAME_TAKERS
                    i += 1
                    continue
        out.append(tok)
        i += 1
    return out


def _tidy(tokens: List[str]) -> List[str]:
    """Doppelte Woerter (Stottern), fuehrendes + / -."""
    out: List[str] = []
    for tok in tokens:
        if out and out[-1] == tok and not _is_num(tok) and tok not in ("Clear", "At") and not isinstance(tok, _Name):
            continue
        out.append(tok)
    return [tok for index, tok in enumerate(out) if not (index == 0 and tok in ("+", "-"))]


def _polish(tokens: List[str]) -> List[str]:
    """Abkuerzungen: Fixture 5 Off -> At 0, Fixture 5 On -> At Full, Out -> At 0, Home / Center -> Pan 50% Tilt 50%; "At At" -> "At"; "Color Color" -> "Color"."""
    out: List[str] = []
    selecting = bool(tokens) and tokens[0] in ("Fixture", "Group")
    for index, tok in enumerate(tokens):
        previous = out[-1] if out else ""
        if tok.endswith("%") and previous in NO_PERCENT:                          # Master / Fader / BPM ... kennen keine Prozentangabe: "Master 80%" ist ein Fehler
            tok = tok[:-1]
        if tok == "Out" and previous != "Blackout":
            out.extend(["At", "0"] if previous != "At" else ["0"])
            continue
        if tok in ("Off", "On") and selecting and index == len(tokens) - 1 and previous not in ("Blackout", "Effect", "Audio", "Cuelist", "Variable"):
            out.extend(["At", "0"] if tok == "Off" else ["At", "Full"])
            continue
        if tok == "Home":
            out.extend(["Pan", "50%", "Tilt", "50%"])
            continue
        if tok == "Full" and selecting and previous not in ("At", "Zoom", "Master", "Fader", "Focus", "Gobo", "Prism", "Strobe", "Pan", "Tilt"):
            out.extend(["At", "Full"])
            continue
        if tok == "Half" and selecting and previous not in ("At", "Zoom", "Master", "Fader", "Focus", "Gobo", "Prism", "Strobe", "Pan", "Tilt"):
            out.extend(["At", "Half"])
            continue
        if tok == "At" and previous == "At":                                      # "at at 70" = Stottern -> "At 70"; "at at" allein = "At At" (alles an: 100 % + Weiss)
            following = tokens[index + 1] if index + 1 < len(tokens) else ""
            stutter = following == "Full" or _is_num(following.lstrip("+-")) or following in ("+", "-")
            if stutter or (len(out) >= 2 and out[-2] == "At"):
                continue
        if tok == "Color" and previous == "Color":
            continue
        out.append(tok)
    return out


def _quote_names(tokens: List[str]) -> List[str]:
    """Mehrere Namenswoerter hinter Group / Cuelist / Effect / Variable ("front truss") gehoeren zusammen: in Anfuehrungszeichen, so versteht die Befehlszeile sie als EINEN Namen."""
    out: List[str] = []
    i = 0
    stop = CANON | {"+", "-"}
    while i < len(tokens):
        tok = tokens[i]
        out.append(tok)
        i += 1
        if tok in ("Group", "Cuelist", "Effect", "Variable"):
            name: List[str] = []
            while i < len(tokens) and (isinstance(tokens[i], _Name) or (tokens[i] not in stop and not _is_num(tokens[i]))) and not tokens[i].startswith('"'):
                name.append(str(tokens[i]))
                i += 1
            if len(name) > 1:
                out.append('"' + " ".join(name) + '"')
            else:
                out.extend(name)
    return out


# ------------------------------------------------------------------------------------------------ Hauptfunktion
def interpret(text: str, wake_words: Optional[List[str]] = None) -> Dict[str, Any]:
    """Gesprochener Text -> {"heard": bereinigter Text nach dem Weckwort, "command": Befehlszeile ("" = nichts verstanden), "commands": [einzelne Befehle], "blocked": gesperrter Befehl,
    "notes": [automatische Korrekturen]}."""
    wake = [w.lower() for w in (wake_words or [])]
    heard = _clean(strip_wake(_clean(str(text or "")[:MAX_TEXT]), wake))
    result: Dict[str, Any] = {"heard": heard, "command": "", "commands": [], "blocked": "", "notes": []}
    if not heard:
        return result
    commands: List[str] = []
    for piece in re.split(r"\b(?:then|after that|next command)\b", heard):                    # mehrere Befehle in einem Atemzug
        notes: List[str] = []
        tokens = _tidy(_ranges(_keywords(_numbers([t for t in piece.split() if t]), notes), notes))
        kept: List[str] = []
        for tok in tokens:                                         # Fuellwoerter weg - ausser dort, wo ein Name stehen kann ("group a")
            if tok.lower() in FILLERS and not isinstance(tok, _Name) and not (kept and kept[-1] in NAME_TAKERS):
                continue
            kept.append(tok)
        while kept and kept[0] not in HEADS:                       # Vorgeplaenkel ("set", Unverstandenes) weg
            kept.pop(0)
        if not kept:
            continue
        kept = _quote_names(_polish(kept))
        lowered = [t.lower() for t in kept]
        for word, name in BLOCKED.items():
            if word in lowered:
                result["blocked"] = name
        if lowered[0] == "clear" and lowered.count("clear") >= 2:
            result["blocked"] = "Clear Clear"
        commands.append(" ".join(kept))
        result["notes"].extend(notes)
    result["commands"] = commands
    result["command"] = "; ".join(commands)
    return result
