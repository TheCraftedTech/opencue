# Copyright (C) 2026 Samuel Zenker
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Funktionsaufrufe, die ein kleines Modell als TEXT schreibt.

Manche Modelle (z. B. qwen2.5-coder) schicken den Aufruf nicht ueber die Schnittstelle (`tool_calls`), sondern schreiben ihn in die Antwort: als JSON, in
```json-Zaeunen oder in <tool_call>-Marken, mit leicht abweichendem Namen, manchmal mit fehlender schliessender Klammer. Hier werden solche Aufrufe erkannt und
aus dem Text entfernt.
"""
from __future__ import annotations

import json
import re
import uuid
from typing import Any, Dict, List, Tuple

from app.ai.tools import PASS_NAME, find_name, tool_names

STARTS = ("{", "<tool_call", "```json", "```tool", "[{")          # so beginnt eine Antwort, die ein Aufruf sein koennte (wird dann erst am Ende gezeigt)
_EMPTY_WRAPPERS = re.compile(r"<tool_call>\s*</tool_call>|```[a-z]*\s*```|</?tool_calls?>", re.I)


def new_call(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    return {"id": uuid.uuid4().hex[:8], "name": name, "arguments": arguments}


def looks_like_call(content: str) -> bool:
    if content.lstrip().lower().startswith(STARTS):
        return True
    m = re.match(r"\s*([A-Za-z_][A-Za-z0-9_.]*)\s*\(", content)                 # Funktionsschreibweise: calculate(...)
    return bool(m and find_name(m.group(1)))


def _as_calls(obj: Any) -> List[Dict[str, Any]]:
    """Ein JSON-Objekt, das wie ein Funktionsaufruf aussieht: {"name": ..., "arguments": {...}} (auch "parameters" / "args", auch unter "function")."""
    if not isinstance(obj, dict):
        return []
    if isinstance(obj.get("tool_calls"), list):
        out: List[Dict[str, Any]] = []
        for item in obj["tool_calls"]:
            out.extend(_as_calls(item))
        return out
    function = obj.get("function") if isinstance(obj.get("function"), dict) else obj
    name = function.get("name") or function.get("tool") or obj.get("tool")
    if not isinstance(name, str):
        return []
    real = find_name(name)
    if real is None:
        if not any(key in function for key in ("arguments", "parameters", "args")):
            return []                                                          # kein Aufruf, nur irgendein JSON
        real = name                                                            # erfundener Name: wird als Aufruf behandelt und mit einem Fehler beantwortet
    arguments = function.get("arguments", function.get("parameters", function.get("args", {})))
    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments or "{}")
        except ValueError:
            return []
    if arguments is None:
        arguments = {}
    if not isinstance(arguments, dict):
        return []
    return [new_call(real, arguments)]


def _close_json(text: str) -> str:
    """Haengt fehlende schliessende Klammern an ('{"a": {"b": 1}' wird repariert); nur wenn Klammern fehlen und der Text sonst ruhig endet."""
    stack: List[str] = []
    in_string = escaped = False
    for ch in text:
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch in "{[":
            stack.append("}" if ch == "{" else "]")
        elif ch in "}]":
            if not stack or stack.pop() != ch:
                return text
    if in_string or not stack or len(stack) > 4:
        return text
    return text.rstrip().rstrip(",") + "".join(reversed(stack))


_FUNCTION_STYLE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_.]*)\s*\((.*)\)\s*;?\s*$", re.S)
_KEY_VALUE = re.compile(r"([A-Za-z_]\w*)\s*[=:]\s*(\"[^\"]*\"|'[^']*'|-?\d+(?:\.\d+)?|true|false)", re.I)


def _function_style(content: str) -> Tuple[str, List[Dict[str, Any]]]:
    """Die Antwort ist ein Aufruf in Funktionsschreibweise: `answer_directly("Hallo!")`, `calculate(expression="1+1")`, `random_number({"min": 1})`. (Text, Aufrufe) oder leer."""
    m = _FUNCTION_STYLE.match(content)
    if not m:
        return content, []
    name = find_name(m.group(1))
    if name is None:
        return content, []
    inner = m.group(2).strip()
    if name == PASS_NAME:                                                    # der Text in den Klammern ist die Antwort der KI
        return inner.strip("\"'` ").strip(), [new_call(PASS_NAME, {})]
    arguments: Dict[str, Any] = {}
    if inner.startswith("{"):
        try:
            loaded = json.loads(inner)
            arguments = loaded if isinstance(loaded, dict) else {}
        except ValueError:
            arguments = {}
    if not arguments:
        for key, raw in _KEY_VALUE.findall(inner):
            low = raw.lower()
            arguments[key] = True if low == "true" else False if low == "false" else raw[1:-1] if raw[:1] in "\"'" else float(raw) if "." in raw else int(raw)
    return "", [new_call(name, arguments)]


def extract_text_calls(content: str) -> Tuple[str, List[Dict[str, Any]]]:
    """(Resttext, Aufrufe). Besteht die Antwort nur aus einem Funktionsnamen ('calculate'), ist das ein Aufruf ohne Angaben."""
    if not content:
        return content, []
    styled = _function_style(content)
    if styled[1]:
        return styled
    bare = content.strip().strip("`\"' ()").rstrip(".:;")
    if bare and " " not in bare and "\n" not in bare:
        named = next((n for n in tool_names() if n.lower() == bare.lower()), None)
        if named:
            return "", [new_call(named, {})]
    if "{" not in content:
        return content, []
    decoder = json.JSONDecoder()
    calls: List[Dict[str, Any]] = []
    spans: List[Tuple[int, int]] = []
    i = 0
    while i < len(content):
        j = content.find("{", i)
        if j < 0:
            break
        try:
            obj, end = decoder.raw_decode(content, j)
        except ValueError:
            fixed = _close_json(content[j:])
            try:
                obj, length = decoder.raw_decode(fixed)
                end = len(content) if length >= len(fixed) else j + length
            except ValueError:
                i = j + 1
                continue
        found = _as_calls(obj)
        if found:
            calls.extend(found)
            spans.append((j, end))
            i = end
        else:
            i = j + 1
    if not calls:
        return content, []
    rest = content
    for start, end in reversed(spans):
        rest = rest[:start] + rest[end:]
    return _EMPTY_WRAPPERS.sub("", rest).strip(), calls
