from runtime.tool_intent_store import ToolIntent, ToolIntentStore


def test_intent_survives_restart(tmp_path):
    path = tmp_path / "intents.json"
    store = ToolIntentStore(str(path))
    intent = ToolIntent("exec:step:1", "call-1", "send_email", {"to": "x@example.test"}, "exec")
    store.prepare(intent)
    restarted = ToolIntentStore(str(path))
    assert restarted.get(intent.idempotency_key).state == "prepared"


def test_intent_is_idempotent_and_recoverable(tmp_path):
    store = ToolIntentStore(str(tmp_path / "intents.json"))
    intent = ToolIntent("k", "c", "write", {})
    assert store.prepare(intent) == intent
    assert store.prepare(intent) == intent
    claimed = store.claim("k", "owner-a", "token-a")
    assert claimed is not None
    assert claimed.state == "executing"
    assert store.pending()[0].idempotency_key == "k"
    assert store.mark_claimed("k", "owner-a", "token-a", "completed") is not None
    assert store.pending() == []


def test_terminal_transition_requires_authorized_claim(tmp_path):
    store = ToolIntentStore(str(tmp_path / "intents.json"))
    store.prepare(ToolIntent("k", "c", "write", {}))
    assert store.mark("k", "completed") is None
    assert store.get("k").state == "prepared"
    claimed = store.claim("k", "owner-a", "token-a")
    assert claimed is not None
    assert store.mark("k", "completed") is None
    assert store.mark_claimed("k", "owner-a", "wrong-token", "completed") is None
    assert store.get("k").state == "executing"
    assert store.mark_claimed("k", "owner-a", "token-a", "completed") is not None
    assert store.get("k").state == "completed"
