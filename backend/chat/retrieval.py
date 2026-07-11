from django.conf import settings
from . import vectorstore
from .gemini_client import embed_query


def retrieve_context(question: str, user_id: int, document_id: int = None):
    """
    Embeds the question, retrieves the most relevant chunks from the vector
    store, and formats them into a labeled context string for the LLM plus
    a list of source citations for the API response.

    Returns (context_text, sources) where sources is a list of
    {"file_name": str, "page": int} with duplicates removed, in relevance order.
    """
    query_vector = embed_query(question)
    hits = vectorstore.query(
        query_vector,
        user_id=user_id,
        document_id=document_id,
        top_k=settings.RETRIEVAL_TOP_K,
    )

    if not hits:
        return "", []

    context_parts = []
    seen = set()
    sources = []
    for hit in hits:
        label = f"[{hit['file_name']}, page {hit['page']}]"
        context_parts.append(f"{label}\n{hit['text']}")
        key = (hit["file_name"], hit["page"])
        if key not in seen:
            seen.add(key)
            sources.append({"file_name": hit["file_name"], "page": hit["page"]})

    return "\n\n".join(context_parts), sources
