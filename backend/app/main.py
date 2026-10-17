# Logfire must be configured before the other app imports so their spans are captured.
import logfire

from app.config import settings

logfire.configure(token=settings.LOGFIRE_TOKEN, send_to_logfire="if-token-present", service_name="spectrasense-backend", console=False)

import hashlib  # noqa: E402
from contextlib import asynccontextmanager  # noqa: E402

from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import JSONResponse  # noqa: E402

from app import guardrails  # noqa: E402
from app.agents.graph import agent  # noqa: E402
from app.gateway import LLMUnavailable  # noqa: E402
from app.schemas import AssessRequest, AssessResponse, QueryRequest, Report, TraceStep  # noqa: E402
from app.services import retrieval  # noqa: E402


@asynccontextmanager
async def lifespan(_app: FastAPI):
    guardrails.initialize_rails()
    yield


app = FastAPI(title="SpectraSense assessment API", version="0.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=[settings.FRONTEND_ORIGIN], allow_methods=["*"], allow_headers=["*"])
logfire.instrument_fastapi(app)

@app.get("/")
@app.get("/health")
def health() -> dict:
    return {
        "service": "spectrasense-backend",
        "llm": ("portkey → openai" if settings.PORTKEY_API_KEY else "openai" if settings.llm_configured else None),
        "models": [settings.PRIMARY_MODEL, settings.FALLBACK_MODEL],
        "fallback_key": bool(settings.OPENAI_FALLBACK_API_KEY),
        "embeddings": bool(settings.GEMINI_API_KEY),
        "qdrant": "cloud" if settings.QDRANT_URL else "local",
        "kb_chunks": len(retrieval.chunks()),
        "guardrails": f"llm ({settings.FALLBACK_MODEL}, rules fallback)" if settings.llm_guard_available else "rules",
    }


@app.get("/graph")
def graph() -> dict:
    return {"mermaid": agent.get_graph().draw_mermaid()}


def _gate(text: str) -> tuple[bool, str | None, list[str], TraceStep]:
    """Safety gate on the latest client message. Hard rails block; premise flags pass through to the checks."""
    with logfire.span("safety gate"):
        r = guardrails.check(text)
    flags = [c.value for c in r.all_flags if c.is_premise_flag]
    if not r.passed:
        return True, r.message, [], TraceStep(step="Safety gate", status="fail", detail=f"blocked: {r.category.value} · {r.engine}")
    detail = f"passed · {r.engine}" + (f" · flags: {', '.join(flags)}" if flags else "")
    return False, None, flags, TraceStep(step="Safety gate", status="warn" if flags else "ok", detail=detail)


def _blocked_report(scenario_id: str | None) -> Report:
    return Report(
        scenarioId=scenario_id, title="Request not assessed", origin="live", decisionStatus="out_of_scope",
        requirements={"stated": [], "unknowns": []}, questions=[], recommendations=[],
        concept={"summary": "Not assessed: the request was stopped by the safety gate."},
        spectralRange={"summary": "Not assessed."}, risks=[], feasibility={"steps": [], "decisionBasis": "Not assessed."},
        sources=[],
    )


def _thread(messages: list[dict], scenario_id: str | None) -> str:
    first = next((m["content"] for m in messages if m["role"] == "user"), "")
    return hashlib.sha256(f"{scenario_id}|{first}".encode()).hexdigest()[:24]


def _unavailable(e: Exception) -> JSONResponse:
    return JSONResponse(status_code=503, content={"error": "llm_unavailable", "message": str(e)})


# The frontend's zod schema uses .optional(), which rejects null: never send None fields.
@app.post("/assess", response_model=AssessResponse, response_model_exclude_none=True)
def assess(req: AssessRequest):
    """Frontend contract: whole conversation in, reply + full report version + trace out."""
    messages = [m.model_dump() for m in req.messages]
    fired, response, flags, gate = _gate(messages[-1]["content"])
    if fired:
        return AssessResponse(reply=response or "This request is outside what the assistant can help with.",
                              report=_blocked_report(req.scenarioId), trace=[gate])
    config = {"configurable": {"thread_id": _thread(messages, req.scenarioId)}}
    try:
        out = agent.invoke({"messages": messages, "scenario_id": req.scenarioId, "gate_flags": flags, "trace": []}, config=config)
    except LLMUnavailable as e:
        return _unavailable(e)
    except Exception as e:  # noqa: BLE001
        logfire.exception("assessment failed")
        return JSONResponse(status_code=500, content={"error": "assessment_failed", "message": f"The assessment failed: {e}"[:300]})
    return AssessResponse(reply=out.get("reply", ""), report=Report(**out["report"]), trace=[gate, *[TraceStep(**t) for t in out.get("trace", [])]])


@app.post("/query")
def query(req: QueryRequest):
    """Template-compatible endpoint (Streamlit chat / eval app): one message per call, memory by thread_id."""
    fired, response, flags, _ = _gate(req.q)
    if fired:
        return {"question": req.q, "answer": response, "thought_process": ["Intent: Guardrails Fired", "Retrieval: Skipped"],
                "status": "Blocked by guardrails.", "sources": []}
    config = {"configurable": {"thread_id": req.thread_id or "default_user"}}
    prior = agent.get_state(config).values.get("messages", []) if agent.get_state(config) else []
    messages = [*prior, {"role": "user", "content": req.q}]
    try:
        out = agent.invoke({"messages": messages, "gate_flags": flags, "trace": []}, config=config)
    except LLMUnavailable as e:
        return _unavailable(e)
    agent.update_state(config, {"messages": [*messages, {"role": "assistant", "content": out.get("reply", "")}]})
    report = out.get("report") or {}
    return {
        "question": req.q,
        "answer": out.get("reply"),
        "report": report,
        "thought_process": [f"{t['step']}: {t.get('detail', t['status'])}" for t in out.get("trace", [])],
        "status": report.get("decisionStatus", "conversational"),
        "sources": [d["text"] for d in out.get("documents", [])],
        "contexts": [f"[{d['source']} p.{d['page']}] {d['text']}" for d in out.get("documents", [])],
    }
