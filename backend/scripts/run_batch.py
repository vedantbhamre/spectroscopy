"""Run the scenarios through the live pipeline and write frontend/outputs/<ID>.json.

    python -m scripts.run_batch            # all D01–D08 and H01–H06
    python -m scripts.run_batch H04 H06    # selected ones

Outputs are generated, never edited by hand; the frontend serves them as "cached" results.
"""

import json
import sys
import time
from pathlib import Path

from app.agents.graph import agent
from app.config import BACKEND_DIR
from app.schemas import AssessResponse, Report, TraceStep

OUT_DIR = BACKEND_DIR.parent / "frontend" / "outputs"
SCENARIOS = json.loads((BACKEND_DIR / "data" / "scenarios.json").read_text())


def run(scenario: dict) -> AssessResponse:
    messages = [{"role": "user", "content": scenario["enquiry"]}]
    config = {"configurable": {"thread_id": f"batch-{scenario['id']}-{time.time()}"}}
    out = agent.invoke({"messages": messages, "scenario_id": scenario["id"], "trace": []}, config=config)
    return AssessResponse(reply=out["reply"], report=Report(**out["report"]), trace=[TraceStep(**t) for t in out["trace"]])


def main(ids: list[str]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    chosen = [s for s in SCENARIOS if not ids or s["id"] in ids]
    for s in chosen:
        start = time.perf_counter()
        try:
            resp = run(s)
        except Exception as e:  # noqa: BLE001 - keep going, report at the end
            print(f"{s['id']}  FAILED  {e}")
            continue
        path = OUT_DIR / f"{s['id']}.json"
        path.write_text(json.dumps(resp.model_dump(exclude_none=True), ensure_ascii=False, indent=1))
        cites = [c for c in resp.report.sources]
        found = sum(c.check in ("verified", "visual_note") for c in cites)
        print(f"{s['id']}  {resp.report.decisionStatus:13} checks={[c.id for c in resp.report.premiseChecks if c.status != 'pass']} "
              f"quotes={found}/{len(cites)}  {time.perf_counter() - start:.1f}s → {path.relative_to(BACKEND_DIR.parent)}")


if __name__ == "__main__":
    main(sys.argv[1:])
