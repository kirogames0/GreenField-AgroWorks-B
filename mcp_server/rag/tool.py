"""
The search_knowledge_base tool -- same JSON-schema + handler shape as the
rest of tools_reads.py (real `inputSchema`, `required`,
`additionalProperties: false`), so it plugs directly into
`_load_tool_definitions()` / `handle_tools_call()` in server.py without
introducing a second tool-definition style.

This is additive: it does not touch db.py-equivalent queries in
tools_reads.py / tools_writes.py, and it answers a different kind of
question -- "what does the compliance handbook say about X" -- that no
query against Fields/Chemicals/Chemical_Applications could ever answer,
because REI, PHI, buffer zones, and spill-response steps only exist as
prose written by the Agronomy & Compliance team.
"""
from mcp_server.rag.decompose_search import combine_search
from mcp_server.rag.hybrid_search import run_hybrid_search
from mcp_server.rag.agentic_rag import llm_client, MODEL_NAME, run_agentic_rag
from mcp_server.rag.self_rag_check import validate_retrieval_and_answer

SEARCH_KNOWLEDGE_BASE_SCHEMA = {
    "name": "search_knowledge_base",
    "description": (
        "Search the Chemical Safety & Compliance Handbook for guidance on "
        "re-entry intervals, pre-harvest intervals, buffer zones, spill "
        "response, and restricted-use requirements. Read-only."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Keywords describing the compliance question or topic.",
            },
            "category": {
                "type": "string",
                "description": "Optional filter. Use 'field_safety', 'emergency', or 'general'.",
            },
            "top_k": {
                "type": "integer",
                "minimum": 1,
                "maximum": 10,
                "default": 3,
            },
        },
        "required": ["query"],
        "additionalProperties": False,
    },
}


DEEP_RESEARCH_SCHEMA = {
    "name": "search_knowledge_base",
    "description": (
        "Use this tool ONLY for complex, multi-part questions where standard search failed "
    "to find a complete answer. It uses a slower reasoning loop to verify document relevance."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Keywords describing the compliance question or topic.",
            },
            "category": {
                "type": "string",
                "description": "Optional filter. Use 'field_safety', 'emergency', or 'general'.",
            },
            "top_k": {
                "type": "integer",
                "minimum": 1,
                "maximum": 10,
                "default": 3,
            },
        },
        "required": ["query"],
        "additionalProperties": False,
    },
}

DECOMPOSE_AND_SEARCH_SCHEMA = {
    "name": "decompose_and_search",
    "description": (
        "Break a compound compliance query into simpler sub-questions and search each one via search_knowledge_base."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Compound compliance question to decompose and search.",
            },
            "category": {
                "type": "string",
                "description": "Optional filter. Use 'field_safety', 'emergency', or 'general'.",
            },
            "top_k": {
                "type": "integer",
                "minimum": 1,
                "maximum": 10,
                "default": 3,
            },
        },
        "required": ["query"],
        "additionalProperties": False,
    },
}

#HOTFIX: the task wanted all approaches to be seperate so i am going to isolate the logic ouf ot the tool for now
#ofc according to the rubric we need to actually make a case on why hybrid is the effecient option here and
#added a new tool for the agentic rag approach. should be wired to the server according to issue #8
def search_knowledge_base(args: dict, cursor=None, session_role: str = "any") -> dict:
    query = args.get("query")
    if not query:
        raise ValueError("query is required")

    top_k = int(args.get("top_k", 3))
    output = run_hybrid_search(query=query, top_k=top_k)

    visible = [m for m in output["results"] if m["metadata"]["role_required"] in ("any", session_role)]
    contexts = [m["payload"] for m in visible]
    validation = validate_retrieval_and_answer(
        query=query,
        retrieved_contexts=contexts,
        generated_answer="",
        source="RAG",
    )

    return {
        "query": query,
        "architecture_used": "Hybrid Search",
        "results": [{"section": m["metadata"]["section"], "text": m["payload"]} for m in visible],
        "validation": validation,
    }


def decompose_and_search(args: dict, cursor=None, session_role: str = "any") -> dict:
    query = args.get("query")
    if not query:
        raise ValueError("query is required")

    top_k = int(args.get("top_k", 3))
    category = args.get("category")

    class LLMProxy:
        def complete(self, prompt: str) -> str:
            response = llm_client.chat.completions.create(
                model=MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
            )
            return response.choices[0].message.content

    def search_tool(query_text: str, tool_top_k: int = 3):
        search_args = {"query": query_text, "top_k": tool_top_k}
        if category:
            search_args["category"] = category
        output = search_knowledge_base(search_args, cursor=cursor, session_role=session_role)
        return [(item.get("text", ""), float(item.get("score", 0.0)) if item.get("score") is not None else 0.0)
                for item in output.get("results", [])]

    tagged_results = combine_search(query, search_tool, LLMProxy(), top_k=top_k)
    return {
        "query": query,
        "architecture_used": "Decomposed Hybrid Search",
        "sub_questions": [result.sub_question for result in tagged_results],
        "results": [
            {"sub_question": result.sub_question, "chunk": result.chunk, "score": result.score}
            for result in tagged_results
        ],
    }


def deep_research_knowledge_base(args: dict, cursor=None, session_role: str = "any") -> dict:
    query = args.get("query")
    if not query:
        raise ValueError("query is required")

    top_k = int(args.get("top_k", 3))
    output = run_agentic_rag(query=query, top_k=top_k)

    visible = [m for m in output["results"] if m["metadata"]["role_required"] in ("any", session_role)]
    contexts = [m["payload"] for m in visible]
    validation = validate_retrieval_and_answer(
        query=query,
        retrieved_contexts=contexts,
        generated_answer="",
        source="RAG",
    )

    return {
        "query": query,
        "architecture_used": "Agentic RAG (Self-Verified)",
        "results": [{"section": m["metadata"]["section"], "text": m["payload"]} for m in visible],
        "validation": validation,
    }

