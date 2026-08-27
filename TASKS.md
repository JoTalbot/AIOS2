# AIOS2 Tasks

## Batch 26

| ID | Task | Priority | Dependencies | Status |
|---|---|---:|---|---|
| B26-01 | Prove malformed journal records are quarantined inside the journal lock boundary | P0 | Batch 25 | DONE |
| B26-02 | Add project architecture documentation | P1 | None | DONE |
| B26-03 | Add testing/CI documentation | P1 | None | DONE |
| B26-04 | Add production-hardening roadmap | P1 | None | DONE |
| B26-05 | Add repository overview README | P1 | None | DONE |
| B26-06 | Maintain durable agent state across autonomous batches | P1 | None | IN_PROGRESS |

## Next candidates

| ID | Task | Priority | Dependencies | Status |
|---|---|---:|---|---|
| B27-01 | Audit journal sequence recovery after malformed/interleaved records | P0 | B26-01 | READY |
| B27-02 | Add concurrent append/read stress regression coverage | P0 | B26-01 | READY |
| B27-03 | Audit audit-log durability and locking | P0 | None | READY |
| B27-04 | Audit execution-store atomic rewrite/fsync semantics | P0 | None | READY |
| B27-05 | Audit lease expiry/fencing edge cases | P0 | None | READY |
| B27-06 | Review recovery RBAC negative paths | P1 | None | READY |
| B27-07 | Add operational diagnostics for pending commits | P1 | B27-01 | READY |
| B27-08 | Review API error handling and consistency | P1 | None | READY |
