"""Expert-review rules P1–P10 (offline, no LLM)."""

import copy
import json

import pytest

from app.agents.nodes.responder import finalise
from app.gateway import LLMResult
from app.knowledge.page_tags import application_of, methods_of
from app.schemas import Citation, Question, Recommendation, Report
from app.services import review_rules as RR
from app.services.premises import Facts
from app.services.validators import label_transfers, validate_claims
from tests.test_graph import RESPONDER

MIR_QUOTE = "Vibrational spectroscopy in the mid-IR range (4000–400 cm-1) is one of the most informative methods of chemical analysis."


def _report(**over) -> Report:
    raw = copy.deepcopy(RESPONDER) | over
    return finalise(raw, checks=[], scenario_id=None)[0]


# P1
def test_provisional_certainty_phrase_is_rejected():
    raw = copy.deepcopy(RESPONDER) | {"answer": {"text": "Yes, MIR-ATR can meet the requirement and will achieve the accuracy."}}
    report, stats, _ = finalise(raw, checks=[], scenario_id=None)
    assert report.decisionStatus == "provisional" and stats["certainty_rejected"] >= 1
    assert not RR.CERTAINTY.search(report.answer.text) and not report.answer.text.lower().startswith("yes")
    assert "most promising first candidate to test" in report.answer.text or "not shown yet" in report.answer.text


# P2
def test_unanswered_decisive_unknown_is_asked():
    raw = copy.deepcopy(RESPONDER) | {"questions": []}
    facts = Facts(decisive_unknowns=["identity of the sample matrix"])
    report, stats, _ = finalise(raw, checks=[], scenario_id=None, facts=facts)
    open_q = [q for q in report.questions if q.status == "open"]
    assert open_q and any("sample matrix" in q.text for q in open_q) and stats["decisive_open"] == 1
    assert "identity of the sample matrix" in report.requirements.decisive


def test_decisive_unknown_in_final_report_is_a_risk_and_a_plan_step():
    facts = Facts(decisive_unknowns=["identity of the sample matrix"])
    report, _, _ = finalise(copy.deepcopy(RESPONDER), checks=[], scenario_id=None, facts=facts, final=True)
    assert not [q for q in report.questions if q.status == "open"]
    assert any("sample matrix" in r for r in report.risks) and any("sample matrix" in s for s in report.feasibility.steps)


# P3
def test_mid_ir_page_cited_for_nir_claim_is_rejected():
    rep = Report.model_validate({**copy.deepcopy(RESPONDER), "decisionStatus": "provisional", "sources": [],
                                 "recommendations": [], "requirements": {"stated": ["x"], "unknowns": []}})
    rep.recommendations = [Recommendation(method="NIR", methodIds=["NIR"], role="primary", reason="Mid-IR spectroscopy is one of the most informative methods of chemical analysis.",
                                          citations=[Citation(source="S01", page="9", quote=MIR_QUOTE, check="verified")])]
    stats = validate_claims(rep, recite_fn=None)
    assert stats["method_mismatch"] == 1 and not rep.recommendations


# P4
@pytest.mark.parametrize("page", [5, 9, 10, 11, 12])
def test_method_description_pages_have_no_application(page):
    assert application_of("S01", str(page)) is None


@pytest.mark.parametrize("src,page,domain", [("S01", 15, "pharmaceutical solids"), ("S01", 17, "dairy and food"),
                                             ("S02", 13, "petroleum and chemicals"), ("S03", 2, "medical and tissue")])
def test_application_pages_are_tagged(src, page, domain):
    assert application_of(src, str(page)) == domain


def test_general_page_never_produces_a_transfer_label():
    rep = _report()
    rep.recommendations = []
    rep.concept.citations = [Citation(source="S01", page="5", quote="x", check="verified"),
                             Citation(source="S01", page="10", quote="x", check="verified")]
    rep.assumptions = []
    assert label_transfers(rep, "medical and tissue") == 0 and not any(c.transfer for c in rep.concept.citations)


def test_page_method_tags():
    assert methods_of("S01", 9) == frozenset({"MIR_ATR"}) and methods_of("S01", 11) == frozenset({"RAMAN"})
    assert methods_of("S01", 5) == frozenset({"general"})


# P6
def test_fact_extraction_ignores_question_text(monkeypatch):
    import app.agents.nodes.analyst as analyst

    q = "Do you have a Karl Fischer titration available as a reference method?"
    msg = f"Answers to your questions:\n- Q: {q}\n  A: yes, we have a lab method"
    payload = {"stated": [{"fact": "Karl Fischer titration available", "quote": "Karl Fischer titration"},
                          {"fact": "A lab reference method is available", "quote": "we have a lab method"}],
               "unknowns": [], "target_variables": ["water"]}
    monkeypatch.setattr(analyst, "chat", lambda *a, **k: LLMResult(text=json.dumps(payload), model="fake", via="test", ms=1))
    state = {"messages": [{"role": "user", "content": "Water in oil, inline."}, {"role": "assistant", "content": "Questions."},
                          {"role": "user", "content": msg}],
             "answers": [{"id": "q1", "question": q, "status": "answered", "answer": "yes, we have a lab method"}],
             "report": {"questions": [Question(id="q1", text=q).model_dump()], "requirements": {"stated": [], "unknowns": []}}}
    facts = analyst.analyst_node(state)["facts"]
    assert not any("karl fischer" in f.lower() for f in facts["stated"])
    assert any("lab" in f.lower() for f in facts["stated"])


# P7
def test_no_duplicated_requirement_rows(monkeypatch):
    import app.agents.nodes.analyst as analyst

    payload = {"stated": [{"fact": "Milk line at 4 °C", "quote": "milk line"}, {"fact": "milk line at 4 °C", "quote": "milk line"},
                          {"fact": "Milk line, 4 °C", "quote": "milk line"}], "unknowns": [], "target_variables": ["fat"]}
    monkeypatch.setattr(analyst, "chat", lambda *a, **k: LLMResult(text=json.dumps(payload), model="fake", via="test", ms=1))
    facts = analyst.analyst_node({"messages": [{"role": "user", "content": "We run a milk line."}]})["facts"]
    assert len(facts["stated"]) == 1


# P8
def test_excitation_never_used_for_absorption_methods():
    rep = _report()
    rep.spectralRange.summary = "NIR excitation range 780–2500 nm. Raman excitation at 785 nm."
    assert RR.fix_excitation(rep) == 1
    assert "NIR absorption range" in rep.spectralRange.summary and "Raman excitation at 785 nm" in rep.spectralRange.summary


# P9
def test_plan_follows_lab_validation_inline_decision_order():
    rep = _report()
    rep.feasibility.steps = ["Install the probe in-line at the pilot plant.", "Build a PLS model and validate it on held-out batches.",
                             "Measure laboratory samples to learn the signal."]
    rep.feasibility.decisionBasis = "Acceptance criteria agreed with the customer."
    RR.order_plan(rep, medical=False)
    phases = [RR._phase(s) for s in rep.feasibility.steps]
    assert phases == sorted(phases) and phases[0] == 1
    assert "threshold" in rep.feasibility.decisionBasis and not any("patient" in s for s in rep.feasibility.steps)


# P10
def test_unsupported_hardware_detail_goes_to_points_to_confirm():
    rep = _report()
    rep.concept.summary = "A diffuse reflection probe in the line. The probe uses a sapphire window rated to 100 bar."
    rep.recommendations = [Recommendation(method="NIR", methodIds=["NIR"], role="primary", reason="x", citations=[])]
    assert RR.validate_hardware(rep) >= 1
    assert "sapphire" not in rep.concept.summary and any("sapphire" in p for p in rep.pointsToConfirm)


def test_path_length_outside_table1_is_flagged():
    assert RR._path_ok("NIR transmission probe with a path length of 2 mm", ["NIR"])
    assert not RR._path_ok("ATR probe with an optical path of 2 mm", ["MIR_ATR"])
