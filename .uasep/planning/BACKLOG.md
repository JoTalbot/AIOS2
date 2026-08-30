# AIOS2 Backlog

Priority is dynamic. Re-score using user value, dependency readiness, risk, reversibility, and available evidence.

## P0 — Coordination
- [x] AIOS2-UASEP-001: Adopt UASEP v3.4.0 and retire the legacy `.agents/` system. — VERIFIED: PR #93, CI run 33300118930, merged aadb7a8

## P1 — Runtime hardening
- [x] AIOS2-RUNTIME-001: Verify whether batch 26–29 branch content is fully included in `main`. — VERIFIED (batch 30): batch/27-recovery-quarantine-determinism is in `main`; batches 26 (quarantine coordination), 27-durability-fencing, 28 (lease durability), 29 (lease hardening) are NOT — their regression tests exist only on branches. Evidence: EV-AIOS2-BRANCHHYGIENE-2026-08-30.json
- [ ] AIOS2-RUNTIME-002: Integrate the verified-unmerged hardening batches (26 quarantine coordination → 27 durability fencing → 28 lease durability → 29 lease hardening); merge each only after green CI. Regression tests already exist on the branches.
- [ ] AIOS2-RUNTIME-003: Unified cognition/runtime boundary review.

## P2 — Test hygiene
- [x] AIOS2-TEST-001: Stabilize `test_concurrent_recovery_workers_commit_one_terminal_effect`. — VERIFIED (batch 30): deterministic lease-hold synchronization; 20/20 consecutive passes. Evidence: EV-AIOS2-TESTHYGIENE-2026-08-30.json
- [x] AIOS2-TEST-002: Stop tests from mutating tracked `data/*.jsonl` fixtures. — VERIFIED (batch 30): `runtime/paths.py` + `AIOS2_DATA_DIR` env (session tmpdir via `tests/conftest.py`); full suite leaves `data/` clean. Open question recorded: tracking policy for the `data/*.jsonl` files themselves. Evidence: EV-AIOS2-TESTHYGIENE-2026-08-30.json

## P2 — Operations
- [ ] AIOS2-OPS-001: Operational documentation debt in `docs/` (13 readiness/audit reports need consolidation).
- [x] AIOS2-OPS-002: Branch hygiene — 38 patch-equivalent branches deleted (git cherry evidence, incl. merged `uasep/adopt-v3.4.0`); ~59 remain, of which batches 26/27/28/29 carry real unmerged work (see AIOS2-RUNTIME-002), the rest pending review. Evidence: EV-AIOS2-BRANCHHYGIENE-2026-08-30.json

## Completed (reference)
- [x] Batches 1–25: crash consistency, leases, fencing, CAS transitions, execution commit journal, journal read coordination.
- [x] Release automation through v1.7.0 (semantic versioning, tag/release pipeline, post-release health, rollback verification).
