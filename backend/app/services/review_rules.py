"""Deterministic report rules from the expert review (generic: extracted facts, report fields and AFS sources only).

P1  certainty: a provisional assessment never claims a method "can meet", "will achieve", "guarantees" or is "approved";
    a "Yes" answer becomes "the most promising first candidate to test".
P2  decisive unknowns: an unknown that could change the method is asked (or, in a final report, listed as a risk and
    tested in the plan); "no open questions" never hides one.
P5  limitations: each recommendation lists what the premise checks found for its method (fibre range, link length,
    geometry); a combination is an escalation after single methods.
P8  wording: "excitation" only for Raman and fluorescence; NIR, MIR and UV-Vis use "absorption range".
P9  plan order: laboratory samples → model and validation on held-out samples → in-line / pilot against the reference
    → decision basis with accuracy and alarm threshold agreed separately.
P10 hardware details (window materials, seals, pressure ratings, path lengths) need a cited passage; path lengths must
    lie in S01 Table 1's range for the proposed methods. Unsupported details move to the points to confirm.
"""

import re

from app.knowledge.table1 import PATHS_UM
from app.schemas import PremiseCheck, Question, Report
from app.services import ledger as L
from app.services.validators import passages, sentences, supported

# ---------------------------------------------------------------- P1
CERTAINTY = re.compile(
    r"\b(can|will|would)\s+(reliably\s+)?(meet|achieve|fulfil|fulfill|satisfy|guarantee|ensure)\b|\bguarantee[sd]?\b|\bapproved\b"
    r"|\bwill\s+(reliably\s+)?(work|detect|measure|deliver|succeed)\b|\b(is|are)\s+proven\b|\bproven\s+to\b|\bcertainly\b", re.I)
_SOFT = [
    (re.compile(r"\b(can|will|would)\s+(reliably\s+)?(meet|achieve|fulfil|fulfill|satisfy|ensure)\b", re.I), r"may \3"),
    (re.compile(r"\b(can|will|would)\s+(reliably\s+)?guarantee\b", re.I), "may support"),
    (re.compile(r"\bguarantees\b", re.I), "may support"),
    (re.compile(r"\bguaranteed\b", re.I), "expected"),
    (re.compile(r"\bapproved\b", re.I), "to be approved"),
    (re.compile(r"\bwill\s+(reliably\s+)?(work|detect|measure|deliver|succeed)\b", re.I), r"may \2"),
    (re.compile(r"\b(is|are)\s+proven\b", re.I), r"\1 shown in the source"),
    (re.compile(r"\bproven\s+to\b", re.I), "shown to"),
    (re.compile(r"\bcertainly\s+", re.I), ""),
]
_YES = re.compile(r"^\s*yes\b[\s,.:;–-]*", re.I)


def soften(text: str | None) -> tuple[str | None, int]:
    if not text or not CERTAINTY.search(text):
        return text, 0
    n = len(CERTAINTY.findall(text))
    for pat, rep in _SOFT:
        text = pat.sub(rep, text)
    return text, n


def reject_certainty(report: Report) -> int:
    """Certainty phrases are rejected while nothing has been measured (every assessment here is provisional at best)."""
    n = 0
    primary = next((r for r in report.recommendations if r.role == "primary"), None)
    a = report.answer
    if a and (CERTAINTY.search(a.text) or (_YES.match(a.text) and report.decisionStatus != "out_of_scope")):
        n += max(len(CERTAINTY.findall(a.text)), 1)
        rest = _YES.sub("", soften(a.text)[0] or "").strip()
        lead = f"{primary.method} is the most promising first candidate to test" if primary else "Possibly, but not shown yet"
        a.text = f"{lead}: {rest[:1].lower() + rest[1:]}" if rest else f"{lead}; the first feasibility experiment decides it."
        if "experiment" not in a.text.lower():
            a.text = a.text.rstrip(". ") + "; the first feasibility experiment decides whether it meets the requirement."
        a.sayInstead, k = soften(a.sayInstead)
        n += k
    for r in report.recommendations:
        r.reason, k = soften(r.reason)
        n += k
    c = report.concept
    c.summary, k = soften(c.summary)
    n += k
    report.spectralRange.summary, k = soften(report.spectralRange.summary)
    n += k
    steps = []
    for s in report.feasibility.steps:
        s, k = soften(s)
        n += k
        steps.append(s)
    report.feasibility.steps = steps
    report.feasibility.decisionBasis, k = soften(report.feasibility.decisionBasis)
    n += k
    return n


# ---------------------------------------------------------------- P2
def _ask(unknown: str) -> str:
    u = unknown.strip().rstrip(".?")
    if re.match(r"(whether|which|what|how|if|where|when|who)\b", u, re.I):
        return f"Can you tell us {u[0].lower() + u[1:]}?"
    return f"Can you tell us the {u[0].lower() + u[1:]}?" if not u[:1].isupper() or not u[1:2].isupper() else f"Can you tell us: {u}?"


def enforce_decisive(report: Report, decisive: list[str], final: bool, turn: int) -> dict:
    """Decisive unknowns persist and are asked; in a final report each becomes a risk and a plan step."""
    stats = {"decisive_open": 0, "decisive_added": 0}
    report.requirements.decisive = list(dict.fromkeys(decisive))
    for u in report.requirements.decisive:
        if not any(L.similar(u, x) for x in report.requirements.unknowns):
            report.requirements.unknowns.append(u)
    led = report.questions
    method_open = any(q.status == "open" and q.impact == "method" for q in led)
    for u in report.requirements.decisive:
        asked = next((q for q in led if L.similar(u, q.text)), None)
        if L.asks_assistant_decision(_ask(u)):  # the expert's own choice (material, fibre type): confirmed, never asked
            note = f"For the expert to select and confirm with the supplier: {u.rstrip('.')}."
            if not any(L.similar(u, p) for p in report.pointsToConfirm):
                report.pointsToConfirm.append(note)
            continue
        if final:
            risk = f"Decisive point not confirmed by the customer, assumed for now: {u}."
            if not any(L.similar(u, r) for r in report.risks):
                report.risks.append(risk)
            if not any(L.similar(u, s) for s in report.feasibility.steps):
                report.feasibility.steps.insert(0, f"Establish with the first laboratory samples: {u}.")
            stats["decisive_open"] += 1
            continue
        if asked is None and method_open:
            stats["decisive_open"] += 1  # an open method question already asks for it (in other words)
            continue
        if asked is None:
            from app.services.ledger import _next_id

            led.append(Question(text=_ask(u), impact="method", id=_next_id(led), askedTurn=turn))
            stats["decisive_added"] += 1
            stats["decisive_open"] += 1
        elif asked.status == "open":
            stats["decisive_open"] += 1
    report.questions = led
    return stats


# ---------------------------------------------------------------- P5
def add_limitations(report: Report, checks: list[PremiseCheck]) -> None:
    for r in report.recommendations:
        lim: list[str] = []
        for c in checks:
            if c.status == "pass":
                continue
            m = re.fullmatch(r"fiber_\w+?_(NIR|MIR_ATR|RAMAN|FLUO|UVVIS)", c.id)
            if (m and m.group(1) in r.methodIds) or (c.id == "mir_link_length" and "MIR_ATR" in r.methodIds) \
                    or (c.id == "geometry_optics" and r.role == "primary"):
                lim.append(f"{c.label}: {c.detail}")
        if r.role == "combination":
            lim.append("Escalation: only after each method has been assessed on its own; the gain is a hypothesis to test.")
        r.limitations = list(dict.fromkeys([*r.limitations, *lim]))


# ---------------------------------------------------------------- P8
_NOT_EXCITED = re.compile(r"\b(nir|near[- ]infrared|mir|mid[- ]?ir|mid-infrared|atr|ftir|uv[- ]?vis|uv|ultraviolet)\b", re.I)
_EXCITED = re.compile(r"raman|fluoresc", re.I)


def fix_excitation(report: Report) -> int:
    n = 0

    def fix(text: str | None) -> str | None:
        nonlocal n
        if not text or "excitation" not in text.lower():
            return text
        out = []
        for s in sentences(text) or [text]:
            if re.search(r"excitation", s, re.I) and _NOT_EXCITED.search(s) and not _EXCITED.search(s):
                s = re.sub(r"excitation (range|band|wavelength)s?", r"absorption \1", s, flags=re.I)
                s = re.sub(r"\bexcitation\b", "absorption", s, flags=re.I)
                n += 1
            out.append(s)
        return " ".join(out)

    report.spectralRange.summary = fix(report.spectralRange.summary) or ""
    report.concept.summary = fix(report.concept.summary) or ""
    for r in report.recommendations:
        r.reason = fix(r.reason) or ""
    return n


# ---------------------------------------------------------------- P9
_PH_DECISION = re.compile(r"\b(decide|decision|go/no-go|acceptance criteri|agree[ds]? (with|on)|criteria)\b", re.I)
_PH_INLINE = re.compile(r"\b(in-line|inline|on-line|online|at-line|pilot|install|plant|production line|process line|under process conditions|real operating)\b", re.I)
_PH_MODEL = re.compile(r"\b(model|calibrat\w*|chemometric|pls|pca|validat\w*|held-out|cross-valid\w*|classif\w*)\b", re.I)
_PH_LAB = re.compile(r"\b(lab|laboratory|samples?|spectra|bench|offline|off-line|interferen\w*|range)\b", re.I)
_DASHES = str.maketrans({c: "-" for c in "‐‑‒–—"})


# Getting the measuring hardware ready (a fibre, cell, lamp) comes before any spectra; installing at the process point does not.
_PH_SETUP = re.compile(r"\b(obtain|procure|buy|order|source|replace|swap|fit|equip|assemble|set up|install)\b.{0,60}?"
                       r"\b(fib(er|re)s?|cells?|lamps?|light sources?|spectrometers?|cables?|windows?)\b", re.I)
_PROCESS_POINT = re.compile(r"\b(line|channel|reactor|vessel|feed frame|flange|port|pipe|tank|plant|pilot|in-line|inline|on-line|"
                            r"process|production|press|stream|outlet|inlet)\b", re.I)


def _phase(step: str) -> int | None:
    s = step.translate(_DASHES)
    if _PH_SETUP.search(s) and not _PROCESS_POINT.search(s):
        return 0
    if _PH_DECISION.search(s) and not _PH_MODEL.search(s):
        return 4
    if _PH_INLINE.search(s):
        return 3
    if _PH_MODEL.search(s):
        return 2
    if _PH_LAB.search(s):
        return 1
    return None


def lab_step() -> str:
    return "Measure representative laboratory samples first to learn the signal, the usable spectral range and the interferences."


def held_out_step(medical: bool) -> str:
    who = "other patients or specimens" if medical else "other batches, days or production runs"
    return (f"Build the model and validate it on samples not used to build it (held-out samples from {who}); "
            "a model built on few samples can fit them without generalising.")


def inline_step(medical: bool) -> str:
    return ("Then measure fresh specimens under realistic conditions against the reference method." if medical
            else "Then measure in-line or in a pilot set-up against the reference method.")


THRESHOLD_NOTE = ("Agree two things separately with the customer before the test: the model accuracy required against the "
                  "reference method, and the alarm or action threshold applied to the measured value.")


def order_plan(report: Report, medical: bool) -> None:
    """Lab → model/validation → in-line/pilot → decision; missing phases get a domain-neutral step."""
    steps = [s for s in report.feasibility.steps if s.strip()]
    if not medical:  # the prompt's held-out example names patients; outside medical work they are batches or days
        steps = [re.sub(r"\b(other\s+)?patients(,\s*|\s+or\s+)", r"\1", s) for s in steps]
    phases, last = [], 1
    for s in steps:
        p = ph if (ph := _phase(s)) is not None else last  # phase 0 (hardware setup) is a phase, not "unknown"
        phases.append(p)
        last = p
    present = set(phases)
    if 1 not in present:
        steps.insert(0, lab_step())
        phases.insert(0, 1)
    if 2 not in present:
        steps.append(held_out_step(medical))
        phases.append(2)
    if 3 not in present and report.decisionStatus != "out_of_scope":
        steps.append(inline_step(medical))
        phases.append(3)
    report.feasibility.steps = [s for _, _, s in sorted(zip(phases, range(len(steps)), steps))]
    basis = report.feasibility.decisionBasis.strip()
    if not re.search(r"threshold|alarm|action limit", basis, re.I):
        report.feasibility.decisionBasis = f"{basis} {THRESHOLD_NOTE}".strip()


# ---------------------------------------------------------------- P10
HARDWARE = re.compile(
    r"\b(sapphire|diamond|znse|zinc selenide|silicon window|quartz window|caf2|baf2|germanium|hastelloy|stainless|316l|ptfe|peek|"
    r"viton|kalrez|ffkm|o-ring|gasket|\d+(\.\d+)?\s?(bar|psi|mpa)|pressure rat\w+|ip6\d|atex|path ?length|optical path|window material)\b", re.I)
_PATH = re.compile(r"(path ?length|optical path|gap)[^.;]{0,40}?(\d+(?:[.,]\d+)?)\s?(?:(?:–|-|to)\s?(\d+(?:[.,]\d+)?))?\s?(µm|um|μm|mm)", re.I)


def _path_ok(sentence: str, methods: list[str]) -> bool:
    m = _PATH.search(sentence)
    if not m:
        return True
    scale = 1000 if m.group(4).lower() == "mm" else 1
    vals = [float(v.replace(",", ".")) * scale for v in (m.group(2), m.group(3)) if v]
    ranges = [r for mid in methods for r in PATHS_UM.get(mid, [])]
    return any(all(lo <= v <= hi for v in vals) for lo, hi in ranges)


def validate_hardware(report: Report) -> int:
    """Unsupported hardware details in the concept and the plan move to the points to confirm."""
    support = passages([c for h in [*report.recommendations, report.concept, report.spectralRange] for c in h.citations])
    methods = sorted({m for r in report.recommendations if r.role != "not_recommended" for m in r.methodIds})
    n = 0

    def ok(s: str) -> bool:
        if not HARDWARE.search(s):
            return True
        return supported(s, support) and _path_ok(s, methods)

    def confirm(s: str) -> None:
        nonlocal n
        n += 1
        note = f"Confirm with the supplier or the customer: {s.strip().rstrip('.')}."
        if not L.covered(s, report.pointsToConfirm, 0.8):  # the probe field repeats the concept sentence
            report.pointsToConfirm.append(note)

    c = report.concept
    kept = []
    for s in sentences(c.summary):
        (kept.append(s) if ok(s) else confirm(s))
    c.summary = " ".join(kept) or c.summary
    for field in ("probe", "location", "fiberLink", "analyzer"):
        v = getattr(c, field)
        if v and not ok(v):
            confirm(v)
            setattr(c, field, f"{v} (to confirm)")
    steps = []
    for s in report.feasibility.steps:
        (steps.append(s) if ok(s) else confirm(s))
    report.feasibility.steps = steps
    return n


# ---------------------------------------------------------------- a failed fibre check is settled, not hedged
_OLD_FIBER = re.compile(r"\b(existing|current|old|present|their|the customer's|reused?)\s+(\w+[\s-]+){0,3}?fib(er|re)", re.I)
_HEDGE = re.compile(r"\b(may|might|could)\s+not\s+(transmit|carry|cover|pass|work)", re.I)
_TEST_IT = re.compile(r"\b(verify|test|check|measure|confirm|determine)\w*\b|cut-?off", re.I)


def settle_failed_fiber(report: Report) -> int:
    """When a premise check shows the fibre cannot carry the range, the report says so: no step re-tests the old fibre,
    no risk says it "may not" transmit, no point asks to confirm its cut-off."""
    failed = [c for c in report.premiseChecks if c.id.startswith("fiber_") and c.status == "fail"]
    if not failed:
        return 0
    n = 0
    about_old = lambda s: bool(_OLD_FIBER.search(s))  # noqa: E731
    keep = [s for s in report.feasibility.steps if not (about_old(s) and _TEST_IT.search(s))]
    n += len(report.feasibility.steps) - len(keep)
    report.feasibility.steps = keep
    before = len(report.pointsToConfirm)
    report.pointsToConfirm = [p for p in report.pointsToConfirm if not (about_old(p) and _TEST_IT.search(p))]
    n += before - len(report.pointsToConfirm)
    firm = f"{failed[0].label}: no. The existing fibre has to be replaced before any measurement (see the premise check)."
    risks = []
    for r in report.risks:
        if re.search(r"fib(er|re)", r, re.I) and _HEDGE.search(r):
            n += 1
            r = firm
        if r not in risks:
            risks.append(r)
    report.risks = risks
    return n


_COLOURED = re.compile(r"\b(yellow\w*|brown\w*|dark\w*|black|amber|tinted|colou?red|discolou?r\w*)\b", re.I)


def raman_colour_risk(report: Report, customer: str) -> int:
    """Raman on a coloured or darkening sample: fluorescence background is the first thing to check."""
    raman = any("RAMAN" in r.methodIds for r in report.recommendations if r.role != "not_recommended")
    if not raman or not _COLOURED.search(customer or "") or any(re.search(r"fluoresc", r, re.I) for r in report.risks):
        return 0
    report.risks.append("The sample is coloured or darkens: fluorescence background can swamp the Raman signal. Check Raman spectra "
                        "of the darkest samples first, and compare with an absorption method if the background dominates.")
    return 1


_NO_INTERFERENCE = re.compile(r"\b(no|not|without|free of|absence of|does not contain|do not contain)\b.{0,60}\binterfer\w*", re.I)


def interferences_as_risk(report: Report) -> int:
    """'No interferents' is an assumption the samples have to confirm; it is also a risk, since other species may absorb there."""
    if not any(_NO_INTERFERENCE.search(a) for a in report.assumptions) or any(re.search(r"interfer", r, re.I) for r in report.risks):
        return 0
    report.risks.append("Other substances in the sample may absorb in the same range and interfere; test this on real samples "
                        "against the reference method before relying on the reading.")
    return 1


_WORDING = [(re.compile(r"\bsolari[sz]ed\b", re.I), "solarisation-resistant")]  # "solarised" means damaged by UV


def fix_wording(report: Report) -> int:
    n = 0

    def fix(text: str | None) -> str | None:
        nonlocal n
        for pat, rep in _WORDING:
            if text and pat.search(text):
                text, k = pat.subn(rep, text)
                n += k
        return text

    c = report.concept
    c.summary, c.fiberLink, c.probe, c.analyzer = fix(c.summary) or "", fix(c.fiberLink), fix(c.probe), fix(c.analyzer)
    for r in report.recommendations:
        r.reason = fix(r.reason) or ""
    report.risks = [fix(r) or "" for r in report.risks]
    report.feasibility.steps = [fix(s) or "" for s in report.feasibility.steps]
    return n


# ---------------------------------------------------------------- empty sections when a premise blocks the method
def explain_blocked_sections(report: Report) -> int:
    """With a failed premise check the composer may leave the concept and spectral range empty; say why instead."""
    failed = [c for c in report.premiseChecks if c.status == "fail"]
    if not failed or report.decisionStatus == "provisional":
        return 0
    why = "; ".join(f"{c.label.lower()}: not yet" for c in failed)
    n = 0
    if not report.concept.summary.strip():
        report.concept.summary = (f"No measurement concept can be fixed yet ({why}). It follows once the open questions are answered; "
                                  "the first step is to agree the measurand and its reference method with the customer.")
        n += 1
    if not report.spectralRange.summary.strip():
        report.spectralRange.summary = (f"No spectral range can be selected yet ({why}). The usable range is set by the method, "
                                        "fibre and probe chosen for the defined measurand, confirmed on sample spectra.")
        n += 1
    return n


# ---------------------------------------------------------------- calibration and reference method
KEEP_REFERENCE = "The existing reference method stays in use until the in-line method is validated against it."


def keep_reference(report: Report) -> bool:
    """When the calibration/reference premise fires, the answer, the risks and the plan all say so."""
    if not any(c.id == "calibration_and_reference" for c in report.premiseChecks):
        return False
    if report.answer and not (re.search(r"\breference\b", report.answer.text, re.I) and re.search(r"\buntil\b|\bvalidat", report.answer.text, re.I)
                              and re.search(r"\b(stays?|keep|remain|continue|alongside|parallel)\w*", report.answer.text, re.I)):
        report.answer.text = f"{report.answer.text.rstrip()} {KEEP_REFERENCE}"
    if not any(re.search(r"reference", s, re.I) and re.search(r"until|keep|parallel|alongside|stays", s, re.I) for s in report.feasibility.steps):
        report.feasibility.steps.append("Keep running the existing reference method alongside the in-line measurement until the "
                                        "in-line method is validated against it on held-out samples.")
    risk = "Without a calibration against reference values, or without the reference method, errors of the in-line method go unnoticed."
    if risk not in report.risks:
        report.risks.append(risk)
    return True


# ---------------------------------------------------------------- fact guard
_NUMWORD = {"one": 1, "a single": 1, "single": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6}
_PORTS = re.compile(r"\b(\d+|one|two|three|four|five|six|a single|single)\s+(?:free\s+|available\s+|spare\s+|open\s+)?"
                    r"(?:side\s+)?(port|access point|probe position|flange|nozzle|opening)s?\b", re.I)
_CLARITY = re.compile(r"\b(clear|transparent|translucent|turbid|opaque|cloudy|scattering)\b", re.I)
_SUBJECT = re.compile(r"\b(stream|liquid|sample|samples|product|medium|broth|melt|oil|solution|blend|powder|line|feed)\b", re.I)
_DIST = re.compile(r"\b(\d+(?:[.,]\d+)?)\s?(m|metres?|meters?|km)\b", re.I)
_HEDGED = re.compile(r"\b(assum\w*|if\b|unless|likely|presumably|probably|may\b|might\b|could\b|to be confirmed|unknown|not stated|"
                     r"not yet known|confirm|whether|e\.g\.|for example)\b", re.I)
CLARITY_GROUPS = [{"clear", "transparent", "translucent"}, {"turbid", "opaque", "cloudy", "scattering"}]


def _count(word: str) -> int | None:
    w = word.lower()
    return int(w) if w.isdigit() else _NUMWORD.get(w)


def unstated_fact(sentence: str, customer: str) -> str | None:
    """The customer fact a sentence asserts that the customer never stated (ports, clarity, distance), or None."""
    if _HEDGED.search(sentence):
        return None
    c = customer.lower()
    for m in _PORTS.finditer(sentence):
        n = _count(m.group(1))
        said = {_count(x.group(1)) for x in _PORTS.finditer(c)}
        if n not in said:
            return m.group(0)
    for m in _CLARITY.finditer(sentence):
        if _SUBJECT.search(sentence):
            group = next((g for g in CLARITY_GROUPS if m.group(1).lower() in g), {m.group(1).lower()})
            if not any(re.search(rf"\b{w}", c) for w in group):
                return m.group(0)
    from app.services.numbers import numbers_in

    for m in _DIST.finditer(sentence):
        if numbers_in(m.group(1)) - numbers_in(customer):
            return m.group(0)
    return None


def guard_facts(report: Report, customer: str) -> int:
    """Statements of customer facts the customer never gave move to the assumptions, worded as assumptions."""
    n = 0

    def clean(text: str | None) -> str | None:
        nonlocal n
        if not text:
            return text
        kept = []
        for s in sentences(text) or [text]:
            if unstated_fact(s, customer):
                note = f"Assumed, not stated by the customer: {s.rstrip('.')}."
                if note not in report.assumptions:
                    report.assumptions.append(note)
                n += 1
            else:
                kept.append(s)
        return " ".join(kept)

    if report.answer:
        report.answer.text = clean(report.answer.text) or ""
        report.answer.sayInstead = clean(report.answer.sayInstead) or None
    report.concept.summary = clean(report.concept.summary) or ""
    for field in ("location", "fiberLink", "probe", "analyzer"):
        v = getattr(report.concept, field)
        if v and unstated_fact(v, customer):
            report.assumptions.append(f"Assumed, not stated by the customer: {v}.")
            setattr(report.concept, field, f"{v} (assumed)")
            n += 1
    for r in report.recommendations:
        r.reason = clean(r.reason) or r.reason
    return n


# ---------------------------------------------------------------- cost claims vs S01 Table 1
_CHEAP = re.compile(r"\b(cheapest|cheaper|lowest[- ]cost|lower[- ]cost|least expensive|less expensive|most economical|most affordable|"
                    r"simplest|simpler|low[- ]cost|inexpensive)\b", re.I)


def check_cost_claims(report: Report) -> int:
    """'Cheapest' / 'simplest' / 'low-cost' must agree with the Table 1 cost column against the other candidates."""
    from app.knowledge import table1 as T1
    from app.knowledge.source_map import METHOD_PATTERNS

    cands = {m for r in report.recommendations if r.role != "not_recommended" for m in r.methodIds}
    cost = {m: T1.RANK[c] for m in cands if (c := T1.probe_cost(m))}
    n = 0

    def wrong(sentence: str, methods: set[str]) -> bool:
        if not _CHEAP.search(sentence):
            return False
        named = methods or {m for m, pat in METHOD_PATTERNS.items() if re.search(pat, sentence, re.I)}
        mine = [cost[m] for m in named if m in cost]
        others = [cost[m] for m in cost if m not in named]
        return bool(mine and others) and min(mine) > min(others)

    for r in report.recommendations:
        kept = []
        for s in sentences(r.reason) or [r.reason]:
            if wrong(s, set(r.methodIds)):
                n += 1
            else:
                kept.append(s)
        r.reason = " ".join(kept) or r.reason
    if report.answer:
        kept = [s for s in sentences(report.answer.text) or [report.answer.text] if not wrong(s, set())]
        n += len(sentences(report.answer.text)) - len(kept)
        report.answer.text = " ".join(kept)
    report.concept.summary = " ".join(s for s in sentences(report.concept.summary) if not wrong(s, set())) or report.concept.summary
    return n


# ---------------------------------------------------------------- numbers stated on a retrieved page: cite it
def cite_numbers(report: Report, documents: list[dict], customer: str) -> int:
    """A number the report takes from a retrieved page that it did not cite: cite the passage, so the number is sourced
    (and kept by the number validator). Numbers on no page and not from the customer are left to the validator."""
    from app.schemas import Citation
    from app.services.citations import page_text
    from app.services.numbers import TOKEN, allowed_numbers
    from app.services.passages import _pieces

    cited = allowed_numbers(customer, [page_text(c.source, c.page) for c in report.sources if c.source != "EXT"])
    fields = [(report.spectralRange, report.spectralRange.summary), (report.concept, report.concept.summary),
              *((r, r.reason) for r in report.recommendations)]
    n = 0
    for holder, text in fields:
        for m in TOKEN.finditer(text or ""):
            from app.services.numbers import _unit, _value

            vals = [v for g in (m.group(1), m.group(3)) if g and (v := _value(g)) is not None]
            unit = _unit(m.group(4))
            if not unit or cited.ok(vals, unit):
                continue
            for d in documents:
                if d.get("kind") == "table":
                    continue
                a = allowed_numbers("", [d["text"]])
                if not a.ok(vals, unit):
                    continue
                piece = next((p for p in _pieces(d["text"]) if allowed_numbers("", [p]).ok(vals, unit)), None)
                if piece:
                    c = Citation(source=d["source"], page=str(d["page"]), quote=piece, check="verified")
                    holder.citations.append(c)
                    report.sources.append(c)
                    cited = allowed_numbers(customer, [*(page_text(x.source, x.page) for x in report.sources if x.source != "EXT")])
                    n += 1
                    break
    return n


# ---------------------------------------------------------------- a comparison candidate when the sources support one
def ensure_comparison(report: Report, documents: list[dict], targets: list[str], access_points: int | None = None) -> bool:
    """A provisional report with a primary but no comparison gets the best-supported other method from the retrieved
    application pages, with the passage that names it and its Table 1 limitation."""
    from app.knowledge import table1 as T1
    from app.knowledge.optics import METHODS
    from app.knowledge.page_tags import application_of, quote_methods
    from app.schemas import Citation, Recommendation
    from app.services.passages import _pieces

    if report.decisionStatus != "provisional" or any(r.role == "comparison" for r in report.recommendations):
        return False
    if any(c.status == "fail" for c in report.premiseChecks):
        return False  # a failed premise blocks the method choice; a comparison would read as a recommendation
    primary = {m for r in report.recommendations if r.role == "primary" for m in r.methodIds}
    if not primary:
        return False
    if access_points is not None and access_points <= len(primary):
        return False  # no free access point for a second probe; the access-point check governs sequential testing
    rejected = {m for r in report.recommendations if r.role == "not_recommended" for m in r.methodIds}
    target_words = {w for t in targets for w in re.findall(r"[a-z]{4,}", t.lower())}
    best = None
    for d in documents:
        if d.get("kind") == "table" or not application_of(d["source"], str(d["page"])):
            continue
        for p in _pieces(d["text"]):
            if len(p.split()) < 8 or not re.search(r"[a-z]{4,}.*[.!?]$", p.strip()):
                continue  # only a full sentence can be quoted as evidence
            for m in quote_methods(p) - primary - rejected:
                if m not in METHODS:
                    continue
                score = len(target_words & set(re.findall(r"[a-z]{4,}", p.lower()))) + 1
                if best is None or score > best[0]:
                    best = (score, m, d, p)
    if best is None:
        return False
    _, m, d, p = best
    cost = T1.probe_cost(m)
    cite = Citation(source=d["source"], page=str(d["page"]), quote=p, check="verified")
    report.recommendations.append(Recommendation(
        method=METHODS[m].label, methodIds=[m], role="comparison",
        reason=f"The supplied material discusses {METHODS[m].label} for this kind of application: “{p}”",
        citations=[cite],
        limitations=[f"Table 1 rates its probe cost as {cost}." if cost else "Not rated in Table 1.",
                     "Its interferences for this sample have to be checked in the same first experiment as the primary method."],
    ))
    report.sources.append(cite)
    return True
