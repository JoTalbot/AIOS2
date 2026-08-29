# AIOS2

AIOS2 is an autonomous AI runtime platform focused on agent execution, API control, runtime orchestration and recovery workflows.

## Architecture

Main components:

- `kernel/` — core runtime and orchestration logic
- `runtime/` — execution environment
- `cognition/` — intelligence and decision modules
- `api/` — service interfaces
- `tests/` — regression and integration coverage
- `.github/workflows/` — CI automation

## Requirements

- Python 3.11+
- pip

## Install

```bash
python -m pip install -U pip pytest pytest-asyncio fastapi pydantic httpx
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
