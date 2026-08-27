# ADR 0012: Fencing Takeover Is a Persistence Invariant

## Status
Accepted

A lease takeover is not sufficient by itself. The new fencing generation must be carried into the same atomic persistence boundary that validates execution version. An old worker presenting the previous generation must be rejected even when its version is otherwise current.

The reference test models the invariant and documents the required behavior for a real distributed adapter.
