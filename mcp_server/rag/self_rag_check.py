"""Post-retrieval and post-generation validation for RAG and memory recall.

This module adds an explicit safety gate that checks whether retrieved context
is relevant to the query and whether the generated answer is supported by that
retrieved context. If either check fails, the output is marked as blocked and
returned with a visible trace instead of being silently passed through.
"""

from __future__ import annotations

from typing import Any


def _contains_relevant_terms(query: str, text: str) -> bool:
    query_terms = {term.lower() for term in query.replace("?", "").split() if term}
    text_terms = {term.lower() for term in text.replace("?", "").split() if term}
    if not query_terms:
        return True
    return bool(query_terms & text_terms)


def _answer_is_supported(query: str, contexts: list[str], answer: str | None) -> bool:
    if not contexts:
        return False

    if answer is None:
        return True  # Skip support check when no answer is provided

    answer_terms = {term.lower() for term in answer.replace("?", "").split() if term}
    context_text = " ".join(contexts).lower()

    if not answer_terms:
        return False

    evidence_terms = {
        term
        for term in answer_terms
        if term in context_text and term not in {"the", "is", "a", "an", "for", "and", "or", "was"}
    }

    if not evidence_terms:
        return False

    if any(term in context_text for term in {"rei", "re-entry", "chemical", "restricted", "approval", "buffer", "phi"}):
        return bool(evidence_terms)

    return bool(evidence_terms)


def validate_retrieval_and_answer(
    query: str,
    retrieved_contexts: list[str],
    generated_answer: str,
    source: str = "RAG",
) -> dict[str, Any]:
    """Validate retrieved content and the generated answer for relevance/support."""

    relevance_check = bool(retrieved_contexts) and any(
        _contains_relevant_terms(query, context) for context in retrieved_contexts
    )
    support_check = _answer_is_supported(query, retrieved_contexts, generated_answer)

    passed = relevance_check and support_check
    status = "passed" if passed else "blocked"

    return {
        "source": source,
        "passed": passed,
        "status": status,
        "relevance_check": relevance_check,
        "support_check": support_check,
        "reason": (
            "retrieval and answer are both supported"
            if passed
            else "retrieval or answer failed the relevance/support gate"
        ),
        "trace": [
            f"{source}: relevance_check={relevance_check}",
            f"{source}: support_check={support_check}",
        ],
    }


def validate_memory_recall_output(
    query: str,
    recalled_memories: list[str],
    generated_answer: str,
    source: str = "memory-recall",
) -> dict[str, Any]:
    """Validate memory recall outputs using the same support gate."""

    return validate_retrieval_and_answer(
        query=query,
        retrieved_contexts=recalled_memories,
        generated_answer=generated_answer,
        source=source,
    )
