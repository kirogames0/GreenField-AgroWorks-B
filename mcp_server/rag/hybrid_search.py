from mcp_server.rag.knowledge_base import vector_store, keyword_store
import time


def run_hybrid_search(query: str, top_k: int = 3) -> dict:
    start_time = time.time()

    vector_results = vector_store.query(query_text=query, top_k=top_k)
    keyword_results = keyword_store.query(query_text=query, top_k=top_k)

    # rrf for score combination
    k_constant = 60
    rrf_scores = {}
    merged_docs = {}

    for rank, res in enumerate(vector_results):
        doc_id = res["metadata"]["section"]
        rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + (1.0 / (k_constant + rank + 1))
        merged_docs[doc_id] = res

    for rank, res in enumerate(keyword_results):
        doc_id = res["metadata"]["section"]
        rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + (1.0 / (k_constant + rank + 1))
        merged_docs[doc_id] = res

    sorted_doc_ids = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)
    final_results = [merged_docs[doc_id] for doc_id in sorted_doc_ids[:top_k]]

    latency = time.time() - start_time
    return {
        "architecture": "Hybrid Search",
        "results": final_results,
        "latency": round(latency, 4),
        "tokens_used": 0
    }