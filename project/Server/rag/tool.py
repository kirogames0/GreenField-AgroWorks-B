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

import sqlite3

from knowledge_base import knowledge_store

SEARCH_KNOWLEDGE_BASE_SCHEMA = {
    "name": "search_knowledge_base",
    "description": (
        "Search the Chemical Safety & Compliance Handbook for guidance on "
        "re-entry intervals, pre-harvest intervals, buffer zones, spill "
        "response, and restricted-use requirements. Use this before "
        "scheduling field work near a recent application, or before "
        "finalizing a compliance report for a buyer audit. Read-only."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Keywords describing the compliance question or topic.",
            },
            "top_k": {
                "type": "integer",
                "minimum": 1,
                "maximum": 10,
                "default": 3,
                "description": "Max number of handbook sections to return.",
            },
        },
        "required": ["query"],
        "additionalProperties": False,
    },
}


def search_knowledge_base(args: dict, cursor: sqlite3.Cursor, session_role: str = "any") -> dict:
    """
    Handler registered for the `search_knowledge_base` tool.

    Signature matches check_field_status(args, cursor) / get_inventory(args, cursor)
    for consistency with the rest of tools_reads.py; `cursor` is accepted
    but unused since this tool queries the in-memory keyword store, not
    the sqlite DB. `session_role` mirrors the pattern used by
    request_pesticide_application: it comes from the session, never from
    `args`, so a caller can't unlock restricted handbook sections just by
    passing a role field.
    """
    query = args.get("query")
    if not query:
        raise ValueError("query is required")

    top_k = args.get("top_k", 3)
    try:
        top_k = int(top_k)
    except (TypeError, ValueError):
        raise ValueError(f"Invalid top_k: {top_k}")
    if not (1 <= top_k <= 10):
        raise ValueError("top_k must be between 1 and 10")

    matches = knowledge_store.query(query_text=query, top_k=top_k)

    visible = [
        m for m in matches
        if m["metadata"]["role_required"] in ("any", session_role)
    ]

    if not visible:
        return {
            "query": query,
            "results": [],
            "message": "No relevant handbook sections found for that query.",
        }

    return {
        "query": query,
        "results": [
            {
                "section": m["metadata"]["section"],
                "text": m["payload"],
                "relevance_score": round(m["score"], 2),
            }
            for m in visible
        ],
    }
