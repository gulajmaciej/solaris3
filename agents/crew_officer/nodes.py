"""LangGraph nodes for crew officer."""

# Per langgraph-Application structure.md: Graphs

from typing import Dict

from agents.common.belief import fuse_readings
from agents.common.decision import (
    apply_guardrails_tool_call,
    deterministic_tool_choice_crew,
    validate_tool_call,
)
from agents.common.llm import llm_choose_tool_crew, resolve_model_name
from agents.types import DecisionMode, ToolCall
from mcp.context import ToolContext

from agents.crew_officer.state import CrewOfficerState


def _log_agent_event(state: CrewOfficerState, node: str, io: str, payload: Dict[str, object]) -> None:
    events = state.get("agent_events", [])
    events.append(
        {
            "event_type": "agent_log",
            "agent_id": "crew_officer",
            "node": node,
            "phase": state.get("phase", "tool_phase"),
            "io": io,
            "payload": payload,
        }
    )
    state["agent_events"] = events


def _log_edge(state: CrewOfficerState, source: str, target: str) -> None:
    events = state.get("agent_events", [])
    events.append(
        {
            "event_type": "agent_edge",
            "agent_id": "crew_officer",
            "source": source,
            "target": target,
            "phase": state.get("phase", "tool_phase"),
        }
    )
    state["agent_events"] = events


def _mark(state: CrewOfficerState, node: str) -> None:
    visited = state.get("visited", [])
    visited.append(node)
    state["visited"] = visited


def read_memory(state: CrewOfficerState) -> CrewOfficerState:
    _mark(state, "read_memory")
    _log_agent_event(state, "read_memory", "input", {"keys": ["belief", "last_tool", "notes_tail"]})
    db = state["db"]
    run_id = state["run_id"]
    last_belief = db.load_agent_memory(run_id, "crew_officer", "belief")
    last_tool = db.load_agent_memory(run_id, "crew_officer", "last_tool")
    notes_tail = db.load_agent_memory(run_id, "crew_officer", "notes_tail") or []
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


def sense_world(state: CrewOfficerState) -> CrewOfficerState:
    _mark(state, "sense_world")
    _log_agent_event(
        state,
        "sense_world",
        "input",
        {"tools": ["sensor_crew_status", "comms_earth_channel", "telemetry_power_bus", "sensor_ocean_signal"]},
    )
    current_state = state["state"]
    context = ToolContext(
        run_id=state["run_id"],
        turn=current_state.turn,
        agent_id="crew_officer",
        seed=state["seed"],
        game_state=current_state,
        history=None,
    )
    mcp = state["mcp"]
    readings = {}

    crew = mcp.call_read("sensor_crew_status", context)
    earth = mcp.call_read("comms_earth_channel", context)
    power = mcp.call_read("telemetry_power_bus", context)
    ocean = mcp.call_read("sensor_ocean_signal", context, mode="NORMAL")

    readings["sensor_crew_status"] = crew
    readings["comms_earth_channel"] = earth
    readings["telemetry_power_bus"] = power
    readings["sensor_ocean_signal"] = ocean
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
                "agent_id": "crew_officer",
                "tool_name": "sensor_crew_status",
                "inputs": {},
                "output": crew,
            },
        }
    )
    events.append(
        {
            "event_type": "tool_read",
            "turn": turn,
            "payload": {
                "agent_id": "crew_officer",
                "tool_name": "comms_earth_channel",
                "inputs": {},
                "output": earth,
            },
        }
    )
    events.append(
        {
            "event_type": "tool_read",
            "turn": turn,
            "payload": {
                "agent_id": "crew_officer",
                "tool_name": "telemetry_power_bus",
                "inputs": {},
                "output": power,
            },
        }
    )
    events.append(
        {
            "event_type": "tool_read",
            "turn": turn,
            "payload": {
                "agent_id": "crew_officer",
                "tool_name": "sensor_ocean_signal",
                "inputs": {"mode": "NORMAL"},
                "output": ocean,
            },
        }
    )
    state["agent_events"] = events
    _log_agent_event(state, "sense_world", "output", {"readings": list(readings.keys())})
    return state


def fuse(state: CrewOfficerState) -> CrewOfficerState:
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


def decide_tool(state: CrewOfficerState) -> CrewOfficerState:
    _mark(state, "decide_tool")
    _log_agent_event(state, "decide_tool", "input", {"mode": str(state.get("mode"))})
    stance = state.get("decisions", {}).get("stance", "BALANCE")
    belief = state.get("belief", {})
    mode = state.get("mode", DecisionMode.DETERMINISTIC)
    allowed_tools = {"rest_protocol", "tighten_procedures", "throttle_information"}
    state["stance"] = stance

    if mode == DecisionMode.DETERMINISTIC:
        tool_call = deterministic_tool_choice_crew(stance, belief)
    elif mode == DecisionMode.LLM:
        tool_call = llm_choose_tool_crew(
            stance,
            belief,
            allowed_tools,
            resolve_model_name(),
            state["state"],
        )
    else:
        quality = state.get("belief_quality", 0.0)
        contradictions = state.get("contradictions", 0)
        crew_load = float(belief.get("crew_load_hat", 0.0))
        tension = float(belief.get("tension_hat", 0.0))
        if quality < 0.70 or contradictions > 0 or crew_load > 0.70 or tension > 0.70:
            tool_call = llm_choose_tool_crew(
                stance,
                belief,
                allowed_tools,
                resolve_model_name(),
                state["state"],
            )
        else:
            tool_call = deterministic_tool_choice_crew(stance, belief)

    ok, reason = validate_tool_call("crew_officer", tool_call, allowed_tools)
    if not ok:
        fallback = deterministic_tool_choice_crew(stance, belief)
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


def apply_tool(state: CrewOfficerState) -> CrewOfficerState:
    _mark(state, "apply_tool")
    _log_agent_event(state, "apply_tool", "input", {"tool": state.get("tool_call", {}).get("tool_name")})
    tool_call = state.get("tool_call", {})
    current_state = state["state"]
    context = ToolContext(
        run_id=state["run_id"],
        turn=current_state.turn,
        agent_id="crew_officer",
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
                "agent_id": "crew_officer",
                "tool_name": tool_call["tool_name"],
                "inputs": tool_call.get("args", {}),
                "output": output,
            },
        }
    )
    state["agent_events"] = events
    _log_agent_event(state, "apply_tool", "output", {"applied": output.get("applied", True)})
    return state


def write_memory(state: CrewOfficerState) -> CrewOfficerState:
    _mark(state, "write_memory")
    _log_agent_event(state, "write_memory", "input", {"notes": len(state.get("notes", []))})
    run_id = state["run_id"]
    notes_tail = list(state.get("notes_tail", []))
    notes_tail.extend(state.get("notes", []))
    tool_name = state.get("tool_call", {}).get("tool_name", "")
    if tool_name:
        notes_tail.append(f"action {tool_name}")
    notes_tail = notes_tail[-5:]

    state["db"].save_agent_memory(run_id, "crew_officer", "belief", state.get("belief", {}))
    last_tool = state.get("tool_call", {}).get("tool_name", "")
    state["db"].save_agent_memory(run_id, "crew_officer", "last_tool", last_tool)
    state["db"].save_agent_memory(run_id, "crew_officer", "notes_tail", notes_tail)
    state["notes_tail"] = notes_tail
    _log_agent_event(state, "write_memory", "output", {"notes_tail": len(notes_tail)})
    return state


def observe_stub(state: CrewOfficerState) -> CrewOfficerState:
    _mark(state, "observe_stub")
    _log_agent_event(state, "observe_stub", "input", {})
    belief = state.get("belief", {})
    crew = belief.get("crew_load_hat", state["state"].crew_load)
    tension = belief.get("tension_hat", state["state"].tension)
    tool = state.get("tool_call", {}).get("tool_name", "none")
    state["observation"] = f"Crew report: load {crew:.2f}, tension {tension:.2f}, action {tool}."
    _log_agent_event(state, "observe_stub", "output", {"observation": state["observation"]})
    return state


def route_phase_node(state: CrewOfficerState) -> CrewOfficerState:
    _mark(state, "route_phase")
    return state


def route_phase(state: CrewOfficerState) -> str:
    phase = state.get("phase", "tool_phase")
    if phase in ("observe", "observe_phase"):
        _log_edge(state, "route_phase", "observe_stub")
        return "observe_stub"
    _log_edge(state, "route_phase", "read_memory")
    return "read_memory"
