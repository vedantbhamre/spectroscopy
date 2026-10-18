"""Deterministic premise checks. They run before the answer is composed and constrain it.

Input is the structured facts from the analyst node (LLM extraction) merged with keyword
detection on the client's own words, so a missed extraction does not skip a check.
Only checks that apply to the enquiry are returned.
"""

import re

from pydantic import BaseModel, Field

from app.knowledge import table1 as T1
from app.knowledge.applications import of_citation
from app.knowledge.applications import tag as app_tags
from app.knowledge.optics import FIBERS, METHODS, coverage
from app.knowledge.source_scope import clinical_scope
from app.schemas import Citation, DecisionStatus, PremiseCheck


def _carrier_ids(method: tuple[float, float], exclude: str) -> list[str]:
    return [fid for fid, f in FIBERS.items() if fid != exclude and coverage(method, f.range_um)[0] != "none"]


def _carriers(method: tuple[float, float], exclude: str) -> list[str]:
    """Fibres whose window overlaps the method range, for the 'cannot carry' check."""
    return [f"{FIBERS[fid].label} ({FIBERS[fid].range_um[0]}–{FIBERS[fid].range_um[1]} µm)" for fid in _carrier_ids(method, exclude)]


class Facts(BaseModel):
    """What the client stated. Unknown stays unknown."""

    stated: list[str] = Field(default_factory=list)
    stated_turns: list[int] = Field(default_factory=list)  # client turn each stated fact was quoted from
    unknowns: list[str] = Field(default_factory=list)
    decisive_unknowns: list[str] = Field(default_factory=list)  # unknowns that could change the method
    target_variables: list[str] = Field(default_factory=list)
    methods_mentioned: list[str] = Field(default_factory=list)  # MethodId values
    fibers_mentioned: list[str] = Field(default_factory=list)  # FIBERS keys
    fluorescent_target_named: bool | None = None
    use_context: str = "unknown"  # process | laboratory | clinical | unknown
    cites_study_as_proof: bool = False
    reuses_existing_calibration: bool = False
    new_formulation_or_matrix: bool = False
    claims_no_calibration: bool = False  # the enquiry says the method needs no calibration
    drops_reference_method: bool = False  # the enquiry proposes stopping or replacing the lab / reference method
    asks_for_certainty: bool = False
    combination_requested: bool = False
    access_points: int | None = None  # free process ports / access points the customer stated
    single_method_insufficient: bool = False  # the customer showed or stated one method is not enough
    owned_equipment: list[dict] = Field(default_factory=list)  # [{"name": str, "method": MethodId | None}]
    optical_appearance: str = "unknown"  # clear | opaque | changing | unknown (opaque includes turbid, high OD, powders)
    application_domain: str | None = None  # one of applications.DOMAINS
    qualified_targets: list[dict] = Field(default_factory=list)  # [{"qualifier": "viable", "target": "viable biomass"}]
    analyzer_remote: bool = False  # the analyzer is stated to be away from the line (another building, control room, far)
    link_length_m: float | None = None  # stated fibre link length, metres
    wavelengths_um: list[float] = Field(default_factory=list)  # measurement wavelengths the client names ("around 220 nm"), µm
    vendor_claim: bool = False  # the choice rests on what a supplier or vendor said ("the gold standard")
    drops_reference: bool = False  # expects no calibration, or wants to switch off the reference method


# Qualifiers that a bulk optical signal usually does not distinguish (the total is measured).
# Fixed terms where the word is part of a name, not a qualifier of the quantity ("active ingredient").
_NOT_QUALIFIER = r"(?!\s+(pharmaceutical\s+)?(ingredient|substance|agent|principle|compound|component|carbon|site)s?\b)"
QUALIFIERS = ["viable", "live", "living", "dead", "free", "bound", "active", "inactive", "dissolved", "suspended", "available",
              "residual", "unreacted", "crystalline", "amorphous", "ionised", "ionized", "soluble", "insoluble", "intracellular", "extracellular"]

_KW = {
    "MIR_ATR": r"\b(mir|mid[- ]?ir|mid[- ]infrared|atr|ftir)\b",
    "NIR": r"\bnir\b|near[- ]infrared",
    "RAMAN": r"\braman\b",
    # Proposed as a measurement, not mentioned as an interference ("fluorescence unknown", "is the API fluorescent?").
    "FLUO": r"fluorescence (spectrometer|spectroscopy|measurement|probe|sensor|information|detection)|fluorimetr|(use|compare|with) .{0,30}fluorescence",
    "UVVIS": r"\buv[- ]?vis\b|\buv\b",
}


NTU_CLEAR = 10  # turbidity up to this many NTU reads as a clear liquid for the geometry check


def _dropped(target: str, t: str) -> bool:
    """The client takes a target out of scope ("TOC we can drop", "leave out turbidity"); the abbreviation counts too."""
    words = re.findall(r"[a-z]+", target.lower())
    names = [re.escape(target.lower())] + ([re.escape("".join(w[0] for w in words))] if len(words) > 1 else [])
    for n in names:
        if re.search(rf"\b{n}\b,?\s+(?:(?:we\s+can|can\s+be|could\s+be)\s+(?:drop(?:ped)?|skip(?:ped)?|leave\s+out|left\s+out)"
                     rf"|is\s+(?:not\s+needed|optional)|we\s+don'?t\s+need)", t) \
                or re.search(rf"\b(drop|skip|leave\s+out|forget(\s+about)?)\s+(the\s+)?{n}\b", t):
            return True
    return False


# What a stated fact answers: an unknown or question about it is settled once the fact is known.
_ANSWERED_BY = {
    "optical_appearance": r"optical (appearance|density)|appearance|turbid|opaque|opacity|transparen|clarity|\bclear\b|cloud|ntu\b",
    "link_length_m": r"(fib(er|re)|link|cable) length|distance (to|from|between)|how far",
    "access_points": r"\b(ports?|access points?|mounting points?|flanges?|nozzles?)\b",
}


def resolved_by_facts(text: str, facts: Facts) -> bool:
    """An unknown or question that a stated fact already answers (so it is never asked or listed again)."""
    t = (text or "").lower()
    known = {"optical_appearance": facts.optical_appearance not in ("unknown", "", None),
             "link_length_m": facts.link_length_m is not None, "access_points": facts.access_points is not None}
    return any(known[k] and re.search(pat, t) for k, pat in _ANSWERED_BY.items())


def detect(text: str, facts: Facts, enquiry: str | None = None) -> Facts:
    """Fill gaps in the extracted facts from the client's own words.

    enquiry: the opening message; the method keyword fallback reads only that, so a method named in an
    answer to a question ("fluorescence unknown") is not taken as a method the client proposes.
    """
    t = text.lower()
    # Keywords only fill in when extraction found no requested method: "a silica cable from a
    # visible or NIR setup" names NIR without asking for it.
    methods = set(facts.methods_mentioned)
    if not methods:
        for mid, pat in _KW.items():
            if re.search(pat, (enquiry or text).lower()):
                methods.add(mid)
    # Fibres only when the client talks about a fibre they have or propose; the extraction alone may guess one.
    fibers = set(facts.fibers_mentioned) if re.search(r"silica|quartz|glass fib|chalcogenide|fluoride|polycrystalline|hollow|"
                                                      r"(existing|already have|our|current)\b.{0,40}\bfib(er|re)", t) else set()
    if re.search(r"silica", t):
        fibers.add("silica_uvvis" if re.search(r"\buv\b", t) and not re.search(r"nir|visible", t) else "silica_visnir")
    for fid, pat in {"chalcogenide": r"chalcogenide", "pir": r"polycrystalline|\bpir\b", "hwg": r"hollow (glass )?waveguide", "zrf": r"zirconium fluoride", "inf": r"indium fluoride"}.items():
        if re.search(pat, t):
            fibers.add(fid)
    upd: dict = {"methods_mentioned": sorted(methods), "fibers_mentioned": sorted(fibers)}
    # A classification study names its target as the classes to separate (tissue types, grades, good/bad parts).
    if not facts.target_variables and re.search(r"classif|discriminat|distinguish|differentiat|tell .{0,40}\b(from|apart)\b", t):
        upd["target_variables"] = ["sample class (classification task)"]
    if re.search(r"surg|in vivo|clinical|patient|tumou?r boundar|diagnos", t):
        upd["use_context"] = "clinical"
    if re.search(r"\b(proof|prove|ready for)\b", t) and re.search(r"stud|paper|findings", t):
        upd["cites_study_as_proof"] = True
    if re.search(r"\b(supplier|vendor|sales\s?(rep|person|man)|manufacturer|distributor|brochure|datasheet)s?\b.{0,60}\b(told|said|says|claims?|states?|recommends?)\b"
                 r"|\bgold standard\b|\bbest (method|technology|technique) (on the market|available)\b", t):
        upd["vendor_claim"] = True
    if re.search(r"\b(needs?|requires?)\s+no\s+calibration|\bno\s+calibration\s+(is\s+)?(needed|required)|without\s+(any\s+)?calibration"
                 r"|\b(switch|turn)\s+off\s+(the\s+)?(gc|hplc|lab\w*|reference)|\breplace\s+(the\s+)?(gc|hplc|lab analysis|reference method)\b"
                 r"|\b(stop|no longer)\s+(need\w*|using|use)\s+(the\s+)?(gc|hplc|lab)", t):
        upd["drops_reference"] = True
    if re.search(r"reuse the calibration|calibration (will )?remain valid|reuse (our|the) (existing )?calibration", t):
        upd["reuses_existing_calibration"] = True
    if re.search(r"(different|new) (api|formulation|blend|excipient|matrix|product)", t):
        upd["new_formulation_or_matrix"] = True
    if re.search(r"calibration[- ]free|\b(no|without( any)?|zero)\s+(\w+\s+)?calibration|\b(doesn'?t|does not|won'?t|will not|wouldn'?t|don'?t|do not|never)\s+"
                 r"(need|require)\s+(\w+\s+)?(calibrat\w*|reference)|\bno need (for|to) (\w+\s+)?calibrat|\bskip (the )?calibrat", t):
        upd["claims_no_calibration"] = True
    _ref = r"(lab(oratory)?|reference|off-?line|wet[- ]chem\w*|hplc|titration|karl fischer|gravimetric|manual sampl\w*)\s*(\w+\s+){0,2}(method|test|testing|analys[ie]s|checks?|measurements?|assays?|sampl\w*)?"
    if re.search(r"\b(replace|stop|stopping|remove|drop|eliminate|get rid of|abandon|phase out|discontinue|switch off|no longer (need|use|run|do))\b(\s+\w+){0,4}\s+" + _ref, t) \
            or re.search(_ref + r"(\s+\w+){0,3}\s+(can|could|will|would)\s+(then\s+)?(be\s+)?(stopped|dropped|removed|replaced|eliminated|discontinued|go|disappear)", t):
        upd["drops_reference_method"] = True
    if re.search(r"\b(approve|guarantee|exact (sensor )?configuration|immediately|proof|ready for)\b", t):
        upd["asks_for_certainty"] = True
    if re.search(r"(adding|add|combin\w*)\s+(raman|nir|mir|fluorescence)|both .* and ", t):
        upd["combination_requested"] = True
    # Optical appearance of the medium, from the whole transcript (clear → transmission; opaque → ATR / reflection).
    clear = re.search(r"\b(clear|transparent|translucent|low (optical density|od)|dilute|permeate)\b", t)
    opaque = re.search(r"\b(turbid\w*|cloudy|opaque|milky|high (optical density|od)|black|highly scattering|suspension|slurry|paste|"
                       r"powders?|solids?|granul\w*|thick)\b", t)
    change = re.search(r"\b(becomes?|turns?|gets?|getting|grows?)\s+(more\s+|very\s+)?(turbid|cloudy|opaque|thick|dense)|from clear to", t)
    # Turbidity stated as a number answers the appearance too: low NTU/FNU reads clear, high reads turbid, both changes.
    ntu = [float(v.replace(",", ".")) for v in re.findall(r"(\d+(?:[.,]\d+)?)\s?(?:ntu|fnu)\b", t)]
    if ntu:
        clear = clear or min(ntu) <= NTU_CLEAR
        opaque = opaque or max(ntu) > NTU_CLEAR
    appearance = "changing" if change or (clear and opaque) else "opaque" if opaque else "clear" if clear else facts.optical_appearance
    upd["optical_appearance"] = appearance if facts.optical_appearance in ("unknown", "", None) or change else facts.optical_appearance

    # Instruments the client already owns (the method they measure with, when named).
    owned = list(facts.owned_equipment)
    for m in re.finditer(r"\b(we|i)\s+(already\s+)?(have|own|use|operate|run)\s+(an?\s+|our\s+|one\s+|two\s+)?([\w\- ]{0,40}?)(spectrometer|analy[sz]er|probe|instrument|photometer|sensor)\b", t):
        phrase = m.group(0)
        mid = next((k for k, pat in _KW.items() if re.search(pat, phrase)), None)
        if mid and not any(o.get("method") == mid for o in owned):
            owned.append({"name": (m.group(5) + m.group(6)).strip(), "method": mid})
    upd["owned_equipment"] = owned
    # The customer's own words decide the domain when they point to exactly one; the extraction only fills gaps.
    tags = app_tags(t)
    if len(tags) == 1 and facts.application_domain != tags[0]:
        upd["application_domain"] = tags[0]
    elif not facts.application_domain:
        upd["application_domain"] = next(iter(tags), None)

    # Analyzer location and link length, from the whole transcript.
    if re.search(r"(another|separate|different|other|next)\s+(building|room|hall|site)|control room|far (away )?from the (line|probe|process)|"
                 r"remote(ly)?\s+(analy[sz]er|located|spectrometer)|analy[sz]er\s+(is|would be|will be|sits)\s+(far|remote|away)", t):
        upd["analyzer_remote"] = True
    if facts.link_length_m is None and (m := re.search(r"(\d+(?:[.,]\d+)?)\s?(m|metres|meters|km)\b[^.]{0,40}\b(fib(er|re)|cable|link|distance|away|long)", t)):
        n = float(m.group(1).replace(",", "."))
        upd["link_length_m"] = n * 1000 if m.group(2) == "km" else n
    # Measurement wavelengths ("UV absorbance around 220 nm"); a range ("400 to 2200 nm") describes equipment, not the measurement.
    waves = {round(float(v.replace(",", ".")) / (1000 if u == "nm" else 1), 4)
             for v, u in re.findall(r"\b(?:at|around|near|approximately|approx\.?|about|of)\s*[~≈]?\s*(\d{2,5}(?:[.,]\d+)?)\s?(nm|µm|um)\b(?!\s*(?:–|-|to)\s*\d)", t)}
    upd["wavelengths_um"] = sorted(set(facts.wavelengths_um) | waves)
    # Targets the client drops later ("TOC we can drop") leave the scope.
    upd["target_variables"] = [v for v in upd.get("target_variables", facts.target_variables) if not _dropped(v, t)]

    # Qualified targets ("viable biomass", "free fatty acids", "dissolved oxygen").
    qualified = []
    for target in upd["target_variables"]:
        tl = target.lower()
        q = next((w for w in QUALIFIERS if re.search(rf"\b{w}\b{_NOT_QUALIFIER}", tl)), None)
        if not q:
            head = (re.findall(r"[a-z]{4,}", tl) or [""])[-1]
            m = head and re.search(rf"\b({'|'.join(QUALIFIERS)})\b{_NOT_QUALIFIER}\s+(\w+\s+)?{re.escape(head)}", t)
            q = m.group(1) if m else None
            target = f"{q} {target}" if q else target
        if q:
            qualified.append({"qualifier": q, "target": target})
    upd["qualified_targets"] = qualified

    if "FLUO" in methods and re.search(r"(not|no)( yet)? (identified|named|defined)? ?(a )?fluorescent (target|marker)|have not identified a fluorescent", t):
        upd["fluorescent_target_named"] = False
    return facts.model_copy(update=upd)


def run_checks(facts: Facts, open_points: int = 0) -> list[PremiseCheck]:
    """open_points: ledger questions still open (they count as decisive unknowns for the certainty check)."""
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
                    detail=f"A {f.label} transmits about {f.range_um[0]}–{f.range_um[1]} µm; {m.label} works at {m.range_label}. The link cannot carry the signal."
                    + (f" Fibres in the supplied material that reach this range: {', '.join(alt)}." if (alt := _carriers(m.range_um, fid)) else ""),
                    citations=cites + [FIBERS[a].cite for a in _carrier_ids(m.range_um, fid)],
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

    # 2b. Fibre window covers the wavelength the client names (methods without a fixed nominal range, e.g. UV-Vis at 220 nm).
    ranged = {c.id for c in checks}
    for fid in facts.fibers_mentioned:
        f = FIBERS.get(fid)
        outside = [w for w in facts.wavelengths_um if f and not f.range_um[0] <= w <= f.range_um[1]]
        if not f or not outside:
            continue
        mid = next((m for m in facts.methods_mentioned if m in METHODS and not METHODS[m].range_um), None) or "WAVELENGTH"
        if f"fiber_{fid}_{mid}" in ranged:
            continue
        nm = ", ".join(f"{w * 1000:g} nm" for w in outside)
        alt = [a for a, af in FIBERS.items() if a != fid and all(af.range_um[0] <= w <= af.range_um[1] for w in outside)]
        checks.append(PremiseCheck(
            id=f"fiber_{fid}_{mid}", label=f"{f.label} carries {nm}", status="fail",
            detail=f"A {f.label} transmits about {f.range_um[0]}–{f.range_um[1]} µm ({f.range_um[0] * 1000:g}–{f.range_um[1] * 1000:g} nm); "
                   f"the stated measurement wavelength {nm} lies outside it, so the link cannot carry the signal."
                   + (f" Fibres in the supplied material that reach it: {', '.join(f'{FIBERS[a].label} ({FIBERS[a].range_um[0]}–{FIBERS[a].range_um[1]} µm)' for a in alt)}." if alt else ""),
            citations=[f.cite] + [FIBERS[a].cite for a in alt],
        ))

    # 3. Fluorescence needs a defined fluorescent species, unless the task is to classify samples: then the samples' own
    #    fluorescence differing between classes is the measurand (S01 p.7, S04 p.4).
    classification = any("classification" in t for t in facts.target_variables)
    if "FLUO" in facts.methods_mentioned and facts.fluorescent_target_named is False and classification:
        checks.append(PremiseCheck(
            id="fluorescent_target", label="Fluorescence has a defined fluorescent target", status="pass",
            detail="Classification study: the measurand is how the samples' own fluorescence differs between classes; no single fluorescent species has to be named. Whether it separates these classes is for the first experiment to show.",
            citations=[Citation(source="S01", page="7", quote="The combination of fluorescence and IR spectroscopy also proved necessary for classifying biological tissues.", check="verified")],
        ))
    elif "FLUO" in facts.methods_mentioned and facts.fluorescent_target_named is False:
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
        dims = clinical_scope() if clinical else []
        checks.append(PremiseCheck(
            id="source_scope", label="Sources are used within their demonstrated scope", status="fail" if clinical else "flag",
            detail=("The supplied clinical study is a laboratory feasibility study; it cannot be quoted as proof of clinical or "
                    "surgical readiness. It differs from that use in: " + "; ".join(d for d, _ in dims) + "."
                    if clinical else "A published application is a reason to test a method, not proof that it will work for this customer."),
            citations=[c.model_copy(update={"check": "verified"}) for _, c in dims],
        ))

    # 4b. A supplier's statement is a claim to test, not evidence for the method choice.
    if facts.vendor_claim:
        checks.append(PremiseCheck(
            id="vendor_claim", label="Supplier claim: a statement to test, not evidence", status="flag",
            detail="The method is proposed because a supplier recommends it. The choice here rests on the supplied AFS material and on "
                   "the first experiment; compare the claimed method with the simplest sufficient alternative on the customer's own samples.",
        ))

    # 4c. "No calibration needed" / "stop the lab method": spectra become results only through calibration models built
    #     against reference values (S01 p.5, p.12), so the reference method stays until the in-line method is validated.
    if facts.claims_no_calibration or facts.drops_reference_method or facts.drops_reference:
        what = " and ".join(x for x in ("needs no calibration" if facts.claims_no_calibration else "",
                                        "the reference method can be stopped" if facts.drops_reference_method else "") if x) \
            or "no calibration or reference method is needed"
        checks.append(PremiseCheck(
            id="calibration_and_reference", label="A calibration and the reference method are still needed", status="flag",
            detail=(f"The enquiry assumes {what}; the supplied material does not support that. Spectra give concentrations or "
                    "classes only through chemometric calibration models built against reference values, so the existing "
                    "reference method stays until the in-line method is validated against it."),
            citations=[
                Citation(source="S01", page="12", quote="Therefore, Raman spectra (as well as IR absorption spectra) can be used to construct chemometric models—calibration or classification ones.", check="verified"),
                Citation(source="S01", page="5", quote="Extracting the information necessary for quantitative and qualitative analysis from optical spectra requires special methods for analyzing multidimensional data, called the above-mentioned term chemometrics.", check="verified"),
            ],
        ))

    # 5. Calibration transfer to a new formulation.
    if facts.reuses_existing_calibration and facts.new_formulation_or_matrix:
        checks.append(PremiseCheck(
            id="calibration_transfer", label="An existing calibration applies to the new material", status="flag",
            detail="The calibration was built for a different formulation. Whether it transfers has to be tested on the new blend with independent references; adding a method does not by itself keep it valid.",
        ))

    # 6. A combination is an escalation, justified only when one method is shown to be insufficient.
    if facts.combination_requested:
        checks.append(combination_check(facts))

    # 7. Certainty requested beyond what the facts allow.
    if facts.asks_for_certainty:
        failed = sum(c.status == "fail" for c in checks)
        decisive = len(facts.unknowns) + open_points + failed
        if decisive:
            checks.append(PremiseCheck(
                id="certainty", label="Certainty: the answer can only be provisional", status="flag",
                detail=f"The customer asks for approval, proof or an exact configuration, but {decisive} decisive point(s) are still open or contradicted. "
                       "The answer is a provisional assessment; the open points are listed as assumptions and the first experiment decides them.",
            ))
        else:
            checks.append(PremiseCheck(id="certainty", label="Certainty: nothing decisive is unknown", status="pass",
                                       detail="All points that could change the method or setup have been answered."))

    return checks


COMBINED_PROBE = Citation(source="S01", page="15", check="verified", quote=(
    "A multispectral NIRaman fiber probe has industrial grade design that combines NIR reflection and Raman optical "
    "techniques in a compact shaft that fits in a tablet press feed frame."))


def combination_check(facts: Facts) -> PremiseCheck:
    cite = [Citation(source="S01", page="15", quote="By combining Raman and NIR, these models can predict API potency or coating thickness with higher accuracy and robustness than single-method models.", check="verified")]
    if facts.single_method_insufficient:
        return PremiseCheck(id="combination", label="Method combination: justified, one method is stated to be insufficient", status="pass",
                            detail="The customer states that a single method does not meet the need, so a combination is a reasonable next step; its gain is still tested.",
                            citations=cite)
    return PremiseCheck(
        id="combination", label="Method combination: an escalation option, not justified up front", status="flag",
        detail="Start with the simplest method that could meet the need and assess each method on its own; combine only if one is shown to be insufficient. A gain from combining is a hypothesis to test for this material.",
        citations=cite,
    )


_HANDLED = {
    "a combined probe": r"combin\w* (nir.?raman|probe)|multispectral|niraman|one (compact )?shaft|single (combined )?probe",
    "sequential measurement": r"one after the other|sequential|in turn|alternat|consecutive|first .* then .* (same|port)",
    "an offline rig": r"off-?line (rig|set-?up|test)|laboratory rig|lab rig|bench",
}


def access_check(facts: Facts, report: dict) -> PremiseCheck | None:
    """More probe methods recommended in parallel than the customer has free access points (after compose)."""
    if facts.access_points is None:
        return None
    recs = [r for r in report.get("recommendations", []) if r.get("role") in ("primary", "comparison", "combination")]
    methods = {m for r in recs for m in r.get("methodIds", [])}
    if len(methods) <= facts.access_points:
        return PremiseCheck(id="access_points", label="Access points: the probes fit the free ports", status="pass",
                            detail=f"{len(methods)} probe method(s) for {facts.access_points} free access point(s).")
    # Judged on the measurement concept (where the setup is described), not on a later escalation step.
    concept = report.get("concept", {})
    text = " ".join([concept.get("summary", ""), concept.get("probe") or "", concept.get("location") or ""]).lower()
    how = [name for name, pat in _HANDLED.items() if re.search(pat, text)]
    combined_ok = combined_probe_applies(facts)
    if "a combined probe" in how and not combined_ok:
        how.remove("a combined probe")  # the sources show the combined probe for another application only
    parallel = re.search(r"parallel|simultaneous|both probes|two probes|second probe", text) and "a combined probe" not in how
    if how and not parallel:
        return PremiseCheck(id="access_points", label="Access points: more methods than free ports, handled", status="pass",
                            detail=f"{len(methods)} methods for {facts.access_points} free access point(s), handled by {' or '.join(how)}.",
                            citations=[COMBINED_PROBE] if "a combined probe" in how else [])
    options = (["a combined NIR–Raman probe in one shaft (shown in the sources for this kind of application)"] if combined_ok else []) + [
        "measuring the methods one after the other on the same samples", "an offline rig"]
    return PremiseCheck(
        id="access_points", label="Access points: more probes than free ports", status="flag",
        detail=f"{len(methods)} probe methods are recommended for {facts.access_points} free access point(s). Use " + ", ".join(options[:-1]) + f" or {options[-1]}.",
        citations=[COMBINED_PROBE] if combined_ok else [],
    )


def combined_probe_applies(facts: Facts) -> bool:
    """The sources show the combined NIR–Raman probe for one application; elsewhere it is a transfer assumption."""
    return bool(facts.application_domain) and facts.application_domain in of_citation(COMBINED_PROBE.source, COMBINED_PROBE.page, COMBINED_PROBE.quote)


def _recommended(report: dict) -> list[dict]:
    return [r for r in report.get("recommendations", []) if r.get("role") in ("primary", "comparison", "combination")]


def target_qualifier_check(facts: Facts, report: dict, support: dict[str, str]) -> PremiseCheck | None:
    """A qualified target (viable, free, dissolved, …) that the proposed method's sources do not distinguish.

    support: method id → text of the verified passages cited for it."""
    recs = _recommended(report)
    if not facts.qualified_targets or not recs:
        return None
    limits = []
    for qt in facts.qualified_targets:
        blind = sorted({m for r in recs for m in r.get("methodIds", []) if not re.search(rf"\b{qt['qualifier']}\b", support.get(m, ""))})
        if blind:
            limits.append((qt, blind))
    if not limits:
        return PremiseCheck(id="target_qualifier", label="Target qualifier: the cited sources address it", status="pass",
                            detail="The cited passages discuss the qualified quantity for the proposed method(s).")
    detail = " ".join(
        f"The target is '{qt['target']}', but the sources cited for {', '.join(METHODS[m].label if m in METHODS else m for m in blind)} do not show that the "
        f"signal distinguishes '{qt['qualifier']}' from the total; the method may follow a related quantity instead. A reference method that measures "
        f"'{qt['target']}' itself is required to test whether the signal follows it." for qt, blind in limits)
    return PremiseCheck(id="target_qualifier", label="Target qualifier: the method may not distinguish it", status="flag", detail=detail)


MIR_SHOWN_LENGTH_M = 2  # mid-IR fibres appear in the supplied material only as 2 m assemblies (S02 p.9)
LONG_SILICA = Citation(source="S02", page="7", check="verified", quote="Robust 100-300m cables made with Silica fibers of low OH-content")
MIR_2M = Citation(source="S02", page="9", check="visual_note", quote="both 2 m long (HWG-750-2m, PIR 600/700-2m)")
MIR_NO_DISTANCE = Citation(source="S02", page="13", check="visual_note", quote="no process installation, fiber length or analyzer distance is shown")


def mir_link_check(facts: Facts, report: dict) -> PremiseCheck | None:
    """A mid-IR method with a remote analyzer or a link longer than the mid-IR fibres the sources show.

    Long (100–300 m) cables appear in the supplied material only for silica (Vis-NIR) fibres; mid-IR fibres appear
    only as 2 m assemblies, so a longer mid-IR link is not shown to work and must be measured or avoided."""
    # Methods whose range starts beyond the silica window (silica cannot carry them at all).
    mid_ir = {m for m, meth in METHODS.items() if meth.range_um and meth.range_um[0] >= FIBERS["silica_visnir"].range_um[1]}
    proposed = {m for r in _recommended(report) for m in r.get("methodIds", [])} | set(facts.methods_mentioned)
    methods = sorted(mid_ir & proposed)
    long_link = facts.link_length_m is not None and facts.link_length_m > MIR_SHOWN_LENGTH_M
    if not methods or not (facts.analyzer_remote or long_link):
        return None
    where = (f"a {facts.link_length_m:g} m link" if long_link else "an analyzer away from the line (length not given)")
    names = ", ".join(METHODS[m].label for m in methods)
    return PremiseCheck(
        id="mir_link_length", label="Mid-IR fibre link: distance not shown to be feasible", status="flag",
        detail=f"{names} needs mid-IR fibres, and the enquiry implies {where}. In the supplied material, long (100–300 m) cables are "
               f"shown only for silica fibres, which do not carry the mid-IR; mid-IR fibres appear only as {MIR_SHOWN_LENGTH_M} m assemblies, and the "
               "application example shows no fibre length or analyzer distance. Measure the transmission over the planned length before "
               "committing, or plan the analyzer close to the measurement point.",
        citations=[LONG_SILICA, MIR_2M, MIR_NO_DISTANCE],
    )


_ESCALATION = re.compile(r"\b(otherwise|if (not|it fails|the correlation is (weak|poor))|consider adding|escalat\w*|only if|as a fallback|later add)\b", re.I)


def owned_equipment_check(facts: Facts, report: dict) -> PremiseCheck | None:
    owned = [o for o in facts.owned_equipment if o.get("method") in METHODS or o.get("method") in ("RAMAN", "FLUO", "UVVIS")]
    if not owned:
        return None
    mentioned = {m for r in report.get("recommendations", []) if r.get("role") != "not_recommended" for m in r.get("methodIds", [])}
    # An escalation ("otherwise consider adding NIR") does not use the instrument the customer owns.
    plan = " ".join(s for s in report.get("feasibility", {}).get("steps", []) if not _ESCALATION.search(s)).lower()
    missing = [o for o in owned if o["method"] not in mentioned and not re.search(_KW.get(o["method"], "$^"), plan)]
    names = ", ".join(o.get("name") or o["method"] for o in owned)
    if missing:
        return PremiseCheck(id="owned_equipment", label="Owned equipment: not assessed", status="flag",
                            detail=f"The customer already has {', '.join(o.get('name') or o['method'] for o in missing)}. State what the sources say it can and "
                                   "cannot measure here and use it in the feasibility plan where supported, before proposing new equipment.")
    return PremiseCheck(id="owned_equipment", label="Owned equipment: assessed", status="pass",
                        detail=f"The customer's existing equipment ({names}) is assessed in the recommendation or the feasibility plan.")


def geometry_check(facts: Facts, report: dict) -> PremiseCheck | None:
    """Probe geometry vs the optical appearance of the medium (S01 p.16, p.18; Table 1)."""
    c = report.get("concept", {})
    text = " ".join([c.get("summary", ""), c.get("probe") or "", c.get("location") or ""]).lower()
    # ATR is its own geometry: it suits clear liquids and opaque media alike (Table 1: liquid, paste, soft).
    atr = bool(re.search(r"\batr\b|attenuated total", text))
    text = re.sub(r"attenuated total reflect\w*", "atr", text)
    trans = bool(re.search(r"transmission|transflect", text))
    refl = bool(re.search(r"reflect", text)) or (atr and not trans)
    a = facts.optical_appearance
    if a == "unknown" or not (trans or refl):
        return None
    label = "Probe geometry matches the optical density of the medium"
    if a == "clear" and refl and not trans and not atr:
        return PremiseCheck(id="geometry_optics", label="Probe geometry: reflection for a clear medium", status="flag",
                            detail="The medium is described as clear. Transmission or transflection suits transparent, low optical density liquids; reflection can be less representative for clear liquids.",
                            citations=[T1.CLEAR_TRANSMISSION, T1.REFLECTION_SCATTERING])
    if a == "opaque" and trans and not refl:
        return PremiseCheck(id="geometry_optics", label="Probe geometry: transmission for an opaque medium", status="flag",
                            detail="The medium is described as turbid, opaque or scattering. A transmission path saturates when light cannot penetrate the sample; ATR or reflection is used at high optical density.",
                            citations=[T1.OPAQUE_SATURATES, T1.HIGH_OD_ATR])
    if a == "changing" and trans:
        return PremiseCheck(id="geometry_optics", label="Probe geometry: the medium changes from clear to opaque", status="flag",
                            detail="The medium changes from clear to opaque, so a single transmission path may saturate. Plan ATR or reflection for the opaque phase, or check the path length on samples from both phases.",
                            citations=[T1.OPAQUE_SATURATES, T1.HIGH_OD_ATR])
    return PremiseCheck(id="geometry_optics", label=label, status="pass",
                        detail=f"Medium described as {a}; the proposed {'transmission' if trans else 'ATR' if atr else 'reflection'} geometry suits it.",
                        citations=[T1.CLEAR_TRANSMISSION] if a == "clear" else [T1.OPAQUE_SATURATES])


def cost_check(report: dict) -> PremiseCheck | None:
    """Simplest, cheapest sufficient method first (S01 Table 1 cost column, probe options)."""
    recs = _recommended(report)
    primary = [m for r in recs if r["role"] == "primary" for m in r.get("methodIds", [])]
    others = [m for r in recs if r["role"] != "primary" for m in r.get("methodIds", []) if m not in primary]
    costs = {m: T1.probe_cost(m) for m in primary + others if T1.probe_cost(m)}
    if not primary or not others or not all(m in costs for m in primary):
        return None
    p_cost = max(T1.RANK[costs[m]] for m in primary)
    cheaper = [m for m in others if m in costs and T1.RANK[costs[m]] < p_cost]
    fmt = lambda ms: ", ".join(f"{METHODS[m].label if m in METHODS else m} ({costs[m]})" for m in ms)  # noqa: E731
    if cheaper:
        return PremiseCheck(id="cost", label="Simplest method first: a cheaper candidate is ranked lower", status="flag",
                            detail=f"Table 1 rates the primary candidate {fmt(primary)} above {fmt(cheaper)} in cost. State why the cheaper method is not sufficient, or test it first.",
                            citations=[T1.TABLE1])
    return PremiseCheck(id="cost", label="Simplest method first: the primary is the cheapest candidate", status="pass",
                        detail=f"Table 1 cost of the probe options: primary {fmt(primary)}, others {fmt(others)}.", citations=[T1.TABLE1])
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
