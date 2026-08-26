def test_autonomy_cycle():
    stages = [
        "goal",
        "reasoning",
        "planning",
        "execution",
        "reflection",
        "learning",
        "evolution",
    ]

    assert len(stages) == 7
    assert stages[-1] == "evolution"
