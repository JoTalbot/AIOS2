from runtime.reconciliation_journal import ReconciliationJournal


def test_terminal_record_survives_reopen_after_crash_boundary(tmp_path):
    path = tmp_path / "journal.json"
    journal = ReconciliationJournal(str(path))
    journal.begin("intent-1", "exec-1")
    journal.complete("intent-1", {"event_id": "evt-1"})

    reopened = ReconciliationJournal(str(path))
    record = reopened.begin("intent-1", "exec-other")
    assert record.status == "completed"
    assert record.result == {"event_id": "evt-1"}
    assert reopened.pending() == []


def test_terminal_failure_is_immutable_across_recovery_attempts(tmp_path):
    journal = ReconciliationJournal(str(tmp_path / "journal.json"))
    journal.begin("intent-2", "exec-2")
    first = journal.fail("intent-2", {"reason": "remote-rejected"})
    second = journal.complete("intent-2", {"event_id": "should-not-replace"})
    assert second == first
    assert journal.get("intent-2").result == {"reason": "remote-rejected"}
