"""Fail-closed, policy-aware execution boundary for AIOS tools."""

from dataclasses import dataclass
from typing import Any

from .execution_audit import ExecutionAudit
from .tool_protocol import ToolCall
from .tool_registry import ToolRegistry


class ToolBoundaryError(PermissionError):
    """Raised when a tool call cannot cross the sandbox boundary safely."""


@dataclass(frozen=True)
class ToolExecutionContext:
    agent_id: str
    permissions: frozenset[str] = frozenset()


class ToolSandbox:
    def __init__(self, registry=None, audit=None, authorization=None):
        self.registry = registry or ToolRegistry()
        self.audit = audit or ExecutionAudit()
        self.authorization = {
            str(agent): frozenset(str(permission).strip() for permission in permissions if str(permission).strip())
            for agent, permissions in (authorization or {}).items()
        }

    def allowed_permissions(self, agent_id):
        return self.authorization.get(str(agent_id), frozenset())

    @staticmethod
    def _normalize_call(tool_name: Any, kwargs: dict[str, Any]) -> ToolCall:
        if isinstance(tool_name, ToolCall):
            if kwargs:
                raise ToolBoundaryError("ToolCall arguments cannot be overridden at the sandbox boundary")
            call = tool_name
        else:
            if not isinstance(tool_name, str) or not tool_name.strip():
                raise ToolBoundaryError("tool name is required")
            call = ToolCall(tool=tool_name.strip(), arguments=dict(kwargs))

        if not isinstance(call.arguments, dict):
            raise ToolBoundaryError("tool arguments must be a mapping")
        if call.timeout is not None and (not isinstance(call.timeout, (int, float)) or call.timeout <= 0):
            raise ToolBoundaryError("tool timeout must be positive")
        return call

    async def execute(self, tool_name, context, *, execution_context=None, **kwargs):
        if not isinstance(context, ToolExecutionContext) or not context.agent_id:
            raise ToolBoundaryError("trusted agent identity is required")

        call = self._normalize_call(tool_name, kwargs)
        # Context permissions are untrusted caller claims. Only the sandbox's
        # server-side authorization map can grant privileged capabilities.
        granted = context.permissions & self.allowed_permissions(context.agent_id)
        self.audit.record("tool.execution.started", context.agent_id, call.tool)
        try:
            result = await self.registry.execute(call, granted_permissions=granted)
            self.audit.record("tool.execution.completed", context.agent_id, call.tool)
            return result
        except Exception as exc:
            self.audit.record(
                "tool.execution.failed",
                context.agent_id,
                call.tool,
                "error",
                error=str(exc),
            )
            raise
