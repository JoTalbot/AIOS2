# AIOS2 Shared Agent Status

## Current phase
- Phase: v2 architecture bootstrap
- Repository: `JoTalbot/AIOS2`
- Source: `JoTalbot/AIOS` branch `new`

## Completed
- AIOS2 confirmed empty before bootstrap.
- Initialized v2 agent instructions and protocol.
- Initialized architecture documentation.

## Migration target
- vNext kernel/runtime
- execution lifecycle, persistence, checkpoint and recovery
- scheduler/orchestrator
- tool registry, sandbox and permission boundary
- memory/persistence
- security, observability and integration
- reusable agent skills, plans and architecture docs

## Next
1. Migrate the complete validated vNext implementation from AIOS `new`.
2. Migrate agent skills, plans and reusable documentation from the old project repository where applicable.
3. Remove obsolete legacy-only code rather than carrying duplicate architecture forward.
4. Run tests and reconcile contracts.

## Rule
AIOS2 is the clean v2 project. New architecture work happens here; AIOS remains the historical/source project.
