"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { ArrowUp, ChevronRight, CircleCheck, CircleDashed, CircleX, FileText, Loader2, SquarePen, TriangleAlert } from "lucide-react";
import { scenarios, scenarioById } from "@/data/scenarios";
import { referenceAnswers } from "@/data/reference-answers";
import { AssessResponse, statusLabel, type ChatMessage, type Report, type TraceStep } from "@/lib/report";
import { ReportView } from "./report/ReportView";

type Turn =
  | { role: "user"; content: string }
  | { role: "assistant"; content: string; trace: TraceStep[]; version?: number; questions?: string[]; error?: boolean };

interface Version { report: Report; exampleId?: string }

// "assess": free-text customer enquiries. "examples": the D01–H06 example enquiries, run in place.
export function Workbench({ mode = "assess" }: { mode?: "assess" | "examples" }) {
  const isExamples = mode === "examples";
  const [turns, setTurns] = useState<Turn[]>([]);
  const [versions, setVersions] = useState<Version[]>([]);
  const [active, setActive] = useState<number | null>(null);
  const [compare, setCompare] = useState(false);
  const [draft, setDraft] = useState("");
  const [exampleId, setExampleId] = useState<string>();
  const [pending, setPending] = useState(false);
  const threadRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => { threadRef.current?.scrollTo({ top: threadRef.current.scrollHeight, behavior: "smooth" }); }, [turns, pending]);

  const example = exampleId ? scenarioById(exampleId) : undefined;
  // An edited example is a new enquiry: it must not pick up the example's batch-run answer.
  const exampleUnchanged = example && draft.trim() === example.enquiry && turns.length === 0;


  const reset = () => { setTurns([]); setVersions([]); setActive(null); setCompare(false); setDraft(""); setExampleId(undefined); };

  // `fresh` starts a new conversation (used when an example is run).
  const submit = async (text: string, opts: { scenarioId?: string; fresh?: boolean } = {}) => {
    if (!text || pending) return;
    const { scenarioId, fresh = false } = opts;
    const prior = fresh ? [] : turns;
    const history: ChatMessage[] = prior.filter((t) => !(t.role === "assistant" && t.error)).map((t) => ({ role: t.role, content: t.content }));
    const messages = [...history, { role: "user" as const, content: text }];
    const firstExample = prior.length === 0 ? scenarioId : versions[0]?.exampleId;
    const version = (fresh ? 0 : versions.length) + 1;
    if (fresh) { setVersions([]); setActive(null); setCompare(false); }
    setTurns((t) => [...(fresh ? [] : t), { role: "user", content: text }]);
    setDraft("");
    setPending(true);
    try {
      const res = await fetch("/api/assess", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ messages, scenarioId }),
      });
      const json = await res.json();
      if (!res.ok) throw new Error(json.message ?? "The assessment failed.");
      const parsed = AssessResponse.safeParse(json);
      if (!parsed.success) throw new Error("The assessment service returned an answer in an unexpected format.");
      const { reply, report, trace } = parsed.data;
      setVersions((v) => [...(fresh ? [] : v), { report, exampleId: firstExample }]);
      setActive(version - 1);
      setCompare(false);
      setTurns((t) => [...t, { role: "assistant", content: reply, trace, version, questions: report.questions.map((q) => q.text) }]);
    } catch (e) {
      setTurns((t) => [...t, { role: "assistant", content: e instanceof Error ? e.message : "The assessment failed.", trace: [], error: true }]);
    } finally {
      setPending(false);
    }
  };

  const send = () => submit(draft.trim(), { scenarioId: exampleUnchanged ? exampleId : undefined });

  // Clicking an example places its enquiry in the message box as a fresh conversation;
  // the user sends it to generate the report.
  const runExample = (id: string) => {
    const s = scenarioById(id);
    if (!s || pending) return;
    setTurns([]); setVersions([]); setActive(null); setCompare(false);
    setExampleId(s.id);
    setDraft(s.enquiry);
    setFocusTick((n) => n + 1);
  };

  // Focus after render: in examples mode the message box only appears once an example is chosen.
  const [focusTick, setFocusTick] = useState(0);
  useEffect(() => {
    if (!focusTick) return;
    const el = inputRef.current;
    el?.focus();
    el?.setSelectionRange(el.value.length, el.value.length);
  }, [focusTick]);

  // ?example=H04 places that example enquiry in the message box on arrival.
  const runRef = useRef(runExample);
  runRef.current = runExample;
  useEffect(() => {
    const id = new URLSearchParams(window.location.search).get("example");
    if (id && scenarioById(id)) { window.history.replaceState(null, "", window.location.pathname); runRef.current(id); }
  }, []);

  const answerQuestions = (qs: string[]) => {
    setDraft(qs.map((q, i) => `${i + 1}. ${q}\n   Answer: `).join("\n"));
    inputRef.current?.focus();
  };

  const current = active !== null ? versions[active] : undefined;
  const reference = current?.exampleId && current.report.origin !== "reference" ? referenceAnswers[current.exampleId] : undefined;
  const shown = compare && reference ? reference : current?.report;
  const transcript = turns.map((t) => `${t.role === "user" ? "Client" : "Assistant"}: ${t.content}`).join("\n\n");

  return (
    <div className="print-layout flex h-[calc(100dvh-3.5rem-3px)] flex-col lg:flex-row">
      {/* Report sheet */}
      <main className="print-main order-2 min-h-0 flex-1 overflow-y-auto bg-bg px-4 pt-8 sm:px-10 lg:order-1">
        {shown ? (
          <ReportView
            key={`${active}-${compare}`}
            report={shown}
            transcript={transcript}
            toolbar={
              <>
                {versions.length > 1 && (
                  <span className="inline-flex overflow-hidden rounded-md border border-line">
                    {versions.map((_, i) => (
                      <button key={i} onClick={() => { setActive(i); setCompare(false); }} className={`px-2 py-0.5 ${i === active && !compare ? "bg-night text-night-ink" : "text-ink-2 hover:bg-panel"}`}>
                        v{i + 1}
                      </button>
                    ))}
                  </span>
                )}
                {reference && (
                  <button onClick={() => setCompare((c) => !c)} className={`rounded-md border px-2 py-0.5 ${compare ? "border-violet bg-violet text-white" : "border-line text-ink-2 hover:bg-panel"}`}>
                    {compare ? "Back to assistant report" : "Compare with organiser example"}
                  </button>
                )}
              </>
            }
          />
        ) : (
          <EmptySheet pending={pending} />
        )}
      </main>

      {/* Chat panel */}
      <aside className="print-hidden order-1 flex h-[55dvh] w-full shrink-0 flex-col border-b border-night-line bg-night text-night-ink lg:order-2 lg:h-auto lg:w-[440px] lg:border-b-0 lg:border-l">
        <div className="flex h-11 items-center justify-between border-b border-night-line px-4">
          <span className="text-sm font-semibold">{isExamples ? "Example enquiries" : "Customer conversation"}</span>
          <button onClick={reset} disabled={(!turns.length && !draft) || pending} className="inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-xs text-night-ink-2 hover:bg-night-2 hover:text-night-ink disabled:opacity-40">
            <SquarePen className="h-3.5 w-3.5" /> {isExamples ? "Back to the list" : "New assessment"}
          </button>
        </div>

        {isExamples && (turns.length > 0 || exampleUnchanged) && (
          <div className="border-b border-night-line px-4 py-2.5">
            <label className="flex items-center gap-2 text-xs text-night-ink-2">
              Example
              <select
                value={versions[0]?.exampleId ?? exampleId ?? ""}
                onChange={(e) => runExample(e.target.value)}
                disabled={pending}
                className="min-w-0 flex-1 rounded-md border border-night-line bg-night-2 px-2 py-1.5 text-sm text-night-ink focus:border-accent focus:outline-none"
              >
                {(["development", "evaluation"] as const).map((set) => (
                  <optgroup key={set} label={set === "development" ? "Development" : "Final evaluation"}>
                    {scenarios.filter((s) => s.set === set).map((s) => <option key={s.id} value={s.id}>{s.id} · {s.title}</option>)}
                  </optgroup>
                ))}
              </select>
            </label>
          </div>
        )}

        <div ref={threadRef} className="min-h-0 flex-1 space-y-5 overflow-y-auto px-4 py-5">
          {isExamples && turns.length === 0 && !pending && !exampleUnchanged && (
            <div>
              <p className="text-sm leading-relaxed text-night-ink-2">Choose an enquiry. It appears in the message box below; send it to generate the report.</p>
              {(["development", "evaluation"] as const).map((set) => (
                <div key={set} className="mt-5">
                  <h3 className="text-xs font-semibold text-night-ink-2">{set === "development" ? "Development enquiries" : "Final evaluation enquiries"}</h3>
                  <ul className="mt-2 space-y-1.5">
                    {scenarios.filter((s) => s.set === set).map((s) => (
                      <li key={s.id}>
                        <button onClick={() => runExample(s.id)} className="flex w-full items-start gap-2.5 rounded-lg border border-night-line bg-night-2 px-3 py-2.5 text-left text-sm hover:border-accent">
                          <span className="mt-px rounded bg-night-3 px-1.5 py-0.5 text-[11px] font-semibold text-accent">{s.id}</span>
                          <span className="leading-snug">{s.title}</span>
                        </button>
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          )}

          {isExamples && turns.length === 0 && !pending && exampleUnchanged && example && (
            <div className="rounded-lg border border-night-line bg-night-2 p-4">
              <div className="text-xs font-semibold text-accent">{example.id} · {example.title}</div>
              <p className="mt-2 text-sm leading-relaxed text-night-ink-2">The enquiry is in the message box below. Press Enter or the send button to generate the report.</p>
            </div>
          )}

          {!isExamples && turns.length === 0 && !pending && (
            <div className="pt-6">
              <h2 className="text-lg font-semibold">What does the customer need to measure?</h2>
              <p className="mt-2 text-sm leading-relaxed text-night-ink-2">
                Describe the process, the sample and any constraints in the customer&apos;s words. The assistant separates what they said from what is unknown, asks what is missing and cites the AFS material it uses.
              </p>
              <p className="mt-4 text-sm text-night-ink-3">You can answer its questions here and it will revise the report.</p>
              <p className="mt-4 text-sm text-night-ink-3">Want to see one first? <Link href="/how-it-works" className="font-medium text-ink underline underline-offset-2 hover:text-violet">See how it works</Link>.</p>
            </div>
          )}

          {turns.map((t, i) =>
            t.role === "user" ? (
              <div key={i} className="rounded-lg border border-night-line bg-night-2 px-3.5 py-2.5 text-sm leading-relaxed whitespace-pre-wrap">{t.content}</div>
            ) : (
              <AssistantTurn key={i} turn={t} activeVersion={active !== null ? active + 1 : undefined} onOpen={(v) => { setActive(v - 1); setCompare(false); }} onAnswer={answerQuestions} statusOf={(v) => versions[v - 1]?.report.decisionStatus} />
            ),
          )}

          {pending && (
            <div className="flex items-center gap-2 text-sm text-night-ink-2">
              <Loader2 className="h-4 w-4 animate-spin text-accent-bright" /> Assessing the enquiry…
            </div>
          )}
        </div>

        {/* Composer */}
        {(!isExamples || turns.length > 0 || draft) && (
        <div className="relative border-t border-night-line p-3">
          <div className="rounded-lg border border-night-line bg-night-2 focus-within:border-accent-bright">
            <textarea
              ref={inputRef}
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }}
              rows={4}
              placeholder={turns.length ? "Answer the questions or add details…" : "Describe the customer's process and what they need to measure…"}
              aria-label="Message"
              className="block max-h-64 w-full resize-none bg-transparent px-3 pt-3 text-sm leading-relaxed text-night-ink placeholder:text-night-ink-3 focus:outline-none focus-visible:outline-none"
            />
            <div className="flex items-center gap-2 px-2 pb-2">
              {exampleUnchanged && <span className="rounded bg-amber/15 px-1.5 py-0.5 text-[11px] font-medium text-amber">Example {exampleId}</span>}
              <span className="ml-auto hidden text-[11px] text-night-ink-3 sm:inline">Enter to send, Shift+Enter for a new line</span>
              <button onClick={send} disabled={!draft.trim() || pending} aria-label="Send" className="flex h-8 w-8 items-center justify-center rounded-md bg-accent text-white hover:bg-accent-dim disabled:bg-line disabled:text-ink-3">
                <ArrowUp className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>
        )}
      </aside>
    </div>
  );
}

const traceIcon = {
  ok: <CircleCheck className="h-3.5 w-3.5 text-ok" />,
  warn: <TriangleAlert className="h-3.5 w-3.5 text-amber" />,
  fail: <CircleX className="h-3.5 w-3.5 text-bad" />,
  skipped: <CircleDashed className="h-3.5 w-3.5 text-night-ink-3" />,
};

function AssistantTurn({ turn, activeVersion, onOpen, onAnswer, statusOf }: {
  turn: Extract<Turn, { role: "assistant" }>;
  activeVersion?: number;
  onOpen: (v: number) => void;
  onAnswer: (qs: string[]) => void;
  statusOf: (v: number) => Report["decisionStatus"] | undefined;
}) {
  const [open, setOpen] = useState(false);
  const total = turn.trace.reduce((s, t) => s + (t.ms ?? 0), 0);
  const status = turn.version ? statusOf(turn.version) : undefined;

  if (turn.error) {
    return (
      <div className="rounded-lg border border-bad/40 bg-bad/5 px-3.5 py-2.5 text-sm text-bad">
        <div className="mb-1 flex items-center gap-1.5 font-semibold"><CircleX className="h-4 w-4" /> No assessment</div>
        {turn.content}
      </div>
    );
  }

  return (
    <div className="rounded-lg bg-ai px-3.5 py-3 text-sm leading-relaxed">
      <div className="mb-1.5 flex items-center gap-2 text-xs font-semibold text-accent-bright">
        <span className="h-1.5 w-1.5 rounded-sm bg-accent-bright" /> SpectraSense
      </div>

      {turn.trace.length > 0 && (
        <div className="mb-2">
          <button onClick={() => setOpen((o) => !o)} aria-expanded={open} className="inline-flex items-center gap-1 text-xs text-night-ink-3 hover:text-night-ink-2">
            <ChevronRight className={`h-3.5 w-3.5 transition-transform ${open ? "rotate-90" : ""}`} />
            {turn.trace.length} steps{total ? ` in ${(total / 1000).toFixed(1)} s` : ""}
          </button>
          {open && (
            <ul className="mt-1.5 space-y-1 border-l border-night-line pl-3">
              {turn.trace.map((s, i) => (
                <li key={i} className="flex gap-2 text-xs">
                  <span className="mt-0.5">{traceIcon[s.status]}</span>
                  <span className="text-night-ink-2">{s.step}{s.detail && <span className="text-night-ink-3">: {s.detail}</span>}{s.ms !== undefined && <span className="text-night-ink-3"> · {s.ms} ms</span>}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      <p className="whitespace-pre-wrap text-night-ink">{turn.content}</p>

      {turn.questions && turn.questions.length > 0 && (
        <div className="mt-3 rounded-lg border border-line bg-bg p-3">
          <div className="mb-1.5 text-xs font-semibold text-amber">Questions for the customer</div>
          <ol className="list-decimal space-y-1 pl-4 text-night-ink-2">
            {turn.questions.map((q, i) => <li key={i}>{q}</li>)}
          </ol>
          <button onClick={() => onAnswer(turn.questions!)} className="mt-2.5 rounded-md bg-accent px-2.5 py-1 text-xs font-semibold text-white hover:bg-accent-dim">
            Answer these
          </button>
        </div>
      )}

      {turn.version && (
        <button onClick={() => onOpen(turn.version!)} className={`mt-3 flex w-full items-center gap-2 rounded-lg border px-3 py-2 text-left text-xs ${activeVersion === turn.version ? "border-accent bg-accent/10" : "border-night-line hover:bg-night-2"}`}>
          <FileText className="h-4 w-4 text-accent-bright" />
          <span className="font-semibold text-night-ink">Report v{turn.version}</span>
          {status && <span className="text-night-ink-2">{statusLabel[status]}</span>}
        </button>
      )}
    </div>
  );
}

function EmptySheet({ pending }: { pending: boolean }) {
  const parts = ["Requirements: stated facts and unknowns", "Clarification questions", "Recommended methods with page citations", "Measurement concept and spectral range", "Risks and uncertainty", "First feasibility experiment"];
  return (
    <div className="mx-auto max-w-2xl pt-10">
      <div className="h-1 w-12 bg-accent" />
      <h1 className="mt-6 text-[28px] font-semibold leading-tight tracking-tight">{pending ? "Writing the first assessment…" : "The assessment report appears here"}</h1>
      <p className="mt-3 font-serif text-[15.5px] leading-relaxed text-ink-2">
        Each reply in the conversation produces a new version of the report. Every important claim links to the AFS page it came from, so an expert can check it.
      </p>
      <ul className="mt-8 divide-y divide-line border-y border-line">
        {parts.map((p) => (
          <li key={p} className="flex items-center gap-3 py-3 text-sm text-ink-3">
            <span className="h-2 w-2 rounded-full bg-line-strong" /> {p}
          </li>
        ))}
      </ul>
    </div>
  );
}
