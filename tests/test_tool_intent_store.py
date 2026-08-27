import pytest
from runtime.tool_intent_store import ToolIntent, ToolIntentStore

def test_intent_survives_restart(tmp_path):
    path=tmp_path/"intents.json"; store=ToolIntentStore(str(path)); intent=ToolIntent("exec:step:1","call-1","send_email",{"to":"x@example.test"},"exec")
    store.prepare(intent); restarted=ToolIntentStore(str(path)); assert restarted.get(intent.idempotency_key).state=="prepared"

def test_intent_is_idempotent_and_recoverable(tmp_path):
    store=ToolIntentStore(str(tmp_path/"intents.json")); intent=ToolIntent("k","c","write",{})
    assert store.prepare(intent)==intent; assert store.prepare(intent)==intent
    claimed=store.claim("k","worker-a","token-a"); assert claimed is not None
    assert store.pending()[0].idempotency_key=="k"
    assert store.mark_claimed("k","worker-a","token-a","completed") is not None
    assert store.pending()==[]

def test_direct_terminal_mark_is_rejected(tmp_path):
    store=ToolIntentStore(str(tmp_path/"intents.json")); store.prepare(ToolIntent("k","c","write",{}))
    with pytest.raises(ValueError): store.mark("k","completed")

def test_stale_claim_cannot_mark_after_takeover(tmp_path):
    store=ToolIntentStore(str(tmp_path/"intents.json"),claim_ttl_seconds=1); store.prepare(ToolIntent("k","c","write",{}))
    first=store.claim("k","worker-a","epoch-1"); assert first is not None
    data=store._read(); data["k"]["claim_expires_at"]="2000-01-01T00:00:00+00:00"; store._write(data)
    second=store.claim("k","worker-b","epoch-2"); assert second is not None
    assert store.mark_claimed("k","worker-a","epoch-1","completed") is None
    assert store.get("k").owner_id=="worker-b"
