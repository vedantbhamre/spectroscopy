import { type Citation, type Report, citeText, closedQuestions, openQuestions, questionStatusLabel, questionText, statusLabel, statusOf } from "./report";

const cites = (cs: Citation[]) => (cs.length ? ` [${cs.map(citeText).join("; ")}]` : "");

export function toMarkdown(r: Report, enquiry: string): string {
  const L: string[] = [];
  L.push(`# ${r.title}`, "");
  if (r.originNote) L.push(`> ${r.originNote}`, "");
  L.push(`**Decision status:** ${statusLabel[r.decisionStatus]}`, "");
  if (r.answer) {
    L.push("## Answer", "", r.answer.text + cites(r.answer.citations), "");
    if (r.answer.sayInstead) L.push(`**What you can say instead:** ${r.answer.sayInstead}`, "");
  }
  L.push("## Enquiry", "", enquiry, "");
  L.push("## Requirements", "", "**Stated by the client**", ...r.requirements.stated.map((s) => `- ${s}`), "");
  L.push("**Key unknowns**", ...r.requirements.unknowns.map((s) => `- ${s}`), "");
  L.push("## Clarification questions", "", ...openQuestions(r).map((q, i) => `${i + 1}. ${questionText(q)}`), "");
  if (closedQuestions(r).length) L.push("**Answered in the conversation**", ...closedQuestions(r).map((q) => `- ${q.text} (${questionStatusLabel[statusOf(q)]})${q.answer ? `: ${q.answer}` : ""}`), "");
  if (r.assumptions?.length) L.push("## Assumptions", "", ...r.assumptions.map((s) => `- ${s}`), "");
  if (r.pointsToConfirm?.length) L.push("## Points to confirm", "", ...r.pointsToConfirm.map((s) => `- ${s}`), "");
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

const plainRole = { primary: "Primary candidate", comparison: "Comparison candidate", combination: "Combination, test after single methods", not_recommended: "Not recommended" } as const;
const plainImpact = { method: "could change the method", setup: "could change the setup", acceptance: "sets acceptance" } as const;
const plainCheck = { pass: "Pass", flag: "Flag", fail: "Fail" } as const;

/** Clean plain-text export (no Markdown syntax), suitable for pasting into email or a ticket. */
export function toPlainText(r: Report, transcript: string): string {
  const L: string[] = [];
  const section = (title: string) => L.push("", "", title, "─".repeat(title.length), "");
  const bullets = (items: string[]) => (items.length ? items.forEach((s) => L.push(`• ${s}`)) : L.push("• None"));

  const heading = r.title;
  L.push(heading, "═".repeat(Math.min(heading.length, 72)), "");
  L.push(`Decision status: ${statusLabel[r.decisionStatus]}`);
  if (r.originNote) L.push(`Note: ${r.originNote}`);
  if (r.answer) {
    section("Answer");
    L.push(r.answer.text + cites(r.answer.citations));
    if (r.answer.sayInstead) L.push("", `What you can say instead: ${r.answer.sayInstead}`);
  }

  if (transcript.trim()) {
    section("Customer conversation");
    L.push(transcript.trim());
  }

  if (r.premiseChecks.length) {
    section("Premise checks");
    for (const c of r.premiseChecks) L.push(`• ${plainCheck[c.status]}: ${c.label}. ${c.detail}${cites(c.citations)}`);
  }

  section("Requirements");
  L.push("Stated by the client");
  bullets(r.requirements.stated);
  L.push("", "Unknown, not assumed");
  bullets(r.requirements.unknowns);

  section("Clarification questions");
  const open = openQuestions(r);
  if (open.length) open.forEach((q, i) => L.push(`${i + 1}. ${questionText(q)}${q.impact ? ` (${plainImpact[q.impact]})` : ""}`));
  else L.push(r.mode === "final" ? "None (final report)." : "None.");
  if (closedQuestions(r).length) {
    L.push("", "Answered in the conversation");
    closedQuestions(r).forEach((q) => L.push(`• ${q.text} (${questionStatusLabel[statusOf(q)]})${q.answer ? `: ${q.answer}` : ""}`));
  }
  if (r.assumptions?.length || r.pointsToConfirm?.length) {
    section("Assumptions and points to confirm");
    L.push("Assumptions");
    bullets(r.assumptions ?? []);
    L.push("", "Points to confirm");
    bullets(r.pointsToConfirm ?? []);
  }

  section("Recommendation");
  if (r.recommendations.length === 0) {
    L.push("No method is recommended on the known facts. The clarification questions and the first step come before a method choice.");
  } else {
    r.recommendations.forEach((rec, i) => {
      if (i) L.push("");
      L.push(`${rec.method} (${plainRole[rec.role]})`, `${rec.reason}${cites(rec.citations)}`);
    });
  }

  section("Measurement concept");
  L.push(r.concept.summary + cites(r.concept.citations));
  const parts: [string, string | undefined][] = [["Analyser", r.concept.analyzer], ["Fibre link", r.concept.fiberLink], ["Probe", r.concept.probe], ["Location", r.concept.location]];
  const shown = parts.filter(([, v]) => v);
  if (shown.length) {
    L.push("");
    shown.forEach(([k, v]) => L.push(`• ${k}: ${v}`));
  }

  section("Spectral range");
  L.push(r.spectralRange.summary + cites(r.spectralRange.citations));

  section("Risks and uncertainty");
  bullets(r.risks);

  section("First feasibility experiment");
  r.feasibility.steps.forEach((s, i) => L.push(`${i + 1}. ${s}`));
  L.push("", `Decision basis: ${r.feasibility.decisionBasis}`);

  section("Sources");
  if (r.sources.length === 0) L.push("No sources attached.");
  for (const c of r.sources) L.push(`• [${citeText(c)}]${c.quote ? ` “${c.quote}”` : ""}${c.url ? ` ${c.url}` : ""}`);

  return L.join("\n").trim() + "\n";
}
