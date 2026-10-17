import { z } from "zod";

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

export const Report = z.object({
  scenarioId: z.string().optional(),
  title: z.string(),
  /** Where the content came from — shown as a badge. */
  origin: z.enum(["live", "cached", "reference"]),
  originNote: z.string().optional(),
  generatedAt: z.string().optional(),
  decisionStatus: DecisionStatus,
  requirements: z.object({ stated: z.array(z.string()), unknowns: z.array(z.string()) }),
  questions: z.array(z.object({ text: z.string(), impact: z.enum(["method", "setup", "acceptance"]).optional() })),
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
});
export type Report = z.infer<typeof Report>;

export const statusLabel: Record<DecisionStatus, string> = {
  provisional: "Provisional feasibility assessment",
  insufficient: "Insufficient information",
  out_of_scope: "Outside the supported scope",
};

export const citeText = (c: Pick<Citation, "source" | "page">) =>
  c.page.startsWith("Table") ? `${c.source} ${c.page}` : `${c.source} p.${c.page}`;
