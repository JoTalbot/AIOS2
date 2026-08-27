from runtime.execution_lease import ExecutionLeaseStore
from runtime.intent_recovery_worker import IntentRecoveryWorker
from runtime.tool_intent_store import ToolIntent, ToolIntentStore

def test_recovery_resolves_without_replaying_side_effect(tmp_path):
    intents=ToolIntentStore(str(tmp_path/"intents.json")); leases=ExecutionLeaseStore(str(tmp_path/"leases.json")); intent=ToolIntent("k","call","send",{},"e1","ambiguous"); intents.prepare(intent); calls=[]
    def resolver(item): calls.append(item.idempotency_key); return "completed",{"ok":True}
    result=IntentRecoveryWorker(intents,leases,"worker-a").recover_all(resolver)
    assert result[0].status=="completed"; assert calls==["k"]; assert intents.pending()==[]

def test_recovery_does_not_commit_after_lease_loss(tmp_path):
    intents=ToolIntentStore(str(tmp_path/"intents.json")); intent=ToolIntent("k","call","send",{},"e1","ambiguous"); intents.prepare(intent)
    class ExpiringLeaseStore(ExecutionLeaseStore):
        def __init__(self,path): super().__init__(path,ttl_seconds=60); self.checks=0
        def is_owner_unlocked(self,execution_id,owner_id,fencing_token=None): self.checks+=1; return self.checks==1
    expiring=ExpiringLeaseStore(str(tmp_path/"leases.json"))
    result=IntentRecoveryWorker(intents,expiring,"worker-a").recover_one(intent,lambda item:("completed",{"ok":True}))
    assert result.status=="lease_lost"; assert intents.get("k").state=="ambiguous"

def test_stale_worker_cannot_terminal_mark_after_claim_takeover(tmp_path):
    intents=ToolIntentStore(str(tmp_path/"intents.json")); leases=ExecutionLeaseStore(str(tmp_path/"leases.json")); intent=ToolIntent("k","call","send",{},"e1","ambiguous"); intents.prepare(intent)
    first=leases.acquire("k","worker-a"); assert first is not None
    worker_a=IntentRecoveryWorker(intents,leases,"worker-a")
    claimed=intents.claim("k","worker-a",f"recovery:worker-a:{first.fencing_token}"); assert claimed is not None
    data=intents._read(); data["k"]["claim_expires_at"]="2000-01-01T00:00:00+00:00"; intents._write(data)
    leases.release("k","worker-a",first.fencing_token); second=leases.acquire("k","worker-b"); assert second.fencing_token>first.fencing_token
    assert intents.mark_claimed("k","worker-a",f"recovery:worker-a:{first.fencing_token}","completed") is None
    assert intents.get("k").state=="executing"; assert intents.get("k").owner_id=="worker-a"
