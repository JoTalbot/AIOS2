# DECISION-0001: Adopt UASEP v3.4.0 as the AIOS2 coordination layer

Date: 2026-08-30 · Status: ACCEPTED

## Context

AIOS2 used a homegrown agent protocol (`.agents/` v1.0: status file, protocol
rules, skills, memory). It worked, but drifted: the status file described
merged work as current, and there was no evidence model, ownership leases, or
truth statuses. UASEP v3.4.0 (JoTalbot/UASEP) provides exactly these as a
runtime-free, repository-native protocol.

## Decision

Adopt UASEP v3.4.0. The canonical normative documents remain in the UASEP
repository; AIOS2 keeps only project-specific norms (`protocol/README.md`).

## Consequences

- Agent coordination artifacts live under `.uasep/` (state, planning,
  knowledge, evidence, decisions) plus `skills/` and `AGENTS.md`.
- `manifest.yaml` declares `runtime: NONE` in the UASEP sense (no UASEP
  runtime required); AIOS2's own runtime is the product, unaffected.
- Domain rules (one canonical execution/persistence/recovery path, regression
  tests for public contracts, ADR requirement) carry over unchanged.
- Adoption findings are recorded in `.uasep/knowledge/UASEP_ADOPTION_FINDINGS.md`
  and feed back to the UASEP protocol as a candidate maintenance batch.
