import { promises as fs } from "fs";
import path from "path";
import { CircleAlert, CircleCheck, CircleX } from "lucide-react";
import type { Metadata } from "next";
import { NumberTicker } from "@/components/NumberTicker";
import { SiteFooter } from "@/components/SiteFooter";
import { SiteHeader } from "@/components/SiteHeader";
import { statusLabel } from "@/lib/report";
import { RunEvals } from "@/components/RunEvals";

export const metadata: Metadata = {
  title: "Evaluation results",
  description: "How SpectraSense scores on the development and final evaluation enquiries: citation validity, grounding, faithfulness, relevancy, context precision and per-scenario expectations.",
  alternates: { canonical: "/evals" },
};
export const dynamic = "force-dynamic";

// Results written by the backend eval run (the button below, or `python -m evals.run_evals`). Generated, never edited by hand.
const RESULTS = path.join(process.cwd(), "outputs", "evals-latest.json");

type Summary = Record<string, { all: number | null; development: number | null; evaluation: number | null }>;
interface Row {
  id: string;
  set: string;
  title: string;
  status?: string;
  ms?: number | null;
  error?: string;
  metrics?: Record<string, unknown> & { expectation_failures?: string[]; unsupported_claims?: string[] };
}
interface Result { run_at: string; mode: string; judge: string | null; judge_calls: number; metrics: string[]; summary: Summary; scenarios: Row[] }

// The organisers' enquiry sets: D = development (used while building), H = final evaluation (held out).
const GROUPS = [
  { set: "development", label: "Development enquiries", note: "the organisers’ cases used while building the assistant (IDs D01–D08)" },
  { set: "evaluation", label: "Final evaluation enquiries", note: "held out for the jury (IDs H01–H06)" },
];

const ABOUT: Record<string, string> = {
  citation_validity: "Citations whose quote was found on the cited page",
  grounding: "Recommendations backed by a verified citation",
  clarification: "Lists unknowns and asks clarification questions",
  feasibility: "First experiment has steps and a decision basis",
  expectations: "Expected status, premise checks and terms (golden.json)",
  faithfulness: "Report claims supported by the retrieved pages (judge)",
  answer_relevancy: "Report addresses the client's enquiry (judge)",
  context_precision: "Retrieved pages that are relevant, rank-weighted (judge)",
  context_recall: "Reference statements found in the retrieved pages (D01, D02)",
  answer_correctness: "Agreement with the organiser reference answer (D01, D02)",
};

async function load(): Promise<Result | null> {
  try {
    return JSON.parse(await fs.readFile(RESULTS, "utf8")) as Result;
  } catch {
    return null;
  }
}

// Score bands carry an icon and a word, not colour alone (thresholds stated in the legend).
const band = (v: number | null | undefined) =>
  v === null || v === undefined ? null : v >= 0.8 ? { Icon: CircleCheck, word: "good" } : v >= 0.5 ? { Icon: CircleAlert, word: "fair" } : { Icon: CircleX, word: "low" };

function Score({ v, large = false }: { v: number | null | undefined; large?: boolean }) {
  const b = band(v);
  return (
    <span className={`inline-flex items-center gap-1 tabular-nums ${tone(v)}`}>
      {b && <b.Icon className={large ? "h-5 w-5" : "h-3.5 w-3.5"} aria-hidden />}
      {large && typeof v === "number" ? <NumberTicker value={v} decimals={2} /> : fmt(v)}
      {b ? <span className="sr-only"> ({b.word})</span> : <span className="sr-only"> (not applicable)</span>}
    </span>
  );
}

const tone = (v: number | null | undefined) =>
  v === null || v === undefined ? "text-ink-3" : v >= 0.8 ? "text-ok" : v >= 0.5 ? "text-warn" : "text-bad";
const fmt = (v: unknown) => (typeof v === "number" ? v.toFixed(2) : "–");

export default async function EvalsPage() {
  const r = await load();
  return (
    <>
      <SiteHeader />
      <main className="mx-auto max-w-[1200px] px-5 pb-20 pt-12 sm:px-8 lg:px-10">
        <h1 className="text-[clamp(2.25rem,4vw,3rem)] font-light leading-tight">Evaluation results</h1>
        <p className="mt-2 max-w-3xl text-ink-2">
          Every development and final-evaluation enquiry is run through the live pipeline and scored. Deterministic checks verify
          citations, grounding and expectations; RAGAS-style metrics are scored by a separate judge model. Scores run from 0 to 1, and a
          dash means a metric does not apply, for example where no organiser reference exists.
        </p>

        <div className="mt-6">
          <RunEvals />
        </div>

        {!r ? (
          <div className="mt-10 rounded-lg border border-line bg-panel p-6">
            <h2 className="font-semibold">No eval run yet</h2>
            <p className="mt-2 text-sm text-ink-2">Press Run evals above, or run them from the backend folder:</p>
            <pre className="mt-3 overflow-x-auto rounded bg-bg p-3 text-sm">cd backend{"\n"}.venv/bin/python -m evals.run_evals</pre>
          </div>
        ) : (
          <>
            <p className="mt-6 text-sm text-ink-3">
              Run {new Date(r.run_at).toLocaleString()} · {r.mode} · judge: {r.judge ?? "off"} · {r.judge_calls} judge calls
            </p>

            <p className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-ink-2">
              <span className="inline-flex items-center gap-1 text-ok"><CircleCheck className="h-3.5 w-3.5" aria-hidden /> good ≥ 0.80</span>
              <span className="inline-flex items-center gap-1 text-warn"><CircleAlert className="h-3.5 w-3.5" aria-hidden /> fair 0.50–0.79</span>
              <span className="inline-flex items-center gap-1 text-bad"><CircleX className="h-3.5 w-3.5" aria-hidden /> low &lt; 0.50</span>
              <span className="text-ink-3">– not applicable</span>
            </p>

            <section className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
              {r.metrics.map((m) => (
                <div key={m} className="rounded-lg border border-line bg-bg p-4">
                  <div className="text-xs text-ink-3">{m.replace(/_/g, " ")}</div>
                  <div className="mt-1 text-[1.75rem] font-light"><Score v={r.summary[m]?.all} large /></div>
                  <div className="mt-1 text-xs leading-snug text-ink-3">{ABOUT[m]}</div>
                  <div className="mt-2 text-xs text-ink-2">dev {fmt(r.summary[m]?.development)} · final {fmt(r.summary[m]?.evaluation)}</div>
                </div>
              ))}
            </section>

            <section className="mt-10 overflow-x-auto rounded-lg border border-line">
              <table className="w-full min-w-[900px] text-sm">
                <thead className="bg-panel-2 text-left text-xs text-ink-2">
                  <tr>
                    <th scope="col" className="min-w-[240px] px-3 py-2 font-semibold">Scenario</th>
                    <th scope="col" className="px-3 py-2 font-semibold">Status</th>
                    {r.metrics.map((m) => <th key={m} scope="col" className="px-3 py-2 font-semibold">{m.replace(/_/g, " ")}</th>)}
                    <th scope="col" className="px-3 py-2 font-semibold">Time</th>
                  </tr>
                </thead>
                {GROUPS.map((g) => {
                  const rows = r.scenarios.filter((s) => s.set === g.set);
                  if (!rows.length) return null;
                  return (
                    <tbody key={g.set}>
                      <tr className="border-t border-line bg-panel">
                        <th scope="colgroup" colSpan={r.metrics.length + 3} className="px-3 py-2 text-left text-sm font-semibold text-ink">
                          {g.label} <span className="font-normal text-ink-2">· {g.note}</span>
                        </th>
                      </tr>
                      {rows.map((s) => (
                        <tr key={s.id} className="border-t border-line align-top">
                          <th scope="row" className="px-3 py-2 text-left font-normal">
                            <span className="text-ink">{s.title}</span> <span className="ml-1 font-mono text-xs text-ink-3">{s.id}</span>
                          </th>
                          {s.error ? (
                            <td colSpan={r.metrics.length + 2} className="px-3 py-2 text-bad">Failed: {s.error}</td>
                          ) : (
                            <>
                              <td className="px-3 py-2 text-ink-2">{s.status ? statusLabel[s.status as keyof typeof statusLabel] ?? s.status : "–"}</td>
                              {r.metrics.map((m) => {
                                const v = s.metrics?.[m] as number | null | undefined;
                                return <td key={m} className="px-3 py-2"><Score v={v} /></td>;
                              })}
                              <td className="whitespace-nowrap px-3 py-2 text-ink-3">{s.ms ? `${(s.ms / 1000).toFixed(1)} s` : "–"}</td>
                            </>
                          )}
                        </tr>
                      ))}
                    </tbody>
                  );
                })}
              </table>
            </section>

            {r.scenarios.some((s) => s.metrics?.expectation_failures?.length || s.metrics?.unsupported_claims?.length) && (
              <section className="mt-10 grid gap-8 lg:grid-cols-2">
                <div>
                  <h2 className="text-lg font-semibold">Expectation failures</h2>
                  <ul className="mt-3 space-y-1.5 text-sm">
                    {r.scenarios.flatMap((s) => (s.metrics?.expectation_failures ?? []).map((f, i) => (
                      <li key={`${s.id}-${i}`}><span className="font-semibold text-accent">{s.id}</span> <span className="text-ink-2">{f}</span></li>
                    )))}
                  </ul>
                </div>
                <div>
                  <h2 className="text-lg font-semibold">Claims not supported by the retrieved pages</h2>
                  <ul className="mt-3 space-y-1.5 text-sm">
                    {r.scenarios.flatMap((s) => (s.metrics?.unsupported_claims ?? []).map((c, i) => (
                      <li key={`${s.id}-u${i}`}><span className="font-semibold text-accent">{s.id}</span> <span className="text-ink-2">{c}</span></li>
                    )))}
                  </ul>
                </div>
              </section>
            )}
          </>
        )}
      </main>
      <SiteFooter />
    </>
  );
}
