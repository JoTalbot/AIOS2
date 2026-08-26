import pytest

from runtime.execution_audit import ExecutionAudit
from runtime.tool_registry import ToolPermissionError, ToolRegistry
from runtime.tool_sandbox import ToolExecutionContext, ToolSandbox


@pytest.mark.asyncio
async def test_audit_records_success_and_failure():
    registry = ToolRegistry()
    registry.register("add", lambda a, b: a + b, permissions={"compute"})
    audit = ExecutionAudit()
    sandbox = ToolSandbox(registry, audit)
    assert await sandbox.execute("add", ToolExecutionContext("agent-1", frozenset({"compute"})), a=1, b=2) == 3
    with pytest.raises(ToolPermissionError):
        await sandbox.execute("add", ToolExecutionContext("agent-1"), a=1, b=2)
    assert [e.event for e in audit.events] == ["tool.execution.started", "tool.execution.completed", "tool.execution.started", "tool.execution.failed"]
