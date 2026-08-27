"""Policy-aware tool registry for AIOS vNext."""

from dataclasses import dataclass
from typing import Any, Callable, Dict, FrozenSet, Iterable, Optional


@dataclass(frozen=True)
class ToolSpec:
    name: str
    handler: Callable[..., Any]
    permissions: FrozenSet[str] = frozenset()


class ToolPermissionError(PermissionError):
    """Raised when a caller lacks a tool's required permissions."""


class ToolRegistry:
    """Register and invoke tools through an explicit permission boundary."""

    def __init__(self):
        self._tools: Dict[str, ToolSpec] = {}

    def register(
        self,
        name: str,
        handler: Callable[..., Any],
        permissions: Optional[Iterable[str]] = None,
    ) -> ToolSpec:
        if not isinstance(name, str) or not name.strip() or not callable(handler):
            raise ValueError("tool name and callable handler are required")
        normalized_name = name.strip()
        required = frozenset(str(permission).strip() for permission in (permissions or ()) if str(permission).strip())
        spec = ToolSpec(normalized_name, handler, required)
        self._tools[normalized_name] = spec
        return spec

    def unregister(self, name: str) -> ToolSpec:
        """Remove and return a registered tool."""
        try:
            return self._tools.pop(name)
        except KeyError as exc:
            raise KeyError(f"unknown tool: {name}") from exc

    def get(self, name: str) -> ToolSpec:
        try:
            return self._tools[name]
        except KeyError as exc:
            raise KeyError(f"unknown tool: {name}") from exc

    async def execute(
        self,
        name: str,
        *,
        granted_permissions: Optional[Iterable[str]] = None,
        **kwargs,
    ):
        spec = self.get(name)
        granted = frozenset(str(permission).strip() for permission in (granted_permissions or ()) if str(permission).strip())
        missing = spec.permissions - granted
        if missing:
            raise ToolPermissionError(f"tool '{name}' requires permissions: {sorted(missing)}")
        result = spec.handler(**kwargs)
        if hasattr(result, "__await__"):
            return await result
        return result

    def names(self):
        return tuple(sorted(self._tools))
