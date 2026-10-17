import json
from pathlib import Path

from app.services.citations import verify
from app.services.premises import Facts, apply_floor, detect, run_checks

SCEN = {s["id"]: s["enquiry"] for s in json.loads((Path(__file__).parent.parent / "data" / "scenarios.json").read_text())}


def checks_for(sid: str, **facts):
    f = detect(SCEN[sid], Facts(**facts))
    return {c.id: c for c in run_checks(f)}


def test_h04_silica_link_cannot_carry_mir():
    c = checks_for("H04", target_variables=["water content"], methods_mentioned=["MIR_ATR"])
    assert c["fiber_silica_visnir_MIR_ATR"].status == "fail"
    assert c["certainty"].status == "flag"
    assert apply_floor("provisional", list(c.values())) == "insufficient"


def test_h03_fluorescence_without_target():
    c = checks_for("H03", target_variables=["glucose", "viable biomass"], methods_mentioned=["FLUO"])
    assert c["fluorescent_target"].status == "fail"


def test_h06_lab_study_for_surgery_is_out_of_scope():
    c = checks_for("H06", target_variables=["tumour boundary"], methods_mentioned=["NIR"])
    assert c["source_scope"].status == "fail"
    assert apply_floor("provisional", list(c.values())) == "out_of_scope"


def test_h05_undefined_target():
    c = checks_for("H05")
    assert c["target_defined"].status == "fail"
    assert c["certainty"].status == "flag"


def test_h01_calibration_transfer_and_combination():
    c = checks_for("H01", target_variables=["API concentration"], methods_mentioned=["NIR", "RAMAN"])
    assert c["calibration_transfer"].status == "flag"
    assert c["combination"].status == "flag"


def test_d01_has_no_failures():
    c = checks_for("D01", target_variables=["API concentration"], methods_mentioned=["NIR"])
    assert not [x for x in c.values() if x.status == "fail"]
    assert apply_floor("provisional", list(c.values())) == "provisional"


def test_nir_keyword_does_not_add_a_method_when_extraction_has_one():
    f = detect(SCEN["H04"], Facts(methods_mentioned=["MIR_ATR"]))
    assert f.methods_mentioned == ["MIR_ATR"]


def test_every_check_citation_is_on_its_page():
    facts = Facts(target_variables=["x"], methods_mentioned=["MIR_ATR", "NIR", "FLUO"],
                  fibers_mentioned=["silica_visnir", "pir", "chalcogenide", "hwg", "zrf", "inf", "silica_uvvis"],
                  fluorescent_target_named=False, use_context="clinical", combination_requested=True)
    for check in run_checks(facts):
        for cite in check.citations:
            assert verify(cite).check in ("verified", "visual_note"), (check.id, cite)
