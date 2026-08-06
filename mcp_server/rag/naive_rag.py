from mcp_server.rag.knowledge_base import vector_store
import time


def run_naive_rag(query: str, top_k: int = 3) -> dict:
    start_time = time.time()
    results = vector_store.query(query_text=query, top_k=top_k)
    latency = time.time() - start_time

    return {
        "architecture": "Naive RAG",
        "results": results,
        "latency": round(latency, 4),
        "tokens_used": 0
    }