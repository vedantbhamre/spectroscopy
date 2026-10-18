"""Direct answer, source-scope dimensions and the feasibility-plan rules (offline, no LLM)."""

import copy

from app.agents.nodes.responder import finalise
from app.knowledge.source_scope import SCOPE
from app.services.citations import verify
from app.services.premises import Facts, run_checks
from tests.test_graph import RESPONDER


def _clinical_checks():
    return run_checks(Facts(use_context="clinical", cites_study_as_proof=True, target_variables=["tissue type"]))


def test_scope_quotes_are_on_their_pages():
    for dims in SCOPE.values():
        for _, c in dims:
            assert verify(c).check == "verified", c


def test_clinical_use_lists_every_scope_dimension():
    chk = next(c for c in _clinical_checks() if c.id == "source_scope")
    assert chk.status == "fail"
    for word in ("in vivo", "seven", "boundary", "prototypes", "aim"):
        assert word in chk.detail, word
    assert {c.page for c in chk.citations} >= {"1", "2", "3", "14"}


def test_answer_contradicting_a_failed_check_is_replaced():
    raw = copy.deepcopy(RESPONDER) | {"answer": {"text": "Yes, the study proves readiness.", "citations": []}}
    report, stats, _ = finalise(raw, checks=_clinical_checks(), scenario_id=None)
    assert stats["answer_written"] and report.answer.text.startswith("Not as asked")
    assert report.answer.citations and all(c.check == "verified" for c in report.answer.citations)


def test_cautious_answer_is_kept_and_cited():
    raw = copy.deepcopy(RESPONDER) | {"answer": {"text": "No: it is an in vitro study.", "sayInstead": "An in vitro study suggests it.", "citations": []}}
    report, stats, _ = finalise(raw, checks=_clinical_checks(), scenario_id=None, facts=Facts(cites_study_as_proof=True))
    assert not stats["answer_written"] and report.answer.text.startswith("No")
    assert report.answer.sayInstead and report.answer.citations


def test_missing_answer_gets_one():
    report, stats, _ = finalise(copy.deepcopy(RESPONDER), checks=[], scenario_id=None)
    assert stats["answer_written"] and report.answer.text


def test_feasibility_stops_before_later_stage_studies_and_validates_on_held_out_samples():
    raw = copy.deepcopy(RESPONDER)
    raw["feasibility"] = {"steps": ["Measure ex vivo samples against histology.", "Run a limited animal or pilot human study."],
                          "decisionBasis": "Criteria agreed first."}
    report, stats, _ = finalise(raw, checks=[], scenario_id=None)
    assert stats["later_stage_moved"] == 1
    assert not any("animal" in s for s in report.feasibility.steps)
    assert any("animal" in p for p in report.pointsToConfirm)
    assert any("not used to build" in s for s in report.feasibility.steps)


def test_say_instead_only_when_the_customer_wants_to_claim_something():
    raw = copy.deepcopy(RESPONDER) | {"answer": {"text": "Not yet.", "sayInstead": "Something to say."}}
    msgs = [{"role": "user", "content": "Which probe for our powder blend?"}]
    report, _, _ = finalise(copy.deepcopy(raw), checks=[], scenario_id=None, messages=msgs)
    assert report.answer.sayInstead is None
    msgs = [{"role": "user", "content": "Can we quote the paper to our customers?"}]
    report, _, _ = finalise(copy.deepcopy(raw), checks=[], scenario_id=None, messages=msgs)
    assert report.answer.sayInstead == "Something to say."


def test_feasibility_rules_survive_typography():
    raw = copy.deepcopy(RESPONDER)
    raw["feasibility"] = {"steps": ["1. Build a model and validate on held\u2011out samples.",
                                    "2. Perform a pilot in\u2011vivo test on a small number of surgeries."], "decisionBasis": "Agreed first."}
    report, stats, _ = finalise(raw, checks=[], scenario_id=None)
    assert "Build a model and validate on held\u2011out samples." in report.feasibility.steps and stats["later_stage_moved"] == 1
    assert not any("vivo" in s for s in report.feasibility.steps)
