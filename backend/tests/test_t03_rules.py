"""T01/T03 review (Raman ester reactor, frying oil with a 40 m mid-IR link): rule fixes, offline (no LLM)."""

from app.agents.nodes.responder import answer_follows_flags, label_methods, settle_certainty
from app.schemas import PremiseCheck, Question
from app.services import ledger as L
from app.services import review_rules as RR
from app.services.premises import Facts, detect, geometry_check, owned_equipment_check, run_checks
from app.services.validators import validate_feasibility
from tests.test_review_rules import _report

T03 = ("We run industrial fryers for potato chips. We'd like to measure free fatty acids and total polar compounds in-line in the hot "
       "oil, around 180 °C, using mid-IR ATR, because a supplier told us mid-IR is the gold standard. We already own a benchtop NIR "
       "analyzer in our QC lab. The analyzer for the line would sit in the control room, about 40 m away.")
T01 = ("We were told Raman needs no calibration because the peaks are specific, so we'd like to switch off the GC once it's installed.")


def test_questions_that_ask_the_customer_to_specify_equipment_are_dropped():
    for q in ("What type of fibre (silica, chalcogenide, etc.) is available or can be installed for a 40 m link?",
              "What temperature rating does the probe material (e.g., diamond, germanium) need to withstand?",
              "Can you tell us the exact probe material compatible with 180°C?",
              "What is the maximum acceptable fibre attenuation at the MIR wavelengths you plan to use?"):
        assert L.asks_assistant_decision(q), q
    for q in ("What maximum pressure will the probe experience in the return line?",
              "Which lab method gives your reference values for total polar compounds?"):
        assert not L.asks_assistant_decision(q), q


def test_follow_up_questions_must_ask_for_a_customer_fact():
    led = [Question(id="q1", text="Which compound is the active ingredient?", status="answered", answer="niacinamide")]
    proposed = [{"text": "Would a sapphire or diamond tip suit this?", "impact": "setup"},
                {"text": "What temperature is the cream during mixing?", "impact": "setup"}]
    out, stats = L.merge_new(led, proposed, 2, final=False)
    assert [q.text for q in out[1:]] == ["What temperature is the cream during mixing?"]
    assert stats["not_customer_fact"] == 1


def test_expert_decision_unknown_goes_to_points_to_confirm_not_a_question():
    r = _report()
    r.questions = []
    RR.enforce_decisive(r, ["exact probe material compatible with 180 °C"], final=False, turn=2)
    assert not r.questions
    assert any("probe material" in p for p in r.pointsToConfirm)


def test_supplier_claim_and_dropped_reference_are_flagged():
    c = {x.id: x for x in run_checks(detect(T03, Facts(target_variables=["total polar compounds"])))}
    assert c["vendor_claim"].status == "flag"
    c = {x.id: x for x in run_checks(detect(T01, Facts(target_variables=["ester concentration"])))}
    assert c["calibration_and_reference"].status == "flag"


def test_answer_and_concept_follow_a_link_length_flag():
    r = _report()
    r.answer.text = "MIR (ATR) is the most promising first candidate to test."
    r.concept.summary = "ATR probe connected via a 40 m chalcogenide fibre to the control room."
    r.premiseChecks = [PremiseCheck(id="mir_link_length", label="Mid-IR fibre link: distance not shown to be feasible", status="flag",
                                    detail="MIR needs mid-IR fibres. Measure the transmission over the planned length before committing, "
                                           "or plan the analyzer close to the measurement point.")]
    assert answer_follows_flags(r) == 1
    assert "plan the analyzer close" in r.answer.text and "not shown to be feasible" in r.concept.summary


def test_certainty_cannot_pass_next_to_an_open_flag():
    r = _report()
    r.assumptions = []
    r.premiseChecks = [PremiseCheck(id="certainty", label="Certainty: nothing decisive is unknown", status="pass", detail="x"),
                       PremiseCheck(id="mir_link_length", label="Mid-IR fibre link: distance not shown to be feasible", status="flag", detail="y")]
    settle_certainty(r)
    assert r.premiseChecks[0].status == "flag" and r.assumptions


def test_method_ids_are_shown_as_names():
    r = _report()
    r.recommendations[0].method = "MIR_ATR"
    r.answer.text = "MIR_ATR is the most promising first candidate."
    label_methods(r)
    assert r.recommendations[0].method == "MIR (ATR)" and r.answer.text.startswith("MIR (ATR) is")


def test_owned_equipment_in_an_escalation_step_is_not_assessed():
    f = detect(T03, Facts())
    rep = {"recommendations": [{"role": "primary", "methodIds": ["MIR_ATR"]}],
           "feasibility": {"steps": ["Measure oil samples with MIR-ATR.", "If correlation is acceptable, proceed; otherwise, consider adding a NIR probe."]}}
    assert owned_equipment_check(f, rep).status == "flag"


def test_atr_is_not_flagged_as_reflection_for_a_clear_liquid():
    f = Facts(optical_appearance="clear")
    chk = geometry_check(f, {"concept": {"summary": "Diamond ATR probe in the return line."}})
    assert chk.status == "pass" and "ATR" in chk.detail


def test_routine_operation_and_patients_leave_a_non_medical_plan():
    r = _report()
    r.feasibility.steps = ["Collect oil samples.", "If correlation is acceptable, proceed to routine operation.",
                           "Validate on held-out samples from other patients, batches or days."]
    validate_feasibility(r)
    RR.order_plan(r, medical=False)
    assert not any("routine operation" in s for s in r.feasibility.steps)
    assert not any("patients" in s for s in r.feasibility.steps)


def test_raman_on_a_darkening_sample_gets_a_fluorescence_risk():
    r = _report()
    r.recommendations[0].methodIds = ["RAMAN"]
    r.risks = []
    assert RR.raman_colour_risk(r, "It turns yellow-brown towards the end of the batch.") == 1
    assert "fluorescence" in r.risks[0]


def test_non_answers_are_not_stored_as_facts(monkeypatch):
    from app.agents.nodes import analyst
    from app.gateway import LLMResult

    monkeypatch.setattr(analyst, "chat", lambda *a, **k: LLMResult(text='{"stated": [], "unknowns": []}', model="t", via="t", ms=0))
    report = {"questions": [{"id": "q1", "text": "What type of fibre do you have?", "status": "open"}]}
    state = {"messages": [{"role": "user", "content": T03}, {"role": "user", "content": "We don't have any fibre yet. That's what we hoped you would recommend."}],
             "report": report, "answers": [{"id": "q1", "question": "What type of fibre do you have?", "status": "answered",
                                            "answer": "We don't have any fibre yet. That's what we hoped you would recommend."}], "trace": []}
    facts = analyst.analyst_node(state)["facts"]
    assert not any("hoped you" in s for s in facts["stated"])
    assert any("don't have any fibre" in s for s in facts["stated"])
