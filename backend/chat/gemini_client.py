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


_GEN_MODEL_CANDIDATES = [
    "gemini-2.0-flash",
    "gemini-1.5-flash",
    "gemini-2.5-flash",
]

_EMBED_MODEL_CANDIDATES = [
    "text-embedding-004",
    "embedding-001",
]


def _generate_with_fallback(prompt: str):
    client = _get_client()
    models_to_try = [settings.GEMINI_MODEL] + [
        m for m in _GEN_MODEL_CANDIDATES if m != settings.GEMINI_MODEL
    ]

    last_exc = None
    for model_name in models_to_try:
        try:
            def _do(m=model_name):
                return client.models.generate_content(model=m, contents=prompt)
            return _call_with_retry(_do, max_retries=2, max_delay=15)
        except genai_errors.ClientError as e:
            last_exc = e
            if "404" in str(e) or "NOT_FOUND" in str(e):
                logger.warning("Generation model %s not found, trying fallback...", model_name)
                continue
            raise
    if last_exc:
        raise last_exc


def _embed_with_fallback(contents, task_type: str):
    client = _get_client()
    config = types.EmbedContentConfig(
        task_type=task_type,
        output_dimensionality=settings.EMBEDDING_DIMENSIONS,
    )
    models_to_try = [settings.GEMINI_EMBEDDING_MODEL] + [
        m for m in _EMBED_MODEL_CANDIDATES if m != settings.GEMINI_EMBEDDING_MODEL
    ]

    last_exc = None
    for model_name in models_to_try:
        # Try 1: with config
        try:
            def _do1(m=model_name):
                return client.models.embed_content(model=m, contents=contents, config=config)
            return _call_with_retry(_do1, max_retries=2, max_delay=15)
        except genai_errors.ClientError as e:
            last_exc = e
            if "404" in str(e) or "NOT_FOUND" in str(e):
                # Try 2: without config
                try:
                    def _do2(m=model_name):
                        return client.models.embed_content(model=m, contents=contents)
                    return _call_with_retry(_do2, max_retries=1, max_delay=10)
                except genai_errors.ClientError as e2:
                    last_exc = e2
                    logger.warning("Embedding model %s failed, trying next candidate...", model_name)
                    continue
            raise
    if last_exc:
        raise last_exc


def ask_question(context_text: str, question: str, history: list = None) -> str:
    """
    Answer a question grounded strictly in the provided context and previous chat history.
    """
    history_text = ""
    if history:
        turns = []
        for item in history:
            q = getattr(item, "question", None) if not isinstance(item, dict) else item.get("question")
            a = getattr(item, "answer", None) if not isinstance(item, dict) else item.get("answer")
            if q and a:
                turns.append(f"User: {q}\nAskDocs AI: {a}")
        if turns:
            history_text = "PREVIOUS CONVERSATION HISTORY:\n" + "\n---\n".join(turns) + "\n\n"

    prompt = (
        "You are AskDocs AI, an intelligent document question-answering assistant. "
        "Answer the user's question using ONLY the information in the "
        "retrieved excerpts below, keeping in mind the conversation history if relevant. "
        "Each excerpt is labeled with its source document and page number. "
        "If the answer isn't in the excerpts, say you couldn't find it in the uploaded documents. "
        "When you use a fact, mention which document/page it came from.\n\n"
        f"{history_text}"
        f"RETRIEVED EXCERPTS:\n{_truncate(context_text)}\n\n"
        f"QUESTION: {question}\n\nANSWER:"
    )

    response = _generate_with_fallback(prompt)
    return response.text.strip()


_EMBED_BATCH_SIZE = 20


def embed_documents(texts: list[str]) -> list[list[float]]:
    vectors = []
    for i in range(0, len(texts), _EMBED_BATCH_SIZE):
        batch = texts[i : i + _EMBED_BATCH_SIZE]
        response = _embed_with_fallback(batch, task_type="RETRIEVAL_DOCUMENT")
        vectors.extend([e.values for e in response.embeddings])
    return vectors


def embed_query(text: str) -> list[float]:
    response = _embed_with_fallback(text, task_type="RETRIEVAL_QUERY")
    return response.embeddings[0].values


def generate_summary(document_text: str) -> str:
    prompt = (
        "Summarize the following document clearly with key takeaways.\n"
        "Format the summary cleanly with brief bullet points.\n\n"
        f"DOCUMENT:\n{_truncate(document_text)}"
    )
    response = _generate_with_fallback(prompt)
    return response.text.strip()
