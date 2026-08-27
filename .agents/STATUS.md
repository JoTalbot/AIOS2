# AIOS New Architecture — Shared Agent Status

## Current phase
- Phase: isolated new architecture hardening and integration
- Branch: `batch7E/recovery-outcome-rebased` (PR preparation)
- Latest integrated main commit: `6114933099bca2b6096e15a4155548b4b5a6da4e`
- Current batch commit: `fefb10f662bb61bcb63ba17ce91c320e10450d0b`

## Active agents

| Agent | Task | Branch | Status |
|---|---|---|---|
| batch/state-machine-hardening | Execution lifecycle invariants | merged via PR #7 | completed |
| batch/tool-registry-hardening | Tool permission/registry contracts | merged via PR #8 | completed |
| batch/recovery-isolation | Restart recovery failure isolation | merged via PR #9 | completed |
| batch/execution-store-integrity | Corrupted execution-store handling | merged via PR #10 | completed |
| batch/execution-commit-journal | Commit journal corruption/sequence recovery | merged via PR #11 | completed |
| batch/lease-corruption-hardening | Fail-closed lease persistence | merged via PR #12 | completed |
| batch/recovery-lease-integration | Lease-aware startup recovery | merged via PR #13 | completed |
| batch/checkpoint-contracts | Lease-aware checkpoint input contracts | merged via PR #14 | completed |
| batch7/lease-sync | Multi-process lease synchronization | merged via PR #23 | completed |
| batch7/observability | Structured recovery outcome | PR #24 | superseded by rebased batch |
| batch7E/recovery-outcome-rebased | Harden stable recovery outcome contract | current branch | in PR preparation |
| batch7C-7F | Readiness/bootstrap/renewal/recovery HTTP | next | planned |

## Completed
- Hardened execution state-machine validation and unknown-state handling.
- Made tool permissions immutable and normalized registry contracts; added unregister support.
- Isolated individual startup-recovery failures and added explicit fail-fast mode.
- Changed corrupted execution-store handling from silent reset to fail-closed errors.
- Prevented malformed commit-journal lines from poisoning later valid entries or reusing sequence numbers.
- Changed corrupted execution leases to fail closed and validate persisted entry shape.
- Integrated optional per-execution leases into recovery with safe release on success/failure.
- Hardened lease-aware checkpoint contracts for execution identity, attempt number and failure error.
- Added multi-process synchronization for file-backed execution leases.
- Added full pytest GitHub Actions workflow.
- Rebased the structured recovery outcome work onto current `main` and added strict boundary validation tests.

## Current architecture work
- vNext orchestration/execution path.
- Agent → Tool Registry → Permission Boundary → Tool Executor.
- Persistence, checkpoint, recovery, leases and audit contracts.
- CI has a full pytest workflow in addition to the security regression workflow.

## Validation
- New recovery outcome tests are committed on the rebased branch.
- No workflow run is exposed yet for the latest branch commit; CI validation remains pending after PR creation.
- PR #24 is divergent from current `main` and should not move `main` backwards; this branch supersedes it with the same feature rebased onto current `main`.

## Next actions
1. Open a replacement PR from the rebased recovery-outcome branch.
2. Use CI as the repository-wide pytest baseline and fix failures in batches.
3. Audit recovery HTTP and runtime bootstrap paths for fail-closed/contract-hardening gaps.
4. Audit lease renewal/release for stale-owner behavior and monotonic ownership semantics.
5. Continue parallel development through isolated branches/PRs and update this status after each significant batch.

## Rules
Every agent updates this file before and after significant work. GitHub is the source of truth; do not rely on local chat history.
