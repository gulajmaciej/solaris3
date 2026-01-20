"""LangGraph nodes for instrument specialist."""

# Per langgraph-Application structure.md: Graphs

from typing import Dict

# Per langgraph-Application structure.md: Graphs

from agents.common.belief import fuse_readings
from agents.common.decision import (
    apply_guardrails_tool_call,
    deterministic_tool_choice_instrument,
    validate_tool_call,
)
from agents.common.llm import llm_choose_tool_instrument, resolve_model_name
from agents.types import DecisionMode, ToolCall
from core.state import GameState
from mcp.context import ToolContext

from agents.instrument_specialist.state import InstrumentState


def _log_agent_event(state: InstrumentState, node: str, io: str, payload: Dict[str, object]) -> None:
    events = state.get("agent_events", [])
    events.append(
        {
            "event_type": "agent_log",
            "agent_id": "instrument_specialist",
            "node": node,
            "phase": state.get("phase", "tool_phase"),
            "io": io,
            "payload": payload,
        }
    )
    state["agent_events"] = events


def _log_edge(state: InstrumentState, source: str, target: str) -> None:
    events = state.get("agent_events", [])
    events.append(
        {
            "event_type": "agent_edge",
            "agent_id": "instrument_specialist",
            "source": source,
            "target": target,
            "phase": state.get("phase", "tool_phase"),
        }
    )
    state["agent_events"] = events


def _mark(state: InstrumentState, node: str) -> None:
    visited = state.get("visited", [])
    visited.append(node)
    state["visited"] = visited


def read_memory(state: InstrumentState) -> InstrumentState:
    _mark(state, "read_memory")
    _log_agent_event(state, "read_memory", "input", {"keys": ["belief", "last_tool", "notes_tail"]})
    db = state["db"]
    run_id = state["run_id"]
    last_belief = db.load_agent_memory(run_id, "instrument_specialist", "belief")
    last_tool = db.load_agent_memory(run_id, "instrument_specialist", "last_tool")
    notes_tail = db.load_agent_memory(run_id, "instrument_specialist", "notes_tail") or []
    state["last_belief"] = last_belief
    state["last_tool"] = last_tool
    state["notes_tail"] = notes_tail
    _log_agent_event(
        state,
        "read_memory",
        "output",
        {"has_belief": bool(last_belief), "last_tool": last_tool, "notes_count": len(notes_tail)},
    )
    return state


def sense_world(state: InstrumentState) -> InstrumentState:
    _mark(state, "sense_world")
    _log_agent_event(state, "sense_world", "input", {"tools": ["sensor_ocean_signal", "telemetry_power_bus"]})
    current_state = state["state"]
    context = ToolContext(
        run_id=state["run_id"],
        turn=current_state.turn,
        agent_id="instrument_specialist",
        seed=state["seed"],
        game_state=current_state,
        history=None,
    )
    mcp = state["mcp"]
    readings = {}

    ocean = mcp.call_read("sensor_ocean_signal", context, mode="NORMAL")
    power = mcp.call_read("telemetry_power_bus", context)
    readings["sensor_ocean_signal"] = ocean
    readings["telemetry_power_bus"] = power
    readings["state_exact"] = {
        "tension": current_state.tension,
        "crew_load": current_state.crew_load,
        "earth_pressure": current_state.earth_pressure,
        "ocean_activity": current_state.ocean_activity,
        "station_power": current_state.station_power,
    }
    state["readings"] = readings
    turn = current_state.turn
    events = state.get("agent_events", [])
    events.append(
        {
            "event_type": "tool_read",
            "turn": turn,
            "payload": {
                "agent_id": "instrument_specialist",
                "tool_name": "sensor_ocean_signal",
                "inputs": {"mode": "NORMAL"},
                "output": ocean,
            },
        }
    )
    events.append(
        {
            "event_type": "tool_read",
            "turn": turn,
            "payload": {
                "agent_id": "instrument_specialist",
                "tool_name": "telemetry_power_bus",
                "inputs": {},
                "output": power,
            },
        }
    )
    state["agent_events"] = events
    _log_agent_event(state, "sense_world", "output", {"readings": list(readings.keys())})
    return state


def fuse(state: InstrumentState) -> InstrumentState:
    _mark(state, "fuse")
    _log_agent_event(state, "fuse", "input", {"reading_keys": list(state.get("readings", {}).keys())})
    readings = state.get("readings", {})
    last_belief = state.get("last_belief")
    belief, quality, contradictions, notes = fuse_readings(readings, last_belief)
    state["belief"] = belief
    state["belief_quality"] = quality
    state["contradictions"] = contradictions
    state["notes"] = notes
    _log_agent_event(
        state,
        "fuse",
        "output",
        {"belief_quality": quality, "contradictions": contradictions},
    )
    return state


def decide_tool(state: InstrumentState) -> InstrumentState:
    _mark(state, "decide_tool")
    _log_agent_event(state, "decide_tool", "input", {"mode": str(state.get("mode"))})
    stance = state.get("decisions", {}).get("stance", "HOLD")
    belief = state.get("belief", {})
    mode = state.get("mode", DecisionMode.DETERMINISTIC)
    allowed_tools = {"probe_sampling", "filter_pipeline", "hold_sampling"}
    state["stance"] = stance

    if mode == DecisionMode.DETERMINISTIC:
        tool_call = deterministic_tool_choice_instrument(stance, belief)
    elif mode == DecisionMode.LLM:
        tool_call = llm_choose_tool_instrument(
            stance,
            belief,
            allowed_tools,
            resolve_model_name(),
            state["state"],
        )
    else:
        quality = state.get("belief_quality", 0.0)
        contradictions = state.get("contradictions", 0)
        if quality >= 0.70 and contradictions == 0:
            tool_call = deterministic_tool_choice_instrument(stance, belief)
        else:
            tool_call = llm_choose_tool_instrument(
                stance,
                belief,
                allowed_tools,
                resolve_model_name(),
                state["state"],
            )

    ok, reason = validate_tool_call("instrument_specialist", tool_call, allowed_tools)
    if not ok:
        fallback = deterministic_tool_choice_instrument(stance, belief)
        tool_call = ToolCall(
            tool_name=fallback.tool_name,
            args=fallback.args,
            reason=f"validation fallback: {reason}",
            chosen_by="fallback",
        )

    tool_call = apply_guardrails_tool_call(state["state"], tool_call)
    state["tool_call"] = {
        "tool_name": tool_call.tool_name,
        "args": tool_call.args,
        "reason": tool_call.reason,
        "chosen_by": tool_call.chosen_by,
    }
    _log_agent_event(state, "decide_tool", "output", {"tool": tool_call.tool_name, "chosen_by": tool_call.chosen_by})
    return state


def apply_tool(state: InstrumentState) -> InstrumentState:
    _mark(state, "apply_tool")
    _log_agent_event(state, "apply_tool", "input", {"tool": state.get("tool_call", {}).get("tool_name")})
    tool_call = state.get("tool_call", {})
    current_state = state["state"]
    context = ToolContext(
        run_id=state["run_id"],
        turn=current_state.turn,
        agent_id="instrument_specialist",
        seed=state["seed"],
        game_state=current_state,
        history=None,
    )
    output = state["mcp"].call_write(tool_call["tool_name"], context, **tool_call.get("args", {}))
    state["tool_write_output"] = output
    events = state.get("agent_events", [])
    events.append(
        {
            "event_type": "tool_write",
            "turn": current_state.turn,
            "payload": {
                "agent_id": "instrument_specialist",
                "tool_name": tool_call["tool_name"],
                "inputs": tool_call.get("args", {}),
                "output": output,
            },
        }
    )
    state["agent_events"] = events
    _log_agent_event(state, "apply_tool", "output", {"applied": output.get("applied", True)})
    return state


def write_memory(state: InstrumentState) -> InstrumentState:
    _mark(state, "write_memory")
    _log_agent_event(state, "write_memory", "input", {"notes": len(state.get("notes", []))})
    run_id = state["run_id"]
    notes_tail = list(state.get("notes_tail", []))
    notes_tail.extend(state.get("notes", []))
    notes_tail = notes_tail[-5:]

    state["db"].save_agent_memory(run_id, "instrument_specialist", "belief", state.get("belief", {}))
    last_tool = state.get("tool_call", {}).get("tool_name", "")
    state["db"].save_agent_memory(run_id, "instrument_specialist", "last_tool", last_tool)
    state["db"].save_agent_memory(run_id, "instrument_specialist", "notes_tail", notes_tail)
    state["notes_tail"] = notes_tail
    _log_agent_event(state, "write_memory", "output", {"notes_tail": len(notes_tail)})
    return state


def observe_stub(state: InstrumentState) -> InstrumentState:
    _mark(state, "observe_stub")
    _log_agent_event(state, "observe_stub", "input", {})
    belief = state.get("belief", {})
    ocean = belief.get("ocean_activity_hat", state["state"].ocean_activity)
    power = belief.get("station_power_hat", state["state"].station_power)
    tool = state.get("tool_call", {}).get("tool_name", "none")
    state["observation"] = f"Instrument report: ocean {ocean:.2f}, power {power:.2f}, action {tool}."
    _log_agent_event(state, "observe_stub", "output", {"observation": state["observation"]})
    return state


def route_phase_node(state: InstrumentState) -> InstrumentState:
    _mark(state, "route_phase")
    return state


def route_phase(state: InstrumentState) -> str:
    phase = state.get("phase", "tool_phase")
    if phase in ("observe", "observe_phase"):
        _log_edge(state, "route_phase", "observe_stub")
        return "observe_stub"
    _log_edge(state, "route_phase", "read_memory")
    return "read_memory"
