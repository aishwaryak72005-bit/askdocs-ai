import re
import time
import math
import hashlib
import logging

from django.conf import settings
from google import genai
from google.genai import errors as genai_errors

logger = logging.getLogger(__name__)

_client = None


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
    text = str(error)
    return "RESOURCE_EXHAUSTED" in text or "UNAVAILABLE" in text or "429" in text


def _call_with_retry(func, max_retries=2, max_delay=15):
    attempt = 0
    while True:
        try:
            return func()
        except genai_errors.ClientError as e:
            if not _is_retryable(e) or attempt >= max_retries:
                raise
            delay = min(2 ** (attempt + 1), max_delay)
            logger.warning("Gemini rate-limited, retrying in %.1fs", delay)
            time.sleep(delay)
            attempt += 1


# ===========================================================
# LOCAL EMBEDDING (does not need any API key or internet)
# Uses TF-IDF-style hashing into a 768-dim unit vector
# ===========================================================
def _local_embed(text: str, dim: int = 768) -> list:
    """
    Deterministic 768-dim hash embedding. Works offline, no API needed.
    Consistent across uploads and queries — so search always works.
    """
    words = re.findall(r'\w+', text.lower())
    vector = [0.0] * dim
    if not words:
        return vector
    # Use bigrams too for better matching
    tokens = words + [f"{words[i]}_{words[i+1]}" for i in range(len(words)-1)]
    for token in tokens:
        h = int(hashlib.sha256(token.encode('utf-8')).hexdigest(), 16)
        idx = h % dim
        val = 1.0 if ((h >> 1) % 2 == 0) else -1.0
        vector[idx] += val
    # L2-normalise
    norm = math.sqrt(sum(x * x for x in vector))
    if norm > 0:
        vector = [x / norm for x in vector]
    return vector


# ===========================================================
# GENERATION — uses Gemini flash with fallback
# ===========================================================
_GEN_CANDIDATES = [
    "gemini-2.0-flash",
    "gemini-1.5-flash",
]


def ask_question(context_text: str, question: str, history: list = None) -> str:
    """Answer a question grounded in provided document context."""
    client = _get_client()

    history_text = ""
    if history:
        turns = []
        for item in history:
            q = getattr(item, "question", None) if not isinstance(item, dict) else item.get("question")
            a = getattr(item, "answer", None) if not isinstance(item, dict) else item.get("answer")
            if q and a:
                turns.append(f"User: {q}\nAskDocs AI: {a}")
        if turns:
            history_text = "PREVIOUS CONVERSATION:\n" + "\n---\n".join(turns) + "\n\n"

    prompt = (
        "You are AskDocs AI, an intelligent document question-answering assistant.\n"
        "Answer the user's question using ONLY the retrieved excerpts below.\n"
        "Each excerpt has its source document and page number. "
        "Cite the source when you use a fact. "
        "If the answer is not in the excerpts, say you couldn't find it.\n\n"
        f"{history_text}"
        f"RETRIEVED EXCERPTS:\n{_truncate(context_text)}\n\n"
        f"QUESTION: {question}\n\nANSWER:"
    )

    model_names = list(dict.fromkeys([settings.GEMINI_MODEL] + _GEN_CANDIDATES))
    last_exc = None
    for model_name in model_names:
        try:
            def _do(m=model_name):
                return client.models.generate_content(model=m, contents=prompt)
            resp = _call_with_retry(_do)
            return resp.text.strip()
        except Exception as e:
            last_exc = e
            if "404" in str(e) or "NOT_FOUND" in str(e):
                logger.warning("Generation model %s not found, trying next...", model_name)
                continue
            raise

    if last_exc:
        raise last_exc


# ===========================================================
# PUBLIC EMBEDDING API — uses local hashing (no Gemini needed)
# ===========================================================
def embed_documents(texts: list) -> list:
    """Embed a list of document texts using local hashing."""
    return [_local_embed(t) for t in texts]


def embed_query(text: str) -> list:
    """Embed a query text using local hashing."""
    return _local_embed(text)


# ===========================================================
# SUMMARY GENERATION
# ===========================================================
def generate_summary(document_text: str) -> str:
    """Generate a bullet-point summary of the given document text."""
    client = _get_client()
    prompt = (
        "Summarize the following document clearly.\n"
        "Use clear bullet points for key takeaways.\n\n"
        f"DOCUMENT:\n{_truncate(document_text)}"
    )

    model_names = list(dict.fromkeys([settings.GEMINI_MODEL] + _GEN_CANDIDATES))
    last_exc = None
    for model_name in model_names:
        try:
            def _do(m=model_name):
                return client.models.generate_content(model=m, contents=prompt)
            resp = _call_with_retry(_do)
            return resp.text.strip()
        except Exception as e:
            last_exc = e
            if "404" in str(e) or "NOT_FOUND" in str(e):
                continue
            raise

    if last_exc:
        raise last_exc
