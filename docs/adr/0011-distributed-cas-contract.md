# ADR 0011: Distributed CAS Contract

## Status
Accepted

## Decision
A production execution repository must expose one transactional conditional mutation primitive. The primitive validates execution version and fencing generation and applies the lifecycle mutation in the same atomic boundary.

## Adapter rule
The reference repository in `runtime/distributed_execution_repository.py` is a contract model, not a claim that an in-process lock is distributed. Production adapters must map the invariant to a transactional database/KV primitive with atomic conditional writes.

## Failure rule
Version conflict and fencing conflict are normal concurrency outcomes and must be explicit, retryable/reconcilable signals rather than silent overwrites.
