# P0 Final Gate

P0 is complete only when all of the following are true on `canonical-execution`:

- canonical execution commit path is the only lifecycle mutation path;
- version CAS rejects stale observations;
- fencing rejects stale owners;
- recovery uses the canonical commit boundary;
- repository access is storage-independent;
- shared-process transactional CAS is covered;
- crash/retry windows are covered by deterministic tests;
- process-level contention is covered;
- committed-state event ordering is covered;
- the full GitHub Actions Tests + Lint + Security workflow is green on the final commit;
- no remaining production runtime path bypasses the canonical repository/commit boundary.

A green subset of tests is not sufficient to declare P0 complete.
