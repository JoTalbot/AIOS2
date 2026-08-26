# AIOS New Architecture — Shared Agent Status

## Current phase
- Phase: isolated new architecture integration
- Target repository: `JoTalbot/AIOS2`
- Source architecture line: `JoTalbot/AIOS:new`

## Architecture
- vNext orchestration/execution path.
- Agent → Tool Registry → Permission Boundary → Tool Executor.
- Persistence, checkpoint, recovery, leases and audit contracts.

## Migration rule
AIOS2 is kept isolated from legacy/product-specific code. Only the new architecture and its required agent-operating documentation belong here.

## Handoff
Every agent updates this file before and after significant work. GitHub is the source of truth; do not rely on local chat history.
