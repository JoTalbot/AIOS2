import json

import pytest

from runtime.reconciliation_journal import ReconciliationJournal


def test_corrupt_json_fails_closed_without_deleting_evidence(tmp_path):
    path = tmp_path / "journal.json"
    path.write_text('{"broken":', encoding="utf-8")
    journal = ReconciliationJournal(str(path))
    with pytest.raises(json.JSONDecodeError):
        journal.pending()
    assert path.read_text(encoding="utf-8") == '{"broken":'


def test_malformed_record_is_not_compacted_or_silently_reinterpreted(tmp_path):
    path = tmp_path / "journal.json"
    journal = ReconciliationJournal(str(path))
    journal._write({"bad": {"status": "completed", "updated_at": "not-a-date"}})
    assert journal.compact() == 0
    assert journal.get("bad").status == "completed"
