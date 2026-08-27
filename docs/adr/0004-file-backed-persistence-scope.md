# ADR 0004: File-backed Persistence Scope

## Status
Accepted

## Decision
File-backed execution/journal/lease adapters are development and controlled single-node implementations. The runtime contracts must not depend on their storage format.

## Production requirement
Multi-machine deployment requires distributed implementations preserving CAS/versioning, durable journal ordering, lease ownership and fencing-token rejection.
