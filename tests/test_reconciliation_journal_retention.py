from datetime import datetime, timedelta, timezone

from runtime.reconciliation_journal import ReconciliationJournal


def test_compact_removes_only_expired_terminal_records(tmp_path):
    path = tmp_path / "journal.json"
    journal = ReconciliationJournal(str(path))
    journal.begin("old", "exec-old")
    journal.complete("old", {"event_id": "evt-old"})
    journal.begin("pending", "exec-pending")
    journal.begin("fresh", "exec-fresh")
    journal.complete("fresh", {"event_id": "evt-fresh"})

    data = journal._read()
    data["old"]["updated_at"] = (datetime.now(timezone.utc) - timedelta(days=31)).isoformat()
    journal._write(data)

    removed = journal.compact(retention=timedelta(days=30))
    assert removed == 1
    assert journal.get("old") is None
    assert journal.get("pending") is not None
    assert journal.get("fresh") is not None


def test_compact_is_idempotent(tmp_path):
    journal = ReconciliationJournal(str(tmp_path / "journal.json"))
    journal.begin("old", "exec-old")
    journal.complete("old", {"event_id": "evt-old"})
    data = journal._read()
    data["old"]["updated_at"] = (datetime.now(timezone.utc) - timedelta(days=31)).isoformat()
    journal._write(data)

    assert journal.compact(retention=timedelta(days=30)) == 1
    assert journal.compact(retention=timedelta(days=30)) == 0
