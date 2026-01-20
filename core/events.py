"""Event models for the simulation."""

from dataclasses import dataclass, asdict
from typing import Any, Dict


@dataclass(frozen=True)
class RunStarted:
    run_id: str
    seed: int
    created_at: str

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["type"] = "RunStarted"
        return data


@dataclass(frozen=True)
class TurnStarted:
    turn: int
    decisions: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["type"] = "TurnStarted"
        return data


@dataclass(frozen=True)
class StateDeltaApplied:
    turn: int
    source: str
    delta_dict: Dict[str, Any]
    state_before: Dict[str, Any]
    state_after: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["type"] = "StateDeltaApplied"
        return data


@dataclass(frozen=True)
class TurnEnded:
    turn: int
    state_snapshot: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["type"] = "TurnEnded"
        return data


@dataclass(frozen=True)
class RunEnded:
    run_id: str
    ending_id: str
    ending_title: str
    turn: int
    final_state: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["type"] = "RunEnded"
        return data


def serialize_event(event: Any) -> Dict[str, Any]:
    if hasattr(event, "to_dict"):
        return event.to_dict()
    data = asdict(event)
    data["type"] = type(event).__name__
    return data
