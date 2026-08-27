from pathlib import Path


def test_architecture_contract_files_exist():
    root = Path(__file__).parents[1]
    required = [
        root / "PROJECT.md",
        root / "docs" / "ARCHITECTURE.md",
        root / "docs" / "NEW_ARCHITECTURE_PLAN.md",
        root / "docs" / "ARCHITECTURE_GUARDS.md",
        root / "docs" / "ROADMAP.md",
        root / "docs" / "adr" / "0001-canonical-execution-authority.md",
    ]
    assert all(path.is_file() for path in required)


def test_runtime_does_not_import_legacy_scheduler():
    runtime = Path(__file__).parents[1] / "runtime"
    offenders = []
    for path in runtime.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        if "from runtime.scheduler import" in text:
            offenders.append(path.name)
    assert offenders == []
