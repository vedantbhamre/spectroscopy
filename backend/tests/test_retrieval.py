"""Retrieval quality, offline: share of the organisers' "useful sources" (AFS_Examples_and_Reference.docx, D01–D08)
that reach the composer. Guards against regressions; the ground truth is evaluation data, never read by the pipeline."""

import json
import re
from pathlib import Path

from app.config import settings
from app.services.retrieval import retrieve

USEFUL = {
    "D01": "S01 p.5, 10, 11, 14–15", "D02": "S01 p.5, 10, 17, 18", "D03": "S01 p.5, 10, 17, 18", "D04": "S01 p.5, 10, 11, 16",
    "D05": "S01 p.5, 16", "D06": "S01 p.6, 9, 10; S02 p.6, 13", "D07": "S01 p.5, 6, 10; S02 p.14", "D08": "S01 p.5, 6, 8–10; S04 p.1, 3, 4",
}
SCEN = {s["id"]: s["enquiry"] for s in json.loads((Path(__file__).parent.parent / "data" / "scenarios.json").read_text())}


def _pages(spec: str) -> set[tuple[str, int]]:
    out = set()
    for part in spec.split(";"):
        src, rest = part.strip().split(" p.")
        for tok in (x.strip() for x in rest.split(",")):
            a, _, b = tok.replace("–", "-").partition("-")
            out |= {(src, p) for p in range(int(a), int(b or a) + 1)}
    return out


def recall() -> dict[str, float]:
    out = {}
    for sid, spec in USEFUL.items():
        truth = _pages(spec)
        docs, _ = retrieve([], top_n=settings.RETRIEVE_TOP_N, routing_text=SCEN[sid])
        got = {(d["source"], int(d["page"])) for d in docs}
        out[sid] = len(truth & got) / len(truth)
    return out


def test_retrieval_reaches_the_useful_pages():
    r = recall()
    mean = sum(r.values()) / len(r)
    assert mean >= 0.95, r  # keyword search alone: ~0.35; routing with alphabetical method order and 8 pages: 0.90
    assert min(r.values()) >= 0.7, r


def test_one_chunk_per_page_and_budget():
    docs, info = retrieve(["water content petroleum"], top_n=8, routing_text=SCEN["D06"])
    pages = [(d["source"], int(d["page"])) for d in docs]
    assert len(pages) == len(set(pages)) <= 8
    assert ("S02", 13) in pages and ("S01", 9) in pages and info["routed"] >= 4


def test_routing_is_generic():
    # A new enquiry in a known domain reaches that domain's application pages without any case-specific rule.
    docs, _ = retrieve([], top_n=8, routing_text="Can we follow fat content of a yoghurt line with a fibre probe?")
    assert {("S01", 17), ("S01", 18), ("S02", 6)} <= {(d["source"], int(d["page"])) for d in docs}
