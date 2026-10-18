"""Answer coverage, deterministic and token-free: does each report contain what the expected answer contains?

    python -m evals.coverage            # score frontend/outputs/<ID>.json, write evals/results/coverage.md

Two measures, both against material the pipeline never reads:
  useful sources  share of the organisers' "useful sources" pages (AFS_Examples_and_Reference.docx, D01–D08) that the
                  report cites
  key points      share of the expected answer's key points found in the report. Points come from the organiser worked
                  examples (D01, D02; also in golden.json "reference") and from the team's expert reviews of H04 and H06.
                  Each point is a list of term groups; it counts as present when every group has a match.
Keyword matching is a proxy, not a judgement: a point can be worded differently and missed, or matched without being
argued well. The LLM judge (evals.run_evals, answer_correctness) is the semantic check.
"""

from __future__ import annotations

import json
import re

from app.config import BACKEND_DIR

FRONTEND_OUT = BACKEND_DIR.parent / "frontend" / "outputs"
RESULTS = BACKEND_DIR / "evals" / "results" / "coverage.md"

USEFUL = {
    "D01": "S01 p.5, 10, 11, 14–15", "D02": "S01 p.5, 10, 17, 18", "D03": "S01 p.5, 10, 17, 18", "D04": "S01 p.5, 10, 11, 16",
    "D05": "S01 p.5, 16", "D06": "S01 p.6, 9, 10; S02 p.6, 13", "D07": "S01 p.5, 6, 10; S02 p.14", "D08": "S01 p.5, 6, 8–10; S04 p.1, 3, 4",
}

Point = tuple[str, list[list[str]]]
KEY_POINTS: dict[str, list[Point]] = {
    "D01": [
        ("NIR diffuse reflection for the powder blend", [["nir"], ["reflect"]]),
        ("matrix-specific calibration to build and test", [["calibrat"]]),
        ("Raman as comparison; check fluorescence background", [["raman"], ["fluoresc"]]),
        ("combination only after each method alone", [["combin", "both methods"], ["single", "each method", "on its own", "separately", "individually"]]),
        ("nominal NIR range 780–2500 nm", [["780"], ["2500"]]),
        ("API or excipient change can invalidate the calibration", [["excipient", "formulation", "composition"], ["calibrat"]]),
        ("physical variation of the powder changes the signal", [["particle size", "density", "flow", "compaction", "segregation"]]),
        ("independent reference assays, validation on held-out runs", [["reference"], ["held-out", "independent", "batch", "runs"]]),
        ("acceptance criteria agreed with the client first", [["acceptance", "criteria"], ["agree"]]),
    ],
    "D02": [
        ("NIR diffuse reflection for the opaque product", [["nir"], ["reflect"]]),
        ("laboratory samples before the process installation", [["laboratory", "lab "], ["sample"]]),
        ("780–2500 nm is the general NIR range", [["780"], ["2500"]]),
        ("temperature, texture, scattering can mimic composition", [["temperature"], ["texture", "scatter"]]),
        ("independent fat and protein reference results", [["fat"], ["protein"], ["reference"]]),
        ("validation on independent production runs", [["independent", "held-out"], ["run", "batch", "production"]]),
    ],
    "H04": [
        ("silica fibre does not carry the mid-IR range", [["silica"], ["mir", "mid-ir", "mid-infrared"]]),
        ("link length / remote analyzer is a feasibility question", [["length", "distance", "building"], ["transmission", "loss", "attenuat", "close to"]]),
    ],
    "H06": [
        ("plain answer: cannot be quoted as proof", [["cannot", "not proof", "no,", "not be used", "not be quoted"]]),
        ("the study is in vitro", [["in vitro", "in-vitro", "ex vivo", "ex-vivo"]]),
        ("small study: seven pairs / 14 samples", [["seven", "14 ", " 7 "]]),
        ("whole samples classified, not a boundary located", [["boundary", "margin"], ["whole sample", "classif"]]),
        ("their own sensor is not the study's", [["own sensor", "customer's sensor", "your sensor", "own setup", "prototype"]]),
        ("'aimed at in vivo' is a goal, not a result", [["aim", "goal"]]),
        ("validate on patients not used for the model", [["held-out", "unseen", "not used to build", "different patients", "other patients"]]),
        ("over-fitting risk", [["overfit", "over-fit"]]),
    ],
}

_DASHES = str.maketrans({c: "-" for c in "‐‑‒–—"})


def pages(spec: str) -> set[tuple[str, int]]:
    out = set()
    for part in spec.split(";"):
        src, rest = part.strip().split(" p.")
        for tok in (x.strip() for x in rest.split(",")):
            a, _, b = tok.replace("–", "-").partition("-")
            out |= {(src, p) for p in range(int(a), int(b or a) + 1)}
    return out


def _cited(report: dict) -> set[tuple[str, int]]:
    out = set()
    for c in report.get("sources", []):
        for n in re.findall(r"\d+", str(c.get("page", ""))):
            out.add((c["source"], int(n)))
        m = re.match(r"(\d+)\s*[–-]\s*(\d+)", str(c.get("page", "")))
        if m:
            out |= {(c["source"], p) for p in range(int(m[1]), int(m[2]) + 1)}
    return out


def _text(report: dict) -> str:
    return json.dumps(report, ensure_ascii=False).translate(_DASHES).lower()


def score(case: str, report: dict) -> dict:
    out: dict = {"case": case, "status": report.get("decisionStatus"), "answer": bool(report.get("answer"))}
    if case in USEFUL:
        truth = pages(USEFUL[case])
        got = _cited(report) & truth
        out["useful"] = len(got) / len(truth)
        out["useful_missing"] = sorted(truth - got)
    if case in KEY_POINTS:
        text = _text(report)
        hit = [label for label, groups in KEY_POINTS[case] if all(any(t in text for t in g) for g in groups)]
        out["points"] = len(hit) / len(KEY_POINTS[case])
        out["points_missing"] = [label for label, _ in KEY_POINTS[case] if label not in hit]
    return out


def run() -> list[dict]:
    rows = []
    for case in sorted({*USEFUL, *KEY_POINTS}):
        path = FRONTEND_OUT / f"{case}.json"
        if path.exists():
            data = json.loads(path.read_text())
            rows.append(score(case, data.get("report", data)))
    return rows


def markdown(rows: list[dict]) -> str:
    def pct(x):
        return "–" if x is None else f"{x:.2f}"

    lines = ["# Answer coverage (deterministic, cached outputs)", "",
             "| Case | Status | Answer first | Useful sources cited | Key points | Missing |", "|---|---|---|---|---|---|"]
    for r in rows:
        miss = [*(f"{s} p.{p}" for s, p in r.get("useful_missing", [])), *r.get("points_missing", [])]
        lines.append(f"| {r['case']} | {r['status']} | {'yes' if r['answer'] else 'no'} | {pct(r.get('useful'))} | {pct(r.get('points'))} | {'; '.join(miss) or '–'} |")
    u = [r["useful"] for r in rows if "useful" in r]
    k = [r["points"] for r in rows if "points" in r]
    lines += ["", f"Mean useful sources cited: {sum(u) / len(u):.2f} ({len(u)} cases) · mean key points: {sum(k) / len(k):.2f} ({len(k)} cases)"]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    rows = run()
    md = markdown(rows)
    RESULTS.write_text(md)
    print(md)
