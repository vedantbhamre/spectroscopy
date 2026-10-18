import logfire

from app.agents import prompts
from app.agents.nodes.common import client_text, client_turns, step, transcript
from app.agents.state import AgentState
from app.gateway import chat, parse_json
from app.services.ledger import wants_final


def planner_node(state: AgentState) -> dict:
    """Route the turn: assessment (full pipeline) or conversational (explain the last report only).

    Any turn with answers, new facts or a request for advice runs the full pipeline, so technical
    advice is always retrieved, checked and validated. Final-report mode: the customer asks for the
    answer without further questions (UI button, wording, or the safety gate's immediate_config flag).
    """
    trace = list(state.get("trace", []))
    has_report = bool(state.get("report"))
    latest = (client_turns(state["messages"]) or [""])[-1]
    final = bool(state.get("final_mode")) or wants_final(latest) or "immediate_config" in (state.get("gate_flags") or [])
    with step({"trace": trace}, "Plan the turn") as rec:
        intent, queries = "assessment", []
        try:
            res = chat(
                [{"role": "system", "content": prompts.PLANNER.replace("{has_report}", "yes" if has_report else "no")},
                 {"role": "user", "content": transcript(state["messages"])}],
                json_mode=True, temperature=0, feature="planner", max_tokens=300, tier="small",
            )
            data = parse_json(res.text)
            intent = data.get("intent", "assessment")
            queries = [q for q in data.get("queries", []) if isinstance(q, str) and q.strip()][:3]
        except Exception as e:  # noqa: BLE001 - planning is advisory; assess by default
            logfire.warning("planner failed: {err}", err=str(e))
            rec["status"] = "warn"
        if not has_report or final or state.get("answers"):
            intent = "assessment"  # nothing to talk about yet, or the turn carries facts / asks for the answer
        if not queries:
            queries = [client_text(state["messages"])[-500:]]
        rec["detail"] = f"{intent}" + (" · final report requested" if final else "") + (f" · {len(queries)} search queries" if intent == "assessment" else "")
    return {"intent": intent, "queries": queries, "final_mode": final, "trace": trace}
