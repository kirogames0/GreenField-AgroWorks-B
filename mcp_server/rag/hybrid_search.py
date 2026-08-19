import time
from typing import Any, Dict, Optional
from mcp_server.rag.knowledge_base import vector_store, keyword_store


def run_hybrid_search(
    query: str,
    top_k: int = 3,
    category: Optional[str] = None,
    session_role: str = "any",
    **kwargs: Any ) -> Dict[str, Any]:

    start_time = time.perf_counter()
    where_filter = {"category": category} if category else None

    vector_results = vector_store.query(
        query_text=query,
        top_k=top_k,
        filter_dict=where_filter
    )
    keyword_results = keyword_store.query(
        query_text=query,
        top_k=top_k,
        filter=where_filter
    )

    # rrf calculation
    k_constant = 60
    rrf_scores: Dict[str, float] = {}
    merged_docs: Dict[str, Dict[str, Any]] = {}

    for rank, res in enumerate(vector_results):
        doc_id = res["metadata"]["section"]
        rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + (1.0 / (k_constant + rank + 1))
        merged_docs[doc_id] = res

    for rank, res in enumerate(keyword_results):
        doc_id = res["metadata"]["section"]
        rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + (1.0 / (k_constant + rank + 1))
        merged_docs[doc_id] = res

    sorted_doc_ids = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)

    final_results = []
    for doc_id in sorted_doc_ids:
        m = merged_docs[doc_id]
        role_req = m.get("metadata", {}).get("role_required", "any")
        if role_req in ("any", session_role):
            final_results.append(m)

    latency = time.perf_counter() - start_time

    return {
        "architecture": "Hybrid Search",
        "results": final_results[:top_k],
        "latency": round(latency, 4),
        "tokens_used": 0
    }