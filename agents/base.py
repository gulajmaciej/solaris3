"""Base agent interface."""

from abc import ABC, abstractmethod
from typing import Any, Dict

from agents.types import DecisionMode, ToolPhaseResult
from core.db import TinyDBRunStore
from core.state import GameState
from mcp.server import MCPServer


class BaseAgent(ABC):
    @abstractmethod
    def tool_phase(
        self,
        run_id: str,
        state: GameState,
        decisions: Dict[str, Any],
        mcp: MCPServer,
        db: TinyDBRunStore,
        mode: DecisionMode,
    ) -> ToolPhaseResult:
        raise NotImplementedError

    def observe_phase(
        self,
        run_id: str,
        state: GameState,
        decisions: Dict[str, Any],
        mcp: MCPServer,
        db: TinyDBRunStore,
        mode: DecisionMode,
    ) -> str:
        return "No observation available."
