from mcp_server.rag.self_rag_check import (
    validate_memory_recall_output,
    validate_retrieval_and_answer,
)


if __name__ == "__main__":
    rag_result = validate_retrieval_and_answer(
        query="What is the REI for Herbicide X?",
        retrieved_contexts=["North Farm has tomatoes"],
        generated_answer="The weather is sunny today.",
        source="RAG",
    )
    print("=== RAG validation demo ===")
    print(rag_result)

    memory_result = validate_memory_recall_output(
        query="What is the REI for Herbicide X?",
        recalled_memories=["The field was planted with wheat"],
        generated_answer="The re-entry interval is 24 hours.",
        source="memory-recall",
    )
    print("=== Memory recall validation demo ===")
    print(memory_result)
