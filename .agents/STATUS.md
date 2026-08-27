# AIOS New Architecture — Shared Agent Status

## Current phase
- Phase: isolated new architecture hardening and integration
- Branch: `batch/lease-renewal-fencing`
- Latest integrated commit: `19defd0e810afc4c2568de46f82928f6937f1d38`
- Active work commit: `79befaafdf3ec51167d71cf770a61bd603f54a5f`

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
| batch7/observability | Structured recovery outcome | merged via PR #24 | completed |
| batch7E/recovery-outcome-rebased | Harden stable recovery outcome contract | superseded by direct main hardening | completed |
| batch/lease-renewal-fencing | Stale-owner lease renewal and bootstrap failure fencing | current branch | completed, awaiting CI |

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
- Added structured recovery outcome contract and then hardened its API boundary validation.
- Added a repository-wide pytest GitHub Actions workflow (`.github/workflows/tests.yml`).
- Added fencing-token validation to lease renewal while preserving the existing owner-only renewal API.
- Updated runtime bootstrap heartbeat to renew with its fencing token.
- Updated bootstrap recovery failure persistence to pass the active lease to `RecoveryManager.mark_failed`, preventing stale workers from committing terminal failure state.
- Added regression coverage for stale renewal using a re-acquired lease with the same owner ID.

## Current architecture work
- vNext orchestration/execution path.
- Agent → Tool Registry → Permission Boundary → Tool Executor.
- Persistence, checkpoint, recovery, leases and audit contracts.
- CI has a full pytest workflow in addition to the security regression workflow.

## Validation
- Code and regression test changes are committed on `batch/lease-renewal-fencing`.
- Local test execution is not available through the GitHub connector; the repository pytest workflow is the validation target after push/PR.

## Next actions
1. Run/inspect repository-wide pytest CI for `batch/lease-renewal-fencing`.
2. Audit recovery HTTP and runtime bootstrap paths for remaining fail-closed/contract-hardening gaps.
3. Continue with atomic execution version + fencing CAS and crash-consistency fault injection.
4. Open/merge the isolated branch after CI passes.
5. Update status on `main` after integration.

## Rules
Every agent updates this file before and after significant work. GitHub is the source of truth; do not rely on local chat history.
