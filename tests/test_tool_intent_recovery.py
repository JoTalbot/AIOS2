import pytest
from runtime.execution_lease import ExecutionLeaseStore
from runtime.tool_executor import ToolExecutor
from runtime.tool_intent_recovery import ToolIntentRecoveryWorker
from runtime.tool_intent_store import ToolIntent, ToolIntentStore
class Resolver:
    def __init__(self): self.calls=0
    async def __call__(self,intent): self.calls+=1; return None
@pytest.mark.asyncio
async def test_recovery_is_bounded_and_does_not_replay_side_effect(tmp_path):
    store=ToolIntentStore(str(tmp_path/"intents.json")); intent=ToolIntent("e1:step1","c1","charge",{"amount":10},"e1","ambiguous"); store.prepare(intent); resolver=Resolver(); worker=ToolIntentRecoveryWorker(store,max_attempts=3); executor=ToolExecutor(object(),intent_store=store)
    result=await worker.recover(executor,resolver); assert result[0].status=="quarantined"; assert result[0].attempts==3; assert resolver.calls==3; assert store.get(intent.idempotency_key).state=="ambiguous"
@pytest.mark.asyncio
async def test_stale_recovery_worker_is_fenced(tmp_path):
    store=ToolIntentStore(str(tmp_path/"intents.json")); leases=ExecutionLeaseStore(str(tmp_path/"leases.json")); intent=ToolIntent("e2:step1","c2","charge",{},"e2","ambiguous"); store.prepare(intent); first=leases.acquire(intent.idempotency_key,"node-a"); leases.release(intent.idempotency_key,"node-a",first.fencing_token); second=leases.acquire(intent.idempotency_key,"node-b"); assert second.fencing_token>first.fencing_token
    worker=ToolIntentRecoveryWorker(store,leases,"node-a"); result=await worker.recover(ToolExecutor(object(),intent_store=store),Resolver()); assert result[0].status=="skipped_by_lease"
@pytest.mark.asyncio
async def test_lease_loss_between_reconcile_and_terminal_mark_is_fenced(tmp_path):
    lock=tmp_path/"coord.lock"; store=ToolIntentStore(str(tmp_path/"intents.json"),coordination_lock_path=str(lock)); leases=ExecutionLeaseStore(str(tmp_path/"leases.json"),coordination_lock_path=str(lock)); intent=ToolIntent("e3:step1","c3","charge",{},"e3","ambiguous"); store.prepare(intent)
    class LosingLeaseStore(ExecutionLeaseStore):
        def __init__(self,*args,**kwargs): super().__init__(*args,**kwargs); self.checks=0
        def is_owner_unlocked(self,execution_id,owner_id,fencing_token=None):
            self.checks+=1
            if self.checks==2:
                current=self._read()[execution_id]; current["owner_id"]="node-b"; current["fencing_token"]=int(current["fencing_token"])+1; self._write(self._read())
                return False
            return True
    losing=LosingLeaseStore(str(tmp_path/"leases2.json"),coordination_lock_path=str(lock)); worker=ToolIntentRecoveryWorker(store,losing,"node-a")
    class Result: ok=True
    class Executor:
        async def reconcile_intent(self,claimed,resolver): return Result()
    result=await worker.recover(Executor(),lambda item: None); assert result[0].status=="skipped_by_lease"; assert store.get(intent.idempotency_key).state=="ambiguous"
