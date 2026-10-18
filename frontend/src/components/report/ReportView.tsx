"use client";

import { AlertTriangle, Ban, CheckCircle2, CircleHelp, Download, FlaskConical, ShieldAlert, ShieldCheck, Copy, Check } from "lucide-react";
import { useState } from "react";
import { type Report, statusLabel, type PremiseCheck, openQuestions, closedQuestions, questionStatusLabel, questionText, statusOf } from "@/lib/report";
import { toPlainText } from "@/lib/markdown";
import type { MethodId } from "@/data/optics";
import { Citations, CitationChip } from "./CitationChip";
import { SetupSketch } from "./SetupSketch";
import { Button } from "../ui/button";
import { SpectralBand } from "../SpectralBand";

const statusStyle = {
  provisional: { cls: "border-accent/40 bg-accent/5 text-accent", icon: CheckCircle2 },
  insufficient: { cls: "border-warn/40 bg-warn/5 text-warn", icon: CircleHelp },
  out_of_scope: { cls: "border-bad/40 bg-bad/5 text-bad", icon: Ban },
};

const originLabel = {
  live: { text: "Live assessment", cls: "text-ok border-ok/40" },
  cached: { text: "Batch run", cls: "text-accent border-accent/40" },
  reference: { text: "Organiser example, not assistant output", cls: "text-violet border-violet/40" },
  demo: { text: "Demo placeholder", cls: "text-warn border-warn/50" },
};

const roleLabel = { primary: "Primary candidate", comparison: "Comparison candidate", combination: "Escalation: combination after single methods", not_recommended: "Not recommended" };
const roleStyle = { primary: "border-l-accent", comparison: "border-l-line-strong", combination: "border-l-violet", not_recommended: "border-l-bad" };
const impactLabel = { method: "could change the method", setup: "could change the setup", acceptance: "sets acceptance" };

export function ReportView({ report, transcript, toolbar }: { report: Report; transcript: string; toolbar?: React.ReactNode }) {
  const S = statusStyle[report.decisionStatus];
  const O = originLabel[report.origin];
  const methodIds = Array.from(new Set(report.recommendations.filter((r) => r.role !== "not_recommended").flatMap((r) => r.methodIds))) as MethodId[];
  const flagged = report.premiseChecks.filter((c) => c.status !== "pass");
  const open = openQuestions(report);
  const closed = closedQuestions(report);
  const assumptions = report.assumptions ?? [];
  const toConfirm = report.pointsToConfirm ?? [];
  const [copied, setCopied] = useState(false);

  const downloadPdf = () => {
    const previous = document.title;
    const restore = () => { document.title = previous; window.removeEventListener("afterprint", restore); };
    // The PDF file name comes from the report title ("silica-link-for-mir-atr-assessment.pdf").
    document.title = `${report.title.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 60) || "spectrasense"}-assessment`;
    window.addEventListener("afterprint", restore);
    window.print();
  };
  const copy = async () => {
    const text = toPlainText(report, transcript);
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      // Clipboard API is unavailable outside secure contexts (e.g. a LAN IP during a demo).
      const ta = document.createElement("textarea");
      ta.value = text;
      ta.style.position = "fixed";
      ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      ta.remove();
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <article className="print-report mx-auto max-w-3xl pb-24">
      <header className="pb-6">
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <span className={`rounded border px-2 py-0.5 font-medium ${O.cls}`}>{O.text}</span>
          {toolbar && <span className="print-hidden contents">{toolbar}</span>}
          <div className="print-hidden ml-auto flex gap-1.5">
            <Button size="sm" variant="ghost" onClick={copy} aria-live="polite">
              {copied ? <Check aria-hidden /> : <Copy aria-hidden />} {copied ? "Copied" : "Copy as text"}
            </Button>
            <Button size="sm" variant="outline" onClick={downloadPdf}>
              <Download aria-hidden /> Download PDF
            </Button>
          </div>
        </div>
        <div className="mt-4 rounded-xl bg-accent px-6 py-6 text-white">
          <h2 className="text-[28px] font-semibold leading-tight tracking-tight">{report.title}</h2>
          <div className="mt-4 inline-flex items-center gap-2 rounded-md bg-white px-3 py-1.5 text-sm font-semibold">
            <S.icon className={`h-4 w-4 ${S.cls.split(" ").pop()}`} aria-hidden />
            <span className={S.cls.split(" ").pop()}>{statusLabel[report.decisionStatus]}</span>
          </div>
          {report.originNote && <p className="mt-3 text-sm text-white/75">{report.originNote}</p>}
        </div>
      </header>

      {report.answer && (
        <section className="print-section border-t border-line py-7" aria-labelledby="answer-heading">
          <h2 id="answer-heading" className="text-lg font-semibold tracking-tight">Answer</h2>
          <p className="mt-3 border-l-4 border-l-accent pl-4 font-serif text-[18px] leading-relaxed text-ink">
            {report.answer.text} <Citations items={report.answer.citations} />
          </p>
          {report.answer.sayInstead && (
            <div className="mt-4 bg-panel-2 px-4 py-3">
              <p className="font-sans text-xs font-semibold uppercase tracking-wide text-ink-3">What you can say instead</p>
              <p className="mt-1 font-serif text-[15.5px] leading-relaxed text-ink">“{report.answer.sayInstead}”</p>
            </div>
          )}
        </section>
      )}

      {report.premiseChecks.length > 0 && (
        <Section title="Premise checks" hint="Checks on what the enquiry assumes, run before the answer is composed.">
          {flagged.length > 0 && (
            <p className="mb-3 font-sans text-sm font-medium text-warn">
              {flagged.length === 1 ? "1 assumption in the enquiry needs attention." : `${flagged.length} assumptions in the enquiry need attention.`}
            </p>
          )}
          <ul className="space-y-2">{report.premiseChecks.map((c) => <CheckRow key={c.id} c={c} />)}</ul>
        </Section>
      )}

      <Section title="Requirements">
        <div className="grid gap-6 md:grid-cols-2">
          <div>
            <h3 className="mb-2 flex items-center gap-1.5 font-sans text-sm font-semibold text-ok"><CheckCircle2 className="h-4 w-4" /> Stated by the client</h3>
            <ul className="space-y-1.5">
              {report.requirements.stated.map((s, i) => {
                const turn = report.requirements.factTurns?.[i];
                return (
                  <li key={s} className="border-l-2 border-ok/40 pl-3">
                    {s}
                    {turn && turn > 1 && <span className="ml-1.5 whitespace-nowrap rounded bg-panel-2 px-1.5 py-0.5 font-sans text-xs text-ink-3">answer, turn {turn}</span>}
                  </li>
                );
              })}
            </ul>
          </div>
          <div>
            <h3 className="mb-2 flex items-center gap-1.5 font-sans text-sm font-semibold text-warn"><CircleHelp className="h-4 w-4" /> Unknown, not assumed</h3>
            <ul className="space-y-1.5">{report.requirements.unknowns.map((s) => <li key={s} className="border-l-2 border-dashed border-warn/50 pl-3">{s}</li>)}</ul>
          </div>
        </div>
      </Section>

      <Section title="Clarification questions" hint={report.mode === "final" ? "Final report: the customer asked for the answer, so no further questions are asked." : "Only new questions; answered ones are never asked again. Questions that could change the method or setup come first."}>
        {open.length > 0 ? (
          <ol className="space-y-2.5">
            {open.map((q, i) => (
              <li key={q.id ?? q.text} className="flex gap-3">
                <span className="w-5 shrink-0 font-sans text-sm font-semibold text-accent">{i + 1}.</span>
                <span className="flex-1">{questionText(q)}</span>
                {q.impact && <span className="h-fit shrink-0 whitespace-nowrap rounded bg-panel-2 px-1.5 py-0.5 font-sans text-xs text-ink-2">{impactLabel[q.impact]}</span>}
              </li>
            ))}
          </ol>
        ) : (
          <p className="text-ink-3">{report.mode === "final" ? "None. Open points are listed under assumptions and points to confirm." : "No open questions."}</p>
        )}
        {closed.length > 0 && (
          <div className="mt-5">
            <h3 className="mb-2 font-sans text-sm font-semibold text-ink-2">Answered in the conversation</h3>
            <ul className="space-y-1.5 text-ink-2">
              {closed.map((q) => (
                <li key={q.id ?? q.text} className="border-l-2 border-line pl-3">
                  <span>{questionText(q)}</span>{" "}
                  <span className="whitespace-nowrap rounded bg-panel-2 px-1.5 py-0.5 font-sans text-xs text-ink-3">{questionStatusLabel[statusOf(q)]}</span>
                  {q.answer && <div className="text-ink">{q.answer}</div>}
                </li>
              ))}
            </ul>
          </div>
        )}
      </Section>

      {(assumptions.length > 0 || toConfirm.length > 0) && (
        <Section title="Assumptions and points to confirm" hint="What this assessment rests on without a customer fact or a verified source.">
          <div className="grid gap-6 md:grid-cols-2">
            <div>
              <h3 className="mb-2 font-sans text-sm font-semibold text-ink-2">Assumptions</h3>
              {assumptions.length ? <ul className="space-y-1.5">{assumptions.map((a) => <li key={a} className="border-l-2 border-dashed border-violet/50 pl-3">{a}</li>)}</ul> : <p className="text-ink-3">None.</p>}
            </div>
            <div>
              <h3 className="mb-2 font-sans text-sm font-semibold text-ink-2">Points to confirm</h3>
              {toConfirm.length ? <ul className="space-y-1.5">{toConfirm.map((a) => <li key={a} className="border-l-2 border-dashed border-warn/50 pl-3">{a}</li>)}</ul> : <p className="text-ink-3">None.</p>}
            </div>
          </div>
        </Section>
      )}

      <Section title="Recommendation">
        {report.recommendations.length === 0 ? (
          <p className="border-l-2 border-warn/60 pl-3 text-warn">No method is recommended on the known facts. The clarification questions and the first step come before a method choice.</p>
        ) : (
          <div className="space-y-4">
            {report.recommendations.map((r) => (
              <div key={r.method} className={`border-l-[3px] pl-4 ${roleStyle[r.role]}`}>
                <div className="font-sans text-xs font-medium text-ink-3">{roleLabel[r.role]}</div>
                <div className="font-sans text-lg font-semibold">{r.method}</div>
                <p className="mt-1 text-ink-2">{r.reason} <Citations items={r.citations} /></p>
                {r.limitations && r.limitations.length > 0 && (
                  <ul className="mt-2 space-y-1 font-sans text-sm text-warn">
                    {r.limitations.map((l) => <li key={l} className="flex gap-1.5"><AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden /> {l}</li>)}
                  </ul>
                )}
              </div>
            ))}
          </div>
        )}
      </Section>

      <Section title="Measurement concept">
        <SetupSketch analyzer={report.concept.analyzer} fiberLink={report.concept.fiberLink} probe={report.concept.probe} location={report.concept.location} />
        <p className="mt-3 text-ink-2">{report.concept.summary} <Citations items={report.concept.citations} /></p>
      </Section>

      <Section title="Spectral range">
        <p className="mb-4 text-ink-2">{report.spectralRange.summary} <Citations items={report.spectralRange.citations} /></p>
        <div className="font-sans"><SpectralBand key={methodIds.join()} highlight={methodIds} /></div>
      </Section>

      <Section title="Risks and uncertainty">
        <ul className="space-y-2">
          {report.risks.map((r) => (
            <li key={r} className="flex gap-2"><AlertTriangle className="mt-1 h-4 w-4 shrink-0 text-warn" aria-hidden />{r}</li>
          ))}
        </ul>
      </Section>

      <Section title="First feasibility experiment">
        <ol className="space-y-2.5">
          {report.feasibility.steps.map((s, i) => (
            <li key={i} className="flex gap-3">
              <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border border-accent font-sans text-xs font-semibold text-accent">{i + 1}</span>
              <span>{s}</span>
            </li>
          ))}
        </ol>
        <div className="mt-4 flex gap-2 rounded-md bg-accent/5 p-3">
          <FlaskConical className="mt-1 h-4 w-4 shrink-0 text-accent" aria-hidden />
          <p><span className="font-sans font-semibold text-accent">Decision basis.</span> {report.feasibility.decisionBasis}</p>
        </div>
      </Section>

      <Section title="Sources">
        {report.sources.length === 0 ? (
          <p className="text-ink-3">No sources attached.</p>
        ) : (
          <ul className="space-y-2">
            {report.sources.map((c, i) => (
              <li key={i} className="flex flex-wrap items-baseline gap-2">
                <CitationChip c={c} />
                {c.quote && <span className="text-ink-2">“{c.quote}”</span>}
                {c.url && <a href={c.url} className="font-sans text-sm text-accent underline" target="_blank" rel="noreferrer">{c.url}</a>}
              </li>
            ))}
          </ul>
        )}
      </Section>
    </article>
  );
}

function Section({ title, hint, children }: { title: string; hint?: string; children: React.ReactNode }) {
  return (
    <section className="print-section border-t border-line py-7">
      <h2 className="text-lg font-semibold tracking-tight">{title}</h2>
      {hint && <p className="mt-0.5 text-sm text-ink-3">{hint}</p>}
      <div className="mt-4 font-serif text-[15.5px] leading-relaxed text-ink">{children}</div>
    </section>
  );
}

function CheckRow({ c }: { c: PremiseCheck }) {
  const s = {
    pass: { icon: ShieldCheck, cls: "border-l-ok text-ok" },
    flag: { icon: ShieldAlert, cls: "border-l-warn text-warn" },
    fail: { icon: Ban, cls: "border-l-bad text-bad" },
  }[c.status];
  return (
    <li className={`flex gap-3 border-l-[3px] bg-panel py-2 pl-3 pr-3 ${s.cls}`}>
      <s.icon className="mt-1 h-4 w-4 shrink-0" aria-hidden />
      <div>
        <div className="font-sans text-sm font-semibold">{c.label} <span className="font-normal opacity-80">· {c.status}</span></div>
        <div className="text-ink-2">{c.detail} <Citations items={c.citations} /></div>
      </div>
    </li>
  );
}
