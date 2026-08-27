# ADR 0001: Canonical Execution Authority

## Status
Accepted

## Decision
`RuntimeOrchestrator` and its execution loop form the single durable execution authority. Lifecycle mutations converge on `ExecutionCommitCoordinator`. Journal, persistence and audit are adapters around that canonical commit boundary.

## Why
A second scheduler, store or recovery state machine creates split-brain execution state and makes crash recovery ambiguous.

## Consequences
Normal execution and recovery share lifecycle semantics. Persistence implementations can be replaced without rewriting orchestration. Direct lifecycle writes become architectural violations except for explicit setup/materialization paths.
