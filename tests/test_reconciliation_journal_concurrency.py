from concurrent.futures import ThreadPoolExecutor

from runtime.reconciliation_journal import ReconciliationJournal


def test_concurrent_begin_has_one_durable_identity(tmp_path):
    path = tmp_path / "journal.json"

    def begin(_):
        return ReconciliationJournal(str(path)).begin("intent-1", "exec-1")

    with ThreadPoolExecutor(max_workers=8) as pool:
        records = list(pool.map(begin, range(32)))

    assert {record.intent_key for record in records} == {"intent-1"}
    assert {record.execution_id for record in records} == {"exec-1"}
    assert ReconciliationJournal(str(path)).pending()[0].intent_key == "intent-1"
