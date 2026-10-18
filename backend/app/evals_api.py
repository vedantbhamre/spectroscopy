"""Run the eval suite from the frontend's Evals page ("Run evals" button).

Evals cost money (every scenario runs the live pipeline, plus judge calls), so a run starts only on
an explicit POST, never on page load or in tests, and is guarded:
  - one run at a time (409 while running)
  - a cooldown of EVAL_COOLDOWN_MIN minutes since the last run, read from the results on disk so it
    survives restarts (429 with the seconds left)
The run itself is evals.run_evals.run() in a background thread; GET /evals/status reports progress.
"""

import json
import threading
from datetime import datetime, timezone

import logfire
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.config import BACKEND_DIR, settings

router = APIRouter(prefix="/evals", tags=["evals"])

LATEST = BACKEND_DIR / "evals" / "results" / "latest.json"
SCENARIO_COUNT = len(json.loads((BACKEND_DIR / "data" / "scenarios.json").read_text()))
# Rough cost of one full run (14 scenarios through the pipeline + judge), for the confirmation dialog.
ESTIMATE = {"openai": "about $0.20 (gpt-4o pipeline, gpt-4o-mini judge)", "groq": "a few cents on Groq (gpt-oss)"}

_lock = threading.Lock()
_state: dict = {"running": False, "done": 0, "total": 0, "current": None, "started_at": None, "finished_at": None, "error": None}


class RunRequest(BaseModel):
    judge: bool = True


def _now() -> datetime:
    return datetime.now(timezone.utc)


def last_run_at() -> datetime | None:
    try:
        return datetime.fromisoformat(json.loads(LATEST.read_text())["run_at"])
    except Exception:  # noqa: BLE001 - no run yet, or an unreadable file
        return None


def cooldown_left() -> int:
    last = last_run_at()
    if not last:
        return 0
    return max(0, int(settings.EVAL_COOLDOWN_MIN * 60 - (_now() - last).total_seconds()))


def status() -> dict:
    last = last_run_at()
    return {
        **_state,
        "last_run_at": last.isoformat() if last else None,
        "cooldown_s": cooldown_left(),
        "cooldown_min": settings.EVAL_COOLDOWN_MIN,
        "scenarios": SCENARIO_COUNT,
        "provider": settings.LLM_PROVIDER,
        "estimate": ESTIMATE.get(settings.LLM_PROVIDER, "unknown"),
        "llm_configured": settings.llm_configured,
    }


def _worker(judge: bool) -> None:
    from evals.run_evals import run  # imported here: the API starts without loading the eval suite

    def progress(done: int, total: int, current: str | None) -> None:
        _state.update(done=done, total=total, current=current)

    try:
        with logfire.span("eval run (button)", judge=judge):
            run(judge_on=judge, progress=progress)
    except Exception as e:  # noqa: BLE001 - surface the failure on the status endpoint
        logfire.exception("eval run failed")
        _state["error"] = str(e)[:300]
    finally:
        _state.update(running=False, current=None, finished_at=_now().isoformat(timespec="seconds"))


@router.get("/status")
def get_status():
    return status()


@router.post("/run")
def start_run(req: RunRequest):
    with _lock:
        if _state["running"]:
            return JSONResponse(status_code=409, content={"error": "running", "message": "An eval run is already in progress.", **status()})
        if not settings.llm_configured:
            return JSONResponse(status_code=503, content={"error": "llm_unavailable", "message": "No LLM key is configured.", **status()})
        if left := cooldown_left():
            return JSONResponse(status_code=429, content={
                "error": "cooldown", "message": f"The last run was less than {settings.EVAL_COOLDOWN_MIN:g} minutes ago. Try again in {left // 60 + 1} min.",
                **status()})
        _state.update(running=True, done=0, total=SCENARIO_COUNT, current=None, error=None,
                      started_at=_now().isoformat(timespec="seconds"), finished_at=None)
        threading.Thread(target=_worker, args=(req.judge,), daemon=True, name="eval-run").start()
    return status()
