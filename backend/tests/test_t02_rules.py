"""T02 review (UV nitrate in wastewater, one port): the rule fixes, offline (no LLM)."""

from app.services import ledger as L
from app.services import review_rules as RR
from app.services.numbers import PLACEHOLDER, allowed_numbers, scrub
from app.services.premises import Facts, _dropped, detect, resolved_by_facts, run_checks
from app.services.validators import validate_feasibility
from tests.test_review_rules import _report

ENQUIRY = ("We operate a municipal wastewater treatment plant and want to monitor nitrate continuously in the outlet channel using UV "
           "absorbance around 220 nm. We already have a fiber cable left over from an NIR moisture analyzer and would like to reuse it "
           "to save cost. While we're at it, we'd like the same probe to also give us turbidity and total organic carbon. There is only "
           "one mounting point available. The water sometimes carries sludge flakes.")
ANSWERS = ("It's a standard silica fiber from a Vis-NIR setup, about 25 m long. We don't have the datasheet, but the NIR analyzer "
           "worked from about 400 to 2200 nm.\n\nUsually low, under 5 NTU, but after heavy rain or a settling problem it can go above "
           "50 NTU for a few hours.\n\nYes, our lab measures nitrate with a cuvette photometric test kit. Nitrate is the priority; "
           "turbidity would be nice, TOC we can drop.")


def _facts(text: str = ENQUIRY + "\n\n" + ANSWERS) -> Facts:
    return detect(text, Facts(target_variables=["nitrate", "turbidity", "total organic carbon"], methods_mentioned=["UVVIS"]), enquiry=ENQUIRY)


def test_stated_wavelength_outside_the_fibre_fails_the_premise():
    f = _facts()
    assert f.wavelengths_um == [0.22]  # "400 to 2200 nm" describes the fibre, not the measurement
    c = {x.id: x for x in run_checks(f)}
    chk = c["fiber_silica_visnir_UVVIS"]
    assert chk.status == "fail" and "220 nm" in chk.label
    assert "UV-Vis silica fibre" in chk.detail


def test_turbidity_in_ntu_answers_the_optical_appearance():
    f = _facts()
    assert f.optical_appearance == "changing"  # under 5 NTU and above 50 NTU
    assert resolved_by_facts("optical appearance may be opaque or changing due to sludge flakes", f)
    assert resolved_by_facts("Can you tell us the optical appearance (transparency/opacity)?", f)
    assert not resolved_by_facts("What accuracy in mg/L do you need?", f)
    assert detect("Usually under 2 NTU.", Facts()).optical_appearance == "clear"


def test_dropped_target_leaves_the_scope():
    assert _facts().target_variables == ["nitrate", "turbidity"]
    assert _dropped("total organic carbon", "toc we can drop")
    assert not _dropped("total organic carbon", "toc we can measure in the lab")


def test_design_limit_questions_are_not_asked():
    for q in ("What is the maximum allowable optical path length for a UV-Vis transmission cell in this water?",
              "What is the maximum path length you can accommodate in the flow cell?",
              "What is the maximum allowable fiber length between the ATR probe and the MIR analyzer?"):
        assert L.asks_assistant_decision(q), q
    assert not L.asks_assistant_decision("What nitrate concentration range do you expect at the outlet?")
    assert not L.asks_assistant_decision("How far is the analyzer location from the mounting point?")


def test_hardware_setup_comes_before_the_measurements():
    r = _report()
    r.feasibility.steps = ["Collect spectra of water samples covering the nitrate range.",
                           "Build a chemometric calibration against the lab test kit.",
                           "Install a UV-grade fiber and a 1–2 mm path length transmission cell."]
    RR.order_plan(r, medical=False)
    assert r.feasibility.steps[0].startswith("Install a UV-grade fiber")
    r.feasibility.steps = ["Measure laboratory samples.", "Install the probe in the outlet channel for a pilot run."]
    RR.order_plan(r, medical=False)
    assert r.feasibility.steps[0] == "Measure laboratory samples."  # installing at the process point stays in-line


def test_failed_fibre_is_settled_not_hedged():
    r = _report()
    r.premiseChecks = [c for c in run_checks(_facts()) if c.id.startswith("fiber_")]
    r.feasibility.steps = ["Verify UV transmission of the existing fiber (cutoff test).", "Collect spectra of water samples."]
    r.risks = ["Existing fiber may not transmit 220 nm, requiring replacement.", "Transmission cell may saturate."]
    r.pointsToConfirm = ["Exact UV transmission cutoff of the current 25 m silica fiber.", "Physical dimensions of the DN50 flange."]
    assert RR.settle_failed_fiber(r) == 3
    assert r.feasibility.steps == ["Collect spectra of water samples."]
    assert "may not" not in " ".join(r.risks) and "has to be replaced" in r.risks[0]
    assert r.pointsToConfirm == ["Physical dimensions of the DN50 flange."]


def test_independent_validation_is_not_duplicated():
    r = _report()
    r.feasibility.steps = ["Collect samples.", "Validate on independent samples, including high-turbidity spikes."]
    validate_feasibility(r)
    assert len(r.feasibility.steps) == 2


def test_example_that_lost_its_number_is_removed():
    out, _ = scrub("What path length fits (e.g., 1 mm, 5 mm) for nitrate?", allowed_numbers("5 mm", []))
    assert PLACEHOLDER not in out and out == "What path length fits for nitrate?"


def test_no_interference_assumption_is_also_a_risk_and_wording():
    r = _report()
    r.assumptions = ["The water matrix does not contain strong UV-absorbing interferents at 220 nm beyond nitrate."]
    r.risks = []
    assert RR.interferences_as_risk(r) == 1 and "interfere" in r.risks[0]
    r.concept.summary = "Install a UV-transparent silica fiber (e.g., solarized quartz)."
    assert RR.fix_wording(r) == 1 and "solarisation-resistant" in r.concept.summary
