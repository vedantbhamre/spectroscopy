"""Question ledger: every clarification question keeps an id and a status across the conversation.

Rules (test review, Fix A):
- an answered, unknown or declined question is never asked again;
- an "unknown" answer moves into the feasibility plan (the experiment establishes it);
- new questions ask only for customer facts (process, access, constraints, available data, requirements),
  never for the assistant's own decision, a method or equipment choice, or a new purchase;
- at most MAX_OPEN open questions, ranked by whether the answer could change the method or the setup;
- final-report mode (the customer asks for the answer): no question block; open points become
  "points to confirm".
Everything here is deterministic; the LLM only proposes questions and binds free-text answers.
"""

import re

from app.schemas import Answer, Question
from app.services.citations import normalise

MAX_OPEN = 5

_STOP = set("a an and are as at be by can do does for from has have how in is it its of on or the this to was what when where which who will with would you your".split())

# Questions that ask the customer to make the assistant's decision ("which probe fits best?").
_ASSISTANT_DECISION = re.compile(
    r"\b(which|what)\s+(\w+\s+){0,2}(method|probe|technique|configuration|fib(er|re)|wavelength|band|sensor|analy[sz]er|spectrometer)s?\s+"
    r"(would|should|will|fits?|is\s+(best|most|better|suitable|appropriate|optimal)|do\s+you\s+recommend)\b"
    r"|\bshould\s+(we|i|the assistant|afs)\s+(use|recommend|choose|select|combine)\b"
    r"|\bdo\s+you\s+(want|prefer)\s+(us|me)\s+to\s+(recommend|choose|select)\b"
    # asks the customer to choose a method or equipment
    r"|\b(which|what)\s+(\w+\s+){0,2}(method|probe|technique|sensor|spectrometer|analy[sz]er|instrument)s?\s+(do|would)\s+you\s+(prefer|want|like|choose)\b"
    r"|\b(do|would)\s+you\s+(prefer|want|like)\s+(to\s+use\s+)?(nir|mir|raman|uv|fluorescence|atr)\b"
    # asks the customer to buy, acquire or install new equipment
    r"|\b(can|could|would|will)\s+you\s+(acquire|buy|purchase|order|procure|rent|lease|invest\s+in|install\s+a\s+new)\b"
    r"|\b(are|is)\s+(you|the\s+customer)\s+(willing|able|prepared)\s+to\s+(buy|purchase|acquire|invest|procure)\b"
    r"|\bbudget\s+(for|to)\s+(buy|purchase|acquire)\b",
    re.I,
)
_NUMBERING = re.compile(r"^\s*(?:q?\d+[.):]|[-•*])\s*", re.I)
IMPACT_RANK = {"method": 0, "setup": 1, "acceptance": 2, None: 3}

# The customer asks for the answer now ("give me the solution, no more questions").
_FINAL_REQUEST = re.compile(
    r"\bno\s+(more|further)\s+questions\b|\bwithout\s+(any\s+)?(more|further)\s+questions\b|\bfinal\s+(answer|report|assessment|recommendation)\b"
    r"|\b(give|tell|send)\s+me\s+the\s+(solution|answer|recommendation|final)\b|\bjust\s+(give|tell)\s+me\b|\bstop\s+asking\b",
    re.I,
)


def wants_final(text: str) -> bool:
    return bool(_FINAL_REQUEST.search(text or ""))


def asks_assistant_decision(text: str) -> bool:
    return bool(_ASSISTANT_DECISION.search(text or ""))


def _words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", normalise(text)) if w not in _STOP and len(w) > 2}


def similar(a: str, b: str, threshold: float = 0.5) -> bool:
    """Same question in other words: high word overlap relative to the shorter question."""
    wa, wb = _words(a), _words(b)
    if not wa or not wb:
        return normalise(a) == normalise(b)
    return len(wa & wb) / min(len(wa), len(wb)) >= threshold


def covered(text: str, by: list[str], threshold: float = 0.6) -> bool:
    """Most of the text's words appear somewhere in the given texts (an answer already listed as facts)."""
    w = _words(text)
    pool = set().union(*(_words(b) for b in by)) if by else set()
    return bool(w) and len(w & pool) / len(w) >= threshold


def from_report(report: dict | None) -> list[Question]:
    """The previous report's questions are the ledger; older reports without ids get them assigned."""
    out = []
    legacy = {"unknown": "answered_unknown", "moved": "moved_to_experiment"}
    for i, q in enumerate((report or {}).get("questions") or [], 1):
        q = Question(**{**q, "status": legacy.get(q.get("status"), q.get("status") or "open"), "text": clean(q.get("text", ""))})
        out.append(q if q.id else q.model_copy(update={"id": f"q{i}"}))
    return out


def _next_id(ledger: list[Question]) -> str:
    nums = [int(m.group(1)) for q in ledger if q.id and (m := re.fullmatch(r"q(\d+)", q.id))]
    return f"q{max(nums, default=0) + 1}"


def apply_answers(ledger: list[Question], answers: list[Answer], turn: int) -> tuple[list[Question], int]:
    """Bind answers to ledger entries by id, else by question text; unmatched answers add a closed entry."""
    ledger = [q.model_copy() for q in ledger]
    bound = 0
    for a in answers:
        target = next((q for q in ledger if a.id and q.id == a.id), None) or next((q for q in ledger if similar(q.text, a.question, 0.8)), None)
        if target is None:
            target = Question(text=a.question, id=_next_id(ledger), askedTurn=turn)
            ledger.append(target)
        if target.status != "open" and target.status == a.status and target.answer == a.answer:
            continue
        target.status = a.status  # answered | answered_unknown | declined
        target.answer = (a.answer or "").strip() or None
        target.answeredTurn = turn
        bound += 1
    return ledger, bound


def closed(ledger: list[Question]) -> list[Question]:
    return [q for q in ledger if q.status != "open"]


def merge_new(ledger: list[Question], proposed: list[dict], turn: int, final: bool) -> tuple[list[Question], dict]:
    """Add the responder's proposed questions that are new, about customer facts, and within the cap."""
    ledger = [q.model_copy() for q in ledger]
    stats = {"repeated": 0, "assistant_decision": 0, "over_cap": 0, "added": 0}
    if final:
        return ledger, stats
    proposed = sorted((r for r in proposed if isinstance(r, dict)), key=lambda r: IMPACT_RANK.get(r.get("impact"), 3))
    for raw in proposed:
        text = clean(str(raw.get("text") or ""))
        if not text:
            continue
        if any(similar(text, q.text) for q in ledger):
            stats["repeated"] += 1
            continue
        if asks_assistant_decision(text):
            stats["assistant_decision"] += 1
            continue
        if sum(q.status == "open" for q in ledger) >= MAX_OPEN:
            stats["over_cap"] += 1
            continue
        impact = raw.get("impact") if raw.get("impact") in ("method", "setup", "acceptance") else None
        ledger.append(Question(text=text, impact=impact, id=_next_id(ledger), askedTurn=turn))
        stats["added"] += 1
    return ledger, stats


def clean(text: str) -> str:
    """Question text without a leading number or bullet: the ledger order is the only numbering."""
    return _NUMBERING.sub("", text.strip()).strip()


def move_unknowns(ledger: list[Question], steps: list[str], risks: list[str]) -> tuple[list[Question], list[str]]:
    """'Unknown' answers become something the first experiment establishes (status 'moved')."""
    steps = list(steps)
    plan = " ".join(steps + risks)
    for q in ledger:
        if q.status != "answered_unknown":
            continue
        if not similar(q.text, plan, 0.6):
            steps.append(f"Establish in the first measurements what the customer could not yet say: {q.text.rstrip('?')}.")
        q.status = "moved_to_experiment"
    return ledger, steps


def ledger_for_prompt(ledger: list[Question]) -> list[dict]:
    return [{"id": q.id, "question": q.text, "status": q.status, **({"answer": q.answer} if q.answer else {})} for q in ledger]
