# AIOS2 Shared Agent Status

## Current phase
- Phase: production hardening of the vNext execution/recovery path
- Branch: `batch/24-coordination-lock-unification`
- Latest integrated commit on `main`: `8c9dc3b87dfaa075317959c0893acb9c4e7b40c1`
- Active work commits: `058adaff1c67f5b50071502e69bd126f29781249`, `1ca1dcc64995ab3e8163c0cf7085fb95e4b2200d`
- Active PR: pending creation

## Current architecture
- Runtime owns execution identity, persistence, checkpoints, recovery, leases, fencing and audit.
- Cognition is an ephemeral decision boundary over the canonical `ExecutionContext`.
- Execution persistence and lease coordination must use one execution-scoped coordination lock when configured.

## Batch 24 — Coordination lock unification
- Fixed `ExecutionStore._save()` and therefore normal `save()`/CAS writes to acquire `execution_lock()` instead of bypassing the configured coordination lock.
- This closes a split-lock race where lease operations and state CAS could coordinate on different lock files.
- Added regression coverage proving CAS uses the configured coordination lock.

## Validation
- Focused regression tests added in `tests/test_execution_lock_protocol.py`.
- Local execution is not available through the GitHub connector; GitHub Actions is authoritative.
- Branch is based directly on current `main` and is 2 commits ahead, 0 behind.

## Next actions
1. Open PR for Batch 24 and wait for GitHub Actions.
2. Fix CI failures on this owning branch only.
3. Merge only after CI is green.
4. Rescan execution/recovery boundaries for the next concurrency, durability or security issue.

## Rules
GitHub is the source of truth. Every significant step updates this file. Do not force-push shared branches.
