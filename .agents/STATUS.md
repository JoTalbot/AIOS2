# AIOS New Architecture — Shared Agent Status

## Current phase
- Phase: P0 execution hardening → P1 AIOS subsystem completion
- Branch: `canonical-execution`
- Source architecture line: `JoTalbot/AIOS:new`

## Completed this batch
- Restored project purpose, original AIOS positioning and new-architecture plan.
- Added `pyproject.toml` with package/dependency/dev-tool contract.
- Added full CI workflow for tests, lint and security regression suite.
- Added architecture guards and regression tests.
- Added roadmap covering P0/P1/P2/P3 completion.
- Added ADRs for canonical execution authority, cognition/runtime boundary, derived events and file-backed persistence scope.
- Created GitHub issues for the next P0/P1 architecture work.
- Added monotonic `ExecutionState.version` with optimistic CAS in the persistence mutation boundary.
- Added `ExecutionState.fencing_token` and stale fencing rejection in persistence.
- Extended `ExecutionCommitCoordinator` journal records with expected version and fencing generation.
- Propagated the lease fencing generation from `LeaseAwareCheckpoint` into execution state/commit.
- Removed the RecoveryCheckpoint direct-store lifecycle fallback; canonical committer is now mandatory.
- Added deterministic concurrency regression coverage for stale version and stale fencing workers.
- Added crash-window tests for journal→store and store→audit failure ordering, including idempotent reconciliation.

## P0 blockers
1. Complete fault-injection coverage for every commit ordering window.
2. Complete atomic distributed persistence adapter — version/fencing CAS is now present in the file-backed boundary; production distributed adapter remains required.

## P1 work queue
3. Unified capability/policy engine — issue #3.
4. Durable Memory runtime — issue #4.
5. LLM provider abstraction — issue #5.
6. Cognition/runtime separation — issue #6.

## Architecture invariants
- One durable execution authority: `RuntimeOrchestrator` → `AutonomousExecutionLoop`.
- One lifecycle mutation authority: `ExecutionCommitCoordinator` → Journal / Store / Audit.
- Runtime lifecycle mutations must not bypass the canonical commit path.
- Mutable execution state requires monotonic version/CAS semantics.
- Worker mutations require valid lease ownership and fencing generation at the persistence boundary.
- Events are derived from committed durable state, never a second state authority.
- Cognition decides WHAT/WHY; Runtime guarantees HOW/WHEN.
- Persistence adapters are replaceable; file-backed adapters are not the distributed production contract.

## Delivery rule
All source, test, documentation, configuration and architecture changes are written directly to GitHub on `canonical-execution`. Each completed atomic batch must be committed/pushed before reporting completion.

## Rules
Every agent updates this file before and after significant work. GitHub is the source of truth; do not rely on local chat history.
