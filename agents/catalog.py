"""Agent catalog and registry."""

# Per langgraph-Application structure.md: File structure

from dataclasses import dataclass
from typing import Callable, Dict, List

from agents.base import BaseAgent
from agents.types import AgentKind
from agents.crew_officer.agent import CrewOfficerAgent
from agents.instrument_specialist.agent import InstrumentSpecialistAgent


@dataclass(frozen=True)
class AgentSpec:
    agent_id: str
    kind: AgentKind
    allowed_stances: List[str]
    default_stance: str
    builder: Callable[[], BaseAgent]


_REGISTRY: Dict[str, AgentSpec] = {}


def register_agent(spec: AgentSpec) -> None:
    _REGISTRY[spec.agent_id] = spec


def list_agents() -> List[AgentSpec]:
    return list(_REGISTRY.values())


def get_agent(agent_id: str) -> AgentSpec:
    if agent_id not in _REGISTRY:
        raise KeyError(f"Unknown agent_id: {agent_id}")
    return _REGISTRY[agent_id]


def _placeholder_builder() -> BaseAgent:
    raise NotImplementedError("Agent not implemented yet.")


register_agent(
    AgentSpec(
        agent_id="instrument_specialist",
        kind=AgentKind.PLAYER_DRIVEN,
        allowed_stances=["PROBE", "FILTER", "HOLD"],
        default_stance="HOLD",
        builder=InstrumentSpecialistAgent,
    )
)

register_agent(
    AgentSpec(
        agent_id="crew_officer",
        kind=AgentKind.PLAYER_DRIVEN,
        allowed_stances=["PUSH", "PROTECT", "BALANCE"],
        default_stance="BALANCE",
        builder=CrewOfficerAgent,
    )
)

register_agent(
    AgentSpec(
        agent_id="solaris",
        kind=AgentKind.AUTONOMOUS,
        allowed_stances=[],
        default_stance="",
        builder=_placeholder_builder,
    )
)
