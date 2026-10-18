"""Live multi-turn retest of the feed-frame review (SpectraSense_test_review_feed_frame.pdf, section 5).

    python -m scripts.retest_feed_frame

Plays the synthetic customer from the review: answers each open question from its facts (by keyword,
through the per-question answer channel the UI uses), sends the remaining facts as extra details,
then asks for the final answer without further questions. Prints the retest checklist.
Costs about four assessments on the configured LLM provider.
"""

import json
import re
import sys

from fastapi.testclient import TestClient

from app.main import app
from app.services.numbers import PLACEHOLDER

ENQUIRY = ("We manufacture tablets from a powder blend containing an active ingredient (API) and excipients. Our laboratory results "
           "arrive too late to react during production. We want to know whether a fiber-based measurement in the feed frame of the "
           "tablet press can follow the API concentration. The first pilot should compare reasonable measurement options.")

# The review's synthetic answers, matched to questions by keyword. None = "unknown".
FACTS = [
    (r"api|active|excipient|formulation|composition|concentration|ingredient", "paracetamol 10% w/w with MCC, lactose, croscarmellose and magnesium stearate"),
    (r"specification|tolerance|limit|accept|range of|target", "specification 95–105% of target"),
    (r"reference|hplc|laborator|analysis method|assay", "HPLC reference, about 2 h per result"),
    (r"fluoresc", None),
    (r"port|access|install|mount|space|opening|probe position|interface", "one free side port of about 12 mm; contact with the powder is allowed"),
    (r"dust|clean|environment|contamina|fouling", "dusty environment; cleaning between batches"),
    (r"speed|throughput|rate|tablets per|fast|press", "about 60,000 tablets per hour"),
    (r"change|vary|new product|frequen", "the formulation changes monthly"),
    (r"sample|blend|calibration|lab", "lab blends with HPLC reference are available"),
]
EXTRA = ("Other facts: paracetamol 10% w/w with MCC, lactose, croscarmellose and magnesium stearate; specification 95–105% of target; "
         "HPLC reference about 2 h; fluorescence unknown; one free side port of about 12 mm; contact allowed; dusty; cleaning between "
         "batches; about 60,000 tablets per hour; formulation changes monthly; lab blends with HPLC available.")
FINAL = "Give me the solution now, no more questions."


def answer_for(question: str) -> dict:
    for pat, value in FACTS:
        if re.search(pat, question, re.I):
            return {"status": "answered_unknown"} if value is None else {"status": "answered", "answer": value}
    return {"status": "declined"}


def message_for(answers: list[dict], extra: str = "") -> str:
    lines = ["Answers to your questions:"] + [f"- Q: {a['question']}\n  A: {a.get('answer') or ('unknown' if a['status'] == 'answered_unknown' else a['status'])}" for a in answers]
    return "\n".join(lines) + (f"\n\nAdditional details: {extra}" if extra else "")


def main() -> None:
    c = TestClient(app)
    msgs, asked, reports = [{"role": "user", "content": ENQUIRY}], [], []

    def turn(**kw):
        r = c.post("/assess", json={"messages": msgs, **kw})
        r.raise_for_status()
        b = r.json()
        reports.append(b)
        msgs.append({"role": "assistant", "content": b["reply"]})
        open_q = [q for q in b["report"]["questions"] if q.get("status", "open") == "open" and b["report"].get("mode") != "final"]
        asked.extend(q["text"] for q in open_q)
        print(f"\n--- turn {len(reports)}: {b['report']['decisionStatus']} · mode {b['report'].get('mode')} · {len(open_q)} open questions")
        for t in b["trace"]:
            print(f"    {t['status']:5} {t['step']}: {t.get('detail', '')}")
        return open_q

    open_q = turn()
    for round_ in range(2):  # answer up to two rounds of questions
        if not open_q:
            break
        answers = [{"id": q.get("id"), "question": q["text"], **answer_for(q["text"])} for q in open_q]
        msgs.append({"role": "user", "content": message_for(answers, EXTRA if round_ == 0 else "")})
        open_q = turn(answers=answers)
    msgs.append({"role": "user", "content": FINAL})
    turn()

    rep = reports[-1]["report"]
    text = json.dumps(rep, ensure_ascii=False).lower() + " " + reports[-1]["reply"].lower()
    dup = [q for i, q in enumerate(asked) if any(_same(q, p) for p in asked[:i])]
    checks = {
        "No repeated questions": not dup,
        "Answers used (port, contact, dust, speed, formulation change)": all(k in text for k in ("12 mm", "contact", "dust", "60,000", "monthly")),
        "Final-answer request: no question block": rep.get("mode") == "final" and not [q for q in rep["questions"] if q.get("status") == "open" and q.get("askedTurn") == len(reports)],
        "Single port handled (access check passes on the concept)": any(ch["id"] == "access_points" and ch["status"] == "pass" for ch in rep["premiseChecks"]),
        "Citations verified": all(ct["check"] in ("verified", "visual_note") for r in rep["recommendations"] for ct in r["citations"]),
        "Status provisional, assumptions listed": rep["decisionStatus"] == "provisional" and bool(rep.get("assumptions") or rep.get("pointsToConfirm")),
    }
    print("\n=== Retest checklist ===")
    for k, ok in checks.items():
        print(f"  {'PASS' if ok else 'FAIL'}  {k}")
    if dup:
        print("  repeated:", dup)
    print(f"  placeholders in final report: {text.count(PLACEHOLDER.lower())}")
    print(f"\nPrimary: {[r['method'] for r in rep['recommendations'] if r['role'] == 'primary']}")
    print(f"Concept: {rep['concept']['summary']}")
    print("Assumptions:", *rep.get("assumptions", []), sep="\n  - ")
    print("Points to confirm:", *rep.get("pointsToConfirm", []), sep="\n  - ")
    print("Feasibility:", *rep["feasibility"]["steps"], sep="\n  - ")
    sys.exit(0 if all(checks.values()) else 1)


def _same(a: str, b: str) -> bool:
    from app.services.ledger import similar

    return similar(a, b)


if __name__ == "__main__":
    main()
