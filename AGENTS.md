# AIOS2 Agent Contract

This repository operates under **UASEP v3.4.0** — a runtime-free, repository-native
protocol. Rules and durable state live in the repository; chat history is temporary
context. The canonical protocol specification lives in `JoTalbot/UASEP`
(`protocol/`); AIOS2-specific norms live in `protocol/README.md`.

## Before every task

1. Read this file.
2. Restore context from `.uasep/state/STATUS.md`, `PROJECT_STATE.md`, `HANDOFF.md`,
   and `state.json`.
3. Read `.uasep/planning/BACKLOG.md` and the applicable `skills/` workflow.
4. Inspect the actual repository, current branch, and recent history.
5. Create or restore the task contract (`.uasep/state/TASK_*.json`) and claim
   ownership (`.uasep/state/OWNERSHIP_*.json`) before consequential edits.
6. Check active ownership and open work before touching shared files.

## Execution rules

- **Batch-branch workflow:** one batch = one branch `batch/<n>-<slug>`; small
  atomic commits; never force-push shared branches; never rewrite merged history.
- **Ownership:** stay inside your declared write set; never overwrite another
  agent's active work; overlapping claims are coordinated or serialized.
- **One canonical path:** a single execution/persistence/recovery path. Parallel
  stores, execution state, or recovery mechanisms require an ADR in
  `.uasep/decisions/`.
- **Regression coverage:** every public-contract change ships with a regression
  test.
- **Research first:** investigate existing implementation and documentation
  before architectural changes; record the decision as an ADR.
- **Honest verification:** verify before claiming completion; record evidence in
  `.uasep/evidence/` proportional to risk. Truth statuses: `VERIFIED`,
  `PARTIALLY_VERIFIED`, `UNKNOWN`, `FAILED` — never promote `UNKNOWN` to
  `VERIFIED`; never claim a test, CI result, commit, or push without evidence.
- GitHub is the source of truth; local files and chat memory are not.

## Handoff

Before stopping, update `.uasep/state/HANDOFF.md` and `STATUS.md` with the exact
current step, completed work, unverified work, blockers, changed files/commits,
evidence, and the recommended next action. A fresh agent must be able to continue
from repository state alone.

## Definition of done

A task is done only when its acceptance criteria are satisfied, evidence is
recorded, and durable state is updated. If verification is unavailable, label
the result `UNKNOWN`, not `VERIFIED`.

## Language

Protocol artifacts (state, planning, knowledge, evidence, decisions, skills) are
written in English for a single convention; the previous Russian instructions
were migrated and superseded by this contract (see
`.uasep/decisions/DECISION-0002`).
