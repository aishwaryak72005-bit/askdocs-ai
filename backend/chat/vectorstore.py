"""
PostgreSQL-backed vector store for RAG retrieval.
Replaces Chroma so document chunks persist across Render deploys.
Uses cosine similarity computed in Python (no pgvector extension needed).
"""
import math
import logging
from django.db import connection

logger = logging.getLogger(__name__)

_table_ready = False


def _ensure_table():
    global _table_ready
    if _table_ready:
        return
    with connection.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS chat_vectorchunk (
                id          SERIAL PRIMARY KEY,
                chunk_id    TEXT UNIQUE NOT NULL,
                user_id     INTEGER NOT NULL,
                document_id INTEGER NOT NULL,
                file_name   TEXT NOT NULL,
                page        INTEGER NOT NULL,
                content     TEXT NOT NULL,
                embedding   TEXT NOT NULL
            )
        """)
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_vectorchunk_user ON chat_vectorchunk (user_id)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_vectorchunk_doc ON chat_vectorchunk (document_id)"
        )
    _table_ready = True


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------
def _dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def _cosine_similarity(a, b):
    dot = _dot(a, b)
    mag_a = math.sqrt(_dot(a, a))
    mag_b = math.sqrt(_dot(b, b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


def _vec_to_str(vec):
    return ",".join(f"{v:.6f}" for v in vec)


def _str_to_vec(s):
    return [float(x) for x in s.split(",")]


# ------------------------------------------------------------------
# Public API (same interface as the old Chroma wrapper)
# ------------------------------------------------------------------
def add_chunks(document_id: int, user_id: int, file_name: str, chunks: list, embeddings: list):
    """Store document chunks with their embeddings in PostgreSQL."""
    _ensure_table()
    if not chunks:
        return
    with connection.cursor() as cur:
        for i, (chunk, vec) in enumerate(zip(chunks, embeddings)):
            chunk_id = f"doc{document_id}_chunk{i}"
            cur.execute(
                """
                INSERT INTO chat_vectorchunk
                    (chunk_id, user_id, document_id, file_name, page, content, embedding)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (chunk_id) DO UPDATE SET
                    content   = EXCLUDED.content,
                    embedding = EXCLUDED.embedding
                """,
                [chunk_id, user_id, document_id, file_name, chunk["page"], chunk["text"], _vec_to_str(vec)],
            )


def delete_document_chunks(document_id: int):
    """Remove all chunks for a document."""
    _ensure_table()
    with connection.cursor() as cur:
        cur.execute("DELETE FROM chat_vectorchunk WHERE document_id = %s", [document_id])


def query(query_embedding: list, user_id: int, document_id: int = None, top_k: int = 6):
    """Return top-k most relevant chunks for the query, scoped to the user."""
    _ensure_table()
    with connection.cursor() as cur:
        if document_id:
            cur.execute(
                "SELECT content, file_name, page, embedding FROM chat_vectorchunk "
                "WHERE user_id = %s AND document_id = %s",
                [user_id, document_id],
            )
        else:
            cur.execute(
                "SELECT content, file_name, page, embedding FROM chat_vectorchunk "
                "WHERE user_id = %s",
                [user_id],
            )
        rows = cur.fetchall()

    if not rows:
        return []

    scored = []
    for content, file_name, page, emb_str in rows:
        vec = _str_to_vec(emb_str)
        sim = _cosine_similarity(query_embedding, vec)
        scored.append((sim, content, file_name, page))

    scored.sort(key=lambda x: x[0], reverse=True)

    return [
        {"text": content, "file_name": file_name, "page": page, "distance": 1 - sim}
        for sim, content, file_name, page in scored[:top_k]
    ]
