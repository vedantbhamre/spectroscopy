from typing import Optional, TypedDict


class AgentState(TypedDict, total=False):
    messages: list[dict]  # full conversation, sent by the client each turn
    scenario_id: Optional[str]
    gate_flags: list[str]  # non-blocking premise flags from the safety gate
    intent: str  # "assessment" | "conversational"
    queries: list[str]
    facts: dict
    documents: list[dict]
    checks: list[dict]
    report: Optional[dict]  # kept by MemorySaver between turns of a thread
    reply: str
    trace: list[dict]  # reset by the API each turn
