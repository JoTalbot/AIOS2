# Lessons Learned

Reusable knowledge collected from AIOS agent runs (migrated from
`.agents/memory/lessons_learned.md`, retained verbatim below).

## New architecture lessons

- Keep execution, persistence and recovery on one canonical path.
- Treat branch/PR state as durable coordination state for parallel agents.
- Contract changes require regression coverage.

## Format for new entries

### LESSON-XXXX

- Context:
- Problem:
- Root cause:
- Resolution:
- Evidence:
- Prevention:

## Rules

- Record reusable knowledge, not temporary notes.
- Link lessons to evidence when available.
- Avoid repeating failed approaches without a new hypothesis.
