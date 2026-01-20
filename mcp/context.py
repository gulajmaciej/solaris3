"""Tool execution context for MCP tools."""

from dataclasses import dataclass
from typing import Any, Callable, Optional

from core.state import GameState


@dataclass(frozen=True)
class ToolContext:
    run_id: str
    turn: int
    agent_id: str
    seed: int
    game_state: GameState
    history: Optional[Callable[..., Any]] = None
