# P0 Completion Checklist

## Execution correctness
- [x] Canonical lifecycle commit coordinator.
- [x] Monotonic execution version.
- [x] Optimistic CAS at persistence boundary.
- [x] Lease fencing carried into mutation.
- [x] Stale version rejected.
- [x] Stale fencing generation rejected.
- [x] Recovery uses canonical commit path.
- [x] Storage-independent repository protocol.
- [x] Distributed CAS/fencing contract reference implementation.

## Remaining validation before P0 is declared complete
- [ ] Run the full test suite in GitHub Actions and fix every failure.
- [ ] Complete fault-injection matrix for every journal/store/audit ordering window.
- [ ] Verify two-process race behavior, not only in-process concurrency.
- [ ] Implement/select a real transactional distributed adapter.
- [ ] Prove recovery takeover with a fenced old worker.
- [ ] Verify event publication is derived only from committed state.

P1 must not be declared complete until these P0 gates pass.
