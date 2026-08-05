"""
Configuration for the GreenField AgroWorks Vector Database.
"""
#used lightweight embedding model instead of external API
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"

# db collection
COLLECTION_NAME = "chemical_safety_handbook"

#metric used: cosine similarity for semantic search
COLLECTION_METADATA = {
    "hnsw:space": "cosine"
}