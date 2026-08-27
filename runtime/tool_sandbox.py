"""Policy-aware execution boundary for AIOS tools."""

from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from .execution_audit import ExecutionAudit
from .tool_registry import ToolRegistry


@dataclass(frozen=True)
class ToolExecutionContext:
    agent_id: str
    permissions: frozenset[str] = frozenset()


class ToolSandbox:
    def __init__(self, registry: ToolRegistry, audit: ExecutionAudit | None = None, authorization: Mapping[str, Iterable[str]] | None = None):
        self.registry = registry
        self.audit = audit or ExecutionAudit()
        self.authorization = None if authorization is None else {str(agent): frozenset(permissions) for agent, permissions in authorization.items()}

    def allowed_permissions(self, agent_id: str) -> frozenset[str]:
        if self.authorization is None:
            return frozenset()
        return self.authorization.get(str(agent_id), frozenset())

    async def execute(self, tool_name: str, context: ToolExecutionContext, **kwargs) -> Any:
        if not context.agent_id:
            raise PermissionError("agent identity is required")
        # When an explicit authorization policy exists, it is authoritative.
        # Without one, the caller's typed permissions are the execution grant.
        granted = context.permissions if self.authorization is None else context.permissions & self.allowed_permissions(context.agent_id)
        self.audit.record("tool.execution.started", context.agent_id, tool_name)
        try:
            result = await self.registry.execute(tool_name, granted_permissions=granted, **kwargs)
            self.audit.record("tool.execution.completed", context.agent_id, tool_name)
            return result
        except Exception as exc:
            self.audit.record("tool.execution.failed", context.agent_id, tool_name, "error", error=str(exc))
            raise
