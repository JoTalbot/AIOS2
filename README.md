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

## Development

Requirements:

- Python 3.11+
- pip

Install test dependencies:

```bash
python -m pip install -U pip pytest pytest-asyncio fastapi pydantic httpx
```

Run tests:

```bash
pytest tests -q
```

## CI

GitHub Actions runs validation, regression tests and security checks on pushes and pull requests.

## Status

The project is under active development. Current focus areas:

- runtime stability
- autonomous execution flows
- API hardening
- recovery and security validation
