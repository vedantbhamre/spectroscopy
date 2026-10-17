import { promises as fs } from "fs";
import path from "path";
import { SiteHeader } from "@/components/SiteHeader";

export const metadata = { title: "Evals · SpectraSense" };
export const dynamic = "force-dynamic";

// Results written by `python -m evals.run_evals` (backend). Generated, never edited by hand.
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

const tone = (v: number | null | undefined) =>
  v === null || v === undefined ? "text-ink-3" : v >= 0.8 ? "text-ok" : v >= 0.5 ? "text-warn" : "text-bad";
const fmt = (v: unknown) => (typeof v === "number" ? v.toFixed(2) : "–");

export default async function EvalsPage() {
  const r = await load();
  return (
    <>
      <SiteHeader />
      <main className="mx-auto max-w-[1200px] px-5 pb-20 pt-12 sm:px-8 lg:px-10">
        <h1 className="text-3xl font-semibold tracking-tight">Evaluation</h1>
        <p className="mt-2 max-w-3xl text-ink-2">
          RAGAS-style metrics scored by a separate judge model, plus deterministic checks that cost nothing. Scores run from 0 to 1;
          a dash means the metric does not apply (for example, no organiser reference for that scenario).
        </p>

        {!r ? (
          <div className="mt-10 rounded-lg border border-line bg-panel p-6">
            <h2 className="font-semibold">No eval run yet</h2>
            <p className="mt-2 text-sm text-ink-2">Run the evals from the backend folder, then reload this page:</p>
            <pre className="mt-3 overflow-x-auto rounded bg-bg p-3 text-sm">cd backend{"\n"}.venv/bin/python -m evals.run_evals</pre>
          </div>
        ) : (
          <>
            <p className="mt-6 text-sm text-ink-3">
              Run {new Date(r.run_at).toLocaleString()} · {r.mode} · judge: {r.judge ?? "off"} · {r.judge_calls} judge calls
            </p>

            <section className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
              {r.metrics.map((m) => (
                <div key={m} className="rounded-lg border border-line bg-bg p-4">
                  <div className="text-xs text-ink-3">{m.replace(/_/g, " ")}</div>
                  <div className={`mt-1 text-2xl font-semibold ${tone(r.summary[m]?.all)}`}>{fmt(r.summary[m]?.all)}</div>
                  <div className="mt-1 text-[11px] leading-snug text-ink-3">{ABOUT[m]}</div>
                  <div className="mt-2 text-[11px] text-ink-2">dev {fmt(r.summary[m]?.development)} · final {fmt(r.summary[m]?.evaluation)}</div>
                </div>
              ))}
            </section>

            <section className="mt-10 overflow-x-auto rounded-lg border border-line">
              <table className="w-full min-w-[900px] text-sm">
                <thead className="bg-panel-2 text-left text-xs text-ink-2">
                  <tr>
                    <th className="px-3 py-2 font-semibold">Scenario</th>
                    <th className="px-3 py-2 font-semibold">Status</th>
                    {r.metrics.map((m) => <th key={m} className="px-3 py-2 font-semibold">{m.replace(/_/g, " ")}</th>)}
                    <th className="px-3 py-2 font-semibold">Time</th>
                  </tr>
                </thead>
                <tbody>
                  {r.scenarios.map((s) => (
                    <tr key={s.id} className="border-t border-line align-top">
                      <td className="px-3 py-2"><span className="font-semibold text-accent">{s.id}</span> <span className="text-ink-2">{s.title}</span></td>
                      {s.error ? (
                        <td colSpan={r.metrics.length + 2} className="px-3 py-2 text-bad">Failed: {s.error}</td>
                      ) : (
                        <>
                          <td className="px-3 py-2 text-ink-2">{s.status}</td>
                          {r.metrics.map((m) => {
                            const v = s.metrics?.[m] as number | null | undefined;
                            return <td key={m} className={`px-3 py-2 tabular-nums ${tone(v)}`}>{fmt(v)}</td>;
                          })}
                          <td className="px-3 py-2 text-ink-3">{s.ms ? `${(s.ms / 1000).toFixed(1)} s` : "–"}</td>
                        </>
                      )}
                    </tr>
                  ))}
                </tbody>
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
    </>
  );
}
