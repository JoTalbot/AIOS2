import pytest

from runtime.execution_store import ExecutionState, ExecutionStore
from runtime.execution_audit import ExecutionAuditLog
from runtime.execution_commit import ExecutionCommitCoordinator
from runtime.recovery_manager import RecoveryManager


class Loop:
    def __init__(self):
        self.calls = []

    async def run(self, goal, agent, context=None, execution_context=None):
        self.calls.append((goal, agent))
        return "resumed"


def coordinator_for(store):
    return ExecutionCommitCoordinator(store, ExecutionAuditLog())


@pytest.mark.asyncio
async def test_recovery_manager_resumes_pending_executions(tmp_path):
    store = ExecutionStore(str(tmp_path / "executions.json"))
    store.save(ExecutionState("e1", status="running", goal="finish task"))
    store.save(ExecutionState("e2", status="completed", goal="already done"))

    loop = Loop()
    results = await RecoveryManager(store, coordinator_for(store)).recover(loop, "agent-1")

    assert results == [("e1", "resumed")]
    assert loop.calls == [("finish task", "agent-1")]


def test_recovery_manager_marks_failed_execution(tmp_path):
    store = ExecutionStore(str(tmp_path / "executions.json"))
    state = store.save(ExecutionState("e1", status="running"))
    updated = RecoveryManager(store, coordinator_for(store)).mark_failed(state, RuntimeError("crash"))
    assert updated.status == "failed"
    assert updated.error == "crash"
