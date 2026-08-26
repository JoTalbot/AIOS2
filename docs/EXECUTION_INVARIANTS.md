# AIOS2 Execution Invariants

This document is the contract for the vNext execution runtime. Runtime changes that affect these invariants require regression coverage.

## Lifecycle

1. Every lifecycle transition is validated by `ExecutionStateMachine`.
2. Runtime components do not mutate lifecycle state directly through `ExecutionStore`.
3. `ExecutionCommitCoordinator` is the canonical lifecycle mutation boundary.
4. A committed transition produces one durable journal record and one idempotent audit event.
5. Commit identity is stable for retries of the same logical transition.

## Recovery

6. A pending journal commit is recoverable after process interruption.
7. Reconciliation is idempotent and must not duplicate audit events.
8. Recovery uses the same commit boundary as normal execution.
9. Recovery must acquire an execution lease before resuming work.
10. A stale lease holder must not checkpoint or transition execution state.

## Ownership and concurrency

11. Lease claim/renew/release read-modify-write operations are process serialized by the lease adapter.
12. An execution may have at most one active lease owner at a time.
13. Losing ownership prevents further lifecycle mutation.

## Durability

14. Journal sequence numbers are monotonic and remain valid when corrupted records are quarantined.
15. Journal records are integrity checked before replay.
16. Persistence adapters are replaceable; runtime orchestration does not depend on JSON implementation details.

## Architecture boundaries

```text
Control Plane
  RuntimeOrchestrator
        |
Execution Plane
  VNext orchestration -> AgentExecutor -> ToolExecutor -> Sandbox -> Registry
        |
Durability Plane
  ExecutionCommitCoordinator -> Journal / Store / Audit
        |
Recovery Plane
  Bootstrap -> Policy / Queue -> Lease -> Resume
```

`ExecutionStore` is a persistence adapter. `ExecutionCommitCoordinator` owns lifecycle mutation semantics. Recovery and normal execution must converge on that same coordinator.

## Verification matrix

| Invariant | Unit | Integration | Crash | Concurrency |
|---|---:|---:|---:|---:|
| State-machine validity | yes | yes | - | - |
| Canonical commit path | yes | yes | yes | - |
| Single audit event | yes | yes | yes | - |
| Reconciliation idempotency | yes | yes | yes | - |
| Lease ownership | yes | yes | - | yes |
| Journal sequence integrity | yes | yes | yes | - |
| Recovery resume | - | yes | yes | yes |
