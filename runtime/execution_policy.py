"""Shared policy primitives for protected execution mutations."""

from dataclasses import dataclass
from typing import Any, Mapping, Optional


@dataclass(frozen=True)
class ExecutionMutationContext:
    """Concurrency credentials attached to a lifecycle mutation."""

    expected_version: int
    fencing_token: Optional[int] = None
    correlation_id: Optional[str] = None


def require_execution_context(
    *, expected_version: Optional[int], fencing_token: Optional[int]
) -> ExecutionMutationContext:
    """Require explicit optimistic-concurrency credentials for runtime mutation."""
    if expected_version is None:
        raise ValueError("runtime lifecycle mutation requires expected_version")
    return ExecutionMutationContext(expected_version=expected_version, fencing_token=fencing_token)
