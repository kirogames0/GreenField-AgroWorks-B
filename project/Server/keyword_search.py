"""
KeywordStore: a minimal BM25-backed store with the same upsert()/query()
shape you'd get from a vector database, but with no embedding model and no
external service to configure.

This is intentionally swappable: if the project later moves to a real
vector DB (pgvector, Chroma, etc.), `knowledge_base.py` and `tool.py` don't
need to change -- only this file does.
"""

import re
from dataclasses import dataclass, field
from typing import Any, Optional

from rank_bm25 import BM25Okapi


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


@dataclass
class _Record:
    payload: Any
    metadata: dict


class KeywordStore:
    def __init__(self):
        self._records: list[_Record] = []
        self._bm25: Optional[BM25Okapi] = None
        self._dirty = True

    def upsert(self, payload: Any, metadata: dict) -> None:
        self._records.append(_Record(payload=payload, metadata=metadata))
        self._dirty = True

    def _ensure_index(self) -> None:
        if not self._dirty:
            return
        corpus = [
            _tokenize(r.payload if isinstance(r.payload, str) else str(r.payload))
            for r in self._records
        ]
        self._bm25 = BM25Okapi(corpus) if corpus else None
        self._dirty = False

    def query(
        self,
        query_text: str,
        top_k: int = 3,
        filter: Optional[dict] = None,
    ) -> list[dict]:
        if not self._records:
            return []

        self._ensure_index()

        # Filter first (cheap, and keeps score ranking scoped correctly)
        candidate_idxs = [
            i
            for i, r in enumerate(self._records)
            if not filter
            or all(r.metadata.get(k) == v for k, v in filter.items())
        ]
        if not candidate_idxs:
            return []

        tokenized_query = _tokenize(query_text)
        all_scores = self._bm25.get_scores(tokenized_query)

        scored = [(all_scores[i], i) for i in candidate_idxs]
        scored.sort(key=lambda x: x[0], reverse=True)

        results = []
        for score, idx in scored[:top_k]:
            if score <= 0:
                continue
            r = self._records[idx]
            results.append({"payload": r.payload, "metadata": r.metadata, "score": float(score)})
        return results
