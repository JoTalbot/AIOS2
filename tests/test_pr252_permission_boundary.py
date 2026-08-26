import asyncio

import pytest

from runtime.agent_executor import AgentExecutor
from runtime.tool_executor import ToolExecutor
from runtime.tool_registry import ToolRegistry, ToolPermissionError
from runtime.tool_sandbox import ToolSandbox


def test_agent_executor_cannot_bypass_sandbox_permissions():
    async def scenario():
        registry = ToolRegistry()
        registry.register("protected", lambda: "secret", permissions={"tool:protected"})
        sandbox = ToolSandbox(registry, authorization={"agent-1": set()})
        executor = AgentExecutor(ToolExecutor(sandbox))
        with pytest.raises(ToolPermissionError):
            await executor.execute(
                "agent-1",
                [{"tool": "protected", "arguments": {}}],
                {"permissions": {"tool:protected"}},
            )

    asyncio.run(scenario())
