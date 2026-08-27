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
    def __init__(self,store:ToolIntentStore,lease_store=None,owner_id:Optional[str]=None,max_attempts:int=3,backoff_seconds:float=0.0,claim_ttl_seconds:Optional[int]=None):
        if (lease_store is None)!=(owner_id is None): raise ValueError("lease_store and owner_id must be provided together")
        if max_attempts<1: raise ValueError("max_attempts must be >= 1")
        self.store,self.lease_store,self.owner_id=store,lease_store,owner_id; self.max_attempts,self.backoff_seconds=max_attempts,max(0.0,backoff_seconds); self.claim_ttl_seconds=claim_ttl_seconds or store.claim_ttl_seconds
        if lease_store is not None:self.store.lock_path=self.lease_store.lock_path
    async def recover(self,executor,resolver:Callable[[ToolIntent],Any],*,limit:Optional[int]=None):
        intents=self.store.pending()
        if limit is not None:intents=intents[:max(0,limit)]
        return [await self._recover_one(executor,resolver,intent) for intent in intents]
    async def _renew_loop(self,key,owner,token,lease):
        interval=max(0.1,self.claim_ttl_seconds/3)
        while True:
            await asyncio.sleep(interval)
            if lease is not None and not self.lease_store.is_owner(key,self.owner_id,lease.fencing_token): return
            if not self.store.renew_claim(key,owner,token): return
    async def _recover_one(self,executor,resolver,intent):
        lease=None; owner=self.owner_id or "local-recovery"
        if self.lease_store is not None:
            lease=self.lease_store.acquire(intent.idempotency_key,self.owner_id)
            if lease is None:return IntentRecoveryResult(intent.idempotency_key,"skipped_by_lease")
        claim_token=f"recovery:{owner}:{lease.fencing_token}" if lease is not None else uuid.uuid4().hex
        if lease is not None:
            with self.lease_store.execution_lock():
                if not self.lease_store.is_owner_unlocked(intent.idempotency_key,self.owner_id,lease.fencing_token):return IntentRecoveryResult(intent.idempotency_key,"skipped_by_lease")
                claimed=self.store._claim_unlocked(intent.idempotency_key,owner,claim_token)
        else: claimed=self.store.claim(intent.idempotency_key,owner,claim_token)
        if claimed is None:
            if lease is not None:self.lease_store.release(intent.idempotency_key,self.owner_id,lease.fencing_token)
            return IntentRecoveryResult(intent.idempotency_key,"skipped_by_claim")
        renewer=asyncio.create_task(self._renew_loop(intent.idempotency_key,owner,claim_token,lease)); attempts=0
        try:
            while attempts<self.max_attempts:
                attempts+=1
                if lease is not None and not self.lease_store.is_owner(intent.idempotency_key,self.owner_id,lease.fencing_token):return IntentRecoveryResult(intent.idempotency_key,"skipped_by_lease",attempts)
                try:result=await executor.reconcile_intent(claimed,resolver)
                except asyncio.CancelledError:raise
                except Exception:result=None
                if result is not None:
                    state="completed" if result.ok else "failed"
                    if lease is not None:
                        with self.lease_store.execution_lock():
                            if not self.lease_store.is_owner_unlocked(intent.idempotency_key,self.owner_id,lease.fencing_token):
                                self.store._release_claim_unlocked(intent.idempotency_key,owner,claim_token,"ambiguous"); return IntentRecoveryResult(intent.idempotency_key,"skipped_by_lease",attempts)
                            marked=self.store._mark_claimed_unlocked(intent.idempotency_key,owner,claim_token,state)
                    else: marked=self.store.mark_claimed(intent.idempotency_key,owner,claim_token,state)
                    if marked is None:return IntentRecoveryResult(intent.idempotency_key,"stale_claim",attempts)
                    return IntentRecoveryResult(intent.idempotency_key,"recovered" if result.ok else "failed",attempts)
                if attempts<self.max_attempts and self.backoff_seconds:await asyncio.sleep(self.backoff_seconds*(2**(attempts-1)))
            self.store.release_claim(intent.idempotency_key,owner,claim_token,"ambiguous"); return IntentRecoveryResult(intent.idempotency_key,"quarantined",attempts)
        finally:
            renewer.cancel()
            try:await renewer
            except asyncio.CancelledError:pass
            if lease is not None:self.lease_store.release(intent.idempotency_key,self.owner_id,lease.fencing_token)
