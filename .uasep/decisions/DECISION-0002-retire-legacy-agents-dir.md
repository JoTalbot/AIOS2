# DECISION-0002: Retire the legacy .agents/ directory

Date: 2026-08-30 · Status: ACCEPTED

## Context

Two parallel agent systems (`.agents/` v1.0 and `.uasep/` v3.4.0) would create
exactly the dual-source drift the protocol exists to prevent.

## Decision

Migrate all live content and remove `.agents/`:

- `.agents/STATUS.md` → `.uasep/state/STATUS.md` (rebuilt from git facts)
- `.agents/protocol.md` → superseded by `AGENTS.md` + UASEP v3.4.0
- `.agents/memory/lessons_learned.md` → `.uasep/knowledge/LESSONS.md`
- `.agents/skills/{agent-continuity,coding,research,testing}` → `skills/`
- `.agents/roles/architect.md` → folded into `AGENTS.md` responsibilities

## Consequences

- Single coordination system; git history preserves the legacy tree.
- References in `AGENTS.md` and `docs/UASEP_INTEGRATION.md` updated.
