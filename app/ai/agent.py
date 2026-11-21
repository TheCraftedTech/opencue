# Copyright (C) 2026 Samuel Zenker
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Der Assistent als Dienst: Einstellungen, Chats und der Ablauf einer Antwort.

Eine Antwort (`start` -> `_run`): Nachricht speichern, Verlauf zusammenstellen, das Modell fragen und die Antwort Stueck fuer Stueck an die Oberflaeche melden
(Ereignisse siehe `_run`). Pro Chat laeuft hoechstens eine Antwort. Das Modell antwortet immer selbst - OpenCue schreibt keine Antworttexte.
Der Modus (siehe modes.py) steht je Chat und je Nachricht; im Chat kann er jederzeit gewechselt werden.

Modus "Arbeiten" = Agenten-Schleife: das Modell antwortet (gestreamt); ruft es Funktionen auf (app/ai/tools), werden sie ausgefuehrt und das Modell wird mit den
Ergebnissen neu gefragt - bis es ohne Aufruf antwortet. Fehler einer Funktion gehen als Ergebnis zurueck, das Modell kann es mit korrigierten Werten neu versuchen.
Es gibt keine feste Rundenzahl; zwei Grenzen schuetzen: `MAX_TOOL_CALLS` je Frage und `MAX_REPEATS` (derselbe Aufruf mit denselben Werten). Beim Abbruch schreibt
das Modell (ohne Funktionen) die Antwort aus dem, was es bis dahin hat.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import threading
import time
import uuid
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple

from app.ai import manual, modes, tools
from app.ai import guide  # noqa: F401  (meldet die Funktionen des Wegweisers an)
from app.ai.chats import ChatStore
from app.ai.config import clean_config, clean_tool_names
from app.ai.errors import AiError
from app.ai.ollama import OllamaClient, model_caps
from app.ai.thinking import ThinkSplit
from app.ai.toolcalls import extract_text_calls, looks_like_call, new_call
from app.ai.tools import ToolContext
from app.ai.tools.helpers import today_text

logger = logging.getLogger("opencue.ai")

Emit = Callable[[Dict[str, Any]], Awaitable[None]]
MAX_TEXT = 8000
FLUSH_S = 0.04                  # Stuecke der Antwort werden gesammelt und alle ~40 ms gemeldet (nicht jedes Wort einzeln)
RESERVE_TOKENS = 600            # Platz im Kontextfenster fuer die Antwort selbst
MAX_TOOL_CALLS = 30             # Funktionsaufrufe je Frage
MAX_REPEATS = 3                 # derselbe Aufruf (gleiche Werte) hoechstens so oft je Frage
TOOL_TIMEOUT_S = 60
EARLIER_TURNS = 6               # so viele fruehere Fragen stehen in der Zusammenfassung
EARLIER_CHARS = 160             # und so lang darf jeder Teil davon sein
EARLIER_RESULT_CHARS = 90       # ein Funktionsergebnis darin (laenger wuerde das Modell es in seiner Antwort wiederholen)
THINK_EXTRA = 2500              # zusaetzliche Tokens, wenn das Modell vor der Antwort denkt (das Denken zaehlt zur Antwortgrenze "num_predict")
THINK_HISTORY_CHARS = 2000      # so viel vom Denken geht innerhalb EINER Frage mit den Funktionsaufrufen zurueck an das Modell
TITLE_SYSTEM = ("You write short titles for chats. Reply with the title only: 2 to 5 words, no quotes, no full stop, written in the language of the conversation. "
                "Do not answer the user and do not explain.")
ALL_TOOLS_SHARE = 0.6           # "alle auf einmal": hoechstens so viel vom Kontextfenster darf die Liste der Funktionen einnehmen, sonst gilt fuer die Frage der Modus "core"
TITLE_WAIT_S = 60               # ein Chat mit nur EINER Frage wird so lange nicht benannt: kommt eine zweite, gibt es mehr Zusammenhang fuer den Titel; sonst nach dieser Zeit
LIMIT_MESSAGE = ("The model used up the answer limit before it finished (thinking counts too). Raise 'Longest answer' in Settings -> AI assistant, "
                 "or ask a shorter question.")

# Wird dem Ergebnis nur in der Anfrage angehaengt (nicht gespeichert, nicht gezeigt): kleine Modelle rufen sonst nach jedem Ergebnis noch eine Funktion auf, statt zu antworten.
NOTE_OK = "\n\n(If this result answers the user's question, now reply to the user in plain words. Call another function only if it is still needed.)"
NOTE_OPEN = "\n\n(This only shows which functions you can call now. You have NOT answered the user yet: now call the function you need, by its name.)"
# Wird nur in der Anfrage an die aktuelle Frage gehaengt (nicht gespeichert, nicht gezeigt): kleine Modelle antworten sonst aus dem Gedaechtnis und erfinden Rechenergebnisse.
NOTE_QUESTION = "\n\n(If the message is a greeting, thanks, small talk, a question about you or an explanation of a term or of how something works: answer in words, without a function. Everything else about the user's show - looking at or changing fixtures, brightness, colours, groups, cue lists, effects, variables - and every calculation, random number, date and time of day needs a function: call it, also for a short follow-up question, and never answer those from memory or make something up. If no function can give it, say plainly that you cannot do that yet.)"
# Wegweiser: statt der Show-Regeln die Regel "nachschlagen, nichts erfinden"
NOTE_GUIDE = ("\n\n(If the message is a greeting, thanks or small talk: answer in words, without a function. If it asks how something in the program works, where something is, what a setting does or how to do something: "
              "call find_help and answer ONLY from its result - never from memory, never invent menu items or buttons. If it asks to open or find a dialog: call show_dialog. "
              "If the message asks to operate the lights or the show, say that this is done in the Work mode.)")
NOTE_ERROR = ("\n\n(This call failed. Read the error. If a value was only written wrongly (format, spelling), correct your values and call again. If the thing the user asked for does not exist "
                  "(for example a fixture number), do NOT pick another one yourself: tell the user plainly that it does not exist and what does exist, and do not claim that anything was done.)")
NOTE_DENIED = "\n\n(The user did not allow this. Do not call it again. Tell the user in one short sentence that you did not do it and why - do not claim that it was done.)"
ASK_TIMEOUT_S = 600                                                                          # so lange wartet eine Rueckfrage auf die Antwort des Benutzers (dann gilt sie als "nein")
WRAP_UP = {"en": "Stop calling functions now. Using the results above, answer my question in plain words. If something did not work, say what.",
           "de": "Rufe jetzt keine Funktionen mehr auf. Beantworte meine Frage in einfachen Worten anhand der Ergebnisse oben. Hat etwas nicht geklappt, sage, was."}


def estimate_tokens(value: Any) -> int:
    return int(len(json.dumps(value, ensure_ascii=False)) / 3) + 4


def _model_item(m: Dict[str, Any], with_tools: bool) -> Optional[Dict[str, Any]]:
    """Eine gespeicherte Nachricht im Format des Modells (None: gehoert nicht in den Verlauf)."""
    role, content = m.get("role"), str(m.get("content") or "")
    if m.get("error") or m.get("manual"):                       # von Hand aufgerufene Funktionen (/read_fixtures ...) gehoeren nicht zum Gespraech mit dem Modell
        return None
    if role == "user":
        return {"role": "user", "content": content} if content else None
    if role == "assistant":
        if m.get("tool_calls"):
            if not with_tools:
                return None
            item = {"role": "assistant", "content": content, "tool_calls": [{"function": {"name": c["name"], "arguments": c.get("arguments") or {}}} for c in m["tool_calls"]]}
            if m.get("thinking"):
                item["thinking"] = str(m["thinking"])[-THINK_HISTORY_CHARS:]            # das Modell setzt seine Gedanken innerhalb der Frage fort
            return item
        return {"role": "assistant", "content": content} if content else None
    if role == "tool" and with_tools:
        return {"role": "tool", "tool_name": m.get("tool_name", ""), "content": content + (NOTE_DENIED if m.get("denied") else NOTE_ERROR if m.get("ok") is False else NOTE_OPEN if m.get("opener") else NOTE_OK)}
    return None


def _short(value: Any, limit: int) -> str:
    text = " ".join(str(value or "").split())
    return text if len(text) <= limit else text[:limit - 3].rstrip() + "..."


def earlier_summary(messages: List[Dict[str, Any]]) -> str:
    """Eine kurze Zusammenfassung der FRUEHEREN Fragen dieses Chats fuer den Modus mit Funktionen: Frage, gerufene Funktionen mit Werten und Ergebnis - bei Fragen ohne
    Funktion nur die Frage - nie eine fruehere TEXTantwort: sie kann aus dem Chat-Modus stammen und erfunden sein, das Modell wiederholt sie sonst. Frueher als echte Nachrichten mitgeschickt, ahmten kleine Modelle die alten Textantworten nach und rechneten aus dem Gedaechtnis, statt die Funktion
    zu rufen; als Zusammenfassung beim Fragetext bleibt der Zusammenhang ('und davon die Haelfte') erhalten, ohne dass es etwas nachzuahmen gibt."""
    turns: List[Dict[str, Any]] = []
    for m in messages:
        if m.get("manual"):
            continue
        role = m.get("role")
        if role == "user" and m.get("content"):
            turns.append({"q": m["content"], "calls": [], "a": ""})
        elif not turns or m.get("error"):
            continue
        elif role == "assistant" and m.get("tool_calls"):
            turns[-1]["calls"].extend({"id": c["id"], "name": c["name"], "args": c.get("arguments") or {}, "result": ""} for c in m["tool_calls"])
        elif role == "tool":
            for c in turns[-1]["calls"]:
                if c["id"] == m.get("call_id"):
                    c["result"] = _short(m.get("content"), EARLIER_RESULT_CHARS)
        elif role == "assistant" and m.get("content"):
            turns[-1]["a"] = _short(m["content"], EARLIER_CHARS)
    lines = []
    for turn in turns[-EARLIER_TURNS:]:
        parts = [f'asked: "{_short(turn["q"], EARLIER_CHARS)}"']
        for c in turn["calls"]:
            tool = tools.get_tool(c["name"])
            if tool is not None and tool.keep_result:                 # nur Ergebnisse, die nie veralten (eine Rechnung): 'und davon die Haelfte' braucht sie. Show-Daten, Uhrzeit, Zufallszahlen
                args = _short(json.dumps(c["args"], ensure_ascii=False), EARLIER_CHARS)      # veralten - sie stehen NICHT drin und auch kein Hinweis 'ruf es nochmal auf' (gemessen: das Modell
                parts.append(f'called {c["name"]}({args}) -> {c["result"]}')                 # rief danach auch bei 'Danke' die Funktion wieder auf)
        lines.append("; ".join(parts))
    return "(These earlier questions are already answered - do not answer or repeat them, they are only for context: " + " | ".join(lines) + ")" if lines else ""


def history_for_model(messages: List[Dict[str, Any]], budget: int, with_tools: bool = False, note: str = "") -> List[Dict[str, Any]]:
    """Die gespeicherten Nachrichten im Format des Modells. Ohne Funktionen (Chat): alle Fragen und Antworten mit Text. Mit Funktionen (Arbeiten): nur die aktuelle Frage mit allem,
    was seither geschah (Funktionsaufrufe und -ergebnisse als echte Nachrichten); die fruehere Unterhaltung steht als kurze Zusammenfassung beim Fragetext (siehe earlier_summary).
    Passt es nicht in `budget` Tokens, fallen im Chat die AELTESTEN Nachrichten weg, in beiden Faellen werden alte Ergebnisse gekuerzt; die aktuelle Frage fliegt NIE raus.
    Gespeichert bleibt alles."""
    last_user = max((i for i, m in enumerate(messages) if m.get("role") == "user" and m.get("content") and not m.get("manual")), default=-1)
    items: List[Tuple[Dict[str, Any], int]] = []
    current_at = 0
    for i, m in enumerate(messages):
        if with_tools and i < last_user:
            continue
        item = _model_item(m, with_tools)
        if item is None:
            continue
        if i == last_user:
            current_at = len(items)
            if with_tools:
                earlier = earlier_summary(messages[:last_user])
                item = {**item, "content": item["content"] + ("\n\n" + earlier if earlier else "") + (note or NOTE_QUESTION)}
        items.append((item, estimate_tokens(item)))
    total = sum(n for _, n in items)
    if total > budget:                                                           # lange Ergebnisse frueherer Schritte kuerzen (das letzte bleibt ganz)
        tool_at = [i for i, (item, _) in enumerate(items) if item["role"] == "tool"]
        for i in tool_at[:-1]:
            item, size = items[i]
            if size > 120:
                short = {**item, "content": str(item["content"])[:200] + " ...(shortened)"}
                items[i] = (short, estimate_tokens(short))
        total = sum(n for _, n in items)
    start = 0
    while total > budget and start < current_at:                                 # die aktuelle Frage fliegt NIE raus
        total -= items[start][1]
        start += 1
    while start < current_at and items[start][0]["role"] != "user":              # nie mit einer Antwort ohne ihre Frage beginnen
        start += 1
    return [item for item, _ in items[start:]]


class AssistantService:
    def __init__(self) -> None:
        self.config: Dict[str, Any] = clean_config({})
        self.store = ChatStore()
        self.runs: Dict[str, "asyncio.Task"] = {}
        self.language = "en"
        self.on_chats_changed: Optional[Callable[[], Awaitable[None]]] = None          # setzt routes.py: meldet geaenderte Chat-Titel an die Oberflaechen
        self._background: set = set()                                                  # laufende Hilfsaufgaben (Chat-Titel), damit sie nicht vorzeitig verworfen werden
        self._notes: Dict[str, str] = {}                                              # die Fragen-Notiz des laufenden Modus je Chat (auch fuer das Zusammenfassen am Ende)
        self.pending: Dict[str, "asyncio.Future"] = {}                                 # Rueckfragen "darf die KI das?", die auf eine Antwort warten (Kennung des Aufrufs -> Future)
        self.pending_info: Dict[str, Dict[str, Any]] = {}                              # dazu: chat_id, Funktion, Werte, Klasse

    # ---- Einstellungen
    def load(self, raw: Any) -> None:
        try:
            self.config = clean_config(raw)
        except AiError:
            self.config = clean_config({})

    def update(self, patch: Any) -> Dict[str, Any]:
        self.config = clean_config(patch, self.config)
        return self.config

    def client(self, url: Optional[str] = None, key: Optional[str] = None) -> OllamaClient:
        return OllamaClient(url if url is not None else self.config["base_url"], self.config["api_key"] if key is None else key, float(self.config["timeout_s"]))

    def state(self) -> Dict[str, Any]:
        return {"enabled": bool(self.config["enabled"]), "model": self.config["model"], "provider": self.config["provider"], "tools_mode": self.config["tools_mode"],
                "default_mode": self.config["default_mode"], "permissions": dict(self.config["permissions"]), "running": list(self.runs)}

    # ---- Berechtigungen: darf die KI diese Funktion ausfuehren?
    def permission(self, tool: "tools.Tool") -> str:
        """"allow" | "ask" | "never". Hilfsfunktionen ("free") sind immer erlaubt; sonst gilt die Einstellung der Klasse. Bei "fragen" erlaubt "immer erlauben" im Chat
        diese eine Funktion dauerhaft (`allowed_tools`) - in jeder Klasse, auch "critical" (alle Funktionen sind gleichberechtigt)."""
        if tool.access == "free":
            return "allow"
        mode = self.config["permissions"].get(tool.access, "never")
        if mode == "ask" and tool.name in self.config["allowed_tools"]:
            return "allow"
        return mode

    def confirm(self, call_id: str, approve: bool) -> Optional[Dict[str, Any]]:
        """Antwort auf eine Rueckfrage. Gibt {chat_id, tool, arguments, access} zurueck (None: es wartet nichts mit dieser Kennung)."""
        future = self.pending.get(call_id)
        if future is None or future.done():
            return None
        info = dict(self.pending_info.get(call_id) or {})
        future.set_result(bool(approve))
        return info

    def add_allowed_tool(self, name: str) -> bool:
        """"Immer erlauben": diese Funktion fragt nicht mehr (alle Klassen ausser "free", die sowieso erlaubt ist). False: gibt es nicht / schon erlaubt."""
        tool = tools.get_tool(name)
        if tool is None or tool.access == "free" or name in self.config["allowed_tools"]:
            return False
        self.config["allowed_tools"] = clean_tool_names(list(self.config["allowed_tools"]) + [name])
        return True

    def pending_for(self, chat_id: str) -> List[Dict[str, Any]]:
        """Die offenen Rueckfragen dieses Chats (fuer ein Panel, das erst jetzt geoeffnet wird)."""
        return [{"call_id": cid, **{k: v for k, v in info.items() if k != "chat_id"}} for cid, info in self.pending_info.items() if info.get("chat_id") == chat_id]

    # ---- Ablauf
    def start(self, chat_id: str, text: str, emit: Emit, mode: Optional[str] = None) -> None:
        """Startet eine Antwort im Hintergrund (Fehler kommen als Ereignis). Pro Chat laeuft hoechstens eine."""
        if not self.config["enabled"]:
            raise AiError("disabled", "The assistant is switched off in Settings -> AI assistant.", 409)
        text = str(text or "").strip()
        if not text:
            raise AiError("bad_request", "The message is empty.")
        if len(text) > MAX_TEXT:
            raise AiError("bad_request", f"The message is too long (at most {MAX_TEXT} characters).")
        self.store.load(chat_id)                                               # unbekannter Chat: 404
        if chat_id in self.runs and not self.runs[chat_id].done():
            raise AiError("busy", "The assistant is still answering in this chat.", 409)
        parsed = manual.split(text)
        if parsed is not None:                                                 # "/read_fixtures {...}": der Benutzer ruft die Funktion selbst auf, die KI antwortet nicht
            self.runs[chat_id] = asyncio.get_running_loop().create_task(self._run_manual(chat_id, text, parsed[0], parsed[1], emit))
            return
        self.runs[chat_id] = asyncio.get_running_loop().create_task(self._run(chat_id, text, mode, emit))

    async def stop(self, chat_id: str) -> bool:
        task = self.runs.get(chat_id)
        if task is None or task.done():
            return False
        task.cancel()
        return True

    def _payload(self, model: str, system: str, history: List[Dict[str, Any]], specs: List[Dict[str, Any]], extra: int = 0) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"model": model, "stream": True, "messages": [{"role": "system", "content": system}] + history,
                                   "options": {"num_ctx": int(self.config["num_ctx"]), "temperature": float(self.config["temperature"]), "num_predict": int(self.config["num_predict"]) + extra},
                                   "keep_alive": self.config["keep_alive"]}
        if specs:
            payload["tools"] = specs
        return payload

    async def _think_extra(self, client: OllamaClient, model: str) -> int:
        """Zusaetzliche Tokens fuers Denken: ein Modell, das laut Server von selbst denkt (qwen3, deepseek-r1), bekommt Platz dafuer - das Denken zaehlt zur Antwortgrenze."""
        caps = await asyncio.to_thread(model_caps, client, model)
        return THINK_EXTRA if caps and "thinking" in caps else 0

    async def _run(self, chat_id: str, text: str, mode: Optional[str], emit: Emit) -> None:
        """Ereignisse an die Oberflaeche: chat (Titel / Modell / Modus), user, start (je Modellaufruf), warning, thinking (Denkschritte), token (Text), tool_call, tool_result,
        assistant_done (Text + Zeiten; has_calls = Zwischenschritt), error, done, stopped."""
        partial = {"content": "", "thinking": ""}
        try:
            chat = self.store.load(chat_id)
            if mode is not None:
                chat["mode"] = modes.clean_mode(mode)
            chat["messages"].append({"role": "user", "content": text, "ts": time.time(), "mode": chat["mode"]})
            if chat.get("auto_title", True) and not chat.get("title"):
                chat["title"] = " ".join(text.split())[:48]
            if not chat.get("model"):
                chat["model"] = self.config["model"]
            self.store.save(chat)
            await emit({"type": "chat", "chat_id": chat_id, "title": chat["title"], "model": chat["model"], "mode": chat["mode"]})
            await emit({"type": "user", "chat_id": chat_id, "text": text})
            model = chat.get("model") or self.config["model"]
            if not model:
                raise AiError("no_model", "No model chosen. Pick one in Settings -> AI assistant or in the chat header.", 409)
            if not modes.MODES[chat["mode"]]["ready"]:
                await emit({"type": "warning", "chat_id": chat_id, "code": "mode_not_ready", "mode": chat["mode"]})
            with_tools = modes.uses_tools(chat["mode"])
            tools_mode = self.config["tools_mode"]
            scope = "guide" if chat["mode"] == "guide" else "work"                  # jeder Modus hat seine eigene Funktionsliste
            note = NOTE_GUIDE if scope == "guide" else NOTE_QUESTION
            self._notes[chat_id] = note
            ctx = ToolContext(chat_id=chat_id, language=self.language, scope=scope)
            if with_tools and scope == "work" and tools_mode == "all" and estimate_tokens(tools.specs_for(ctx, "all")) > int(self.config["num_ctx"]) * ALL_TOOLS_SHARE:
                tools_mode = "core"                                              # alle Funktionen passen nicht ins Kontextfenster: fuer diese Frage die haeufigen + Sammelfunktionen (die Einstellung bleibt)
                await emit({"type": "warning", "chat_id": chat_id, "code": "tools_too_big"})
            everything = tools_mode == "all"
            openers = ", ".join(tools.openers_for(tools_mode, scope))
            system = modes.system_prompt(chat["mode"], self.language, tools_mode, openers, today_text(self.language))
            client = self.client()
            extra = await self._think_extra(client, model)
            started = time.monotonic()                                           # Gesamtzeit: vom Absenden bis zur fertigen Antwort (alle Runden)
            rounds, total_calls = 0, 0
            counts: Dict[str, int] = {}
            limit: Optional[str] = None
            while True:
                rounds += 1
                specs = tools.specs_for(ctx, tools_mode) if with_tools else []
                budget = max(int(self.config["num_ctx"]) - RESERVE_TOKENS - estimate_tokens(system) - estimate_tokens(specs), 500)
                payload = self._payload(model, system, history_for_model(chat["messages"], budget, with_tools, note), specs, extra)
                await emit({"type": "start", "chat_id": chat_id, "model": model, "mode": chat["mode"], "round": rounds})
                try:
                    content, calls, stats, thinking = await self._stream(client, payload, chat_id, emit, partial, detect_calls=with_tools)
                except AiError as exc:
                    if with_tools and exc.code == "http_error" and "tool" in exc.message.lower():
                        raise AiError("no_tools", f"The model '{model}' cannot call functions. Pick another model for the Work mode, or use the Chat mode.", 409)
                    raise
                partial["content"] = partial["thinking"] = ""
                if any(c["name"] == tools.PASS_NAME for c in calls):
                    # Die KI sagt: keine Funktion noetig. Hat sie schon Text geschrieben, ist das die Antwort; sonst antwortet sie jetzt ohne Funktionen (ihr eigener Text).
                    calls = [c for c in calls if c["name"] != tools.PASS_NAME]
                    if not calls and not content.strip():
                        await emit({"type": "start", "chat_id": chat_id, "model": model, "mode": chat["mode"], "round": rounds})
                        plain = self._payload(model, system, history_for_model(chat["messages"], budget, with_tools, note), [], extra)
                        content, _, stats, thinking = await self._stream(client, plain, chat_id, emit, partial, detect_calls=False)
                        partial["content"] = partial["thinking"] = ""
                if not calls:
                    if not content.strip():
                        if stats.get("truncated"):
                            raise AiError("answer_limit", LIMIT_MESSAGE, 502)
                        if rounds == 1:
                            raise AiError("empty_answer", "The model gave an empty answer. Try again, or pick another model in the chat header.", 502)
                        content, stats, thinking = await self._wrap_up(client, model, system, chat, budget, chat_id, emit, partial, extra)
                    stats["run_ms"] = int((time.monotonic() - started) * 1000)
                    stats["rounds"] = rounds
                    chat["messages"].append({"role": "assistant", "content": content, "ts": time.time(), "stats": stats, "model": model, "mode": chat["mode"], **_thinking_field(thinking)})
                    self.store.save(chat)
                    await emit({"type": "assistant_done", "chat_id": chat_id, "content": content, "stats": stats, **_thinking_field(thinking)})
                    break
                stats["rounds"] = rounds
                chat["messages"].append({"role": "assistant", "content": content, "ts": time.time(), "stats": stats, "model": model, "mode": chat["mode"], **_thinking_field(thinking),
                                         "tool_calls": [{"id": c["id"], "name": c["name"], "arguments": c["arguments"]} for c in calls]})
                self.store.save(chat)
                await emit({"type": "assistant_done", "chat_id": chat_id, "content": content, "stats": stats, "has_calls": True, **_thinking_field(thinking),
                            "tool_calls": [{"id": c["id"], "name": c["name"], "arguments": c["arguments"]} for c in calls]})
                for call in calls:
                    key = call["name"] + "|" + json.dumps(call["arguments"], sort_keys=True, ensure_ascii=False, default=str)
                    if limit is None and total_calls >= MAX_TOOL_CALLS:
                        limit = "max_calls"
                    elif limit is None and counts.get(key, 0) >= MAX_REPEATS:
                        limit = "repeat"
                    if limit is not None:
                        message = await self._skip_call(call, chat_id, emit)
                    else:
                        total_calls += 1
                        counts[key] = counts.get(key, 0) + 1
                        message = await self._call_tool(call, ctx, chat_id, emit, everything)
                    chat["messages"].append(message)
                    self.store.save(chat)
                if limit is not None:
                    await emit({"type": "warning", "chat_id": chat_id, "code": limit})
                    content, stats, thinking = await self._wrap_up(client, model, system, chat, budget, chat_id, emit, partial, extra)
                    stats["run_ms"] = int((time.monotonic() - started) * 1000)
                    stats["rounds"] = rounds + 1
                    chat["messages"].append({"role": "assistant", "content": content, "ts": time.time(), "stats": stats, "model": model, "mode": chat["mode"], **_thinking_field(thinking)})
                    self.store.save(chat)
                    await emit({"type": "assistant_done", "chat_id": chat_id, "content": content, "stats": stats, **_thinking_field(thinking)})
                    break
            chat["unread"] = True                                              # fertig: im Chat-Verzeichnis markiert, bis ein Panel den Chat zeigt (gelber Punkt)
            self.store.save(chat)
            await emit({"type": "done", "chat_id": chat_id})
            self._schedule_title(chat_id)
        except asyncio.CancelledError:
            try:
                chat = self.store.load(chat_id)
                chat["messages"].append({"role": "assistant", "content": partial["content"], "ts": time.time(), "stopped": True, **_thinking_field(partial.get("thinking", ""))})
                self.store.save(chat)
            except Exception:
                pass
            await emit({"type": "stopped", "chat_id": chat_id})
        except AiError as exc:
            await self._fail(chat_id, exc.code, exc.message, emit)
        except Exception as exc:                                               # ein Fehler im Assistenten darf nie das Programm stoeren
            logger.exception("KI-Assistent: Antwort fehlgeschlagen")
            await self._fail(chat_id, "internal", str(exc), emit)
        finally:
            self.runs.pop(chat_id, None)
            self._notes.pop(chat_id, None)

    # ---- Chat-Titel: nach der ersten Antwort schreibt die KI selbst einen kurzen Titel
    def _schedule_title(self, chat_id: str) -> None:
        if not self.config["auto_title"]:
            return
        task = asyncio.get_running_loop().create_task(self._title_when_ready(chat_id))
        self._background.add(task)
        task.add_done_callback(self._background.discard)

    async def _title_when_ready(self, chat_id: str) -> None:
        """Nach der zweiten Antwort sofort (mehr Zusammenhang = besserer Titel). Hat der Chat erst EINE Frage, wartet es `TITLE_WAIT_S`: kommt keine zweite (und laeuft keine Antwort),
        wird nach der ersten benannt."""
        try:
            chat = self.store.load(chat_id)
            if chat.get("ai_titled") or not chat.get("auto_title", True):
                return
            asked = sum(1 for m in chat["messages"] if m.get("role") == "user" and m.get("content") and not m.get("manual"))
            if asked < 2:
                await asyncio.sleep(TITLE_WAIT_S)
                if chat_id in self.runs:                                        # eine zweite Frage wird gerade beantwortet: ihr Ende benennt den Chat
                    return
            await self._auto_title(chat_id)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.info("KI-Assistent: Chat-Titel nicht erstellt (%s)", exc)

    async def _auto_title(self, chat_id: str) -> None:
        """Einmal je Chat, solange der Benutzer ihn nicht selbst benannt hat: die KI bekommt die erste Frage und die erste Antwort und schreibt einen Titel von 2 bis 5 Woertern.
        Bis dahin steht der Anfang der ersten Frage als Titel. Jeder Fehler wird verschluckt (der vorlaeufige Titel bleibt)."""
        try:
            chat = self.store.load(chat_id)
            if not chat.get("auto_title", True) or chat.get("ai_titled"):
                return
            pairs: List[Tuple[str, str]] = []                                   # die ersten ZWEI Fragen mit ihren Antworten (von Hand aufgerufene Funktionen zaehlen nicht)
            asked = ""
            for m in chat["messages"]:
                if m.get("manual"):
                    continue
                if m.get("role") == "user" and m.get("content"):
                    asked = m["content"]
                elif m.get("role") == "assistant" and m.get("content") and not m.get("tool_calls") and not m.get("error") and asked:
                    pairs.append((asked, m["content"]))
                    asked = ""
                    if len(pairs) >= 2:
                        break
            model = chat.get("model") or self.config["model"]
            if not (pairs and model):
                return
            conversation = "\n".join(f"User: {_short(q, 300)}\nAssistant: {_short(a, 300)}" for q, a in pairs)
            client = self.client()
            caps = await asyncio.to_thread(model_caps, client, model)
            payload: Dict[str, Any] = {"model": model, "messages": [{"role": "system", "content": TITLE_SYSTEM},
                                                                     {"role": "user", "content": "Conversation:\n" + conversation + "\n\nTitle:"}],
                                       "options": {"num_ctx": 2048, "temperature": 0.2, "num_predict": 40}, "keep_alive": self.config["keep_alive"]}
            if caps and "thinking" in caps:
                payload["options"]["num_predict"] = 400                          # ein Modell, das erst denkt: das Denken zaehlt zur Grenze, sonst bliebe fuer den Titel nichts
            data = await asyncio.to_thread(client.chat_once, payload, 90)
            title = clean_title((data.get("message") or {}).get("content", ""))
            if not title:
                return
            for _ in range(240):                                                   # laeuft gerade eine neue Antwort, deren Chat-Datei nicht ueberschreiben: warten
                if chat_id not in self.runs:
                    break
                await asyncio.sleep(0.5)
            chat = self.store.load(chat_id)
            if not chat.get("auto_title", True) or chat.get("ai_titled"):
                return
            chat["title"], chat["ai_titled"] = title, True
            self.store.save(chat)
            if self.on_chats_changed is not None:
                await self.on_chats_changed()
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.info("KI-Assistent: Chat-Titel nicht erstellt (%s)", exc)

    async def _fail(self, chat_id: str, code: str, message: str, emit: Emit) -> None:
        try:
            chat = self.store.load(chat_id)
            chat["messages"].append({"role": "assistant", "content": "", "ts": time.time(), "error": message, "error_code": code})
            chat["unread"] = True
            self.store.save(chat)
        except Exception:
            pass
        await emit({"type": "error", "chat_id": chat_id, "code": code, "message": message})
        await emit({"type": "done", "chat_id": chat_id})

    # ---- Funktionen ausfuehren
    async def _skip_call(self, call: Dict[str, Any], chat_id: str, emit: Emit) -> Dict[str, Any]:
        result = {"ok": False, "error": "Not run: too many calls for this question. Answer now with what you have."}
        await emit({"type": "tool_call", "chat_id": chat_id, "call_id": call["id"], "name": call["name"], "arguments": call["arguments"]})
        await emit({"type": "tool_result", "chat_id": chat_id, "call_id": call["id"], "name": call["name"], "ok": False, "result": result, "ms": 0, "skipped": True})
        return {"role": "tool", "call_id": call["id"], "tool_name": call["name"], "content": json.dumps(result, ensure_ascii=False), "ok": False, "ms": 0, "skipped": True, "ts": time.time()}

    async def _call_tool(self, call: Dict[str, Any], ctx: ToolContext, chat_id: str, emit: Emit, everything: bool, manual: bool = False) -> Dict[str, Any]:
        """Fuehrt einen Aufruf aus. Jeder Fehler (unbekannter Name, fehlende Angaben, Ausnahme) wird zum Ergebnis, das die KI liest und korrigieren kann.
        `manual`: der Benutzer hat die Funktion selbst aufgerufen (/name ...) - dann gelten die Berechtigungen der KI nicht."""
        real = tools.find_name(call["name"])
        if real is not None:
            call["name"] = real
        await emit({"type": "tool_call", "chat_id": chat_id, "call_id": call["id"], "name": call["name"], "arguments": call["arguments"]})
        t0 = time.monotonic()
        result: Any
        opener = tools.collection_for_opener(call["name"])
        tool = tools.get_tool(call["name"])
        if opener is not None:
            result = await tools.run_opener(opener, ctx, self.config["tools_mode"])
        elif tool is not None and tool.scope != ctx.scope and not manual:
            result = {"ok": False, "error": f"The function '{call['name']}' is not available in this mode.", "functions": [s["function"]["name"] for s in tools.specs_for(ctx, self.config["tools_mode"])]}
        elif tool is None:
            result = {"ok": False, "error": f"There is no function '{call['name']}'.", "functions": [s["function"]["name"] for s in tools.specs_for(ctx, self.config["tools_mode"])]}
        else:
            args = call["arguments"] if isinstance(call["arguments"], dict) else {}
            required = [k for k in tool.parameters.get("required", []) if args.get(k) in (None, "")]
            if required:
                result = {"ok": False, "error": "Missing value(s): " + ", ".join(required), "parameters": tool.parameters.get("properties", {})}
            else:
                if not everything:
                    tools.open_collection(tool.collection, ctx)                  # ruft die KI eine Funktion einer noch geschlossenen Sammlung direkt, oeffnet sie sich von selbst
                refused = None if manual else await self._ask_permission(tool, call, args, chat_id, emit)
                t0 = time.monotonic()                                            # die Wartezeit auf die Antwort des Benutzers zaehlt nicht zur Dauer der Funktion
                if refused is not None:
                    result = refused
                else:
                    try:
                        result = await asyncio.wait_for(tool.handler(args, ctx), TOOL_TIMEOUT_S)
                    except asyncio.TimeoutError:
                        result = {"ok": False, "error": f"The function took longer than {TOOL_TIMEOUT_S} s."}
                    except asyncio.CancelledError:
                        raise
                    except Exception as exc:
                        logger.exception("KI-Funktion %s fehlgeschlagen", call["name"])
                        result = {"ok": False, "error": str(exc) or exc.__class__.__name__}
        ok = not (isinstance(result, dict) and result.get("ok") is False)
        denied = bool(isinstance(result, dict) and result.get("denied"))
        ms = 0 if denied else round((time.monotonic() - t0) * 1000, 1)
        await emit({"type": "tool_result", "chat_id": chat_id, "call_id": call["id"], "name": call["name"], "ok": ok, "result": result, "ms": ms, **({"denied": True} if denied else {})})
        message = {"role": "tool", "call_id": call["id"], "tool_name": call["name"], "arguments": call["arguments"], "content": json.dumps(result, ensure_ascii=False, default=str), "ok": ok, "ms": ms, "ts": time.time()}
        if opener is not None:
            message["opener"] = True
        if denied:
            message["denied"] = True
        return message

    async def _run_manual(self, chat_id: str, text: str, name: str, rest: str, emit: Emit) -> None:
        """Der Benutzer ruft eine Funktion selbst auf (`/name {Werte}`, `/name Wert`, `/help`): sie laeuft genau wie bei der KI (gleiche Pruefung, gleiches Ergebnis), das Ergebnis steht im
        Chat - das Modell wird nicht gefragt und antwortet nicht. Gespeichert als Frage + Aufruf + Ergebnis mit `manual`; fuers Modell unsichtbar. Ein Fehler (unbekannte Funktion, falsche
        Schreibweise der Werte) wird ein fehlgeschlagener Aufruf mit Erklaerung."""
        try:
            chat = self.store.load(chat_id)
            chat["messages"].append({"role": "user", "content": text, "ts": time.time(), "mode": chat["mode"], "manual": True})
            if chat.get("auto_title", True) and not chat.get("title"):
                chat["title"] = " ".join(text.split())[:48]
            if not chat.get("model"):
                chat["model"] = self.config["model"]
            self.store.save(chat)
            await emit({"type": "chat", "chat_id": chat_id, "title": chat["title"], "model": chat["model"], "mode": chat["mode"]})
            await emit({"type": "user", "chat_id": chat_id, "text": text, "manual": True})
            is_help = name.lower() in manual.HELP_NAMES
            real = "help" if is_help else (tools.find_name(name) or name)
            tool = None if is_help else tools.get_tool(real)
            args: Dict[str, Any] = {}
            problem = ""
            if tool is not None:
                try:
                    args = manual.arguments(tool, rest)
                except AiError as exc:
                    problem = exc.message
            elif not is_help and rest.strip():
                try:
                    args = manual.arguments(tools.Tool(real, "", tools.base.schema(), None), rest)             # unbekannte Funktion: die Werte trotzdem zeigen
                except AiError:
                    args = {}
            call = {"id": uuid.uuid4().hex[:8], "name": real, "arguments": args}
            calls = [{"id": call["id"], "name": real, "arguments": args}]
            chat["messages"].append({"role": "assistant", "content": "", "ts": time.time(), "manual": True, "mode": chat["mode"], "tool_calls": calls})
            self.store.save(chat)
            await emit({"type": "assistant_done", "chat_id": chat_id, "content": "", "stats": {}, "has_calls": True, "manual": True, "tool_calls": calls})
            if is_help or problem:
                result = manual.help_result() if is_help else {"ok": False, "error": problem}
                await emit({"type": "tool_call", "chat_id": chat_id, "call_id": call["id"], "name": real, "arguments": args})
                await emit({"type": "tool_result", "chat_id": chat_id, "call_id": call["id"], "name": real, "ok": result["ok"], "result": result, "ms": 0})
                message = {"role": "tool", "call_id": call["id"], "tool_name": real, "arguments": args, "content": json.dumps(result, ensure_ascii=False), "ok": result["ok"], "ms": 0, "ts": time.time()}
            else:
                message = await self._call_tool(call, ToolContext(chat_id=chat_id, language=self.language), chat_id, emit, True, manual=True)
            message["manual"] = True
            chat["messages"].append(message)
            self.store.save(chat)
            await emit({"type": "done", "chat_id": chat_id})
        except asyncio.CancelledError:
            await emit({"type": "stopped", "chat_id": chat_id})
        except AiError as exc:
            await self._fail(chat_id, exc.code, exc.message, emit)
        except Exception as exc:
            logger.exception("KI-Assistent: Funktion von Hand fehlgeschlagen")
            await self._fail(chat_id, "internal", str(exc), emit)
        finally:
            self.runs.pop(chat_id, None)

    async def _ask_permission(self, tool: "tools.Tool", call: Dict[str, Any], args: Dict[str, Any], chat_id: str, emit: Emit) -> Optional[Dict[str, Any]]:
        """None = die Funktion darf laufen. Sonst das Ergebnis, das die KI statt dessen bekommt (ihre Klasse ist auf "nie" gestellt oder der Benutzer hat abgelehnt).
        Bei "fragen" meldet das Ereignis `tool_ask` an alle Panels und Geraete die Rueckfrage und der Ablauf wartet auf `confirm()` (Antwort ueber den WebSocket: ai_confirm)."""
        mode = self.permission(tool)
        if mode == "allow":
            return None
        if mode == "never":
            return {"ok": False, "denied": True, "error": f"The user's settings do not allow '{tool.access}' functions, so this was not done. Tell the user that it is switched off in Settings -> AI assistant -> Permissions."}
        future: "asyncio.Future" = asyncio.get_running_loop().create_future()
        self.pending[call["id"]] = future
        self.pending_info[call["id"]] = {"chat_id": chat_id, "name": tool.name, "arguments": args, "access": tool.access}
        await emit({"type": "tool_ask", "chat_id": chat_id, "call_id": call["id"], "name": tool.name, "arguments": args, "access": tool.access})
        approved = False
        try:
            approved = bool(await asyncio.wait_for(future, ASK_TIMEOUT_S))
        except asyncio.TimeoutError:
            approved = False
        finally:
            self.pending.pop(call["id"], None)
            self.pending_info.pop(call["id"], None)
        await emit({"type": "tool_answer", "chat_id": chat_id, "call_id": call["id"], "approved": approved})
        if approved:
            return None
        return {"ok": False, "denied": True, "error": "The user did not allow this action, so it was not done."}

    async def _wrap_up(self, client: OllamaClient, model: str, system: str, chat: Dict[str, Any], budget: int, chat_id: str, emit: Emit,
                       partial: Dict[str, Any], extra: int = 0) -> Tuple[str, Dict[str, Any], str]:
        """Die KI schreibt die Antwort aus den bisherigen Ergebnissen - ohne Funktionen (Grenze erreicht oder sie hat nach den Funktionen nichts gesagt)."""
        history = history_for_model(chat["messages"], budget, True, self._notes.get(chat_id, "")) + [{"role": "user", "content": WRAP_UP.get(self.language, WRAP_UP["en"])}]
        await emit({"type": "start", "chat_id": chat_id, "model": model, "mode": chat["mode"], "wrap_up": True})
        content, _, stats, thinking = await self._stream(client, self._payload(model, system, history, [], extra), chat_id, emit, partial, detect_calls=False)
        partial["content"] = partial["thinking"] = ""
        if not content.strip():
            if stats.get("truncated"):
                raise AiError("answer_limit", LIMIT_MESSAGE, 502)
            raise AiError("empty_answer", "The model gave no answer after the functions ran. Try again, or pick another model in the chat header.", 502)
        return content, stats, thinking

    # ---- Eine Antwort des Modells (gestreamt)
    async def _stream(self, client: OllamaClient, payload: Dict[str, Any], chat_id: str, emit: Emit, partial: Dict[str, Any],
                           detect_calls: bool = False) -> Tuple[str, List[Dict[str, Any]], Dict[str, Any], str]:
        """Fragt das Modell und meldet die Antwort gestreamt (Ereignisse `thinking` fuer die Denkschritte, `token` fuer den Text). Das Lesen laeuft in einem Thread
        (urllib blockiert), die Stuecke kommen ueber eine Warteschlange. Gibt (Text, Funktionsaufrufe, Messwerte, Denkschritte) zurueck.
        `detect_calls`: Funktionsaufrufe erkennen - ueber die Schnittstelle oder als Text geschrieben (dann wird der Text erst am Ende gezeigt, falls er keiner war)."""
        loop = asyncio.get_running_loop()
        queue: "asyncio.Queue" = asyncio.Queue()
        cancel = threading.Event()
        holder: Dict[str, Any] = {}

        def put(item: Any) -> None:
            loop.call_soon_threadsafe(queue.put_nowait, item)

        def worker() -> None:
            try:
                response = client.open_chat(payload)
                holder["response"] = response
                with response:
                    for raw in response:
                        if cancel.is_set():
                            break
                        raw = raw.strip()
                        if raw:
                            put(json.loads(raw.decode("utf-8", "replace")))
            except Exception as exc:
                put(exc if not cancel.is_set() else None)
            finally:
                put(None)

        started = time.monotonic()
        threading.Thread(target=worker, name="opencue-ai-stream", daemon=True).start()
        splitter = ThinkSplit()
        content, buffer, last_flush = "", "", 0.0
        thinking, think_buffer, last_think_flush = "", "", 0.0
        think_from: Optional[float] = None
        think_to: Optional[float] = None
        calls: List[Dict[str, Any]] = []
        first_ms: Optional[int] = None
        final: Dict[str, Any] = {}

        async def flush(force: bool = False) -> None:
            nonlocal buffer, last_flush, think_buffer, last_think_flush
            now = time.monotonic()
            if think_buffer and (force or now - last_think_flush >= FLUSH_S):
                text, think_buffer = think_buffer, ""
                last_think_flush = now
                await emit({"type": "thinking", "chat_id": chat_id, "text": text})
            if buffer and (force or (not (detect_calls and looks_like_call(content)) and now - last_flush >= FLUSH_S)):
                text, buffer = buffer, ""
                last_flush = now
                await emit({"type": "token", "chat_id": chat_id, "text": text})

        def add(said: str, thought: str) -> None:
            nonlocal content, buffer, thinking, think_buffer, first_ms, think_from, think_to
            now = time.monotonic()
            if (said or thought) and first_ms is None:
                first_ms = int((now - started) * 1000)
            if thought:
                if think_from is None:
                    think_from = now
                thinking += thought
                think_buffer += thought
                partial["thinking"] = thinking
            if said:
                if think_from is not None and think_to is None:
                    think_to = now
                content += said
                buffer += said
                partial["content"] = content

        try:
            while True:
                item = await queue.get()
                if item is None:
                    break
                if isinstance(item, Exception):
                    raise item if isinstance(item, AiError) else AiError("stream_failed", f"The answer stopped: {item}", 502)
                if item.get("error"):
                    raise AiError("http_error", str(item["error"]), 502)
                message = item.get("message") or {}
                said, thought = splitter.feed(message.get("content") or "")
                add(said, (message.get("thinking") or "") + thought)
                if said or thought or message.get("thinking"):
                    await flush()
                for raw_call in message.get("tool_calls") or []:
                    function = raw_call.get("function") or {}
                    arguments = function.get("arguments") or {}
                    if isinstance(arguments, str):
                        try:
                            arguments = json.loads(arguments or "{}")
                        except ValueError:
                            arguments = {}
                    if first_ms is None:
                        first_ms = int((time.monotonic() - started) * 1000)
                    if think_from is not None and think_to is None:
                        think_to = time.monotonic()
                    name = str(function.get("name", ""))
                    calls.append(new_call(tools.find_name(name) or name, arguments if isinstance(arguments, dict) else {}))
                if item.get("done"):
                    final = item
            add(*splitter.finish())
            if think_from is not None and think_to is None:
                think_to = time.monotonic()
            if detect_calls and not calls:
                rest, found = extract_text_calls(content)
                if found:
                    calls, content, buffer = found, rest, ""
                    partial["content"] = content
            await flush(True)
        finally:
            cancel.set()
            response = holder.get("response")
            if response is not None:
                try:
                    response.close()
                except Exception:
                    pass
        total_ms = int((time.monotonic() - started) * 1000)
        eval_count = int(final.get("eval_count") or 0)
        eval_ns = int(final.get("eval_duration") or 0)
        stats = {"total_ms": total_ms, "run_ms": total_ms, "first_token_ms": first_ms, "load_ms": int((final.get("load_duration") or 0) / 1e6),
                 "prompt_tokens": int(final.get("prompt_eval_count") or 0), "tokens": eval_count, "truncated": final.get("done_reason") == "length",
                 "tokens_per_s": round(eval_count / (eval_ns / 1e9), 1) if eval_ns else None,
                 "think_ms": int((think_to - think_from) * 1000) if think_from is not None and think_to is not None else 0}
        return content, calls, stats, thinking


def _thinking_field(thinking: str) -> Dict[str, Any]:
    return {"thinking": thinking} if thinking else {}


def clean_title(text: str) -> str:
    """Der Titel aus der Antwort des Modells: erste Zeile, ohne 'Titel:', Anfuehrungszeichen und Schlusszeichen, hoechstens 8 Woerter / 60 Zeichen."""
    text = re.sub(r"<think>.*?</think>", "", str(text or ""), flags=re.S)
    line = next((l.strip() for l in text.splitlines() if l.strip()), "")
    line = re.sub(r"^(title|titel)\s*:\s*", "", line, flags=re.I).strip(" \"'«»„“”`*#.:;!")
    words = line.split()
    return " ".join(words[:8])[:60].strip()


assistant = AssistantService()
