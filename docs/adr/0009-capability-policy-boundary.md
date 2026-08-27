# ADR 0009: Unified Capability and Policy Boundary

## Status
Accepted

## Decision
Authorization decisions use a common model: `Subject`, `Action`, `Resource`, `Context`, `Policy`, `Decision`. Tools, recovery, operators and future agent capabilities use the same policy boundary.

## Consequences
Security rules are expressed consistently, denied operations can be audited with the same correlation model, and new capabilities do not require a separate authorization architecture.
