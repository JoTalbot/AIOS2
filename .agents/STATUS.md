# AIOS New Architecture — Shared Agent Status

## Current phase
- Phase: isolated new architecture hardening and integration
- Branch: `batch/15-tool-boundary-integration`
- Latest integrated commit on `main`: `a9e5b9161f6985a104b775ca0008f10261cc8378`
- Active work commit: `a98236f72059bc6b6e195dabcf05cf048c97a397`
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

## Batch 15 — Tool execution boundary integration
- Corrected the ambiguous-result regression to reflect the store's `executing` claim state.
- Routed terminal ToolExecutor persistence through the canonical `ToolExecutionBoundary` when both durable intent and idempotency stores are configured.
- Claim loss after durable terminal-result persistence now propagates as an ambiguous result instead of falsely reporting a committed terminal intent.
- Added regression coverage proving the durable result survives claim loss while the intent remains non-terminal for recovery.

## Validation
- Changes are committed on `batch/15-tool-boundary-integration`.
- Target: `main`.
- GitHub Actions is the authoritative full-suite validation path.

## Next actions
1. Create PR for Batch 15 and wait for GitHub Actions validation.
2. Fix any CI failures only on the owning branch.
3. Merge only after required CI is green, then update this status on `main`.

## Rules
Every agent updates this file before and after significant work. GitHub is the source of truth; do not rely on local chat history.
