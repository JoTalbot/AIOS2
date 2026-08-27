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
    def __init__(self, registry, audit=None, authorization=None):
        self.registry=registry; self.audit=audit or ExecutionAudit(); self.authorization={str(a):frozenset(p) for a,p in (authorization or {}).items()}
    def allowed_permissions(self, agent_id): return self.authorization.get(str(agent_id), frozenset())
    async def execute(self, tool_name, context, **kwargs):
        if not context.agent_id: raise PermissionError("agent identity is required")
        allowed = context.permissions if not self.authorization else self.allowed_permissions(context.agent_id)
        granted = context.permissions & allowed
        self.audit.record("tool.execution.started", context.agent_id, getattr(tool_name,"tool",tool_name))
        try:
            result=await self.registry.execute(tool_name, granted_permissions=granted, **kwargs)
            self.audit.record("tool.execution.completed", context.agent_id, getattr(tool_name,"tool",tool_name)); return result
        except Exception as exc:
            self.audit.record("tool.execution.failed", context.agent_id, getattr(tool_name,"tool",tool_name), "error", error=str(exc)); raise
