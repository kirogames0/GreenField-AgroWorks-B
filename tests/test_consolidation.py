import unittest
from datetime import datetime

from memory.consolidation import Episode, run_periodic_consolidation


class ConsolidationTests(unittest.TestCase):
    def test_consolidation_versions_conflicts_and_tracks_trace(self):
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

        current = store["chemical:Herbicide X:rei"]
        self.assertEqual(current.value, "REI 72h")
        self.assertEqual(current.version, 2)
        self.assertTrue(current.history)
        self.assertTrue(any(entry["status"] == "superseded" for entry in current.history))
        self.assertTrue(any("conflict" in entry.lower() for entry in result["trace"]))
        self.assertTrue(any("version" in entry.lower() for entry in result["trace"]))

    def test_consolidation_marks_expired_facts(self):
        episodes = [
            Episode(
                id="ep3",
                key="chemical:Herbicide X:rei",
                value="REI 96h",
                timestamp=datetime(2024, 1, 1),
                source="manual-note",
                expires_at=datetime(2024, 1, 1),
            )
        ]

        store = {}
        result = run_periodic_consolidation(episodes, store, now=datetime(2024, 1, 2))

        current = store["chemical:Herbicide X:rei"]
        self.assertFalse(current.active)
        self.assertTrue(any("expired" in entry.lower() for entry in result["trace"]))


if __name__ == "__main__":
    unittest.main()
