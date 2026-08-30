# AIOS2 Testing

## CI checks

GitHub Actions runs two required validation paths:

- `pytest tests -q` for the complete test suite.
- `pytest tests/test_recovery_rbac_matrix.py -q` for the recovery authorization/security matrix.

## Reliability testing

Recovery tests cover durable commit intent, store failure, stale concurrent transitions, fencing loss, journal integrity, and journal-lock coordination.

## Regression rule

A bug that can be reproduced should receive a regression test before the fix is considered complete. CI must remain green after the change.

## Local execution

Install the CI dependencies and run:

```text
python -m pytest tests -q
python -m pytest tests/test_recovery_rbac_matrix.py -q
```
