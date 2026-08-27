import pytest

from runtime.execution_store import ExecutionState, ExecutionStore, ExecutionStoreCorruptionError


def test_corrupted_store_fails_closed(tmp_path):
    path = tmp_path / "executions.json"
    path.write_text("{not-json", encoding="utf-8")
    store = ExecutionStore(str(path))

    with pytest.raises(ExecutionStoreCorruptionError, match="invalid JSON"):
        store.get("e1")


def test_non_object_store_fails_closed(tmp_path):
    path = tmp_path / "executions.json"
    path.write_text("[]", encoding="utf-8")
    store = ExecutionStore(str(path))

    with pytest.raises(ExecutionStoreCorruptionError, match="root must be an object"):
        store.resumable()


def test_empty_execution_id_is_rejected(tmp_path):
    store = ExecutionStore(str(tmp_path / "executions.json"))
    with pytest.raises(ValueError, match="execution_id"):
        store.save(ExecutionState(""))
