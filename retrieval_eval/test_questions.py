"""
Fixed Domain-Specific Test Suite for Retrieval Architecture Benchmarking.

Covers three specific query patterns:
1. General Concepts (Naive RAG friendly)
2. Exact Identifiers (Hybrid Search friendly)
3. Multi-part / Complex Context (Agentic RAG friendly)
"""

TEST_QUESTIONS = [
    {
        "id": "Q1_GENERAL",
        "category": "General Concept",
        "query": "What are the standard worker safety guidelines and general re-entry interval requirements after chemical application?",
        "target_architecture": "Naive RAG",
        "expected_keywords": ["safety", "re-entry", "interval", "protective", "equipment"],
        "description": "Standard conceptual query easily handled by semantic embedding similarity."
    },
    {
        "id": "Q2_IDENTIFIER",
        "category": "Exact Identifier",
        "query": "What does Protocol 4.2b specify for 14-day pre-harvest intervals (PHI) on tomato crops?",
        "target_architecture": "Hybrid Search",
        "expected_keywords": ["4.2b", "14-day", "PHI", "tomatoes"],
        "description": "Query containing exact section codes and numeric constraints where keyword matching (BM25) is crucial."
    },
    {
        "id": "Q3_MULTIPART",
        "category": "Multi-Part / Complex",
        "query": "For an emergency spill of Chemical 402 near a surface water buffer zone, what immediate PPE, notification steps, and containment protocols apply?",
        "target_architecture": "Agentic RAG",
        "expected_keywords": ["spill", "Chemical 402", "buffer zone", "PPE", "containment"],
        "description": "Multi-hop query requiring verification across multiple distinct policy sections (emergency, safety, and environmental)."
    }
]