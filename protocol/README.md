# AIOS2 Protocol Layer

AIOS2 operates under **UASEP v3.4.0** (Universal Autonomous Engineering &
Self-Maintenance Protocol). The canonical normative documents live in the
protocol repository: `JoTalbot/UASEP` → `protocol/` (CORE, CONFORMANCE,
TASK_CONTRACT, OWNERSHIP, EVIDENCE_SCHEMA, EXECUTION, DRIFT_DETECTION, …).

This directory holds only AIOS2-specific norms that extend the protocol.

## Project-specific norms

1. **Batch-branch workflow.** One batch = one branch `batch/<n>-<slug>`.
   Never force-push shared branches; never rewrite merged history.
2. **One canonical path.** A single execution/persistence/recovery path.
   Parallel stores, execution state, or recovery mechanisms require an ADR in
   `.uasep/decisions/`.
3. **Regression coverage.** Every public-contract change ships with a
   regression test.
4. **Release discipline.** Versioning, tags, and releases flow through the
   automated release pipeline; do not hand-tag.
5. **Verification baseline.** The full suite is `python -m pytest tests -q`
   (232 tests at adoption); CI additionally runs the RBAC security matrix and
   production smoke checks.

## Precedence

Project-specific rules take precedence where they are stricter, provided they
stay compatible with the core UASEP safety and integrity requirements (see
`examples/ADOPTION.md` in the protocol repository).
