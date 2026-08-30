# AIOS2 Architecture

## Boundaries

`cognition` decides what should happen. `runtime` owns whether and how an execution is durably performed. `api` is the external service boundary. `kernel` supplies scheduling.

## Execution lifecycle

1. An execution receives a stable identity and versioned state.
2. Runtime persists state and checkpoints.
3. Lease ownership and fencing prevent stale workers from mutating state.
4. Commit coordination journals an intended state transition before applying it.
5. The state transition uses CAS under the configured execution coordination lock.
6. Audit records describe applied or reconciled transitions.
7. Recovery reconciles pending journal intents only when the current state and fencing authority still permit the transition.

## Journal protocol

The commit journal is an integrity-protected JSONL log. Append, read, quarantine, and rewrite operations share the journal lock boundary. `_read_journal_unlocked()` is an internal primitive used only when its caller already owns that lock, avoiding nested lock acquisition during `_mark()`.

## Concurrency model

Execution state and lease operations must not coordinate through unrelated lock files when an execution-scoped coordination lock is configured. Journal coordination is a separate concern because the journal is a process-shared recovery log.

## Failure model

The design assumes crashes can occur after durable journal append but before state persistence, after state persistence but before audit, and during recovery. Pending journal intents provide the durable recovery point. Fencing and state/version checks prevent stale workers from replaying obsolete intents.

## Security boundary

Recovery operations are protected by the API RBAC layer. Fencing is treated as an authorization primitive for state mutation, not merely as a concurrency optimization.
