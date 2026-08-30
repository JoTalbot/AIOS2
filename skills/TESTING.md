# Skill: Testing

Reusable validation workflow for AIOS2 changes.

## Steps
1. Identify affected contracts and failure modes.
2. Add focused regression tests first.
3. Run targeted tests (`python -m pytest tests/<file> -q`).
4. Run the full suite (`python -m pytest tests -q`) and the relevant security
   validation (`tests/test_recovery_rbac_matrix.py`, production smoke).
5. Record failures and root causes in `.uasep/knowledge/FAILURES.md`.
6. Improve the test strategy when a new failure class is discovered.
7. Record evidence in `.uasep/evidence/` proportional to risk.
