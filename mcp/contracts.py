"""Shared MCP tool contracts and helpers."""

from typing import Any, Dict


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def apply_scaled_delta(delta: Dict[str, float], power_factor: float) -> Dict[str, float]:
    return {key: value * power_factor for key, value in delta.items()}


def _round_value(value: Any) -> Any:
    if isinstance(value, float):
        return round(value, 4)
    if isinstance(value, dict):
        return {key: _round_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_round_value(item) for item in value]
    return value


def build_read_response(
    value: Any,
    sigma: float,
    flags: Dict[str, bool],
    as_of_turn: int,
    notes: str,
) -> Dict[str, Any]:
    return _round_value(
        {
            "value": value,
            "sigma": sigma,
            "flags": flags,
            "as_of_turn": as_of_turn,
            "notes": notes,
        }
    )


def build_write_response(
    applied: bool,
    cost: Dict[str, float],
    delta: Dict[str, float],
    reason: str,
) -> Dict[str, Any]:
    return _round_value(
        {
            "applied": applied,
            "cost": cost,
            "delta": delta,
            "reason": reason,
        }
    )
