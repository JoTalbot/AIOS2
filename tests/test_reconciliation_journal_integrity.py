import json

import pytest

from runtime.reconciliation_journal import ReconciliationJournal


def test_corrupt_json_fails_closed_without_deleting_evidence(tmp_path):
    path = tmp_path / "journal.json"
    original = '{"broken":'
    path.write_text(original, encoding="utf-8")
    journal = ReconciliationJournal(str(path))

    with pytest.raises(json.JSONDecodeError):
        journal.pending()

    assert path.read_text(encoding="utf-8") == original


def test_malformed_timestamp_is_not_compacted_or_reinterpreted(tmp_path):
    journal = ReconciliationJournal(str(tmp_path / "journal.json"))
    journal._write({"bad": {"status": "completed", "updated_at": "not-a-date"}})

    assert journal.compact() == 0
    with pytest.raises(ValueError, match="invalid journal record"):
        journal.get("bad")
