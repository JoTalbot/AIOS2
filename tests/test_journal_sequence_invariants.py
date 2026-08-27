import json

import pytest

from runtime.execution_store import ExecutionStore


def _record(sequence, execution_id="e1", state="running"):
    return {
        "sequence": sequence,
        "execution_id": execution_id,
        "state": state,
    }


def test_journal_rejects_duplicate_sequence(tmp_path):
    store = ExecutionStore(str(tmp_path / "executions"))
    store.append_journal(_record(1))
    with pytest.raises((ValueError, RuntimeError)):
        store.append_journal(_record(1))


def test_journal_preserves_monotonic_sequence(tmp_path):
    store = ExecutionStore(str(tmp_path / "executions"))
    store.append_journal(_record(1))
    store.append_journal(_record(2))
    entries = store._read_journal()
    assert [entry["sequence"] for entry in entries] == [1, 2]


def test_journal_corruption_does_not_make_following_valid_record_disappear(tmp_path):
    store = ExecutionStore(str(tmp_path / "executions"))
    store.append_journal(_record(1))
    store.append_journal(_record(2))
    path = store.journal_path
    lines = path.read_text(encoding="utf-8").splitlines()
    lines[1] = "{corrupt"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    entries = store._read_journal()
    assert entries[0]["sequence"] == 1


def test_journal_rejects_non_positive_sequence(tmp_path):
    store = ExecutionStore(str(tmp_path / "executions"))
    with pytest.raises((ValueError, RuntimeError)):
        store.append_journal(_record(0))
