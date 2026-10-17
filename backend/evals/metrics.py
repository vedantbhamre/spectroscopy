"""Metrics for one assessment.

LLM-judged (RAGAS-style, implemented here so no extra dependency is needed):
  faithfulness       share of the report's factual claims supported by the retrieved pages
  answer_relevancy   how well the report addresses the client's enquiry (judge-generated
                     questions compared with the enquiry)
  context_precision  rank-weighted share of retrieved pages that are relevant (average precision)
  context_recall     share of the reference answer's claims found in the retrieved pages
                     (only where an organiser reference exists: D01, D02)
  answer_correctness F1 of the report's key statements against the reference (D01, D02)

Deterministic (no LLM cost):
  citation_validity  share of citations whose quote was found on the cited page
  grounding          share of recommendations backed by at least one verified citation
  clarification      the report lists unknowns and asks clarification questions
  feasibility        the first experiment has at least two steps and a decision basis
  expectations       per-scenario checks from golden.json (status, premise checks, terms)

Scores are 0..1; None means "not applicable" (e.g. no reference, or nothing to cite).
"""

from __future__ import annotations

from evals.judge import Judge

MAX_DOC_CHARS = 1500
VALID = ("verified", "visual_note")


# ---------------------------------------------------------------- report helpers

def report_claim_text(report: dict) -> str:
    """The parts of a report that make factual claims (what faithfulness is measured on)."""
    rows = [f"- {r['method']} ({r['role']}): {r['reason']}" for r in report.get("recommendations", [])]
    rows.append(f"- Measurement concept: {report.get('concept', {}).get('summary', '')}")
    rows.append(f"- Spectral range: {report.get('spectralRange', {}).get('summary', '')}")
    rows += [f"- Risk: {r}" for r in report.get("risks", [])]
    return "\n".join(rows)


def report_text(report: dict) -> str:
    """Everything a reader sees, lower-cased, for term checks."""
    parts = [report.get("title", ""), report_claim_text(report)]
    parts += report.get("requirements", {}).get("stated", []) + report.get("requirements", {}).get("unknowns", [])
    parts += [q.get("text", "") for q in report.get("questions", [])]
    parts += report.get("feasibility", {}).get("steps", []) + [report.get("feasibility", {}).get("decisionBasis", "")]
    parts += [f"{c.get('label', '')} {c.get('detail', '')}" for c in report.get("premiseChecks", [])]
    return "\n".join(parts).lower()


def _citations(report: dict) -> list[dict]:
    cites = [c for r in report.get("recommendations", []) for c in r.get("citations", [])]
    cites += report.get("concept", {}).get("citations", []) + report.get("spectralRange", {}).get("citations", [])
    return cites


def _contexts(documents: list[dict]) -> str:
    rows = []
    for i, d in enumerate(documents, 1):
        label = d.get("label") or f"p.{d.get('page', '?')}"
        rows.append(f"[{i}] {d.get('source', '?')} {label}\n{d.get('text', '')[:MAX_DOC_CHARS]}")
    return "\n\n".join(rows)


# ---------------------------------------------------------------- deterministic

def citation_validity(report: dict) -> float | None:
    cites = _citations(report)
    if not cites:
        return None
    return sum(c.get("check") in VALID for c in cites) / len(cites)


def grounding(report: dict) -> float | None:
    recs = [r for r in report.get("recommendations", []) if r.get("role") != "not_recommended"]
    if not recs:
        return None
    return sum(any(c.get("check") in VALID for c in r.get("citations", [])) for r in recs) / len(recs)


def clarification(report: dict) -> float:
    has_unknowns = bool(report.get("requirements", {}).get("unknowns"))
    has_questions = bool(report.get("questions"))
    return (has_unknowns + has_questions) / 2


def feasibility(report: dict) -> float:
    f = report.get("feasibility", {})
    return (len(f.get("steps", [])) >= 2) * 0.5 + bool(f.get("decisionBasis", "").strip()) * 0.5


def expectations(report: dict, golden: dict) -> tuple[float | None, list[str]]:
    """Checks from golden.json. Returns (share passed, list of failures)."""
    checks: list[tuple[str, bool]] = []
    if allowed := golden.get("status_in"):
        checks.append((f"decision status in {allowed} (got {report.get('decisionStatus')})", report.get("decisionStatus") in allowed))
    flagged = {c["id"] for c in report.get("premiseChecks", []) if c.get("status") in ("flag", "fail")}
    for prefix in golden.get("premise_flagged", []):
        checks.append((f"premise check '{prefix}*' flagged or failed", any(i.startswith(prefix) for i in flagged)))
    text = report_text(report)
    for group in golden.get("must_mention_any", []):
        checks.append((f"mentions one of {group}", any(term.lower() in text for term in group)))
    if golden.get("min_questions"):
        checks.append((f"at least {golden['min_questions']} clarification questions", len(report.get("questions", [])) >= golden["min_questions"]))
    if not checks:
        return None, []
    return sum(ok for _, ok in checks) / len(checks), [name for name, ok in checks if not ok]


# ---------------------------------------------------------------- LLM-judged

def faithfulness(judge: Judge, report: dict, documents: list[dict]) -> tuple[float | None, list[dict]]:
    claims = report_claim_text(report)
    if not documents or not claims.strip():
        return None, []
    out = judge.ask(
        "You grade faithfulness for a retrieval-augmented assistant. Split the ANSWER into its atomic factual "
        "claims about methods, materials, ranges, fibres or applications (skip advice, questions and hedges such as "
        "'must be tested'). For each claim decide if the CONTEXT supports it. Return JSON: "
        '{"claims": [{"claim": str, "supported": true|false, "context": int|null}]} with at most 12 claims.',
        f"CONTEXT:\n{_contexts(documents)}\n\nANSWER:\n{claims}",
    )
    items = [c for c in out.get("claims", []) if isinstance(c, dict)]
    if not items:
        return None, []
    return sum(bool(c.get("supported")) for c in items) / len(items), items


def answer_relevancy(judge: Judge, enquiry: str, report: dict) -> float | None:
    out = judge.ask(
        "You grade answer relevancy. Read the ANSWER only and write the 3 questions a client most likely asked to get "
        "it. Then rate, for each, how closely it matches the ORIGINAL enquiry's intent from 0 (unrelated) to 1 "
        '(same request). Return JSON: {"questions": [str, str, str], "similarity": [float, float, float]}.',
        f"ORIGINAL ENQUIRY:\n{enquiry}\n\nANSWER:\n{report.get('title', '')}\n{report_claim_text(report)}\n"
        + "\n".join(f"Question asked: {q.get('text', '')}" for q in report.get("questions", [])),
    )
    sims = [float(s) for s in out.get("similarity", []) if isinstance(s, (int, float))]
    return round(sum(sims) / len(sims), 4) if sims else None


def context_precision(judge: Judge, enquiry: str, documents: list[dict]) -> float | None:
    if not documents:
        return None
    out = judge.ask(
        "You grade retrieval. For each numbered CONTEXT page decide whether it is useful for answering the client's "
        'ENQUIRY (methods, sample type, probe, fibre or application that apply). Return JSON: {"relevant": [true|false, ...]} '
        "with one entry per page, in order.",
        f"ENQUIRY:\n{enquiry}\n\nCONTEXT:\n{_contexts(documents)}",
    )
    rel = [bool(r) for r in out.get("relevant", [])][: len(documents)]
    return average_precision(rel)


def average_precision(relevant: list[bool]) -> float | None:
    """RAGAS context precision: mean of precision@k over the ranks k that are relevant."""
    if not relevant:
        return None
    hits, total = 0, 0.0
    for k, r in enumerate(relevant, 1):
        if r:
            hits += 1
            total += hits / k
    return total / hits if hits else 0.0


def context_recall(judge: Judge, reference: list[str], documents: list[dict]) -> float | None:
    if not reference or not documents:
        return None
    out = judge.ask(
        "You grade context recall. For each REFERENCE statement decide whether the CONTEXT contains the information "
        'needed to make it. Return JSON: {"attributed": [true|false, ...]} with one entry per statement, in order.',
        f"CONTEXT:\n{_contexts(documents)}\n\nREFERENCE STATEMENTS:\n" + "\n".join(f"{i}. {s}" for i, s in enumerate(reference, 1)),
    )
    att = [bool(a) for a in out.get("attributed", [])][: len(reference)]
    return sum(att) / len(reference) if att else None


def answer_correctness(judge: Judge, reference: list[str], report: dict) -> float | None:
    if not reference:
        return None
    out = judge.ask(
        "You compare an ANSWER with a REFERENCE answer written by experts. Count: tp = reference statements the answer "
        "also makes (same meaning, any wording); fn = reference statements the answer misses; fp = statements in the "
        'answer that contradict the reference. Return JSON: {"tp": int, "fp": int, "fn": int}.',
        f"REFERENCE:\n" + "\n".join(f"- {s}" for s in reference) + f"\n\nANSWER:\n{report_claim_text(report)}\n"
        + "\n".join(f"- Question: {q.get('text', '')}" for q in report.get("questions", []))
        + "\n" + "\n".join(f"- Step: {s}" for s in report.get("feasibility", {}).get("steps", [])),
    )
    tp, fp, fn = (int(out.get(k, 0) or 0) for k in ("tp", "fp", "fn"))
    return tp / (tp + 0.5 * (fp + fn)) if tp + fp + fn else None
