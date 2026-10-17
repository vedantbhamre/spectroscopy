"""Deterministic premise checks. They run before the answer is composed and constrain it.

Input is the structured facts from the analyst node (LLM extraction) merged with keyword
detection on the client's own words, so a missed extraction does not skip a check.
Only checks that apply to the enquiry are returned.
"""

import re

from pydantic import BaseModel, Field

from app.knowledge.optics import FIBERS, METHODS, coverage
from app.schemas import Citation, DecisionStatus, PremiseCheck


class Facts(BaseModel):
    """What the client stated. Unknown stays unknown."""

    stated: list[str] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)
    target_variables: list[str] = Field(default_factory=list)
    methods_mentioned: list[str] = Field(default_factory=list)  # MethodId values
    fibers_mentioned: list[str] = Field(default_factory=list)  # FIBERS keys
    fluorescent_target_named: bool | None = None
    use_context: str = "unknown"  # process | laboratory | clinical | unknown
    cites_study_as_proof: bool = False
    reuses_existing_calibration: bool = False
    new_formulation_or_matrix: bool = False
    asks_for_certainty: bool = False
    combination_requested: bool = False


_KW = {
    "MIR_ATR": r"\b(mir|mid[- ]?ir|mid[- ]infrared|atr|ftir)\b",
    "NIR": r"\bnir\b|near[- ]infrared",
    "RAMAN": r"\braman\b",
    "FLUO": r"fluoresc",
    "UVVIS": r"\buv[- ]?vis\b|\buv\b",
}


def detect(text: str, facts: Facts) -> Facts:
    """Fill gaps in the extracted facts from the client's own words."""
    t = text.lower()
    # Keywords only fill in when extraction found no requested method: "a silica cable from a
    # visible or NIR setup" names NIR without asking for it.
    methods = set(facts.methods_mentioned)
    if not methods:
        for mid, pat in _KW.items():
            if re.search(pat, t):
                methods.add(mid)
    fibers = set(facts.fibers_mentioned)
    if re.search(r"silica", t):
        fibers.add("silica_uvvis" if re.search(r"\buv\b", t) and not re.search(r"nir|visible", t) else "silica_visnir")
    for fid, pat in {"chalcogenide": r"chalcogenide", "pir": r"polycrystalline|\bpir\b", "hwg": r"hollow (glass )?waveguide", "zrf": r"zirconium fluoride", "inf": r"indium fluoride"}.items():
        if re.search(pat, t):
            fibers.add(fid)
    upd: dict = {"methods_mentioned": sorted(methods), "fibers_mentioned": sorted(fibers)}
    if re.search(r"surg|in vivo|clinical|patient|tumou?r boundar|diagnos", t):
        upd["use_context"] = "clinical"
    if re.search(r"\b(proof|prove|ready for)\b", t) and re.search(r"stud|paper|findings", t):
        upd["cites_study_as_proof"] = True
    if re.search(r"reuse the calibration|calibration (will )?remain valid|reuse (our|the) (existing )?calibration", t):
        upd["reuses_existing_calibration"] = True
    if re.search(r"(different|new) (api|formulation|blend|excipient|matrix|product)", t):
        upd["new_formulation_or_matrix"] = True
    if re.search(r"\b(approve|guarantee|exact (sensor )?configuration|immediately|proof|ready for)\b", t):
        upd["asks_for_certainty"] = True
    if re.search(r"(adding|add|combin\w*)\s+(raman|nir|mir|fluorescence)|both .* and ", t):
        upd["combination_requested"] = True
    if "FLUO" in methods and re.search(r"(not|no)( yet)? (identified|named|defined)? ?(a )?fluorescent (target|marker)|have not identified a fluorescent", t):
        upd["fluorescent_target_named"] = False
    return facts.model_copy(update=upd)


def run_checks(facts: Facts) -> list[PremiseCheck]:
    checks: list[PremiseCheck] = []

    # 1. Variable to measure is defined.
    if not facts.target_variables:
        checks.append(PremiseCheck(
            id="target_defined", label="The variable to measure is named", status="fail",
            detail="The enquiry does not name the variable or substance to measure, so no method can be chosen yet. Ask for it first.",
        ))
    else:
        checks.append(PremiseCheck(id="target_defined", label="The variable to measure is named", status="pass",
                                   detail="Target: " + ", ".join(facts.target_variables) + "."))

    # 2. Fibre window covers the nominal method range.
    for mid in facts.methods_mentioned:
        m = METHODS.get(mid)
        if not m or not m.range_um:
            continue
        for fid in facts.fibers_mentioned:
            f = FIBERS.get(fid)
            if not f:
                continue
            kind, share = coverage(m.range_um, f.range_um)
            cites = [c for c in (m.cite, f.cite) if c]
            if kind == "none":
                checks.append(PremiseCheck(
                    id=f"fiber_{fid}_{mid}", label=f"{f.label} carries the {m.label} range", status="fail",
                    detail=f"A {f.label} transmits about {f.range_um[0]}–{f.range_um[1]} µm; {m.label} works at {m.range_label}. The link cannot carry the signal.",
                    citations=cites,
                ))
            elif kind == "partial":
                checks.append(PremiseCheck(
                    id=f"fiber_{fid}_{mid}", label=f"{f.label} carries the {m.label} range", status="flag",
                    detail=f"The fibre window covers only part ({round(share * 100)}%) of the nominal {m.label} range. Confirm the bands that matter on sample spectra.",
                    citations=cites,
                ))
            else:
                checks.append(PremiseCheck(id=f"fiber_{fid}_{mid}", label=f"{f.label} carries the {m.label} range", status="pass",
                                           detail="The fibre window covers the nominal range.", citations=cites))

    # 3. Fluorescence needs a defined fluorescent species.
    if "FLUO" in facts.methods_mentioned and facts.fluorescent_target_named is False:
        checks.append(PremiseCheck(
            id="fluorescent_target", label="Fluorescence has a defined fluorescent target", status="fail",
            detail="No fluorescent species, marker or reference relationship is named. Sensitivity alone does not make fluorescence a measurement of the requested variables.",
            citations=[
                Citation(source="S01", page="16", quote="Fluorescence spectroscopy can be used for highsensitivity detection (down to the nM-µM range) of critical cofactors and amino acids like NADH, tryptophan, and riboflavin.", check="verified"),
                Citation(source="S01", page="5", quote="NIR, UV, and fluorescence spectra contain broad, highly overlapping signals", check="verified"),
            ],
        ))

    # 4. A source is used within its scope.
    if facts.use_context == "clinical" or facts.cites_study_as_proof:
        clinical = facts.use_context == "clinical"
        checks.append(PremiseCheck(
            id="source_scope", label="Sources are used within their demonstrated scope", status="fail" if clinical else "flag",
            detail=("The supplied tumour study is an in vitro laboratory study; it cannot support clinical or surgical readiness."
                    if clinical else "A published application is a reason to test a method, not proof that it will work for this customer."),
            citations=[Citation(source="S03", page="2", quote="seven pairs each of tumor and normal in vitro clinical samples from different patients", check="verified")] if clinical else [],
        ))

    # 5. Calibration transfer to a new formulation.
    if facts.reuses_existing_calibration and facts.new_formulation_or_matrix:
        checks.append(PremiseCheck(
            id="calibration_transfer", label="An existing calibration applies to the new material", status="flag",
            detail="The calibration was built for a different formulation. Whether it transfers has to be tested on the new blend with independent references; adding a method does not by itself keep it valid.",
        ))

    # 6. A combination is a hypothesis.
    if facts.combination_requested:
        checks.append(PremiseCheck(
            id="combination", label="A method combination is justified", status="flag",
            detail="Assess each method on its own first; a gain from combining them is a hypothesis to test for this material.",
            citations=[Citation(source="S01", page="15", quote="By combining Raman and NIR, these models can predict API potency or coating thickness with higher accuracy and robustness than single-method models.", check="verified")],
        ))

    # 7. Certainty requested beyond what the facts allow.
    if facts.asks_for_certainty:
        checks.append(PremiseCheck(
            id="certainty", label="The request can be answered with certainty", status="flag",
            detail="The client asks for approval, proof or an exact configuration. The answer can only be a provisional assessment with the questions and experiment that would decide it.",
        ))

    return checks


def status_floor(checks: list[PremiseCheck]) -> DecisionStatus | None:
    """Most permissive decision status the checks allow (None = no constraint)."""
    ids = {c.id: c.status for c in checks}
    if ids.get("source_scope") == "fail":
        return "out_of_scope"
    if any(c.status == "fail" for c in checks):
        return "insufficient"
    return None


_RANK = {"provisional": 0, "insufficient": 1, "out_of_scope": 2}


def apply_floor(status: DecisionStatus, checks: list[PremiseCheck]) -> DecisionStatus:
    floor = status_floor(checks)
    return floor if floor and _RANK[floor] > _RANK[status] else status
