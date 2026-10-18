"""Acceptance properties for any multi-turn conversation (generic: no scenario IDs, no case wording).

Each check takes the conversation as a list of turns, where a turn is
    {"messages": [...], "answers": [...], "final": bool, "report": {...}, "reply": str}
and returns a list of violations (empty = pass).
"""

from __future__ import annotations

import re

from app.agents.nodes.common import client_text
from app.agents.nodes.responder import assistant_texts, cited_page_texts
from app.schemas import Report
from app.services.ledger import similar
from app.services.numbers import TOKEN, _needs_support, _unit, _value, allowed_numbers
from app.services.validators import VALID, passages, sentences, supported

REQUIRED = ["requirements", "key unknowns", "recommendation", "measurement concept", "spectral range", "risks", "assumptions",
            "feasibility plan", "decision status"]


def _open(report: dict) -> list[dict]:
    return [q for q in report.get("questions", []) if q.get("status", "open") == "open" and report.get("mode") != "final"]


def no_repeated_questions(turns: list[dict]) -> list[str]:
    """No question appears twice; answered or declined questions are never asked again."""
    out, asked, closed = [], [], []
    for i, t in enumerate(turns, 1):
        open_now = [q["text"] for q in _open(t["report"])]
        for j, q in enumerate(open_now):
            if any(similar(q, p) for p in open_now[:j]):
                out.append(f"turn {i}: asked twice in one report: {q}")
            if any(similar(q, c) for c in closed):
                out.append(f"turn {i}: re-asked after it was answered or declined: {q}")
        new = [q for q in open_now if not any(similar(q, a) for a in asked)]
        asked += new
        closed += [q["text"] for q in t["report"].get("questions", []) if q.get("status", "open") != "open"]
    return out


def follow_up_facts_used(turns: list[dict]) -> list[str]:
    """Every answer given in a turn appears among the stated facts of that turn's report."""
    out = []
    for i, t in enumerate(turns, 1):
        stated = " ".join(t["report"]["requirements"]["stated"])
        for a in t.get("answers") or []:
            if a.get("status") == "answered" and a.get("answer") and not similar(a["answer"], stated, 0.6):
                out.append(f"turn {i}: answer not used as a fact: {a['answer']}")
    return out


def final_has_no_questions(turns: list[dict]) -> list[str]:
    return [f"turn {i}: final request but {len(_open(t['report']))} open questions" for i, t in enumerate(turns, 1)
            if t.get("final") and (t["report"].get("mode") != "final" or _open(t["report"]))]


def numbers_traceable(turns: list[dict]) -> list[str]:
    """Every number the assistant wrote exists in the customer transcript or on a cited page."""
    out = []
    for i, t in enumerate(turns, 1):
        report = Report(**t["report"])
        allowed = allowed_numbers(client_text(t["messages"]), cited_page_texts(report))
        for text in assistant_texts(report, t.get("reply", "")):
            for m in TOKEN.finditer(text):
                vals = [v for g in (m.group(1), m.group(3)) if g and (v := _value(g)) is not None]
                unit = _unit(m.group(4))
                if _needs_support(m.group(1), vals, unit, bool(m.group(3))) and not allowed.ok(vals, unit):
                    out.append(f"turn {i}: untraceable number '{m.group(0)}' in: {text[:80]}")
    return out


def recommendations_cited(turns: list[dict]) -> list[str]:
    """Every recommendation sentence has a verified page citation that supports it."""
    out = []
    for i, t in enumerate(turns, 1):
        for r in Report(**t["report"]).recommendations:
            if r.role == "not_recommended":
                continue
            if not any(c.check in VALID for c in r.citations):
                out.append(f"turn {i}: {r.method} has no verified citation")
                continue
            support = passages(r.citations)
            out += [f"turn {i}: {r.method}: unsupported sentence: {s}" for s in sentences(r.reason) if not supported(s, support)]
    return out


def probes_within_access_points(turns: list[dict], access_points: int | None) -> list[str]:
    """Proposed parallel probes never exceed the stated access points (combined probe / sequential handled by the check)."""
    if access_points is None:
        return []
    out = []
    for i, t in enumerate(turns, 1):
        rep = t["report"]
        if not re.search(r"\bport|access|position|flange|nozzle", " ".join(rep["requirements"]["stated"]), re.I):
            continue  # the customer has not stated the access points yet in this turn
        methods = {m for r in rep["recommendations"] if r["role"] in ("primary", "comparison", "combination") for m in r.get("methodIds", [])}
        chk = next((c for c in rep.get("premiseChecks", []) if c["id"] == "access_points"), None)
        if len(methods) > access_points and not (chk and chk["status"] == "pass"):
            out.append(f"turn {i}: {len(methods)} probe methods for {access_points} access point(s) without a combined or sequential plan")
    return out


def qualified_target_limited(turns: list[dict], qualifier: str) -> list[str]:
    """A qualified target triggers a stated limitation when the method cannot measure the qualifier."""
    out = []
    for i, t in enumerate(turns, 1):
        rep = t["report"]
        if not [r for r in rep["recommendations"] if r["role"] != "not_recommended"]:
            continue
        chk = next((c for c in rep.get("premiseChecks", []) if c["id"] == "target_qualifier"), None)
        if not chk:
            out.append(f"turn {i}: no target-qualifier check for '{qualifier}'")
        elif chk["status"] == "flag" and not re.search(rf"\b{qualifier}\b", " ".join(rep["risks"] + rep["feasibility"]["steps"]), re.I):
            out.append(f"turn {i}: limitation for '{qualifier}' not carried into risks or the feasibility plan")
    return out


def missing_sections(report: dict) -> list[str]:
    r = Report(**report)
    present = {
        "requirements": bool(r.requirements.stated),
        "key unknowns": bool(r.requirements.unknowns or r.pointsToConfirm or any(q.status == "open" for q in r.questions)),
        "recommendation": bool([x for x in r.recommendations if x.role != "not_recommended" and any(c.check in VALID for c in x.citations)])
                          or r.decisionStatus != "provisional",
        "measurement concept": bool(r.concept.summary.strip()),
        "spectral range": bool(r.spectralRange.summary.strip()),
        "risks": bool(r.risks),
        "assumptions": bool(r.assumptions),
        "feasibility plan": bool(r.feasibility.steps and r.feasibility.decisionBasis.strip()),
        "decision status": r.decisionStatus in ("provisional", "insufficient", "out_of_scope"),
    }
    return [k for k in REQUIRED if not present[k]]


def all_sections_present(turns: list[dict]) -> list[str]:
    return [f"turn {i}: missing {', '.join(m)}" for i, t in enumerate(turns, 1) if (m := missing_sections(t["report"]))]


def run_all(turns: list[dict], access_points: int | None = None) -> dict[str, list[str]]:
    return {
        "no repeated questions": no_repeated_questions(turns),
        "follow-up facts used": follow_up_facts_used(turns),
        "final request has no question block": final_has_no_questions(turns),
        "numbers traceable": numbers_traceable(turns),
        "recommendation sentences cited": recommendations_cited(turns),
        "probes within access points": probes_within_access_points(turns, access_points),
        "required sections present": all_sections_present(turns),
    }
