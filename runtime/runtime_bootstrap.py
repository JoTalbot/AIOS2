"""Startup orchestration for restart-safe AIOS runtime recovery."""
import asyncio
import inspect
from dataclasses import dataclass
from typing import Any, Awaitable, Callable
from .execution_store import ExecutionStore
from .recovery_manager import RecoveryManager
from .recovery_policy import RecoveryAction, RecoveryPolicy
from .recovery_queue import RecoveryQueue, RecoveryQueueItem
from .execution_lease import ExecutionLeaseStore

@dataclass(frozen=True)
class RecoveryReport:
    discovered:int; attempted:int; recovered:int; failed:int; skipped:int=0; reconciled:int=0; reconciliation_failed:int=0; retried:int=0; quarantined:int=0; manual_review:int=0

class RuntimeBootstrap:
    def __init__(self, store=None, recovery_manager=None, lease_store=None, owner_id="aios-runtime", heartbeat_interval=None, commit_coordinator=None, recovery_policy=None, recovery_queue=None):
        self.store=store or ExecutionStore(); self.recovery_manager=recovery_manager or RecoveryManager(self.store); self.lease_store=lease_store or ExecutionLeaseStore(); self.owner_id=owner_id; self.heartbeat_interval=heartbeat_interval if heartbeat_interval is not None else max(0.1,self.lease_store.ttl_seconds/3); self.commit_coordinator=commit_coordinator; self.recovery_policy=recovery_policy or RecoveryPolicy(); self.recovery_queue=recovery_queue or RecoveryQueue()
    async def _heartbeat(self, execution_id, fencing_token=None):
        while True:
            await asyncio.sleep(self.heartbeat_interval)
            renewed = self.lease_store.renew(execution_id, self.owner_id, fencing_token) if fencing_token is not None else self.lease_store.renew(execution_id, self.owner_id)
            if renewed is None: raise RuntimeError(f"execution lease lost: {execution_id}")
            if fencing_token is not None and not self.lease_store.is_owner(execution_id, self.owner_id, fencing_token):
                raise RuntimeError(f"execution lease fenced: {execution_id}")
    def _reconcile(self):
        if self.commit_coordinator is None: return 0,0
        try: return len(self.commit_coordinator.reconcile()),0
        except Exception: return 0,1
    async def recover_pending(self, resume: Callable[[Any], Awaitable[Any]]):
        reconciled,reconciliation_failed=self._reconcile(); pending=self.store.resumable(); recovered=failed=skipped=retried=quarantined=manual_review=0
        for state in pending:
            decision=self.recovery_policy.decide(state.execution_id,state.status,state.attempt)
            if decision.action is RecoveryAction.SKIP: skipped+=1; continue
            if decision.action in {RecoveryAction.QUARANTINE,RecoveryAction.MANUAL_REVIEW}:
                self.recovery_queue.enqueue(RecoveryQueueItem(state.execution_id,decision.action.value,decision.reason,state.attempt,getattr(state,"correlation_id",None))); quarantined += decision.action is RecoveryAction.QUARANTINE; manual_review += decision.action is RecoveryAction.MANUAL_REVIEW; continue
            retried+=1; lease=self.lease_store.acquire(state.execution_id,self.owner_id)
            if lease is None: skipped+=1; continue
            fencing_token=getattr(lease,"fencing_token",None)
            heartbeat=asyncio.create_task(self._heartbeat(state.execution_id,fencing_token)) if fencing_token is not None else None
            try:
                if fencing_token is not None and not self.lease_store.is_owner(state.execution_id,self.owner_id,fencing_token):
                    skipped+=1; continue
                result = resume(state)
                if inspect.isawaitable(result):
                    await result
                recovered+=1
            except Exception as exc: failed+=1; self.recovery_manager.mark_failed(state,exc,lease=lease)
            finally:
                if heartbeat is not None:
                    heartbeat.cancel()
                    try: await heartbeat
                    except asyncio.CancelledError: pass
                if fencing_token is not None: self.lease_store.release(state.execution_id,self.owner_id,fencing_token)
                else: self.lease_store.release(state.execution_id,self.owner_id)
        return RecoveryReport(len(pending),retried,recovered,failed,skipped,reconciled,reconciliation_failed,retried,quarantined,manual_review)
    async def recover_with_loop(self, loop, agent, context=None): return await self.recover_pending(lambda state: loop.resume(state.execution_id,agent,context=context))
