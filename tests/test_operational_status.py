from runtime.operational_status import build_operational_status


def test_operational_status_contains_core_layers():
    report = build_operational_status()

    assert report["system"] == "AIOS2"
    assert report["status"] == "operational"
    assert report["runtime"]["checks"]["runtime"] == "ok"
    assert report["runtime"]["checks"]["recovery"] == "ok"
    assert report["startup"]["system"] == "AIOS2"
