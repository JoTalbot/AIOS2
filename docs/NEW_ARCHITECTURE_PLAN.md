# AIOS New Architecture — Development Plan

This plan reconstructs and preserves the development line used in `JoTalbot/AIOS:new`. It is the working plan for the isolated AIOS2 architecture.

## Mission

Preserve the original AIOS goal — a general-purpose AI Operating System for autonomous agents — while rebuilding the execution foundation so autonomous work is durable, recoverable, secure, auditable and suitable for long-running multi-agent operation.

## Phase 0 — Repository and agent continuity

- Isolate the new architecture on its own branch/repository line.
- Make GitHub the source of truth for code, documentation and handoff state.
- Establish `AGENTS.md`, shared status, protocol, roles and reusable skills.
- Require research, validation, regression coverage, commit and durable handoff for every substantial change.

## Phase 1 — Canonical execution model

Build the durable execution foundation:

1. `ExecutionContext` — canonical execution identity and state payload.
2. `ExecutionStateMachine` — valid lifecycle transitions.
3. `ExecutionStore` — durable execution persistence.
4. `ExecutionAudit` — auditable lifecycle history.
5. `ExecutionCommitCoordinator` — single lifecycle mutation/commit boundary.
6. Journal and integrity/checksum semantics.
7. Idempotent reconciliation after interruption.

Invariant: execution, persistence and recovery must not split into parallel state paths.

## Phase 2 — Agent/tool execution boundary

Build the controlled execution path:

`Planner → Agent Executor → Tool Protocol → Tool Registry → Permission Boundary → Tool Executor → Sandbox`

Tools are explicit capabilities rather than arbitrary access to the process environment. Public contracts receive regression coverage.

## Phase 3 — Autonomous orchestration

Introduce bounded autonomous execution on top of the canonical execution model:

- planning;
- scheduling/orchestration;
- agent execution;
- tool execution;
- replanning;
- reflection;
- result propagation.

Do not create a second durable execution world. Orchestration must converge on the canonical runtime execution identity.

## Phase 4 — Checkpoint and recovery

Implement:

- recovery checkpoints;
- recovery policy;
- recovery queue;
- startup reconciliation;
- resumable execution discovery;
- deterministic resume;
- recovery failure handling.

All lifecycle mutations during recovery use the same canonical commit boundary as normal execution.

## Phase 5 — Ownership and concurrency

Implement execution ownership:

- leases;
- renewal/heartbeat;
- expiry and takeover;
- fencing generations/tokens;
- stale-worker rejection;
- concurrency tests.

A worker is authoritative only while its lease and fencing generation are valid.

## Phase 6 — Runtime composition

Unify the lifecycle under the runtime:

`RuntimeOrchestrator → VNext orchestration facade → AutonomousExecutionLoop → Agent/Tool execution`

Runtime owns startup, persistence, recovery, restart and shutdown. There must not be an independent scheduler/execution state universe beside the canonical runtime.

## Phase 7 — Verification

For every invariant, maintain the progression:

`implementation → unit test → integration test → crash test → concurrency test`

Required verification classes include:

- state-machine correctness;
- commit idempotency;
- journal integrity and monotonic sequence;
- crash-window reconciliation;
- audit idempotency;
- lease takeover;
- stale fencing rejection;
- fresh-runtime recovery;
- API-to-execution end-to-end flow;
- tool permission/sandbox boundaries.

## Phase 8 — Production persistence boundary

Keep runtime independent of storage implementation. Replace file-backed adapters with production distributed implementations when required:

- transactional/conditional execution repository;
- durable atomic journal;
- distributed lease with compare-and-set and fencing tokens.

The orchestration and agent contracts should remain stable when persistence adapters change.

## Definition of architectural completion

The new architecture is complete when one durable execution identity can move from intent through planning, agent/tool execution, memory/reflection and result; every lifecycle transition is validated, journaled, audited and recoverable; ownership prevents stale workers; and restart can deterministically resume work without creating a second execution state.
