from typing import Optional, TypedDict


class AgentState(TypedDict, total=False):
    messages: list[dict]  # full conversation, sent by the client each turn
    scenario_id: Optional[str]
    gate_flags: list[str]  # non-blocking premise flags from the safety gate
    answers: list[dict]  # answers bound to ledger questions by the UI (schemas.Answer)
    final_mode: bool  # the customer asked for the answer without further questions
    ledger: list[dict]  # every question asked so far, with status and answer (schemas.Question)
    validation: dict  # what the deterministic validators changed in this turn (numbers, claims, sections, …)
    intent: str  # "assessment" | "conversational"
    queries: list[str]
    facts: dict
    documents: list[dict]
    checks: list[dict]
    report: Optional[dict]  # kept by MemorySaver between turns of a thread
    reply: str
    trace: list[dict]  # reset by the API each turn
