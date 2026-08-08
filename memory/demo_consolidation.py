from datetime import datetime

from memory.consolidation import Episode, run_periodic_consolidation


if __name__ == "__main__":
    episodes = [
        Episode(
            id="ep1",
            key="chemical:Herbicide X:rei",
            value="REI 48h",
            timestamp=datetime(2024, 1, 1),
            source="field-report",
        ),
        Episode(
            id="ep2",
            key="chemical:Herbicide X:rei",
            value="REI 72h",
            timestamp=datetime(2024, 1, 2),
            source="compliance-notice",
        ),
    ]

    store = {}
    result = run_periodic_consolidation(episodes, store, now=datetime(2024, 1, 3))
    fact = store["chemical:Herbicide X:rei"]

    print("=== Consolidation demo ===")
    print(f"Current fact: {fact.value}")
    print(f"Version: {fact.version}")
    print("Trace:")
    for entry in result["trace"]:
        print(f"- {entry}")
    print("History:")
    for entry in fact.history:
        print(f"- {entry}")
