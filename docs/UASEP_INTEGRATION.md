# UASEP Integration

AIOS2 operates under UASEP v3.4.0 (see `.uasep/manifest.yaml`). This document
supersedes the earlier v1.0 integration notes.

## Operating model

UASEP provides the host-neutral development lifecycle: discovery, bootstrap,
planning, execution, verification, evidence, checkpointing, recovery, and
handoff — as repository artifacts only. AIOS2 remains responsible for its own
domain architecture and runtime contracts.

## Repository truth

- GitHub is the source of truth.
- `AGENTS.md` is the mandatory agent contract.
- `.uasep/state/` holds durable status and handoff; `.uasep/planning/` the
  backlog; `.uasep/knowledge/` decisions, failures, lessons, and adoption
  findings; `.uasep/evidence/` verification records; `.uasep/decisions/` ADRs.
- Existing AIOS2 execution, persistence, lease, recovery, and audit paths
  remain canonical. UASEP must not introduce a competing execution store or
  recovery mechanism without an explicit ADR.

## Resume protocol

A new agent reads `AGENTS.md`, restores `.uasep/state/`, checks open work and
ownership, selects the highest-value unblocked task from
`.uasep/planning/BACKLOG.md`, claims ownership, executes, verifies, records
evidence, and updates state.

## Historical note

The legacy `.agents/` system (protocol v1.0) was retired on 2026-08-30; its
content was migrated into the UASEP artifact tree. Its status file had drifted
(recorded batch 25 as current although its content was already merged and
releases had reached v1.7.0) — a concrete example of the drift the durable
state model prevents. See `.uasep/decisions/` and
`.uasep/knowledge/UASEP_ADOPTION_FINDINGS.md`.
