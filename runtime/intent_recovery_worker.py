"""Lease- and claim-fenced reconciliation worker for ambiguous tool intents."""
from dataclasses import dataclass
from typing import Callable, Optional
from uuid import uuid4

from .execution_lease import ExecutionLeaseStore
from .tool_intent_store import ToolIntentStore


@dataclass(frozen=True)
class IntentRecoveryResult:
    key: str
    status: str
    reason: Optional[str] = None


class IntentRecoveryWorker:
    def __init__(self, store: ToolIntentStore, lease_store: ExecutionLeaseStore,
                 owner_id: str = "tool-intent-recovery"):
        self.store = store
        self.lease_store = lease_store
        self.owner_id = owner_id

    def recover_one(self, intent, resolver: Callable):
        lease = self.lease_store.acquire(intent.idempotency_key, self.owner_id)
        if lease is None:
            return IntentRecoveryResult(intent.idempotency_key, "skipped_by_lease")
        claim_token = uuid4().hex
        claimed = self.store.claim(intent.idempotency_key, self.owner_id, claim_token)
        if claimed is None:
            self.lease_store.release(intent.idempotency_key, self.owner_id, lease.fencing_token)
            return IntentRecoveryResult(intent.idempotency_key, "skipped_by_claim")
        try:
            if not self.lease_store.is_owner(intent.idempotency_key, self.owner_id, lease.fencing_token):
                return IntentRecoveryResult(intent.idempotency_key, "skipped_by_lease")
            status, _ = resolver(claimed)
            if status in {"completed", "failed"}:
                committed = self.store.mark_claimed(
                    intent.idempotency_key, self.owner_id, claim_token, status
                )
                if committed is None:
                    return IntentRecoveryResult(intent.idempotency_key, "skipped_by_claim")
                return IntentRecoveryResult(intent.idempotency_key, status)
            self.store.release_claim(intent.idempotency_key, self.owner_id, claim_token)
            return IntentRecoveryResult(intent.idempotency_key, "ambiguous", "resolver returned unknown state")
        finally:
            self.lease_store.release(intent.idempotency_key, self.owner_id, lease.fencing_token)

    def recover_all(self, resolver: Callable):
        return [self.recover_one(intent, resolver) for intent in self.store.pending()]
