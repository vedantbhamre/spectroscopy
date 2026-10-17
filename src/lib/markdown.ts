import { type Citation, type Report, citeText, statusLabel } from "./report";

const cites = (cs: Citation[]) => (cs.length ? ` [${cs.map(citeText).join("; ")}]` : "");

export function toMarkdown(r: Report, enquiry: string): string {
  const L: string[] = [];
  L.push(`# ${r.scenarioId ? `${r.scenarioId} · ` : ""}${r.title}`, "");
  if (r.originNote) L.push(`> ${r.originNote}`, "");
  L.push(`**Decision status:** ${statusLabel[r.decisionStatus]}`, "");
  L.push("## Enquiry", "", enquiry, "");
  L.push("## Requirements", "", "**Stated by the client**", ...r.requirements.stated.map((s) => `- ${s}`), "");
  L.push("**Key unknowns**", ...r.requirements.unknowns.map((s) => `- ${s}`), "");
  L.push("## Clarification questions", "", ...r.questions.map((q, i) => `${i + 1}. ${q.text}`), "");
  L.push("## Recommendation", "");
  for (const rec of r.recommendations) L.push(`- **${rec.method}** (${rec.role.replace("_", " ")}). ${rec.reason}${cites(rec.citations)}`);
  L.push("", "## Measurement concept", "", r.concept.summary + cites(r.concept.citations), "");
  L.push("## Spectral range", "", r.spectralRange.summary + cites(r.spectralRange.citations), "");
  L.push("## Risks and uncertainty", "", ...r.risks.map((s) => `- ${s}`), "");
  L.push("## First feasibility experiment", "", ...r.feasibility.steps.map((s, i) => `${i + 1}. ${s}`), "");
  L.push(`**Decision basis:** ${r.feasibility.decisionBasis}`, "");
  if (r.premiseChecks.length) {
    L.push("## Premise checks", "");
    for (const c of r.premiseChecks) L.push(`- [${c.status.toUpperCase()}] ${c.label}: ${c.detail}${cites(c.citations)}`);
    L.push("");
  }
  L.push("## Sources", "");
  for (const c of r.sources) L.push(`- ${citeText(c)}${c.quote ? ` — “${c.quote}”` : ""}${c.url ? ` (${c.url})` : ""}`);
  return L.join("\n") + "\n";
}
