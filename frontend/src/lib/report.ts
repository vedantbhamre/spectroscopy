import { z } from "zod";
import { sourceShort, sourceTitle } from "./sources";

// Contract between the assessment pipeline (engine + LLM compose) and the UI.
// Section names follow AFS_Examples_and_Reference.docx §3 "Answer structure".

export const SourceId = z.enum(["S01", "S02", "S03", "S04", "S05", "S06", "EXT"]);

export const Citation = z.object({
  source: SourceId,
  page: z.string(), // "10", "14–15", "Table 1 (p.6)"
  quote: z.string().optional(),
  url: z.string().url().optional(), // required for EXT by the brief
  /** Result of the citation verifier (quote found on cited page). */
  check: z.enum(["verified", "visual_note", "unverified", "failed"]).default("unverified"),
  /** The cited passage shows this for another application ("transfer assumption"). */
  transfer: z.boolean().optional(),
  application: z.string().optional(),
});
export type Citation = z.infer<typeof Citation>;

export const DecisionStatus = z.enum(["provisional", "insufficient", "out_of_scope"]);
export type DecisionStatus = z.infer<typeof DecisionStatus>;

export const Recommendation = z.object({
  method: z.string(),
  methodIds: z.array(z.enum(["NIR", "MIR_ATR", "RAMAN", "FLUO", "UVVIS"])).default([]),
  role: z.enum(["primary", "comparison", "combination", "not_recommended"]),
  reason: z.string(),
  citations: z.array(Citation).default([]),
});

export const PremiseCheck = z.object({
  id: z.string(),
  label: z.string(),
  status: z.enum(["pass", "flag", "fail"]),
  detail: z.string(),
  citations: z.array(Citation).default([]),
});
export type PremiseCheck = z.infer<typeof PremiseCheck>;

export const QuestionStatus = z.enum(["open", "answered", "answered_unknown", "declined", "moved_to_experiment"]);
export type QuestionStatus = z.infer<typeof QuestionStatus>;

export const Question = z.object({
  text: z.string(),
  impact: z.enum(["method", "setup", "acceptance"]).optional(),
  id: z.string().optional(),
  status: QuestionStatus.optional(), // missing = "open" (reports from before the ledger)
  answer: z.string().optional(),
  askedTurn: z.number().optional(),
  answeredTurn: z.number().optional(),
});
export type Question = z.infer<typeof Question>;

export const Report = z.object({
  scenarioId: z.string().optional(),
  title: z.string(),
  /** Where the content came from — shown as a badge. "demo" = placeholder from the mock, not an assessment. */
  origin: z.enum(["live", "cached", "reference", "demo"]),
  originNote: z.string().optional(),
  generatedAt: z.string().optional(),
  decisionStatus: DecisionStatus,
  requirements: z.object({
    stated: z.array(z.string()),
    unknowns: z.array(z.string()),
    /** Client turn (1 = enquiry) each stated fact was quoted from. */
    factTurns: z.array(z.number()).optional(),
  }),
  /** The question ledger: every question asked so far, with its status. Only "open" ones are still asked. */
  questions: z.array(Question),
  recommendations: z.array(Recommendation),
  concept: z.object({
    summary: z.string(),
    probe: z.string().optional(),
    location: z.string().optional(),
    fiberLink: z.string().optional(),
    analyzer: z.string().optional(),
    citations: z.array(Citation).default([]),
  }),
  spectralRange: z.object({ summary: z.string(), citations: z.array(Citation).default([]) }),
  risks: z.array(z.string()),
  feasibility: z.object({ steps: z.array(z.string()), decisionBasis: z.string() }),
  premiseChecks: z.array(PremiseCheck).default([]),
  sources: z.array(Citation),
  /** "final": the customer asked for the answer without further questions. */
  mode: z.enum(["draft", "final"]).optional(),
  assumptions: z.array(z.string()).optional(),
  pointsToConfirm: z.array(z.string()).optional(),
});
export type Report = z.infer<typeof Report>;

// Chat contract: the UI sends the whole conversation, the backend answers with a reply,
// a full report version and the trace of the steps it ran.

export const ChatMessage = z.object({
  role: z.enum(["user", "assistant"]),
  content: z.string().min(1).max(8000),
});
export type ChatMessage = z.infer<typeof ChatMessage>;

export const TraceStep = z.object({
  step: z.string(),
  status: z.enum(["ok", "warn", "fail", "skipped"]),
  ms: z.number().optional(),
  detail: z.string().optional(),
});
export type TraceStep = z.infer<typeof TraceStep>;

/** An answer bound to one ledger question (one input box per question in the UI). */
export const Answer = z.object({
  id: z.string().optional(),
  question: z.string().min(1).max(1000),
  status: z.enum(["answered", "answered_unknown", "declined"]),
  answer: z.string().max(2000).optional(),
});
export type Answer = z.infer<typeof Answer>;

export const AssessRequest = z.object({
  messages: z.array(ChatMessage).min(1).max(40),
  scenarioId: z.string().optional(),
  answers: z.array(Answer).max(20).optional(),
  final: z.boolean().optional(),
});
export type AssessRequest = z.infer<typeof AssessRequest>;

export const AssessResponse = z.object({
  reply: z.string(),
  report: Report,
  trace: z.array(TraceStep).default([]),
});
export type AssessResponse = z.infer<typeof AssessResponse>;

export const statusLabel: Record<DecisionStatus, string> = {
  provisional: "Provisional feasibility assessment",
  insufficient: "Insufficient information",
  out_of_scope: "Outside the supported scope",
};

// Readable citation: "Process Control slides p.13"; the full form names the document and its ID for cross-checking.
export const citeText = (c: Pick<Citation, "source" | "page">) =>
  c.page.startsWith("Table") ? `${sourceShort(c.source)}, ${c.page}` : `${sourceShort(c.source)} p.${c.page}`;
export const citeFull = (c: Pick<Citation, "source" | "page">) =>
  `${sourceTitle(c.source)} (${c.source}), ${c.page.startsWith("Table") ? c.page : `page ${c.page}`}`;

export const statusOf = (q: Question): QuestionStatus => q.status ?? "open";
export const openQuestions = (r: Pick<Report, "questions" | "mode">) => (r.mode === "final" ? [] : r.questions.filter((q) => statusOf(q) === "open"));
export const closedQuestions = (r: Pick<Report, "questions">) => r.questions.filter((q) => statusOf(q) !== "open");

export const questionStatusLabel: Record<QuestionStatus, string> = {
  open: "open",
  answered: "answered",
  answered_unknown: "answered: unknown",
  declined: "declined",
  moved_to_experiment: "moved to the experiment",
};

/** Question text without a leading number or bullet: the ledger order is the only numbering. */
export const questionText = (q: Pick<Question, "text">) => q.text.replace(/^\s*(?:q?\d+[.):]|[-•*])\s*/i, "");
