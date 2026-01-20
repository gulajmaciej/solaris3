"""Read-only MCP tools for noisy telemetry."""

from __future__ import annotations

import hashlib
import random
from typing import Dict

from mcp.context import ToolContext
from mcp.contracts import build_read_response, clamp01


def _seed_for(context: ToolContext, tool_name: str) -> int:
    payload = f"{context.run_id}:{context.turn}:{context.agent_id}:{tool_name}"
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return int(digest[:16], 16)


def _flag_draws(rng: random.Random, tension: float, earth_pressure: float, station_power: float) -> Dict[str, bool]:
    glitch = rng.random() < (0.05 + 0.20 * tension)
    stale = rng.random() < (0.03 + 0.10 * earth_pressure)
    missing = rng.random() < (0.01 + 0.05 * (1.0 - station_power))
    return {"glitch": glitch, "stale": stale, "missing": missing}


def sensor_ocean_signal(context: ToolContext, mode: str = "NORMAL") -> Dict[str, object]:
    tool_name = "sensor_ocean_signal"
    rng = random.Random(_seed_for(context, tool_name))
    state = context.game_state
    sigma = 0.02 + 0.06 * state.tension + 0.03 * state.earth_pressure + 0.04 * (1.0 - state.station_power)
    flags = _flag_draws(rng, state.tension, state.earth_pressure, state.station_power)
    as_of_turn = context.turn - 1 if flags["stale"] else context.turn
    if flags["missing"]:
        return build_read_response(None, sigma, flags, as_of_turn, f"mode={mode}, missing")
    noise = rng.normalvariate(0.0, sigma * (3.0 if flags["glitch"] else 1.0))
    value = clamp01(state.ocean_activity + noise)
    return build_read_response(value, sigma, flags, as_of_turn, f"mode={mode}")


def sensor_crew_status(context: ToolContext) -> Dict[str, object]:
    tool_name = "sensor_crew_status"
    rng = random.Random(_seed_for(context, tool_name))
    state = context.game_state
    sigma = 0.02 + 0.05 * state.crew_load + 0.03 * state.tension
    flags = _flag_draws(rng, state.tension, state.earth_pressure, state.station_power)
    as_of_turn = context.turn - 1 if flags["stale"] else context.turn
    if flags["missing"]:
        return build_read_response(None, sigma, flags, as_of_turn, "missing")
    noise = rng.normalvariate(0.0, sigma * (2.0 if flags["glitch"] else 1.0))
    value = clamp01(state.crew_load + noise)
    return build_read_response(value, sigma, flags, as_of_turn, "")


def telemetry_power_bus(context: ToolContext) -> Dict[str, object]:
    tool_name = "telemetry_power_bus"
    rng = random.Random(_seed_for(context, tool_name))
    state = context.game_state
    sigma = 0.005 + 0.003 * (1.0 - state.station_power)
    flags = {
        "glitch": rng.random() < 0.02,
        "stale": rng.random() < 0.01,
        "missing": rng.random() < 0.01,
    }
    as_of_turn = context.turn - 1 if flags["stale"] else context.turn
    if flags["missing"]:
        return build_read_response(None, sigma, flags, as_of_turn, "missing")
    noise = rng.normalvariate(0.0, sigma * (2.5 if flags["glitch"] else 1.0))
    value = clamp01(state.station_power + noise)
    return build_read_response(value, sigma, flags, as_of_turn, "")


def comms_earth_channel(context: ToolContext) -> Dict[str, object]:
    tool_name = "comms_earth_channel"
    rng = random.Random(_seed_for(context, tool_name))
    state = context.game_state
    sigma = 0.02 + 0.06 * state.earth_pressure + 0.02 * state.tension
    flags = _flag_draws(rng, state.tension, state.earth_pressure, state.station_power)
    as_of_turn = context.turn - 1 if flags["stale"] else context.turn
    if flags["missing"]:
        return build_read_response(None, sigma, flags, as_of_turn, "missing")
    noise = rng.normalvariate(0.0, sigma * (2.0 if flags["glitch"] else 1.0))
    value = clamp01(state.earth_pressure + noise)
    return build_read_response(value, sigma, flags, as_of_turn, "")
