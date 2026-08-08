import unittest

from mcp_server.rag.self_rag_check import (
    validate_memory_recall_output,
    validate_retrieval_and_answer,
)


class SelfRAGCheckTests(unittest.TestCase):
    def test_blocks_irrelevant_retrieval_and_unsupported_answer(self):
        result = validate_retrieval_and_answer(
            query="What is the REI for Herbicide X?",
            retrieved_contexts=["North Farm has tomatoes"],
            generated_answer="The weather is sunny today.",
            source="RAG",
        )

        self.assertFalse(result["passed"])
        self.assertEqual(result["status"], "blocked")
        self.assertFalse(result["relevance_check"])
        self.assertFalse(result["support_check"])

    def test_blocks_memory_recall_when_answer_is_not_supported(self):
        result = validate_memory_recall_output(
            query="What is the REI for Herbicide X?",
            recalled_memories=["The field was planted with wheat"],
            generated_answer="The re-entry interval is 24 hours.",
            source="memory-recall",
        )

        self.assertFalse(result["passed"])
        self.assertEqual(result["status"], "blocked")


if __name__ == "__main__":
    unittest.main()
