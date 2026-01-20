"""LangGraph state for the crew officer."""

# Per langgraph-Application structure.md: File structure

from typing import Any, Dict, List, Optional, TypedDict

from agents.types import DecisionMode
from core.db import TinyDBRunStore
from core.state import GameState
from mcp.server import MCPServer


class CrewOfficerState(TypedDict, total=False):
    run_id: str
    seed: int
    state: GameState
    decisions: Dict[str, Any]
    mode: DecisionMode
    mcp: MCPServer
    db: TinyDBRunStore
    phase: str
    stance: str
    readings: Dict[str, Dict[str, Any]]
    belief: Dict[str, Any]
    belief_quality: float
    contradictions: int
    tool_call: Dict[str, Any]
    tool_write_output: Dict[str, Any]
    notes: List[str]
    notes_tail: List[str]
    last_belief: Optional[Dict[str, Any]]
    last_tool: Optional[str]
    visited: List[str]
    observation: str
    agent_events: List[Dict[str, Any]]
