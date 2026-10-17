"use client";

import { useState } from "react";
import { Loader2, Play, RotateCcw, Lock } from "lucide-react";
import { scenarios, scenarioById, type Scenario } from "@/data/scenarios";
import { Report } from "@/lib/report";
import { ReportView } from "./report/ReportView";

type State =
  | { kind: "idle" }
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "done"; report: Report; enquiry: string };

const groups: { label: string; set: Scenario["set"] }[] = [
  { label: "Development · D01–D08", set: "development" },
  { label: "Final evaluation · H01–H06", set: "evaluation" },
];

export function Workbench() {
  const [scenarioId, setScenarioId] = useState<string | undefined>("D01");
  const [text, setText] = useState(scenarioById("D01")!.enquiry);
  const [state, setState] = useState<State>({ kind: "idle" });

  const scenario = scenarioId ? scenarioById(scenarioId) : undefined;
  const edited = scenario ? text.trim() !== scenario.enquiry : true;

  const pick = (s: Scenario) => {
    setScenarioId(s.id);
    setText(s.enquiry);
    setState({ kind: "idle" });
  };

  const run = async () => {
    setState({ kind: "loading" });
    try {
      const res = await fetch("/api/assess", {
        method: "POST",
        headers: { "content-type": "application/json" },
        // An edited scenario is a new enquiry: don't let it pick up the scenario's cached answer.
        body: JSON.stringify({ enquiry: text.trim(), scenarioId: edited ? undefined : scenarioId }),
      });
      const json = await res.json();
      if (!res.ok) return setState({ kind: "error", message: json.message ?? "Assessment failed." });
      const report = Report.safeParse(json);
      if (!report.success) return setState({ kind: "error", message: "The pipeline returned a report that does not match the expected structure." });
      setState({ kind: "done", report: report.data, enquiry: text.trim() });
    } catch {
      setState({ kind: "error", message: "Could not reach the assessment service." });
    }
  };

  return (
    <div className="mx-auto grid max-w-[1400px] gap-6 px-4 py-6 sm:px-6 lg:grid-cols-[380px_1fr]">
      <aside className="space-y-4 lg:sticky lg:top-20 lg:h-[calc(100vh-6rem)] lg:overflow-y-auto lg:pr-1">
        <div className="rounded-lg border border-line bg-panel p-4">
          <label htmlFor="enquiry" className="flex items-center justify-between text-xs font-medium uppercase tracking-[0.14em] text-ink-2">
            Customer enquiry
            <span className="font-mono normal-case tracking-normal text-ink-3">
              {scenario && !edited ? scenario.id : "your enquiry"}
            </span>
          </label>
          <textarea
            id="enquiry"
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={9}
            placeholder="Paste a short customer use case…"
            className="mt-2 w-full resize-y rounded-md border border-line bg-bg/70 p-3 text-sm leading-relaxed text-ink placeholder:text-ink-3 focus:border-cyan focus:outline-none"
          />
          <p className="mt-1.5 flex items-center gap-1.5 text-[11px] text-ink-3">
            <Lock className="h-3 w-3" aria-hidden /> Anything the client did not state is treated as unknown, never as fact.
          </p>
          {scenario?.factsStated && !edited && (
            <div className="mt-3">
              <div className="text-[10px] font-medium uppercase tracking-wider text-ink-3">Facts stated (organizer list)</div>
              <div className="mt-1 flex flex-wrap gap-1">
                {scenario.factsStated.map((f) => <span key={f} className="rounded bg-panel-2 px-1.5 py-0.5 text-[11px] text-ink-2">{f}</span>)}
              </div>
            </div>
          )}
          <div className="mt-4 flex gap-2">
            <button
              onClick={run}
              disabled={!text.trim() || state.kind === "loading"}
              className="glow inline-flex flex-1 items-center justify-center gap-2 rounded-md bg-cyan px-4 py-2.5 text-sm font-semibold text-bg hover:bg-white disabled:opacity-50"
            >
              {state.kind === "loading" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
              Run assessment
            </button>
            {scenario && edited && (
              <button onClick={() => pick(scenario)} title="Restore scenario text" className="rounded-md border border-line px-3 text-ink-2 hover:border-cyan">
                <RotateCcw className="h-4 w-4" /><span className="sr-only">Restore scenario text</span>
              </button>
            )}
          </div>
        </div>

        {groups.map((g) => (
          <div key={g.set} className="rounded-lg border border-line bg-panel p-2">
            <div className="px-2 py-1.5 font-mono text-[10px] uppercase tracking-wider text-ink-3">{g.label}</div>
            <ul>
              {scenarios.filter((s) => s.set === g.set).map((s) => {
                const on = s.id === scenarioId;
                return (
                  <li key={s.id}>
                    <button
                      onClick={() => pick(s)}
                      aria-current={on}
                      className={`flex w-full gap-2.5 rounded px-2 py-1.5 text-left text-sm transition ${on ? "bg-cyan/10 text-ink" : "text-ink-2 hover:bg-panel-2"}`}
                    >
                      <span className={`font-mono text-xs ${on ? "text-cyan" : "text-ink-3"}`}>{s.id}</span>
                      <span className="leading-snug">{s.title}</span>
                    </button>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </aside>

      <main className="min-w-0">
        {state.kind === "done" && <ReportView report={state.report} enquiry={state.enquiry} />}
        {state.kind === "idle" && (
          <Placeholder title="Ready to assess" text="Pick a scenario or paste an enquiry, then run the assessment. The report follows the AFS answer structure: requirements, questions, recommendation, concept, spectral range, risks, feasibility plan, sources." />
        )}
        {state.kind === "loading" && <Placeholder title="Assessing…" text="Extracting stated facts, checking premises and composing a cited answer." loading />}
        {state.kind === "error" && <Placeholder title="No assessment available" text={state.message} tone="warn" />}
      </main>
    </div>
  );
}

function Placeholder({ title, text, loading, tone }: { title: string; text: string; loading?: boolean; tone?: "warn" }) {
  return (
    <div className={`grid-bg flex min-h-[60vh] flex-col items-center justify-center rounded-lg border p-10 text-center ${tone === "warn" ? "border-warn/40" : "border-line"}`}>
      <div className="spectrum-line h-[2px] w-40 rounded opacity-80" />
      {loading && <Loader2 className="mt-6 h-6 w-6 animate-spin text-cyan" />}
      <h2 className={`mt-6 text-xl font-semibold ${tone === "warn" ? "text-warn" : ""}`}>{title}</h2>
      <p className="mt-2 max-w-lg text-sm leading-relaxed text-ink-2">{text}</p>
    </div>
  );
}
