"""
Demo: search_knowledge_base answering compliance questions that no query
against Fields / Chemicals / Chemical_Applications could answer, since
the answer is regulatory procedure, not a row in a table.

Run standalone (no DB / server needed) with:
    cd greenfield/rag && python3 demo.py
"""

from tool import search_knowledge_base

if __name__ == "__main__":
    print("=== Demo query: can a field hand re-enter the field today? ===")
    print("Query: 'how long before workers can re-enter after spraying'\n")
    result = search_knowledge_base(
        {"query": "how long before workers can re-enter after spraying", "top_k": 2},
        cursor=None,
        session_role="any",
    )
    for r in result["results"]:
        print(f"[{r['section']}] (score {r['relevance_score']})\n{r['text']}\n")

    print("\n=== Demo query: is the harvest date compliant? ===")
    print("Query: 'pre-harvest interval before we can pick the crop'\n")
    result = search_knowledge_base(
        {"query": "pre-harvest interval before we can pick the crop", "top_k": 2},
        cursor=None,
        session_role="any",
    )
    for r in result["results"]:
        print(f"[{r['section']}] (score {r['relevance_score']})\n{r['text']}\n")

    print("\n=== Control: query with no real keyword overlap in the handbook ===")
    print("Query: 'karaoke night signup sheet'\n")
    result = search_knowledge_base(
        {"query": "karaoke night signup sheet", "top_k": 2},
        cursor=None,
        session_role="any",
    )
    print(result["message"] if not result["results"] else result["results"])
