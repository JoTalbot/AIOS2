# ADR 0005: Execution CAS and Fencing at the Persistence Boundary

## Status
Accepted

## Decision
Every mutable execution lifecycle mutation carries both an expected execution version and the worker fencing generation. Persistence must validate both atomically with the mutation.

## Rationale
Checking ownership before persistence leaves a race window in which a worker can be fenced after its check but before its write. CAS versioning prevents concurrent state transitions; fencing prevents an old owner from mutating after lease takeover.

## Required invariant

`mutation succeeds ⇔ expected_version == current_version AND fencing_generation == current_generation`

The check and mutation belong to the same atomic persistence operation.
