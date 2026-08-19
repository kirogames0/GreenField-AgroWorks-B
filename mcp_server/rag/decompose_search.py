"""
Option A starter: decompose_and_search

Wraps your EXISTING search_knowledge_base tool with a decomposition step,
so compound questions get split into sub-questions before searching.

WHAT YOU NEED TO DO (look for "TODO"):
  1. Replace call_llm() with your real LLM client call.
  2. Replace search_knowledge_base() with an import of your real MCP tool.
  3. Wire combine_search() up as a new MCP tool in your server, same style
     as your other tools (typed schema: query: str, top_k: int).

This file runs on its own with fake stand-ins so you can see the shape of
the flow before touching your real server.
"""

from dataclasses import dataclass


# Decompose the incoming query into sub-questions

DECOMPOSE_PROMPT = """\
Break the following question into 2-4 simpler sub-questions that, together,
fully answer it. If the question is already simple, just return it as-is
as a single sub-question.

Question: {query}

Return ONLY a numbered list, one sub-question per line. Example:
1. ...
2. ...
"""


def decompose_query(query: str, llm) -> list[str]:
    """Turn one (possibly compound) query into a list of sub-questions."""
    raw = llm.complete(DECOMPOSE_PROMPT.format(query=query))

    sub_questions = []
    for line in raw.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        # strip a leading "1.", "2)", "- " etc.
        for sep in [". ", ") ", "- "]:
            if sep in line[:4]:
                line = line.split(sep, 1)[1]
                break
        sub_questions.append(line.strip())

    return sub_questions or [query]  # fallback: treat as one question


# Tagged result so the model knows which sub-question each chunk answers


@dataclass
class TaggedChunk:
    sub_question: str
    chunk: str
    score: float


def combine_search(query: str, search_tool, llm, top_k: int = 3) -> list[TaggedChunk]:
    """
    The new tool: decompose the query, run your EXISTING search tool once
    per sub-question, and return everything tagged so the model can see
    which piece of the original question each chunk is answering.

    `search_tool` is your existing search_knowledge_base function/tool.
    It's passed in here so this file has no hard dependency on your server
    -- swap in the real one where you wire this up as an MCP tool.
    """
    sub_questions = decompose_query(query, llm)

    results: list[TaggedChunk] = []
    for sub_q in sub_questions:
        hits = search_tool(sub_q, top_k)  # same call signature as your existing tool
        for chunk, score in hits:
            results.append(TaggedChunk(sub_question=sub_q, chunk=chunk, score=score))
    
    return results
