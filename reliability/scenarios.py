from dataclasses import dataclass


@dataclass
class FailureScenario:
    name: str
    triggered: bool = False

    def inject(self) -> None:
        self.triggered = True

    def reset(self) -> None:
        self.triggered = False
