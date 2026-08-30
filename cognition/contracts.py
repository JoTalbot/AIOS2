"""Contracts separating cognition decisions from durable execution runtime."""

from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol, Sequence

from runtime.execution_context import ExecutionContext


@dataclass(frozen=True)
class CognitionRequest:
    """Read-only cognition input derived from the canonical execution context."""

    context: ExecutionContext
    observation: Any = None
    history: Sequence[Any] = field(default_factory=tuple)


@dataclass(frozen=True)
class CognitionDecision:
    """Ephemeral cognition output; runtime decides whether/how it is persisted."""

    kind: str
    value: Any = None
    metadata: Mapping[str, Any] = field(default_factory=dict)


class Planner(Protocol):
    async def plan(self, request: CognitionRequest) -> CognitionDecision: ...


class Evaluator(Protocol):
    async def evaluate(self, request: CognitionRequest) -> CognitionDecision: ...


class Reflector(Protocol):
    async def reflect(self, request: CognitionRequest) -> CognitionDecision: ...


class Learner(Protocol):
    async def learn(self, request: CognitionRequest) -> CognitionDecision: ...
