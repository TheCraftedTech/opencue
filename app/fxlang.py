"""
fxlang.py
Die Skriptsprache der Effekte: C++/Arduino-aehnlich, nur Zahlen (float, int, bool), ohne Fremdzugriff.

Ein Skript besteht aus (optionalen) globalen Variablen, eigenen Funktionen, einem optionalen setup() (einmal beim Start eines Effekts) und loop()
(wird `#RATE` mal pro Sekunde aufgerufen):

    float winkel = 0;                       // global: bleibt zwischen den loop()-Aufrufen erhalten
    float welle(float x) { return 0.5 + 0.5 * sin(2 * PI * x); }
    setup() { winkel = 0; }
    loop() {
      for (int i = 0; i < 3; i++) { winkel += 0.1; }
      if (winkel > 1) { winkel = 0; } else if (index == 0) { dimmer = 100 * welle(speed * elapsed); }
      while (winkel < 0) { winkel++; }
    }

Anweisungen: Deklaration (float/double, int/long/short/byte, bool/boolean, const), Zuweisung (= += -= *= /= %=), ++/--, if/else if/else, for, while, do-while,
break, continue, return, Funktionsaufruf, Block. Ausdruecke: + - * / %, Vergleiche, && || !, ?:, Funktionen (siehe BUILTINS), Konstanten (PI, E, true, false ...).
Alles ist eine Zahl: bool ist 0/1, int wird beim Zuweisen abgeschnitten, Division durch 0 ergibt 0. Wer ohne Deklaration einer unbekannten Variablen zuweist, legt
eine globale float-Variable an (so liefen die aelteren Skripte). Eine Schleife, die zu lange laeuft, bricht mit einem Fehler ab (MAX_STEPS je Aufruf).

Aufbau: Tokenizer -> Parser (AST aus Tupeln) -> Compiler (prueft Namen, Argumentzahlen, Gueltigkeitsbereiche und baut je Knoten eine Python-Funktion) ->
Program. Ausgefuehrt wird ueber execute(); der persistente Zustand einer Effekt-Instanz ist ein einfaches dict (nur globale Variablen und der Zufallsgenerator).
"""
from __future__ import annotations

import itertools
import math
import random
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, Set, Tuple

from app.fx_categories import OUTPUT_NAMES          # Ausgabe-Variablen aller Kategorien (Tabelle: app/fx_categories.py)

MAX_STEPS = 60000            # Schleifendurchlaeufe + Funktionsaufrufe je loop()-Aufruf
MAX_DEPTH = 24               # Schachtelungstiefe eigener Funktionen (Rekursion)

SYSTEM_VARS = ("t", "elapsed", "dt", "tick", "loop_count", "rate", "index", "count", "phase", "slots", "slots2")
CONSTANTS: Dict[str, float] = {
    "PI": math.pi, "TWO_PI": 2 * math.pi, "HALF_PI": math.pi / 2, "E": math.e,
    "true": 1.0, "false": 0.0, "HIGH": 1.0, "LOW": 0.0,
}
TYPE_ALIASES = {"float": "float", "double": "float", "int": "int", "long": "int", "short": "int", "byte": "int", "bool": "bool", "boolean": "bool", "void": "void"}
KEYWORDS = {"if", "else", "for", "while", "do", "break", "continue", "return", "const"} | set(TYPE_ALIASES)


class FxScriptError(Exception):
    def __init__(self, line: int, message: str) -> None:
        super().__init__(f"Zeile {line}: {message}")
        self.line = line
        self.message = message


class FxScriptRuntimeError(Exception):
    pass


# ---------------------------------------------------------------------------------------------- Eingebaute Funktionen
def _fract(x: float) -> float:
    return x - math.floor(x)


def _smoothstep(e0: float, e1: float, x: float) -> float:
    if e0 == e1:
        return 0.0 if x < e0 else 1.0
    k = max(0.0, min(1.0, (x - e0) / (e1 - e0)))
    return k * k * (3 - 2 * k)


def _map(x: float, a: float, b: float, c: float, d: float) -> float:
    return c if a == b else c + (x - a) * (d - c) / (b - a)


def _square(x: float, duty: float = 0.5) -> float:
    return 1.0 if _fract(x) < duty else 0.0


def _tri(x: float) -> float:
    return 1.0 - abs(2.0 * _fract(x) - 1.0)


def _mod(a: float, b: float) -> float:
    return a % b if b != 0 else 0.0


def _round(x: float) -> float:
    return float(math.floor(x + 0.5))


def _sign(x: float) -> float:
    return (x > 0) - (x < 0)


# name -> (erlaubte Argumentzahlen, Funktion). Beschreibungen stehen in der Anleitung (static/help/effect-studio.*.md).
BUILTINS: Dict[str, Tuple[Tuple[int, ...], Callable[..., float]]] = {
    "sin": ((1,), math.sin), "cos": ((1,), math.cos), "tan": ((1,), math.tan),
    "asin": ((1,), math.asin), "acos": ((1,), math.acos), "atan": ((1,), math.atan), "atan2": ((2,), math.atan2),
    "sqrt": ((1,), math.sqrt), "pow": ((2,), math.pow), "exp": ((1,), math.exp), "log": ((1,), math.log),
    "abs": ((1,), abs), "sign": ((1,), _sign), "min": ((2,), min), "max": ((2,), max),
    "floor": ((1,), math.floor), "ceil": ((1,), math.ceil), "round": ((1,), _round), "fract": ((1,), _fract), "mod": ((2,), _mod),
    "constrain": ((3,), lambda x, lo, hi: min(max(x, lo), hi)), "map": ((5,), _map), "lerp": ((3,), lambda a, b, k: a + (b - a) * k),
    "smoothstep": ((3,), _smoothstep), "saw": ((1,), _fract), "tri": ((1,), _tri), "square": ((1, 2), _square),
    "radians": ((1,), math.radians), "degrees": ((1,), math.degrees),
}
# Funktionen, die den Ablauf kennen muessen (Zufall, Ausgaben)
SPECIAL_FUNCTIONS: Dict[str, Tuple[int, ...]] = {"random": (0, 1, 2), "hsv": (3,), "slot": (1, 2)}
RESERVED_NAMES = set(SYSTEM_VARS) | set(OUTPUT_NAMES) | set(CONSTANTS) | KEYWORDS | set(BUILTINS) | set(SPECIAL_FUNCTIONS)


# ---------------------------------------------------------------------------------------------- Tokenizer
@dataclass(frozen=True)
class Token:
    kind: str   # "num" | "id" | "op" | "eof"
    value: Any
    line: int


_TOKEN_RE = re.compile(
    r"(?P<ws>\s+)|(?P<lc>//[^\n]*)|(?P<bc>/\*.*?\*/)|(?P<badc>/\*)"
    r"|(?P<num>(?:\d+\.\d*|\.\d+|\d+)(?:[eE][+-]?\d+)?)|(?P<id>[A-Za-z_][A-Za-z0-9_]*)"
    r"|(?P<op>\+\+|--|\+=|-=|\*=|/=|%=|==|!=|<=|>=|&&|\|\||[-+*/%<>=(){};,!?:])",
    re.S,
)


def tokenize(text: str) -> List[Token]:
    tokens: List[Token] = []
    line = 1
    pos = 0
    while pos < len(text):
        match = _TOKEN_RE.match(text, pos)
        if not match:
            raise FxScriptError(line, f"Unerwartetes Zeichen '{text[pos]}'")
        kind = match.lastgroup
        chunk = match.group()
        if kind == "badc":
            raise FxScriptError(line, "Kommentar '/*' ist nicht mit '*/' geschlossen")
        if kind == "num":
            tokens.append(Token("num", float(chunk), line))
        elif kind == "id":
            tokens.append(Token("id", chunk, line))
        elif kind == "op":
            tokens.append(Token("op", chunk, line))
        line += chunk.count("\n")
        pos = match.end()
    tokens.append(Token("eof", None, line))
    return tokens


# ---------------------------------------------------------------------------------------------- Parser
_ASSIGN_OPS = ("=", "+=", "-=", "*=", "/=", "%=")
_BIN_LEVELS = (("||",), ("&&",), ("==", "!="), ("<", "<=", ">", ">="), ("+", "-"), ("*", "/", "%"))


class _Parser:
    def __init__(self, tokens: List[Token]) -> None:
        self.tokens = tokens
        self.pos = 0

    # -- Hilfen
    def peek(self, offset: int = 0) -> Token:
        return self.tokens[min(self.pos + offset, len(self.tokens) - 1)]

    def next(self) -> Token:
        token = self.peek()
        self.pos += 1
        return token

    def is_op(self, value: str, offset: int = 0) -> bool:
        token = self.peek(offset)
        return token.kind == "op" and token.value == value

    def is_id(self, value: str, offset: int = 0) -> bool:
        token = self.peek(offset)
        return token.kind == "id" and token.value == value

    def is_type(self, offset: int = 0) -> bool:
        token = self.peek(offset)
        return token.kind == "id" and (token.value in TYPE_ALIASES or token.value == "const")

    @staticmethod
    def _found(token: Token) -> str:
        return "Dateiende" if token.kind == "eof" else f"'{token.value}'"

    def expect_op(self, value: str) -> Token:
        token = self.next()
        if token.kind != "op" or token.value != value:
            raise FxScriptError(token.line, f"'{value}' erwartet, gefunden {self._found(token)}")
        return token

    def expect_id(self, what: str) -> Token:
        token = self.next()
        if token.kind != "id":
            raise FxScriptError(token.line, f"{what} erwartet, gefunden {self._found(token)}")
        return token

    # -- Programm
    def program(self) -> List[tuple]:
        items: List[tuple] = []
        while self.peek().kind != "eof":
            items.append(self.top_level())
        return items

    def top_level(self) -> tuple:
        token = self.peek()
        if token.kind == "id" and self.is_op("(", 1):                       # loop() { ... } / setup() { ... } wie in Arduino ohne Rueckgabetyp
            return self.function("void")
        if self.is_type():
            start = self.pos
            const = False
            if self.is_id("const"):
                self.next()
                const = True
            type_token = self.expect_id("Typ")
            if type_token.value not in TYPE_ALIASES:
                raise FxScriptError(type_token.line, f"Typ erwartet, gefunden '{type_token.value}'")
            if self.peek().kind == "id" and self.is_op("(", 1):
                if const:
                    raise FxScriptError(type_token.line, "Eine Funktion kann nicht 'const' sein")
                self.pos = start
                return self.function(None)
            self.pos = start
            decl = self.declaration()
            self.expect_op(";")
            return decl
        raise FxScriptError(token.line, "Hier sind nur Variablen und Funktionen erlaubt (z. B. 'float x = 0;' oder 'loop() { ... }')")

    def function(self, default_type: Optional[str]) -> tuple:
        if default_type is None:
            type_token = self.next()
            ret = TYPE_ALIASES[type_token.value]
        else:
            ret = default_type
        name = self.expect_id("Funktionsname")
        self.expect_op("(")
        params: List[Tuple[str, str]] = []
        if self.is_id("void") and self.is_op(")", 1):
            self.next()
        while not self.is_op(")"):
            type_token = self.expect_id("Typ")
            if type_token.value not in TYPE_ALIASES or TYPE_ALIASES[type_token.value] == "void":
                raise FxScriptError(type_token.line, f"Parametertyp erwartet (float, int oder bool), gefunden '{type_token.value}'")
            param = self.expect_id("Parametername")
            params.append((param.value, TYPE_ALIASES[type_token.value]))
            if self.is_op(","):
                self.next()
            elif not self.is_op(")"):
                token = self.peek()
                raise FxScriptError(token.line, f"',' oder ')' erwartet, gefunden {self._found(token)}")
        self.expect_op(")")
        body = self.block()
        return ("func", name.line, name.value, ret, params, body)

    # -- Anweisungen
    def block(self) -> tuple:
        start = self.expect_op("{")
        stmts: List[tuple] = []
        while not self.is_op("}"):
            if self.peek().kind == "eof":
                raise FxScriptError(self.peek().line, "'}' erwartet, Dateiende gefunden")
            stmts.append(self.statement())
        self.expect_op("}")
        return ("block", start.line, stmts)

    def declaration(self) -> tuple:
        first = self.peek()
        const = False
        if self.is_id("const"):
            self.next()
            const = True
        type_token = self.expect_id("Typ")
        vtype = TYPE_ALIASES.get(type_token.value)
        if vtype is None or vtype == "void":
            raise FxScriptError(type_token.line, f"Variablentyp erwartet (float, int oder bool), gefunden '{type_token.value}'")
        items: List[Tuple[str, int, Optional[tuple]]] = []
        while True:
            name = self.expect_id("Variablenname")
            init = None
            if self.is_op("="):
                self.next()
                init = self.expr()
            elif const:
                raise FxScriptError(name.line, f"'const {name.value}' braucht einen Wert (z. B. '= 1;')")
            items.append((name.value, name.line, init))
            if self.is_op(","):
                self.next()
                continue
            break
        return ("decl", first.line, vtype, const, items)

    def simple(self) -> tuple:
        """Zuweisung, ++/-- oder Funktionsaufruf (ohne abschliessendes ';')."""
        token = self.peek()
        if token.kind == "op" and token.value in ("++", "--"):
            self.next()
            name = self.expect_id("Variablenname")
            return ("incdec", token.line, name.value, 1.0 if token.value == "++" else -1.0)
        if token.kind == "id":
            if self.peek(1).kind == "op" and self.peek(1).value in _ASSIGN_OPS:
                self.next()
                op = self.next().value
                return ("assign", token.line, token.value, op, self.expr())
            if self.peek(1).kind == "op" and self.peek(1).value in ("++", "--"):
                self.next()
                op = self.next().value
                return ("incdec", token.line, token.value, 1.0 if op == "++" else -1.0)
            if self.is_op("(", 1):
                return ("expr", token.line, self.expr())
        raise FxScriptError(token.line, "Anweisung erwartet (z. B. 'dimmer = 50;' oder 'x++;')")

    def statement(self) -> tuple:
        token = self.peek()
        if token.kind == "op":
            if token.value == "{":
                return self.block()
            if token.value == ";":
                self.next()
                return ("block", token.line, [])
        if token.kind == "id":
            word = token.value
            if word == "if":
                self.next()
                self.expect_op("(")
                cond = self.expr()
                self.expect_op(")")
                then = self.statement()
                other = None
                if self.is_id("else"):
                    self.next()
                    other = self.statement()
                return ("if", token.line, cond, then, other)
            if word == "while":
                self.next()
                self.expect_op("(")
                cond = self.expr()
                self.expect_op(")")
                return ("while", token.line, cond, self.statement())
            if word == "do":
                self.next()
                body = self.statement()
                if not self.is_id("while"):
                    raise FxScriptError(self.peek().line, f"'while' erwartet, gefunden {self._found(self.peek())}")
                self.next()
                self.expect_op("(")
                cond = self.expr()
                self.expect_op(")")
                self.expect_op(";")
                return ("dowhile", token.line, body, cond)
            if word == "for":
                self.next()
                self.expect_op("(")
                init = None
                if not self.is_op(";"):
                    init = self.declaration() if self.is_type() else self.simple()
                self.expect_op(";")
                cond = None if self.is_op(";") else self.expr()
                self.expect_op(";")
                step = None if self.is_op(")") else self.simple()
                self.expect_op(")")
                return ("for", token.line, init, cond, step, self.statement())
            if word in ("break", "continue"):
                self.next()
                self.expect_op(";")
                return (word, token.line)
            if word == "return":
                self.next()
                value = None if self.is_op(";") else self.expr()
                self.expect_op(";")
                return ("return", token.line, value)
            if self.is_type():
                decl = self.declaration()
                self.expect_op(";")
                return decl
            if word in ("else", "case", "switch"):
                raise FxScriptError(token.line, f"'{word}' ist hier nicht erlaubt" if word == "else" else f"'{word}' wird nicht unterstuetzt (nutze if / else if)")
        stmt = self.simple()
        self.expect_op(";")
        return stmt

    # -- Ausdruecke
    def expr(self) -> tuple:
        cond = self._binary(0)
        if self.is_op("?"):
            question = self.next()
            a = self.expr()
            self.expect_op(":")
            b = self.expr()
            return ("tern", question.line, cond, a, b)
        return cond

    def _binary(self, level: int) -> tuple:
        if level == len(_BIN_LEVELS):
            return self.unary()
        left = self._binary(level + 1)
        while self.peek().kind == "op" and self.peek().value in _BIN_LEVELS[level]:
            op = self.next()
            right = self._binary(level + 1)
            left = ("bin", op.line, op.value, left, right)
        return left

    def unary(self) -> tuple:
        token = self.peek()
        if token.kind == "op" and token.value in ("-", "!", "+"):
            self.next()
            operand = self.unary()
            return ("un", token.line, token.value, operand)
        return self.primary()

    def primary(self) -> tuple:
        token = self.next()
        if token.kind == "num":
            return ("num", token.line, token.value)
        if token.kind == "id":
            if self.is_op("("):
                self.next()
                args: List[tuple] = []
                if not self.is_op(")"):
                    args.append(self.expr())
                    while self.is_op(","):
                        self.next()
                        args.append(self.expr())
                self.expect_op(")")
                return ("call", token.line, token.value, args)
            return ("var", token.line, token.value)
        if token.kind == "op" and token.value == "(":
            inner = self.expr()
            self.expect_op(")")
            return inner
        raise FxScriptError(token.line, f"Ausdruck erwartet, gefunden {self._found(token)}")


# ---------------------------------------------------------------------------------------------- Ablauf (Laufzeitzustand eines loop()-Aufrufs)
_BREAK, _CONTINUE, _RETURN = 1, 2, 3


class _Run:
    __slots__ = ("sys", "g", "outs", "scopes", "steps", "ret", "depth", "rng")

    def __init__(self, sys_vars: Dict[str, float], g: Dict[str, Any], rng: random.Random) -> None:
        self.sys = sys_vars
        self.g = g
        self.outs: Dict[str, float] = {}
        self.scopes: List[Dict[str, float]] = [{}]
        self.steps = 0
        self.ret = 0.0
        self.depth = 0
        self.rng = rng

    def tick_step(self) -> None:
        self.steps += 1
        if self.steps > MAX_STEPS:
            raise FxScriptRuntimeError(f"Zu viele Schritte in einem Durchlauf (mehr als {MAX_STEPS}) - Endlosschleife?")


def _finite(x: float) -> float:
    return x if x == x and x not in (math.inf, -math.inf) else 0.0


def _coercer(vtype: str) -> Callable[[float], float]:
    if vtype == "int":
        return lambda x: float(int(x)) if x == x and abs(x) != math.inf else 0.0
    if vtype == "bool":
        return lambda x: 1.0 if x != 0 else 0.0
    return lambda x: x


# ---------------------------------------------------------------------------------------------- Compiler
@dataclass
class _Func:
    name: str
    ret: str
    params: List[Tuple[str, str]]
    body: Optional[Callable] = None
    line: int = 0


_program_ids = itertools.count(1)


@dataclass
class Program:
    """Uebersetztes Skript. `init` = globale Variablen mit Anfangswert (in Reihenfolge), `setup`/`loop` = aufrufbare Funktionen."""
    uid: int = field(default_factory=lambda: next(_program_ids))
    init: List[Tuple[str, Optional[Callable]]] = field(default_factory=list)
    setup: Optional[Callable] = None
    loop: Optional[Callable] = None
    globals_declared: Set[str] = field(default_factory=set)
    assigned_outputs: Set[str] = field(default_factory=set)      # Ausgaben, denen das Skript irgendwo einen Wert zuweist (hsv() zaehlt als r, g, b)


class _Compiler:
    def __init__(self, items: List[tuple], params: Dict[str, Any], internals: Dict[str, float], outputs: Sequence[str]) -> None:
        self.items = items
        self.param_names = set(params)               # nur lesbar (Regler aus #VAR)
        self.internals = dict(internals)             # #VAR ... Internal: globale Variablen mit Anfangswert
        self.outputs = set(OUTPUT_NAMES)
        self.category_outputs = set(outputs)
        self.global_types: Dict[str, str] = {}
        self.global_const: Set[str] = set()
        self.assigned_outputs: Set[str] = set()
        self.funcs: Dict[str, _Func] = {}
        self.scopes: List[Dict[str, Tuple[str, bool]]] = []     # Compile-Zeit: Name -> (Typ, const)
        self.loop_depth = 0
        self.current: Optional[_Func] = None

    # -- Namensaufloesung
    def _name_problem(self, name: str) -> Optional[str]:
        """Warum ein Name nicht als eigene Variable/Funktion taugt (None = frei)."""
        if name in OUTPUT_NAMES:
            return f"'{name}' ist eine Ausgabe des Effekts (dimmer, r, g, b, pan, tilt) und kann nicht als eigener Name dienen"
        if name in SYSTEM_VARS or name in CONSTANTS:
            return f"'{name}' ist eine Systemvariable oder Konstante und kann nicht als eigener Name dienen"
        if name in KEYWORDS or name in BUILTINS or name in SPECIAL_FUNCTIONS:
            return f"'{name}' ist ein Schluesselwort oder eine eingebaute Funktion"
        if name in self.param_names:
            return f"'{name}' ist schon ein Regler (#VAR)"
        if name in self.funcs:
            return f"'{name}' ist schon eine Funktion"
        return None

    def _declare_local(self, name: str, vtype: str, const: bool, line: int) -> None:
        problem = self._name_problem(name)
        if problem:
            raise FxScriptError(line, problem)
        if name in self.scopes[-1]:
            raise FxScriptError(line, f"'{name}' ist in diesem Block schon deklariert")
        self.scopes[-1][name] = (vtype, const)

    def _lookup(self, name: str) -> Optional[Tuple[str, str, bool]]:
        """(Art, Typ, const) mit Art = local | global | sys | param | out | const, sonst None."""
        for scope in reversed(self.scopes):
            if name in scope:
                return ("local", scope[name][0], scope[name][1])
        if name in self.global_types:
            return ("global", self.global_types[name], name in self.global_const)
        if name in SYSTEM_VARS:
            return ("sys", "float", True)
        if name in self.param_names:
            return ("param", "float", True)
        if name in self.outputs:
            return ("out", "float", False)
        if name in CONSTANTS:
            return ("const", "float", True)
        return None

    # -- Ausdruecke
    def expr(self, node: tuple) -> Callable[[_Run], float]:
        kind = node[0]
        line = node[1]
        if kind == "num":
            value = node[2]
            return lambda rt: value
        if kind == "var":
            name = node[2]
            found = self._lookup(name)
            if found is None:
                raise FxScriptError(line, f"Unbekannte Variable '{name}'")
            where = found[0]
            if where == "const":
                value = CONSTANTS[name]
                return lambda rt: value
            if where in ("sys", "param"):
                return lambda rt: rt.sys.get(name, 0.0)
            if where == "out":
                return lambda rt: rt.outs.get(name, 0.0)
            if where == "global":
                return lambda rt: rt.g.get(name, 0.0)

            def read_local(rt: _Run) -> float:
                for scope in reversed(rt.scopes):
                    if name in scope:
                        return scope[name]
                return 0.0
            return read_local
        if kind == "un":
            op = node[2]
            inner = self.expr(node[3])
            if op == "-":
                return lambda rt: -inner(rt)
            if op == "+":
                return inner
            return lambda rt: 0.0 if inner(rt) else 1.0
        if kind == "tern":
            cond, a, b = self.expr(node[2]), self.expr(node[3]), self.expr(node[4])
            return lambda rt: a(rt) if cond(rt) else b(rt)
        if kind == "bin":
            return self._binary(node)
        if kind == "call":
            return self._call(node, as_value=True)
        raise FxScriptError(line, f"Unbekannter Ausdruck {kind}")

    def _binary(self, node: tuple) -> Callable[[_Run], float]:
        op = node[2]
        a, b = self.expr(node[3]), self.expr(node[4])
        if op == "&&":
            return lambda rt: 1.0 if (a(rt) and b(rt)) else 0.0
        if op == "||":
            return lambda rt: 1.0 if (a(rt) or b(rt)) else 0.0
        if op == "+":
            return lambda rt: a(rt) + b(rt)
        if op == "-":
            return lambda rt: a(rt) - b(rt)
        if op == "*":
            return lambda rt: a(rt) * b(rt)
        if op == "/":
            def divide(rt: _Run) -> float:
                x, y = a(rt), b(rt)
                return x / y if y != 0 else 0.0
            return divide
        if op == "%":
            def modulo(rt: _Run) -> float:
                x, y = a(rt), b(rt)
                return math.fmod(x, y) if y != 0 else 0.0
            return modulo
        compare = {"==": lambda x, y: x == y, "!=": lambda x, y: x != y, "<": lambda x, y: x < y,
                   "<=": lambda x, y: x <= y, ">": lambda x, y: x > y, ">=": lambda x, y: x >= y}[op]
        return lambda rt: 1.0 if compare(a(rt), b(rt)) else 0.0

    def _call(self, node: tuple, as_value: bool) -> Callable[[_Run], float]:
        line, name, arg_nodes = node[1], node[2], node[3]
        args = [self.expr(n) for n in arg_nodes]
        count = len(args)
        if name in self.funcs:
            func = self.funcs[name]
            if count != len(func.params):
                raise FxScriptError(line, f"{name}() erwartet {len(func.params)} Argument(e)")
            if as_value and func.ret == "void":
                raise FxScriptError(line, f"{name}() liefert keinen Wert (void)")
            coerce = [_coercer(t) for _, t in func.params]
            names = [p for p, _ in func.params]

            def call_user(rt: _Run) -> float:
                values = [c(a(rt)) for c, a in zip(coerce, args)]
                rt.tick_step()
                if rt.depth >= MAX_DEPTH:
                    raise FxScriptRuntimeError(f"Funktionen sind zu tief verschachtelt ({name}() ruft sich zu oft selbst auf)")
                saved = rt.scopes
                rt.scopes = [dict(zip(names, values))]
                rt.depth += 1
                rt.ret = 0.0
                try:
                    func.body(rt)
                finally:
                    rt.depth -= 1
                    rt.scopes = saved
                result = rt.ret
                rt.ret = 0.0
                return result
            return call_user
        if name in BUILTINS:
            arities, impl = BUILTINS[name]
            if count not in arities:
                raise FxScriptError(line, f"{name}() erwartet {' oder '.join(str(n) for n in arities)} Argument(e)")

            def call_builtin(rt: _Run) -> float:
                try:
                    return float(impl(*[a(rt) for a in args]))
                except (ValueError, OverflowError, ZeroDivisionError):
                    return 0.0
            return call_builtin
        if name in SPECIAL_FUNCTIONS:
            if count not in SPECIAL_FUNCTIONS[name]:
                raise FxScriptError(line, f"{name}() erwartet {' oder '.join(str(n) for n in SPECIAL_FUNCTIONS[name])} Argument(e)")
            if name == "random":
                def call_random(rt: _Run) -> float:
                    values = [a(rt) for a in args]
                    if not values:
                        return rt.rng.random()
                    low, high = (0.0, values[0]) if len(values) == 1 else (values[0], values[1])
                    return low + rt.rng.random() * (high - low)
                return call_random

            if name == "slot":
                def call_slot(rt: _Run) -> float:
                    # n-tes Gobo (0 = erstes, meist "offen") als Wert in Prozent; zweites Argument = Gobo-Rad (1 oder 2). Die Listen kennt nur die Gobo-Kategorie (pro Geraet
                    # verschieden), sonst 0
                    wheel = args[1](rt) if len(args) > 1 else 1
                    table = rt.sys.get("__slot_list2" if wheel == 2 else "__slot_list") or []
                    if not table:
                        return 0.0
                    index = args[0](rt)
                    return float(table[max(0, min(len(table) - 1, int(index) if index == index else 0))])
                return call_slot

            self.assigned_outputs.update("rgb")

            def call_hsv(rt: _Run) -> float:
                h, s, v = [a(rt) for a in args]
                h = _fract(h) * 6.0
                s, v = max(0.0, min(1.0, s)), max(0.0, min(1.0, v))
                i = int(h) % 6
                f = h - int(h)
                p, q, t_ = v * (1 - s), v * (1 - s * f), v * (1 - s * (1 - f))
                red, green, blue = [(v, t_, p), (q, v, p), (p, v, t_), (p, q, v), (t_, p, v), (v, p, q)][i]
                rt.outs["r"], rt.outs["g"], rt.outs["b"] = red * 255.0, green * 255.0, blue * 255.0
                return 0.0
            return call_hsv
        raise FxScriptError(line, f"Unbekannte Funktion '{name}()'")

    # -- Anweisungen: jede liefert None oder ein Signal (_BREAK/_CONTINUE/_RETURN)
    def stmt(self, node: tuple) -> Callable[[_Run], Optional[int]]:
        kind = node[0]
        line = node[1]
        if kind == "block":
            self.scopes.append({})
            body = [self.stmt(s) for s in node[2]]
            self.scopes.pop()

            def run_block(rt: _Run) -> Optional[int]:
                rt.scopes.append({})
                try:
                    for s in body:
                        signal = s(rt)
                        if signal:
                            return signal
                finally:
                    rt.scopes.pop()
                return None
            return run_block
        if kind == "decl":
            return self._decl(node)
        if kind == "assign":
            return self._assign(node)
        if kind == "incdec":
            return self._assign(("assign", line, node[2], "+=" if node[3] > 0 else "-=", ("num", line, 1.0)))
        if kind == "expr":
            call = self._call(node[2], as_value=False)

            def run_expr(rt: _Run) -> Optional[int]:
                call(rt)
                return None
            return run_expr
        if kind == "if":
            cond = self.expr(node[2])
            then = self.stmt(node[3])
            other = self.stmt(node[4]) if node[4] is not None else None
            if other is None:
                return lambda rt: then(rt) if cond(rt) else None
            return lambda rt: then(rt) if cond(rt) else other(rt)
        if kind in ("while", "dowhile"):
            return self._while(node)
        if kind == "for":
            return self._for(node)
        if kind in ("break", "continue"):
            if self.loop_depth == 0:
                raise FxScriptError(line, f"'{kind}' ist nur in einer Schleife erlaubt")
            signal = _BREAK if kind == "break" else _CONTINUE
            return lambda rt: signal
        if kind == "return":
            return self._return(node)
        raise FxScriptError(line, f"Unbekannte Anweisung {kind}")

    def _target(self, name: str, line: int) -> Tuple[str, str]:
        """Ziel einer Zuweisung -> (Art, Typ); unbekannte Namen werden zu globalen float-Variablen (aeltere Skripte)."""
        found = self._lookup(name)
        if found is None:
            if name in self.funcs:
                raise FxScriptError(line, f"'{name}' ist eine Funktion")
            self.global_types[name] = "float"
            return ("global", "float")
        where, vtype, const = found
        if where == "sys":
            raise FxScriptError(line, f"'{name}' ist eine Systemvariable und kann nicht geaendert werden")
        if where == "param":
            raise FxScriptError(line, f"'{name}' ist ein Regler (#VAR) und kann im Skript nicht geaendert werden")
        if where == "const" or const:
            raise FxScriptError(line, f"'{name}' ist konstant und kann nicht geaendert werden")
        return (where, vtype)

    def _assign(self, node: tuple) -> Callable[[_Run], Optional[int]]:
        line, name, op, value_node = node[1], node[2], node[3], node[4]
        value = self.expr(value_node)
        where, vtype = self._target(name, line)
        coerce = _coercer(vtype)
        read = self.expr(("var", line, name)) if op != "=" else None
        if op == "+=":
            compute = lambda rt: read(rt) + value(rt)
        elif op == "-=":
            compute = lambda rt: read(rt) - value(rt)
        elif op == "*=":
            compute = lambda rt: read(rt) * value(rt)
        elif op == "/=":
            compute = lambda rt: (read(rt) / v) if (v := value(rt)) != 0 else 0.0
        elif op == "%=":
            compute = lambda rt: math.fmod(read(rt), v) if (v := value(rt)) != 0 else 0.0
        else:
            compute = value
        if where == "out":
            self.assigned_outputs.add(name)
            def set_out(rt: _Run) -> Optional[int]:
                rt.outs[name] = compute(rt)
                return None
            return set_out
        if where == "global":
            def set_global(rt: _Run) -> Optional[int]:
                rt.g[name] = coerce(compute(rt))
                return None
            return set_global

        def set_local(rt: _Run) -> Optional[int]:
            result = coerce(compute(rt))
            for scope in reversed(rt.scopes):
                if name in scope:
                    scope[name] = result
                    break
            return None
        return set_local

    def _decl(self, node: tuple) -> Callable[[_Run], Optional[int]]:
        _, line, vtype, const, items = node
        coerce = _coercer(vtype)
        steps: List[Tuple[str, Optional[Callable[[_Run], float]]]] = []
        for name, item_line, init in items:
            init_fn = self.expr(init) if init is not None else None          # Anfangswert darf die neue Variable noch nicht sehen
            self._declare_local(name, vtype, const, item_line)
            steps.append((name, init_fn))

        def run_decl(rt: _Run) -> Optional[int]:
            scope = rt.scopes[-1]
            for name, init_fn in steps:
                scope[name] = coerce(init_fn(rt)) if init_fn is not None else 0.0
            return None
        return run_decl

    def _while(self, node: tuple) -> Callable[[_Run], Optional[int]]:
        kind = node[0]
        self.loop_depth += 1
        if kind == "while":
            cond, body = self.expr(node[2]), self.stmt(node[3])
        else:
            body, cond = self.stmt(node[2]), self.expr(node[3])
        self.loop_depth -= 1
        if kind == "while":
            def run_while(rt: _Run) -> Optional[int]:
                while cond(rt):
                    rt.tick_step()
                    signal = body(rt)
                    if signal == _BREAK:
                        break
                    if signal == _RETURN:
                        return signal
                return None
            return run_while

        def run_do_while(rt: _Run) -> Optional[int]:
            while True:
                rt.tick_step()
                signal = body(rt)
                if signal == _BREAK:
                    break
                if signal == _RETURN:
                    return signal
                if not cond(rt):
                    break
            return None
        return run_do_while

    def _for(self, node: tuple) -> Callable[[_Run], Optional[int]]:
        _, line, init, cond, step, body_node = node
        self.scopes.append({})
        init_fn = self.stmt(init) if init is not None else None
        cond_fn = self.expr(cond) if cond is not None else None
        step_fn = self.stmt(step) if step is not None else None
        self.loop_depth += 1
        body = self.stmt(body_node)
        self.loop_depth -= 1
        self.scopes.pop()

        def run_for(rt: _Run) -> Optional[int]:
            rt.scopes.append({})
            try:
                if init_fn:
                    init_fn(rt)
                while cond_fn is None or cond_fn(rt):
                    rt.tick_step()
                    signal = body(rt)
                    if signal == _BREAK:
                        break
                    if signal == _RETURN:
                        return signal
                    if step_fn:
                        step_fn(rt)
            finally:
                rt.scopes.pop()
            return None
        return run_for

    def _return(self, node: tuple) -> Callable[[_Run], Optional[int]]:
        line, value_node = node[1], node[2]
        func = self.current
        if func is not None and func.ret == "void" and value_node is not None:
            raise FxScriptError(line, f"{func.name}() ist void und kann keinen Wert zurueckgeben")
        if func is not None and func.ret != "void" and value_node is None:
            raise FxScriptError(line, f"{func.name}() muss einen Wert zurueckgeben")
        value = self.expr(value_node) if value_node is not None else None
        coerce = _coercer(func.ret) if func is not None and func.ret != "void" else (lambda x: x)

        def run_return(rt: _Run) -> Optional[int]:
            rt.ret = coerce(value(rt)) if value is not None else 0.0
            return _RETURN
        return run_return

    # -- Programm
    def _implicit_globals(self) -> List[str]:
        """Namen, die irgendwo zugewiesen, aber nirgends deklariert sind: aeltere Skripte legen so ihre persistenten Variablen an."""
        assigned: List[str] = []
        declared: Set[str] = set()

        def walk(node: Any) -> None:
            if node is None:
                return
            if isinstance(node, list):
                for child in node:
                    walk(child)
                return
            kind = node[0]
            if kind == "func":
                declared.update(p for p, _ in node[4])
                walk(node[5])
            elif kind == "block":
                walk(node[2])
            elif kind == "decl":
                declared.update(name for name, _, _ in node[4])
            elif kind in ("assign", "incdec"):
                assigned.append(node[2])
            elif kind == "if":
                walk(node[3])
                walk(node[4])
            elif kind == "while":
                walk(node[3])
            elif kind == "dowhile":
                walk(node[2])
            elif kind == "for":
                walk(node[2])
                walk(node[4])
                walk(node[5])

        walk(self.items)
        known = set(SYSTEM_VARS) | self.param_names | self.outputs | set(CONSTANTS) | set(self.global_types) | declared
        return [name for name in dict.fromkeys(assigned) if name not in known and name not in self.funcs]

    def compile(self) -> Program:
        program = Program()
        # 1. Funktionen anmelden (Aufrufe duerfen vor der Definition stehen), globale Deklarationen eintragen
        for name, value in self.internals.items():
            self.global_types[name] = "float"
        funcs = [item for item in self.items if item[0] == "func"]
        for item in funcs:
            _, line, name, ret, params, _ = item
            if name in self.funcs:
                raise FxScriptError(line, f"Funktion '{name}' ist doppelt definiert")
            if name in RESERVED_NAMES or name in self.param_names:
                raise FxScriptError(line, self._name_problem(name) or f"'{name}' kann keine Funktion sein")
            if name in ("loop", "setup") and (params or ret != "void"):
                raise FxScriptError(line, f"{name}() hat keine Parameter und keinen Rueckgabewert (void)")
            self.funcs[name] = _Func(name, ret, params, None, line)
        if "loop" not in self.funcs:
            raise FxScriptError(self.items[0][1] if self.items else 1, "loop() erwartet")
        # 2. Globale Variablen (in Reihenfolge; der Anfangswert sieht nur die davor)
        self.scopes = [{}]
        for name in self._implicit_globals():
            self.global_types[name] = "float"
        for name, value in self.internals.items():
            program.init.append((name, (lambda v: (lambda rt: v))(value)))
            program.globals_declared.add(name)
        for item in self.items:
            if item[0] != "decl":
                continue
            _, line, vtype, const, entries = item
            coerce = _coercer(vtype)
            for name, entry_line, init in entries:
                init_fn = self.expr(init) if init is not None else None
                problem = self._name_problem(name)
                if problem or name in self.global_types:
                    raise FxScriptError(entry_line, problem or f"'{name}' ist schon als globale Variable vergeben")
                self.global_types[name] = vtype
                if const:
                    self.global_const.add(name)
                program.globals_declared.add(name)
                program.init.append((name, (lambda f, c: (lambda rt: c(f(rt))))(init_fn, coerce) if init_fn else (lambda rt: 0.0)))
        # 3. Funktionskoerper
        for item in funcs:
            _, line, name, ret, params, body = item
            func = self.funcs[name]
            self.current = func
            self.scopes = [{}]
            for pname, ptype in params:
                self._declare_local(pname, ptype, False, line)
            inner = self.stmt(body)
            self.current = None

            def make_body(inner_fn: Callable[[_Run], Optional[int]]) -> Callable[[_Run], None]:
                def run_body(rt: _Run) -> None:
                    inner_fn(rt)
                return run_body
            func.body = make_body(inner)
        program.setup = self.funcs["setup"].body if "setup" in self.funcs else None
        program.loop = self.funcs["loop"].body
        program.assigned_outputs = set(self.assigned_outputs)
        # Zuweisungen an unbekannte Namen haben globale Variablen angelegt: sie starten bei 0
        for name in self.global_types:
            if name not in program.globals_declared:
                program.init.append((name, None))
                program.globals_declared.add(name)
        return program


def compile_program(text: str, params: Dict[str, Any], internals: Dict[str, float], outputs: Sequence[str]) -> Program:
    """Uebersetzt den Skripttext (ohne Header-Zeilen). params = Namen der Regler (lesbar), internals = #VAR ... Internal mit Anfangswert."""
    items = _Parser(tokenize(text)).program()
    return _Compiler(items, params, internals, outputs).compile()


# ---------------------------------------------------------------------------------------------- Ausfuehrung
def execute(program: Program, state: Dict[str, Any], sys_vars: Dict[str, float], outputs: Sequence[str], seed: int = 0) -> Dict[str, float]:
    """Ein loop()-Aufruf. `state` ist der Speicher der Instanz (globale Variablen); ein leerer `state` startet den Effekt neu (Anfangswerte + setup()).
    Wurde das Skript im Betrieb geaendert (anderes Program), bleiben die vorhandenen Variablen erhalten und nur neue werden angelegt."""
    fresh = "__rng" not in state
    if fresh:
        state["__rng"] = random.Random(seed * 7919 + 1)
    run = _Run(sys_vars, state, state["__rng"])
    if fresh or state.get("__program") != program.uid:
        for name, init in program.init:
            if name not in state:
                state[name] = init(run) if init is not None else 0.0
        state["__program"] = program.uid
        if fresh and program.setup is not None:
            program.setup(run)
            run.scopes = [{}]
    program.loop(run)
    return {name: _finite(run.outs[name]) for name in outputs if name in run.outs}
