from app.agents.nodes.common import step
from app.agents.state import AgentState
from app.services.premises import Facts, run_checks


def checker_node(state: AgentState) -> dict:
    """Deterministic premise checks (fibre windows, target defined, source scope, …)."""
    trace = list(state.get("trace", []))
    with step({"trace": trace}, "Premise checks") as rec:
        checks = run_checks(Facts(**state.get("facts", {})))
        fails = [c for c in checks if c.status == "fail"]
        flags = [c for c in checks if c.status == "flag"]
        rec["status"] = "fail" if fails else "warn" if flags else "ok"
        rec["detail"] = "; ".join(c.label for c in fails + flags) or "nothing contradicted"
    return {"checks": [c.model_dump() for c in checks], "trace": trace}
