# Persistence adapter boundary

The runtime must depend on persistence interfaces rather than file-format details.

## Current adapters

- `ExecutionStore`: file-backed execution repository.
- `ExecutionCommitCoordinator`: canonical lifecycle commit boundary.
- `ExecutionLeaseStore`: file-backed ownership lease.
- execution journal: file-backed recovery journal.

## Production boundary

Multi-machine deployment requires replaceable distributed implementations for:

- execution repository with conditional/transactional mutation;
- journal with durable monotonic sequencing and atomic append;
- lease service with compare-and-set ownership and fencing tokens.

The runtime orchestration layer must not change when these adapters are replaced.
