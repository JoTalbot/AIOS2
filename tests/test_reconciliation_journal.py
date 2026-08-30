from runtime.reconciliation_journal import ReconciliationJournal


def test_begin_is_idempotent_and_preserves_terminal_result(tmp_path):
    journal = ReconciliationJournal(str(tmp_path / "journal.json"))
    first = journal.begin("intent-1", "exec-1")
    second = journal.begin("intent-1", "exec-2")
    assert first == second
    completed = journal.complete("intent-1", {"accepted": True})
    repeated = journal.complete("intent-1", {"accepted": False})
    assert repeated == completed
    assert journal.get("intent-1").result == {"accepted": True}


def test_pending_records_survive_reopen(tmp_path):
    path = tmp_path / "journal.json"
    journal = ReconciliationJournal(str(path))
    journal.begin("intent-2", "exec-2")
    reopened = ReconciliationJournal(str(path))
    pending = reopened.pending()
    assert len(pending) == 1
    assert pending[0].intent_key == "intent-2"
    assert pending[0].execution_id == "exec-2"
