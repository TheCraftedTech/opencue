# Copyright (C) 2026 Samuel Zenker
# SPDX-License-Identifier: GPL-3.0-or-later
"""Funktionen von Hand aufrufen: im Chat tippt der Benutzer `/read_fixtures {"fixtures": "6-8"}` (oder `/read_fixtures 6-8`, `/read_fixtures fixtures=6-8`, `/help`) und sieht das Ergebnis
der Funktion - ohne dass die KI antwortet. Das Modell wird dafuer nicht gefragt. Der Benutzer handelt selbst, deshalb gelten die Berechtigungen der KI hier nicht (kein "fragen" / "nie")."""
from __future__ import annotations

import json
import re
from typing import Any, Dict, Optional, Tuple

from app.ai import tools
from app.ai.errors import AiError

# "/name" am Anfang der Nachricht, danach Ende, Leerraum oder der Anfang der Werte ({ [ ( " '). "/etc/hosts" ist KEIN Befehl.
COMMAND = re.compile(r"^/([A-Za-z_][A-Za-z0-9_]*)(?=$|[\s{\[(\"'])\s*(.*)$", re.DOTALL)
PAIRS = re.compile(r"""(\w+)\s*=\s*("[^"]*"|'[^']*'|\S+)""")
HELP_NAMES = ("help", "functions", "hilfe", "funktionen")
MAX_TEXT = 4000


def split(text: str) -> Optional[Tuple[str, str]]:
    """(Name, Rest) einer Nachricht wie '/read_fixtures {"fixtures": "6-8"}'; None: eine normale Nachricht an die KI."""
    found = COMMAND.match(str(text or "").strip())
    return (found.group(1), found.group(2).strip()) if found else None


def _example(tool: "tools.Tool") -> str:
    props = tool.parameters.get("properties", {})
    keys = tool.parameters.get("required") or list(props)[:1]
    return json.dumps({k: "..." for k in keys}, ensure_ascii=False) if keys else ""


def arguments(tool: "tools.Tool", rest: str) -> Dict[str, Any]:
    """Die Werte der Funktion aus dem Text hinter dem Namen: JSON-Objekt, `key=value ...` oder - hat die Funktion genau einen Pflichtwert - der ganze Rest. AiError bei allem anderen."""
    rest = rest.strip()
    if not rest:
        return {}
    if rest.startswith("{"):
        try:
            data = json.loads(rest)
        except ValueError as exc:
            raise AiError("bad_request", f"The values are not valid JSON ({getattr(exc, 'msg', exc)}). Example: /{tool.name} {_example(tool)}")
        if not isinstance(data, dict):
            raise AiError("bad_request", f"The values must be a JSON object. Example: /{tool.name} {_example(tool)}")
        return data
    pairs = PAIRS.findall(rest)
    if pairs and not PAIRS.sub("", rest).strip():
        return {key: value.strip("\"'") for key, value in pairs}
    props = tool.parameters.get("properties", {})
    keys = tool.parameters.get("required") or (list(props) if len(props) == 1 else [])
    if len(keys) == 1:
        return {keys[0]: rest.strip("\"'")}
    raise AiError("bad_request", f"Give the values as JSON or as key=value. Example: /{tool.name} {_example(tool)}  -  /help lists the functions.")


def _first_sentence(text: str, limit: int = 140) -> str:
    text = " ".join(str(text).split())
    cut = re.split(r"(?<=[.!?])\s", text, maxsplit=1)[0]
    return cut if len(cut) <= limit else cut[:limit - 3].rstrip() + "..."


def help_result() -> Dict[str, Any]:
    """Alle Funktionen mit ihrer Art und den Werten (Pflichtwerte mit *): damit man weiss, was man tippen kann."""
    rows = []
    for tool in tools.all_tools():
        required = set(tool.parameters.get("required", []))
        rows.append({"function": "/" + tool.name, "kind": tool.access, "about": _first_sentence(tool.description),
                     "values": [k + ("*" if k in required else "") for k in tool.parameters.get("properties", {})]})
    return {"ok": True, "how": "Type /<function> followed by the values as JSON, for example /read_fixtures {\"fixtures\": \"6-8\"}. With one required value the plain text is enough: /read_fixtures 6-8. "
                               "The result is shown here and the AI does not answer. Values with * are required.", "functions": rows}
