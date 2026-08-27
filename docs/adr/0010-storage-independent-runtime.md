# ADR 0010: Storage-Independent Runtime

## Status
Accepted

## Decision
Runtime orchestration depends on a stable `ExecutionRepository` protocol. Storage adapters implement that contract; no orchestration logic may depend on JSON/file layout or adapter-specific persistence APIs.

## Production consequence
The file-backed store remains useful for development and single-node operation. A distributed implementation can replace it while preserving execution identity, version CAS, fencing and recovery semantics.
