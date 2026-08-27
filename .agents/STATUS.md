# AIOS New Architecture — Shared Agent Status

## Current phase
- Phase: isolated new architecture hardening and Cognition/Runtime integration
- Branch: `batch/18-cognition-runtime-boundary`
- Latest integrated commit on `main`: `70bd953ab6c9a7a0ff9965a873a992e6c0131a80`
- Active work commit: `168dab761fc7c7584e50a37957a1705c38f24254`
- Active PR: pending creation

## Current architecture work
- vNext orchestration/execution path.
- Persistence, checkpoint, recovery, leases and audit contracts remain owned by Runtime.
- Cognition is an ephemeral decision boundary over the canonical `ExecutionContext`.
- Cognition components do not own stores, leases, checkpoints, recovery or tool execution.
- Execution identity and lifecycle remain runtime-owned; cognition receives and returns decisions without durable side effects.

## Batch 18 — Unified Cognition/Runtime Boundary
- Added provider-independent cognition contracts for Planner, Evaluator, Reflector and Learner.
- Added `CognitionRequest` and `CognitionDecision` bound to the canonical runtime `ExecutionContext`.
- Added `CognitionPipeline` that composes cognition stages without introducing a second execution state path.
- Added regression coverage proving one execution context flows through all cognition stages and runtime ownership is not duplicated.

## Validation
- Focused tests added in `tests/test_cognition_boundary.py`.
- GitHub Actions is authoritative; branch currently has no workflow run reported yet.
- Target: `main`.

## Next actions
1. Create PR for Batch 18 and wait for GitHub Actions validation.
2. Fix any CI failures only on the owning branch.
3. Merge only after required CI is green, then update this status on `main`.
4. Continue Batch 18 integration by adapting `VNextOrchestrator` to consume the cognition boundary without moving durable lifecycle ownership into Cognition.

## Rules
Every agent updates this file before and after significant work. GitHub is the source of truth; do not rely on local chat history.
