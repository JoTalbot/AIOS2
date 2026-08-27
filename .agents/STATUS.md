# AIOS New Architecture — Shared Agent Status

## Current phase
- Phase: isolated new architecture hardening and integration
- Branch: `main`
- Latest integrated commit: `16327541969a6a121e1c99760216e41050b9dfae`

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
| batch7/observability | Structured recovery outcome | PR #24 | open / pending merge | 
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
- Added structured recovery outcome work in PR #24.
- Added a repository-wide pytest GitHub Actions workflow (`.github/workflows/tests.yml`) so the full test suite runs on pushes and pull requests.

## Current architecture work
- vNext orchestration/execution path.
- Agent → Tool Registry → Permission Boundary → Tool Executor.
- Persistence, checkpoint, recovery, leases and audit contracts.
- CI now has a full pytest workflow in addition to the security regression workflow.

## Validation
- Security workflow is present and has passed on recent commits.
- Full pytest workflow has just been added; its first run should be used as the baseline for the entire repository test suite.
- PR #23 merged successfully; PR #24 remains open until its branch is synchronized and validated.

## Next actions
1. Let the new full pytest workflow establish the repository-wide baseline and fix failures in batches.
2. Merge/synchronize PR #24 without moving `main` backwards.
3. Audit recovery HTTP and runtime bootstrap paths for fail-closed/contract-hardening gaps.
4. Audit lease renewal/release for stale-owner behavior and monotonic ownership semantics.
5. Continue parallel development through isolated branches/PRs and update this status after each significant batch.

## Rules
Every agent updates this file before and after significant work. GitHub is the source of truth; do not rely on local chat history.
