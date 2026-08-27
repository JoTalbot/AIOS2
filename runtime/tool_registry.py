"""Policy-aware tool registry for AIOS vNext."""
from dataclasses import dataclass
from typing import Any, Callable, Dict, FrozenSet

@dataclass(frozen=True)
class ToolSpec:
    name: str
    handler: Callable[..., Any]
    permissions: FrozenSet[str] = frozenset()

class ToolPermissionError(PermissionError):
    """Raised when a caller lacks a tool's required permissions."""

class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, ToolSpec] = {}

    def register(self, name, handler, permissions=None):
        if not isinstance(name, str) or not name.strip() or not callable(handler):
            raise ValueError("tool name and callable handler are required")
        spec = ToolSpec(
            name.strip(),
            handler,
            frozenset(str(p).strip() for p in (permissions or ()) if str(p).strip()),
        )
        self._tools[spec.name] = spec
        return spec

    def unregister(self, name):
        try:
            return self._tools.pop(name)
        except KeyError as exc:
            raise KeyError(f"unknown tool: {name}") from exc

    def get(self, name):
        name = getattr(name, "tool", name)
        try:
            return self._tools[name]
        except KeyError as exc:
            raise KeyError(f"unknown tool: {name}") from exc

    async def execute(self, name, *, granted_permissions=None, **kwargs):
        """Execute a registered tool, preserving typed ToolCall arguments.

        ToolExecutor passes the normalized tool name today, while some callers
        intentionally pass a ToolCall directly. In the latter case its arguments
        are the invocation kwargs unless explicit kwargs were supplied.
        """
        call_arguments = getattr(name, "arguments", None)
        spec = self.get(name)
        granted = frozenset(
            str(p).strip() for p in (granted_permissions or ()) if str(p).strip()
        )
        missing = spec.permissions - granted
        if missing:
            raise ToolPermissionError(
                f"tool '{spec.name}' requires permissions: {sorted(missing)}"
            )
        if call_arguments is not None:
            merged = dict(call_arguments)
            merged.update(kwargs)
            kwargs = merged
        result = spec.handler(**kwargs)
        return await result if hasattr(result, "__await__") else result

    def names(self):
        return tuple(sorted(self._tools))
