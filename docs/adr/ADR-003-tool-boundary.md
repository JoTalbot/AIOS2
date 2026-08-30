# ADR-003: Canonical Agent-to-Tool Boundary

## Decision

Agent-originated external tool execution enters through `runtime.tool_gateway.ToolGateway` and then `ToolExecutor` and `ToolSandbox`. `ToolRegistry` is an internal dispatch mechanism, not an authorization boundary.

## Security invariants

1. `ToolExecutionContext.agent_id` is required.
2. Effective permissions are the intersection of context permissions and server-side sandbox authorization.
3. Tool arguments are normalized into a typed `ToolCall` before dispatch.
4. Durable intent and idempotency are established before side effects when an idempotency key is present.
5. Ambiguous outcomes are never automatically replayed.
6. Control-plane API routes do not expose a direct external-tool execution endpoint; operator routes are separately authenticated.
7. Future API tool execution must depend on `ToolGateway`, never call `ToolRegistry.execute()` directly.

## Rationale

The registry knows what a tool requires, but it must not decide who is trusted to invoke the tool. Authorization belongs at the sandbox boundary, while durable execution semantics belong in the executor/intent layer.
