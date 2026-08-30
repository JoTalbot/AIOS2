from runtime.startup_validation import validate_startup


def test_startup_validation_report():
    report = validate_startup()

    assert report["system"] == "AIOS2"
    assert "status" in report
    assert report["checks"]["runtime"] == "ok"
