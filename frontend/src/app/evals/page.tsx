import { promises as fs } from "fs";
import path from "path";
import Link from "next/link";
import { ArrowRight, Bot, ChevronDown, CircleAlert, CircleCheck, CircleX, Code2, FileSearch, Info, Scale, ShieldCheck, Target } from "lucide-react";
import type { Metadata } from "next";
import { SiteFooter } from "@/components/SiteFooter";
import { SiteHeader } from "@/components/SiteHeader";
import { Citations } from "@/components/report/CitationChip";
import { type Citation, statusLabel } from "@/lib/report";
import { sourceShort } from "@/lib/sources";
import { scenarioById } from "@/data/scenarios";
import { RunEvals } from "@/components/RunEvals";

export const metadata: Metadata = {
  title: "Evaluation results",
  description: "How good are SpectraSense's answers? 14 real customer enquiries, every answer marked from 0 to 1 by code and by a judge model, with the sources behind each answer.",
  alternates: { canonical: "/evals" },
};
export const dynamic = "force-dynamic";

// Results written by the backend eval run (the button below, or `python -m evals.run_evals`). Generated, never edited by hand.
const OUTPUTS = path.join(process.cwd(), "outputs");
const RESULTS = path.join(OUTPUTS, "evals-latest.json");

type Summary = Record<string, { all: number | null; development: number | null; evaluation: number | null }>;
interface Row {
  id: string;
  set: string;
  title: string;
  status?: string;
  ms?: number | null;
  error?: string;
  metrics?: Record<string, unknown> & { expectation_failures?: string[]; unsupported_claims?: string[]; metric_errors?: Record<string, string> };
}
interface Result { run_at: string; mode: string; judge: string | null; judge_calls: number; metrics: string[]; summary: Summary; scenarios: Row[] }
interface CachedReport { generatedAt?: string; decisionStatus?: string; answer?: { text: string } | null; sources?: Citation[] }

// ---------------------------------------------------------------- the scores, in plain words

type Marker = "code" | "judge";
interface MetricInfo { name: string; question: string; how: string; marker: Marker; only?: string }

const METRICS: Record<string, MetricInfo> = {
  citation_validity: { name: "Quotes on the page", marker: "code", question: "Is every quote really on the page it cites?", how: "Code opens the cited page and looks for the exact words." },
  grounding: { name: "Sourced recommendations", marker: "code", question: "Does every recommended method have a checked source?", how: "A dash means no method was recommended yet." },
  faithfulness: { name: "Nothing invented", marker: "judge", question: "Is every statement backed by the source pages?", how: "The judge checks each claim against the pages. Flagged claims are listed per enquiry." },
  clarification: { name: "Asks what it doesn’t know", marker: "code", question: "Does it list the unknowns and ask about them?", how: "Half for listing unknowns, half for asking questions." },
  feasibility: { name: "A real first experiment", marker: "code", question: "Are there steps and a rule for deciding?", how: "At least two steps plus a decision basis." },
  answer_relevancy: { name: "Answers the question", marker: "judge", question: "Does it answer what the customer asked?", how: "The judge guesses the question from the report and compares." },
  expectations: { name: "Right verdict", marker: "code", question: "Does it reach the verdict the case requires?", how: "Our answer key per enquiry: status, premise checks, key terms." },
  answer_correctness: { name: "Matches the official answer", marker: "judge", only: "D01, D02", question: "How close is it to the organisers’ own answer?", how: "Only two enquiries have one; the rest show a dash." },
  context_precision: { name: "Right pages found", marker: "judge", question: "Were the pages it read useful, best ones first?", how: "The judge marks each retrieved page useful or not." },
  context_recall: { name: "Official points covered", marker: "judge", only: "D01, D02", question: "Did the pages hold the points of the official answer?", how: "Low by nature: much of the official answer is expert judgement, not page text." },
};

const GROUPS: { id: string; title: string; short: string; line: string; icon: typeof ShieldCheck; keys: string[] }[] = [
  { id: "honest", title: "Honest", short: "Is it honest?", line: "Everything it says is backed by a real page.", icon: ShieldCheck, keys: ["citation_validity", "grounding", "faithfulness"] },
  { id: "helpful", title: "Helpful", short: "Is it helpful?", line: "It moves the customer to a clear next step.", icon: Target, keys: ["clarification", "feasibility", "answer_relevancy"] },
  { id: "right", title: "Right", short: "Is it right?", line: "It reaches the verdict an expert would.", icon: Scale, keys: ["expectations", "answer_correctness"] },
  { id: "search", title: "Search", short: "Did the search work?", line: "It reads the right pages before it writes.", icon: FileSearch, keys: ["context_precision", "context_recall"] },
];

const SETS = [
  { set: "development", label: "Practice enquiries", ids: "D01–D08", note: "used while building" },
  { set: "evaluation", label: "Final enquiries", ids: "H01–H06", note: "held back for the jury" },
];

// ---------------------------------------------------------------- data

async function readJson<T>(file: string): Promise<T | null> {
  try {
    return JSON.parse(await fs.readFile(file, "utf8")) as T;
  } catch {
    return null;
  }
}

async function loadReports(ids: string[]): Promise<Record<string, CachedReport>> {
  const out: Record<string, CachedReport> = {};
  await Promise.all(ids.map(async (id) => {
    const d = await readJson<{ report?: CachedReport }>(path.join(OUTPUTS, `${id}.json`));
    if (d?.report) out[id] = d.report;
  }));
  return out;
}

/** "S01 p.5, 10, 14–15; S02 p.6" → ["S01|5", "S01|10", "S01|14", "S01|15", "S02|6"] */
function usefulPages(spec?: string): string[] {
  if (!spec) return [];
  return spec.split(";").flatMap((part) => {
    const [src, rest] = part.trim().split(" p.");
    if (!rest) return [];
    return rest.split(",").flatMap((tok) => {
      const [a, b] = tok.trim().replace("–", "-").split("-").map(Number);
      return Array.from({ length: (b || a) - a + 1 }, (_, k) => `${src}|${a + k}`);
    });
  });
}

function citedPages(sources: Citation[] = []): Set<string> {
  const out = new Set<string>();
  for (const c of sources) {
    const range = c.page.match(/^(\d+)\s*[–-]\s*(\d+)$/);
    if (range) for (let p = +range[1]; p <= +range[2]; p++) out.add(`${c.source}|${p}`);
    else if (c.page.startsWith("Table")) out.add(`${c.source}|6`);
    else (c.page.match(/\d+/g) ?? []).forEach((n) => out.add(`${c.source}|${n}`));
  }
  return out;
}

const mean = (xs: (number | null | undefined)[]) => {
  const v = xs.filter((x): x is number => typeof x === "number");
  return v.length ? v.reduce((a, b) => a + b, 0) / v.length : null;
};
const fmtDate = (s: string) => new Date(s).toLocaleString("en-GB", { dateStyle: "medium", timeStyle: "short" });

// ---------------------------------------------------------------- score display (icon + word + colour, never colour alone)

type Band = "good" | "fair" | "low";
const bandOf = (v: number | null | undefined): Band | null => (typeof v !== "number" ? null : v >= 0.8 ? "good" : v >= 0.5 ? "fair" : "low");
const ICON = { good: CircleCheck, fair: CircleAlert, low: CircleX } as const;
const TEXT = { good: "text-ok", fair: "text-warn", low: "text-bad" } as const;
const CELL = { good: "bg-ok/10", fair: "bg-warn/10", low: "bg-bad/10" } as const;
const BAR = { good: "bg-ok", fair: "bg-warn", low: "bg-bad" } as const;
const HERO = { good: "text-hero-ok", fair: "text-hero-warn", low: "text-hero-bad" } as const;
const fmt = (v: unknown) => (typeof v === "number" ? v.toFixed(2) : "–");

function Score({ v }: { v: number | null | undefined }) {
  const b = bandOf(v);
  if (!b) return <span className="text-ink-3">–<span className="sr-only"> (does not apply)</span></span>;
  const Icon = ICON[b];
  return (
    <span className={`inline-flex items-center gap-1 tabular-nums ${TEXT[b]}`}>
      <Icon className="h-3.5 w-3.5" aria-hidden />{fmt(v)}<span className="sr-only"> ({b})</span>
    </span>
  );
}

/** A score ring for the dark band: arc length = score; the number and the band word sit inside. */
function Ring({ v, label, line, href }: { v: number | null; label: string; line: string; href: string }) {
  const b = bandOf(v);
  const r = 44;
  const c = 2 * Math.PI * r;
  return (
    <a href={href} className="group flex items-center gap-4 border border-hero-line p-4 transition-colors hover:border-hero-ink-2 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-hero-ink">
      <svg viewBox="0 0 100 100" className="h-24 w-24 shrink-0 -rotate-90" aria-hidden>
        <circle cx="50" cy="50" r={r} fill="none" stroke="var(--hero-line)" strokeWidth="7" />
        {b && <circle cx="50" cy="50" r={r} fill="none" stroke="currentColor" strokeWidth="7" strokeLinecap="butt"
                      strokeDasharray={`${c * (v as number)} ${c}`} className={HERO[b]} />}
      </svg>
      <div className="min-w-0">
        <p className="text-sm text-hero-ink-2">{label}</p>
        <p className={`text-[2.25rem] font-light leading-none tabular-nums ${b ? HERO[b] : "text-hero-ink-2"}`}>
          {fmt(v)}
        </p>
        <p className="mt-1.5 text-xs leading-snug text-hero-ink-2">{line}</p>
      </div>
    </a>
  );
}

/** Practice vs final as two slim bars on one card. */
function Bars({ dev, fin }: { dev: number | null; fin: number | null }) {
  return (
    <div className="space-y-1.5">
      {[["Practice", dev], ["Final", fin]].map(([label, v]) => {
        const b = bandOf(v as number | null);
        return (
          <div key={label as string} className="grid grid-cols-[4.25rem_1fr_2.5rem] items-center gap-2 text-xs">
            <span className="text-ink-3">{label}</span>
            <span className="h-1.5 bg-panel-2" aria-hidden>
              {b && <span className={`block h-full ${BAR[b]}`} style={{ width: `${Math.round((v as number) * 100)}%` }} />}
            </span>
            <span className="text-right"><Score v={v as number | null} /></span>
          </div>
        );
      })}
    </div>
  );
}

function MarkerBadge({ marker }: { marker: Marker }) {
  return marker === "code" ? (
    <span className="inline-flex items-center gap-1 text-[11px] font-medium text-ink-2"><Code2 className="h-3 w-3" aria-hidden /> code</span>
  ) : (
    <span className="inline-flex items-center gap-1 text-[11px] font-medium text-violet"><Bot className="h-3 w-3" aria-hidden /> judge</span>
  );
}

// ---------------------------------------------------------------- page

export default async function EvalsPage() {
  const r = await readJson<Result>(RESULTS);
  const reports = r ? await loadReports(r.scenarios.map((s) => s.id)) : {};
  const independent = !!r?.judge && !/no judge key/i.test(r.judge);
  const metricKeys = r ? GROUPS.flatMap((g) => g.keys).filter((k) => r.metrics.includes(k)) : [];
  const groupStarts = new Set(r ? GROUPS.map((g) => g.keys.find((k) => r.metrics.includes(k))).filter(Boolean) : []);
  const judgeKeys = Object.entries(METRICS).filter(([, m]) => m.marker === "judge").map(([k]) => k).filter((k) => r?.metrics.includes(k));
  const judgeMissing = r ? r.scenarios.reduce((n, s) => n + Object.keys(s.metrics?.metric_errors ?? {}).filter((k) => judgeKeys.includes(k)).length, 0) : 0;
  const judgeTotal = r ? r.scenarios.reduce((n, s) => n + judgeKeys.filter((k) => typeof s.metrics?.[k] === "number" || s.metrics?.metric_errors?.[k]).length, 0) : 0;
  const groupScore = (keys: string[]) => (r ? mean(keys.filter((k) => r.metrics.includes(k)).map((k) => r.summary[k]?.all)) : null);

  return (
    <>
      <SiteHeader />
      <main>
        {/* ---------------- the verdict, at a glance */}
        <section className="bg-hero text-hero-ink">
          <div className="mx-auto max-w-300 px-5 pb-14 pt-14 sm:px-8 lg:px-10">
            <p className="text-sm text-hero-ink-2">Evaluation</p>
            <h1 className="mt-2 text-[clamp(2.5rem,5vw,4rem)] font-light leading-[1.05] tracking-[-0.01em]">How good are the answers?</h1>
            <p className="mt-5 max-w-2xl text-lg leading-relaxed text-hero-ink-2">
              We gave the assistant 14 real customer enquiries and marked every answer from 0 to 1.
              Code checks the facts. A second model reads for meaning.
            </p>
            {r && (
              <div className="mt-10 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                {GROUPS.map((g) => <Ring key={g.id} v={groupScore(g.keys)} label={g.short} line={g.line} href={`#${g.id}`} />)}
              </div>
            )}
            {r && (
              <p className="mt-5 text-xs text-hero-ink-2">
                Group score = average of its scores below · marked {fmtDate(r.run_at)} · {r.mode} · judge: {r.judge ?? "off"}
                {judgeTotal > 0 && ` · ${judgeTotal - judgeMissing} of ${judgeTotal} judge marks completed`}
              </p>
            )}
          </div>
          <div className="h-1" style={{ background: "var(--spectrum)" }} aria-hidden />
        </section>

        <div className="mx-auto max-w-300 px-5 pb-20 sm:px-8 lg:px-10">
          {/* ---------------- re-run the marking (live pipeline + judge) */}
          {r && (
            <section className="pt-10" aria-labelledby="rerun">
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <h2 id="rerun" className="text-lg font-semibold">Re-run the marking</h2>
                <p className="text-sm text-ink-3">Runs all 14 enquiries through the live assistant and marks them again. The page updates when it finishes.</p>
              </div>
              <div className="mt-3"><RunEvals /></div>
            </section>
          )}

          {/* ---------------- how the marking works */}
          <section className="py-14" aria-labelledby="how">
            <h2 id="how" className="text-2xl font-semibold tracking-tight">How we mark</h2>
            <ol className="mt-6 grid gap-px bg-line md:grid-cols-3">
              {[
                { n: "01", title: "The test", text: "14 real enquiries from the organisers. 8 to practise on, 6 held back for the jury.", icon: Info },
                { n: "02", title: "The answer key", text: "Code checks the hard facts: is each quote on its page, is each method backed by a source? Free and repeatable.", icon: Code2 },
                { n: "03", title: "The second reader", text: "A judge model reads like an expert: is it true to the sources, does it answer the question?", icon: Bot },
              ].map((s) => (
                <li key={s.n} className="bg-panel p-6">
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-3xl font-light text-accent">{s.n}</span>
                    <s.icon className="h-5 w-5 text-ink-3" aria-hidden />
                  </div>
                  <p className="mt-4 font-semibold">{s.title}</p>
                  <p className="mt-1 text-sm leading-relaxed text-ink-2">{s.text}</p>
                </li>
              ))}
            </ol>

            {r?.judge && !independent && (
              <p className="mt-4 flex gap-2 border-l-4 border-l-warn bg-panel p-4 text-sm">
                <CircleAlert className="mt-0.5 h-4 w-4 shrink-0 text-warn" aria-hidden />
                This run had no separate judge key, so the assistant’s own model did the judge marking. Treat those scores as a self-check.
                The code-marked scores are unaffected.
              </p>
            )}

            <div className="mt-6 flex flex-wrap items-center gap-x-5 gap-y-2 text-xs text-ink-2">
              <span className="font-medium text-ink">Reading a score</span>
              <span className="inline-flex items-center gap-1 text-ok"><CircleCheck className="h-3.5 w-3.5" aria-hidden /> 0.80+ good</span>
              <span className="inline-flex items-center gap-1 text-warn"><CircleAlert className="h-3.5 w-3.5" aria-hidden /> 0.50–0.79 fair</span>
              <span className="inline-flex items-center gap-1 text-bad"><CircleX className="h-3.5 w-3.5" aria-hidden /> below 0.50 low</span>
              <span>– does not apply (not a zero)</span>
              {judgeMissing > 0 && <span className="italic">not marked: the judge hit its rate limit ({judgeMissing} of {judgeTotal} judge marks)</span>}
            </div>
          </section>

          {!r ? (
            <div className="border border-line bg-panel p-6">
              <h2 className="font-semibold">No marks yet</h2>
              <p className="mt-2 text-sm text-ink-2">Press Run evals below, or from the backend folder: <code className="bg-bg px-1">.venv/bin/python -m evals.run_evals</code></p>
              <div className="mt-4"><RunEvals /></div>
            </div>
          ) : (
            <>
              {/* ---------------- the four questions */}
              <div className="divide-y divide-line border-y border-line">
                {GROUPS.map((g) => {
                  const keys = g.keys.filter((k) => r.metrics.includes(k));
                  if (!keys.length) return null;
                  const v = groupScore(keys);
                  const b = bandOf(v);
                  return (
                    <section key={g.id} id={g.id} aria-labelledby={`h-${g.id}`} className="grid scroll-mt-20 gap-6 py-10 lg:grid-cols-[17rem_1fr]">
                      <div>
                        <g.icon className="h-6 w-6 text-accent" aria-hidden />
                        <h2 id={`h-${g.id}`} className="mt-3 text-2xl font-semibold tracking-tight">{g.short}</h2>
                        <p className="mt-1 text-ink-2">{g.line}</p>
                        <p className={`mt-4 text-5xl font-light tabular-nums ${b ? TEXT[b] : "text-ink-3"}`}>{fmt(v)}</p>
                      </div>
                      <div className={`grid gap-3 ${keys.length > 2 ? "md:grid-cols-3" : "md:grid-cols-2"}`}>
                        {keys.map((k) => {
                          const m = METRICS[k];
                          const s = r.summary[k];
                          return (
                            <article key={k} className="flex flex-col border border-line bg-panel p-5">
                              <div className="flex items-center justify-between gap-2">
                                <MarkerBadge marker={m.marker} />
                                {m.only && <span className="text-[11px] text-ink-3">only {m.only}</span>}
                              </div>
                              <h3 className="mt-3 font-semibold leading-snug">{m.name}</h3>
                              <p className="mt-1 text-sm text-ink">{m.question}</p>
                              <p className="mt-1 text-xs leading-relaxed text-ink-3">{m.how}</p>
                              <div className="mt-auto pt-5"><Bars dev={s?.development ?? null} fin={s?.evaluation ?? null} /></div>
                            </article>
                          );
                        })}
                      </div>
                    </section>
                  );
                })}
              </div>

              {/* ---------------- every enquiry */}
              <section className="pt-14" aria-labelledby="table">
                <h2 id="table" className="text-2xl font-semibold tracking-tight">Every enquiry, every mark</h2>
                <p className="mt-1 text-ink-2">Click an enquiry to see the answer and its sources.</p>
                <div className="mt-5 overflow-x-auto border border-line bg-panel">
                  <table className="w-full min-w-260 border-collapse text-sm">
                    <thead className="text-left text-xs text-ink-2">
                      <tr className="bg-panel-2">
                        <th scope="col" rowSpan={2} className="min-w-62.5 px-3 py-2 align-bottom font-semibold">Enquiry</th>
                        <th scope="col" rowSpan={2} className="px-3 py-2 align-bottom font-semibold">Verdict</th>
                        {GROUPS.map((g) => {
                          const n = g.keys.filter((k) => r.metrics.includes(k)).length;
                          return n ? <th key={g.id} scope="colgroup" colSpan={n} className="border-l border-line px-3 pt-2 font-semibold text-ink">{g.title}</th> : null;
                        })}
                        <th scope="col" rowSpan={2} className="border-l border-line px-3 py-2 align-bottom font-semibold">Time</th>
                      </tr>
                      <tr className="bg-panel-2">
                        {metricKeys.map((k) => (
                          <th key={k} scope="col" title={METRICS[k].question} className={`px-3 pb-2 font-normal ${groupStarts.has(k) ? "border-l border-line" : ""}`}>
                            {METRICS[k].name}{METRICS[k].marker === "judge" && <Bot className="ml-1 inline h-3 w-3 text-violet" aria-label="judge" />}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    {SETS.map((g) => {
                      const rows = r.scenarios.filter((s) => s.set === g.set);
                      if (!rows.length) return null;
                      return (
                        <tbody key={g.set}>
                          <tr className="border-t border-line">
                            <th scope="colgroup" colSpan={metricKeys.length + 3} className="px-3 pb-2 pt-4 text-left">
                              <span className="font-semibold">{g.label}</span> <span className="font-mono text-xs text-ink-3">{g.ids}</span>
                              <span className="ml-2 text-xs font-normal text-ink-3">{g.note}</span>
                            </th>
                          </tr>
                          {rows.map((s) => (
                            <tr key={s.id} className="border-t border-line align-top hover:bg-bg">
                              <th scope="row" className="px-3 py-2.5 text-left font-normal">
                                <a href={`#case-${s.id}`} className="text-ink underline decoration-line-strong underline-offset-4 hover:decoration-accent">{s.title}</a>
                                <span className="ml-1.5 font-mono text-xs text-ink-3">{s.id}</span>
                              </th>
                              {s.error ? (
                                <td colSpan={metricKeys.length + 2} className="px-3 py-2.5 text-bad">Failed: {s.error}</td>
                              ) : (
                                <>
                                  <td className="px-3 py-2.5 text-xs text-ink-2">{s.status ? statusLabel[s.status as keyof typeof statusLabel] ?? s.status : "–"}</td>
                                  {metricKeys.map((k) => {
                                    const v = s.metrics?.[k] as number | null | undefined;
                                    const b = bandOf(v);
                                    const missed = s.metrics?.metric_errors?.[k];
                                    return <td key={k} className={`px-3 py-2.5 ${b ? CELL[b] : ""} ${groupStarts.has(k) ? "border-l border-line" : ""}`}>
                                      {missed ? <span className="text-xs italic text-ink-3" title={`The judge could not mark this: ${missed}`}>not marked</span> : <Score v={v} />}
                                    </td>;
                                  })}
                                  <td className="whitespace-nowrap border-l border-line px-3 py-2.5 text-xs text-ink-3">{s.ms ? `${(s.ms / 1000).toFixed(1)} s` : "–"}</td>
                                </>
                              )}
                            </tr>
                          ))}
                        </tbody>
                      );
                    })}
                  </table>
                </div>
              </section>

              {/* ---------------- drill-down */}
              <section className="pt-14" aria-labelledby="compare">
                <h2 id="compare" className="text-2xl font-semibold tracking-tight">See for yourself</h2>
                <p className="mt-1 max-w-2xl text-ink-2">
                  Open an enquiry: what the customer asked, what the assistant answered, and the pages behind it. Click a source to read the quote.
                </p>
                <div className="mt-5 divide-y divide-line border-y border-line">
                  {r.scenarios.map((s) => {
                    const sc = scenarioById(s.id);
                    const rep = reports[s.id];
                    const useful = usefulPages(sc?.usefulSources);
                    const cited = citedPages(rep?.sources);
                    const hit = useful.filter((u) => cited.has(u));
                    const failures = s.metrics?.expectation_failures ?? [];
                    const unsupported = s.metrics?.unsupported_claims ?? [];
                    const flags = failures.length + unsupported.length;
                    return (
                      <details key={s.id} id={`case-${s.id}`} className="group scroll-mt-20">
                        <summary className="flex cursor-pointer list-none flex-wrap items-center gap-x-3 gap-y-1 px-2 py-4 hover:bg-panel focus-visible:outline-2 focus-visible:outline-accent">
                          <ChevronDown className="h-4 w-4 shrink-0 text-ink-3 transition-transform group-open:rotate-180 motion-reduce:transition-none" aria-hidden />
                          <span className="font-mono text-xs text-ink-3">{s.id}</span>
                          <span className="font-medium">{s.title}</span>
                          <span className="ml-auto flex items-center gap-2 text-xs">
                            {useful.length > 0 && <span className="border border-line bg-panel px-1.5 py-0.5 text-ink-2">{hit.length}/{useful.length} useful pages cited</span>}
                            <span className={`border px-1.5 py-0.5 ${flags ? "border-warn/40 text-warn" : "border-ok/40 text-ok"}`}>{flags ? `${flags} flagged` : "nothing flagged"}</span>
                          </span>
                        </summary>
                        <div className="grid gap-8 px-2 pb-8 pt-2 lg:grid-cols-2">
                          <div className="space-y-5">
                            {sc && (
                              <figure>
                                <figcaption className="text-xs font-semibold uppercase tracking-wide text-ink-3">The customer asked</figcaption>
                                <blockquote className="mt-2 border-l-2 border-line-strong pl-4 font-serif text-[15px] leading-relaxed text-ink-2">{sc.enquiry}</blockquote>
                              </figure>
                            )}
                            <figure>
                              <figcaption className="text-xs font-semibold uppercase tracking-wide text-ink-3">The assistant answered</figcaption>
                              {rep ? (
                                <blockquote className="mt-2 border-l-4 border-l-accent bg-panel p-4">
                                  <span className="text-xs font-semibold text-accent">{rep.decisionStatus ? statusLabel[rep.decisionStatus as keyof typeof statusLabel] : ""}</span>
                                  <p className="mt-1 font-serif text-[16px] leading-relaxed text-ink">{rep.answer?.text ?? "This report predates the direct-answer section."}</p>
                                </blockquote>
                              ) : (
                                <p className="mt-2 text-sm text-ink-3">No stored report for this enquiry.</p>
                              )}
                            </figure>
                            <Link href={`/assess?example=${s.id}`} className="inline-flex items-center gap-1.5 text-sm font-medium text-accent hover:underline">
                              Try this enquiry yourself <ArrowRight className="h-4 w-4" aria-hidden />
                            </Link>
                          </div>
                          <div className="space-y-5 text-sm">
                            {useful.length > 0 && (
                              <div>
                                <h3 className="text-xs font-semibold uppercase tracking-wide text-ink-3">Pages the organisers call useful</h3>
                                <ul className="mt-2 flex flex-wrap gap-1.5">
                                  {useful.map((u) => {
                                    const [src, pg] = u.split("|");
                                    const ok = cited.has(u);
                                    return (
                                      <li key={u} className={`inline-flex items-center gap-1 border px-1.5 py-0.5 text-xs ${ok ? "border-ok/40 bg-ok/10 text-ok" : "border-line text-ink-3"}`}>
                                        {ok ? <CircleCheck className="h-3 w-3" aria-hidden /> : <CircleX className="h-3 w-3" aria-hidden />}
                                        {sourceShort(src)} p.{pg}<span className="sr-only">{ok ? " (cited)" : " (not cited)"}</span>
                                      </li>
                                    );
                                  })}
                                </ul>
                                <p className="mt-1.5 text-xs text-ink-3">Green = cited in the answer. Grey = not cited (it may still have been read).</p>
                              </div>
                            )}
                            <div>
                              <h3 className="text-xs font-semibold uppercase tracking-wide text-ink-3">Sources it cites</h3>
                              {rep?.sources?.length ? <div className="mt-2"><Citations items={rep.sources} /></div> : <p className="mt-2 text-ink-3">None.</p>}
                            </div>
                            <div>
                              <h3 className="text-xs font-semibold uppercase tracking-wide text-ink-3">What the markers flagged</h3>
                              {flags ? (
                                <ul className="mt-2 space-y-1.5">
                                  {failures.map((f, i) => <li key={`f${i}`} className="flex gap-2 text-ink-2"><Code2 className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-label="code" /> Missed: {f}</li>)}
                                  {unsupported.map((c, i) => <li key={`u${i}`} className="flex gap-2 text-ink-2"><Bot className="mt-0.5 h-3.5 w-3.5 shrink-0 text-violet" aria-label="judge" /> Not found on the pages: “{c}”</li>)}
                                </ul>
                              ) : (
                                <p className="mt-2 inline-flex items-center gap-1.5 text-ok"><CircleCheck className="h-3.5 w-3.5" aria-hidden /> Nothing flagged.</p>
                              )}
                            </div>
                            {rep?.generatedAt && Math.abs(new Date(rep.generatedAt).getTime() - new Date(r.run_at).getTime()) > 3_600_000 && (
                              <p className="text-xs text-ink-3">Answer from {fmtDate(rep.generatedAt)}; marks from {fmtDate(r.run_at)}.</p>
                            )}
                          </div>
                        </div>
                      </details>
                    );
                  })}
                </div>
              </section>

              {/* ---------------- honesty about the numbers */}
              <section className="mt-14 grid gap-6 border border-line bg-panel p-8 md:grid-cols-[14rem_1fr]" aria-labelledby="limits">
                <h2 id="limits" className="text-xl font-semibold tracking-tight">Read with care</h2>
                <ul className="grid gap-4 text-sm text-ink-2 sm:grid-cols-2">
                  <li><b className="block font-semibold text-ink">A small test</b>14 enquiries show how it behaves on these cases, not on every possible enquiry.</li>
                  <li><b className="block font-semibold text-ink">Our own answer key</b>Only D01 and D02 have an official answer. The other checks are written by the team.</li>
                  <li><b className="block font-semibold text-ink">Judges can be wrong</b>That is why code checks and clickable sources sit next to every judge score.</li>
                  <li><b className="block font-semibold text-ink">A draft for an expert</b>Every report is a starting point for an AFS specialist, never a final decision.</li>
                </ul>
              </section>
            </>
          )}
        </div>
      </main>
      <SiteFooter />
    </>
  );
}
