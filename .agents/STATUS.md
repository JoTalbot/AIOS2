# AIOS New Architecture — Shared Agent Status

## Current phase
- Phase: isolated new architecture hardening and integration
- Branch: `main`
- Latest integrated commit: `7e2ee98a96b0dfe74b6afb12165f9543d2a17211`

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

## Completed
- Hardened execution state-machine validation and unknown-state handling.
- Made tool permissions immutable and normalized registry contracts; added unregister support.
- Isolated individual startup-recovery failures and added explicit fail-fast mode.
- Changed corrupted execution-store handling from silent reset to fail-closed errors.
- Prevented malformed commit-journal lines from poisoning later valid entries or reusing sequence numbers.
- Changed corrupted execution leases to fail closed and validate persisted entry shape.
- Integrated optional per-execution leases into recovery with safe release on success/failure.
- Hardened lease-aware checkpoint contracts for execution identity, attempt number and failure error.
- Added regression coverage for hardening areas; full runtime test execution remains pending in a project environment.

## Current architecture work
- vNext orchestration/execution path.
- Agent → Tool Registry → Permission Boundary → Tool Executor.
- Persistence, checkpoint, recovery, leases and audit contracts.

## Validation
- GitHub commit status is currently empty; this repository has no general test workflow configured under `.github/workflows` (only `security.yml` is present).
- PRs #12–#14 merged successfully.
- Full runtime test execution should be performed by the next agent/machine with the project environment available.

## Next actions
1. Add targeted regression tests for the new lease corruption and checkpoint contract behavior.
2. Audit recovery HTTP and runtime bootstrap paths for fail-closed/contract-hardening gaps.
3. Audit lease acquisition for multi-process race resistance and stale-owner behavior.
4. Add ADR/research notes for public lifecycle or persistence contract changes.
5. Continue parallel development through isolated branches/PRs and update this status after each significant batch.

## Rules
Every agent updates this file before and after significant work. GitHub is the source of truth; do not rely on local chat history.
