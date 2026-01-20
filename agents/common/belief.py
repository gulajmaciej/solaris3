"""Belief fusion from noisy sensor readings."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple


def _reading_weight(reading: Dict[str, Any]) -> float:
    sigma = float(reading.get("sigma", 0.1))
    flags = reading.get("flags", {}) or {}
    if flags.get("missing"):
        return 0.0
    if flags.get("glitch"):
        sigma *= 2.0
    if flags.get("stale"):
        sigma *= 1.5
    if sigma <= 0.0:
        return 0.0
    return 1.0 / (sigma * sigma)


def _weighted_value(readings: List[Dict[str, Any]]) -> Tuple[Optional[float], float, int]:
    total_weight = 0.0
    total_value = 0.0
    used = 0
    for reading in readings:
        value = reading.get("value")
        if value is None:
            continue
        weight = _reading_weight(reading)
        if weight <= 0.0:
            continue
        total_weight += weight
        total_value += float(value) * weight
        used += 1
    if total_weight <= 0.0:
        return None, 0.0, used
    return total_value / total_weight, total_weight, used


def fuse_readings(
    readings: Dict[str, Dict[str, Any]],
    last_belief: Optional[Dict[str, Any]],
) -> Tuple[Dict[str, float], float, int, List[str]]:
    notes: List[str] = []
    contradictions = 0
    belief: Dict[str, float] = {}

    state_exact = readings.get("state_exact", {})

    def _fallback(key: str, fallback_value: float) -> float:
        if last_belief and key in last_belief:
            notes.append(f"{key} fallback last_belief")
            return float(last_belief[key])
        notes.append(f"{key} fallback state")
        return fallback_value

    ocean_candidates = [readings["sensor_ocean_signal"]] if "sensor_ocean_signal" in readings else []
    ocean_value, ocean_weight, ocean_used = _weighted_value(ocean_candidates)
    if ocean_value is None:
        ocean_value = _fallback("ocean_activity_hat", float(state_exact.get("ocean_activity", 0.0)))
    belief["ocean_activity_hat"] = ocean_value

    crew_candidates = [readings["sensor_crew_status"]] if "sensor_crew_status" in readings else []
    crew_value, crew_weight, crew_used = _weighted_value(crew_candidates)
    if crew_value is None:
        crew_value = _fallback("crew_load_hat", float(state_exact.get("crew_load", 0.0)))
    belief["crew_load_hat"] = crew_value

    power_candidates = [readings["telemetry_power_bus"]] if "telemetry_power_bus" in readings else []
    power_value, power_weight, power_used = _weighted_value(power_candidates)
    if power_value is None:
        power_value = _fallback("station_power_hat", float(state_exact.get("station_power", 0.0)))
    belief["station_power_hat"] = power_value

    earth_candidates = [readings["comms_earth_channel"]] if "comms_earth_channel" in readings else []
    earth_value, earth_weight, earth_used = _weighted_value(earth_candidates)
    if earth_value is None:
        earth_value = _fallback("earth_pressure_hat", float(state_exact.get("earth_pressure", 0.0)))
    belief["earth_pressure_hat"] = earth_value

    belief["tension_hat"] = float(state_exact.get("tension", 0.0))

    spread_checks = [
        ("ocean_activity_hat", ocean_candidates, ocean_value),
        ("crew_load_hat", crew_candidates, crew_value),
        ("station_power_hat", power_candidates, power_value),
        ("earth_pressure_hat", earth_candidates, earth_value),
    ]
    for name, candidates, estimate in spread_checks:
        if len(candidates) >= 2 and estimate is not None:
            values = [c["value"] for c in candidates if c.get("value") is not None]
            if values and max(values) - min(values) > 0.25:
                contradictions += 1
                notes.append(f"{name} contradiction")

    total_weight = ocean_weight + crew_weight + power_weight + earth_weight
    total_used = ocean_used + crew_used + power_used + earth_used
    quality = 0.0
    if total_used > 0:
        quality = min(1.0, total_weight / (total_used * 400.0))
    if contradictions > 0:
        quality *= 0.7
    return belief, quality, contradictions, notes
