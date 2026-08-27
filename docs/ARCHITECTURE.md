# AIOS vNext Architecture

AIOS is a modular operating system architecture for autonomous agents.

## Core layers

- Kernel: scheduling, context, memory, lifecycle
- Agents: planning and execution processes
- Cognition: reflection and learning loops
- Communication: agent message bus
- Security: sandbox and permissions
- Tools: controlled external actions
- LLM: provider abstraction
- Runtime: boot and orchestration

## Execution flow

Intent -> Planner -> Execution/Orchestration -> Agent -> Tools -> Memory/State -> Reflection -> Result

## Runtime orchestration contract

The runtime owns lifecycle, persistence, recovery, restart and execution identity. Orchestration coordinates autonomous work without creating a second independent execution state world.

Execution lifecycle mutations converge on the canonical `ExecutionCommitCoordinator`. Persistence, journal/recovery and audit are adapters behind that boundary. Ownership is enforced through leases and fencing generations.

## Lifecycle guarantees

1. Startup recovers durable execution state before normal autonomous execution.
2. Execution lifecycle transitions are validated by the state machine.
3. Durable lifecycle mutations use the canonical commit path.
4. Journaled mutations are recoverable and idempotent.
5. Audit follows canonical committed transitions.
6. A stale lease/fencing generation cannot mutate an execution.
7. Recovery and restart remain owned by the runtime rather than individual agents.

## Historical relationship

This is the continuation of the architecture described in the original AIOS documentation. AIOS2 isolates the new architecture so legacy/product-specific implementation does not determine the new runtime design.
