"""Deterministic validators run on every composed report (generic: facts and AFS sources only).

- claim validator: every recommendation sentence needs a verified page citation whose passage supports it;
  unsupported sentences, and recommendations without any verified citation, move to the assumptions
- transfer labels: a cited passage that shows the setup for another application than the customer's is a
  "transfer assumption"
- method ranges: a nominal method range in the spectral-range text gets the page that states it
- required sections: requirements with quotes, key unknowns, recommendation with citations (or a decision
  status that says why there is none), measurement concept, spectral range, risks, assumptions,
  feasibility plan, decision status
"""

import re

from app.knowledge.applications import context, of_citation
from app.knowledge.optics import METHODS
from app.schemas import Report
from app.services.numbers import numbers_in

VALID = ("verified", "visual_note")
_STOP = set(
    "about also and are as at be been being but by can could does each for from has have how into is it its may more most must "
    "not of on or only other over should such than that the their them then there these they this those through to under use used "
    "uses using very was were what when where which while who will with within would your customer client process measurement".split()
    # domain words in nearly every sentence: they show the topic, not that the passage supports the claim
    + "probe probes measure measures measured measuring method methods signal signals spectra spectrum spectral spectroscopy "
      "sample samples inline in-line fiber fibre fibers fibres light analysis analyser analyzer data model models based provide "
      "provides allow allows suitable candidate candidates option options".split()
)


def _words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z][a-z\-]{3,}", text.lower()) if w not in _STOP}


def sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+(?=[A-Z(])", text or "") if s.strip()]


def supported(sentence: str, passage: str) -> bool:
    """The cited passage covers the sentence's distinctive words: 3+ of them and 30 %, or 2+ and half."""
    sw, pw = _words(sentence), _words(passage)
    if not sw:
        return True  # nothing to support ("See the cited page.")
    hit = len(sw & pw)
    return (hit >= 3 and hit / len(sw) >= 0.3) or (hit >= 2 and hit / len(sw) >= 0.5)


def passages(cites) -> str:
    return " ".join(f"{c.quote or ''} {context(c.source, c.page, c.quote)}" for c in cites if c.check in VALID and c.source != "EXT")


def validate_claims(report: Report) -> dict:
    """Move unsupported recommendation sentences (and uncited recommendations) to the assumptions."""
    moved, removed, kept = 0, 0, []
    for r in report.recommendations:
        if r.role == "not_recommended":
            kept.append(r)
            continue
        support = passages(r.citations)
        if not support:
            report.assumptions.append(f"{r.method} ({r.role.replace('_', ' ')} candidate, no verified page citation): {r.reason}")
            removed += 1
            continue
        ok = [s for s in sentences(r.reason) if supported(s, support)]
        for s in sentences(r.reason):
            if s not in ok:
                report.assumptions.append(f"{r.method}: {s} (not supported by the cited page)")
                moved += 1
        if not ok:
            removed += 1
            continue
        r.reason = " ".join(ok)
        kept.append(r)
    report.recommendations = kept
    return {"sentences_moved": moved, "recommendations_moved": removed}


_LATER_STAGE = re.compile(r"\b(animal|human|clinical|patient|in-vivo|in vivo|first-in-human)\s+(pilot\s+)?(stud(y|ies)|trials?|tests?|testing|evaluation)\b"
                          r"|\bclinical trial|\bpilot (in-vivo |in vivo )?(human|clinical|patient|in-vivo|in vivo)|\bregulatory (submission|approval)"
                          r"|\b(during|in) (live |real )?(surgery|surgeries|operations)\b", re.I)
_DASHES = str.maketrans({c: "-" for c in "\u2010\u2011\u2012\u2013\u2014"})
_NUMBERED = re.compile(r"^\s*(?:step\s*)?\d+[.):]\s*", re.I)
_HELD_OUT = re.compile(r"held[- ]out|unseen|not used (to build|for (building|training|calibration))|independent (test|validation) set"
                       r"|external validation|(new|other|different) (patients|batches|lots|samples) (that|not)|not part of the (model|calibration)", re.I)
HELD_OUT_STEP = ("Validate the model on samples not used to build it (held-out samples, e.g. from other patients, batches or "
                 "days) before drawing any conclusion; a model built on few samples can fit them without generalising.")


def validate_feasibility(report: Report) -> int:
    """A feasibility study ends at a validated feasibility result: later-stage studies (animal, human, clinical trials,
    regulatory) move to the points to confirm, and validation on held-out samples is always part of the plan."""
    keep, moved = [], 0
    for s in report.feasibility.steps:
        s = _NUMBERED.sub("", s)  # the UI numbers the steps
        if _LATER_STAGE.search(s.translate(_DASHES)):
            report.pointsToConfirm.append(f"After a successful feasibility study, not part of it: {s}")
            moved += 1
        else:
            keep.append(s)
    if not any(_HELD_OUT.search(s.translate(_DASHES)) for s in keep):
        keep.append(HELD_OUT_STEP)
    report.feasibility.steps = keep
    return moved


def label_transfers(report: Report, domain: str | None) -> int:
    """Cited examples from another application are transfer assumptions, labelled on the citation and listed."""
    if not domain:
        return 0
    n = 0
    holders = [*report.recommendations, report.concept]
    for h in holders:
        for c in h.citations:
            if c.check not in VALID or c.source == "EXT":
                continue
            tags = of_citation(c.source, c.page, c.quote)
            if tags and domain not in tags:
                c.transfer, c.application = True, ", ".join(tags)
                note = (f"Transfer assumption: {c.source} p.{c.page} shows this for {c.application}, not for {domain}; "
                        "it has to be tested for this application.")
                if note not in report.assumptions:
                    report.assumptions.append(note)
                    n += 1
    return n


def cite_method_ranges(report: Report) -> None:
    """A nominal method range quoted in the spectral-range text is cited with the page that states it."""
    have = {(c.source, c.page) for c in report.spectralRange.citations}
    nums = numbers_in(report.spectralRange.summary)
    for m in METHODS.values():
        if m.cite and (m.cite.source, m.cite.page) not in have and len(numbers_in(m.range_label) & nums) >= 2:
            report.spectralRange.citations.append(m.cite.model_copy())
            have.add((m.cite.source, m.cite.page))


def missing_sections(report: Report) -> list[str]:
    missing = []
    if not report.requirements.stated:
        missing.append("requirements (stated facts with quotes)")
    if not report.requirements.unknowns and not report.pointsToConfirm and not any(q.status == "open" for q in report.questions):
        missing.append("key unknowns")
    cited = [r for r in report.recommendations if r.role != "not_recommended" and any(c.check in VALID for c in r.citations)]
    if report.decisionStatus == "provisional" and not cited:
        missing.append("recommendation with citations")
    if not report.concept.summary.strip():
        missing.append("measurement concept")
    if not report.spectralRange.summary.strip():
        missing.append("spectral range")
    if not report.risks:
        missing.append("risks")
    if not report.assumptions:
        missing.append("assumptions")
    if not report.feasibility.steps or not report.feasibility.decisionBasis.strip():
        missing.append("feasibility plan")
    return missing
