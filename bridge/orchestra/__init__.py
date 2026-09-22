"""
MAGI-Orchestra System (v3.0)
Orquestador Multi-Agente inspirado en Magisys.
Dirigido por Google Gemini 3.8 Flash High, administrando Claude Code CLI, Codex CLI y ZCode.
"""
from .token_optimizer import token_optimizer, TokenTracker
from .directors_health import directors_health
from .coordinator import orchestra_coordinator

__all__ = ["token_optimizer", "TokenTracker", "directors_health", "orchestra_coordinator"]
