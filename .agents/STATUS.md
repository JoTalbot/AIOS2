# AIOS New Architecture — Shared Agent Status

## Current phase
- Phase: isolated new architecture hardening and integration
- Branch: `batch/bootstrap-recovery-fail-closed`
- Latest integrated commit on `main`: `ae1838a2c4994f1cd7d6e110532e0fe341bcf021`
- Active work commit: `499f21d23811043a2c4c6a0cf6111240fbcc1c18`

## Current architecture work
- vNext orchestration/execution path.
- Persistence, checkpoint, recovery, leases and audit contracts.
- ExecutionStore and ExecutionLeaseStore share one execution-scoped coordination lock domain.
- Commit/reconcile holds the shared lock across lease validation and version/status/fencing-aware CAS, preventing lease rotation between validation and state mutation.
- Post-CAS crash is recoverable from the durable pending journal intent; reconciliation records audit exactly once and marks the intent applied.
- Lease rotation after a post-CAS crash fences the stale worker and prevents stale reconciliation from reapplying the intent.

## New hardening
- Runtime bootstrap recovery now observes heartbeat failures instead of silently cancelling a failed heartbeat task.
- A lost/fenced lease during an asynchronous resume fails the recovery operation closed and cancels the stale resume task.
- Synchronous resume paths perform a final fencing ownership check before reporting success.

## Validation
- Existing bootstrap lease tests remain covered.
- Added regression coverage proving heartbeat lease loss cannot be reported as successful recovery.
- Required targeted and full GitHub Actions validation is pending for this branch.

## Next actions
1. Run targeted bootstrap lease/recovery tests through GitHub Actions.
2. Run full tests and security regression checks.
3. Merge only after required CI is green, then update this status on `main`.

## Rules
Every agent updates this file before and after significant work. GitHub is the source of truth; do not rely on local chat history.
