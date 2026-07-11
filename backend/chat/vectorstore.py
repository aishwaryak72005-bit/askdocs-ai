"""
Thin wrapper around a persistent Chroma collection used for RAG retrieval.
One collection holds chunks from every user's documents; user_id and
document_id are stored as metadata and used to filter queries so users
only ever retrieve their own content.
"""
import chromadb
from django.conf import settings

_client = None
_collection = None

COLLECTION_NAME = "documind_chunks"


def _get_collection():
    global _client, _collection
    if _collection is None:
        _client = chromadb.PersistentClient(
            path=settings.CHROMA_DB_DIR,
            settings=chromadb.config.Settings(anonymized_telemetry=False),
        )
        _collection = _client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


def add_chunks(document_id: int, user_id: int, file_name: str, chunks: list[dict], embeddings: list[list[float]]):
    """
    chunks: list of {"text": str, "page": int}
    embeddings: parallel list of embedding vectors
    """
    if not chunks:
        return
    collection = _get_collection()
    ids = [f"doc{document_id}_chunk{i}" for i in range(len(chunks))]
    documents = [c["text"] for c in chunks]
    metadatas = [
        {"user_id": user_id, "document_id": document_id, "file_name": file_name, "page": c["page"]}
        for c in chunks
    ]
    collection.add(ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas)


def delete_document_chunks(document_id: int):
    collection = _get_collection()
    collection.delete(where={"document_id": document_id})


def query(query_embedding: list[float], user_id: int, document_id: int = None, top_k: int = 6):
    """
    Returns a list of {"text": str, "file_name": str, "page": int, "distance": float}
    ordered by relevance, scoped to the given user (and optionally a single document).
    """
    collection = _get_collection()
    where = {"user_id": user_id}
    if document_id:
        where = {"$and": [{"user_id": user_id}, {"document_id": document_id}]}

    count = collection.count()
    if count == 0:
        return []

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(top_k, count),
        where=where,
    )

    if not results["documents"] or not results["documents"][0]:
        return []

    hits = []
    for text, meta, dist in zip(
        results["documents"][0], results["metadatas"][0], results["distances"][0]
    ):
        hits.append(
            {
                "text": text,
                "file_name": meta["file_name"],
                "page": meta["page"],
                "distance": dist,
            }
        )
    return hits
