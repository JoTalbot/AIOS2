# AIOS

**AI Operating System for Autonomous Agents**

AIOS is a modular operating-system architecture for autonomous AI agents. It provides the foundations for persistent agent execution: planning, orchestration, tools, memory, communication, security, lifecycle management, recovery, audit and learning.

The project is designed as a general-purpose foundation, not a product-specific application. Agents should be able to operate as durable software processes: observe their environment, plan and execute work, use controlled external capabilities, remember experience, evaluate outcomes, recover after interruption and improve future behavior.

## Core loop

`Observe → Execute → Remember → Evaluate → Optimize → Improve`

## Architecture

- Kernel — scheduling, context, memory and lifecycle primitives
- Agents — planning, execution and collaboration
- Cognition — reflection, evaluation and learning
- Communication — agent messaging and coordination
- Security — capabilities, permissions, sandboxing and audit
- Tools — typed, controlled external actions
- LLM — model/provider abstraction
- Runtime — durable execution, orchestration and recovery

## New architecture

AIOS2 is the isolated new-architecture continuation of `JoTalbot/AIOS`. The current architecture focuses on a canonical execution path with durable state, commit/journal/audit semantics, checkpointing, recovery and lease/fencing ownership.

See [`PROJECT.md`](PROJECT.md) for the project purpose and positioning, and [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the architecture contract.

## Agent development

Work is performed by multiple AI agents, machines and parallel branches. GitHub is the source of truth. Before changing code, agents must read `AGENTS.md`, `.agents/STATUS.md` and relevant skills. Every substantial step requires validation, durable handoff/status and a commit.
