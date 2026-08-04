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

_KB_PATH = os.path.join(os.path.dirname(__file__), "data", "chemical_safety_handbook.md")

knowledge_store = KeywordStore()


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
    """Loads the handbook, chunks it by section, and indexes each chunk.

    Safe to call more than once (e.g. on server startup); callers wanting
    a clean re-index should construct a fresh KeywordStore first.
    """
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()

    sections = _chunk_markdown_by_section(raw)
    for section in sections:
        knowledge_store.upsert(
            payload=section["text"],
            metadata={
                "source": "chemical_safety_handbook.md",
                "section": section["title"],
                # Every field_hand and certified_applicator can read this
                # doc today. The field exists so a future restricted
                # section (e.g. internal incident-cost data) can be
                # locked to a role without changing the tool's schema.
                "role_required": "any",
            },
        )
    return len(sections)


# Index once at import time.
_CHUNK_COUNT = index_knowledge_base()
