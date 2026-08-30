"""Crash-safe execution boundary for side-effecting tool calls.

The boundary makes the ordering explicit: durable result first, then a fenced
terminal intent transition. A stale/expired claimant cannot finalize the intent.
"""
from dataclasses import dataclass
from typing import Any

from .tool_idempotency_store import StoredToolResult, ToolIdempotencyStore
from .tool_intent_store import ToolIntentStore


@dataclass(frozen=True)
class BoundaryCommit:
    ok: bool
    value: Any = None
    error: str | None = None
    committed: bool = False


class ExecutionBoundary:
    def __init__(self, intents: ToolIntentStore, results: ToolIdempotencyStore):
        self.intents = intents
        self.results = results

    def commit(self, *, key: str, call_id: str, tool: str, owner_id: str,
               claim_token: str, ok: bool, value: Any = None,
               error: str | None = None) -> BoundaryCommit:
        """Persist the outcome, then terminally commit the matching claim.

        If the claim has expired or was fenced by another worker, the durable
        result remains authoritative and this caller reports ``committed=False``.
        """
        stored = self.results.put_if_absent(
            StoredToolResult(key, call_id, tool, ok, value if ok else None, error)
        )
        terminal = "completed" if stored.ok else "failed"
        intent = self.intents.mark_claimed(key, owner_id, claim_token, terminal)
        return BoundaryCommit(stored.ok, stored.value, stored.error, intent is not None)
