import unittest

from memory.short_term_buffer import ShortTermBuffer


class PromoteOrDropTests(unittest.TestCase):
    def test_overflow_router_promotes_and_drops_with_visible_reasoning(self):
        buffer = ShortTermBuffer(max_messages=1)

        buffer.add("user", "routine field update")
        buffer.add("assistant", "flagged compliance event: restricted chemical approval needed")
        buffer.add("assistant", "final follow-up")

        decisions = buffer.overflow_decisions

        self.assertTrue(any(d["action"] == "drop" for d in decisions))
        self.assertTrue(any(d["action"] == "promote_to_episodic" for d in decisions))
        self.assertTrue(any("reasoning" in d for d in decisions))
        self.assertTrue(any("compliance" in d["reasoning"].lower() for d in decisions))
        self.assertTrue(any("safe to drop" in d["reasoning"].lower() for d in decisions))
        self.assertTrue(buffer.episodic_promotions)
        self.assertEqual(len(buffer.messages), 1)


if __name__ == "__main__":
    unittest.main()
