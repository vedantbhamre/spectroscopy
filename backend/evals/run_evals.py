"""Evals pipeline: run scenarios through the live graph, score them, write a report.

    python -m evals.run_evals                  # all D01–D08, H01–H06 (live pipeline + judge)
    python -m evals.run_evals D01 H04          # selected scenarios
    python -m evals.run_evals --no-judge       # deterministic metrics only (no judge LLM cost)
    python -m evals.run_evals --from-cache     # score frontend/outputs/<ID>.json instead of running the graph
                                               # (no retrieved pages there, so context metrics are skipped)

Writes evals/results/<timestamp>.json, evals/results/latest.json + latest.md,
and frontend/outputs/evals-latest.json for the frontend's evals view.
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean

from app.config import BACKEND_DIR
from evals import metrics as M
from evals.judge import Judge, JudgeUnavailable

EVALS_DIR = BACKEND_DIR / "evals"
RESULTS_DIR = EVALS_DIR / "results"
FRONTEND_OUT = BACKEND_DIR.parent / "frontend" / "outputs"
SCENARIOS = json.loads((BACKEND_DIR / "data" / "scenarios.json").read_text())
GOLDEN = {k: v for k, v in json.loads((EVALS_DIR / "golden.json").read_text()).items() if not k.startswith("_")}

DETERMINISTIC = ["citation_validity", "grounding", "clarification", "feasibility", "expectations"]
JUDGED = ["faithfulness", "answer_relevancy", "context_precision", "context_recall", "answer_correctness"]


def reference_doc() -> dict:
    """The method ranges and fibre windows the pipeline reasons with (app/knowledge/optics.py), as one
    context page for the judge: every line is backed by a quote verified on S01/S02, but those pages are
    not always among the retrieved ones, so without this the judge marks range claims unsupported."""
    from app.knowledge.optics import FIBERS, METHODS

    rows = [f"{m.label}: nominal range {m.range_label} ({m.cite.source} p.{m.cite.page}: \"{m.cite.quote}\")"
            for m in METHODS.values() if m.cite]
    rows += [f"{f.label}: transmits about {f.range_um[0]}–{f.range_um[1]} µm ({f.cite.source} p.{f.cite.page}: \"{f.cite.quote}\")"
             for f in FIBERS.values()]
    return {"source": "S01/S02", "label": "method ranges and fibre windows", "text": "\n".join(rows)}


def run_live(scenario: dict) -> tuple[dict, list[dict], float]:
    from app.agents.graph import agent  # imported lazily: --from-cache needs no LLM key

    start = time.perf_counter()
    out = agent.invoke(
        {"messages": [{"role": "user", "content": scenario["enquiry"]}], "scenario_id": scenario["id"], "trace": []},
        config={"configurable": {"thread_id": f"eval-{scenario['id']}-{time.time()}"}},
    )
    return out["report"], out.get("documents", []), (time.perf_counter() - start) * 1000


def load_cached(scenario: dict) -> tuple[dict, list[dict], float | None]:
    """A stored answer and the pages it was written from. The pages are rebuilt offline (no LLM): the same retrieval for
    the enquiry (without the planner's extra queries) plus every page the answer cites, so the judge can grade
    faithfulness and context against them."""
    from app.config import settings
    from app.services.retrieval import chunks, retrieve

    data = json.loads((FRONTEND_OUT / f"{scenario['id']}.json").read_text())
    report = data.get("report", data)
    docs, _ = retrieve([], top_n=settings.RETRIEVE_TOP_N, routing_text=scenario["enquiry"])
    have = {(d["source"], str(d["page"])) for d in docs}
    for c in report.get("sources", []):
        key = (c.get("source"), str(c.get("page")))
        if key in have or not str(c.get("page", "")).isdigit():
            continue
        page = [ch for ch in chunks() if ch["source"] == key[0] and str(ch["page"]) == key[1]]
        if page:
            docs.append(page[0])
            have.add(key)
    return report, docs, None


def score(scenario: dict, report: dict, documents: list[dict], judge: Judge | None) -> dict:
    golden = GOLDEN.get(scenario["id"], {})
    reference = golden.get("reference", [])
    exp_score, exp_failures = M.expectations(report, golden)
    row: dict = {
        "citation_validity": M.citation_validity(report),
        "grounding": M.grounding(report),
        "clarification": M.clarification(report),
        "feasibility": M.feasibility(report),
        "expectations": exp_score,
        "expectation_failures": exp_failures,
    }
    if judge is None:
        return row
    jobs = {
        "faithfulness": lambda: M.faithfulness(judge, report, [*documents, reference_doc()] if documents else []),
        "answer_relevancy": lambda: M.answer_relevancy(judge, scenario["enquiry"], report),
        "context_precision": lambda: M.context_precision(judge, scenario["enquiry"], documents),
        "context_recall": lambda: M.context_recall(judge, reference, documents),
        "answer_correctness": lambda: M.answer_correctness(judge, reference, report),
    }
    errors = {}
    for name, job in jobs.items():
        try:
            value = job()
            if name == "faithfulness":
                value, row["unsupported_claims"] = value[0], [c.get("claim") for c in value[1] if not c.get("supported")]
            row[name] = value
        except Exception as e:  # noqa: BLE001 - one failing metric must not stop the run
            row[name], errors[name] = None, str(e)[:200]
    if errors:
        row["metric_errors"] = errors
    return row


def _fmt(v) -> str:
    return "  –  " if v is None else f"{v:5.2f}"


def summarise(rows: list[dict], names: list[str]) -> dict:
    out = {}
    for name in names:
        for subset, label in ((rows, "all"), ([r for r in rows if r["set"] == "development"], "development"),
                              ([r for r in rows if r["set"] == "evaluation"], "evaluation")):
            vals = [r["metrics"][name] for r in subset if r.get("metrics", {}).get(name) is not None]
            out.setdefault(name, {})[label] = round(mean(vals), 4) if vals else None
    return out


def to_markdown(result: dict, names: list[str]) -> str:
    lines = [f"# Eval run {result['run_at']}", "",
             f"Mode: {result['mode']} · judge: {result['judge'] or 'off'} · judge calls: {result['judge_calls']}", "",
             "| Scenario | Status | " + " | ".join(names) + " | Time |", "|" + "---|" * (len(names) + 3)]
    for r in result["scenarios"]:
        if r.get("error"):
            lines.append(f"| {r['id']} | FAILED: {r['error']} |" + " |" * (len(names) + 1))
            continue
        m = r["metrics"]
        t = f"{r['ms'] / 1000:.1f}s" if r.get("ms") else "–"
        lines.append(f"| {r['id']} | {r['status']} | " + " | ".join(_fmt(m.get(n)).strip() for n in names) + f" | {t} |")
    lines += ["", "## Averages", "", "| Metric | All | Development | Evaluation |", "|---|---|---|---|"]
    for n in names:
        s = result["summary"][n]
        lines.append(f"| {n} | {_fmt(s['all']).strip()} | {_fmt(s['development']).strip()} | {_fmt(s['evaluation']).strip()} |")
    failures = [(r["id"], f) for r in result["scenarios"] for f in r.get("metrics", {}).get("expectation_failures", [])]
    if failures:
        lines += ["", "## Expectation failures", ""] + [f"- **{i}**: {f}" for i, f in failures]
    unsupported = [(r["id"], c) for r in result["scenarios"] for c in r.get("metrics", {}).get("unsupported_claims", []) if c]
    if unsupported:
        lines += ["", "## Claims the judge found unsupported by the retrieved pages", ""] + [f"- **{i}**: {c}" for i, c in unsupported]
    return "\n".join(lines) + "\n"


def run(ids: list[str] | None = None, *, judge_on: bool = True, from_cache: bool = False, progress=None) -> dict:
    """One eval run; writes the result files and returns the result.

    progress(done, total, scenario_id) is called before each scenario (the API's status endpoint uses it).
    """
    judge = None
    if judge_on:
        try:
            judge = Judge()
        except JudgeUnavailable as e:
            print(f"Judge off: {e}. Running deterministic metrics only.")
    names = DETERMINISTIC + (JUDGED if judge else [])

    chosen = [s for s in SCENARIOS if not ids or s["id"] in ids]
    rows = []
    for i, s in enumerate(chosen):
        if progress:
            progress(i, len(chosen), s["id"])
        try:
            report, docs, ms = load_cached(s) if from_cache else run_live(s)
            m = score(s, report, docs, judge)
            rows.append({"id": s["id"], "set": s["set"], "title": s["title"], "status": report.get("decisionStatus"),
                         "ms": ms, "pages_retrieved": len(docs), "metrics": m})
            print(f"{s['id']}  {report.get('decisionStatus', '?'):13}" + " ".join(f"{n[:12]}={_fmt(m.get(n)).strip()}" for n in names))
        except Exception as e:  # noqa: BLE001 - keep going, report at the end
            rows.append({"id": s["id"], "set": s["set"], "title": s["title"], "error": str(e)[:300]})
            print(f"{s['id']}  FAILED  {e}")
    if progress:
        progress(len(chosen), len(chosen), None)

    result = {
        "run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "mode": "stored answers (pages rebuilt offline)" if from_cache else "live pipeline",
        "judge": judge.route if judge else None,
        "judge_calls": judge.calls if judge else 0,
        "metrics": names,
        "summary": summarise([r for r in rows if not r.get("error")], names),
        "scenarios": rows,
    }
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = result["run_at"].replace(":", "").replace("-", "")
    payload = json.dumps(result, ensure_ascii=False, indent=1)
    (RESULTS_DIR / f"{stamp}.json").write_text(payload)
    (RESULTS_DIR / "latest.json").write_text(payload)
    (RESULTS_DIR / "latest.md").write_text(to_markdown(result, names))
    FRONTEND_OUT.mkdir(parents=True, exist_ok=True)
    (FRONTEND_OUT / "evals-latest.json").write_text(payload)
    print(f"\nWrote {RESULTS_DIR.relative_to(BACKEND_DIR)}/latest.md and frontend/outputs/evals-latest.json")
    return result


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("ids", nargs="*", help="scenario IDs (default: all)")
    p.add_argument("--no-judge", action="store_true", help="deterministic metrics only")
    p.add_argument("--from-cache", action="store_true", help="score frontend/outputs/<ID>.json instead of running the graph")
    args = p.parse_args()
    run(args.ids, judge_on=not args.no_judge, from_cache=args.from_cache)


if __name__ == "__main__":
    main()
