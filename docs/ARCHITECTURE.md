# AIOS vNext Architecture

AIOS2 is a modular operating system architecture for autonomous agents.

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

Intent -> Planner -> Scheduler -> Agent -> Tool Registry -> Permission Boundary -> Tool -> Memory/Persistence -> Reflection

## Runtime orchestration contract

`KernelFactory` assembles the runtime through `KernelContainer` and `KernelRegistry`. The resulting `RuntimeContext` owns lifecycle, persistence, recovery, and restart services.

`Scheduler` owns task state and execution. `SchedulerLoop` owns worker lifecycle and queue draining. This separation keeps scheduling policy independent from process lifetime and makes the runtime testable without a permanent background loop.

## Lifecycle guarantees
1. Startup recovers agent state before normal execution.
2. Scheduler workers are created explicitly and can be stopped deterministically.
3. Queued tasks are drained before scheduler shutdown.
4. Agent snapshots and persistence hooks run during runtime shutdown.
5. Recovery and restart remain owned by the runtime context instead of individual agents.
