"use client";

import { AlertTriangle, Ban, CheckCircle2, CircleHelp, Download, FlaskConical, ShieldAlert, ShieldCheck, Copy, Check } from "lucide-react";
import { useState } from "react";
import { type Report, statusLabel, type PremiseCheck } from "@/lib/report";
import { toMarkdown } from "@/lib/markdown";
import type { MethodId } from "@/data/optics";
import { Citations, CitationChip } from "./CitationChip";
import { SetupSketch } from "./SetupSketch";
import { SpectralBand } from "../SpectralBand";

const sections = [
  ["requirements", "Requirements"],
  ["questions", "Clarification questions"],
  ["recommendation", "Recommendation"],
  ["concept", "Measurement concept"],
  ["range", "Spectral range"],
  ["risks", "Risks & uncertainty"],
  ["plan", "Feasibility plan"],
  ["checks", "Premise checks"],
  ["sources", "Sources"],
] as const;

const statusStyle = {
  provisional: { cls: "border-cyan/50 bg-cyan/10 text-cyan", icon: CheckCircle2 },
  insufficient: { cls: "border-warn/50 bg-warn/10 text-warn", icon: CircleHelp },
  out_of_scope: { cls: "border-bad/50 bg-bad/10 text-bad", icon: Ban },
};

const originStyle = {
  live: "border-ok/50 text-ok",
  cached: "border-cyan/50 text-cyan",
  reference: "border-violet/50 text-violet",
};

const roleLabel = { primary: "Primary candidate", comparison: "Comparison candidate", combination: "Combination (test after singles)", not_recommended: "Not recommended" };
const roleStyle = { primary: "border-cyan/50", comparison: "border-line-strong", combination: "border-violet/50", not_recommended: "border-bad/50" };
const impactLabel = { method: "could change method", setup: "could change setup", acceptance: "sets acceptance" };

export function ReportView({ report, enquiry }: { report: Report; enquiry: string }) {
  const S = statusStyle[report.decisionStatus];
  const methodIds = Array.from(new Set(report.recommendations.filter((r) => r.role !== "not_recommended").flatMap((r) => r.methodIds))) as MethodId[];
  const [copied, setCopied] = useState(false);

  const download = () => {
    const blob = new Blob([toMarkdown(report, enquiry)], { type: "text/markdown" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `${report.scenarioId ?? "assessment"}-assessment.md`;
    a.click();
    URL.revokeObjectURL(a.href);
  };
  const copy = async () => {
    await navigator.clipboard.writeText(toMarkdown(report, enquiry));
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <article className="flex gap-8">
      <div className="min-w-0 flex-1 space-y-5">
        <header className="rounded-lg border border-line bg-panel p-5">
          <div className="flex flex-wrap items-center gap-2">
            {report.scenarioId && <span className="rounded bg-panel-2 px-2 py-0.5 font-mono text-xs text-ink-2">{report.scenarioId}</span>}
            <span className={`rounded border px-2 py-0.5 font-mono text-[11px] uppercase tracking-wider ${originStyle[report.origin]}`}>{report.origin}</span>
            <div className="ml-auto flex gap-2">
              <button onClick={copy} className="inline-flex items-center gap-1.5 rounded border border-line px-2.5 py-1 text-xs text-ink-2 hover:border-cyan hover:text-ink">
                {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />} {copied ? "Copied" : "Copy Markdown"}
              </button>
              <button onClick={download} className="inline-flex items-center gap-1.5 rounded border border-line px-2.5 py-1 text-xs text-ink-2 hover:border-cyan hover:text-ink">
                <Download className="h-3.5 w-3.5" /> Export .md
              </button>
            </div>
          </div>
          <h1 className="mt-3 text-2xl font-semibold tracking-tight">{report.title}</h1>
          <div className={`mt-4 inline-flex items-center gap-2 rounded-md border px-3 py-1.5 text-sm font-medium ${S.cls}`}>
            <S.icon className="h-4 w-4" aria-hidden /> Decision status: {statusLabel[report.decisionStatus]}
          </div>
          {report.originNote && <p className="mt-3 text-xs text-violet/90">{report.originNote}</p>}
        </header>

        <Section id="requirements" title="Requirements">
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <h4 className="mb-2 flex items-center gap-1.5 text-xs font-medium uppercase tracking-wider text-ok"><CheckCircle2 className="h-3.5 w-3.5" /> Stated by the client</h4>
              <ul className="space-y-1.5 text-sm">{report.requirements.stated.map((s) => <li key={s} className="rounded border border-ok/20 bg-ok/5 px-2.5 py-1.5">{s}</li>)}</ul>
            </div>
            <div>
              <h4 className="mb-2 flex items-center gap-1.5 text-xs font-medium uppercase tracking-wider text-warn"><CircleHelp className="h-3.5 w-3.5" /> Key unknowns — not assumed</h4>
              <ul className="space-y-1.5 text-sm">{report.requirements.unknowns.map((s) => <li key={s} className="rounded border border-dashed border-warn/40 bg-warn/5 px-2.5 py-1.5">{s}</li>)}</ul>
            </div>
          </div>
        </Section>

        <Section id="questions" title="Clarification questions" hint="Ordered: answers that could change the method or setup come first.">
          <ol className="space-y-2">
            {report.questions.map((q, i) => (
              <li key={i} className="flex gap-3 rounded border border-line bg-bg/40 px-3 py-2 text-sm">
                <span className="font-mono text-cyan">{String(i + 1).padStart(2, "0")}</span>
                <span className="flex-1">{q.text}</span>
                {q.impact && <span className="h-fit whitespace-nowrap rounded bg-panel-2 px-1.5 py-0.5 font-mono text-[10px] text-ink-3">{impactLabel[q.impact]}</span>}
              </li>
            ))}
          </ol>
        </Section>

        <Section id="recommendation" title="Recommendation">
          {report.recommendations.length === 0 ? (
            <p className="rounded border border-dashed border-warn/40 p-3 text-sm text-warn">No method is recommended on the known facts. See the clarification questions and the proposed first step.</p>
          ) : (
            <div className="grid gap-3 lg:grid-cols-2">
              {report.recommendations.map((r) => (
                <div key={r.method} className={`rounded-md border bg-bg/40 p-4 ${roleStyle[r.role]}`}>
                  <div className="font-mono text-[10px] uppercase tracking-wider text-ink-3">{roleLabel[r.role]}</div>
                  <div className="mt-1 text-lg font-semibold">{r.method}</div>
                  <p className="mt-2 text-sm leading-relaxed text-ink-2">{r.reason}</p>
                  <div className="mt-3"><Citations items={r.citations} /></div>
                </div>
              ))}
            </div>
          )}
        </Section>

        <Section id="concept" title="Measurement concept">
          <SetupSketch analyzer={report.concept.analyzer} fiberLink={report.concept.fiberLink} probe={report.concept.probe} location={report.concept.location} />
          <p className="mt-3 text-sm leading-relaxed text-ink-2">{report.concept.summary} <Citations items={report.concept.citations} /></p>
        </Section>

        <Section id="range" title="Spectral range">
          <p className="mb-3 text-sm leading-relaxed text-ink-2">{report.spectralRange.summary} <Citations items={report.spectralRange.citations} /></p>
          <SpectralBand key={methodIds.join()} highlight={methodIds} />
        </Section>

        <Section id="risks" title="Risks and uncertainty">
          <ul className="space-y-1.5 text-sm">
            {report.risks.map((r) => (
              <li key={r} className="flex gap-2"><AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-warn" aria-hidden />{r}</li>
            ))}
          </ul>
        </Section>

        <Section id="plan" title="First feasibility experiment">
          <ol className="relative space-y-3 border-l border-line pl-5">
            {report.feasibility.steps.map((s, i) => (
              <li key={i} className="text-sm">
                <span className="absolute -left-[9px] mt-0.5 flex h-4 w-4 items-center justify-center rounded-full border border-cyan bg-bg font-mono text-[9px] text-cyan">{i + 1}</span>
                {s}
              </li>
            ))}
          </ol>
          <div className="mt-4 flex gap-2 rounded-md border border-cyan/30 bg-cyan/5 p-3 text-sm">
            <FlaskConical className="mt-0.5 h-4 w-4 shrink-0 text-cyan" aria-hidden />
            <p><span className="font-medium text-cyan">Decision basis.</span> {report.feasibility.decisionBasis}</p>
          </div>
        </Section>

        <Section id="checks" title="Premise checks" hint="Deterministic checks the pipeline runs before the answer is composed.">
          {report.premiseChecks.length === 0 ? (
            <p className="text-sm text-ink-3">No premise checks attached{report.origin === "reference" ? " — organizer reference answers do not carry pipeline checks." : "."}</p>
          ) : (
            <ul className="space-y-2">{report.premiseChecks.map((c) => <CheckRow key={c.id} c={c} />)}</ul>
          )}
        </Section>

        <Section id="sources" title="Sources">
          <ul className="space-y-1.5 text-sm">
            {report.sources.map((c, i) => (
              <li key={i} className="flex flex-wrap items-baseline gap-2">
                <CitationChip c={c} />
                {c.quote && <span className="text-ink-2">“{c.quote}”</span>}
                {c.url && <a href={c.url} className="text-cyan underline" target="_blank" rel="noreferrer">{c.url}</a>}
              </li>
            ))}
          </ul>
        </Section>
      </div>

      <nav className="sticky top-20 hidden h-fit w-44 shrink-0 xl:block" aria-label="Report sections">
        <p className="mb-2 font-mono text-[10px] uppercase tracking-wider text-ink-3">On this report</p>
        <ul className="space-y-1 border-l border-line text-sm">
          {sections.map(([id, label]) => (
            <li key={id}><a href={`#${id}`} className="-ml-px block border-l border-transparent py-0.5 pl-3 text-ink-3 hover:border-cyan hover:text-ink">{label}</a></li>
          ))}
        </ul>
      </nav>
    </article>
  );
}

function Section({ id, title, hint, children }: { id: string; title: string; hint?: string; children: React.ReactNode }) {
  return (
    <section id={id} className="scroll-mt-20 rounded-lg border border-line bg-panel p-5">
      <h2 className="text-sm font-semibold uppercase tracking-[0.14em] text-ink-2">{title}</h2>
      {hint && <p className="mt-1 text-xs text-ink-3">{hint}</p>}
      <div className="mt-4">{children}</div>
    </section>
  );
}

function CheckRow({ c }: { c: PremiseCheck }) {
  const s = {
    pass: { icon: ShieldCheck, cls: "border-ok/30 text-ok" },
    flag: { icon: ShieldAlert, cls: "border-warn/40 text-warn" },
    fail: { icon: Ban, cls: "border-bad/50 text-bad" },
  }[c.status];
  return (
    <li className={`flex gap-3 rounded border bg-bg/40 px-3 py-2 ${s.cls}`}>
      <s.icon className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
      <div className="text-sm">
        <div className="font-medium">{c.label} <span className="font-mono text-[10px] uppercase opacity-80">{c.status}</span></div>
        <div className="text-ink-2">{c.detail} <Citations items={c.citations} /></div>
      </div>
    </li>
  );
}
