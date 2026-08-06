from typing import Any, Dict, List, Optional, Tuple
import time
from mcp_server.rag.hybrid_search import run_hybrid_search


SELF_RAG_CRITIQUE_PROMPT = """
You are a strict compliance evaluator for agricultural chemical safety documents.
Analyze whether the provided document chunk directly answers or contains necessary context for the user query.

Query: {query}

Document Chunk:
{document}

Task: Respond strictly with a JSON object containing:
- "is_relevant": boolean (true if relevant, false otherwise)
- "reasoning": brief one-sentence justification
"""


def call_llm(query: str, payload: str, llm_client: Optional[Any] = None) -> Tuple[bool, int, str]:
    """
    Executes the Self-RAG verification pass against an LLM.

    Args:
        query: The user's input search request.
        payload: The retrieved text chunk being evaluated.
        llm_client: Optional LLM client instance injected at runtime.

    Returns:
        Tuple[bool, int, str]: (is_relevant, tokens_consumed, reasoning)
    """
    pass
    #issue #8 should handle this with a real call
    #use the self_rag_critique_prompt to format the prompt and call the llm_client
    #if during testing the loop in run_agentic_rag is too slow or takes multiple calls
    # i give you permission to limit the calls and return the best last result for the sake of testing
    #until the issue #8 is resolved I cannot run the tests needed to support our findings


def run_agentic_rag(
    query: str,
    top_k: int = 3,
    category: Optional[str] = None,
    session_role: str = "any",
    llm_client: Optional[Any] = None ) -> Dict[str, Any]:
    """
    Executes Agentic RAG with iterative candidate verification and trace tracking.

    Args:
        query: User search string.
        top_k: Target number of verified results to return.
        category: Optional metadata filtering category.
        session_role: User role for authorization checks.
        llm_client: Optional initialized LLM client instance.

    Returns:
        Dict containing architecture name, verified results, latency, token count, and execution trace.
    """
    start_time = time.perf_counter()
    total_tokens = 0
    trace: List[Dict[str, Any]] = []
    candidate_fetch_k = top_k + 2
    hybrid_output = run_hybrid_search(
        query=query,
        top_k=candidate_fetch_k,
        category=category,
        session_role=session_role
    )

    candidates = hybrid_output.get("results", [])
    total_tokens += hybrid_output.get("tokens_used", 0)

    trace.append({
        "step": "candidate_retrieval",
        "candidates_retrieved": len(candidates)
    })

    verified_results: List[Dict[str, Any]] = []

    for idx, candidate in enumerate(candidates):
        doc_text = candidate.get("payload", candidate.get("text", ""))
        section_title = candidate.get("metadata", {}).get("section", f"chunk_{idx}")

        is_relevant, tokens, reasoning = call_llm(
            query=query,
            payload=doc_text,
            llm_client=llm_client
        )
        total_tokens += tokens

        trace.append({
            "step": f"critique_candidate_{idx + 1}",
            "section": section_title,
            "is_relevant": is_relevant,
            "reasoning": reasoning,
            "tokens_consumed": tokens
        })

        if is_relevant:
            verified_results.append(candidate)

        if len(verified_results) >= top_k:
            break

    latency = time.perf_counter() - start_time

    return {
        "architecture": "Agentic RAG",
        "results": verified_results[:top_k],
        "latency": round(latency, 4),
        "tokens_used": total_tokens,
        "trace": trace
    }