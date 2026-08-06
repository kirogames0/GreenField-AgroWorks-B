from typing import Any, Dict, List, Optional
import chromadb
from chromadb.utils import embedding_functions
from mcp_server.rag.vector_store.config import COLLECTION_NAME, COLLECTION_METADATA


class VectorStore:
    def __init__(self):
        self.client = chromadb.Client()
        self.embedding_function = embedding_functions.DefaultEmbeddingFunction()
        self.collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata=COLLECTION_METADATA,
            embedding_function=self.embedding_function
        )

    def upsert(self, doc_id: str, payload: str, metadata: Dict[str, Any]) -> None:
        self.collection.upsert(
            ids=[doc_id],
            documents=[payload],
            metadatas=[metadata]
        )

    def query(
            self,
            query_text: str,
            top_k: int = 3,
            filter_dict: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        results = self.collection.query(
            query_texts=[query_text],
            n_results=top_k,
            where=filter_dict if filter_dict else None
        )

        formatted_results = []
        if results and results["documents"] and len(results["documents"][0]) > 0:
            for doc, meta, dist in zip(results["documents"][0], results["metadatas"][0], results["distances"][0]):
                formatted_results.append({
                    "payload": doc,
                    "metadata": meta,
                    "score": round(1.0 - dist, 4)
                })
        return formatted_results