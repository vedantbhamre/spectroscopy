"""Eval metrics with a scripted judge: the scoring maths must be right without any LLM or network."""

import json
from pathlib import Path

from evals import metrics as M

REPORT = {
    "title": "Water in a petroleum line",
    "decisionStatus": "insufficient",
    "requirements": {"stated": ["Water content"], "unknowns": ["Link length"]},
    "questions": [{"text": "How long is the fibre link?"}, {"text": "What temperature?"}],
    "recommendations": [
        {"method": "MIR ATR", "role": "primary", "reason": "Water in petroleum is a supplied application.",
         "citations": [{"source": "S02", "page": "13", "check": "verified"}, {"source": "S02", "page": "13", "check": "failed"}]},
        {"method": "NIR", "role": "comparison", "reason": "Overtone bands.", "citations": [{"source": "S01", "page": "10", "check": "unverified"}]},
    ],
    "concept": {"summary": "ATR probe in the line; silica does not carry mid-IR, use chalcogenide fibre.", "citations": []},
    "spectralRange": {"summary": "4000-400 cm-1", "citations": [{"source": "S01", "page": "9", "check": "visual_note"}]},
    "risks": ["Fouling of the ATR crystal"],
    "feasibility": {"steps": ["Lab samples", "Compare fibres"], "decisionBasis": "Error vs lab water results"},
    "premiseChecks": [{"id": "fiber_silica_visnir_MIR_ATR", "label": "Silica carries MIR", "status": "fail", "detail": ""},
                      {"id": "certainty", "label": "Certainty", "status": "pass", "detail": ""}],
}
DOCS = [{"source": "S02", "page": "13", "text": "water in petroleum"}, {"source": "S01", "page": "6", "text": "table"}]


class FakeJudge:
    def __init__(self, answers):
        self.answers, self.calls = list(answers), 0

    def ask(self, system, user):
        self.calls += 1
        return self.answers.pop(0)


def test_deterministic_metrics():
    assert M.citation_validity(REPORT) == 2 / 4  # verified + visual_note out of 4
    assert M.grounding(REPORT) == 1 / 2  # MIR ATR has a verified citation, NIR does not
    assert M.clarification(REPORT) == 1.0
    assert M.feasibility(REPORT) == 1.0
    assert M.feasibility({"feasibility": {"steps": ["one"], "decisionBasis": ""}}) == 0.0


def test_not_applicable_is_none():
    empty = {**REPORT, "recommendations": [], "concept": {"summary": ""}, "spectralRange": {"summary": ""}}
    assert M.citation_validity(empty) is None
    assert M.grounding(empty) is None


def test_expectations():
    golden = {"status_in": ["insufficient"], "premise_flagged": ["fiber_", "source_scope"],
              "must_mention_any": [["silica"], ["chalcogenide", "fluoride"]], "min_questions": 3}
    score, failures = M.expectations(REPORT, golden)
    assert score == 4 / 6  # status, fiber_, silica, chalcogenide pass; source_scope and 3 questions fail
    assert len(failures) == 2
    assert any("source_scope" in f for f in failures)
    assert any("3 clarification" in f for f in failures)
    assert M.expectations(REPORT, {}) == (None, [])


def test_average_precision():
    assert M.average_precision([True, False, True]) == (1 / 1 + 2 / 3) / 2
    assert M.average_precision([False, False]) == 0.0
    assert M.average_precision([]) is None


def test_judged_metrics():
    judge = FakeJudge([
        {"claims": [{"claim": "a", "supported": True}, {"claim": "b", "supported": False}]},
        {"questions": ["q1", "q2", "q3"], "similarity": [1, 0.5, 0.75]},
        {"relevant": [True, False]},
        {"attributed": [True, True, False, False]},
        {"tp": 3, "fp": 1, "fn": 1},
    ])
    faith, claims = M.faithfulness(judge, REPORT, DOCS)
    assert faith == 0.5 and len(claims) == 2
    assert M.answer_relevancy(judge, "enquiry", REPORT) == 0.75
    assert M.context_precision(judge, "enquiry", DOCS) == 1.0
    assert M.context_recall(judge, ["r1", "r2", "r3", "r4"], DOCS) == 0.5
    assert M.answer_correctness(judge, ["r1"], REPORT) == 3 / (3 + 0.5 * 2)
    assert judge.calls == 5


def test_reference_metrics_skip_without_reference_or_docs():
    judge = FakeJudge([])
    assert M.context_recall(judge, [], DOCS) is None
    assert M.answer_correctness(judge, [], REPORT) is None
    assert M.faithfulness(judge, REPORT, [])[0] is None
    assert judge.calls == 0


def test_golden_covers_every_scenario():
    root = Path(__file__).parent.parent
    ids = {s["id"] for s in json.loads((root / "data" / "scenarios.json").read_text())}
    golden = json.loads((root / "evals" / "golden.json").read_text())
    assert ids <= set(golden)
    assert golden["D01"]["reference"] and golden["D02"]["reference"]
