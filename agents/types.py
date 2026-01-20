"""Shared agent types."""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List


class DecisionMode(str, Enum):
    DETERMINISTIC = "deterministic"
    LLM = "llm"
    HYBRID = "hybrid"


class AgentKind(str, Enum):
    PLAYER_DRIVEN = "player_driven"
    AUTONOMOUS = "autonomous"


@dataclass(frozen=True)
class ToolCall:
    tool_name: str
    args: Dict[str, Any]
    reason: str
    chosen_by: str


@dataclass(frozen=True)
class ToolPhaseResult:
    agent_id: str
    tool_call: ToolCall
    tool_write_output: Dict[str, Any]
    belief: Dict[str, Any]
    belief_quality: float
    contradictions: int
    agent_events: List[Dict[str, Any]]
