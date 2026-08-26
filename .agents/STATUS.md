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

## Current architecture work
- vNext orchestration/execution path.
- Agent → Tool Registry → Permission Boundary → Tool Executor.
- Canonical lifecycle mutation: `ExecutionCommitCoordinator` → Journal / Store / Audit.
- Recovery: Bootstrap → Policy / Queue → Lease → Resume.
- Persistence adapters remain replaceable behind runtime boundaries.

## Next actions
1. Run the complete test suite and targeted recovery/concurrency tests.
2. Audit all remaining direct lifecycle mutations (`ExecutionStore.save/transition`) outside repository/bootstrap setup.
3. Consolidate `RuntimeOrchestrator` and `VNextOrchestrator` ownership so there is one execution authority.
4. Add crash-window tests for journal/store/audit ordering.
5. Evaluate a distributed persistence/lease adapter for multi-machine production use.
6. Record architectural decisions and handoffs here or in docs/ADR.

## Rules
Every agent updates this file before and after significant work. GitHub is the source of truth; do not rely on local chat history.
