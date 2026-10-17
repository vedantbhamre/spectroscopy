"""Hybrid retrieval: Qdrant vector search (if embeddings are configured) + BM25, then FlashRank reranking.

BM25 always runs, so retrieval works without a Gemini key, Qdrant or network, and exact
technical terms (cm-1, ATR, ZrO2) are not lost to embedding fuzziness.
"""

import json
import math
import re
from collections import Counter
from functools import lru_cache

import logfire

from app.config import settings

_TOKEN = re.compile(r"[a-z0-9]+(?:[-–][a-z0-9]+)?")
STOP = set("the a an and or of to in for on with by is are be as at from that this it its can we our you your".split())


def _tokens(text: str) -> list[str]:
    return [t for t in _TOKEN.findall(text.lower()) if t not in STOP]


@lru_cache(maxsize=1)
def chunks() -> list[dict]:
    if not settings.CHUNKS_FILE.exists():
        return []
    return json.loads(settings.CHUNKS_FILE.read_text())


@lru_cache(maxsize=1)
def _bm25_index():
    docs = [Counter(_tokens(c["text"])) for c in chunks()]
    n = len(docs) or 1
    df: Counter = Counter()
    for d in docs:
        df.update(d.keys())
    idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}
    avg = sum(sum(d.values()) for d in docs) / n
    return docs, idf, avg


def bm25(query: str, limit: int = 15, k1: float = 1.5, b: float = 0.75) -> list[dict]:
    docs, idf, avg = _bm25_index()
    q = _tokens(query)
    scored = []
    for i, d in enumerate(docs):
        length = sum(d.values()) or 1
        s = sum(idf.get(t, 0) * d[t] * (k1 + 1) / (d[t] + k1 * (1 - b + b * length / avg)) for t in q if t in d)
        if s > 0:
            scored.append((s, i))
    scored.sort(reverse=True)
    return [{**chunks()[i], "score": s} for s, i in scored[:limit]]


def vector(query: str, limit: int = 15) -> list[dict]:
    from app.services.embedding import embed_query, embeddings_available
    from app.services.vectorstore import search

    if not embeddings_available():
        return []
    try:
        return search(embed_query(query), limit)
    except Exception as e:  # noqa: BLE001 - degrade to BM25 only
        logfire.warning("vector search unavailable: {err}", err=str(e))
        return []


_ranker = None


def rerank(query: str, candidates: list[dict], top_n: int) -> tuple[list[dict], str]:
    """FlashRank cross-encoder (local ONNX). Falls back to the fused order."""
    global _ranker
    if not candidates:
        return [], "none"
    try:
        from flashrank import Ranker, RerankRequest

        if _ranker is None:
            _ranker = Ranker(cache_dir=str(settings.PROCESSED_DIR.parent / ".flashrank"))
        passages = [{"id": i, "text": c["text"]} for i, c in enumerate(candidates)]
        ranked = _ranker.rerank(RerankRequest(query=query, passages=passages))
        return [{**candidates[r["id"]], "rerank": float(r["score"])} for r in ranked[:top_n]], "flashrank"
    except Exception as e:  # noqa: BLE001 - model download or runtime failure
        logfire.warning("FlashRank unavailable, using fused order: {err}", err=str(e))
        return candidates[:top_n], "fused"


def retrieve(queries: list[str], top_n: int = 8) -> tuple[list[dict], dict]:
    """Reciprocal-rank fusion of BM25 and vector hits over several query phrasings, then rerank."""
    fused: dict[str, float] = {}
    by_id: dict[str, dict] = {}
    used_vector = False
    for q in queries:
        lists = [bm25(q)]
        v = vector(q)
        if v:
            used_vector = True
            lists.append(v)
        for hits in lists:
            for rank, h in enumerate(hits):
                by_id[h["id"]] = h
                fused[h["id"]] = fused.get(h["id"], 0.0) + 1.0 / (60 + rank)
    candidates = [by_id[i] for i, _ in sorted(fused.items(), key=lambda x: -x[1])[:30]]
    top, how = rerank(" ".join(queries[:1]), candidates, top_n)
    return top, {"candidates": len(candidates), "vector": used_vector, "rerank": how}
