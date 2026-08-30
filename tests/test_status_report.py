from runtime.status_report import build_status_report


def test_status_report_contains_runtime_checks():
    report = build_status_report()

    assert report["system"] == "AIOS2"
    assert report["status"] == "operational"
    assert report["checks"]["runtime"] == "ok"
    assert report["checks"]["api"] == "ok"
    assert report["checks"]["recovery"] == "ok"
