# AIOS2 Shared Agent Status

## Current phase
- Phase: production hardening of the vNext execution/recovery path
- Branch: `batch/25-journal-read-coordination`
- Base: `main` at `42674320f157b49133aa38542e40a50b3e6a94f9`
- Active PR: pending creation

## Current architecture
- Runtime owns execution identity, persistence, checkpoints, recovery, leases, fencing and audit.
- Cognition is an ephemeral decision boundary over the canonical `ExecutionContext`.
- Execution persistence and lease coordination use one execution-scoped coordination lock when configured.
- Commit journal writes and reads use a dedicated journal lock.

## Batch 25 — Journal read coordination
- Added `_read_journal_unlocked()` as the internal parser/repair primitive.
- Wrapped public journal reads in `_JournalLock` so readers cannot observe a concurrent append/mark operation mid-write.
- Updated `_mark()` to call the unlocked reader while already holding the journal lock, removing reliance on nested lock acquisition.
- Added regression coverage proving `pending()` uses the journal lock.

## Validation
- Focused regression test added in `tests/test_execution_commit_faults.py`.
- Full CI and security validation will run through GitHub Actions after PR creation.

## Next actions
1. Open PR for Batch 25.
2. Wait for full CI and security checks.
3. Fix failures on this owning branch only.
4. Merge only after CI is green.
5. Continue with concurrent corruption/quarantine behavior and then operational documentation debt.

## Rules
GitHub is the source of truth. Every significant step updates this file. Do not force-push shared branches.
