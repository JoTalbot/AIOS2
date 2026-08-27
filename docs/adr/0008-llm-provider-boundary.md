# ADR 0008: LLM Provider Boundary

## Status
Accepted

## Decision
Agents and cognition consume a provider-independent inference contract. Provider adapters own vendor-specific authentication, request formatting, streaming, retry and model details.

## Consequences
AIOS can switch between hosted and local models without changing execution or cognition contracts. Usage, latency, cost and model identity remain correlated to the canonical execution.
