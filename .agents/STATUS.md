# AIOS New Architecture — Shared Agent Status

## Current phase
- Phase: canonical execution consolidation
- Branch: `canonical-execution`
- Source architecture line: `main` (new vNext architecture)

## Active agents

| Agent | Task | Branch | Status |
|---|---|---|---|
| current | canonical execution/recovery/persistence consolidation | `canonical-execution` | in progress |

## Completed
- Established dedicated new-architecture repository line.
- Mapped execution lifecycle, persistence, journal, audit, lease and recovery boundaries.
- Added the canonical execution invariants contract in `docs/EXECUTION_INVARIANTS.md`.
- Routed autonomous-loop lifecycle checkpoints through `ExecutionCommitCoordinator`.
- Routed recovery failure mutations through the same coordinator.
- Shared one coordinator through `RuntimeOrchestrator` and `RuntimeFactory`.
- Added process-level file locking to the file-backed lease adapter.
- Hardened journal sequence allocation across quarantined/corrupt records.
- Added regression tests for canonical audit, reconciliation idempotency, journal integrity and lease ownership.
- Enforced that persistent `AutonomousExecutionLoop` instances receive an explicit checkpoint/commit boundary.
- Exposed canonical `execution_id` on `LoopResult` for control-plane correlation.
- Replaced the duplicate scheduler-based `VNextOrchestrator` execution world with a facade over `RuntimeOrchestrator`.
- Updated loop transition coverage to construct the canonical persistence path explicitly.

## Current architecture work
- One durable execution authority: `RuntimeOrchestrator` → `AutonomousExecutionLoop`.
- One lifecycle mutation authority: `ExecutionCommitCoordinator` → Journal / Store / Audit.
- vNext orchestration is a facade over the canonical runtime; it no longer creates a second scheduler execution world.
- Agent → Tool Registry → Permission Boundary → Tool Executor.
- Recovery: Bootstrap → Policy / Queue → Lease → Resume.
- Persistence adapters remain replaceable behind runtime boundaries.

## Next actions
1. Run the complete test suite and targeted recovery/concurrency tests in CI.
2. Audit all remaining direct lifecycle mutations (`ExecutionStore.save/transition`) and classify setup-only persistence versus runtime mutation.
3. Add crash-window tests for journal/store/audit ordering.
4. Add integration tests for stale lease ownership and recovery takeover.
5. Evaluate a distributed persistence/lease adapter for multi-machine production use.
6. Record architectural decisions and handoffs here or in docs/ADR.

## Rules
Every agent updates this file before and after significant work. GitHub is the source of truth; do not rely on local chat history.
