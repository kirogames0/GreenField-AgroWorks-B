"""
Chunking + indexing for the Chemical Safety & Compliance Handbook.

Source: rag/data/chemical_safety_handbook.md -- unstructured Agronomy &
Compliance team prose. This is distinct from the structured `Chemicals` /
`Chemical_Applications` tables: the DB stores WHETHER a chemical is
restricted and WHEN an application happened, but the handbook is where
the procedural requirements live (REI, PHI, buffer zones, spill
response) that neither `check_field_status`, `get_inventory`, nor
`generate_compliance_report` can surface, because they only ever return
what's in a column.

Chunking strategy: split on markdown "## " section headers, same
rationale as the Nextlink add-on -- each section is one self-contained
compliance topic, and splitting mid-topic (e.g. cutting the REI duration
off from the reason it matters) would make a chunk useless on its own.
"""

import os
from mcp_server.rag.keyword_search import KeywordStore
from mcp_server.rag.vector_store.store import VectorStore

_KB_PATH = os.path.join(os.path.dirname(__file__), "data", "chemical_safety_handbook.md")

keyword_store = KeywordStore()
vector_store = VectorStore()


def _chunk_markdown_by_section(text: str) -> list[dict]:
    chunks = []
    current_title = None
    current_lines: list[str] = []

    def flush():
        if current_title is not None and current_lines:
            body = "\n".join(current_lines).strip()
            if body:
                chunks.append({"title": current_title, "text": f"## {current_title}\n\n{body}"})

    for line in text.splitlines():
        if line.startswith("## "):
            flush()
            current_title = line[3:].strip()
            current_lines = []
        elif current_title is not None:
            current_lines.append(line)
    flush()
    return chunks


def index_knowledge_base(path: str = _KB_PATH) -> int:
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()

    sections = _chunk_markdown_by_section(raw)
    for idx, section in enumerate(sections):
        title_lower = section["title"].lower()

        category = "general"
        if "re-entry" in title_lower or "rei" in title_lower:
            category = "field_safety"
        elif "spill" in title_lower or "emergency" in title_lower:
            category = "emergency"

        meta = {
            "source": "chemical_safety_handbook.md",
            "section": section["title"],
            "category": category,
            "role_required": "any",
        }

        #needed for hybrid search
        keyword_store.upsert(payload=section["text"], metadata=meta, doc_id=f"handbook_{idx}")
        vector_store.upsert(payload=section["text"], metadata=meta, doc_id=f"handbook_{idx}")

    return len(sections)


_CHUNK_COUNT = index_knowledge_base()
