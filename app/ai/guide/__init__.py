# Copyright (C) 2026 Samuel Zenker
# SPDX-License-Identifier: GPL-3.0-or-later
"""Modus "Wegweiser" des KI-Assistenten: erklaert das PROGRAMM (nicht die Show). Wissen kommt aus kleinen Textschnipseln (static/help/guide/), die Python heraussucht (snippets.py);
Dialoge und Einstellungen werden ueber Schaltflaechen im Chat geoeffnet (targets.py, tools.py). Die KI erfindet nichts: sie antwortet nur mit dem, was ein Funktionsergebnis liefert."""
from app.ai.guide import tools  # noqa: F401  (meldet die Funktionen des Wegweisers an)
