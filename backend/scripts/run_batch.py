"""Run the scenarios through the live pipeline, write frontend/outputs/<ID>.json and a validation report.

    python -m scripts.run_batch            # all D01–D08 and H01–H06
    python -m scripts.run_batch H04 H06    # selected ones
    python -m scripts.run_batch --single   # first turn only (no follow-up)

Each case: turn 1 = the enquiry (written to frontend/outputs as the cached result); turn 2 = a generic
follow-up in which the customer answers every open question with "don't know", which exposes repeated
questions. Reported per case: citation pass rate, number-validator hits, repeated-question count,
missing-section count, plus the acceptance-property violations (evals/acceptance.py) and the golden
expectations for turn 1. Outputs are generated, never edited by hand.
"""

import json
import sys
import time
from pathlib import Path

from app.agents.graph import agent
from app.gateway.client import USAGE
from app.config import BACKEND_DIR
from app.schemas import AssessResponse, Report, TraceStep
from evals import acceptance as A
from evals import metrics as M

OUT_DIR = BACKEND_DIR.parent / "frontend" / "outputs"
REPORT_MD = BACKEND_DIR / "evals" / "results" / "batch-latest.md"
SCENARIOS = json.loads((BACKEND_DIR / "data" / "scenarios.json").read_text())
GOLDEN = {k: v for k, v in json.loads((BACKEND_DIR / "evals" / "golden.json").read_text()).items() if not k.startswith("_")}


def invoke(messages: list[dict], scenario_id: str, thread: str, answers: list[dict] | None = None) -> dict:
    return agent.invoke({"messages": messages, "scenario_id": scenario_id, "trace": [], "answers": answers or [], "final_mode": False,
                         "gate_flags": []}, config={"configurable": {"thread_id": thread}})


def _composer(out: dict) -> str:
    return next((x["detail"].split(" · ")[0] for x in out["trace"] if x["step"] == "Compose the assessment"), "?")


def first_turn(s: dict) -> dict:
    thread = f"batch-{s['id']}-{time.time()}"
    messages = [{"role": "user", "content": s["enquiry"]}]
    before = dict(USAGE)
    out = invoke(messages, s["id"], thread)
    resp = AssessResponse(reply=out["reply"], report=Report(**out["report"]), trace=[TraceStep(**t) for t in out["trace"]])
    (OUT_DIR / f"{s['id']}.json").write_text(json.dumps(resp.model_dump(exclude_none=True), ensure_ascii=False, indent=1))
    return {"thread": thread, "turns": [{"messages": list(messages), "answers": [], "final": False, "report": out["report"], "reply": out["reply"],
                                          "validation": out.get("validation", {}), "model": _composer(out), "tokens": _used(before)}]}


def follow_up(s: dict, case: dict) -> None:
    """Turn 2: the customer answers every open question with "don't know" (exposes repeated questions)."""
    t1 = case["turns"][0]
    open_q = [q for q in t1["report"]["questions"] if q.get("status") == "open"]
    answers = [{"id": q["id"], "question": q["text"], "status": "answered_unknown"} for q in open_q]
    messages = t1["messages"] + [{"role": "assistant", "content": t1["reply"]},
                                 {"role": "user", "content": "Answers to your questions:\n" + "\n".join(f"- Q: {q['text']}\n  A: unknown" for q in open_q)}]
    before = dict(USAGE)
    out = invoke(messages, s["id"], case["thread"], answers)
    case["turns"].append({"messages": list(messages), "answers": answers, "final": False, "report": out["report"], "reply": out["reply"],
                          "validation": out.get("validation", {}), "model": _composer(out), "tokens": _used(before)})


def _used(before: dict) -> int:
    return sum(USAGE.values()) - sum(before.values())


def summarise(s: dict, turns: list[dict]) -> dict:
    cites = [t["validation"].get("citations", {}) for t in turns]
    found = sum(c.get("verified", 0) + c.get("visual_note", 0) for c in cites)
    total = sum(sum(c.values()) for c in cites)
    violations = A.run_all(turns)
    exp, fails = M.expectations(turns[0]["report"], GOLDEN.get(s["id"], {}))
    return {
        "id": s["id"], "status": [t["report"]["decisionStatus"] for t in turns],
        "citation_pass": f"{found}/{total}" + (f" ({found / total:.0%})" if total else ""),
        "number_hits": sum(t["validation"].get("numbers_replaced", 0) for t in turns),
        "repeated_questions": len(violations["no repeated questions"]),
        "missing_sections": sum(len(A.missing_sections(t["report"])) for t in turns),
        "repaired": sum(bool(t["validation"].get("repaired")) for t in turns),
        "moved_sentences": sum(t["validation"].get("sentences_moved", 0) + t["validation"].get("recommendations_moved", 0) for t in turns),
        "violations": {k: v for k, v in violations.items() if v},
        "models": [t.get("model") for t in turns], "tokens": sum(t.get("tokens", 0) for t in turns),
        "expectations": exp, "expectation_failures": fails,
        **{k: sum(t["validation"].get(k, 0) for t in turns) for k in ("certainty_rejected", "method_mismatch", "recited", "hardware_moved")},
        "decisive_open": turns[-1]["validation"].get("decisive_open", 0),
    }


def main(argv: list[str]) -> None:
    follow_up_on = "--single" not in argv
    ids = [a for a in argv if not a.startswith("--")]
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    chosen = [s for s in SCENARIOS if not ids or s["id"] in ids]
    cases: dict[str, dict] = {}
    errors: dict[str, str] = {}
    # Phase 1: every enquiry first (these are the cached results the frontend serves), then the follow-ups.
    for s in chosen:
        try:
            cases[s["id"]] = first_turn(s)
            t = cases[s["id"]]["turns"][0]
            print(f"{s['id']} turn 1: {t['report']['decisionStatus']} · {t['model']} · {t['tokens']} tokens", flush=True)
        except Exception as e:  # noqa: BLE001 - keep going, report at the end
            errors[s["id"]] = str(e)[:200]
            print(f"{s['id']} turn 1 FAILED: {errors[s['id']]}", flush=True)
        time.sleep(3)  # spread the load: providers limit tokens per minute
    if follow_up_on:
        for s in chosen:
            if s["id"] not in cases:
                continue
            try:
                follow_up(s, cases[s["id"]])
                t = cases[s["id"]]["turns"][1]
                print(f"{s['id']} turn 2: {t['report']['decisionStatus']} · {t['model']} · {t['tokens']} tokens", flush=True)
            except Exception as e:  # noqa: BLE001
                print(f"{s['id']} turn 2 FAILED: {str(e)[:200]}", flush=True)
            time.sleep(3)
    rows = [summarise(s, cases[s["id"]]["turns"]) if s["id"] in cases else {"id": s["id"], "error": errors.get(s["id"], "not run")} for s in chosen]
    for r in rows:
        print(json.dumps(r, ensure_ascii=False), flush=True)

    # Merge with the stored rows of earlier runs, so re-running some cases keeps the others.
    store = REPORT_MD.with_suffix(".json")
    merged = {r["id"]: r for r in (json.loads(store.read_text()) if store.exists() else [])}
    merged.update({r["id"]: r for r in rows if "error" not in r or "error" in merged.get(r["id"], {"error": 1})})  # a failed run keeps an earlier result
    order = [s["id"] for s in SCENARIOS]
    rows = [merged[i] for i in order if i in merged]
    store.parent.mkdir(parents=True, exist_ok=True)
    store.write_text(json.dumps(rows, ensure_ascii=False, indent=1))
    ok = [r for r in rows if "error" not in r]
    lines = ["# Batch validation report", "", f"{len(ok)} of {len(rows)} cases ran · turns per case: {2 if follow_up_on else 1}", "",
             "| Case | Status (turns) | Citation pass | Number hits | Repeated questions | Missing sections | Repairs | Sentences moved | Certainty rejected | Method-mismatch citations | Re-cited | Open decisive unknowns | Expectations | Model (turns) | Tokens |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        if "error" in r:
            lines.append(f"| {r['id']} | FAILED: {r['error']} | | | | | | | | | | | | | |")
            continue
        lines.append(f"| {r['id']} | {' → '.join(r['status'])} | {r['citation_pass']} | {r['number_hits']} | {r['repeated_questions']} | "
                     f"{r['missing_sections']} | {r['repaired']} | {r['moved_sentences']} | {r.get('certainty_rejected', '–')} | {r.get('method_mismatch', '–')} | {r.get('recited', '–')} | {r.get('decisive_open', '–')} | "
                     f"{r['expectations'] if r['expectations'] is not None else '–'} | "
                     f"{' → '.join(m.replace('openai/', '') for m in r.get('models', []))} | {r.get('tokens', 0):,} |")
    viol = [(r["id"], k, v) for r in ok for k, vs in r["violations"].items() for v in vs]
    lines += ["", "## Acceptance violations", ""] + ([f"- **{i}** {k}: {v}" for i, k, v in viol] or ["None."])
    fails = [(r["id"], f) for r in ok for f in r["expectation_failures"]]
    lines += ["", "## Golden expectation failures (turn 1)", ""] + ([f"- **{i}**: {f}" for i, f in fails] or ["None."])
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_MD.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main(sys.argv[1:])
