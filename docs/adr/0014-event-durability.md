# ADR 0014: Events Are Derived From Committed State

## Status
Accepted

Lifecycle events must never become a second mutable source of execution truth. A transition is observable as committed only after the canonical persistence boundary accepts it. Recovery may replay/reconcile durable records, but must not emit an event for a transition that was never durably committed.

The current audit log is therefore treated as a derived durability record. A future external event bus must preserve the same ordering/idempotency contract and include execution id plus committed version/fencing generation.
