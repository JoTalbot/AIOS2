"""Stable repository contract for durable execution state.

Concrete storage adapters may be file-backed or distributed, but runtime code
must depend on this protocol rather than a storage format.
"""

from typing import Any, Optional, Protocol

from .execution_store import ExecutionState


class ExecutionRepository(Protocol):
    def get(self, execution_id: str) -> Optional[ExecutionState]: ...

    def transition(
        self,
        execution_id: str,
        status: str,
        *,
        expected_version: int,
        fencing_token: Optional[int] = None,
        _audit: bool = True,
        **updates: Any,
    ) -> ExecutionState: ...
