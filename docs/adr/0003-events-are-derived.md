# ADR 0003: Events Are Derived From Durable State

## Status
Accepted

## Decision
The durable execution state and canonical commit journal are authoritative. EventBus messages are derived notifications.

## Consequences
A consumer must never infer that an execution mutation became durable merely because an event was observed. Event publication needs explicit delivery/retry semantics and correlation to the canonical execution commit.
