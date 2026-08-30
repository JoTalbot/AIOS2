from runtime.reconciliation_journal import ReconciliationJournal


def test_replay_of_completed_intent_is_idempotent(tmp_path):
    path = tmp_path / "journal.json"
    journal = ReconciliationJournal(str(path))
    first = journal.begin("intent-1", "exec-1")
    completed = journal.complete("intent-1", {"value": 42})

    replay = ReconciliationJournal(str(path))
    assert replay.begin("intent-1", "exec-replay") == completed
    assert replay.complete("intent-1", {"value": 99}) == completed
    assert replay.get("intent-1") == completed
    assert first.execution_id == "exec-1"


def test_replay_of_failed_intent_does_not_reopen_it(tmp_path):
    path = tmp_path / "journal.json"
    journal = ReconciliationJournal(str(path))
    journal.begin("intent-1", "exec-1")
    failed = journal.fail("intent-1", {"error": "boom"})

    replay = ReconciliationJournal(str(path))
    assert replay.begin("intent-1", "exec-replay") == failed
    assert replay.fail("intent-1", {"error": "different"}) == failed
    assert replay.get("intent-1") == failed
