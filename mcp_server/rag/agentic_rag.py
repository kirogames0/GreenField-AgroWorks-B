import json
import os
import time
from typing import Any, Dict, List, Optional, Tuple

import requests
from mcp_server.rag.hybrid_search import run_hybrid_search

MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "")
MISTRAL_MODEL = os.getenv("MISTRAL_MODEL", "mistral-large")
MISTRAL_API_URL = os.getenv(
    "MISTRAL_API_URL",
    "https://api.mistral.ai/v1/chat/completions",
)

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
    if not MISTRAL_API_KEY:
        lower_query = query.lower()
        lower_payload = payload.lower()
        matched_terms = [term for term in lower_query.split() if term and term in lower_payload]
        is_relevant = len(matched_terms) >= max(1, len(lower_query.split()) // 5)
        reasoning = (
            "Fallback lexical relevance decision because MISTRAL_API_KEY is not configured."
            f" Matched terms: {matched_terms}"
        )
        return is_relevant, 0, reasoning

    formatted_prompt = SELF_RAG_CRITIQUE_PROMPT.format(query=query, document=payload)
    response = requests.post(
        MISTRAL_API_URL,
        headers={
            "Authorization": f"Bearer {MISTRAL_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": MISTRAL_MODEL,
            "messages": [{"role": "user", "content": formatted_prompt}],
            "temperature": 0.0,
        },
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()

    raw_content = ""
    if data.get("choices"):
        raw_content = data["choices"][0].get("message", {}).get("content", "").strip()

    tokens_used = 0
    usage = data.get("usage")
    if isinstance(usage, dict):
        tokens_used = usage.get("total_tokens", 0) or usage.get("prompt_tokens", 0) or 0

    cleaned_content = raw_content
    if "```json" in cleaned_content:
        cleaned_content = cleaned_content.split("```json")[1].split("```")[0].strip()
    elif "```" in cleaned_content:
        cleaned_content = cleaned_content.split("```", 1)[1].split("```", 1)[0].strip()

    try:
        res_json = json.loads(cleaned_content)
    except json.JSONDecodeError:
        return False, tokens_used, f"Unable to parse verification response: {cleaned_content}"

    is_relevant = bool(res_json.get("is_relevant", False))
    reasoning = res_json.get("reasoning", "No reasoning provided.")

    return is_relevant, tokens_used, reasoning


def run_agentic_rag(
    query: str,
    top_k: int = 3,
    category: Optional[str] = None,
    session_role: str = "any",
) -> Dict[str, Any]:
    start_time = time.perf_counter()
    total_tokens = 0
    trace: List[Dict[str, Any]] = []
    candidate_fetch_k = top_k + 2
    hybrid_output = run_hybrid_search(
        query=query,
        top_k=candidate_fetch_k,
        category=category,
        session_role=session_role,
    )

    candidates = hybrid_output.get("results", [])
    total_tokens += hybrid_output.get("tokens_used", 0)

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
