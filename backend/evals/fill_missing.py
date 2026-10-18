"""Re-run only the judge marks that failed in the latest eval run (rate limit, malformed JSON) and update its result files.

    JUDGE_GROQ_MODEL=openai/gpt-oss-20b python -m evals.fill_missing [--minutes 75]

Uses the same judge and the same inputs as the run (stored answers, pages rebuilt offline); waits for the provider's
retry time on a rate limit, up to the time budget. Marks that still fail stay recorded as not marked.
"""

from __future__ import annotations

import argparse
import json
import re
import time

from evals import metrics as M
from evals.judge import Judge
from evals.run_evals import FRONTEND_OUT, GOLDEN, RESULTS_DIR, SCENARIOS, load_cached, reference_doc, summarise, to_markdown


def _wait_s(err: str) -> float | None:
    m = re.search(r"try again in (?:(\d+)m)?([\d.]+)s", err)
    return (int(m.group(1) or 0) * 60 + float(m.group(2))) if m else None


def mark(judge: Judge, scenario: dict, report: dict, docs: list[dict], name: str):
    reference = GOLDEN.get(scenario["id"], {}).get("reference", [])
    if name == "faithfulness":
        return M.faithfulness(judge, report, [*docs, reference_doc()] if docs else [])
    return {"answer_relevancy": lambda: M.answer_relevancy(judge, scenario["enquiry"], report),
            "context_precision": lambda: M.context_precision(judge, scenario["enquiry"], docs),
            "context_recall": lambda: M.context_recall(judge, reference, docs),
            "answer_correctness": lambda: M.answer_correctness(judge, reference, report)}[name]()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--minutes", type=float, default=75)
    deadline = time.time() + ap.parse_args().minutes * 60
    path = FRONTEND_OUT / "evals-latest.json"
    result = json.loads(path.read_text())
    judge = Judge()
    by_id = {s["id"]: s for s in SCENARIOS}

    def save() -> None:
        result["summary"] = summarise([r for r in result["scenarios"] if not r.get("error")], result["metrics"])
        payload = json.dumps(result, ensure_ascii=False, indent=1)
        for p in (path, RESULTS_DIR / "latest.json"):
            p.write_text(payload)
        (RESULTS_DIR / "latest.md").write_text(to_markdown(result, result["metrics"]))

    for row in result["scenarios"]:
        errors = row.get("metrics", {}).get("metric_errors") or {}
        for name in list(errors):
            report, docs, _ = load_cached(by_id[row["id"]])
            while time.time() < deadline:
                try:
                    value = mark(judge, by_id[row["id"]], report, docs, name)
                    if name == "faithfulness":
                        value, row["metrics"]["unsupported_claims"] = value[0], [c.get("claim") for c in value[1] if not c.get("supported")]
                    row["metrics"][name] = value
                    del errors[name]
                    print(f"{row['id']} {name} = {value}", flush=True)
                    save()
                    break
                except Exception as e:  # noqa: BLE001
                    wait = _wait_s(str(e))
                    errors[name] = str(e)[:200]
                    if wait is None:  # not a rate limit: one retry, then leave it
                        print(f"{row['id']} {name} failed: {str(e)[:120]}", flush=True)
                        if errors.get(f"_{name}_retried"):
                            break
                        errors[f"_{name}_retried"] = "1"
                        continue
                    print(f"{row['id']} {name}: rate limited, waiting {min(wait + 5, 600):.0f} s", flush=True)
                    time.sleep(min(wait + 5, 600))
        for k in [k for k in errors if k.startswith("_")]:
            del errors[k]
        if not errors:
            row["metrics"].pop("metric_errors", None)
    result["judge_calls"] = result.get("judge_calls", 0) + judge.calls
    save()
    left = sum(len(r.get("metrics", {}).get("metric_errors") or {}) for r in result["scenarios"])
    print(f"done; {left} marks still missing")


if __name__ == "__main__":
    main()
