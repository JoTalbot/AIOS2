# AIOS New Architecture — Shared Agent Status

## Current phase
- Phase: isolated new architecture hardening and integration
- Branch: `batch/bootstrap-recovery-hardening-v2`
- Latest integrated commit on `main`: `d25aa96390cc9f06344fae7ca60bc0d262548648`
- Active work commit: `a69c9d12426691d6f26d9366c278f3f699024fbc`
- Active PR: #50

## Current architecture work
- vNext orchestration/execution path.
- Persistence, checkpoint, recovery, leases and audit contracts.
- ExecutionStore and ExecutionLeaseStore share one execution-scoped coordination lock domain.
- Commit/reconcile holds the shared lock across lease validation and version/status/fencing-aware CAS, preventing lease rotation between validation and state mutation.
- Post-CAS crash leaves a durable pending intent; recovery appends the audit event by stable event identity and marks the journal intent reconciled/applied.
- Audit append is idempotent by event identity, so a crash after audit append and before journal marking cannot create duplicates on repeated recovery.
- Lease rotation after a post-CAS crash fences the stale worker and prevents stale reconciliation from reapplying the intent.
- Durable tool intents use owner/claim-token fencing for recovery and terminal transitions.

## New hardening — PR #50
- Runtime bootstrap recovery now observes heartbeat failures instead of silently cancelling a failed heartbeat task.
- A lost/fenced lease during an asynchronous resume fails the recovery operation closed and cancels the stale resume task.
- Both synchronous and asynchronous resume paths perform a final fencing ownership check before reporting success.
- Added regression coverage for heartbeat lease loss and post-resume fencing.

## Validation
- Code changes are committed on `batch/bootstrap-recovery-hardening-v2`.
- PR #50 targets `main`.
- GitHub Actions is the authoritative full-suite validation path; no workflow run is reported yet for the new head commit.

## Next actions
1. Wait for GitHub Actions validation of PR #50.
2. Review any CI failures and fix only on the owning branch.
3. Merge only after required CI is green, then update this status on `main`.

## Rules
Every agent updates this file before and after significant work. GitHub is the source of truth; do not rely on local chat history.
