"""Deterministic policies and tool validation."""

from typing import Dict, Set, Tuple

from agents.types import ToolCall
from core.state import GameState


_TOOL_ARGS: Dict[str, Set[str]] = {
    "probe_sampling": {"intensity"},
    "filter_pipeline": {"strength"},
    "hold_sampling": set(),
    "rest_protocol": {"duration"},
    "tighten_procedures": {"level"},
    "throttle_information": {"level"},
}


def deterministic_tool_choice_instrument(stance: str, belief: Dict[str, float]) -> ToolCall:
    stance = stance.upper()
    station_power = belief.get("station_power_hat", 0.0)
    tension = belief.get("tension_hat", 0.0)

    if station_power < 0.20:
        return ToolCall(
            tool_name="hold_sampling",
            args={},
            reason="station_power_hat low; holding sampling",
            chosen_by="deterministic",
        )
    if tension > 0.75:
        return ToolCall(
            tool_name="filter_pipeline",
            args={"strength": "HIGH"},
            reason="tension_hat high; filter aggressively",
            chosen_by="deterministic",
        )
    if stance == "PROBE":
        return ToolCall(
            tool_name="probe_sampling",
            args={"intensity": "MEDIUM"},
            reason="stance=PROBE",
            chosen_by="deterministic",
        )
    if stance == "FILTER":
        return ToolCall(
            tool_name="filter_pipeline",
            args={"strength": "MEDIUM"},
            reason="stance=FILTER",
            chosen_by="deterministic",
        )
    return ToolCall(
        tool_name="hold_sampling",
        args={},
        reason="stance=HOLD",
        chosen_by="deterministic",
    )


def deterministic_tool_choice_crew(stance: str, belief: Dict[str, float]) -> ToolCall:
    stance = stance.upper()
    crew_load = float(belief.get("crew_load_hat", 0.0))
    tension = float(belief.get("tension_hat", 0.0))

    if crew_load >= 0.85:
        return ToolCall(
            tool_name="rest_protocol",
            args={"duration": "LONG"},
            reason="crew_load_hat critical; rest long",
            chosen_by="deterministic",
        )
    if tension >= 0.75:
        return ToolCall(
            tool_name="tighten_procedures",
            args={"level": "HIGH"},
            reason="tension_hat high; tighten procedures",
            chosen_by="deterministic",
        )

    if stance == "PROTECT":
        if crew_load >= 0.65:
            return ToolCall(
                tool_name="rest_protocol",
                args={"duration": "STANDARD"},
                reason="stance=PROTECT; crew_load elevated",
                chosen_by="deterministic",
            )
        return ToolCall(
            tool_name="throttle_information",
            args={"level": "MEDIUM"},
            reason="stance=PROTECT; throttle information",
            chosen_by="deterministic",
        )

    if stance == "PUSH":
        if crew_load < 0.55:
            return ToolCall(
                tool_name="tighten_procedures",
                args={"level": "LOW"},
                reason="stance=PUSH; tighten low",
                chosen_by="deterministic",
            )
        return ToolCall(
            tool_name="rest_protocol",
            args={"duration": "SHORT"},
            reason="stance=PUSH; short rest for recovery",
            chosen_by="deterministic",
        )

    if tension >= 0.65:
        return ToolCall(
            tool_name="tighten_procedures",
            args={"level": "MEDIUM"},
            reason="stance=BALANCE; tension elevated",
            chosen_by="deterministic",
        )
    if crew_load >= 0.65:
        return ToolCall(
            tool_name="throttle_information",
            args={"level": "MEDIUM"},
            reason="stance=BALANCE; crew_load elevated",
            chosen_by="deterministic",
        )
    return ToolCall(
        tool_name="throttle_information",
        args={"level": "LOW"},
        reason="stance=BALANCE; steady operations",
        chosen_by="deterministic",
    )


def validate_tool_call(agent_id: str, tool_call: ToolCall, allowed_tools: Set[str]) -> Tuple[bool, str]:
    if tool_call.tool_name not in allowed_tools:
        return False, f"tool {tool_call.tool_name} not allowed for {agent_id}"
    expected_args = _TOOL_ARGS.get(tool_call.tool_name)
    if expected_args is None:
        return False, f"tool {tool_call.tool_name} has no schema"
    provided_args = set(tool_call.args.keys())
    if provided_args != expected_args:
        return False, f"tool {tool_call.tool_name} args mismatch"
    return True, "ok"


def apply_guardrails_tool_call(state: GameState, tool_call: ToolCall) -> ToolCall:
    if state.station_power < 0.05 and tool_call.tool_name != "hold_sampling":
        return ToolCall(
            tool_name="hold_sampling",
            args={},
            reason="station_power critically low; forced hold",
            chosen_by=tool_call.chosen_by,
        )
    return tool_call
