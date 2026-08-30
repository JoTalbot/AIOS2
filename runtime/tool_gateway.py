"""Canonical Agent-to-Tool gateway.

Runtime callers should enter the external-tool boundary through this object,
never through ToolRegistry directly. The gateway keeps policy, execution
context, and durable execution semantics in one place.
"""

from .execution_context import ExecutionContext
from .tool_protocol import ToolCall, ToolResult
from .tool_sandbox import ToolExecutionContext, ToolSandbox
from .tool_executor import ToolExecutor


class ToolGateway:
    """Single supported entry point for agent-originated tool execution."""

    def __init__(self, executor: ToolExecutor):
        self.executor = executor

    async def execute(
        self,
        call: ToolCall,
        context: ToolExecutionContext,
        execution_context: ExecutionContext | None = None,
    ) -> ToolResult:
        return await self.executor.execute(
            call,
            context,
            execution_context=execution_context,
        )
