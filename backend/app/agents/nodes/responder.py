import json
from datetime import datetime, timezone

from pydantic import ValidationError

from app.agents import prompts
from app.agents.nodes.common import step, transcript
from app.agents.state import AgentState
from app.gateway import chat, parse_json
from app.schemas import Citation, PremiseCheck, Report
from app.services.citations import verify
from app.services.premises import apply_floor

KNOWN_METHODS = {"NIR", "MIR_ATR", "RAMAN", "FLUO", "UVVIS"}


def _excerpts(docs: list[dict]) -> str:
    rows = []
    for d in docs:
        label = d.get("label") or f"p.{d['page']}"
        kind = " (team transcription of a slide image)" if d["kind"] == "visual_note" else ""
        rows.append(f"[{d['source']} {label}{kind}]\n{d['text']}")
    return "\n\n".join(rows)


def _page_for(c: dict) -> str:
    page = str(c.get("page", "")).replace("p.", "").strip()
    return "Table 1 (p.6)" if "table" in page.lower() else page


def finalise(raw: dict, *, checks: list[PremiseCheck], scenario_id: str | None) -> tuple[Report, dict]:
    """Deterministic post-processing: computed checks, status floor, verified citations, known methods."""
    data = {k: v for k, v in raw.items() if k != "reply"}
    for section in (data.get("recommendations") or []):
        section["methodIds"] = [m for m in section.get("methodIds", []) if m in KNOWN_METHODS]
    for holder in [*(data.get("recommendations") or []), data.get("concept") or {}, data.get("spectralRange") or {}]:
        holder["citations"] = [{**c, "page": _page_for(c)} for c in holder.get("citations", []) if isinstance(c, dict) and c.get("source")]
    data.update(premiseChecks=[c.model_dump() for c in checks], sources=[], scenarioId=scenario_id, origin="live",
                generatedAt=datetime.now(timezone.utc).isoformat(timespec="seconds"))
    report = Report.model_validate(data)

    stats = {"verified": 0, "visual_note": 0, "failed": 0, "unverified": 0}
    seen: dict[tuple, Citation] = {}

    def check_all(cites: list[Citation]) -> list[Citation]:
        out = []
        for c in cites:
            v = verify(c)
            stats[v.check] += 1
            seen.setdefault((v.source, v.page, v.quote), v)
            out.append(v)
        return out

    for rec in report.recommendations:
        rec.citations = check_all(rec.citations)
    report.concept.citations = check_all(report.concept.citations)
    report.spectralRange.citations = check_all(report.spectralRange.citations)
    for chk in report.premiseChecks:
        for c in chk.citations:
            seen.setdefault((c.source, c.page, c.quote), verify(c))
    report.sources = list(seen.values())
    report.decisionStatus = apply_floor(report.decisionStatus, report.premiseChecks)
    return report, stats


def responder_node(state: AgentState) -> dict:
    trace = list(state.get("trace", []))
    checks = [PremiseCheck(**c) for c in state.get("checks", [])]
    context = {
        "facts": state.get("facts", {}),
        "premise_checks": [{"label": c.label, "status": c.status, "detail": c.detail} for c in checks],
    }
    messages = [
        {"role": "system", "content": prompts.RESPONDER},
        {"role": "user", "content": (
            f"CONVERSATION:\n{transcript(state['messages'])}\n\n"
            f"EXTRACTED FACTS AND PREMISE CHECKS:\n{json.dumps(context, ensure_ascii=False, indent=1)}\n\n"
            f"EXCERPTS:\n{_excerpts(state.get('documents', []))}"
        )},
    ]
    with step({"trace": trace}, "Compose the assessment") as rec:
        res = chat(messages, json_mode=True, temperature=0.1, feature="responder", max_tokens=4096)
        raw = parse_json(res.text)
        try:
            report, stats = finalise(raw, checks=checks, scenario_id=state.get("scenario_id"))
        except ValidationError as e:
            rec["status"] = "warn"
            fix = chat(messages + [{"role": "assistant", "content": res.text},
                                   {"role": "user", "content": prompts.REPAIR.replace("{errors}", str(e)[:1500])}],
                       json_mode=True, temperature=0, feature="repair", max_tokens=4096)
            raw = parse_json(fix.text)
            report, stats = finalise(raw, checks=checks, scenario_id=state.get("scenario_id"))
        rec["detail"] = f"{res.model} via {res.via}" + (" · repaired" if rec["status"] == "warn" else "")

    with step({"trace": trace}, "Verify citations") as rec:
        total = sum(stats.values())
        found = stats["verified"] + stats["visual_note"]
        rec["detail"] = f"{found} of {total} quotes found on the cited page" + (f" · {stats['failed']} not found" if stats["failed"] else "")
        rec["status"] = "warn" if stats["failed"] else "ok"

    reply = str(raw.get("reply") or "The first assessment is ready for review.")
    return {"report": report.model_dump(), "reply": reply, "trace": trace}


def conversational_node(state: AgentState) -> dict:
    trace = list(state.get("trace", []))
    with step({"trace": trace}, "Answer from the previous report") as rec:
        res = chat(
            [{"role": "system", "content": prompts.CONVERSATIONAL.replace("{report}", json.dumps(state.get("report"), ensure_ascii=False)[:12000])},
             {"role": "user", "content": transcript(state["messages"])}],
            temperature=0.2, feature="conversational", max_tokens=500,
        )
        rec["detail"] = f"{res.model} via {res.via}"
    return {"reply": res.text.strip(), "trace": trace}
