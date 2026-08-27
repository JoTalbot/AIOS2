# AIOS New Architecture — Shared Agent Status

## Current phase
- Phase: isolated new architecture hardening and integration
- Branch: `batch/recovery-fencing-races`
- Latest integrated commit on `main`: `47103e6e5f972b7b578d6dca7c0b94c957d97fb2`
- Active work commit: `d5d738ea06a65f882ec5b9de46cda9bd002c8d47`

## Active agents
| Agent | Task | Branch | Status |
|---|---|---|---|
| batch/recovery-http-hardening | Recovery HTTP contract validation, centralized mutation RBAC, and crash-consistency fault injection | merged via PR #40 | completed |
| batch/recovery-fencing-races | Fence stale commit/reconcile workers with execution lease tokens | current branch | ready for CI |

## Current architecture work
- vNext orchestration/execution path.
- Persistence, checkpoint, recovery, leases and audit contracts.
- Execution commit coordination optionally enforces an `ExecutionLeaseStore` owner/fencing token during commit and reconciliation.
- Recovery reconciliation now refuses to apply pending intent when the worker's lease/fencing token is no longer current.

## Validation
- Added regression coverage for stale fencing tokens during reconciliation.
- Added regression coverage for fencing loss after journal append before store transition.
- GitHub Actions is the authoritative full-suite validation path.

## Next actions
1. Validate `batch/recovery-fencing-races` through GitHub Actions.
2. Audit runtime bootstrap/recovery exception mapping for remaining fail-closed gaps.
3. Merge only after required CI is green, then update this status on `main`.

## Rules
Every agent updates this file before and after significant work. GitHub is the source of truth; do not rely on local chat history.
