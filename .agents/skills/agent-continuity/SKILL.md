---
name: agent-continuity
description: Use when AIOS work is performed by multiple agents, machines, temporary environments, or parallel branches. Establishes durable state, handoff, conflict control and Git delivery.
---
# Agent Continuity

## Startup
1. Read `AGENTS.md`, `.agents/STATUS.md`, relevant skills and open work.
2. Fetch remote state and inspect ownership before editing.
3. Never assume local files or processes from another agent exist.

## Durable handoff
- Commit code and declarative configuration atomically.
- Record checkpoints, artifacts, correlation IDs and outcomes in durable project state where applicable.
- Write a concise handoff with completed work, next step, risks and validation.

## Parallelism
- Scope ownership to files/subsystems.
- Use idempotency and optimistic concurrency for side effects/state where applicable.
- Resolve integration conflicts against the current target branch; never rewrite shared history.
