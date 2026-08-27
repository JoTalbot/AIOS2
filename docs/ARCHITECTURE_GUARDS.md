# Architecture Guards

These rules are intended to become machine-checked CI invariants.

## Execution authority

- Runtime lifecycle mutations MUST converge on `ExecutionCommitCoordinator`.
- `ExecutionStore` is not a second lifecycle authority.
- Setup/materialization persistence must be distinguishable from runtime lifecycle mutation.

## Concurrency

- Every mutable execution has a monotonic version.
- Lifecycle mutation must use optimistic compare-and-set semantics.
- A worker mutation must carry the lease fencing generation.
- The persistence boundary, not only the checkpoint layer, rejects stale fencing generations.

## Recovery

- Recovery is idempotent.
- Recovery uses the same lifecycle commit path as normal execution.
- A recovered execution cannot be resumed by a stale owner.

## Events

- Durable execution state is authoritative.
- Events are derived notifications and must not become a second state store.
- Event publication must not silently turn an uncommitted mutation into an observed success.

## Agent boundaries

- Cognition decides what/why.
- Runtime decides how/when and guarantees durability.
- Agents cannot bypass tool/capability boundaries.

## Persistence

- Runtime depends on repository interfaces, not file formats.
- File-backed adapters are development/single-node implementations.
- Distributed adapters must preserve execution, version, journal and fencing contracts.
