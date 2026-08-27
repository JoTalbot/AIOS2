"""Lease- and claim-fenced reconciliation worker for ambiguous tool intents."""
from dataclasses import dataclass
from typing import Callable, Optional

from .execution_lease import ExecutionLeaseStore
from .tool_intent_store import ToolIntentStore


@dataclass(frozen=True)
class IntentRecoveryResult:
    key: str
    status: str
    reason: Optional[str] = None


class IntentRecoveryWorker:
    """Reconcile ambiguous intents without permitting stale workers to commit."""

    def __init__(
        self,
        store: ToolIntentStore,
        lease_store: ExecutionLeaseStore,
        owner_id: str = "tool-intent-recovery",
    ):
        if not owner_id:
            raise ValueError("owner_id is required")
        self.store = store
        self.lease_store = lease_store
        self.owner_id = owner_id

    def recover_one(self, intent, resolver: Callable):
        key = intent.idempotency_key
        lease = self.lease_store.acquire(key, self.owner_id)
        if lease is None:
            return IntentRecoveryResult(key, "skipped_by_lease")

        claim_token = f"recovery:{self.owner_id}:{lease.fencing_token}"
        claimed = False
        try:
            # Establish both fences before invoking reconciliation. The claim
            # token embeds the lease epoch, so a later worker invalidates this
            # worker's ability to mark the intent after lease expiry.
            if not self.lease_store.is_owner(key, self.owner_id, lease.fencing_token):
                return IntentRecoveryResult(key, "skipped_by_lease")

            claimed_intent = self.store.claim(key, self.owner_id, claim_token)
            if claimed_intent is None:
                current = self.store.get(key)
                if current and current.state in {"completed", "failed"}:
                    return IntentRecoveryResult(key, current.state, "already_terminal")
                return IntentRecoveryResult(key, "skipped_by_claim")
            claimed = True

            status, _ = resolver(claimed_intent)
            if status not in {"completed", "failed"}:
                self.store.release_claim(key, self.owner_id, claim_token, "ambiguous")
                return IntentRecoveryResult(key, "ambiguous", "resolver returned unknown state")

            # Re-check the lease immediately before the durable terminal mark.
            # mark_claimed also checks the claim epoch/expiry, preventing an
            # expired worker from committing a stale result.
            if not self.lease_store.is_owner(key, self.owner_id, lease.fencing_token):
                self.store.release_claim(key, self.owner_id, claim_token, "ambiguous")
                return IntentRecoveryResult(key, "lease_lost", "lease lost before terminal commit")

            marked = self.store.mark_claimed(key, self.owner_id, claim_token, status)
            if marked is None:
                return IntentRecoveryResult(key, "claim_lost", "intent claim lost before terminal commit")
            claimed = False
            return IntentRecoveryResult(key, status)
        finally:
            if claimed:
                self.store.release_claim(key, self.owner_id, claim_token, "ambiguous")
            self.lease_store.release(key, self.owner_id, lease.fencing_token)

    def recover_all(self, resolver: Callable):
        return [self.recover_one(intent, resolver) for intent in self.store.pending()]
