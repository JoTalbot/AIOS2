# AIOS New Architecture — Shared Agent Status

## Current phase
- Phase: isolated new architecture hardening and integration
- Branch: `main`
- Latest integrated commit: `19defd0e810afc4c2568de46f82928f6937f1d38`
- Active work branch: `batch7G/pytest-baseline-hardening`

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
| batch7G/pytest-baseline-hardening | Full-suite baseline and execution-boundary compatibility | active | in progress |

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
- Added structured recovery outcome contract and hardened its API boundary validation.
- Added regression coverage for empty execution IDs, unsupported statuses and stable serialization.
- Added a repository-wide pytest GitHub Actions workflow (`.github/workflows/tests.yml`).
- Fixed typed `ToolCall` argument forwarding in the registry execution boundary and added regression coverage.

## Validation
- Security workflow for main commit `19defd0e810afc4c2568de46f82928f6937f1d38` is passing.
- Repository-wide pytest workflow for that commit is currently failing: 17 failed, 87 passed.
- The failures are a mixture of stale pre-hardening expectations and remaining compatibility/integration defects; they are now the primary baseline for batch remediation.
- Active branch contains the first execution-boundary compatibility fix and its regression test.

## Next actions
1. Push the active branch and run its full pytest workflow.
2. Remediate remaining genuine integration defects without weakening lease, permission, CAS, or recovery fencing guarantees.
3. Update stale tests to the stabilized recovery outcome and lease-aware contracts where the API intentionally changed.
4. Continue with atomic execution version + fencing CAS and crash-consistency fault injection.
5. Audit recovery HTTP/runtime bootstrap and lease renewal/release for fail-closed stale-owner behavior.

## Rules
Every agent updates this file before and after significant work. GitHub is the source of truth; do not rely on local chat history.
