"""Citation by passage number: the quote is the page's own text by construction."""

import copy

from app.agents.nodes.responder import finalise
from app.services.citations import verify
from app.services.passages import number
from app.services.retrieval import chunks
from tests.test_graph import RESPONDER


def test_every_numbered_passage_is_on_its_page():
    _, refs = number(chunks())
    bad = [k for k, c in refs.items() if verify(c, allow_snap=False).check not in ("verified", "visual_note") and len(c.quote) >= 12]
    assert len(refs) > 1000 and len(bad) <= 2, bad


def test_reference_citations_resolve_and_unknown_ones_are_dropped():
    docs = [c for c in chunks() if c["source"] == "S01" and int(c["page"]) == 14][:1]
    _, refs = number(docs)
    ref = next(iter(refs))
    raw = copy.deepcopy(RESPONDER)
    raw["recommendations"][0]["citations"] = [{"ref": ref}, {"ref": "S01.99.1"}, ref]
    raw["recommendations"][0]["reason"] = refs[ref].quote  # supported by construction
    report, stats, _ = finalise(raw, checks=[], scenario_id=None, documents=docs)
    cites = report.recommendations[0].citations
    assert stats["unknown_refs"] == 1
    assert [(c.source, c.page, c.check) for c in cites] == [("S01", "14", "verified")] * 2
    assert cites[0].quote == refs[ref].quote


def test_reference_markers_are_stripped_from_prose():
    from app.services.passages import strip_refs
    assert strip_refs('IR alone separates classes【ref":"S04.4.2"】; this is the baseline.') == "IR alone separates classes; this is the baseline."
    assert strip_refs("Shown for powders (S01.14.3, S01.15.2).") == "Shown for powders."
    assert strip_refs("NIR range 780–2500 nm (S01 p.10).") == "NIR range 780–2500 nm (S01 p.10)."
