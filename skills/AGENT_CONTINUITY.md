# Skill: Agent Continuity

Use when AIOS2 work is performed by multiple agents, machines, temporary
environments, or parallel branches.

## Startup
1. Read `AGENTS.md`, `.uasep/state/STATUS.md`, `.uasep/state/HANDOFF.md`, the
   applicable skill, and open work.
2. Fetch remote state and inspect ownership (`.uasep/state/OWNERSHIP_*.json`)
   before editing.
3. Never assume local files or processes from another agent exist.

## Durable handoff
- Commit code and declarative configuration atomically.
- Record checkpoints, artifacts, correlation IDs, and outcomes in durable
  project state.
- Write a concise handoff (completed work, next step, risks, validation) in
  `.uasep/state/HANDOFF.md` before stopping.

## Parallelism
- Scope ownership to files/subsystems via the ownership lease.
- Use idempotency and optimistic concurrency for side effects/state.
- Resolve integration conflicts against the current target branch; never
  rewrite shared history.
