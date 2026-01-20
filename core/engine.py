"""Simulation runner for the core loop."""

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from agents.catalog import get_agent
from agents.types import DecisionMode, ToolPhaseResult
from core.db import TinyDBRunStore
from core.endings import EndingRegistry, EndingSpec
from core.events import (
    RunEnded,
    RunStarted,
    StateDeltaApplied,
    TurnEnded,
    TurnStarted,
    serialize_event,
)
from core.state import GameState, clamp_state, initial_state
from mcp.server import MCPServer


@dataclass(frozen=True)
class TurnResult:
    state: GameState
    events: List[Dict[str, Any]]
    ending: Optional[EndingSpec]
    run_id: str
    tool_phase_results: List[ToolPhaseResult]


class SimulationRunner:
    def __init__(
        self,
        db: TinyDBRunStore,
        endings_registry: EndingRegistry,
        seed: int,
        mcp_server: MCPServer,
        decision_mode: DecisionMode,
    ) -> None:
        self._db = db
        self._endings = endings_registry
        self._seed = seed
        self._mcp = mcp_server
        self._decision_mode = decision_mode
        self._run_id: Optional[str] = None
        self._state: Optional[GameState] = None
        self._ended = False
        self._instrument_agent = get_agent("instrument_specialist").builder()
        self._crew_agent = get_agent("crew_officer").builder()

    def start_run(self) -> str:
        if self._run_id is not None:
            raise RuntimeError("Run already started")
        run_id = self._db.create_run(self._seed)
        created_at = datetime.now(timezone.utc).isoformat()
        event = RunStarted(run_id=run_id, seed=self._seed, created_at=created_at)
        self._record_event(run_id, serialize_event(event), None)
        self._run_id = run_id
        self._state = initial_state()
        return run_id

    def step(self, decisions: Dict[str, Any]) -> TurnResult:
        if self._run_id is None or self._state is None:
            raise RuntimeError("Run has not been started")
        if self._ended:
            raise RuntimeError("Run has already ended")

        events: List[Dict[str, Any]] = []
        before_state = self._state

        started = TurnStarted(turn=before_state.turn, decisions=decisions)
        self._record_event(self._run_id, serialize_event(started), events)

        tool_phase_results = self._run_tool_phase(decisions, events)
        tool_state = self._state
        if tool_state is None:
            raise RuntimeError("Tool phase did not produce state")

        tension = tool_state.tension + 0.01 + 0.01 * tool_state.ocean_activity + 0.01 * tool_state.crew_load
        crew_load = tool_state.crew_load + 0.01
        earth_pressure = tool_state.earth_pressure + 0.005 * tool_state.tension
        station_power = tool_state.station_power + 0.01 - 0.01 * tool_state.ocean_activity
        ocean_activity = tool_state.ocean_activity - 0.005

        next_state = GameState(
            tension=tension,
            ocean_activity=ocean_activity,
            crew_load=crew_load,
            earth_pressure=earth_pressure,
            station_power=station_power,
            turn=tool_state.turn + 1,
        )
        next_state = clamp_state(next_state)
        after_dict = asdict(next_state)
        tool_state_dict = asdict(tool_state)
        delta_dict: Dict[str, Any] = {key: after_dict[key] - tool_state_dict[key] for key in after_dict}

        delta_event = StateDeltaApplied(
            turn=next_state.turn,
            source="core.tick",
            delta_dict=delta_dict,
            state_before=tool_state_dict,
            state_after=after_dict,
        )
        self._record_event(self._run_id, serialize_event(delta_event), events)

        ended_turn = TurnEnded(turn=next_state.turn, state_snapshot=after_dict)
        self._record_event(self._run_id, serialize_event(ended_turn), events)
        self._db.save_turn_snapshot(self._run_id, next_state.turn, after_dict)

        ending = self._endings.evaluate(next_state)
        if ending is not None:
            ended_event = self.end_run(ending)
            events.append(ended_event)

        self._state = next_state
        return TurnResult(
            state=next_state,
            events=events,
            ending=ending,
            run_id=self._run_id,
            tool_phase_results=tool_phase_results,
        )

    def end_run(self, ending_spec: EndingSpec) -> Dict[str, Any]:
        if self._run_id is None or self._state is None:
            raise RuntimeError("Run has not been started")
        if self._ended:
            raise RuntimeError("Run has already ended")
        self._ended = True
        final_state = asdict(self._state)
        self._db.finalize_run(
            self._run_id,
            ending_spec.id,
            ending_spec.title,
            self._state.turn,
            final_state,
        )
        event = RunEnded(
            run_id=self._run_id,
            ending_id=ending_spec.id,
            ending_title=ending_spec.title,
            turn=self._state.turn,
            final_state=final_state,
        )
        event_dict = serialize_event(event)
        self._record_event(self._run_id, event_dict, None)
        return event_dict

    def _run_tool_phase(self, decisions: Dict[str, Any], events: List[Dict[str, Any]]) -> List[ToolPhaseResult]:
        if self._run_id is None or self._state is None:
            raise RuntimeError("Run has not been started")

        tool_phase_results: List[ToolPhaseResult] = []
        tool_sequence: List[Tuple[str, Dict[str, Any]]] = [
            ("instrument_specialist", decisions.get("instrument_specialist", {})),
            ("crew_officer", decisions.get("crew_officer", {})),
        ]
        for agent_id, agent_decisions in tool_sequence:
            result = self._run_agent_tools(agent_id, agent_decisions, events)
            if result is not None:
                tool_phase_results.append(result)
        return tool_phase_results

    def _run_agent_tools(
        self, agent_id: str, agent_decisions: Dict[str, Any], events: List[Dict[str, Any]]
    ) -> Optional[ToolPhaseResult]:
        if self._run_id is None or self._state is None:
            raise RuntimeError("Run has not been started")

        if agent_id == "instrument_specialist":
            tool_result = self._instrument_agent.tool_phase(
                run_id=self._run_id,
                state=self._state,
                decisions=agent_decisions,
                mcp=self._mcp,
                db=self._db,
                mode=self._decision_mode,
            )
            for event in tool_result.agent_events:
                self._record_event(self._run_id, event, events)
            self._apply_tool_result(tool_result, events)
            return tool_result

        if agent_id == "crew_officer":
            if "stance" not in agent_decisions:
                return None
            tool_result = self._crew_agent.tool_phase(
                run_id=self._run_id,
                state=self._state,
                decisions=agent_decisions,
                mcp=self._mcp,
                db=self._db,
                mode=self._decision_mode,
            )
            for event in tool_result.agent_events:
                self._record_event(self._run_id, event, events)
            self._apply_tool_result(tool_result, events)
            return tool_result

        return None

    def _apply_delta(self, state: GameState, delta: Dict[str, Any]) -> GameState:
        updated = GameState(
            tension=state.tension + float(delta.get("tension", 0.0)),
            ocean_activity=state.ocean_activity + float(delta.get("ocean_activity", 0.0)),
            crew_load=state.crew_load + float(delta.get("crew_load", 0.0)),
            earth_pressure=state.earth_pressure + float(delta.get("earth_pressure", 0.0)),
            station_power=state.station_power + float(delta.get("station_power", 0.0)),
            turn=state.turn,
        )
        return clamp_state(updated)

    def _record_event(
        self,
        run_id: Optional[str],
        event_dict: Dict[str, Any],
        events: Optional[List[Dict[str, Any]]],
    ) -> None:
        if events is not None:
            events.append(event_dict)
        if run_id is not None:
            self._db.append_event(run_id, event_dict)

    def _apply_tool_result(self, tool_result: ToolPhaseResult, events: List[Dict[str, Any]]) -> None:
        if self._state is None:
            raise RuntimeError("Run has not been started")
        state_before = self._state
        delta = tool_result.tool_write_output.get("delta", {})
        self._state = self._apply_delta(state_before, delta)
        state_after = self._state
        before_dict = asdict(state_before)
        after_dict = asdict(state_after)
        actual_delta = {key: after_dict[key] - before_dict[key] for key in after_dict}

        delta_event = StateDeltaApplied(
            turn=state_after.turn,
            source=f"tool:{tool_result.tool_call.tool_name}",
            delta_dict=actual_delta,
            state_before=before_dict,
            state_after=after_dict,
        )
        self._record_event(self._run_id, serialize_event(delta_event), events)
