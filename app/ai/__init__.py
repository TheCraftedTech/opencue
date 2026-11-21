# Copyright (C) 2026 Samuel Zenker
# SPDX-License-Identifier: GPL-3.0-or-later
"""KI-Assistent von OpenCue (Gespraech mit einem lokalen Sprachmodell ueber Ollama). Aufbau: config, ollama, chats, modes, agent, routes."""
from app.ai.agent import assistant
from app.ai.errors import AiError

__all__ = ["assistant", "AiError"]
