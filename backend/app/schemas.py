"""Pydantic mirror of frontend/src/lib/report.ts. Keep the two in sync."""

from typing import Literal, Optional

from pydantic import BaseModel, Field

SourceId = Literal["S01", "S02", "S03", "S04", "S05", "S06", "EXT"]
CheckStatus = Literal["verified", "visual_note", "unverified", "failed"]
DecisionStatus = Literal["provisional", "insufficient", "out_of_scope"]
MethodId = Literal["NIR", "MIR_ATR", "RAMAN", "FLUO", "UVVIS"]


class Citation(BaseModel):
    source: SourceId
    page: str  # "10", "14–15", "Table 1 (p.6)"
    quote: Optional[str] = None
    url: Optional[str] = None
    check: CheckStatus = "unverified"
    # The cited passage shows this for another application than the customer's ("transfer assumption").
    transfer: Optional[bool] = None
    application: Optional[str] = None


class Recommendation(BaseModel):
    method: str
    methodIds: list[MethodId] = Field(default_factory=list)
    role: Literal["primary", "comparison", "combination", "not_recommended"]
    reason: str
    citations: list[Citation] = Field(default_factory=list)


class PremiseCheck(BaseModel):
    id: str
    label: str
    status: Literal["pass", "flag", "fail"]
    detail: str
    citations: list[Citation] = Field(default_factory=list)


class Requirements(BaseModel):
    stated: list[str]
    unknowns: list[str]
    factTurns: list[int] = Field(default_factory=list)  # client turn (1 = enquiry) each stated fact was quoted from


# Question ledger: every question asked in the conversation keeps its status, so it is never re-asked.
# answered = the customer gave the fact; answered_unknown = the customer does not know it; declined = the
# customer will not answer; moved_to_experiment = an unknown answer turned into a feasibility step.
QuestionStatus = Literal["open", "answered", "answered_unknown", "declined", "moved_to_experiment"]


class Question(BaseModel):
    text: str
    impact: Optional[Literal["method", "setup", "acceptance"]] = None
    id: Optional[str] = None
    status: QuestionStatus = "open"
    answer: Optional[str] = None
    askedTurn: Optional[int] = None
    answeredTurn: Optional[int] = None


class Concept(BaseModel):
    summary: str
    probe: Optional[str] = None
    location: Optional[str] = None
    fiberLink: Optional[str] = None
    analyzer: Optional[str] = None
    citations: list[Citation] = Field(default_factory=list)


class SpectralRange(BaseModel):
    summary: str
    citations: list[Citation] = Field(default_factory=list)


class Feasibility(BaseModel):
    steps: list[str]
    decisionBasis: str


class Report(BaseModel):
    scenarioId: Optional[str] = None
    title: str
    origin: Literal["live", "cached", "reference", "demo"] = "live"
    originNote: Optional[str] = None
    generatedAt: Optional[str] = None
    decisionStatus: DecisionStatus
    requirements: Requirements
    questions: list[Question]
    recommendations: list[Recommendation]
    concept: Concept
    spectralRange: SpectralRange
    risks: list[str]
    feasibility: Feasibility
    premiseChecks: list[PremiseCheck] = Field(default_factory=list)
    sources: list[Citation]
    # "final": the customer asked for an answer without further questions; open points become
    # assumptions and points to confirm instead of a question block.
    mode: Literal["draft", "final"] = "draft"
    assumptions: list[str] = Field(default_factory=list)
    pointsToConfirm: list[str] = Field(default_factory=list)


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=8000)


class TraceStep(BaseModel):
    step: str
    status: Literal["ok", "warn", "fail", "skipped"]
    ms: Optional[float] = None
    detail: Optional[str] = None


class Answer(BaseModel):
    """An answer bound to one ledger question (the UI's per-question input)."""

    id: Optional[str] = None
    question: str = Field(min_length=1, max_length=1000)
    status: Literal["answered", "answered_unknown", "declined"]
    answer: Optional[str] = Field(default=None, max_length=2000)


class AssessRequest(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1, max_length=40)
    scenarioId: Optional[str] = None
    answers: list[Answer] = Field(default_factory=list, max_length=20)
    final: bool = False  # the customer asked for the final answer, no more questions


class AssessResponse(BaseModel):
    reply: str
    report: Report
    trace: list[TraceStep] = Field(default_factory=list)


# Template-compatible endpoint (Streamlit chat / eval app in the architecture diagram).
class QueryRequest(BaseModel):
    q: str = Field(min_length=1, max_length=8000)
    thread_id: Optional[str] = "default_user"
