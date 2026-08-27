# AIOS2

AIOS2 is an agent-oriented runtime with a separated cognition boundary, durable execution state, recovery, leases, fencing, audit, and an HTTP API.

## Architecture

- `cognition/` contains decision contracts and the cognition pipeline. It should remain an ephemeral decision boundary over runtime state.
- `runtime/` owns execution identity, persistence, checkpoints, recovery, leases, fencing, commit coordination, and audit.
- `kernel/` provides scheduling primitives.
- `api/` exposes the runtime through the service boundary and security/RBAC controls.
- `tests/` contains unit, integration, recovery, and security regression coverage.

## Reliability invariants

1. Execution state changes use versioned compare-and-set semantics.
2. Execution persistence and lease coordination can share one execution-scoped coordination lock.
3. Commit journal reads and writes are serialized by a dedicated journal lock.
4. Journal records carry checksums and malformed records are quarantined rather than silently accepted.
5. Recovery never applies a pending commit when the execution state or fencing token no longer permits that transition.
6. Audit events are emitted only for transitions that are actually applied or reconciled.

## Development

The repository is intentionally small and dependency-light. CI installs the runtime test dependencies and runs the complete `tests/` suite plus the recovery RBAC security matrix.

See `TESTING.md`, `ARCHITECTURE.md`, and `MIGRATION.md` for operational details.
