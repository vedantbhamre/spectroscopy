"""Local semantic search: BGE-base (BAAI/bge-base-en-v1.5, 768-dim, ONNX via fastembed), on CPU, no API key or network
after the first model download.

The knowledge base is a few hundred chunks, so the vectors live in memory and search is one matrix product. They are
cached in backend/.embeddings/ keyed by model and chunk content: embedding the chunks takes ~40 s once, loading the
cache well under a second. Each process (API server, batch script, tests) keeps its own copy, so there is no shared
database file to lock.

Chosen by measurement (no LLM tokens): with source-guide routing + BM25, adding BGE-base vectors kept recall of the
organisers' useful sources at 0.90 on the development enquiries and raised it from 0.64 to 0.93 on enquiries worded
without any of the routing keywords. BGE-small and mxbai-large scored the same; BGE-base is the middle ground in size.
"""

import hashlib
import json
import threading

import logfire
import numpy as np

from app.config import settings

_lock = threading.Lock()
_model = None
_matrix: np.ndarray | None = None


def available() -> bool:
    try:
        import fastembed  # noqa: F401
    except ImportError:
        return False
    return True


def _get_model():
    global _model
    if _model is None:
        from fastembed import TextEmbedding

        _model = TextEmbedding(model_name=settings.LOCAL_EMBEDDING_MODEL, cache_dir=str(settings.EMBEDDING_CACHE_DIR / "models"))
    return _model


def _normalise(m: np.ndarray) -> np.ndarray:
    return m / np.clip(np.linalg.norm(m, axis=-1, keepdims=True), 1e-12, None)


def _index(chunks: list[dict]) -> np.ndarray:
    global _matrix
    with _lock:
        if _matrix is not None and len(_matrix) == len(chunks):
            return _matrix
        key = hashlib.sha256(json.dumps([settings.LOCAL_EMBEDDING_MODEL, [c["text"] for c in chunks]]).encode()).hexdigest()[:16]
        path = settings.EMBEDDING_CACHE_DIR / f"{key}.npy"
        if path.exists():
            _matrix = np.load(path)
        else:
            with logfire.span("embedding {n} chunks with {model}", n=len(chunks), model=settings.LOCAL_EMBEDDING_MODEL):
                _matrix = _normalise(np.array(list(_get_model().passage_embed([c["text"] for c in chunks])), dtype=np.float32))
            path.parent.mkdir(parents=True, exist_ok=True)
            np.save(path, _matrix)
        return _matrix


def search(query: str, chunks: list[dict], limit: int = 15) -> list[dict]:
    """Chunks most similar to the query, best first, with cosine similarity as score."""
    if not chunks:
        return []
    m = _index(chunks)
    q = _normalise(np.array(list(_get_model().query_embed([query]))[0], dtype=np.float32))
    sims = m @ q
    return [{**chunks[i], "score": float(sims[i])} for i in np.argsort(-sims)[:limit]]


def warm(chunks: list[dict]) -> None:
    """Load the model and the chunk vectors ahead of the first request."""
    try:
        search("warm up", chunks, 1)
    except Exception as e:  # noqa: BLE001 - retrieval degrades to BM25 when vectors are unavailable
        logfire.warning("local embeddings unavailable: {err}", err=str(e))
