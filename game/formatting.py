"""Event formatting helpers for the TUI."""

import json
from typing import Any, Dict, List


def _format_float(value: float) -> str:
    text = f"{value:.4f}".rstrip("0").rstrip(".")
    return text if text else "0"


def _round_floats(value: Any) -> Any:
    if isinstance(value, float):
        return _format_float(value)
    if isinstance(value, dict):
        return {key: _round_floats(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_round_floats(item) for item in value]
    return value


def _compact(data: Any, limit: int = 120) -> str:
    try:
        text = json.dumps(_round_floats(data), separators=(",", ":"), ensure_ascii=True)
    except TypeError:
        text = str(data)
    if len(text) > limit:
        return text[: limit - 3] + "..."
    return text


def _format_delta(delta: Dict[str, Any]) -> str:
    parts = []
    for key, value in delta.items():
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        sign = "+" if number >= 0 else ""
        parts.append(f"{key} {sign}{_format_float(number)}")
    return ", ".join(parts)


def _format_snapshot(snapshot: Dict[str, Any]) -> str:
    fields = [
        "tension",
        "ocean_activity",
        "crew_load",
        "earth_pressure",
        "station_power",
        "turn",
    ]
    parts = []
    for key in fields:
        if key not in snapshot:
            continue
        value = snapshot[key]
        if isinstance(value, (float, int)):
            parts.append(f"{key}={_format_float(float(value))}")
        else:
            parts.append(f"{key}={value}")
    return ", ".join(parts)


def format_event_line(event: Dict[str, Any]) -> List[str]:
    event_type = event.get("event_type") or event.get("type")
    lines: List[str] = []

    if event_type == "agent_log":
        agent = event.get("agent_id", "agent").replace("_", " ").title()
        node = event.get("node", "node")
        io = event.get("io", "io")
        payload = event.get("payload", {})
        lines.append(f"[{agent}][{node}][{io}]: {_compact(payload)}")
        return lines

    if event_type == "agent_edge":
        agent = event.get("agent_id", "agent").replace("_", " ").title()
        source = event.get("source", "?")
        target = event.get("target", "?")
        lines.append(f"[{agent}][edge]: {source} -> {target}")
        return lines

    if event_type == "tool_read":
        payload = event.get("payload", {})
        tool = payload.get("tool_name", "tool")
        output = payload.get("output", {})
        value = output.get("value")
        sigma = output.get("sigma")
        flags = output.get("flags", {})
        lines.append(f"[MCP][tool_read][{tool}]: value={value} sigma={sigma} flags={_compact(flags)}")
        return lines

    if event_type == "tool_write":
        payload = event.get("payload", {})
        tool = payload.get("tool_name", "tool")
        output = payload.get("output", {})
        delta = output.get("delta", {})
        cost = output.get("cost", {})
        args = payload.get("inputs", {})
        lines.append(
            f"[MCP][tool_write][{tool}]: args={_compact(args)} cost={_compact(cost)} delta={_compact(delta)}"
        )
        return lines

    if event_type == "StateDeltaApplied":
        source = event.get("source", "state")
        delta = event.get("delta_dict", {})
        lines.append(f"[CORE][delta][{source}]: {_format_delta(delta)}")
        return lines

    if event_type == "TurnStarted":
        turn = event.get("turn", "?")
        decisions = event.get("decisions", {})
        lines.append(f"[TURN][start]: turn={turn} decisions={_compact(decisions)}")
        return lines

    if event_type == "TurnEnded":
        snapshot = event.get("state_snapshot", {})
        lines.append(f"[TURN][end]: {_format_snapshot(snapshot)}")
        return lines

    if event_type == "RunStarted":
        run_id = event.get("run_id", "")
        lines.append(f"[RUN][start]: {run_id}")
        return lines

    if event_type == "RunEnded":
        title = event.get("ending_title", "")
        lines.append(f"[RUN][end]: {title}")
        return lines

    lines.append(f"[EVENT]: {_compact(event)}")
    return lines
