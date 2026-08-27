import pytest

from runtime.tool_registry import ToolPermissionError, ToolRegistry


@pytest.mark.asyncio
async def test_registry_normalizes_permissions_and_returns_spec():
    registry = ToolRegistry()

    async def handler(value):
        return value

    spec = registry.register("  echo  ", handler, [" read ", "", "read"])

    assert spec.name == "echo"
    assert spec.permissions == frozenset({"read"})
    assert await registry.execute("echo", granted_permissions=["read"], value="ok") == "ok"


@pytest.mark.asyncio
async def test_registry_enforces_permissions_before_handler():
    called = False

    def handler():
        nonlocal called
        called = True
        return "ok"

    registry = ToolRegistry()
    registry.register("secure", handler, ["write"])

    with pytest.raises(ToolPermissionError):
        await registry.execute("secure", granted_permissions=["read"])
    assert called is False


def test_registry_spec_permissions_are_immutable():
    registry = ToolRegistry()
    spec = registry.register("tool", lambda: None, ["read"])
    with pytest.raises(AttributeError):
        spec.permissions.add("write")


def test_registry_unregisters_tools():
    registry = ToolRegistry()
    registry.register("tool", lambda: None)
    removed = registry.unregister("tool")
    assert removed.name == "tool"
    assert registry.names() == ()
    with pytest.raises(KeyError, match="unknown tool"):
        registry.unregister("tool")
