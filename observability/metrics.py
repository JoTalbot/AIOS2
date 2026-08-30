from collections import defaultdict


class Metrics:
    """Minimal in-memory runtime metrics collector."""

    def __init__(self):
        self._counters = defaultdict(int)

    def increment(self, name: str, value: int = 1) -> None:
        self._counters[name] += value

    def get(self, name: str) -> int:
        return self._counters[name]

    def snapshot(self) -> dict[str, int]:
        return dict(self._counters)
