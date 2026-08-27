# UASEP Integration

AIOS2 is an existing project managed through the UASEP autonomous development protocol.

## Operating model

UASEP provides the host-neutral development lifecycle: discovery, bootstrap/resume, planning, execution, verification, evidence, checkpointing, recovery, and continued work. AIOS2 remains responsible for its own domain architecture and runtime contracts.

## Repository truth

- GitHub is the source of truth.
- `AGENTS.md` and `.agents/STATUS.md` are mandatory local project instructions.
- `.uasep/manifest.yaml` records the UASEP project state and current execution focus.
- Existing AIOS2 execution, persistence, lease, recovery, and audit paths remain canonical. UASEP must not introduce a competing execution store or recovery mechanism without an explicit ADR.

## Resume protocol

A new agent must inspect `AGENTS.md`, `.agents/STATUS.md`, relevant skills, the current GitHub state, open work, and `.uasep/manifest.yaml` before changing code. It then selects the highest-value unblocked work, applies the repository's ownership rules, runs targeted validation, and updates status after the atomic step.

## Current continuation point

Batch 25 hardens journal read/write coordination. After its owning work and CI are complete, continue with concurrent corruption/quarantine behavior and operational documentation debt, while preserving the existing execution/persistence/recovery path.
