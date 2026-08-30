# UASEP v3.4.0 Adoption Findings

Date: 2026-08-30 · Adopter: AIOS2 · Recorded during the first real-world
adoption of UASEP on a project other than the protocol repository itself.

These findings should feed a future UASEP maintenance batch (candidate M63).

## F1 — `manifest.schema.json` cannot describe runtime projects

The schema requires `runtime: {"const": "NONE"}`. AIOS2 *is* an autonomous
runtime, so the field is false as a project description. The intended meaning
is "no UASEP runtime is required", but the field name says "runtime".

**Impact:** an adopter must either violate the schema or write a semantically
false statement.

**Recommendation (v3.5):** rename to `uasep_runtime` (or document the field as
"UASEP runtime required: NONE") and allow a free-form `project_runtime`
descriptor for projects whose product is a runtime.

## F2 — Adoption guidance pushes adopters to duplicate the normative spec

`examples/ADOPTION.md` says "Add or adapt … `protocol/` for normative rules".
Copying all 17 normative documents into every adopter creates a versioning
nightmare: the protocol would fork across repositories with no migration path.

**Resolution taken here:** AIOS2 keeps a slim `protocol/README.md` that
references the canonical UASEP repository and adds only project-specific norms.

**Recommendation (v3.5):** add explicit guidance distinguishing "reference the
canonical protocol" from "copy the protocol", and version the reference
(`protocol_version` in the manifest already covers this).

## F3 — No migration path for legacy agent systems

AIOS2 arrived with a working pre-UASEP agent system (`.agents/` v1.0: status,
protocol, roles, skills, memory). UASEP has no migration guide: what maps where
(status → `.uasep/state/`, memory → `knowledge/`, skills → `skills/`, rules →
AGENTS.md), what to do with the legacy directory, or how to preserve history.

**Recommendation (v3.5):** add a `skills/LEGACY_MIGRATION.md` workflow to the
protocol repository.

## F4 — The v3.4.0 manifest is less expressive than what adopters already had

AIOS2's legacy manifest (v1.0) recorded validation requirements, current
execution focus, next focus queue, and operative rules. The v3.4.0 schema
(with `additionalProperties: false`) has no place for any of that; the
information has to be pushed into free-text arrays of `state.json`.

**Recommendation (v3.5):** either allow an optional project-specific extension
object, or document where validation/focus/rules should live in the canonical
artifact set.

## F5 — No branch-lifecycle rules; adopters accumulate branch debt

AIOS2 has ~100 stale `batch/*` branches. UASEP's ownership model covers files
and write sets but says nothing about branch lifecycle (when to delete a merged
branch, how rebase merges break ancestry checks, how to verify "is this branch
already in main?").

**Recommendation (v3.5):** add branch hygiene rules to `protocol/OWNERSHIP.md`
or `protocol/EXECUTION.md`, including the rebase-merge ancestry caveat.

## F6 — Legacy state drift confirms the protocol's own diagnosis

The legacy status file described merged work as current ("Active PR: pending
creation" for batch 25, whose content is already on `main`). This is exactly
the drift UASEP's durable-state model exists to prevent — evidence that the
problem is real, and that rebuilding state from git facts (not from the stale
status file) must be the documented adoption procedure.

## F7 — Conformance tests are not portable

UASEP's 56-test conformance suite is repository-specific (paths and invariants
hard-coded to the UASEP repo). An adopter cannot reuse it to check its own
durable artifacts. AIOS2 validated its JSON records against the UASEP schemas
manually, one-off.

**Recommendation:** package a reusable "conformance kit" (schema validation +
minimal artifact checks) that adopters can drop into `tests/`.

## Positive results

- The adoption flow itself (discover → baseline → migrate → verify → evidence)
  worked and caught real drift in the legacy state.
- Schema validation of `state.json`, task, ownership, and evidence records
  against the published JSON schemas succeeded with no schema changes needed
  for the core artifact set.
- The evidence model (baseline run recorded before touching anything) directly
  enabled honest before/after comparison.
