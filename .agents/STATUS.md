# AIOS New Architecture — Shared Agent Status

## Current phase
- Phase: isolated new architecture integration
- Branch: `new`
- Source architecture line: `feat/vnext-tools-sandbox` at `8fd83f3`

## Active agents

| Agent | Task | Branch | Status |
|---|---|---|---|

## Completed
- Created dedicated `new` branch for new architecture.
- Moved current vNext/tools-sandbox architecture onto the dedicated line.
- Migrated general multi-agent operating instructions and reusable engineering skills from `JoTalbot/refund`.
- Preserved product-specific refund/returns skills outside AIOS.

## Current architecture work
- vNext orchestration/execution path.
- Agent → Tool Registry → Permission Boundary → Tool Executor.
- Persistence, checkpoint, recovery, leases and audit contracts.

## Next actions
1. Reconcile the new architecture with the current stable `main` only when required, without importing unrelated legacy work.
2. Run targeted and integration validation on `new`.
3. Keep all new-architecture implementation and documentation on `new`.
4. Record every handoff and architectural decision here or in docs/ADR.

## Rules
Every agent updates this file before and after significant work. GitHub is the source of truth; do not rely on local chat history.
