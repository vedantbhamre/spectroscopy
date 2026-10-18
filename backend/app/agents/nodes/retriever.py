from app.agents.nodes.common import client_text, step
from app.agents.state import AgentState
from app.config import settings
from app.knowledge.applications import tag
from app.services.retrieval import retrieve


def retriever_node(state: AgentState) -> dict:
    """Pages routed by the source guide (domain, methods, fibre topic), then BM25 / vector search, one chunk per page."""
    trace = list(state.get("trace", []))
    facts = state.get("facts", {})
    queries = list(state.get("queries", []))
    if facts.get("target_variables"):
        queries.append(" ".join(facts["target_variables"] + facts.get("methods_mentioned", [])))
    with step({"trace": trace}, "Retrieve AFS pages") as rec:
        # Route on the customer's own words plus what the analyst recognised (domain, named methods).
        routing = " ".join([client_text(state["messages"]), facts.get("application_domain") or "",
                            " ".join(m.replace("_", " ") for m in facts.get("methods_mentioned", []))])
        docs, info = retrieve(queries, top_n=settings.RETRIEVE_TOP_N, routing_text=routing)
        # Each retrieved example carries the application(s) it describes, so a transfer to another one is visible.
        docs = [{**d, "applications": tag(d.get("text", ""))} for d in docs]
        pages = sorted({f"{d['source']} p.{d['page']}" for d in docs})
        rec["detail"] = (", ".join(pages[:10]) + f" · {info['routed']} routed by the source guide · "
                         + ("vector+BM25" if info["vector"] else "BM25") + (f" · rerank {info['rerank']}" if info["rerank"] != "off" else ""))
        if not docs:
            rec["status"] = "warn"
    return {"documents": docs, "trace": trace}
