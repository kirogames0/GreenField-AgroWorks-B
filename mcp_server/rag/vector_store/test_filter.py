"""
Acceptance Test for Issue #5
"""
from mcp_server.rag.knowledge_base import vector_store

def test_metadata_filtering():
    query = "What are the rules for safety and emergencies?"

    print("\n=== Test 1: Unfiltered Vector Search ===")
    unfiltered_results = vector_store.query(query_text=query, top_k=2)
    for r in unfiltered_results:
        print(f"[{r['metadata']['category']}] {r['metadata']['section']} (Score: {r['score']})")

    print("\n=== Test 2: Pre-Filtered Vector Search (category='field_safety') ===")
    filtered_results = vector_store.query(
        query_text=query,
        top_k=2,
        filter_dict={"category": "field_safety"}
    )
    for r in filtered_results:
        print(f"[{r['metadata']['category']}] {r['metadata']['section']} (Score: {r['score']})")

    assert unfiltered_results != filtered_results, "Validation failed: Pre-filtering did not alter results."
    print("\n SUCCESS: Issue #5 Acceptance criteria met.")

if __name__ == "__main__":
    test_metadata_filtering()