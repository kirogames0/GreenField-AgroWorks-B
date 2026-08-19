import json
import time
from typing import Any, Dict, List, Optional, Tuple

import requests
from mcp_server.rag.hybrid_search import run_hybrid_search
from config import get_llm_client

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


def call_llm(query: str, payload: str) -> Tuple[bool, int, str]:
    """Use centralized LLM config instead of direct API calls."""
    formatted_prompt = SELF_RAG_CRITIQUE_PROMPT.format(query=query, document=payload)
    
    try:
        llm = get_llm_client()
        response = llm.invoke(formatted_prompt)
        raw_content = response.content
        
        cleaned_content = raw_content
        if "```json" in cleaned_content:
            cleaned_content = cleaned_content.split("```json")[1].split("```")[0].strip()
        elif "```" in cleaned_content:
            cleaned_content = cleaned_content.split("```", 1)[1].split("```", 1)[0].strip()

        try:
            res_json = json.loads(cleaned_content)
            is_relevant = res_json.get("is_relevant", False)
            reasoning = res_json.get("reasoning", "No reasoning provided.")
            return is_relevant, 0, reasoning  # Tokens not available from centralized client
        except json.JSONDecodeError:
            return False, 0, f"Unable to parse verification response: {raw_content}"
    except Exception as e:
        # Fallback lexical relevance if LLM call fails
        lower_query = query.lower()
        lower_payload = payload.lower()
        matched_terms = [term for term in lower_query.split() if term and term in lower_payload]
        is_relevant = len(matched_terms) >= max(1, len(lower_query.split()) // 5)
        reasoning = (
            f"Fallback lexical relevance due to LLM error: {e}. "
            f"Matched terms: {matched_terms}"
        )
        return is_relevant, 0, reasoning


def run_agentic_rag(query: str, top_k: int = 3) -> Dict[str, Any]:
    """Agentic RAG: retrieve, critique, and filter chunks using LLM."""
    start_time = time.perf_counter()
    total_tokens = 0
    trace: List[Dict[str, Any]] = []

    # Retrieve initial candidates
    candidates = run_hybrid_search(query, top_k=top_k * 2)  # Wider net
    trace.append({
        "step": "candidate_retrieval",
        "candidates_retrieved": len(candidates),
    })

    verified_results: List[Dict[str, Any]] = []

    for idx, candidate in enumerate(candidates):
        doc_text = candidate.get("payload", candidate.get("text", ""))
        section_title = candidate.get("metadata", {}).get("section", f"chunk_{idx + 1}")

        try:
            is_relevant, tokens, reasoning = call_llm(
                query=query,
                payload=doc_text,
            )
        except Exception as err:
            trace.append({
                "step": f"critique_candidate_{idx + 1}",
                "section": section_title,
                "is_relevant": False,
                "reasoning": str(err),
                "tokens_consumed": 0,
            })
            continue

        total_tokens += tokens
        trace.append({
            "step": f"critique_candidate_{idx + 1}",
            "section": section_title,
            "is_relevant": is_relevant,
            "reasoning": reasoning,
            "tokens_consumed": tokens,
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
        "trace": trace,
    }