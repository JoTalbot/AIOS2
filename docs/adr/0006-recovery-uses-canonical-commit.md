# ADR 0006: Recovery Uses the Canonical Commit Path

## Status
Accepted

## Decision
Recovery may discover and classify interrupted work, but it must mutate execution state through the same `ExecutionCommitCoordinator` used by normal execution.

## Consequences
Recovery cannot silently invent a parallel lifecycle. Reconciliation, retry, resume and terminal failure remain auditable and subject to version/fencing rules.
