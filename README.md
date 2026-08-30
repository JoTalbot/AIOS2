# AIOS2

AIOS2 is an agent-oriented runtime with a separated cognition boundary, durable execution state, recovery, leases, fencing, audit, and an HTTP API.

## Architecture

- `cognition/` contains decision contracts and the cognition pipeline. It should remain an ephemeral decision boundary over runtime state.
- `runtime/` owns execution identity, persistence, checkpoints, recovery, leases, fencing, commit coordination, and audit.
- `kernel/` provides scheduling primitives.
- `api/` exposes the runtime through the service boundary and security/RBAC controls.
- `tests/` contains unit, integration, recovery, security, and protocol conformance coverage.
- `.github/workflows/` — CI automation

## Reliability invariants

1. Execution state changes use versioned compare-and-set semantics.
2. Execution persistence and lease coordination can share one execution-scoped coordination lock.
3. Commit journal reads and writes are serialized by a dedicated journal lock.
4. Journal records carry checksums and malformed records are quarantined rather than silently accepted.
5. Recovery never applies a pending commit when the execution state or fencing token no longer permits that transition.
6. Audit events are emitted only for transitions that are actually applied or reconciled.
7. Autonomous-loop state updates across awaits go through version-checked transitions: a stale state copy never overwrites a newer durable write.

## Requirements

- Python 3.11+
- pip

## Install

```bash
python -m pip install -U pip pytest pytest-asyncio fastapi pydantic httpx jsonschema pyyaml
```

## Validation

Run the complete test suite:

```bash
pytest tests -q
```

## Runtime Validation

Available checks:

- `/health` — service availability
- `/ready` — readiness validation
- `/diagnostics` — operational diagnostics

## CI

GitHub Actions validates regression tests, security checks and production smoke validation on repository changes.

## Release Status

AIOS2 has completed the production readiness validation cycle.

Completed areas:

- runtime stability
- autonomous execution flows
- API hardening
- recovery validation
- security checks
- regression coverage

The project is prepared for final deployment validation.
