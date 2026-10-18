import json
import re

from app.agents import prompts
from app.agents.nodes.common import client_turns, customer_words, step, transcript
from app.agents.state import AgentState
from app.knowledge.applications import DOMAINS
from app.gateway import chat, parse_json
from app.schemas import Answer
from app.services import ledger as L
from app.services.citations import contains, normalise
from app.services.premises import Facts, detect, resolved_by_facts


# Answers that state no fact: they hand the decision back or repeat an earlier answer.
_NON_FACT = re.compile(r"\b(don'?t know|do not know|not sure|no idea|please recommend|recommend it|(hoped|want|expect) you (would|to)|"
                       r"that'?s (for|what) (you|we hoped)|up to you|same as before|as (i|we) said)\b", re.I)


def _quoted_turn(quote: str, turns_n: list[str]) -> int | None:
    """Turn (1-based) whose words contain the quote: verbatim (with "..." elisions), else nearly all its
    content words in that one turn, so a reworded join of two phrases still counts but invented facts do not."""
    q = normalise(quote)
    if len(q) < 3:
        return None
    for i, t in enumerate(turns_n, 1):
        if contains(t, q):
            return i
    words = set(re.findall(r"[a-z0-9]+", q)) - L._STOP
    if len(words) < 3:
        return None
    for i, t in enumerate(turns_n, 1):
        tw = set(re.findall(r"[a-z0-9]+", t))
        if len(words & tw) / len(words) >= 0.85:
            return i
    return None


def analyst_node(state: AgentState) -> dict:
    """Separate stated facts from unknowns and bind answers to the question ledger.

    A fact is kept only if its quote is the client's own words, from any turn of the conversation
    (enquiry and every answer); each fact is tagged with the turn it came from.
    """
    trace = list(state.get("trace", []))
    turns = [customer_words(t) for t in client_turns(state["messages"])]
    turn = len(turns)
    turns_n = [normalise(t) for t in turns]  # quotes must be the customer's words, never the echoed question text

    with step({"trace": trace}, "Separate facts and unknowns") as rec:
        # 1. Answers the UI bound to questions (one input per question) are authoritative.
        ledger, bound_ui = L.apply_answers(L.from_report(state.get("report")), [Answer(**a) for a in state.get("answers") or []], turn)
        open_q = [q for q in ledger if q.status == "open"]

        res = chat(
            [{"role": "system", "content": prompts.ANALYST.replace("{open_questions}", json.dumps(L.ledger_for_prompt(open_q), ensure_ascii=False) or "[]")
                                                     .replace("{domains}", " | ".join(DOMAINS))},
             {"role": "user", "content": transcript(state["messages"])}],
            json_mode=True, temperature=0, feature="analyst", max_tokens=2000,
        )
        data = parse_json(res.text)

        # 2. Free-text answers: the model binds them to open questions; kept only if quoted from the latest message.
        llm_answers = []
        for a in data.get("answers") or []:
            status = {"unknown": "answered_unknown"}.get(a.get("status"), a.get("status")) if isinstance(a, dict) else None
            if status not in ("answered", "answered_unknown", "declined"):
                continue
            q = next((q for q in open_q if q.id == a.get("id")), None)
            if q and a.get("quote") and _quoted_turn(a["quote"], turns_n[-1:]):
                llm_answers.append(Answer(id=q.id, question=q.text, status=status, answer=a.get("answer") or a.get("quote")))
        ledger, bound_llm = L.apply_answers(ledger, llm_answers, turn)

        # 3. Stated facts, quote-checked against every client turn.
        stated, stated_turns, dropped = [], [], 0
        for item in data.get("stated", []):
            item = item or {}
            t = _quoted_turn(item.get("quote", ""), turns_n)
            if t:
                stated.append(item.get("fact") or item["quote"])
                stated_turns.append(t)
            else:
                dropped += 1
        # Every answered question is a fact in the customer's own answer words (never the question's wording).
        # Sentence by sentence: only what the facts do not already say, and never a non-answer ("please recommend it").
        for q in ledger:
            if q.status != "answered" or not q.answer:
                continue
            for s in re.split(r"(?<=[.!?;])\s+", q.answer.strip()):
                if _NON_FACT.search(s) and not re.search(r"\d", s):
                    continue
                if len(L._words(s)) >= 2 and not L.covered(s, stated):
                    stated.append(s.strip())
                    stated_turns.append(q.answeredTurn or turn)
        # One row per fact (normalised); raw question-answer pairs stay in the ledger, not in the requirements.
        seen: set[str] = set()
        uniq = [(f, t) for f, t in zip(stated, stated_turns) if not (normalise(f) in seen or seen.add(normalise(f)))]
        def same(a: str, b: str) -> bool:  # symmetric: a short fact is not a duplicate of a longer one that contains it
            wa, wb = L._words(a), L._words(b)
            return bool(wa and wb) and len(wa & wb) / len(wa | wb) >= 0.8

        uniq = [(f, t) for i, (f, t) in enumerate(uniq) if not any(same(f, g) for g, _ in uniq[:i])]
        stated, stated_turns = [f for f, _ in uniq], [t for _, t in uniq]

        # Unknowns persist from the previous report until a customer answer or a new fact resolves them.
        prev = (state.get("report") or {}).get("requirements") or {}
        latest = [f for f, t in zip(stated, stated_turns) if t == turn and turn > 1]
        settled_q = [q for q in ledger if q.status in ("answered", "declined")]

        def resolved(u: str) -> bool:
            return any(L.similar(u, q.text) for q in settled_q) or (bool(latest) and L.covered(u, latest, 0.7))

        raw_unknowns = [u if isinstance(u, dict) else {"text": u} for u in data.get("unknowns", []) if isinstance(u, (str, dict))]
        unknowns = [str(u.get("text") or "").strip() for u in raw_unknowns]
        decisive = [str(u.get("text") or "").strip() for u in raw_unknowns if u.get("impact") == "method"]
        for u in prev.get("unknowns") or []:
            if u and not u.startswith("Not known yet") and not any(L.similar(u, x) for x in unknowns):
                unknowns.append(u)
        for u in prev.get("decisive") or []:
            if not any(L.similar(u, x) for x in decisive):
                decisive.append(u)
        unknowns = [u for u in unknowns if u and not resolved(u)]
        decisive = [u for u in decisive if u and not resolved(u)]

        facts = Facts(
            stated=stated,
            stated_turns=stated_turns,
            unknowns=unknowns,
            decisive_unknowns=decisive,
            target_variables=[t for t in data.get("target_variables", []) if isinstance(t, str)],
            methods_mentioned=[m for m in data.get("methods_requested", []) if m in ("NIR", "MIR_ATR", "RAMAN", "FLUO", "UVVIS")],
            fibers_mentioned=[f for f in data.get("fibers_mentioned", []) if isinstance(f, str)],
            fluorescent_target_named=data.get("fluorescent_target_named"),
            use_context=data.get("use_context") or "unknown",
            cites_study_as_proof=bool(data.get("cites_study_as_proof")),
            reuses_existing_calibration=bool(data.get("reuses_existing_calibration")),
            new_formulation_or_matrix=bool(data.get("new_formulation_or_matrix")),
            asks_for_certainty=bool(data.get("asks_for_certainty")),
            combination_requested=bool(data.get("combination_requested")),
            access_points=data.get("access_points") if isinstance(data.get("access_points"), int) else None,
            single_method_insufficient=bool(data.get("single_method_insufficient")),
            # Owned equipment and the optical appearance count only when quoted from the client.
            owned_equipment=[{"name": str(o.get("name") or ""), "method": o.get("method") if o.get("method") in ("NIR", "MIR_ATR", "RAMAN", "FLUO", "UVVIS") else None}
                             for o in data.get("owned_equipment") or [] if isinstance(o, dict) and _quoted_turn(o.get("quote", ""), turns_n)],
            optical_appearance=(oa.get("value") if isinstance(oa := data.get("optical_appearance"), dict) and oa.get("value") in ("clear", "opaque", "changing")
                                and _quoted_turn(oa.get("quote", ""), turns_n) else "unknown"),
            application_domain=data.get("application_domain") if data.get("application_domain") in DOMAINS else None,
            analyzer_remote=bool(data.get("analyzer_remote")),
            link_length_m=float(data["link_length_m"]) if isinstance(data.get("link_length_m"), (int, float)) else None,
        )
        facts = detect("\n\n".join(turns), facts, enquiry=turns[0] if turns else "")  # customer words only
        # A fact the customer has stated (turbidity in NTU, link length, ports) settles the unknowns about it.
        facts.unknowns = [u for u in facts.unknowns if not resolved_by_facts(u, facts)]
        facts.decisive_unknowns = [u for u in facts.decisive_unknowns if not resolved_by_facts(u, facts)]
        # Safety-gate premise flags (approval demand, immediate config, research as proof) feed the checks.
        gate = set(state.get("gate_flags") or [])
        if gate & {"approval_demand", "immediate_config"}:
            facts.asks_for_certainty = True
        if "research_as_proof" in gate:
            facts.cites_study_as_proof = True

        from_answers = sum(t > 1 for t in stated_turns)
        rec["detail"] = (f"{len(stated)} stated ({from_answers} from answers) · {len(facts.unknowns)} unknown"
                         + (f" · {bound_ui + bound_llm} answers bound to questions" if bound_ui + bound_llm else "")
                         + (f" · {dropped} unquoted dropped" if dropped else ""))
        if dropped:
            rec["status"] = "warn"
    return {"facts": facts.model_dump(), "ledger": [q.model_dump() for q in ledger], "trace": trace}
