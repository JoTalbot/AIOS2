# ADR 0013: Process-Level Concurrency Must Use the Same CAS Boundary

## Status
Accepted

Workers in separate processes must never rely on process-local locks for correctness. The distributed repository adapter is responsible for atomic conditional mutation. Process-level tests therefore validate that workers use the shared CAS contract; the reference in-process adapter is explicitly not presented as distributed coordination.
