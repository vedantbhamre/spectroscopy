"""Acceptance tests for multi-turn conversations, with a scripted LLM that makes every mistake from the
multi-turn test reports (repeats answered questions, asks for the customer's choice or a purchase, invents
figures, writes unsupported claims, recommends two probes for one port, drops a target qualifier, ignores
owned equipment, transmission in a turbid medium, numbered question text, missing sections).

The deterministic safeguards must hold for any conversation; evals/acceptance.py states each property.
"""

import json

import pytest
from fastapi.testclient import TestClient

from app.gateway.client import LLMResult
from app.services import ledger as L
from app.services.numbers import PLACEHOLDER
from evals import acceptance as A

SCRIPT: dict = {}


@pytest.fixture
def client(monkeypatch):
    def fake_chat(messages, *, feature="assess", **_):
        payload = SCRIPT.get(feature)
        if isinstance(payload, list):  # successive answers (e.g. responder, then repair)
            payload = payload.pop(0) if len(payload) > 1 else payload[0]
        if payload is None and feature == "planner":
            payload = {"intent": "assessment", "queries": ["probe process"]}
        return LLMResult(text=json.dumps(payload) if payload is not None else "ok", model="fake", via="test", ms=1)

    import app.agents.nodes.analyst as analyst
    import app.agents.nodes.planner as planner
    import app.agents.nodes.responder as resp

    for mod in (planner, analyst, resp):
        monkeypatch.setattr(mod, "chat", fake_chat)
    SCRIPT.clear()
    from app.main import app

    return TestClient(app)


class Conversation:
    def __init__(self, client):
        self.client, self.messages, self.turns = client, [], []

    def say(self, text: str, answers: list[dict] | None = None, final: bool = False) -> dict:
        self.messages.append({"role": "user", "content": text})
        r = self.client.post("/assess", json={"messages": self.messages, "answers": answers or [], "final": final})
        assert r.status_code == 200, r.text
        body = r.json()
        self.turns.append({"messages": list(self.messages), "answers": answers or [], "final": final, "report": body["report"], "reply": body["reply"]})
        self.messages.append({"role": "assistant", "content": body["reply"]})
        return body


# A powder process with one free port. Citations are real, verified S01 passages.
POWDER = "We press tablets from a powder blend and want to follow the active ingredient concentration in the feed frame in line."
COMBINED = "A multispectral NIRaman fiber probe has industrial grade design that combines NIR reflection and Raman optical techniques in a compact shaft that fits in a tablet press feed frame."
Q_COMPOSITION, Q_FLUO, Q_PORTS = "1. Which ingredients are in the blend, at what concentration?", "2. Is any ingredient fluorescent?", "3. How many free ports does the feed frame have?"


def responder(questions, concept="NIR and Raman probes in parallel at the feed frame.", **extra):
    base = {
        "reply": "Target RMSEP ≤ 0.25% w/w and a bias ≤ 0.20.", "title": "Blend concentration in the feed frame", "decisionStatus": "provisional",
        "requirements": {"stated": ["paraphrase"], "unknowns": ["Ingredient fluorescence"]}, "questions": questions,
        "recommendations": [
            {"method": "NIR (diffuse reflection)", "methodIds": ["NIR"], "role": "primary",
             "reason": "NIR reflection probes can follow blend potency in a tablet press feed frame. The probe fits comfortably in a 12 mm port.",
             "citations": [{"source": "S01", "page": "15", "quote": COMBINED}]},
            {"method": "Raman", "methodIds": ["RAMAN"], "role": "comparison", "reason": "Raman is more sensitive to dust.", "citations": []},
        ],
        "concept": {"summary": concept, "citations": []}, "spectralRange": {"summary": "NIR nominal 780–2500 nm.", "citations": []},
        "risks": ["Dust on the probe window"],
        "feasibility": {"steps": ["Lab blends spanning 5–15 % w/w with independent reference results", "False-alarm rate ≤ 5%"], "decisionBasis": "Compare with the reference."},
        "assumptions": ["Contact measurement is acceptable"],
    }
    return {**base, **extra}


def test_powder_conversation_meets_every_acceptance_property(client):
    c = Conversation(client)
    SCRIPT.update(analyst={"stated": [{"fact": "Tablets pressed from a powder blend", "quote": "tablets from a powder blend"}], "unknowns": ["Ingredients"],
                           "target_variables": ["active ingredient concentration"]},
                  responder=responder([{"text": Q_COMPOSITION, "impact": "method"}, {"text": Q_FLUO, "impact": "method"}, {"text": Q_PORTS, "impact": "setup"},
                                       {"text": "Can you acquire a Raman probe?"}, {"text": "Which probe do you prefer?"}]))
    b1 = c.say(POWDER)
    open1 = [q for q in b1["report"]["questions"] if q["status"] == "open"]
    assert [q["text"] for q in open1] == [Q_COMPOSITION[3:], Q_FLUO[3:], Q_PORTS[3:]]  # numbering stripped; purchase / choice questions dropped

    answers = [{"id": "q1", "question": open1[0]["text"], "status": "answered", "answer": "paracetamol 10% w/w with lactose and cellulose"},
               {"id": "q2", "question": open1[1]["text"], "status": "answered_unknown"},
               {"id": "q3", "question": open1[2]["text"], "status": "answered", "answer": "one free side port of about 12 mm"}]
    SCRIPT.update(analyst={"stated": [{"fact": "Tablets pressed from a powder blend", "quote": "tablets from a powder blend"},
                                      {"fact": "One free side port, 12 mm", "quote": "one free side port of about 12 mm"},
                                      {"fact": "Paracetamol 10 % w/w", "quote": "paracetamol 10% w/w"}],
                           "unknowns": ["Ingredient fluorescence"], "target_variables": ["active ingredient concentration"], "access_points": 1},
                  responder=responder([{"text": open1[0]["text"]}, {"text": "Is any of the ingredients fluorescent?"}, {"text": open1[2]["text"]},
                                       {"text": "How are the probe windows cleaned between batches?", "impact": "setup"}]))
    b2 = c.say("Answers to your questions: paracetamol 10% w/w with lactose and cellulose; fluorescence unknown; one free side port of about 12 mm.", answers)
    rep = b2["report"]
    st = {q["id"]: q["status"] for q in rep["questions"]}
    assert st["q1"] == "answered" and st["q3"] == "answered" and st["q2"] == "moved_to_experiment"
    assert any("fluorescent" in s for s in rep["feasibility"]["steps"])
    assert 2 in rep["requirements"]["factTurns"]
    assert PLACEHOLDER in b2["reply"] and "0.25" not in b2["reply"]
    assert any("fits comfortably" in a for a in rep["assumptions"]) and not any("fits comfortably" in r["reason"] for r in rep["recommendations"])
    assert [r["method"] for r in rep["recommendations"]] == ["NIR (diffuse reflection)"]  # uncited Raman moved to assumptions
    assert any(a.startswith("Raman") for a in rep["assumptions"])
    assert any(ct["page"] == "10" for ct in rep["spectralRange"]["citations"])  # nominal NIR range cited with its page

    # Final request in the wording: no question block, open points to confirm, status provisional.
    SCRIPT["responder"] = responder([{"text": "What is the press speed?"}], concept="A combined NIR–Raman probe in one compact shaft at the side port.",
                                    pointsToConfirm=["Probe window cleaning"])
    b3 = c.say("Give me the final answer now, no more questions.")
    assert b3["report"]["mode"] == "final" and b3["report"]["decisionStatus"] == "provisional"
    assert "How are the probe windows cleaned between batches?" in b3["report"]["pointsToConfirm"]

    violations = A.run_all(c.turns, access_points=1)
    assert {k: v for k, v in violations.items() if v} == {}, violations
    resolved = next(ch for ch in b3["report"]["premiseChecks"] if ch["id"] == "access_points")
    assert resolved["status"] == "pass"  # one cited probe method left for one port


def test_two_parallel_probes_for_one_port_are_flagged(client):
    SCRIPT.update(analyst={"stated": [{"fact": "One free port", "quote": "one free port"}], "unknowns": ["x"],
                           "target_variables": ["active ingredient concentration"], "access_points": 1, "application_domain": "pharmaceutical solids"},
                  responder=responder([], recommendations=[
                      {"method": "NIR", "methodIds": ["NIR"], "role": "primary", "reason": "NIR reflection probes can follow blend potency in a tablet press feed frame.",
                       "citations": [{"source": "S01", "page": "15", "quote": COMBINED}]},
                      {"method": "Raman", "methodIds": ["RAMAN"], "role": "comparison", "reason": "Raman optical techniques combine with NIR reflection in a tablet press feed frame.",
                       "citations": [{"source": "S01", "page": "15", "quote": COMBINED}]}]))
    c = Conversation(client)
    rep = c.say(POWDER + " There is one free port.")["report"]
    chk = next(x for x in rep["premiseChecks"] if x["id"] == "access_points")
    assert chk["status"] == "flag" and "combined NIR–Raman probe" in chk["detail"] and "one after the other" in chk["detail"]


QUAL = "We run a fermentation and need viable biomass in line. We already have a UV-Vis spectrometer. The broth starts clear and becomes turbid."
BIOMASS = "UV/Vis spectroscopy can be deployed as a lowcost, robust tool for real-time biomass monitoring, as cell suspension turbidity correlates well with cell density."


def test_qualifier_owned_equipment_geometry(client):
    SCRIPT.update(
        analyst={"stated": [{"fact": "Fermentation", "quote": "We run a fermentation"}], "unknowns": ["Cell line"], "target_variables": ["viable biomass"],
                 "owned_equipment": [{"name": "UV-Vis spectrometer", "method": "UVVIS", "quote": "We already have a UV-Vis spectrometer"}],
                 "optical_appearance": {"value": "changing", "quote": "becomes turbid"}, "application_domain": "bioprocess"},
        responder=responder([{"text": "What is the vessel volume?", "impact": "setup"}], concept="A UV-Vis transmission probe in the vessel.",
                            recommendations=[{"method": "UV-Vis", "methodIds": ["UVVIS"], "role": "primary",
                                              "reason": "UV/Vis can monitor biomass in real time because suspension turbidity correlates with cell density.",
                                              "citations": [{"source": "S01", "page": "16", "quote": BIOMASS}]}]))
    c = Conversation(client)
    rep = c.say(QUAL)["report"]
    chk = {x["id"]: x for x in rep["premiseChecks"]}
    assert chk["target_qualifier"]["status"] == "flag" and "viable" in chk["target_qualifier"]["detail"]
    assert chk["owned_equipment"]["status"] == "pass"
    assert chk["geometry_optics"]["status"] == "flag" and "saturate" in chk["geometry_optics"]["detail"]
    assert A.qualified_target_limited(c.turns, "viable") == []
    assert A.all_sections_present(c.turns) == [] and A.recommendations_cited(c.turns) == []


def test_owned_equipment_ignored_is_flagged_and_transfer_is_labelled(client):
    SCRIPT.update(
        analyst={"stated": [{"fact": "Milk line", "quote": "milk line"}], "unknowns": ["Fat range"], "target_variables": ["fat content"],
                 "owned_equipment": [{"name": "Raman analyser", "method": "RAMAN", "quote": "we already have a Raman analyser"}],
                 "application_domain": "dairy and food"},
        responder=responder([{"text": "Which fat range must be covered?", "impact": "method"}], concept="A diffuse reflection probe in the milk line."))
    c = Conversation(client)
    rep = c.say("We monitor fat content in a milk line; we already have a Raman analyser.")["report"]
    chk = {x["id"]: x for x in rep["premiseChecks"]}
    assert chk["owned_equipment"]["status"] == "flag"
    nir = rep["recommendations"][0]
    assert nir["citations"][0]["transfer"] is True and "pharmaceutical" in nir["citations"][0]["application"]
    assert any(a.startswith("Transfer assumption") for a in rep["assumptions"])


def test_missing_sections_are_repaired_once(client):
    broken = responder([{"text": "What is the temperature?"}], risks=[], assumptions=[])
    SCRIPT.update(analyst={"stated": [{"fact": "Powder blend", "quote": "powder blend"}], "unknowns": ["x"], "target_variables": ["concentration"]},
                  responder=[broken], repair=responder([{"text": "What is the temperature?"}]))
    c = Conversation(client)
    body = c.say(POWDER)
    assert A.all_sections_present(c.turns) == []
    assert "repaired once" in next(t for t in body["trace"] if t["step"] == "Compose the assessment")["detail"]


def test_unusable_repair_keeps_the_first_report(client):
    SCRIPT.update(analyst={"stated": [{"fact": "Powder blend", "quote": "powder blend"}], "unknowns": ["x"], "target_variables": ["concentration"]},
                  responder=responder([], risks=[]))  # "repair" not scripted: the fake returns non-JSON
    body = Conversation(client).say(POWDER)
    assert "risks" in next(t for t in body["trace"] if t["step"].startswith("Validate"))["detail"]


def test_gate_immediate_config_triggers_final_mode(client, monkeypatch):
    import app.main as main

    monkeypatch.setattr(main, "_gate", lambda text, history=None: (False, None, ["immediate_config"], main.TraceStep(step="Safety gate", status="warn")))
    SCRIPT.update(analyst={"stated": [{"fact": "Powder blend", "quote": "powder blend"}], "unknowns": ["x"], "target_variables": ["concentration"]},
                  responder=responder([{"text": "What is the temperature?"}]))
    c = Conversation(client)
    rep = c.say(POWDER)["report"]
    assert rep["mode"] == "final" and A.final_has_no_questions([{**c.turns[0], "final": True}]) == []


def test_certainty_and_combination_labels_do_not_read_as_claims():
    from app.services.premises import Facts, run_checks

    c = {x.id: x for x in run_checks(Facts(target_variables=["API"], unknowns=["port"], asks_for_certainty=True, combination_requested=True))}
    assert c["certainty"].status == "flag" and "provisional" in c["certainty"].label
    assert c["combination"].status == "flag" and "escalation" in c["combination"].label
    c = {x.id: x for x in run_checks(Facts(target_variables=["API"], asks_for_certainty=True, combination_requested=True, single_method_insufficient=True))}
    assert c["certainty"].status == "pass" and c["combination"].status == "pass"


def test_cost_check_prefers_the_cheaper_sufficient_method():
    from app.services.premises import cost_check

    assert cost_check({"recommendations": [{"role": "primary", "methodIds": ["RAMAN"]}, {"role": "comparison", "methodIds": ["NIR"]}]}).status == "flag"
    assert cost_check({"recommendations": [{"role": "primary", "methodIds": ["NIR"]}, {"role": "comparison", "methodIds": ["RAMAN"]}]}).status == "pass"


@pytest.mark.parametrize("text,final", [("Give me the solution, no more questions.", True), ("Please send the final report.", True),
                                        ("Just tell me what to buy.", True), ("What does the second question mean?", False)])
def test_final_request_detection(text, final):
    assert L.wants_final(text) is final


@pytest.mark.parametrize("text,dropped", [("Which probe would fit the port best?", True), ("Should we use Raman as well?", True),
                                          ("Which method is most suitable?", True), ("Can you acquire a Raman probe?", True),
                                          ("Which method do you prefer?", True), ("Are you willing to purchase a new analyser?", True),
                                          ("Which ingredients are in the blend?", False), ("How many free ports does the line have?", False),
                                          ("What reference data do you already have?", False)])
def test_questions_ask_only_for_customer_facts(text, dropped):
    assert L.asks_assistant_decision(text) is dropped


def test_numbers_need_the_customer_or_a_cited_page_with_the_same_unit():
    from app.services.numbers import allowed_numbers, scrub

    a = allowed_numbers("paracetamol 10% w/w; specification 95–105% of target", ["S01 page 15, Fig. 5; NIR spectra (780–2500 nm)"])
    assert scrub("blends covering 5–15 % w/w", a)[1] == 1  # page numbers 5 and 15 do not support a concentration range
    assert scrub("NIR 780–2500 nm; see Fig. 5; 95–105% of target", a)[1] == 0
    assert scrub("NIR 780–2500 µm", a)[1] == 1  # right numbers, wrong unit
    assert scrub("slightly beyond 9.5–10.5% w/w", a)[1] == 1  # derived figures are not in the transcript or a page
