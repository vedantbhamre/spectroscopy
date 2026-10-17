from app.agents.nodes.common import step
from app.agents.state import AgentState
from app.services.retrieval import retrieve


def retriever_node(state: AgentState) -> dict:
    """Hybrid search over the AFS pages (Qdrant + BM25), reranked with FlashRank."""
    trace = list(state.get("trace", []))
    facts = state.get("facts", {})
    queries = list(state.get("queries", []))
    if facts.get("target_variables"):
        queries.append(" ".join(facts["target_variables"] + facts.get("methods_mentioned", [])))
    with step({"trace": trace}, "Retrieve AFS pages") as rec:
        docs, info = retrieve(queries, top_n=8)
        pages = sorted({f"{d['source']} p.{d['page']}" for d in docs})
        rec["detail"] = ", ".join(pages[:8]) + f" · {'vector+BM25' if info['vector'] else 'BM25'} · {info['rerank']}"
        if not docs:
            rec["status"] = "warn"
    return {"documents": docs, "trace": trace}
