from app.agents import prompts
from app.agents.nodes.common import client_text, step, transcript
from app.agents.state import AgentState
from app.gateway import chat, parse_json
from app.services.citations import normalise
from app.services.premises import Facts, detect


def analyst_node(state: AgentState) -> dict:
    """Separate stated facts from unknowns. A fact is kept only if its quote is the client's own words."""
    trace = list(state.get("trace", []))
    said = client_text(state["messages"])
    with step({"trace": trace}, "Separate facts and unknowns") as rec:
        res = chat(
            [{"role": "system", "content": prompts.ANALYST}, {"role": "user", "content": transcript(state["messages"])}],
            json_mode=True, temperature=0, feature="analyst", max_tokens=1500,
        )
        data = parse_json(res.text)
        said_n = normalise(said)
        stated, dropped = [], 0
        for item in data.get("stated", []):
            quote = (item or {}).get("quote", "")
            if quote and normalise(quote) in said_n:
                stated.append(item.get("fact") or quote)
            else:
                dropped += 1
        facts = Facts(
            stated=stated,
            unknowns=[u for u in data.get("unknowns", []) if isinstance(u, str)],
            target_variables=[t for t in data.get("target_variables", []) if isinstance(t, str)],
            methods_mentioned=[m for m in data.get("methods_requested", []) if m in ("NIR", "MIR_ATR", "RAMAN", "FLUO", "UVVIS")],
            fibers_mentioned=[f for f in data.get("fibers_mentioned", []) if isinstance(f, str)],
            fluorescent_target_named=data.get("fluorescent_target_named"),
            use_context=data.get("use_context") or "unknown",
            cites_study_as_proof=bool(data.get("cites_study_as_proof")),
            reuses_existing_calibration=bool(data.get("reuses_existing_calibration")),
            new_formulation_or_matrix=bool(data.get("new_formulation_or_matrix")),
            asks_for_certainty=bool(data.get("asks_for_certainty")),
            combination_requested=bool(data.get("combination_requested")),
        )
        facts = detect(said, facts)
        rec["detail"] = f"{len(stated)} stated · {len(facts.unknowns)} unknown" + (f" · {dropped} unquoted dropped" if dropped else "")
        if dropped:
            rec["status"] = "warn"
    return {"facts": facts.model_dump(), "trace": trace}
