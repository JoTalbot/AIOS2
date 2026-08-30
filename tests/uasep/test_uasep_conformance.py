"""UASEP conformance kit — portable checks for adopting repositories.

Validates the repository's UASEP artifacts (manifest, durable state, task,
ownership, and evidence records) against the schema snapshots shipped with
this kit. Copy `tests/uasep/` from the UASEP protocol repository; see
kit/README.md there for usage and versioning.
"""
import json
from pathlib import Path

import pytest

try:
    import jsonschema
except ImportError:  # pragma: no cover
    jsonschema = None

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

HERE = Path(__file__).resolve().parent
SCHEMAS = HERE / "schemas"

_REASONS = []
if jsonschema is None:
    _REASONS.append("jsonschema")
if yaml is None:
    _REASONS.append("pyyaml")
requires_schemas = pytest.mark.skipif(
    _REASONS, reason=f"schema validation dependencies missing: {', '.join(_REASONS)}"
)


def _find_repo_root() -> Path:
    """Walk up from this file until the UASEP manifest is found."""
    for candidate in [HERE, *HERE.parents]:
        if (candidate / ".uasep" / "manifest.yaml").is_file():
            return candidate
    pytest.fail("UASEP conformance kit: no .uasep/manifest.yaml found in this repository")


ROOT = _find_repo_root()
VALIDATOR = jsonschema.Draft202012Validator if jsonschema else None


def _load_schema(name: str) -> dict:
    return json.loads((SCHEMAS / name).read_text(encoding="utf-8"))


def _validate(document: dict, schema_name: str, label: str) -> None:
    schema = _load_schema(schema_name)
    errors = sorted(VALIDATOR(schema).iter_errors(document), key=lambda e: e.path)
    assert not errors, (
        f"{label} does not conform to {schema_name}: "
        + "; ".join(f"{'/'.join(map(str, e.path)) or '<root>'}: {e.message}" for e in errors)
    )


@requires_schemas
def test_manifest_conforms_to_schema():
    manifest = yaml.safe_load((ROOT / ".uasep" / "manifest.yaml").read_text(encoding="utf-8"))
    _validate(manifest, "manifest.schema.json", ".uasep/manifest.yaml")
    assert manifest["protocol"] == "UASEP"
    assert manifest["uasep_runtime"] == "NONE"


@requires_schemas
def test_durable_state_conforms_and_matches_manifest():
    state = json.loads((ROOT / ".uasep" / "state" / "state.json").read_text(encoding="utf-8"))
    _validate(state, "state.schema.json", ".uasep/state/state.json")
    manifest = yaml.safe_load((ROOT / ".uasep" / "manifest.yaml").read_text(encoding="utf-8"))
    for key in ("protocol", "protocol_version", "project_state"):
        assert state[key] == manifest[key], (
            f"durable state and manifest disagree on {key}: "
            f"{state[key]!r} != {manifest[key]!r}"
        )


def test_required_durable_artifacts_exist():
    required = [
        "AGENTS.md",
        ".uasep/state/STATUS.md",
        ".uasep/state/PROJECT_STATE.md",
        ".uasep/state/HANDOFF.md",
        ".uasep/state/state.json",
    ]
    for rel in required:
        assert (ROOT / rel).is_file(), f"missing required artifact: {rel}"
    for rel in (".uasep/planning", ".uasep/knowledge"):
        path = ROOT / rel
        assert path.is_dir() and any(path.iterdir()), f"missing or empty: {rel}/"


@requires_schemas
def test_task_contracts_conform_to_schema():
    for path in sorted((ROOT / ".uasep" / "state").glob("TASK_*.json")):
        document = json.loads(path.read_text(encoding="utf-8"))
        _validate(document, "task.schema.json", path.name)


@requires_schemas
def test_ownership_leases_conform_to_schema():
    for path in sorted((ROOT / ".uasep" / "state").glob("OWNERSHIP_*.json")):
        document = json.loads(path.read_text(encoding="utf-8"))
        _validate(document, "ownership.schema.json", path.name)


@requires_schemas
def test_evidence_records_conform_and_ids_are_unique():
    records = sorted((ROOT / ".uasep" / "evidence").glob("*.json"))
    assert records, "no evidence records found in .uasep/evidence/"
    seen = set()
    for path in records:
        document = json.loads(path.read_text(encoding="utf-8"))
        _validate(document, "evidence.schema.json", path.name)
        evidence_id = document["evidence_id"]
        assert evidence_id not in seen, f"duplicate evidence_id: {evidence_id}"
        seen.add(evidence_id)


def test_truth_model_statuses_are_used_honestly():
    """Status narratives must not silently claim UNKNOWN work as VERIFIED."""
    status = (ROOT / ".uasep" / "state" / "STATUS.md").read_text(encoding="utf-8")
    assert "UNKNOWN" not in status.replace("UNKNOWN ≠", "") or "VERIFIED" in status
    for forbidden in ("silently verified", "assumed VERIFIED"):
        assert forbidden.lower() not in status.lower()
