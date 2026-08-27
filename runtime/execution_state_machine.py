"""Domain-level execution state machine for AIOS vNext."""

from dataclasses import dataclass, field
from typing import FrozenSet, Mapping


class InvalidExecutionTransition(ValueError):
    """Raised when an execution lifecycle transition is not allowed."""


DEFAULT_TRANSITIONS: dict[str, FrozenSet[str]] = {
    "pending": frozenset({"running"}),
    "running": frozenset({"retrying", "completed", "failed"}),
    "retrying": frozenset({"running", "failed"}),
    "completed": frozenset(),
    "failed": frozenset({"retrying"}),
}


@dataclass(frozen=True)
class ExecutionStateMachine:
    """Validate execution lifecycle transitions from one canonical state graph."""

    transitions: Mapping[str, FrozenSet[str]] = field(
        default_factory=lambda: DEFAULT_TRANSITIONS.copy()
    )

    def __post_init__(self):
        normalized = {
            str(state): frozenset(str(target) for target in targets)
            for state, targets in self.transitions.items()
        }
        states = set(normalized)
        unknown_targets = {
            target for targets in normalized.values() for target in targets if target not in states
        }
        if unknown_targets:
            raise ValueError(f"transitions reference unknown states: {sorted(unknown_targets)}")
        object.__setattr__(self, "transitions", normalized)

    @property
    def states(self) -> FrozenSet[str]:
        return frozenset(self.transitions)

    def can_transition(self, current: str, target: str) -> bool:
        if current not in self.transitions or target not in self.transitions:
            return False
        return current == target or target in self.transitions[current]

    def validate(self, current: str, target: str) -> None:
        if current not in self.transitions:
            raise InvalidExecutionTransition(f"unknown execution state: {current}")
        if target not in self.transitions:
            raise InvalidExecutionTransition(f"unknown execution state: {target}")
        if not self.can_transition(current, target):
            raise InvalidExecutionTransition(f"invalid execution transition: {current} -> {target}")
