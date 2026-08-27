# AIOS New Architecture — Shared Agent Status

## Current phase
- Phase: isolated new architecture hardening and integration
- Branch: `batch/recovery-http-hardening`
- Latest integrated commit on `main`: `ec5ac30764bfa54ef66ac639f0c26ce369ce3f22`
- Active work commit: `8626a2ae5ef1855373edd365e8055c4f69be7981`

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
| batch/lease-renewal-fencing | Stale-owner lease renewal and bootstrap failure fencing | merged via PR #38 | completed |
| batch/atomic-cas-crash-hardening | Atomic execution CAS durability and recovery isolation | merged via PR #39 | completed |
| batch/recovery-http-hardening | Recovery HTTP contract validation and centralized mutation RBAC | current branch | active |

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
- Added a repository-wide pytest GitHub Actions workflow (`.github/workflows/tests.yml`).
- Added fencing-token validation to lease renewal while preserving the existing owner-only renewal API.
- Updated runtime bootstrap heartbeat to renew with its fencing token.
- Updated bootstrap recovery failure persistence to pass the active lease to `RecoveryManager.mark_failed`, preventing stale workers from committing terminal failure state.
- Added regression coverage for stale renewal using a re-acquired lease with the same owner ID.
- Restored `ExecutionContext` compatibility export through `runtime.execution_store`.
- Added optimistic execution-state CAS and atomic persistence hardening in the latest integrated batch.

## Current architecture work
- vNext orchestration/execution path.
- Agent → Tool Registry → Permission Boundary → Tool Executor.
- Persistence, checkpoint, recovery, leases and audit contracts.
- CI has a full pytest workflow in addition to the security regression workflow.
- Recovery HTTP transport now validates supported actions at the request boundary and uses one centralized operator-role guard for mutations.

## Validation
- Recovery HTTP hardening implementation and focused regression tests are committed on `batch/recovery-http-hardening`.
- The branch is based directly on current `main` after PR #39 integration.
- GitHub Actions remains the authoritative full-suite validation path; local execution is not available through the GitHub connector.

## Next actions
1. Open a PR for `batch/recovery-http-hardening` and validate its CI.
2. Audit runtime bootstrap/recovery exception mapping for remaining fail-closed gaps.
3. Continue crash-consistency fault injection around execution CAS + commit journal ordering.
4. Merge only after required CI is green, then update this status on `main`.

## Rules
Every agent updates this file before and after significant work. GitHub is the source of truth; do not rely on local chat history.
