# Failed Approaches

## Format

- Date / Symptom / Evidence / Interpretation / Resolution

## Entries

(none recorded yet — record recurring failures here with evidence; do not convert unavailable evidence into success claims)

## Legacy note

The legacy `.agents/STATUS.md` drifted: it described batch 25 as current work
("Active PR: pending creation") while that content was already merged into
`main` and releases had reached v1.7.0. Root cause: status updates were manual
and not reconciled with git history after rebase merges. The UASEP state tree
replaces it; state must be rebuilt from factual history when it disagrees with
the repository.

## 2026-08-30 — Flaky concurrency test (observed during UASEP adoption)

- Symptom: `tests/test_recovery_concurrency_e2e.py::test_concurrent_recovery_workers_commit_one_terminal_effect` fails intermittently in repeated local runs (3 of ~10), passes in CI and on retry.
- Evidence: repeated full-suite runs on the adoption branch (zero Python changes) — failure appears and disappears with no code delta.
- Interpretation: timing-sensitive concurrency test; local sandbox load affects scheduling. Not related to the UASEP adoption changes.
- Resolution: none yet; recorded for a dedicated stabilization task.
- Related finding: the suite mutates tracked `data/*.jsonl` files (execution journal, operator audit), so local runs dirty the worktree and results can depend on accumulated state. Candidate fix: use tmp_path fixtures for journal/audit files in tests.
