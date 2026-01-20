"""Ending registry and placeholder endings."""

from dataclasses import dataclass
from typing import Callable, List, Optional

from core.state import GameState


@dataclass(frozen=True)
class EndingSpec:
    id: str
    title: str
    priority: int
    condition: Callable[[GameState], bool]
    render_text: Callable[[GameState], str]


class EndingRegistry:
    def __init__(self) -> None:
        self._specs: List[EndingSpec] = []

    def register(self, spec: EndingSpec) -> None:
        self._specs.append(spec)

    def list(self) -> List[EndingSpec]:
        return list(self._specs)

    def evaluate(self, state: GameState) -> Optional[EndingSpec]:
        best: Optional[EndingSpec] = None
        for spec in self._specs:
            if spec.condition(state):
                if best is None or spec.priority > best.priority:
                    best = spec
        return best
