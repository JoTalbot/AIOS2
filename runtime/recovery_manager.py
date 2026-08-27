"""Startup recovery for restart-safe AIOS executions."""
from typing import Any, Optional

from .execution_store import ExecutionState, ExecutionStore, ExecutionVersionConflictError, ExecutionFencingConflictError
from .recovery_outcome import RecoveryOutcome


class RecoveryManager:
    """Resume recoverable executions while isolating individual failures."""

    def __init__(self, store: ExecutionStore, lease_store=None, owner_id: Optional[str] = None):
        if (lease_store is None) != (owner_id is None):
            raise ValueError("lease_store and owner_id must be provided together")
        self.store, self.lease_store, self.owner_id = store, lease_store, owner_id

    def pending(self):
        return self.store.resumable()

    async def recover(self, loop, agent: Any, context: Optional[dict] = None, *, continue_on_error: bool = True):
        recovered = []
        for state in self.pending():
            lease = None
            if self.lease_store is not None:
                lease = self.lease_store.acquire(state.execution_id, self.owner_id)
                if lease is None:
                    recovered.append(RecoveryOutcome(state.execution_id, "skipped_by_lease")); continue
            try:
                if lease is not None and not self.lease_store.is_owner(state.execution_id, self.owner_id, lease.fencing_token):
                    recovered.append(RecoveryOutcome(state.execution_id, "skipped_by_lease")); continue
                resume = getattr(loop, "resume", None)
                result = resume(state.execution_id, agent, context=context) if resume is not None else loop.run(state.goal, agent, context=context, execution_context=None)
                if hasattr(result, "__await__"): await result
                if lease is not None and not self.lease_store.is_owner(state.execution_id, self.owner_id, lease.fencing_token):
                    raise ExecutionFencingConflictError(f"execution lease fenced: {state.execution_id}")
            except ExecutionFencingConflictError:
                recovered.append(RecoveryOutcome(state.execution_id, "stale"))
                if not continue_on_error: raise
                continue
            except Exception as exc:
                try: marked = self.mark_failed(state, exc, lease=lease)
                except (ExecutionVersionConflictError, ExecutionFencingConflictError): marked = False
                recovered.append(RecoveryOutcome(state.execution_id, "failed" if marked is not False else "stale"))
                if not continue_on_error: raise
                continue
            finally:
                if lease is not None:
                    try: self.lease_store.release(state.execution_id, self.owner_id, lease.fencing_token)
                    except Exception: pass
            recovered.append(RecoveryOutcome(state.execution_id, "recovered"))
        return recovered

    def mark_failed(self, state: ExecutionState, error: BaseException, *, lease=None):
        fencing_token = None; fencing_validator = None
        if lease is not None:
            if self.lease_store is None or not self.lease_store.is_owner(state.execution_id, self.owner_id, lease.fencing_token): return False
            fencing_token = lease.fencing_token
            fencing_validator = lambda execution_id, token: self.lease_store.is_owner(execution_id, self.owner_id, token)
        state.status, state.error = "failed", str(error)
        return self.store.compare_and_set(state, state.version, fencing_token=fencing_token, fencing_validator=fencing_validator)
