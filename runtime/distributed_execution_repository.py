"""Production adapter seam for distributed execution persistence.

This module intentionally contains a contract-level implementation rather than
binding AIOS runtime code to a particular database vendor. A real deployment
can implement ``DistributedExecutionRepository`` over a transactional KV/SQL
store while preserving CAS + fencing semantics.
"""

from dataclasses import dataclass
from threading import RLock
from typing import Any, Dict, Optional

from .execution_store import ExecutionConcurrencyError, ExecutionState


@dataclass(frozen=True)
class VersionedExecution:
    state: ExecutionState


class DistributedExecutionRepository:
    """Reference in-process model of the distributed repository contract.

    The critical operation is the conditional mutation: version and fencing
    checks happen while holding the repository's atomic transaction boundary.
    External adapters must map this operation to their native transaction/CAS.
    """

    def __init__(self):
        self._lock = RLock()
        self._states: Dict[str, ExecutionState] = {}

    def get(self, execution_id: str) -> Optional[ExecutionState]:
        with self._lock:
            state = self._states.get(execution_id)
            return None if state is None else ExecutionState(**state.__dict__)

    def create(self, state: ExecutionState) -> ExecutionState:
        with self._lock:
            if state.execution_id in self._states:
                raise ExecutionConcurrencyError("execution already exists")
            self._states[state.execution_id] = ExecutionState(**state.__dict__)
            return self.get(state.execution_id)

    def compare_and_set(
        self,
        execution_id: str,
        *,
        expected_version: int,
        fencing_token: Optional[int],
        status: str,
        **updates: Any,
    ) -> ExecutionState:
        with self._lock:
            current = self._states.get(execution_id)
            if current is None:
                raise KeyError(execution_id)
            if current.version != expected_version:
                raise ExecutionConcurrencyError("version conflict")
            if fencing_token is not None and current.fencing_token != fencing_token:
                raise ExecutionConcurrencyError("fencing conflict")
            current.status = status
            for key, value in updates.items():
                setattr(current, key, value)
            current.version += 1
            if fencing_token is not None:
                current.fencing_token = fencing_token
            self._states[execution_id] = current
            return ExecutionState(**current.__dict__)
