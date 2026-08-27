# AIOS New Architecture — Shared Agent Status

## Current phase
- Phase: isolated new architecture hardening and integration
- Branch: `batch/recovery-fencing-cas`
- Latest integrated commit on `main`: `47103e6e5f972b7b578d6dca7c0b94c957d97fb2`
- Active work commit: `b07410551e53d3700e291c2a2a5c0d30b3ce4cb3`

## Active agents
| Agent | Task | Branch | Status |
|---|---|---|---|
| batch/recovery-http-hardening | Recovery HTTP contract validation, centralized mutation RBAC, and crash-consistency fault injection | merged via PR #40 | completed |
| batch/recovery-fencing-cas | Close lease-to-state TOCTOU with shared execution-scoped lock, fencing-aware CAS, post-CAS recovery, and audit idempotency | current branch | awaiting CI |

## Current architecture work
- vNext orchestration/execution path.
- Persistence, checkpoint, recovery, leases and audit contracts.
- ExecutionStore and ExecutionLeaseStore share one execution-scoped coordination lock domain.
- Commit/reconcile holds the shared lock across lease validation and version/status/fencing-aware CAS, preventing lease rotation between validation and state mutation.
- Post-CAS crash leaves a durable pending intent; recovery appends the audit event by stable event identity and marks the journal intent reconciled/applied.
- Audit append is idempotent by event identity, so a crash after audit append and before journal marking cannot create duplicates on repeated recovery.
- Lease rotation after a post-CAS crash fences the stale worker and prevents stale reconciliation from reapplying the intent.

## Validation
- Added regression coverage proving stale fencing cannot reconcile pending intent.
- Added regression coverage for fencing loss after journal append.
- Added concurrency coverage proving lease rotation waits for the coordinated state transition.
- Added fault-injection coverage for crashes before audit/journal-applied marking and post-CAS recovery.
- Added fault-injection coverage for crash after audit append before journal-applied marking, including repeated recovery and stable audit identity deduplication.
- GitHub Actions is the authoritative full-suite validation path.

## Next actions
1. Validate `batch/recovery-fencing-cas` through GitHub Actions.
2. Audit runtime bootstrap/recovery exception mapping for remaining fail-closed gaps.
3. Merge only after required CI is green, then update this status on `main`.

## Rules
Every agent updates this file before and after significant work. GitHub is the source of truth; do not rely on local chat history.
