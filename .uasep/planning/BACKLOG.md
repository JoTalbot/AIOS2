# AIOS2 Backlog

Priority is dynamic. Re-score using user value, dependency readiness, risk, reversibility, and available evidence.

## P0 — Coordination
- [ ] AIOS2-UASEP-001: Adopt UASEP v3.4.0 and retire the legacy `.agents/` system. — in progress (branch `uasep/adopt-v3.4.0`)

## P1 — Runtime hardening
- [ ] AIOS2-RUNTIME-001: Verify whether batch 26–29 branch content is fully included in `main` (content-level check; ancestry unreliable under rebase merges).
- [ ] AIOS2-RUNTIME-002: Concurrent corruption and quarantine behavior (continues batches 26–29 themes).
- [ ] AIOS2-RUNTIME-003: Unified cognition/runtime boundary review.

## P2 — Operations
- [ ] AIOS2-OPS-001: Operational documentation debt in `docs/` (13 readiness/audit reports need consolidation).
- [ ] AIOS2-OPS-002: Branch hygiene — ~100 stale `batch/*` branches; reconcile merged content, then delete.

## Completed (reference)
- [x] Batches 1–25: crash consistency, leases, fencing, CAS transitions, execution commit journal, journal read coordination.
- [x] Release automation through v1.7.0 (semantic versioning, tag/release pipeline, post-release health, rollback verification).
