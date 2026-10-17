"""Gemini embeddings (gemini-embedding-2-preview, 3072-dim) with retry on rate limits."""

import time

from app.config import settings

BATCH_SIZE = 50
_model = None


def embeddings_available() -> bool:
    return bool(settings.GEMINI_API_KEY)


def _get():
    global _model
    if _model is None:
        from langchain_google_genai import GoogleGenerativeAIEmbeddings

        _model = GoogleGenerativeAIEmbeddings(model=settings.EMBEDDING_MODEL, google_api_key=settings.GEMINI_API_KEY)
    return _model


def _retry(fn, *args):
    for attempt in range(4):
        try:
            return fn(*args)
        except Exception as e:  # noqa: BLE001 - SDK raises several error types
            err = str(e).lower()
            if attempt < 3 and any(x in err for x in ("429", "rate", "quota", "resource_exhausted")):
                time.sleep(2**attempt)
                continue
            raise


def embed_query(text: str) -> list[float]:
    return _retry(_get().embed_query, text)


def embed_texts(texts: list[str]) -> list[list[float]]:
    out: list[list[float]] = []
    for i in range(0, len(texts), BATCH_SIZE):
        out.extend(_retry(_get().embed_documents, texts[i : i + BATCH_SIZE]))
    return out
