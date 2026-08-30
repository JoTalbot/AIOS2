from concurrent.futures import ThreadPoolExecutor

from runtime.reconciliation_journal import ReconciliationJournal


def test_concurrent_begin_is_idempotent(tmp_path):
    path = tmp_path / "journal.json"

    def begin(execution_id):
        return ReconciliationJournal(str(path)).begin("shared-intent", execution_id)

    with ThreadPoolExecutor(max_workers=8) as pool:
        records = list(pool.map(begin, [f"exec-{i}" for i in range(8)]))

    assert {record.intent_key for record in records} == {"shared-intent"}
    assert len({record.execution_id for record in records}) == 1
    stored = ReconciliationJournal(str(path)).get("shared-intent")
    assert stored is not None
    assert stored.execution_id in {f"exec-{i}" for i in range(8)}


def test_concurrent_terminal_updates_preserve_single_terminal_state(tmp_path):
    path = tmp_path / "journal.json"
    ReconciliationJournal(str(path)).begin("shared-intent", "exec-1")

    def finish(index):
        return ReconciliationJournal(str(path)).complete("shared-intent", {"winner": index})

    with ThreadPoolExecutor(max_workers=8) as pool:
        records = list(pool.map(finish, range(8)))

    stored = ReconciliationJournal(str(path)).get("shared-intent")
    assert stored is not None
    assert stored.status == "completed"
    assert stored.result["winner"] in range(8)
    assert all(record.status == "completed" for record in records)
