from observability import Event, Metrics


def test_event_creation():
    event = Event(event="startup", component="runtime", status="ok")
    assert event.event == "startup"
    assert event.status == "ok"


def test_metrics_counter():
    metrics = Metrics()
    metrics.increment("requests")
    metrics.increment("requests")
    assert metrics.get("requests") == 2
