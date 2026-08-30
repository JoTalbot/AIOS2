# AIOS2 Project State

Status: ACTIVE

Protocol: UASEP 3.4.0

## Objective

Production hardening of the AIOS2 autonomous runtime: execution/recovery durability, API hardening, and release automation.

## Architecture

- `kernel/` — core runtime and orchestration logic
- `runtime/` — execution environment: commit journal, leases, fencing, checkpoints, recovery
- `cognition/` — ephemeral decision boundary over the canonical `ExecutionContext`
- `api/` — FastAPI service interfaces (`/health`, `/ready`, `/diagnostics`)
- `tests/` — 102 test files, 232 tests green at adoption time
- One canonical execution/persistence/recovery path; parallel stores or recovery mechanisms require an ADR (`.uasep/decisions/`)

## Current phase

Production hardening. Batches 1–25 landed; release automation matured to v1.7.0.

## Verified

- Full test suite green on `main` @ `97e2edf`: 232 passed (EV-AIOS2-BASELINE-2026-08-30.json).
- Batch 25 (journal read coordination) content is present on `main` (`_JournalLock`, `_read_journal_unlocked` in `runtime/execution_commit.py`) even though the branch ref is not an ancestor of `main` (rebase-merge history).
- UASEP v3.4.0 durable artifacts validate against the UASEP JSON schemas.

## Unknown

- Whether batch 26–29 branch content is fully included in `main`; ancestry checks are unreliable under rebase merges and require content-level verification.

## Next best actions

1. Verify batch 26–29 inclusion at content level; open new work only for concrete gaps.
2. Continue concurrent corruption and quarantine hardening.
3. Reduce operational documentation debt.
4. Reconcile or delete stale batch branches.

## Permanent constraints

- Do not force-push shared branches; do not rewrite merged history.
- No parallel execution stores, execution state, or recovery mechanisms without an ADR.
- Every public-contract change ships with a regression test.
- AIOS2 remains responsible for its own domain architecture; the UASEP layer is coordination and memory only — it must not introduce competing execution infrastructure.
