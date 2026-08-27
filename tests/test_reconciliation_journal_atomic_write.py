import json

import pytest

from runtime.reconciliation_journal import ReconciliationJournal


def test_failed_replace_preserves_previous_durable_state(tmp_path, monkeypatch):
    path = tmp_path / "journal.json"
    journal = ReconciliationJournal(str(path))
    journal.begin("intent-1", "exec-1")
    before = path.read_text(encoding="utf-8")

    def fail_replace(src, dst):
        raise OSError("simulated crash during replace")

    monkeypatch.setattr("runtime.reconciliation_journal.Path.replace", fail_replace)
    with pytest.raises(OSError):
        journal.complete("intent-1", {"ok": True})

    assert path.read_text(encoding="utf-8") == before
    assert json.loads(before)["intent-1"]["status"] == "pending"


def test_atomic_write_leaves_no_tmp_after_success(tmp_path):
    path = tmp_path / "journal.json"
    journal = ReconciliationJournal(str(path))
    journal.begin("intent-1", "exec-1")
    journal.complete("intent-1", {"ok": True})

    assert path.exists()
    assert not path.with_suffix(path.suffix + ".tmp").exists()
