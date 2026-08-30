# AIOS2 Fault Injection Plan

## Goal
Validate recovery guarantees under controlled failures.

## Scenarios

### Persistence failures
- interrupted atomic write
- invalid JSON recovery path
- temporary file cleanup

### Concurrency failures
- optimistic version conflict
- stale fencing token rejection
- competing state transitions

### Recovery validation
- resume after interrupted execution
- audit consistency after recovery
- no lost execution state

## Completion criteria
- Each scenario has a regression test.
- Failures are deterministic.
- CI executes the recovery suite.
