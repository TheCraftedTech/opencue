# Copyright (C) 2026 Samuel Zenker
# SPDX-License-Identifier: GPL-3.0-or-later
"""Sammlung "helper": Funktionen, die nichts mit der Show zu tun haben - Taschenrechner und Zufallszahlen. Die KI soll nie im Kopf rechnen oder Zahlen erfinden."""
from __future__ import annotations

import ast
import math
import operator
import random
from datetime import datetime
from typing import Any, Dict

from app.ai.tools.base import Collection, Tool, ToolContext, register, schema

MAX_EXPRESSION = 300
MAX_COUNT = 50
MAX_POWER = 1000
_BINARY = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod, ast.Pow: operator.pow}
_UNARY = {ast.UAdd: operator.pos, ast.USub: operator.neg}
_FUNCTIONS = {"sqrt": math.sqrt, "sin": math.sin, "cos": math.cos, "tan": math.tan, "asin": math.asin, "acos": math.acos, "atan": math.atan, "atan2": math.atan2,
              "exp": math.exp, "ln": math.log, "log10": math.log10, "log2": math.log2, "abs": abs, "round": round, "floor": math.floor, "ceil": math.ceil,
              "min": min, "max": max, "radians": math.radians, "degrees": math.degrees, "pow": pow, "factorial": math.factorial, "hypot": math.hypot}
_NAMES = {"pi": math.pi, "e": math.e, "tau": math.tau}
SYNTAX = ("Numbers with a DOT as decimal separator (3.5). Operators + - * / // (whole division) % (remainder) ** or ^ (power) and parentheses. "
          "Functions: " + ", ".join(sorted(_FUNCTIONS)) + "; log(x) is base 10, log(x, base) any base. Constants: pi, e, tau. Trigonometry uses radians (radians(deg) converts). "
          "Percent: write 200*0.15, not 15%.")


class CalcError(Exception):
    pass


def _eval(node: ast.AST) -> Any:
    if isinstance(node, ast.Expression):
        return _eval(node.body)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise CalcError("Only numbers are allowed.")
        return node.value
    if isinstance(node, ast.Name):
        if node.id in _NAMES:
            return _NAMES[node.id]
        raise CalcError(f"Unknown name '{node.id}'. Known constants: pi, e, tau.")
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY:
        return _UNARY[type(node.op)](_eval(node.operand))
    if isinstance(node, ast.BinOp) and type(node.op) in _BINARY:
        left, right = _eval(node.left), _eval(node.right)
        if isinstance(node.op, ast.Pow) and (abs(right) > MAX_POWER or (isinstance(left, int) and isinstance(right, int) and abs(left) > 1 and right * math.log10(abs(left)) > 300)):
            raise CalcError("The power is too large.")
        return _BINARY[type(node.op)](left, right)
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and not node.keywords:
        name = node.func.id
        args = [_eval(a) for a in node.args]
        if name == "log":
            if len(args) == 1:
                return math.log10(args[0])
            if len(args) == 2:
                return math.log(args[0], args[1])
            raise CalcError("log takes 1 or 2 values.")
        if name in _FUNCTIONS:
            return _FUNCTIONS[name](*args)
        raise CalcError(f"Unknown function '{name}'.")
    raise CalcError("This is not a plain calculation.")


def evaluate(expression: str) -> Any:
    """Rechnet einen Ausdruck sicher aus (nur Zahlen, Operatoren und erlaubte Funktionen - kein eval). CalcError bei allem Ungueltigen."""
    text = str(expression or "").strip()
    if not text:
        raise CalcError("The expression is empty.")
    if len(text) > MAX_EXPRESSION:
        raise CalcError(f"The expression is too long (at most {MAX_EXPRESSION} characters).")
    text = text.replace("^", "**").replace("×", "*").replace("·", "*").replace("÷", "/").replace("−", "-")
    try:
        tree = ast.parse(text, mode="eval")
    except SyntaxError:
        raise CalcError("This is not a valid calculation. " + SYNTAX)
    try:
        value = _eval(tree)
    except CalcError:
        raise
    except ZeroDivisionError:
        raise CalcError("Division by zero.")
    except (ValueError, OverflowError, TypeError) as exc:
        raise CalcError(f"Not possible: {exc}")
    if isinstance(value, complex):
        raise CalcError("The result is not a real number.")
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            raise CalcError("The result is not a finite number.")
        if value == int(value) and abs(value) < 1e15:
            return int(value)
        return float(f"{value:.12g}")
    return value


async def _calculate(args: Dict[str, Any], ctx: ToolContext) -> Any:
    expression = args.get("expression", args.get("formula", args.get("expr", "")))
    try:
        value = evaluate(str(expression))
    except CalcError as exc:
        return {"ok": False, "error": str(exc), "syntax": SYNTAX}
    return {"ok": True, "expression": str(expression).strip(), "result": value}


def _number(value: Any, name: str, default: float) -> float:
    if value is None or value == "":
        return default
    try:
        number = float(str(value).replace(",", "."))
    except ValueError:
        raise CalcError(f"'{name}' must be a number.")
    if number != number or abs(number) > 1e15:
        raise CalcError(f"'{name}' is out of range.")
    return number


async def _random_number(args: Dict[str, Any], ctx: ToolContext) -> Any:
    try:
        low = _number(args.get("min"), "min", 1)
        high = _number(args.get("max"), "max", 100)
        count = int(_number(args.get("count"), "count", 1))
    except CalcError as exc:
        return {"ok": False, "error": str(exc)}
    if low > high:
        return {"ok": False, "error": f"min ({low:g}) is greater than max ({high:g})."}
    if not 1 <= count <= MAX_COUNT:
        return {"ok": False, "error": f"count must be between 1 and {MAX_COUNT}."}
    integer = args.get("integer")
    whole = True if integer is None else str(integer).lower() not in ("false", "0", "no", "nein")
    if whole:
        values = [random.randint(int(math.ceil(low)), int(math.floor(high))) for _ in range(count)] if math.ceil(low) <= math.floor(high) else None
        if values is None:
            return {"ok": False, "error": "There is no whole number between min and max."}
    else:
        values = [round(random.uniform(low, high), 6) for _ in range(count)]
    return {"ok": True, "min": low if not whole else int(math.ceil(low)), "max": high if not whole else int(math.floor(high)), "count": count, "numbers": values}


_WEEKDAYS = {"de": ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"], "en": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]}


async def _current_time(args: Dict[str, Any], ctx: ToolContext) -> Any:
    now = datetime.now().astimezone()
    lang = "de" if ctx.language == "de" else "en"
    weekday = _WEEKDAYS[lang][now.weekday()]
    text = (f"Es ist {weekday}, der {now.strftime('%d.%m.%Y')}, {now.strftime('%H:%M:%S')} Uhr." if lang == "de" else f"It is {weekday}, {now.strftime('%Y-%m-%d')}, {now.strftime('%H:%M:%S')}.")
    return {"ok": True, "message": text, "date": now.strftime("%Y-%m-%d"), "time": now.strftime("%H:%M:%S"), "weekday": weekday, "timezone": now.tzname() or ""}


def today_text(language: str) -> str:
    """'Mittwoch, 28.10.2026' - nur das Datum (aendert sich einmal am Tag), fuer den System-Prompt des Chat-Modus."""
    now = datetime.now()
    lang = "de" if language == "de" else "en"
    return f"{_WEEKDAYS[lang][now.weekday()]}, {now.strftime('%d.%m.%Y')}" if lang == "de" else f"{_WEEKDAYS[lang][now.weekday()]}, {now.strftime('%Y-%m-%d')}"


register(Collection("helper", "helper_functions",
                    "Gives you more functions that have nothing to do with the show: a calculator (never do arithmetic in your head), random numbers and the current date and time. "
                    "Call it ONLY when the user asks for a calculation, a random number, a dice roll or the time or date - never for greetings, thanks, small talk or general questions.", [
    Tool("calculate", "Calculator: calculates a mathematical expression exactly and returns the result. Use it for EVERY calculation (\"what is 17 times 23\", \"was ist 15 Prozent von 200\", \"wurzel aus 144\") instead of computing yourself. Write the expression with + - * / ^ and parentheses.",
         schema({"expression": {"type": "string", "description": "The calculation as an expression, e.g. \"17 * 23\", \"(12 + 8) * 1.5\" or \"sqrt(144) + 2^3\"."}}, ["expression"]), _calculate, access="free", keep_result=True),
    Tool("random_number", "Draws random numbers between min and max (inclusive). Use it for \"give me a random number\", \"roll a die\" / \"würfle\", \"zufallszahl\", \"pick a number between 1 and 10\". "
                          "Defaults: min 1, max 100, count 1, whole numbers. A die is min 1, max 6.",
         schema({"min": {"type": "number", "description": "Smallest possible number (default 1)."}, "max": {"type": "number", "description": "Largest possible number (default 100)."},
                 "count": {"type": "integer", "description": f"How many numbers (1-{MAX_COUNT}, default 1)."},
                 "integer": {"type": "boolean", "description": "true = whole numbers (default), false = decimals."}}), _random_number, access="free"),
    Tool("current_time", "Returns the current time of day, today's date and the weekday of this computer. Use it for \"what time is it?\", \"wie spät ist es?\", \"welche Uhrzeit?\", \"which date is today?\", \"welcher Tag ist heute?\". "
                         "It has no parameters. Call it again every time the user asks, because the time keeps changing.", schema(), _current_time, access="free"),
]))
