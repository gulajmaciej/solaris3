"""Instrument specialist agent wrapper."""

# Per langgraph-Application structure.md: Graphs

from typing import Any, Dict

from typing import Any

from agents.base import BaseAgent
from agents.instrument_specialist.graph import build_graph
from agents.instrument_specialist.state import InstrumentState
from agents.types import DecisionMode, ToolCall, ToolPhaseResult
from core.db import TinyDBRunStore
from core.state import GameState
from mcp.server import MCPServer


class InstrumentSpecialistAgent(BaseAgent):
    def __init__(self) -> None:
        # Per langgraph-Application structure.md: Graphs
        self._graph: Any = build_graph().compile()

    def tool_phase(
        self,
        run_id: str,
        state: GameState,
        decisions: Dict[str, Any],
        mcp: MCPServer,
        db: TinyDBRunStore,
        mode: DecisionMode,
    ) -> ToolPhaseResult:
        # Per langgraph-Application structure.md: Graphs
        graph_state: InstrumentState = {
            "run_id": run_id,
            "seed": state.turn,
            "state": state,
            "decisions": decisions,
            "mode": mode,
            "mcp": mcp,
            "db": db,
            "phase": "tool_phase",
            "visited": [],
            "agent_events": [],
        }
        output: InstrumentState = self._graph.invoke(graph_state)
        tool_call_data = output.get("tool_call", {})
        tool_call = ToolCall(
            tool_name=tool_call_data.get("tool_name", ""),
            args=tool_call_data.get("args", {}),
            reason=tool_call_data.get("reason", ""),
            chosen_by=tool_call_data.get("chosen_by", "deterministic"),
        )
        return ToolPhaseResult(
            agent_id="instrument_specialist",
            tool_call=tool_call,
            tool_write_output=output.get("tool_write_output", {}),
            belief=output.get("belief", {}),
            belief_quality=output.get("belief_quality", 0.0),
            contradictions=output.get("contradictions", 0),
            agent_events=output.get("agent_events", []),
        )

    def observe_phase(
        self,
        run_id: str,
        state: GameState,
        decisions: Dict[str, Any],
        mcp: MCPServer,
        db: TinyDBRunStore,
        mode: DecisionMode,
    ) -> str:
        graph_state: InstrumentState = {
            "run_id": run_id,
            "seed": state.turn,
            "state": state,
            "decisions": decisions,
            "mode": mode,
            "mcp": mcp,
            "db": db,
            "phase": "observe_phase",
            "visited": [],
            "agent_events": [],
        }
        output: InstrumentState = self._graph.invoke(graph_state)
        return output.get("observation", "Instrument report unavailable.")
