# ADR 0007: Memory Is Correlated With Canonical Execution

## Status
Accepted

## Decision
Every durable memory write originating from an agent execution must carry the canonical `execution_id` and correlation metadata. Memory is an experience substrate, not a second execution state store.

## Consequences
Memory can explain what happened during an execution, support future retrieval and learning, and remain auditable without owning lifecycle transitions. Runtime remains authoritative for execution state.
