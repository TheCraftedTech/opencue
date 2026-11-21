# Copyright (C) 2026 Samuel Zenker
# SPDX-License-Identifier: GPL-3.0-or-later
"""Denkschritte: Modelle wie qwen3 oder deepseek-r1 "denken" erst und antworten dann. Neuere Ollama-Versionen liefern das Denken getrennt (Feld `thinking`);
aeltere schreiben es als <think>...</think> in den Text. `ThinkSplit` trennt beides sauber - auch wenn eine Markierung in zwei Stuecke zerrissen ankommt."""
from __future__ import annotations

from typing import Tuple

OPEN, CLOSE = "<think>", "</think>"


class ThinkSplit:
    def __init__(self) -> None:
        self.inside = False
        self.hold = ""                                  # ein moeglicher Anfang einer Markierung am Ende des letzten Stuecks

    def feed(self, piece: str) -> Tuple[str, str]:
        """(Antworttext, Denktext) aus einem neuen Stueck."""
        data, self.hold = self.hold + piece, ""
        text = thought = ""
        while data:
            tag = CLOSE if self.inside else OPEN
            at = data.find(tag)
            if at >= 0:
                chunk, data = data[:at], data[at + len(tag):]
                if self.inside:
                    thought += chunk
                else:
                    text += chunk
                self.inside = not self.inside
                continue
            keep = 0
            for k in range(min(len(tag) - 1, len(data)), 0, -1):
                if tag.startswith(data[-k:]):
                    keep = k
                    break
            body, self.hold = data[:len(data) - keep], data[len(data) - keep:]
            if self.inside:
                thought += body
            else:
                text += body
            break
        return text, thought

    def finish(self) -> Tuple[str, str]:
        """Was am Ende noch zurueckgehalten wurde (war doch keine Markierung)."""
        rest, self.hold = self.hold, ""
        return ("", rest) if self.inside else (rest, "")
