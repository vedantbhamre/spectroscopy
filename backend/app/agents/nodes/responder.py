import json
import re
from datetime import datetime, timezone

from pydantic import ValidationError

from app.agents import prompts
from app.agents.nodes.common import client_text, client_turns, step, transcript
from app.agents.state import AgentState
from app.gateway import chat, parse_json
from app.knowledge import table1 as T1
from app.schemas import Citation, DirectAnswer, PremiseCheck, Question, Report
from app.services import ledger as L
from app.services import review_rules as RR
from app.services import validators as V
from app.services.citations import page_text, verify
from app.services.numbers import allowed_numbers, scrub
from app.services.passages import number, resolve, strip_refs
from app.services.premises import (Facts, access_check, apply_floor, combination_check, combined_probe_applies, cost_check,
                                   geometry_check, mir_link_check, owned_equipment_check, target_qualifier_check)

KNOWN_METHODS = {"NIR", "MIR_ATR", "RAMAN", "FLUO", "UVVIS"}
VALID = V.VALID


def _excerpts(docs: list[dict]) -> str:
    return number(docs)[0]


def _page_for(c: dict) -> str:
    page = str(c.get("page", "")).replace("p.", "").strip()
    return "Table 1 (p.6)" if "table" in page.lower() else page


def assistant_texts(report: Report, reply: str = "") -> list[str]:
    """Everything the model wrote (premise checks and verified quotes are computed, not written)."""
    c = report.concept
    a = report.answer
    out = [reply, a.text if a else "", (a.sayInstead or "") if a else "", *(x for r in report.recommendations for x in (r.method, r.reason)), c.summary, c.probe or "", c.location or "",
           c.fiberLink or "", c.analyzer or "", report.spectralRange.summary, *report.risks, *report.feasibility.steps,
           report.feasibility.decisionBasis, *report.assumptions, *report.pointsToConfirm, *report.requirements.unknowns,
           *(q.text for q in report.questions if q.status == "open")]
    return [x for x in out if x]


def _validate_numbers(report: Report, reply: str, *, customer: str, cited_pages: list[str]) -> tuple[str, int]:
    """Every number must appear in the customer transcript or on a cited page; otherwise a placeholder."""
    allowed = allowed_numbers(customer, cited_pages)
    total = 0

    def fix(s: str | None) -> str | None:
        nonlocal total
        if not s:
            return s
        out, n = scrub(s, allowed)
        total += n
        return out

    for r in report.recommendations:
        r.method, r.reason = fix(r.method), fix(r.reason)
    c = report.concept
    c.summary, c.probe, c.location, c.fiberLink, c.analyzer = (fix(x) for x in (c.summary, c.probe, c.location, c.fiberLink, c.analyzer))
    report.spectralRange.summary = fix(report.spectralRange.summary)
    report.risks = [fix(r) for r in report.risks]
    report.feasibility.steps = [fix(s) for s in report.feasibility.steps]
    report.feasibility.decisionBasis = fix(report.feasibility.decisionBasis)
    report.assumptions = [fix(a) for a in report.assumptions]
    report.pointsToConfirm = [fix(p) for p in report.pointsToConfirm]
    report.requirements.unknowns = [fix(u) for u in report.requirements.unknowns]
    for q in report.questions:
        if q.status == "open":
            q.text = fix(q.text)
    if report.answer:
        report.answer.text = fix(report.answer.text) or ""
        report.answer.sayInstead = fix(report.answer.sayInstead)
    return fix(reply) or "", total


_CLAIM = re.compile(r"\b(quote|cite|claim|proof|prove|promise|guarantee|advertis\w*|marketing|tell (our|the|their) (customers?|clients?))\b", re.I)
_NEGATIVE = re.compile(r"\b(no|not|cannot|can't|isn't|aren't|unlikely|insufficient|only after|not yet)\b", re.I)


def ensure_answer(report: Report) -> bool:
    """The report opens with an answer to the customer's question. When a premise check fails, the answer must say
    what it rules out; a missing or contradicting answer is replaced by one built from the failed checks.
    Returns True when the answer was written here."""
    failed = [c for c in report.premiseChecks if c.status == "fail"]
    a = report.answer
    if a and a.text.strip() and (not failed or _NEGATIVE.search(a.text)):
        if failed and not a.citations:
            a.citations = [c for chk in failed for c in chk.citations][:3]
        return False
    if failed:
        text = "Not as asked. " + " ".join(f"{c.label}: no. {c.detail.split('. ')[0].rstrip('.')}." for c in failed)
        cites = [c for chk in failed for c in chk.citations][:3]
    else:
        text = {"insufficient": "Not decidable yet: the open questions below decide it.",
                "out_of_scope": "Not from the supplied sources."}.get(report.decisionStatus,
                "Provisionally yes, as a feasibility candidate; the first experiment below decides it.")
        cites = []
    report.answer = DirectAnswer(text=text, sayInstead=a.sayInstead if a else None, citations=cites)
    return True


def _strip_refs(report: Report) -> None:
    """Passage numbers belong in citations; the model sometimes also writes them into the prose."""
    for r in report.recommendations:
        r.reason = strip_refs(r.reason) or ""
    c = report.concept
    c.summary = strip_refs(c.summary) or ""
    report.spectralRange.summary = strip_refs(report.spectralRange.summary) or ""
    if report.answer:
        report.answer.text = strip_refs(report.answer.text) or ""
        report.answer.sayInstead = strip_refs(report.answer.sayInstead)
    for key in ("risks", "assumptions", "pointsToConfirm"):
        setattr(report, key, [strip_refs(x) or "" for x in getattr(report, key)])
    report.feasibility.steps = [strip_refs(x) or "" for x in report.feasibility.steps]
    report.feasibility.decisionBasis = strip_refs(report.feasibility.decisionBasis) or ""


def cited_page_texts(report: Report) -> list[str]:
    return [page_text(c.source, c.page) for c in report.sources if c.source != "EXT"]


def finalise(raw: dict, *, checks: list[PremiseCheck], scenario_id: str | None, facts: Facts | None = None,
             ledger: list[Question] | None = None, messages: list[dict] | None = None, documents: list[dict] | None = None,
             final: bool = False) -> tuple[Report, dict, str]:
    """Deterministic post-processing of the composed report. Returns (report, stats, reply).

    Order: verified facts with turns → question ledger → citations verified (method ranges cited) → transfer
    labels → claim validator → checks that depend on the recommendation → number validator → status floor
    → required sections.
    """
    messages = messages or []
    facts = facts or Facts()
    turn = max(len(client_turns(messages)), 1)
    data = {k: v for k, v in raw.items() if k != "reply"}
    proposed = [q for q in (data.get("questions") or []) if isinstance(q, dict)]
    data["questions"] = []
    for section in (data.get("recommendations") or []):
        section["methodIds"] = [m for m in section.get("methodIds", []) if m in KNOWN_METHODS]
    if isinstance(data.get("answer"), str):
        data["answer"] = {"text": data["answer"]}
    if not isinstance(data.get("answer"), dict) or not str(data["answer"].get("text") or "").strip():
        data.pop("answer", None)
    refs = number(documents or [])[1]
    unknown_refs = 0
    for holder in [*(data.get("recommendations") or []), data.get("concept") or {}, data.get("spectralRange") or {}, data.get("answer") or {}]:
        cites = []
        for c in holder.get("citations", []):
            if isinstance(c, str):  # a bare reference: "S01.14.3"
                c = {"ref": c}
            if not isinstance(c, dict):
                continue
            r = resolve(c, refs)
            if r is None:
                unknown_refs += 1
            elif r.get("source"):
                cites.append({**r, "page": _page_for(r)})
        holder["citations"] = cites
    for key in ("assumptions", "pointsToConfirm", "risks"):
        data[key] = [str(x) for x in (data.get(key) or []) if str(x).strip()]
    data.update(premiseChecks=[c.model_dump() for c in checks], sources=[], scenarioId=scenario_id, origin="live",
                mode="final" if final else "draft", generatedAt=datetime.now(timezone.utc).isoformat(timespec="seconds"))
    report = Report.model_validate(data)
    _strip_refs(report)
    stats: dict = {"verified": 0, "visual_note": 0, "failed": 0, "unverified": 0, "numbers": 0, "questions": {}, "unknown_refs": unknown_refs}

    # Stated facts: the analyst's quote-verified facts with their turn, not the composer's paraphrase.
    if facts.stated:
        report.requirements.stated = facts.stated
        report.requirements.factTurns = facts.stated_turns

    # Question ledger: every earlier question keeps its status; only new customer-fact questions are added.
    led, stats["questions"] = L.merge_new(ledger or [], proposed, turn, final)
    led, report.feasibility.steps = L.move_unknowns(led, report.feasibility.steps, report.risks)
    settled = [q for q in led if q.status in ("answered", "declined")]
    report.requirements.unknowns = [u for u in report.requirements.unknowns if not any(L.similar(u, q.text) for q in settled)]
    for q in led:  # what the customer could not say stays a key unknown (the experiment establishes it)
        if q.status == "moved_to_experiment" and not any(L.similar(q.text, u) for u in report.requirements.unknowns):
            report.requirements.unknowns.append(f"Not known yet (to be established in the first experiment): {q.text.rstrip('?')}")
    if final:
        for q in led:
            if q.status == "open" and not any(L.similar(q.text, p) for p in report.pointsToConfirm):
                report.pointsToConfirm.append(q.text)
    report.questions = led

    # Citations: verified on their page; the nominal range of a method in the spectral range is cited.
    V.cite_method_ranges(report)

    def check_all(cites: list[Citation]) -> list[Citation]:
        out = []
        for c in cites:
            v = verify(c)
            stats[v.check] += 1
            out.append(v)
        return out

    for rec in report.recommendations:
        rec.citations = check_all(rec.citations)
    report.concept.citations = check_all(report.concept.citations)
    report.spectralRange.citations = check_all(report.spectralRange.citations)
    if report.answer:
        report.answer.citations = check_all(report.answer.citations)

    stats["transfers"] = V.label_transfers(report, facts.application_domain)
    stats.update(V.validate_claims(report))

    # Checks that depend on the composed recommendation and concept.
    dumped = report.model_dump()
    support = {m: V.passages(r.citations) for r in report.recommendations for m in r.methodIds}
    ids = {c.id for c in report.premiseChecks}
    extra = [access_check(facts, dumped), target_qualifier_check(facts, dumped, support), owned_equipment_check(facts, dumped),
             geometry_check(facts, dumped), cost_check(dumped), mir_link_check(facts, dumped)]
    if "combination" not in ids and any(r.role == "combination" for r in report.recommendations):
        extra.append(combination_check(facts))
    report.premiseChecks += [c for c in extra if c is not None]
    if any(c.id == "target_qualifier" and c.status == "flag" for c in report.premiseChecks):
        qts = ", ".join(q["target"] for q in facts.qualified_targets)
        if not any("reference" in s.lower() and any(q["qualifier"] in s.lower() for q in facts.qualified_targets) for s in report.feasibility.steps):
            report.feasibility.steps.append(f"Measure {qts} with an independent reference method that distinguishes it, and test whether the spectral signal follows it rather than the total.")
        report.risks.append(f"The proposed signal may follow a related quantity rather than {qts}.")

    if any(c.id == "mir_link_length" for c in report.premiseChecks):
        if not any(re.search(r"transmission|loss", s, re.I) and re.search(r"length|distance|link", s, re.I) for s in report.feasibility.steps):
            report.feasibility.steps.insert(0, "Measure the transmission of the chosen mid-IR fibre over the planned link length, or plan the analyzer close to the measurement point.")
        report.risks.append("The mid-IR fibre link over the required distance is not shown to be feasible in the supplied material.")

    stats["later_stage_moved"] = V.validate_feasibility(report)
    stats["hardware_moved"] = RR.validate_hardware(report)
    stats["excitation_fixed"] = RR.fix_excitation(report)
    RR.order_plan(report, medical=facts.application_domain == "medical and tissue" or facts.use_context == "clinical")
    RR.add_limitations(report, report.premiseChecks)
    stats.update(RR.enforce_decisive(report, facts.decisive_unknowns, final, turn))

    seen: dict[tuple, Citation] = {}
    for c in [*(report.answer.citations if report.answer else []), *(c for r in report.recommendations for c in r.citations), *report.concept.citations, *report.spectralRange.citations]:
        seen.setdefault((c.source, c.page, c.quote), c)
    for chk in report.premiseChecks:
        for c in chk.citations:
            seen.setdefault((c.source, c.page, c.quote), verify(c) if c.quote else c)
    report.sources = list(seen.values())

    reply, stats["numbers"] = _validate_numbers(report, strip_refs(str(raw.get("reply") or "")) or "", customer=client_text(messages),
                                                cited_pages=cited_page_texts(report))

    # Final mode: provisional unless the checks justify otherwise. Otherwise the checks set the floor.
    report.decisionStatus = apply_floor("provisional" if final else report.decisionStatus, report.premiseChecks)
    stats["answer_written"] = ensure_answer(report)
    stats["certainty_rejected"] = RR.reject_certainty(report)
    if report.answer and not (facts.cites_study_as_proof or _CLAIM.search(client_text(messages))):
        report.answer.sayInstead = None  # only when the customer wants to quote, claim or promise something
    stats["missing"] = V.missing_sections(report)
    return report, stats, reply


def responder_node(state: AgentState) -> dict:
    trace = list(state.get("trace", []))
    checks = [PremiseCheck(**c) for c in state.get("checks", [])]
    facts = Facts(**state.get("facts", {}))
    ledger = [Question(**q) for q in state.get("ledger") or []]
    final = bool(state.get("final_mode"))
    open_n = sum(q.status == "open" for q in ledger)
    context = {
        "facts": facts.model_dump(include={"stated", "unknowns", "target_variables", "qualified_targets", "methods_mentioned", "access_points",
                                           "owned_equipment", "optical_appearance", "application_domain"}),
        "premise_checks": [{"label": c.label, "status": c.status, "detail": c.detail} for c in checks],
    }
    notes = []
    if facts.access_points is not None:
        combined = ("a combined NIR–Raman probe in one shaft (S01 p.15, shown for this kind of application)" if combined_probe_applies(facts)
                    else "measuring the methods one after the other on the same samples, or an offline rig (the sources show a combined probe only for another application)")
        notes.append(f"ACCESS POINTS: the customer has {facts.access_points} free access point(s). The concept must fit them: one probe per port, or {combined}.")
    if facts.owned_equipment:
        notes.append("OWNED EQUIPMENT: " + "; ".join(f"{o['name']} ({o.get('method') or 'method not named'})" for o in facts.owned_equipment)
                     + ". State what the sources say it can and cannot measure and use it in the feasibility plan where supported, before proposing purchases.")
    notes.append('[S01 Table 1 (p.6)] techniques, sample types and cost (prefer the simplest, cheapest sufficient method). '
                 'Cite a row as {"source": "S01", "page": "Table 1 (p.6)", "quote": "<the row>"}:\n' + T1.for_prompt())
    system = prompts.RESPONDER.replace("{mode}", "final" if final else "draft").replace("{max_new}", str(min(5, max(L.MAX_OPEN - open_n, 0))))
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": (
            f"CONVERSATION:\n{transcript(state['messages'])}\n\n"
            f"QUESTION LEDGER:\n{json.dumps(L.ledger_for_prompt(ledger), ensure_ascii=False)}\n\nMODE: {'final' if final else 'draft'}\n\n"
            + "\n\n".join(notes) + "\n\n"
            f"EXTRACTED FACTS AND PREMISE CHECKS:\n{json.dumps(context, ensure_ascii=False, indent=1)}\n\n"
            f"EXCERPTS:\n{_excerpts(state.get('documents', []))}"
        )},
    ]
    kw = dict(checks=checks, scenario_id=state.get("scenario_id"), facts=facts, ledger=ledger, messages=state["messages"],
              documents=state.get("documents", []), final=final)
    repaired = []
    with step({"trace": trace}, "Compose the assessment") as rec:
        res = chat(messages, json_mode=True, temperature=0.1, feature="responder", max_tokens=4096)
        raw = parse_json(res.text)
        try:
            report, stats, reply = finalise(raw, **kw)
            problem = f"These required sections are missing or empty: {', '.join(stats['missing'])}." if stats["missing"] else None
            if problem and "recommendation with citations" in stats["missing"]:
                problem += (" Each recommendation needs at least one citation by passage number from EXCERPTS ({\"ref\": \"S01.14.3\"})"
                            " or a Table 1 row, and its reason may only say what those passages say."
                            + (f" {stats['unknown_refs']} cited numbers do not exist in EXCERPTS." if stats.get("unknown_refs") else ""))
        except ValidationError as e:
            report, stats, reply, problem = None, None, "", str(e)[:1500]
        if problem:  # reject and repair once; if the repair is unusable, keep the first report (when it was valid)
            repaired.append(problem)
            rec["status"] = "warn"
            try:
                fix = chat(messages + [{"role": "assistant", "content": res.text},
                                       {"role": "user", "content": prompts.REPAIR.replace("{errors}", problem)}],
                           json_mode=True, temperature=0, feature="repair", max_tokens=4096)
                fixed = finalise(parse_json(fix.text), **kw)
                if report is None or len(fixed[1]["missing"]) <= len(stats["missing"]):
                    report, stats, reply = fixed
            except Exception:  # noqa: BLE001
                if report is None:
                    raise
        rec["detail"] = f"{res.model} via {res.via}" + (" · final report" if final else "") + (" · repaired once" if repaired else "")

    with step({"trace": trace}, "Verify citations") as rec:
        total = stats["verified"] + stats["visual_note"] + stats["failed"] + stats["unverified"]
        found = stats["verified"] + stats["visual_note"]
        rec["detail"] = f"{found} of {total} quotes found on the cited page" + (f" · {stats['failed']} not found" if stats["failed"] else "")
        rec["status"] = "warn" if stats["failed"] else "ok"

    with step({"trace": trace}, "Validate numbers, claims and questions") as rec:
        q = stats["questions"]
        parts = [f"{stats['numbers']} unsupported numbers replaced" if stats["numbers"] else "all numbers traced to the customer or a cited page",
                 f"{stats['sentences_moved']} unsupported sentences and {stats['recommendations_moved']} uncited recommendations moved to assumptions"
                 if stats["sentences_moved"] or stats["recommendations_moved"] else "every recommendation sentence cited",
                 f"{stats['transfers']} transfer assumptions labelled" if stats["transfers"] else None,
                 f"{q.get('repeated', 0)} repeated questions dropped" if q.get("repeated") else None,
                 f"{q.get('assistant_decision', 0)} questions about methods, equipment or purchases dropped" if q.get("assistant_decision") else None,
                 f"{sum(x.status == 'open' for x in report.questions)} open questions" if not final else "final report: no questions",
                 f"missing sections: {', '.join(stats['missing'])}" if stats["missing"] else "all required sections present"]
        rec["detail"] = " · ".join(p for p in parts if p)
        rec["status"] = "warn" if stats["numbers"] or stats["sentences_moved"] or stats["recommendations_moved"] or stats["missing"] else "ok"

    reply = reply or "The first assessment is ready for review."
    validation = {"numbers_replaced": stats["numbers"], "missing_sections": stats["missing"], "repaired": bool(repaired),
                  "sentences_moved": stats["sentences_moved"], "recommendations_moved": stats["recommendations_moved"],
                  "questions": stats["questions"], "transfers": stats["transfers"],
                  "certainty_rejected": stats.get("certainty_rejected", 0), "method_mismatch": stats.get("method_mismatch", 0),
                  "recited": stats.get("recited", 0), "decisive_open": stats.get("decisive_open", 0),
                  "hardware_moved": stats.get("hardware_moved", 0), "excitation_fixed": stats.get("excitation_fixed", 0),
                  "citations": {k: stats[k] for k in ("verified", "visual_note", "failed", "unverified")}}
    return {"report": report.model_dump(), "reply": reply, "ledger": [x.model_dump() for x in report.questions], "trace": trace,
            "validation": validation}


def conversational_node(state: AgentState) -> dict:
    """Explains the existing report only; its numbers are validated against the report and the customer's words."""
    trace = list(state.get("trace", []))
    report_json = json.dumps(state.get("report"), ensure_ascii=False)
    with step({"trace": trace}, "Explain the previous report") as rec:
        res = chat(
            [{"role": "system", "content": prompts.CONVERSATIONAL.replace("{report}", report_json[:12000])},
             {"role": "user", "content": transcript(state["messages"])}],
            temperature=0.2, feature="conversational", max_tokens=500,
        )
        reply, n = scrub(res.text.strip(), allowed_numbers(client_text(state["messages"]), [report_json]))
        rec["detail"] = f"{res.model} via {res.via}" + (f" · {n} numbers not in the report replaced" if n else "")
        if n:
            rec["status"] = "warn"
    return {"reply": reply, "trace": trace}
