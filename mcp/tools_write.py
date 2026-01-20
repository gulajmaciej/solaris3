"""Write tools that return deterministic deltas."""

from __future__ import annotations

from typing import Dict

from mcp.context import ToolContext
from mcp.contracts import apply_scaled_delta, build_write_response, clamp01


def _power_factor(station_power: float, required_power: float) -> float:
    if required_power <= 0.0:
        return 1.0
    return max(0.1, clamp01(station_power / required_power))


def _build_response(
    delta: Dict[str, float],
    required_power: float,
    power_factor: float,
) -> Dict[str, object]:
    scaled = apply_scaled_delta(delta, power_factor)
    cost = {"station_power": required_power * power_factor}
    reason = f"scaled by power_factor={power_factor:.2f}"
    return build_write_response(True, cost, scaled, reason)


_PROBE_DELTAS = {
    "LOW": {"ocean_activity": 0.03, "tension": 0.01, "crew_load": 0.01, "earth_pressure": 0.005, "station_power": -0.08},
    "MEDIUM": {"ocean_activity": 0.05, "tension": 0.02, "crew_load": 0.02, "earth_pressure": 0.01, "station_power": -0.12},
    "HIGH": {"ocean_activity": 0.08, "tension": 0.03, "crew_load": 0.03, "earth_pressure": 0.015, "station_power": -0.18},
}
_PROBE_POWER = {"LOW": 0.20, "MEDIUM": 0.30, "HIGH": 0.40}

_FILTER_DELTAS = {
    "LOW": {"ocean_activity": -0.02, "tension": -0.01, "crew_load": 0.005, "earth_pressure": -0.005, "station_power": -0.06},
    "MEDIUM": {"ocean_activity": -0.04, "tension": -0.02, "crew_load": 0.01, "earth_pressure": -0.01, "station_power": -0.09},
    "HIGH": {"ocean_activity": -0.06, "tension": -0.03, "crew_load": 0.015, "earth_pressure": -0.015, "station_power": -0.12},
}
_FILTER_POWER = {"LOW": 0.15, "MEDIUM": 0.25, "HIGH": 0.35}

_HOLD_DELTA = {"ocean_activity": -0.01, "tension": -0.005, "crew_load": -0.01, "earth_pressure": -0.005, "station_power": -0.02}
_HOLD_POWER = 0.08

_REST_DELTAS = {
    "SHORT": {"crew_load": -0.03, "tension": -0.01, "earth_pressure": 0.005, "ocean_activity": -0.005, "station_power": -0.04},
    "STANDARD": {"crew_load": -0.05, "tension": -0.02, "earth_pressure": 0.01, "ocean_activity": -0.01, "station_power": -0.06},
    "LONG": {"crew_load": -0.08, "tension": -0.03, "earth_pressure": 0.015, "ocean_activity": -0.015, "station_power": -0.08},
}
_REST_POWER = {"SHORT": 0.12, "STANDARD": 0.18, "LONG": 0.25}

_TIGHTEN_DELTAS = {
    "LOW": {"tension": 0.01, "crew_load": 0.01, "earth_pressure": -0.005, "ocean_activity": -0.005, "station_power": -0.05},
    "MEDIUM": {"tension": 0.02, "crew_load": 0.02, "earth_pressure": -0.01, "ocean_activity": -0.01, "station_power": -0.08},
    "HIGH": {"tension": 0.03, "crew_load": 0.03, "earth_pressure": -0.015, "ocean_activity": -0.015, "station_power": -0.12},
}
_TIGHTEN_POWER = {"LOW": 0.15, "MEDIUM": 0.25, "HIGH": 0.35}

_THROTTLE_DELTAS = {
    "LOW": {"tension": -0.005, "crew_load": -0.005, "earth_pressure": 0.01, "ocean_activity": 0.0, "station_power": -0.04},
    "MEDIUM": {"tension": -0.01, "crew_load": -0.01, "earth_pressure": 0.02, "ocean_activity": -0.005, "station_power": -0.06},
    "HIGH": {"tension": -0.02, "crew_load": -0.015, "earth_pressure": 0.03, "ocean_activity": -0.01, "station_power": -0.08},
}
_THROTTLE_POWER = {"LOW": 0.12, "MEDIUM": 0.18, "HIGH": 0.25}


def probe_sampling(context: ToolContext, intensity: str) -> Dict[str, object]:
    intensity = intensity.upper()
    delta = _PROBE_DELTAS[intensity]
    required_power = _PROBE_POWER[intensity]
    power_factor = _power_factor(context.game_state.station_power, required_power)
    return _build_response(delta, required_power, power_factor)


def filter_pipeline(context: ToolContext, strength: str) -> Dict[str, object]:
    strength = strength.upper()
    delta = _FILTER_DELTAS[strength]
    required_power = _FILTER_POWER[strength]
    power_factor = _power_factor(context.game_state.station_power, required_power)
    return _build_response(delta, required_power, power_factor)


def hold_sampling(context: ToolContext) -> Dict[str, object]:
    power_factor = _power_factor(context.game_state.station_power, _HOLD_POWER)
    return _build_response(_HOLD_DELTA, _HOLD_POWER, power_factor)


def rest_protocol(context: ToolContext, duration: str) -> Dict[str, object]:
    duration = duration.upper()
    delta = _REST_DELTAS[duration]
    required_power = _REST_POWER[duration]
    power_factor = _power_factor(context.game_state.station_power, required_power)
    return _build_response(delta, required_power, power_factor)


def tighten_procedures(context: ToolContext, level: str) -> Dict[str, object]:
    level = level.upper()
    delta = _TIGHTEN_DELTAS[level]
    required_power = _TIGHTEN_POWER[level]
    power_factor = _power_factor(context.game_state.station_power, required_power)
    return _build_response(delta, required_power, power_factor)


def throttle_information(context: ToolContext, level: str) -> Dict[str, object]:
    level = level.upper()
    delta = _THROTTLE_DELTAS[level]
    required_power = _THROTTLE_POWER[level]
    power_factor = _power_factor(context.game_state.station_power, required_power)
    return _build_response(delta, required_power, power_factor)
