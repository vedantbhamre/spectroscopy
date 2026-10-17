import logfire

from app.agents import prompts
from app.agents.nodes.common import client_text, step, transcript
from app.agents.state import AgentState
from app.gateway import chat, parse_json


def planner_node(state: AgentState) -> dict:
    """Intent classification: new/updated assessment vs. conversational turn about the last report."""
    trace = list(state.get("trace", []))
    has_report = bool(state.get("report"))
    with step({"trace": trace}, "Plan the turn") as rec:
        intent, queries = "assessment", []
        try:
            res = chat(
                [{"role": "system", "content": prompts.PLANNER.replace("{has_report}", "yes" if has_report else "no")},
                 {"role": "user", "content": transcript(state["messages"])}],
                json_mode=True, temperature=0, feature="planner", max_tokens=300,
            )
            data = parse_json(res.text)
            intent = data.get("intent", "assessment")
            queries = [q for q in data.get("queries", []) if isinstance(q, str) and q.strip()][:3]
        except Exception as e:  # noqa: BLE001 - planning is advisory; assess by default
            logfire.warning("planner failed: {err}", err=str(e))
            rec["status"] = "warn"
        if not has_report:
            intent = "assessment"  # nothing to talk about yet
        if not queries:
            queries = [client_text(state["messages"])[-500:]]
        rec["detail"] = f"{intent}" + (f" · {len(queries)} search queries" if intent == "assessment" else "")
    return {"intent": intent, "queries": queries, "trace": trace}
