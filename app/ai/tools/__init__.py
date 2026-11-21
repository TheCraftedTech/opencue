# Copyright (C) 2026 Samuel Zenker
# SPDX-License-Identifier: GPL-3.0-or-later
"""Die Funktionen des Modus "Arbeiten" (Aufbau und Sammlungen: siehe base.py). Neue Sammlungen hier importieren, damit sie sich anmelden."""
from app.ai.tools import show, control, operate, manage, helpers  # noqa: F401  (melden ihre Sammlungen an)
from app.ai.tools.base import (COLLECTIONS, CORE_TOOLS, GUIDE_TOOLS, PASS_NAME, TOOLS_MODES, Collection, Tool, ToolContext, all_tools, collection_for_opener, describe_for_prompt, find_name, get_tool,
                               open_collection, openers_for, register_guide, run_opener, specs_for, tool_names)

__all__ = ["COLLECTIONS", "CORE_TOOLS", "GUIDE_TOOLS", "PASS_NAME", "TOOLS_MODES", "Collection", "Tool", "ToolContext", "all_tools", "collection_for_opener", "describe_for_prompt", "find_name", "get_tool",
           "open_collection", "openers_for", "register_guide", "run_opener", "specs_for", "tool_names"]
