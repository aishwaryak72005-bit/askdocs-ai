import re
import time
import math
import hashlib
import logging

from django.conf import settings
from google import genai
from google.genai import types
from google.genai import errors as genai_errors

logger = logging.getLogger(__name__)

_client = None
_discovered_embed_model = None
_discovered_gen_model = None


def _get_client():
    global _client
    if _client is None:
        _client = genai.Client(api_key=settings.GEMINI_API_KEY)
    return _client


MAX_CONTEXT_CHARS = 100_000


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
            logger.warning("Gemini API rate-limited (attempt %d/%d), retrying in %.1fs", attempt + 1, max_retries, delay)
            time.sleep(delay)
            attempt += 1


def _local_fallback_embed(text: str, dim: int = 768) -> list[float]:
    """
    Deterministic word-hash embedding fallback if Gemini embedding API is unavailable on the user's API key.
    """
    words = re.findall(r'\w+', text.lower())
    vector = [0.0] * dim
    if not words:
        return vector
    for word in words:
        h = int(hashlib.md5(word.encode('utf-8')).hexdigest(), 16)
        idx = h % dim
        val = 1.0 if (h % 2 == 0) else -1.0
        vector[idx] += val
    
    norm = math.sqrt(sum(x * x for x in vector))
    if norm > 0:
        vector = [x / norm for x in vector]
    return vector


def _discover_models():
    global _discovered_embed_model, _discovered_gen_model
    if _discovered_embed_model and _discovered_gen_model:
        return _discovered_embed_model, _discovered_gen_model

    client = _get_client()
    try:
        models = list(client.models.list_models())
        for m in models:
            name = getattr(m, "name", str(m))
            clean_name = name.replace("models/", "")
            methods = getattr(m, "supported_generation_methods", []) or getattr(m, "supported_actions", [])
            
            if not _discovered_embed_model:
                if "embedContent" in str(methods) or "embed" in clean_name:
                    _discovered_embed_model = clean_name
            
            if not _discovered_gen_model:
                if "generateContent" in str(methods) and ("flash" in clean_name or "gemini" in clean_name):
                    _discovered_gen_model = clean_name
    except Exception as e:
        logger.warning("Dynamic model discovery warning: %s", e)

    if not _discovered_embed_model:
        _discovered_embed_model = settings.GEMINI_EMBEDDING_MODEL or "text-embedding-004"
    if not _discovered_gen_model:
        _discovered_gen_model = settings.GEMINI_MODEL or "gemini-2.0-flash"

    return _discovered_embed_model, _discovered_gen_model


def _generate_with_fallback(prompt: str):
    client = _get_client()
    disc_embed, disc_gen = _discover_models()
    
    candidates = [disc_gen, "gemini-2.0-flash", "gemini-1.5-flash", "gemini-2.5-flash"]
    seen = set()
    models_to_try = []
    for c in candidates:
        if c and c not in seen:
            seen.add(c)
            models_to_try.append(c)

    last_exc = None
    for model_name in models_to_try:
        try:
            def _do(m=model_name):
                return client.models.generate_content(model=m, contents=prompt)
            return _call_with_retry(_do, max_retries=2, max_delay=15)
        except Exception as e:
            last_exc = e
            if "404" in str(e) or "NOT_FOUND" in str(e):
                logger.warning("Generation model %s not found, trying fallback...", model_name)
                continue
            raise
    if last_exc:
        raise last_exc


def _embed_single(text: str, task_type: str) -> list[float]:
    client = _get_client()
    disc_embed, _ = _discover_models()
    
    candidates = [disc_embed, "text-embedding-004", "embedding-001", "text-multilingual-embedding-002"]
    seen = set()
    models_to_try = []
    for c in candidates:
        if c and c not in seen:
            seen.add(c)
            models_to_try.append(c)

    config = types.EmbedContentConfig(
        task_type=task_type,
        output_dimensionality=settings.EMBEDDING_DIMENSIONS,
    )

    for model_name in models_to_try:
        # Try 1: with config
        try:
            def _do1(m=model_name):
                return client.models.embed_content(model=m, contents=text, config=config)
            resp = _call_with_retry(_do1, max_retries=1, max_delay=10)
            return resp.embeddings[0].values
        except Exception as e1:
            if "404" in str(e1) or "NOT_FOUND" in str(e1):
                # Try 2: without config
                try:
                    def _do2(m=model_name):
                        return client.models.embed_content(model=m, contents=text)
                    resp = _call_with_retry(_do2, max_retries=1, max_delay=10)
                    return resp.embeddings[0].values
                except Exception:
                    continue

    # Fallback to local embedding if API embedding fails
    logger.info("Using local embedding fallback for query")
    return _local_fallback_embed(text)


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
    for text in texts:
        vectors.append(_embed_single(text, task_type="RETRIEVAL_DOCUMENT"))
    return vectors


def embed_query(text: str) -> list[float]:
    return _embed_single(text, task_type="RETRIEVAL_QUERY")


def generate_summary(document_text: str) -> str:
    prompt = (
        "Summarize the following document clearly with key takeaways.\n"
        "Format the summary cleanly with brief bullet points.\n\n"
        f"DOCUMENT:\n{_truncate(document_text)}"
    )
    response = _generate_with_fallback(prompt)
    return response.text.strip()
