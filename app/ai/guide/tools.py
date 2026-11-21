# Copyright (C) 2026 Samuel Zenker
# SPDX-License-Identifier: GPL-3.0-or-later
"""Funktionen des Wegweisers (Modus "Wegweiser"): Anleitung suchen, Dialog als Schaltflaeche anbieten, Themen auflisten. Sie ersetzen den grossen Prompt: das Wissen kommt erst, wenn die
KI nachschlaegt - und nur das, was in den Textschnipseln steht. Alle sind "free": sie aendern nichts an Show oder Programm (die Schaltflaeche oeffnet der Benutzer selbst)."""
from __future__ import annotations

from typing import Any, Dict

from app.ai.guide import snippets, targets
from app.ai.tools import base
from app.ai.tools.base import Tool, ToolContext, schema

INSTRUCTION = ("Answer ONLY with facts that stand in 'snippets'. Do not add menu items, buttons, settings or steps that are not in the text. If the snippets do not fully answer the question, say what is missing. "
               "Use the names of menus and buttons exactly as they are written there.")


def _lang(ctx: ToolContext) -> str:
    return ctx.language if ctx.language in ("de", "en", "fr", "nl", "it", "es") else "en"


async def _find_help(args: Dict[str, Any], ctx: ToolContext) -> Any:
    question = str(args.get("question", args.get("query", args.get("frage", args.get("topic", ""))))).strip()
    if not question:
        return {"ok": False, "error": "Give the question or the topic you want to look up."}
    lang = _lang(ctx)
    found = snippets.search(question, lang)
    if not found:
        pages = [t["page"] for t in snippets.topics(lang)]
        return {"ok": True, "found": False, "message": "The guide has nothing about this. Tell the user plainly that you do not know and name what you can explain: " + "; ".join(pages) + ". Do NOT answer from memory."}
    result: Dict[str, Any] = {"ok": True, "found": True, "instruction": INSTRUCTION, "snippets": found}
    dialogs = targets.search(question, lang)
    if dialogs:
        result["buttons_you_can_offer"] = [{"target": t["id"], "label": targets.path_of(t, lang)} for t in dialogs]
        result["button_hint"] = "To give the user a button that opens one of these dialogs, call show_dialog with the target."
    return result


async def _show_dialog(args: Dict[str, Any], ctx: ToolContext) -> Any:
    lang = _lang(ctx)
    target, candidates = targets.resolve(args.get("target", args.get("dialog", args.get("name", ""))), lang)
    if target is None:
        listing = [{"target": t["id"], "label": targets.path_of(t, lang)} for t in (candidates or targets.targets())]
        return {"ok": False, "error": "No such dialog" + (" - did you mean one of these?" if candidates else ". These exist:"), "dialogs": listing}
    info = targets.describe(target, lang)
    return {"ok": True, "button": {"target": info["id"], "label": info["label"], "kind": info["kind"]}, "about": info["about"],
            "message": ("A button now appears under your answer; the USER presses it to open this. " if info["kind"] == "dialog" else "A button now appears under your answer; the USER presses it to switch this. ")
                       + "Tell the user where it is in the menu (the label is the path) and what is in it, using 'about' - nothing else."}


async def _list_help_topics(args: Dict[str, Any], ctx: ToolContext) -> Any:
    lang = _lang(ctx)
    return {"ok": True, "topics": snippets.topics(lang), "dialogs": [{"target": t["id"], "label": targets.path_of(t, lang)} for t in targets.targets()],
            "hint": "These are the things the guide can explain. Look a topic up with find_help."}


_IDS = ", ".join(t["id"] for t in targets.targets())

base.register_guide([
    Tool("find_help", "Looks up the USER GUIDE of OpenCue and returns the matching text snippets. Use it for EVERY question about how something works, where something is or what something means in the PROGRAM: "
                      "\"wie speichere ich eine Show?\", \"wo ändere ich die Farben?\", \"how do I connect lights?\", \"what is the executor?\", \"wie benutze ich das Tablet?\". Answer ONLY from the result; "
                      "if nothing was found, say you do not know.",
         schema({"question": {"type": "string", "description": "The question or the topic, in the user's own words."}}, ["question"]), _find_help, access="free"),
    Tool("show_dialog", "Puts a BUTTON into the chat that opens a dialog of the program when the user presses it (you cannot click yourself). Use it when the user wants to open or find a dialog: "
                        "\"öffne die Einstellungen\", \"wo ist der Dateimanager?\", \"zeig mir die Scheinwerfer-Bibliothek\", \"open the settings\". Targets: " + _IDS + ". A free text such as \"farben\" is understood too.",
         schema({"target": {"type": "string", "description": "The target (e.g. settings:appearance, file-manager, fixture-library) or what the user wants to open."}}, ["target"]), _show_dialog, access="free"),
    Tool("list_help_topics", "Lists everything the guide can explain (pages and sections) and all dialogs you can offer as buttons. Use it for \"was kannst du erklären?\", \"what can you help me with?\".",
         schema(), _list_help_topics, access="free"),
])
