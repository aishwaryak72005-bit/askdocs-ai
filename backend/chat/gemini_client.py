import re
import time
import logging

from django.conf import settings
from google import genai
from google.genai import types
from google.genai import errors as genai_errors

logger = logging.getLogger(__name__)

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = genai.Client(api_key=settings.GEMINI_API_KEY)
    return _client


MAX_CONTEXT_CHARS = 100_000  # keep prompts within a safe context size


def _truncate(text: str) -> str:
    if len(text) > MAX_CONTEXT_CHARS:
        return text[:MAX_CONTEXT_CHARS] + "\n...[truncated]..."
    return text


# ----------------------------------------------------------------------
# Retry with backoff for rate limits (429 RESOURCE_EXHAUSTED) and
# transient server errors (503 UNAVAILABLE etc).
#
# Gemini's free tier is easy to hit (100 embedding requests/minute), and
# when it's exceeded the API tells you exactly how long to wait via a
# "retryDelay" field in the error — e.g. "Please retry in 57.3s". This
# respects that hint instead of guessing with blind exponential backoff,
# and only falls back to backoff when no hint is given.
# ----------------------------------------------------------------------

_RETRYABLE_STATUS_CODES = {429, 503}
_RETRY_DELAY_RE = re.compile(r"retryDelay['\"]?\s*[:=]\s*['\"]?(\d+(?:\.\d+)?)s")
_RETRY_IN_RE = re.compile(r"retry in ([\d.]+)s")


def _is_retryable(error: Exception) -> bool:
    code = getattr(error, "code", None)
    if code in _RETRYABLE_STATUS_CODES:
        return True
    text = str(error)
    return "RESOURCE_EXHAUSTED" in text or "UNAVAILABLE" in text or "429" in text


def _suggested_delay(error: Exception) -> float | None:
    text = str(error)
    for pattern in (_RETRY_DELAY_RE, _RETRY_IN_RE):
        match = pattern.search(text)
        if match:
            return float(match.group(1))
    return None


def _call_with_retry(func, *, max_retries: int, max_delay: float, **kwargs):
    """
    Calls func(**kwargs), retrying on rate-limit/transient errors.
    Waits the server-suggested delay when available (capped at max_delay),
    otherwise falls back to exponential backoff (2s, 4s, 8s, ...).
    Re-raises the original error once retries are exhausted or the error
    isn't retryable (e.g. bad API key — no point waiting on those).
    """
    attempt = 0
    while True:
        try:
            return func(**kwargs)
        except genai_errors.ClientError as e:
            if not _is_retryable(e) or attempt >= max_retries:
                raise
            delay = _suggested_delay(e)
            if delay is None:
                delay = min(2 ** (attempt + 1), max_delay)
            else:
                delay = min(delay, max_delay)
            logger.warning(
                "Gemini API rate-limited (attempt %d/%d), retrying in %.1fs",
                attempt + 1, max_retries, delay,
            )
            time.sleep(delay)
            attempt += 1


def ask_question(context_text: str, question: str) -> str:
    """
    Answer a question grounded strictly in the provided context.
    context_text is expected to already be a set of labeled, retrieved
    chunks (see chat/retrieval.py), not a whole document.
    """
    client = _get_client()
    prompt = (
        "You are AskDocs AI, a document question-answering assistant. "
        "Answer the user's question using ONLY the information in the "
        "retrieved excerpts below. Each excerpt is labeled with its source "
        "document and page number. If the answer isn't in the excerpts, say "
        "you couldn't find it in the uploaded documents. When you use a "
        "fact, mention which document/page it came from.\n\n"
        f"RETRIEVED EXCERPTS:\n{_truncate(context_text)}\n\n"
        f"QUESTION: {question}\n\nANSWER:"
    )

    def _do():
        return client.models.generate_content(model=settings.GEMINI_MODEL, contents=prompt)

    response = _call_with_retry(_do, max_retries=3, max_delay=30)
    return response.text.strip()


_EMBED_BATCH_SIZE = 20


def embed_documents(texts: list[str]) -> list[list[float]]:
    """Embed a batch of document chunks for storage (RETRIEVAL_DOCUMENT task)."""
    client = _get_client()
    config = types.EmbedContentConfig(
        task_type="RETRIEVAL_DOCUMENT",
        output_dimensionality=settings.EMBEDDING_DIMENSIONS,
    )
    vectors = []
    for i in range(0, len(texts), _EMBED_BATCH_SIZE):
        batch = texts[i : i + _EMBED_BATCH_SIZE]

        def _do(batch=batch):
            return client.models.embed_content(
                model=settings.GEMINI_EMBEDDING_MODEL, contents=batch, config=config
            )

        # Free-tier quota resets fairly quickly but can suggest waits of
        # a minute or more between batches — worth waiting out during a
        # one-time upload/indexing pass rather than failing the whole doc.
        response = _call_with_retry(_do, max_retries=4, max_delay=65)
        vectors.extend([e.values for e in response.embeddings])
    return vectors


def embed_query(text: str) -> list[float]:
    """Embed a single user question for retrieval (RETRIEVAL_QUERY task)."""
    client = _get_client()
    config = types.EmbedContentConfig(
        task_type="RETRIEVAL_QUERY",
        output_dimensionality=settings.EMBEDDING_DIMENSIONS,
    )

    def _do():
        return client.models.embed_content(
            model=settings.GEMINI_EMBEDDING_MODEL, contents=text, config=config
        )

    # Kept shorter than embed_documents — this happens inline while a user
    # is waiting on an answer, so fail fast with a clear error instead of
    # making them stare at a spinner for a minute.
    response = _call_with_retry(_do, max_retries=2, max_delay=15)
    return response.embeddings[0].values


def generate_summary(document_text: str) -> str:
    """Generate a short summary plus key points for a document."""
    client = _get_client()
    prompt = (
        "Summarize the following document in 3-5 sentences, then list 3-6 key "
        "points as bullet points.\n\n"
        f"DOCUMENT:\n{_truncate(document_text)}"
    )

    def _do():
        return client.models.generate_content(model=settings.GEMINI_MODEL, contents=prompt)

    response = _call_with_retry(_do, max_retries=3, max_delay=30)
    return response.text.strip()
