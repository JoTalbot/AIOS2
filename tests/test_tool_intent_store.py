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
    store.mark("k", "executing")
    assert store.pending()[0].idempotency_key == "k"
    store.mark("k", "completed")
    assert store.pending() == []
