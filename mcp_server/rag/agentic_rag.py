import json
import os
import time
from typing import Any, Dict, List, Optional, Tuple
from dotenv import load_dotenv
from openai import OpenAI
from mcp_server.rag.hybrid_search import run_hybrid_search


load_dotenv()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL_NAME = "openai/gpt-oss-20b:free"
llm_client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
    default_headers={
        "HTTP-Referer": "https://github.com/GreenField-AgroWorks",
        "X-Title": "GreenField AgroWorks MCP Agent",
    }
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

    formatted_prompt = SELF_RAG_CRITIQUE_PROMPT.format(query=query, document=payload)
    try:
        response = llm_client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": formatted_prompt}],
            temperature=0.0,
        )

        raw_content = response.choices[0].message.content.strip()
        tokens_used = response.usage.total_tokens if response.usage else 0

        # Handle models that format JSON output inside markdown fences
        cleaned_content = raw_content
        if "```json" in cleaned_content:
            cleaned_content = cleaned_content.split("```json")[1].split("```")[0].strip()
        elif "```" in cleaned_content:
            cleaned_content = cleaned_content.split("```")[1].split("```")[0].strip()

        res_json = json.loads(cleaned_content)
        is_relevant = bool(res_json.get("is_relevant", False))
        reasoning = res_json.get("reasoning", "No reasoning provided.")

        return is_relevant, tokens_used, reasoning

    except Exception as err:
        print(f"LLM Verification error: {err}")
        return True, 0, f"Error during verification: {str(err)}"

def run_agentic_rag(
    query: str,
    top_k: int = 3,
    category: Optional[str] = None,
    session_role: str = "any",  ) -> Dict[str, Any]:

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

        is_relevant, tokens, reasoning = call_llm(
            query=query,
            payload=doc_text,
        )
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
