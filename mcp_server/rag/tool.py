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
from mcp_server.rag.knowledge_base import vector_store

SEARCH_KNOWLEDGE_BASE_SCHEMA = {
    "name": "search_knowledge_base",
    "description": (
        "Search the Chemical Safety Handbook using vector similarity."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Keywords describing the compliance question.",
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

def search_knowledge_base(args: dict, cursor=None, session_role: str = "any") -> dict:
    query = args.get("query")
    if not query:
        raise ValueError("query is required")

    category = args.get("category")
    top_k = int(args.get("top_k", 3))

    where_filter = {}
    if category:
        where_filter["category"] = category

    matches = vector_store.query(
        query_text=query,
        top_k=top_k,
        filter_dict=where_filter if where_filter else None
    )
    visible = [
        m for m in matches
        if m["metadata"]["role_required"] in ("any", session_role)
    ]

    return {
        "query": query,
        "results": [
            {
                "section": m["metadata"]["section"],
                "text": m["payload"],
                "relevance_score": m["score"],
            }
            for m in visible
        ],
    }
