import threading

from runtime.tool_intent_store import ToolIntent, ToolIntentStore


def test_only_one_worker_can_claim(tmp_path):
    store = ToolIntentStore(str(tmp_path / "intents.json"))
    store.prepare(ToolIntent("k", "call", "write", {}))
    results = []
    def claim(owner):
        results.append(store.claim("k", owner, owner + "-token"))
    threads = [threading.Thread(target=claim, args=(f"worker-{i}",)) for i in range(8)]
    for t in threads: t.start()
    for t in threads: t.join()
    assert sum(r is not None for r in results) == 1
