"""Second review round: calibration/reference premise, fact guard, cost claims, cited numbers, comparison candidate,
customer-fact questions (offline, no LLM)."""

import copy

from app.agents.nodes.responder import finalise
from app.schemas import Recommendation
from app.services import ledger as L
from app.services import review_rules as RR
from app.services.citations import verify
from app.services.premises import Facts, detect, run_checks
from app.services.retrieval import chunks
from tests.test_graph import RESPONDER


def _checks(text: str):
    return {c.id: c for c in run_checks(detect(text, Facts(target_variables=["water"])))}


# 1. calibration and reference method
def test_no_calibration_or_dropping_the_reference_is_flagged_and_cited():
    for text in ("Raman is calibration-free, so we can stop the lab titration.", "We want to replace our Karl Fischer test with the probe."):
        c = _checks(text)["calibration_and_reference"]
        assert c.status == "flag" and {x.page for x in c.citations} == {"5", "12"}
        assert all(verify(x).check == "verified" for x in c.citations)
    assert "calibration_and_reference" not in _checks("We keep our lab method as the reference.")


def test_reference_method_stays_until_validated():
    chk = _checks("NIR needs no calibration, so the lab method can be dropped.")["calibration_and_reference"]
    raw = copy.deepcopy(RESPONDER) | {"answer": {"text": "Not yet: NIR needs a calibration first."}}
    report, stats, _ = finalise(raw, checks=[chk], scenario_id=None)
    assert stats["reference_kept"] and "reference method stays" in report.answer.text
    assert any("reference method" in s and "until" in s for s in report.feasibility.steps)


# 2. fact guard
def test_unstated_customer_facts_move_to_assumptions():
    customer = "We measure water in oil in a pipeline."
    assert RR.unstated_fact("The line has two free ports for probes.", customer) == "two free ports"
    assert RR.unstated_fact("The oil stream is clear.", customer) == "clear"
    assert RR.unstated_fact("The analyzer is 50 m away.", customer) == "50 m"
    assert RR.unstated_fact("Assuming the oil is clear, transmission may work.", customer) is None
    assert RR.unstated_fact("The pipeline has one free port.", "There is one free port on the pipe.") is None
    rep = finalise(copy.deepcopy(RESPONDER) | {"answer": {"text": "Not yet. The oil is clear and there are two free ports."}},
                   checks=[], scenario_id=None, messages=[{"role": "user", "content": customer}])[0]
    assert "two free ports" not in rep.answer.text and any("Assumed, not stated" in a for a in rep.assumptions)


# 3. cost claims
def test_cheapest_claim_must_match_table1():
    rep = copy.deepcopy(finalise(copy.deepcopy(RESPONDER), checks=[], scenario_id=None)[0])
    rep.recommendations = [
        Recommendation(method="Raman", methodIds=["RAMAN"], role="primary", reason="Raman is the cheapest option. It sees the API."),
        Recommendation(method="NIR", methodIds=["NIR"], role="comparison", reason="NIR is shown for powders."),
    ]
    assert RR.check_cost_claims(rep) == 1 and "cheapest" not in rep.recommendations[0].reason
    rep.recommendations[0].reason, rep.recommendations[1].reason = "Raman sees the API.", "NIR is the lower-cost option."
    assert RR.check_cost_claims(rep) == 0  # Table 1: NIR average, Raman high


# 4. numbers on a retrieved page get a citation and are kept
def test_number_on_a_retrieved_page_is_cited_not_replaced():
    docs = [c for c in chunks() if c["source"] == "S01" and int(c["page"]) == 15]
    raw = copy.deepcopy(RESPONDER) | {"spectralRange": {"summary": "Raman with 785 nm excitation.", "citations": []}}
    report, stats, _ = finalise(raw, checks=[], scenario_id=None, documents=docs)
    assert "785 nm" in report.spectralRange.summary and stats["numbers"] == 0
    assert any(c.source == "S01" and c.page == "15" for c in report.sources)  # cited here or by another section


# 5. comparison candidate
def test_comparison_candidate_added_from_an_application_page():
    docs = [c for c in chunks() if c["source"] == "S01" and int(c["page"]) in (14, 15)]
    rep = copy.deepcopy(finalise(copy.deepcopy(RESPONDER), checks=[], scenario_id=None)[0])
    rep.decisionStatus = "provisional"
    rep.recommendations = [Recommendation(method="NIR", methodIds=["NIR"], role="primary", reason="x")]
    assert RR.ensure_comparison(rep, docs, ["API concentration"])
    comp = rep.recommendations[-1]
    assert comp.role == "comparison" and comp.limitations and verify(comp.citations[0]).check == "verified"
    rep.recommendations = rep.recommendations[:1]
    assert not RR.ensure_comparison(rep, docs, ["API concentration"], access_points=1)


# 6. questions
def test_questions_ask_customer_facts_not_design_parameters():
    assert L.asks_assistant_decision("What wavelength range should the spectrometer cover?")
    assert L.asks_assistant_decision("What path length should we use?")
    assert not L.asks_assistant_decision("What is the distance between the measuring point and the analyzer?")
    assert not L.asks_assistant_decision("Is the area a hazardous (ATEX) zone?")
    assert not L.asks_assistant_decision("What wavelength range does your existing analyzer cover?")


def test_double_numbering_is_stripped():
    assert [L.clean(x) for x in ("1. 1. What is the flow?", "Q2: 2) Which port?", "(3) Is it hot?")] == ["What is the flow?", "Which port?", "Is it hot?"]


def test_reference_sentence_added_even_when_the_answer_names_the_reference():
    chk = _checks("We want to stop the Karl Fischer titration.")["calibration_and_reference"]
    raw = copy.deepcopy(RESPONDER) | {"answer": {"text": "No: a calibration against the Karl Fischer reference is needed first."}}
    report, _, _ = finalise(raw, checks=[chk], scenario_id=None)
    assert "stays in use until" in report.answer.text


def test_independent_samples_count_as_held_out_validation():
    raw = copy.deepcopy(RESPONDER)
    raw["feasibility"] = {"steps": ["Measure lab samples.", "Validate the model on independent samples against the reference."], "decisionBasis": "x"}
    report, _, _ = finalise(raw, checks=[], scenario_id=None)
    assert not any("not used to build" in s for s in report.feasibility.steps)
