# Execution Invariants

AIOS2 durable execution is governed by these invariants. Production runtime paths must preserve them; tests should encode each one.

## I-001 — State-machine validity

Every lifecycle transition must be accepted by the canonical execution state machine.

## I-002 — Canonical mutation boundary

Every externally visible lifecycle transition must pass through `ExecutionCommitCoordinator`.

`AutonomousExecutionLoop`, recovery services, checkpoints, and orchestration layers must not mutate lifecycle state directly through `ExecutionStore`.

The only non-transition persistence operation permitted in the execution loop is initial materialization of a new `pending` execution before its first canonical transition.

## I-003 — Journal before durable transition

A lifecycle transition is journaled before its durable store transition. A crash after journal append but before store mutation must be recoverable by reconciliation.

## I-004 — Audit idempotency

A logical commit produces at most one audit event, identified by the commit identity. Reconciliation must not duplicate audit events.

## I-005 — Journal integrity

Every journal record has a checksum over all fields except the checksum itself. Any mutation of a record, including changing `pending` to `applied` or `reconciled`, must recompute the checksum. Invalid records are quarantined and never treated as authoritative.

## I-006 — Monotonic journal sequence

Valid journal records have strictly increasing sequence numbers. Sequence allocation must consider sequence numbers present in malformed/corrupt records so that a new commit cannot reuse a previously allocated sequence.

## I-007 — Serialized journal mutation

All journal read-modify-write operations are serialized by the journal lock. File-backed persistence is a single-node/process-safe adapter, not a distributed database.

## I-008 — Lease ownership

A worker may mutate a leased execution only while it owns a non-expired lease. Lease acquisition/renewal/release operations are serialized across processes.

## I-009 — Recovery convergence

Startup recovery first reconciles pending journal commits, then discovers resumable executions, applies recovery policy, acquires a lease, and resumes through the canonical loop.

## I-010 — Recovery mutation boundary

Recovery failure handling must use `ExecutionCommitCoordinator`; there is no production fallback that writes lifecycle failure directly to `ExecutionStore`.

## I-011 — Orchestration convergence

`RuntimeOrchestrator` is the runtime lifecycle owner. `VNextOrchestrator` is an orchestration facade and must not create an independent execution/scheduler state machine.

## I-012 — Execution identity continuity

An execution retains its `execution_id` across retries, checkpoints, restart, reconciliation, and resume.

## Verification matrix

| Invariant | Unit | Integration | Crash/concurrency |
| --- | --- | --- | --- |
| I-001 | state machine | loop transitions | — |
| I-002 | coordinator boundary | runtime factory/loop | — |
| I-003 | commit protocol | bootstrap reconciliation | journal/store crash window |
| I-004 | audit idempotency | recovery | repeated reconciliation |
| I-005 | checksum | journal reader | corrupted-record recovery |
| I-006 | sequence | journal append | corruption + append |
| I-007 | lock | coordinator | multi-process writers |
| I-008 | lease | lease store | stale-owner takeover |
| I-009 | recovery | fresh-runtime recovery | restart |
| I-010 | recovery manager | bootstrap failure | crash during recovery |
| I-011 | orchestrator | end-to-end runtime | restart |
| I-012 | execution context | resume | restart |
