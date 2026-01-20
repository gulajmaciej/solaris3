"""Core game state definitions."""

from dataclasses import dataclass


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


@dataclass(frozen=True)
class GameState:
    tension: float
    ocean_activity: float
    crew_load: float
    earth_pressure: float
    station_power: float
    turn: int


def clamp_state(state: GameState) -> GameState:
    return GameState(
        tension=clamp01(state.tension),
        ocean_activity=clamp01(state.ocean_activity),
        crew_load=clamp01(state.crew_load),
        earth_pressure=clamp01(state.earth_pressure),
        station_power=clamp01(state.station_power),
        turn=state.turn,
    )


def initial_state() -> GameState:
    return GameState(
        tension=0.20,
        ocean_activity=0.30,
        crew_load=0.25,
        earth_pressure=0.20,
        station_power=0.60,
        turn=0,
    )
