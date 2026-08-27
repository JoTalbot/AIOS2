# Crash consistency contract

AIOS execution persistence uses a journal-first recovery protocol. The file-backed adapter is a single-node durability implementation, not a distributed transaction coordinator.

## Required invariants

1. A lifecycle mutation is represented by a journal commit before it is considered durable.
2. A pending journal commit is replayable after process restart.
3. Reconciliation is idempotent: an already-applied commit is not applied again.
4. Journal sequence allocation remains monotonic across quarantined/corrupt records.
5. Journal status changes recompute integrity metadata.
6. Lifecycle audit is emitted exactly once for a canonical commit.
7. Lease ownership is required before recovery mutates an execution.
8. Stale workers must not be allowed to publish a lifecycle mutation after losing ownership.

## Crash windows

The current protocol explicitly tolerates a crash between journal append, store mutation, audit, and journal finalization. Startup reconciliation is responsible for converging pending commits.

The file-backed implementation serializes local processes with locks, but production multi-machine deployment requires a distributed repository, journal, and lease implementation with atomic ownership/commit primitives.
