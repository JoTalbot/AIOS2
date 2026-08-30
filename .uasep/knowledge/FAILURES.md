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
