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
    for u in report.requirements.decisive:
        asked = next((q for q in led if L.similar(u, q.text)), None)
        if final:
            risk = f"Decisive point not confirmed by the customer, assumed for now: {u}."
            if not any(L.similar(u, r) for r in report.risks):
                report.risks.append(risk)
            if not any(L.similar(u, s) for s in report.feasibility.steps):
                report.feasibility.steps.insert(0, f"Establish with the first laboratory samples: {u}.")
            stats["decisive_open"] += 1
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
        r.limitations = list(dict.fromkeys(lim))


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


def _phase(step: str) -> int | None:
    s = step.translate(_DASHES)
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
    phases, last = [], 1
    for s in steps:
        p = _phase(s) or last
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
        if note not in report.pointsToConfirm:
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
