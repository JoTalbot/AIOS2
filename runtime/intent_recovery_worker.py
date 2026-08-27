"""Lease- and claim-fenced reconciliation worker for ambiguous tool intents."""
from dataclasses import dataclass
from typing import Callable, Optional
from uuid import uuid4

from .execution_lease import ExecutionLeaseStore
from .reconciliation_journal import ReconciliationJournal
from .tool_intent_store import ToolIntentStore


@dataclass(frozen=True)
class IntentRecoveryResult:
    key: str
    status: str
    reason: Optional[str] = None


class IntentRecoveryWorker:
    def __init__(self, store: ToolIntentStore, lease_store: ExecutionLeaseStore,
                 owner_id: str = "tool-intent-recovery", journal: ReconciliationJournal | None = None):
        self.store = store
        self.lease_store = lease_store
        self.owner_id = owner_id
        self.journal = journal

    def recover_one(self, intent, resolver: Callable):
        lease_key = intent.execution_id or intent.idempotency_key
        lease = self.lease_store.acquire(lease_key, self.owner_id)
        if lease is None:
            return IntentRecoveryResult(intent.idempotency_key, "skipped_by_lease")
        claim_token = uuid4().hex
        claimed = self.store.claim(intent.idempotency_key, self.owner_id, claim_token)
        if claimed is None:
            self.lease_store.release(lease_key, self.owner_id, lease.fencing_token)
            return IntentRecoveryResult(intent.idempotency_key, "skipped_by_claim")
        if self.journal:
            record = self.journal.begin(intent.idempotency_key, intent.execution_id)
            if record.status in {"completed", "failed"}:
                with self.lease_store.execution_lock():
                    if self.lease_store.is_owner_unlocked(lease_key, self.owner_id, lease.fencing_token):
                        self.store.mark_claimed(intent.idempotency_key, self.owner_id, claim_token, record.status)
                return IntentRecoveryResult(intent.idempotency_key, record.status)
        try:
            status, value = resolver(claimed)
            if status not in {"completed", "failed"}:
                if self.journal:
                    self.journal.begin(intent.idempotency_key, intent.execution_id)
                self.store.release_claim(intent.idempotency_key, self.owner_id, claim_token)
                return IntentRecoveryResult(intent.idempotency_key, "ambiguous", "resolver returned unknown state")

            with self.lease_store.execution_lock():
                if not self.lease_store.is_owner_unlocked(lease_key, self.owner_id, lease.fencing_token):
                    self.store.release_claim(intent.idempotency_key, self.owner_id, claim_token)
                    return IntentRecoveryResult(intent.idempotency_key, "skipped_by_lease")
                committed = self.store.mark_claimed(
                    intent.idempotency_key, self.owner_id, claim_token, status
                )
                if committed is None:
                    return IntentRecoveryResult(intent.idempotency_key, "skipped_by_claim")
                if self.journal:
                    if status == "completed": self.journal.complete(intent.idempotency_key, value)
                    else: self.journal.fail(intent.idempotency_key, value)
            return IntentRecoveryResult(intent.idempotency_key, status)
        finally:
            self.lease_store.release(lease_key, self.owner_id, lease.fencing_token)

    def recover_all(self, resolver: Callable):
        return [self.recover_one(intent, resolver) for intent in self.store.pending()]
