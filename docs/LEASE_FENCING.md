# Execution lease fencing

A lease identifies the current execution owner and a monotonically increasing fencing generation.

## Contract

- A fresh acquisition after expiry increments `fencing_token`.
- Renewal by the same owner keeps the current fencing generation.
- A stale owner with an older token is no longer authoritative after takeover.
- Mutation-capable adapters must validate owner + fencing generation before publishing state.

The current file-backed lease store exposes `owns_token()` for this boundary. The runtime should carry the lease token through recovery/checkpoint context as the distributed adapters are introduced.

Fencing is required because a worker can pause past its TTL and resume after another worker has legitimately taken ownership. An owner-id check alone cannot distinguish that stale worker from the current generation.
