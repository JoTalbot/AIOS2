# AIOS New Architecture — Shared Agent Status

## Current phase
- Phase: isolated new architecture hardening and integration
- Branch: `batch/16-recovery-lease-fencing`
- Latest integrated commit on `main`: `87bb83bf558931fe97fdae2040b4425c500e8273`
- Active work commit: `6bb18b8358624d091540d57a685b38ab5b2a6520`
- Active PR: pending creation

## Current architecture work
- vNext orchestration/execution path.
- Persistence, checkpoint, recovery, leases and audit contracts.
- ExecutionStore and ExecutionLeaseStore share one execution-scoped coordination lock domain.
- Commit/reconcile holds the shared lock across lease validation and version/status/fencing-aware CAS, preventing lease rotation between validation and state mutation.
- Post-CAS crash leaves a durable pending intent; recovery appends the audit event by stable event identity and marks the journal intent reconciled/applied.
- Audit append is idempotent by event identity, so a crash after audit append and before journal marking cannot create duplicates on repeated recovery.
- Lease rotation after a post-CAS crash fences the stale worker and prevents stale reconciliation from reapplying the intent.
- Durable tool intents use owner/claim-token fencing for recovery and terminal transitions.

## Batch 16 — Recovery/Lease Fencing Hardening
- Recovery lease scope now follows `execution_id` when present, falling back to the intent key for legacy intents.
- Final lease ownership validation and terminal claim transition are performed under the lease coordination lock, closing the check-to-act fencing window.
- Lease loss before terminal commit leaves the intent executing for safe recovery instead of allowing a stale worker to finalize it.
- Added regression coverage for execution-scoped leases and deterministic lease rotation during reconciliation.

## Validation
- Changes are committed on `batch/16-recovery-lease-fencing`.
- Target: `main`.
- GitHub Actions is the authoritative full-suite validation path.

## Next actions
1. Create PR for Batch 16 and wait for GitHub Actions validation.
2. Fix any CI failures only on the owning branch.
3. Merge only after required CI is green, then update this status on `main`.

## Rules
Every agent updates this file before and after significant work. GitHub is the source of truth; do not rely on local chat history.
