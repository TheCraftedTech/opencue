# Copyright (C) 2026 Samuel Zenker
# SPDX-License-Identifier: GPL-3.0-or-later
"""Fehler des KI-Assistenten: ein Code (maschinenlesbar), eine Meldung (fuer den Benutzer, englisch) und ein HTTP-Status."""
from __future__ import annotations


class AiError(Exception):
    def __init__(self, code: str, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.code, self.message, self.status = code, message, status
