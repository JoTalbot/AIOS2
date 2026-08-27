# ADR 0002: Cognition vs Runtime Boundary

## Status
Accepted

## Decision
Cognition determines goals, plans, reasoning, evaluation and learning. Runtime provides scheduling, durability, lifecycle, recovery, ownership and execution guarantees.

## Rule
`Cognition decides WHAT/WHY; Runtime guarantees HOW/WHEN.`

## Consequences
Planner/reflection/learning components must not implement their own durable execution state or recovery system. They use the canonical runtime execution context and commit path.
