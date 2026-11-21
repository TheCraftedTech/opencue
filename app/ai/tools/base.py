# Copyright (C) 2026 Samuel Zenker
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Funktionen ("Werkzeuge", Function Calling), die die KI im Modus "Arbeiten" aufrufen kann.

Jede Funktion gehoert zu einer Sammlung (`Collection`). Im Modus "nach Bedarf" sieht die KI zuerst nur die Sammelfunktionen (eine je Sammlung, z. B.
`read_functions`): ruft sie eine auf, bekommt sie die Liste der Funktionen dieser Sammlung und kann sie ab dem naechsten Schritt aufrufen. So bleibt der Prompt
klein (wichtig fuer kleine lokale Modelle). Im Modus "alle auf einmal" stehen alle Funktionen sofort da (immer dieselbe Liste: schneller, braucht ein besseres Modell).

`access` einer Funktion (Berechtigungen siehe agent.py und Einstellungen -> KI-Assistent -> Berechtigungen):
- "free"     : Hilfsfunktionen ohne Wirkung auf die Show (Taschenrechner, Zufallszahl, Uhrzeit) - immer erlaubt, nicht einstellbar
- "read"     : die Show nur LESEN (Voreinstellung: immer erlauben)
- "write"    : die Show VERAENDERN / bedienen (Voreinstellung: fragen)
- "critical" : heikle Dinge (beliebiger Befehl, Cues / Gruppen loeschen ...; Voreinstellung: fragen - "immer erlauben" geht wie bei allen anderen)
Je Klasse stellt der Benutzer "nie", "immer erlauben" oder "fragen" ein.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Optional

ACCESS_CLASSES = ("free", "read", "write", "critical")
PERMISSION_CLASSES = ("read", "write", "critical")          # die Klassen, die der Benutzer einstellen kann ("free" ist immer erlaubt)
Handler = Callable[[Dict[str, Any], "ToolContext"], Awaitable[Any]]


@dataclass
class ToolContext:
    """Was eine Funktion vom laufenden Gespraech wissen darf; `open` = die geoeffneten Sammlungen dieser Frage."""
    chat_id: str
    language: str = "en"
    open: List[str] = field(default_factory=list)
    scope: str = "work"                 # "work" (Modus Arbeiten) | "guide" (Modus Wegweiser): jeder Modus sieht nur seine eigene Funktionsliste


# Die HAEUFIGEN Funktionen: im Modus "core" (Standard) stehen sie immer in der Liste, alle anderen kommen ueber ihre Sammelfunktion (Prompt klein, kleine Modelle bleiben treffsicher).
CORE_TOOLS = {"show_overview", "list_fixtures", "read_fixtures", "list_groups", "list_cuelists", "set_fixtures", "set_blackout", "set_master", "control_cuelist",
              "apply_variable", "apply_effect", "stop_effects", "command_help", "run_command", "calculate", "random_number", "current_time"}
TOOLS_MODES = ("core", "collections", "all")


@dataclass
class Tool:
    name: str
    description: str
    parameters: Dict[str, Any]
    handler: Handler
    collection: str = ""
    access: str = "read"
    keep_result: bool = False           # das Ergebnis darf in der Zusammenfassung frueherer Fragen stehen (nur bei Ergebnissen, die nie veralten, z. B. eine Rechnung)
    core: bool = False                  # steht im Modus "core" immer in der Liste (siehe CORE_TOOLS)
    scope: str = "work"                 # "work" | "guide": zu welchem Modus die Funktion gehoert (Wegweiser-Funktionen stehen in GUIDE_TOOLS, nicht in den Sammlungen)

    def spec(self) -> Dict[str, Any]:
        """Beschreibung im Format der Ollama-/OpenAI-Schnittstelle."""
        return {"type": "function", "function": {"name": self.name, "description": self.description, "parameters": self.parameters}}


@dataclass
class Collection:
    name: str
    opener: str                         # Name der Sammelfunktion
    description: str                    # Beschreibung der Sammelfunktion (sagt der KI, wann sie sie rufen soll)
    tools: List[Tool] = field(default_factory=list)


COLLECTIONS: Dict[str, Collection] = {}
GUIDE_TOOLS: List[Tool] = []        # die Funktionen des Modus "Wegweiser" (eigene kleine Liste, keine Sammlungen)
# "Keine Funktion noetig": wird NICHT mehr angeboten (Messung mit dem 3B-Modell: es waehlte sie auch fuer Show-Fragen und antwortete dann aus dem Gedaechtnis). Schreibt oder ruft ein
# Modell sie trotzdem, wird das vertragen: die KI antwortet dann ohne Funktionen (ihr eigener Text). Wird weder gezeigt noch gespeichert.
PASS_NAME = "answer_directly"
PASS_DESCRIPTION = ("Call this when you need NO other function: for greetings, thanks, small talk, questions about you and general questions. "
                    "Then write your answer to the user in plain words.")
_BY_NAME: Dict[str, Tool] = {}


def schema(properties: Optional[Dict[str, Any]] = None, required: Optional[List[str]] = None) -> Dict[str, Any]:
    return {"type": "object", "properties": properties or {}, "required": required or []}


def register(collection: Collection) -> None:
    for tool in collection.tools:
        tool.collection = collection.name
        tool.core = tool.name in CORE_TOOLS
        _BY_NAME[tool.name] = tool
    COLLECTIONS[collection.name] = collection


def register_guide(tools: List[Tool]) -> None:
    for tool in tools:
        tool.scope, tool.core, tool.collection = "guide", True, "guide"
        _BY_NAME[tool.name] = tool
        GUIDE_TOOLS.append(tool)


def all_tools() -> List[Tool]:
    return [t for c in COLLECTIONS.values() for t in c.tools]


def collection_for_opener(name: str) -> Optional[Collection]:
    return next((c for c in COLLECTIONS.values() if c.tools and c.opener == name), None)


def tool_names() -> set:
    """Alle Namen, die als Aufruf gelten (Funktionen und Sammelfunktionen), auch die noch nicht angebotenen."""
    return {t.name for t in all_tools()} | {t.name for t in GUIDE_TOOLS} | {c.opener for c in COLLECTIONS.values() if c.tools} | {PASS_NAME}


_NOISE = ("get", "show", "fetch", "read", "call", "run", "do", "use", "tool", "function", "func", "the")


def _tokens(name: str) -> List[str]:
    """Namen in Woerter zerlegen: 'getRandomNumber' / 'functions.random-number' -> random, number (ohne Fuellwoerter wie get / tool)."""
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", str(name).strip().split("/")[-1].split(".")[-1])
    words = [w for w in re.split(r"[^a-zA-Z0-9]+", spaced.lower()) if w]
    return [w for w in words if w not in _NOISE] or words


def find_name(name: str) -> Optional[str]:
    """Der echte Name zu einem Namen, den ein (kleines) Modell geschrieben hat: genau, sonst abweichende Gross-/Kleinschreibung oder Schreibweise
    ('functions.Random_Number', 'randomNumber'), sonst ein EINDEUTIGER Treffer ueber die Wortbestandteile. None: gibt es nicht."""
    names = tool_names()
    if name == PASS_NAME:
        return name
    if name in names:
        return name
    wanted = _tokens(name)
    if not wanted:
        return None
    same = [n for n in names if _tokens(n) == wanted]
    if len(same) == 1:
        return same[0]
    part = [n for n in names if set(wanted) <= set(_tokens(n)) or set(_tokens(n)) <= set(wanted)]
    return part[0] if len(part) == 1 else None


def get_tool(name: str) -> Optional[Tool]:
    return _BY_NAME.get(name)


def open_collection(name: str, ctx: ToolContext) -> None:
    if name not in ctx.open:
        ctx.open.append(name)


def _hidden(collection: Collection, mode: str) -> List[Tool]:
    """Die Funktionen einer Sammlung, die NICHT schon sofort in der Liste stehen (im Modus "core" gehoeren die haeufigen dazu)."""
    return [t for t in collection.tools if not (mode == "core" and t.core)]


def _mode(value: Any) -> str:
    """Alte Aufrufe uebergaben einen Wahrheitswert (`everything`): True = alle, False = Sammlungen."""
    if value is True:
        return "all"
    if value is False:
        return "collections"
    return value if value in TOOLS_MODES else "core"


def specs_for(ctx: ToolContext, mode: Any) -> List[Dict[str, Any]]:
    """Die Funktionen, die die KI gerade sehen soll. "all": alle sofort. "collections": nur die Sammelfunktionen, die Funktionen geoeffneter Sammlungen kommen dazu.
    "core": die haeufigen Funktionen immer, fuer den Rest die Sammelfunktionen (und die geoeffneten Sammlungen)."""
    if ctx.scope == "guide":
        return [t.spec() for t in GUIDE_TOOLS]
    mode = _mode(mode)
    if mode == "all":
        return [t.spec() for t in all_tools()]
    out = [t.spec() for t in all_tools() if mode == "core" and t.core]
    out += [open_spec(c) for c in COLLECTIONS.values() if _hidden(c, mode)]
    for name in ctx.open:
        collection = COLLECTIONS.get(name)
        if collection:
            out.extend(t.spec() for t in _hidden(collection, mode))
    return out


def openers_for(mode: Any, scope: str = "work") -> List[str]:
    """Die Namen der Sammelfunktionen, die in diesem Modus angeboten werden (fuer den System-Prompt)."""
    mode = _mode(mode)
    return [] if mode == "all" or scope == "guide" else [c.opener for c in COLLECTIONS.values() if _hidden(c, mode)]


def pass_spec() -> Dict[str, Any]:
    return {"type": "function", "function": {"name": PASS_NAME, "description": PASS_DESCRIPTION, "parameters": schema()}}


def open_spec(collection: Collection) -> Dict[str, Any]:
    """Die Sammelfunktion: nur was darin steckt (der erste Satz) und wann man sie ruft - kurz, damit die Liste fuer kleine Modelle klein bleibt."""
    what = collection.description.split(" Call it ONLY")[0].strip()
    return {"type": "function", "function": {"name": collection.opener, "description": what + " Call it ONLY when the user asks for this - never for greetings or small talk.", "parameters": schema()}}


async def run_opener(collection: Collection, ctx: ToolContext, mode: Any = "collections") -> Dict[str, Any]:
    """Ergebnis einer Sammelfunktion: die Funktionen der Sammlung (Name, Beschreibung, Angaben); sie stehen der KI ab dem naechsten Schritt zur Verfuegung."""
    open_collection(collection.name, ctx)
    return {"ok": True, "functions": [{"name": t.name, "description": t.description, "parameters": t.parameters.get("properties", {}), "required": t.parameters.get("required", [])}
                                      for t in _hidden(collection, _mode(mode))], "hint": "These functions are available now. Call the one you need by its name."}


def describe_for_prompt() -> str:
    """Eine Zeile fuer den System-Prompt (im Modus 'alle auf einmal' nicht noetig): was es gibt, nur Namen."""
    return "; ".join(f"{c.opener}: " + ", ".join(t.name for t in c.tools) for c in COLLECTIONS.values() if c.tools)
