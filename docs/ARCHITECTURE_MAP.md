# AIOS2 Architecture Map

## Canonical flow

```text
Intent / API
    ↓
Agent + Cognition
    ↓
RuntimeOrchestrator
    ↓
AutonomousExecutionLoop
    ↓
ExecutionContext + StateMachine
    ↓
ExecutionCommitCoordinator
    ├── Journal
    ├── ExecutionStore
    └── ExecutionAudit
    ↓
Committed execution state
    ↓
Derived events / Memory experience
```

## Capability flow

```text
Agent / Operator
    ↓
Capability Request
    ↓
Policy Engine
    ↓
Tool Registry / Recovery / Operator API
    ↓
Sandboxed action
    ↓
Audit correlated to execution
```

## Recovery flow

```text
Bootstrap
  ↓
Journal discovery
  ↓
Reconciliation
  ↓
Recovery policy
  ↓
Lease acquisition
  ↓
Fencing generation
  ↓
Canonical commit
  ↓
Resume / retry / terminal outcome
```

## Cognition flow

```text
Goal
 ↓
Planner
 ↓
Execution intent
 ↓
Runtime
 ↓
Observation/result
 ↓
Evaluator + Reflector
 ↓
Memory
 ↓
Replan / Learn
```

## Non-negotiable boundaries

1. No second durable execution authority.
2. No lifecycle write that bypasses the canonical commit boundary.
3. No stale worker mutation after fencing takeover.
4. No cognition-owned recovery state machine.
5. No provider-specific LLM contract leaking into agent code.
6. No memory subsystem owning execution lifecycle.
7. No event consumer treated as authoritative execution state.
