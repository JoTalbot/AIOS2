# AIOS — Project Purpose

## What AIOS is

AIOS is a modular **AI Operating System architecture for autonomous agents**. It is intended to provide the runtime, coordination, memory, tools, security, lifecycle, recovery, and learning foundations that let autonomous agents operate as persistent software processes rather than isolated model calls.

AIOS is not a single chatbot or a product-specific workflow. It is an extensible operating-system-like foundation in which agents can plan, execute actions, use controlled tools, communicate, remember experience, reflect on outcomes, recover from interruption, and improve future behavior.

## Original positioning

The original AIOS concept is preserved: a general-purpose operating system architecture for autonomous AI agents, with modular subsystems and an execution loop of:

`Observe → Execute → Remember → Evaluate → Optimize → Improve`

The new architecture keeps that goal while making execution durable, recoverable, secure, auditable, and suitable for long-running autonomous work.

## Core layers

- **Kernel** — scheduling, context, memory, lifecycle primitives.
- **Agents** — planning, execution, lifecycle, collaboration/swarm behavior.
- **Cognition** — reflection, evaluation, reasoning and learning loops.
- **Communication** — agent-to-agent messaging and coordination.
- **Security** — capabilities, permissions, sandboxing and audit.
- **Tools** — controlled external actions through a typed tool boundary.
- **LLM** — provider/model abstraction.
- **Runtime** — durable execution, orchestration, persistence, checkpointing, recovery and restart.

## New architecture execution flow

`Intent → Planner → Execution/Orchestration → Agent → Tool Boundary → Memory/State → Reflection → Result`

The execution layer is designed around a canonical execution identity and lifecycle. Persistent state changes, audit, journal/recovery and ownership/lease semantics must converge on one authoritative execution path.

## Long-term goal

Build a general autonomous-agent operating system in which agents can run continuously, safely and recoverably; coordinate with other agents; interact with the outside world through controlled capabilities; preserve state across restarts; learn from experience; and evolve their strategies over time.

## Scope of AIOS2

AIOS2 is the isolated continuation of the new architecture work from `JoTalbot/AIOS`. Product-specific legacy functionality is intentionally excluded. The repository should contain the new architecture, its required tests, documentation, agent operating instructions, skills and reusable engineering knowledge.
