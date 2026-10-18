"""Retrieval: pages routed by the organisers' source guide, then BM25 (+ Qdrant vector search when embeddings are
configured) to fill the remaining slots, one chunk per page.

Measured against the organisers' "useful sources" for the development enquiries (tests/test_retrieval.py), keyword
search alone reached about a third of the useful pages: customers describe processes, not the method pages an
assessment rests on. Routing by application domain, method and topic closes that gap. BM25 always runs, so retrieval
works without a Gemini key, Qdrant or network. FlashRank reranking is optional (RERANK=flashrank): with the default
TinyBERT model it measured no gain and dropped correct pages, so it is off by default.
"""

import json
import math
import re
from collections import Counter
from functools import lru_cache

import logfire

from app.config import settings

_TOKEN = re.compile(r"[a-z0-9]+(?:[-–][a-z0-9]+)?")
# Function words and enquiry filler ("we want to investigate…"): they only reward generic, wordy pages.
STOP = set("""a about above after again all also am an and any are as at be because been before being between both but by can
could did do does doing during each few for from further had has have having he her here how i if in into is it its itself just
me more most my no nor not now of off on once only or other our ours out over own same she should so some such than that the
their them then there these they this those through to too under until up very was we were what when where which while who whom
why will with would you your want wants need needs like currently able know first make made use used using based handle send""".split())


def _tokens(text: str) -> list[str]:
    """Lower-case terms without function words; simple plurals folded (fibers → fiber)."""
    out = []
    for w in _TOKEN.findall(text.lower()):
        if w in STOP or len(w) < 2:
            continue
        out.append(w[:-1] if len(w) > 4 and w.endswith("s") and not w.endswith("ss") else w)
    return out


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


def routed_pages(text: str) -> list[tuple[str, int]]:
    """Pages the source guide points to for this enquiry: core method pages, application pages for its domain, method
    pages it names or its application pages discuss, and fibre pages when fibres or distance come up."""
    from app.knowledge import source_map as M
    from app.knowledge.applications import tag

    want = list(M.CORE)
    for domain in tag(text):
        want += M.DOMAIN_PAGES.get(domain, [])
    methods = {m for m, pat in M.METHOD_PATTERNS.items() if re.search(pat, text, re.I)}
    for src, pg in [w for w in want if w not in M.CORE]:
        page = " ".join(c["text"] for c in chunks() if c["source"] == src and int(c["page"]) == pg)
        methods |= {m for m, pat in M.METHOD_PATTERNS.items() if len(re.findall(pat, page, re.I)) >= M.METHOD_MENTIONS}
    want += [M.METHOD_PAGES[m] for m in sorted(methods)]
    if M.FIBRE_TOPIC.search(text):
        want += M.FIBRE_PAGES
    return list(dict.fromkeys(want))


def _best_chunk(src: str, pg: int, query: str) -> dict | None:
    """The chunk of a page that best matches the query (the page's first chunk if none does)."""
    page = [c for c in chunks() if c["source"] == src and int(c["page"]) == pg]
    if not page:
        return None
    q = set(_tokens(query))
    return max(page, key=lambda c: (len(q & set(_tokens(c["text"]))), c["kind"] == "table"))


def retrieve(queries: list[str], top_n: int = 8, routing_text: str = "") -> tuple[list[dict], dict]:
    """Routed pages first, then reciprocal-rank fusion of BM25 (and vector) hits over the query phrasings, one chunk
    per page, up to top_n pages."""
    query = " ".join([routing_text, *queries])
    picked: list[dict] = []
    seen: set[tuple[str, int]] = set()
    routed = routed_pages(routing_text or query)
    for src, pg in routed:
        c = _best_chunk(src, pg, query)
        if c and len(picked) < top_n:
            picked.append({**c, "routed": True})
            seen.add((src, pg))

    fused: dict[str, float] = {}
    by_id: dict[str, dict] = {}
    used_vector = False
    for q in [routing_text, *queries] if routing_text else queries:
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
    how = "off"
    if settings.RERANK == "flashrank":
        candidates, how = rerank(query, candidates, len(candidates))
    for c in candidates:
        key = (c["source"], int(c["page"]))
        if key not in seen and len(picked) < top_n:
            picked.append(c)
            seen.add(key)
    return picked, {"candidates": len(candidates), "vector": used_vector, "rerank": how, "routed": len([p for p in picked if p.get("routed")])}
