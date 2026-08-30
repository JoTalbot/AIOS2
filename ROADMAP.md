# AIOS2 Roadmap

## Current phase: production hardening

1. Complete journal concurrency and corruption-recovery hardening.
2. Audit execution persistence, lease/fencing, and recovery for remaining durability races.
3. Strengthen critical-path regression and integration coverage.
4. Close API recovery/security gaps discovered by audit.
5. Improve observability and operational diagnostics.
6. Document stable runtime contracts before broader feature expansion.

Feature work should not outrun the execution and recovery invariants.
