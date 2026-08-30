import pytest

from runtime.reconciliation_journal import ReconciliationJournal, SCHEMA_VERSION


def test_legacy_record_without_version_is_read_compatibly(tmp_path):
    journal = ReconciliationJournal(str(tmp_path / "journal.json"))
    journal._write({
        "legacy": {
            "intent_key": "legacy",
            "execution_id": "exec-1",
            "status": "completed",
            "result": {"ok": True},
            "updated_at": "2026-01-01T00:00:00+00:00",
        }
    })
    record = journal.get("legacy")
    assert record.schema_version == SCHEMA_VERSION
    assert record.result == {"ok": True}


def test_new_records_persist_current_schema_version(tmp_path):
    journal = ReconciliationJournal(str(tmp_path / "journal.json"))
    journal.begin("new", "exec-2")
    assert journal._read()["new"]["schema_version"] == SCHEMA_VERSION


def test_future_schema_version_fails_closed(tmp_path):
    journal = ReconciliationJournal(str(tmp_path / "journal.json"))
    journal._write({
        "future": {
            "intent_key": "future",
            "execution_id": "exec-3",
            "status": "pending",
            "result": None,
            "updated_at": "2026-01-01T00:00:00+00:00",
            "schema_version": SCHEMA_VERSION + 1,
        }
    })
    with pytest.raises(ValueError, match="unsupported journal schema version"):
        journal.get("future")
