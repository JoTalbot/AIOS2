"""Bounded, fenced recovery worker for ambiguous tool intents."""
from dataclasses import dataclass
import asyncio
import uuid
from typing import Any, Callable, Optional
from .tool_intent_store import ToolIntent, ToolIntentStore

@dataclass(frozen=True)
class IntentRecoveryResult:
    idempotency_key: str
    status: str
    attempts: int = 0

class ToolIntentRecoveryWorker:
    """Reconcile durable ambiguous intents without replaying side effects."""
    def __init__(self, store: ToolIntentStore, lease_store=None, owner_id: Optional[str] = None, max_attempts: int = 3, backoff_seconds: float = 0.0):
        if (lease_store is None) != (owner_id is None): raise ValueError("lease_store and owner_id must be provided together")
        if max_attempts < 1: raise ValueError("max_attempts must be >= 1")
        self.store, self.lease_store, self.owner_id = store, lease_store, owner_id
        self.max_attempts, self.backoff_seconds = max_attempts, max(0.0, backoff_seconds)

    async def recover(self, executor, resolver: Callable[[ToolIntent], Any], *, limit: Optional[int] = None):
        intents = self.store.pending()
        if limit is not None: intents = intents[:max(0, limit)]
        return [await self._recover_one(executor, resolver, intent) for intent in intents]

    async def _recover_one(self, executor, resolver, intent):
        lease = None
        if self.lease_store is not None:
            lease = self.lease_store.acquire(intent.idempotency_key, self.owner_id)
            if lease is None: return IntentRecoveryResult(intent.idempotency_key, "skipped_by_lease")
        claim_token = uuid.uuid4().hex
        claimed = self.store.claim(intent.idempotency_key, self.owner_id or "local-recovery", claim_token)
        if claimed is None:
            if lease is not None: self.lease_store.release(intent.idempotency_key, self.owner_id, lease.fencing_token)
            return IntentRecoveryResult(intent.idempotency_key, "skipped_by_claim")
        attempts = 0
        try:
            while attempts < self.max_attempts:
                attempts += 1
                if lease is not None and not self.lease_store.is_owner(intent.idempotency_key, self.owner_id, lease.fencing_token):
                    return IntentRecoveryResult(intent.idempotency_key, "skipped_by_lease", attempts)
                try: result = await executor.reconcile_intent(claimed, resolver)
                except Exception: result = None
                if result is not None:
                    state = "completed" if result.ok else "failed"
                    if self.store.mark_claimed(intent.idempotency_key, self.owner_id or "local-recovery", claim_token, state) is None:
                        return IntentRecoveryResult(intent.idempotency_key, "stale_claim", attempts)
                    return IntentRecoveryResult(intent.idempotency_key, "recovered" if result.ok else "failed", attempts)
                if attempts < self.max_attempts and self.backoff_seconds: await asyncio.sleep(self.backoff_seconds * (2 ** (attempts - 1)))
            self.store.release_claim(intent.idempotency_key, self.owner_id or "local-recovery", claim_token, "ambiguous")
            return IntentRecoveryResult(intent.idempotency_key, "quarantined", attempts)
        finally:
            if lease is not None: self.lease_store.release(intent.idempotency_key, self.owner_id, lease.fencing_token)
