# AIOS2 Operator Runbook

## Start

Local:

```bash
python start.py
```

Docker:

```bash
docker compose up -d
```

## Validation

```bash
pytest tests -q
```

Runtime checks:

- `/health`
- `/ready`
- `/diagnostics`

## Recovery

Use recovery endpoints only with authenticated operator access.

## Operations

Check logs, diagnostics and CI results before production changes.
