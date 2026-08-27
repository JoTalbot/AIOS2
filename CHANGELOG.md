# Changelog

## Unreleased

### Reliability
- Coordinated execution-store persistence with the configured execution lock.
- Coordinated execution commit journal reads and writes with a dedicated journal lock.
- Added regression coverage for crash recovery, fencing loss, stale transitions, journal locking, and corruption quarantine.

### Documentation
- Added repository overview, architecture, testing, roadmap, and task backlog documentation.

## Batch 24

- Unified the execution persistence coordination lock and closed the split-lock race between state CAS and lease operations.

## Batch 25

- Hardened journal read coordination and removed nested journal-lock acquisition from `_mark()`.
