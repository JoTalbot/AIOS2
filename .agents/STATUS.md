# AIOS New Architecture — Shared Agent Status

## Current phase
- Phase: project-definition and new-architecture plan migration, then canonical execution consolidation
- Branch: `canonical-execution`
- Source architecture line: `JoTalbot/AIOS:new`

## Active agents

| Agent | Task | Branch | Status |
|---|---|---|---|
| current | project definition / plan migration and canonical execution consolidation | `canonical-execution` | in progress |

## Completed
- Established dedicated new-architecture repository line.
- Restored the original AIOS project positioning and purpose in `README.md` and `PROJECT.md`.
- Preserved the original AIOS v1 architecture description in `docs/AIOS_V1.md`.
- Ported the vNext architecture contract to `docs/ARCHITECTURE.md`.
- Preserved the development plan used by `JoTalbot/AIOS:new` in `docs/NEW_ARCHITECTURE_PLAN.md`.
- Aligned `AGENTS.md` with the AIOS2 canonical-execution branch.
- Verified shared agent protocol, status, memory, architect role and reusable skills are present in AIOS2.
- Mapped execution lifecycle, persistence, journal, audit, lease and recovery boundaries.
- Added the canonical execution invariants contract in `docs/EXECUTION_INVARIANTS.md`.
- Routed autonomous-loop lifecycle checkpoints through `ExecutionCommitCoordinator`.
- Routed recovery failure mutations through the same coordinator; direct recovery failure persistence is no longer supported.
- Shared one coordinator through `RuntimeOrchestrator` and `RuntimeFactory`.
- Added process-level file locking to the file-backed lease adapter.
- Hardened journal sequence allocation across quarantined/corrupt records.
- Fixed journal checksum recomputation when commit status changes from `pending` to `applied`/`reconciled`.
- Added regression tests for canonical audit, reconciliation idempotency, journal integrity and lease ownership.
- Enforced that persistent `AutonomousExecutionLoop` instances receive an explicit checkpoint/commit boundary.
- Exposed canonical `execution_id` on `LoopResult` for control-plane correlation.
- Replaced the duplicate scheduler-based `VNextOrchestrator` execution world with a facade over `RuntimeOrchestrator`.
- Added crash-consistency and persistence-boundary documentation/tests.
- Added lease fencing generation support and stale-owner checks.

## Current architecture work
- One durable execution authority: `RuntimeOrchestrator` → `AutonomousExecutionLoop`.
- One lifecycle mutation authority: `ExecutionCommitCoordinator` → Journal / Store / Audit.
- vNext orchestration is a facade over the canonical runtime; it no longer creates a second scheduler execution world.
- Agent → Tool Registry → Permission Boundary → Tool Executor.
- Recovery: Bootstrap → Policy / Queue → Lease → Resume.
- Persistence adapters remain replaceable behind runtime boundaries.
- Journal integrity is enforced on every record rewrite, including lifecycle status changes.

## Next actions
1. Finish fencing-token propagation into the persistence mutation boundary.
2. Run the complete test suite and targeted recovery/concurrency tests in CI.
3. Audit all remaining direct lifecycle mutations (`ExecutionStore.save/transition`) and classify setup-only persistence versus runtime mutation.
4. Add crash-window tests for journal/store/audit ordering.
5. Add integration tests for stale lease ownership and recovery takeover.
6. Evaluate a distributed persistence/lease adapter for multi-machine production use.
7. Record architectural decisions and handoffs here or in docs/ADR.

## Rules
Every agent updates this file before and after significant work. GitHub is the source of truth; do not rely on local chat history.
