from runtime.execution_store import ExecutionState, ExecutionStore


def test_file_store_exposes_execution_repository_contract(tmp_path):
    store = ExecutionStore(str(tmp_path / "executions.json"))
    state = store.save(ExecutionState("protocol-test"))
    assert store.get(state.execution_id).execution_id == state.execution_id
    assert hasattr(store, "get")
    assert hasattr(store, "transition")
