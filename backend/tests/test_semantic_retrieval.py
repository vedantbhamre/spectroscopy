"""Semantic retrieval (local BGE-base vectors fused with BM25), offline after the one-time model download.

The enquiries below were written for this test in wording the source-guide router does not key on, so keyword routing
alone misses their application pages (recall ~0.64). Ground truth is evaluation data, never read by the pipeline.
"""

import pytest

from app.config import settings
from app.knowledge.applications import tag
from app.services import local_embedding
from app.services.retrieval import retrieve
from tests.test_retrieval import recall

pytestmark = pytest.mark.skipif(not local_embedding.available(), reason="fastembed not installed")

UNSEEN = [
    ("We make pills from a mixed powder and want to see the drug level before compression without sending samples to the lab.", {("S01", 14), ("S01", 15)}),
    ("How much moisture is in the lubricating oil circulating in our gearbox loop?", {("S02", 13)}),
    ("We produce an ice cream mix and want the solids and fat level continuously.", {("S01", 17), ("S01", 18)}),
    ("Microbial growth in a stirred tank fed with sugar: can light tell us how fast the organisms multiply?", {("S01", 16)}),
    ("Doctors want to tell malignant from benign samples during an operation.", {("S03", 1), ("S01", 13)}),
    ("Our plastic compounder melts pellets with an active additive; can we check the additive level in the melt?", {("S02", 14)}),
    ("Which glass cable carries mid-infrared light over a long distance?", {("S02", 6), ("S02", 7)}),
]


def _unseen_recall() -> float:
    scores = []
    for q, truth in UNSEEN:
        docs, _ = retrieve([], top_n=settings.RETRIEVE_TOP_N, routing_text=q)
        scores.append(len(truth & {(d["source"], int(d["page"])) for d in docs}) / len(truth))
    return sum(scores) / len(scores)


@pytest.fixture
def semantic(monkeypatch):
    monkeypatch.setattr(settings, "EMBEDDINGS", "local")


def test_unseen_wording_is_mostly_not_routed():
    # Written to miss the router; only the clinical one is now caught by the medical vocabulary.
    assert sum(bool(tag(q)) for q, _ in UNSEEN) <= 1


def test_vectors_reach_pages_keywords_miss(semantic):
    docs, info = retrieve([], top_n=8, routing_text=UNSEEN[0][0])
    assert info["vector"]
    assert _unseen_recall() >= 0.95  # routing + BM25 alone: ~0.64


def test_vectors_keep_development_recall(semantic):
    r = recall()
    assert sum(r.values()) / len(r) >= 0.85, r
