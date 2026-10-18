"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { ArrowUp, ChevronRight, CircleCheck, CircleDashed, CircleX, FileCheck2, FileText, Loader2, SquarePen, TriangleAlert } from "lucide-react";
import { scenarioById } from "@/data/scenarios";
import { referenceAnswers } from "@/data/reference-answers";
import { AssessResponse, openQuestions, questionText, statusLabel, type Answer, type ChatMessage, type Question, type Report, type TraceStep } from "@/lib/report";
import { ReportView } from "./report/ReportView";
import { readableSources } from "@/lib/sources";
import { Button } from "./ui/button";
import { AnimatedBackground } from "./motion-primitives/animated-background";
import { BorderTrail } from "./motion-primitives/border-trail";
import { Disclosure, DisclosureContent, DisclosureTrigger } from "./motion-primitives/disclosure";
import { ScrollProgress } from "./motion-primitives/scroll-progress";
import { TextShimmer } from "./motion-primitives/text-shimmer";
import { useReducedMotion } from "motion/react";

type Turn =
  | { role: "user"; content: string }
  | { role: "assistant"; content: string; trace: TraceStep[]; version?: number; questions?: Question[]; final?: boolean; error?: boolean };

interface Version { report: Report; exampleId?: string }

// Free-text customer enquiries; /assess?example=ID places one of the example enquiries in the message box.
export function Workbench() {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [versions, setVersions] = useState<Version[]>([]);
  const [active, setActive] = useState<number | null>(null);
  const [compare, setCompare] = useState(false);
  const [draft, setDraft] = useState("");
  const [exampleId, setExampleId] = useState<string>();
  const [pending, setPending] = useState(false);
  const threadRef = useRef<HTMLDivElement>(null);
  const reportRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => { threadRef.current?.scrollTo({ top: threadRef.current.scrollHeight, behavior: "smooth" }); }, [turns, pending]);
  // The message box grows with its text (up to half the screen), so a normal enquiry is visible without scrolling inside it.
  useEffect(() => {
    const el = inputRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, Math.round(window.innerHeight * 0.45))}px`;
  }, [draft]);

  const example = exampleId ? scenarioById(exampleId) : undefined;
  // An edited example is a new enquiry: it must not pick up the example's batch-run answer.
  const exampleUnchanged = example && draft.trim() === example.enquiry && turns.length === 0;


  const reset = () => { setTurns([]); setVersions([]); setActive(null); setCompare(false); setDraft(""); setExampleId(undefined); };

  // `fresh` starts a new conversation (used when an example is run).
  const submit = async (text: string, opts: { scenarioId?: string; fresh?: boolean; answers?: Answer[]; final?: boolean } = {}) => {
    if (!text || pending) return;
    const { scenarioId, fresh = false, answers = [], final = false } = opts;
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
        body: JSON.stringify({ messages, scenarioId, answers, final }),
      });
      const json = await res.json();
      if (!res.ok) throw new Error(json.message ?? "The assessment failed.");
      const parsed = AssessResponse.safeParse(json);
      if (!parsed.success) throw new Error("The assessment service returned an answer in an unexpected format.");
      const { reply, report, trace } = parsed.data;
      setVersions((v) => [...(fresh ? [] : v), { report, exampleId: firstExample }]);
      setActive(version - 1);
      setCompare(false);
      setTurns((t) => [...t, { role: "assistant", content: reply, trace, version, questions: openQuestions(report), final: report.mode === "final" }]);
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

  // Focus the message box after an example enquiry is placed in it.
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

  // Answers from the per-question form, each bound to its question id; the message text carries them for the transcript.
  const sendAnswers = (answers: Answer[], extra: string, final: boolean) => {
    const lines: string[] = [];
    if (answers.length) {
      lines.push("Answers to your questions:");
      for (const a of answers) {
        const value = a.status === "answered_unknown" ? "unknown" : a.status === "declined" ? "(no answer, declined)" : a.answer;
        lines.push(`- Q: ${a.question}`, `  A: ${value}`);
      }
    }
    if (extra.trim()) lines.push(...(lines.length ? [""] : []), `Additional details: ${extra.trim()}`);
    if (final) lines.push(...(lines.length ? [""] : []), "Please give the final assessment now, without further questions.");
    submit(lines.join("\n"), { answers, final });
  };
  const lastAssistant = turns.reduce((last, t, i) => (t.role === "assistant" && !t.error ? i : last), -1);

  const current = active !== null ? versions[active] : undefined;
  const reference = current?.exampleId && current.report.origin !== "reference" ? referenceAnswers[current.exampleId] : undefined;
  const shown = compare && reference ? reference : current?.report;
  const transcript = turns.map((t) => `${t.role === "user" ? "Client" : "Assistant"}: ${t.content}`).join("\n\n");

  return (
    <div className="print-layout flex h-[calc(100dvh-3.5rem-3px)] flex-col lg:flex-row">
      {/* Report sheet */}
      {/* `relative` keeps absolutely positioned children (sr-only labels) inside this scroller, so the page itself never scrolls.
          The padding sits on the inner sheet: a sticky bar in a padded scroller sticks below the padding and lets text show above it. */}
      <div ref={reportRef} className="print-main relative order-2 min-h-0 flex-1 overflow-y-auto bg-bg lg:order-1">
        {shown && <ScrollProgress containerRef={reportRef} className="print-hidden sticky top-0 z-20 h-0.5 bg-accent" />}
        <div className="px-4 pt-8 sm:px-10 print:p-0">
        {shown ? (
          <ReportView
            key={`${active}-${compare}`}
            report={shown}
            transcript={transcript}
            toolbar={
              <>
                {versions.length > 1 && (
                  <span role="group" aria-label="Report versions" className="inline-flex border border-line">
                    <AnimatedBackground defaultValue={compare ? undefined : `v${active}`} className="bg-ink" transition={{ type: "spring", bounce: 0, duration: 0.3 }}>
                      {versions.map((_, i) => (
                        <button
                          key={i}
                          data-id={`v${i}`}
                          aria-pressed={i === active && !compare}
                          onClick={() => { setActive(i); setCompare(false); }}
                          className="min-h-6 px-2.5 text-ink-2 data-[checked=true]:text-bg"
                        >
                          v{i + 1}
                        </button>
                      ))}
                    </AnimatedBackground>
                  </span>
                )}
                {reference && (
                  <Button size="xs" variant={compare ? "secondary" : "outline"} onClick={() => setCompare((c) => !c)}>
                    {compare ? "Back to assistant report" : "Compare with organiser example"}
                  </Button>
                )}
              </>
            }
          />
        ) : (
          <EmptySheet pending={pending} />
        )}
        </div>
      </div>

      {/* Chat panel */}
      <aside className="print-hidden order-1 flex h-[55dvh] w-full shrink-0 flex-col border-b border-night-line bg-night text-night-ink lg:order-2 lg:h-auto lg:w-[440px] lg:border-b-0 lg:border-l xl:w-[520px]">
        <div className="flex h-11 items-center justify-between border-b border-night-line px-4">
          <span className="text-sm font-semibold">Customer conversation</span>
          <Button variant="ghost" size="sm" onClick={reset} disabled={(!turns.length && !draft) || pending}>
            <SquarePen aria-hidden /> New assessment
          </Button>
        </div>

        <div ref={threadRef} aria-busy={pending} className="min-h-0 flex-1 space-y-5 overflow-y-auto px-4 py-5">
          {turns.length === 0 && !pending && (
            <div className="pt-4">
              <h2 className="text-lg font-semibold">What does the customer need to measure?</h2>
              <p className="mt-2 text-sm leading-relaxed text-night-ink-2">
                Paste or describe the enquiry in the customer&apos;s words. SpectraSense separates what they said from what is unknown,
                asks only the questions that could change the method, and cites the AFS material for every recommendation.
              </p>
              <h3 className="mt-5 text-sm font-semibold">A good enquiry mentions</h3>
              <ul className="mt-2 space-y-1.5 text-sm text-night-ink-2">
                {[
                  ["What to measure", "the substance or property, and any qualifier (\u201cviable\u201d, \u201cdissolved\u201d)"],
                  ["The sample", "liquid, powder or solid; clear or turbid; temperature"],
                  ["Where it is measured", "in the line, a free port or window, the distance to an analyser"],
                  ["Equipment already owned", "a spectrometer, probe or fibre cable"],
                  ["How success is judged", "the reference method and the decision it supports"],
                ].map(([k, v]) => (
                  <li key={k} className="flex gap-2"><span className="mt-2 h-1 w-1 shrink-0 rounded-full bg-accent" aria-hidden /><span><span className="text-night-ink">{k}</span>: {v}</span></li>
                ))}
              </ul>
              <p className="mt-3 text-xs text-night-ink-3">Missing details are fine: the assistant asks for what matters, and &ldquo;Don&apos;t know&rdquo; is a valid answer.</p>
              <p className="mt-5 text-sm text-night-ink-3">New here? <Link href="/how-it-works" className="text-accent underline underline-offset-2">See how it works</Link>, with worked examples you can try.</p>
            </div>
          )}

          {turns.map((t, i) =>
            t.role === "user" ? (
              <div key={i} className="rounded-lg border border-night-line bg-night-2 px-3.5 py-2.5 text-sm leading-relaxed whitespace-pre-wrap">{t.content}</div>
            ) : (
              <AssistantTurn key={i} turn={t} latest={i === lastAssistant} busy={pending} activeVersion={active !== null ? active + 1 : undefined} onOpen={(v) => { setActive(v - 1); setCompare(false); }} onAnswer={sendAnswers} statusOf={(v) => versions[v - 1]?.report.decisionStatus} />
            ),
          )}

          {pending && <PendingSteps />}
        </div>

        {/* Composer */}
        <div className="relative border-t border-night-line p-3">
          <div className="border border-line-strong bg-night-2 focus-within:border-accent focus-within:outline focus-within:outline-2 focus-within:outline-accent">
            <textarea
              ref={inputRef}
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }}
              rows={4}
              placeholder={turns.length ? "Answer the questions or add details…" : "Describe the customer's process and what they need to measure…"}
              aria-label="Message"
              className="block max-h-[45dvh] min-h-24 w-full resize-none overflow-y-auto bg-transparent px-3 pt-3 text-sm leading-relaxed text-night-ink placeholder:text-night-ink-3 focus:outline-none focus-visible:outline-none"
            />
            <div className="flex items-center gap-2 px-2 pb-2">
              {exampleUnchanged && <span className="border border-accent px-1.5 py-0.5 text-xs text-accent">Example enquiry</span>}
              <span className="ml-auto hidden text-xs text-night-ink-3 sm:inline">Enter to send, Shift+Enter for a new line</span>
              {versions.length > 0 && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => sendAnswers([], draft, true)}
                  disabled={pending}
                  title="Ask for the final report: no question block, open points listed as assumptions"
                >
                  <FileCheck2 aria-hidden /> Final report
                </Button>
              )}
              <Button size="icon-sm" onClick={send} disabled={!draft.trim() || pending} aria-label="Send">
                <ArrowUp aria-hidden />
              </Button>
            </div>
          </div>
        </div>
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

function AssistantTurn({ turn, latest, busy, activeVersion, onOpen, onAnswer, statusOf }: {
  turn: Extract<Turn, { role: "assistant" }>;
  latest: boolean;
  busy: boolean;
  activeVersion?: number;
  onOpen: (v: number) => void;
  onAnswer: (answers: Answer[], extra: string, final: boolean) => void;
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
        <Disclosure open={open} onOpenChange={setOpen} className="mb-2" transition={{ type: "spring", bounce: 0, duration: 0.25 }}>
          <DisclosureTrigger>
            <button type="button" className="inline-flex min-h-6 items-center gap-1 text-xs text-night-ink-3 hover:text-night-ink-2">
              <ChevronRight className={`h-3.5 w-3.5 transition-transform ${open ? "rotate-90" : ""}`} aria-hidden />
              {turn.trace.length} steps{total ? ` in ${(total / 1000).toFixed(1)} s` : ""}
            </button>
          </DisclosureTrigger>
          <DisclosureContent>
            <ul className="mt-1.5 space-y-1 border-l border-night-line pl-3">
              {turn.trace.map((s, i) => (
                <li key={i} className="flex gap-2 text-xs">
                  <span className="mt-0.5">{traceIcon[s.status]}</span>
                  <span className="text-night-ink-2">{s.step}{s.detail && <span className="text-night-ink-3">: {readableSources(s.detail)}</span>}{s.ms !== undefined && <span className="text-night-ink-3"> · {s.ms} ms</span>}</span>
                </li>
              ))}
            </ul>
          </DisclosureContent>
        </Disclosure>
      )}

      <p className="whitespace-pre-wrap text-night-ink">{turn.content}</p>

      {turn.questions && turn.questions.length > 0 && (
        latest ? (
          <QuestionForm questions={turn.questions} onSend={onAnswer} busy={busy} />
        ) : (
          <div className="mt-3 rounded-lg border border-night-line p-3">
            <div className="mb-1.5 text-xs font-semibold text-night-ink-3">Questions asked</div>
            <ol className="list-decimal space-y-1 pl-4 text-night-ink-3">
              {turn.questions.map((q) => <li key={q.id ?? q.text}>{questionText(q)}</li>)}
            </ol>
          </div>
        )
      )}
      {turn.final && <div className="mt-3 text-xs font-semibold text-accent-bright">Final report: no further questions; open points are listed as assumptions and points to confirm.</div>}

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

type Entry = { status: "answered" | "answered_unknown" | "declined"; answer: string };

// One input per question, so each answer is bound to its question (no answers under the wrong question).
// Stays mounted while the answers are being assessed (disabled), so a failed request keeps what was typed.
function QuestionForm({ questions, onSend, busy }: { questions: Question[]; onSend: (answers: Answer[], extra: string, final: boolean) => void; busy: boolean }) {
  const [entries, setEntries] = useState<Record<string, Entry>>({});
  const [extra, setExtra] = useState("");
  const key = (q: Question) => q.id ?? q.text;
  const set = (q: Question, e: Partial<Entry>) => setEntries((s) => ({ ...s, [key(q)]: { ...(s[key(q)] ?? { status: "answered", answer: "" }), ...e } }));
  const answers: Answer[] = questions.flatMap((q) => {
    const e = entries[key(q)];
    if (!e || (e.status === "answered" && !e.answer.trim())) return [];
    return [{ id: q.id, question: q.text, status: e.status, ...(e.status === "answered" ? { answer: e.answer.trim() } : {}) }];
  });
  // Toggle chips: outlined when pressed (a tinted fill under the accent text fails contrast); 24 px minimum target.
  const chip = (on: boolean) =>
    `inline-flex min-h-6 items-center rounded border px-2 text-xs ${on ? "border-amber font-semibold text-amber" : "border-transparent text-night-ink-3 hover:text-night-ink-2"}`;

  return (
    <fieldset disabled={busy} className="mt-3 rounded-lg border border-line bg-bg p-3 text-ink disabled:opacity-70">
      <legend className="sr-only">Answers to the questions for the customer</legend>
      <div className="mb-2 text-xs font-semibold text-amber">Questions for the customer</div>
      <ol className="space-y-3">
        {questions.map((q, i) => {
          const e = entries[key(q)];
          return (
            <li key={key(q)}>
              <label htmlFor={`answer-${key(q)}`} className="text-sm text-ink-2">{i + 1}. {questionText(q)}</label>
              <div className="mt-1 flex items-start gap-2">
                <textarea
                  id={`answer-${key(q)}`}
                  rows={1}
                  value={e?.status === "answered" ? e.answer : ""}
                  disabled={e?.status === "answered_unknown" || e?.status === "declined"}
                  onChange={(ev) => set(q, { status: "answered", answer: ev.target.value })}
                  placeholder={e?.status === "answered_unknown" ? "Customer does not know" : e?.status === "declined" ? "Customer will not answer" : "Customer's answer"}
                  className="min-h-8 flex-1 resize-y rounded-md border border-line-strong bg-panel px-2 py-1 text-sm disabled:opacity-60"
                />
                <button type="button" aria-pressed={e?.status === "answered_unknown"} onClick={() => set(q, { status: e?.status === "answered_unknown" ? "answered" : "answered_unknown", answer: "" })} className={chip(e?.status === "answered_unknown")}>Don&apos;t know</button>
                <button type="button" aria-pressed={e?.status === "declined"} onClick={() => set(q, { status: e?.status === "declined" ? "answered" : "declined", answer: "" })} className={chip(e?.status === "declined")}>Skip</button>
              </div>
            </li>
          );
        })}
      </ol>
      <label htmlFor="answer-extra" className="mt-3 block text-sm text-ink-2">Other details from the customer <span className="text-ink-3">(optional)</span></label>
      <textarea
        id="answer-extra"
        rows={2}
        value={extra}
        onChange={(ev) => setExtra(ev.target.value)}
        placeholder="Anything the customer said that the questions do not cover"
        className="mt-1 w-full resize-y rounded-md border border-line-strong bg-panel px-2 py-1 text-sm"
      />
      <div className="mt-2 flex flex-wrap gap-2">
        <Button size="sm" onClick={() => onSend(answers, extra, false)} disabled={!answers.length && !extra.trim()}>
          Send answers
        </Button>
        <Button size="sm" variant="outline" onClick={() => onSend(answers, extra, true)}>
          Final report, no more questions
        </Button>
      </div>
    </fieldset>
  );
}

// The backend does not stream which step is running, so this lists what the pipeline does and the elapsed
// time, without claiming a current step.
const PIPELINE = ["Safety gate", "Plan the turn", "Separate facts and unknowns", "Retrieve AFS pages", "Premise checks", "Compose the assessment", "Verify citations", "Validate numbers, claims and questions"];

function PendingSteps() {
  const reduce = useReducedMotion();
  const [seconds, setSeconds] = useState(0);
  useEffect(() => {
    const t = setInterval(() => setSeconds((s) => s + 1), 1000);
    return () => clearInterval(t);
  }, []);
  return (
    <div role="status" className="relative border border-night-line px-3.5 py-3 text-sm text-night-ink-2">
      {!reduce && <BorderTrail size={56} transition={{ repeat: Infinity, duration: 4, ease: "linear" }} />}
      <div className="flex items-center gap-2 text-night-ink">
        <Loader2 className="h-4 w-4 animate-spin text-accent-bright" aria-hidden />
        {reduce ? <span>Assessing…</span> : <TextShimmer as="span" duration={1.6}>Assessing…</TextShimmer>}
        <span className="tabular-nums text-night-ink-3">{seconds} s</span>
      </div>
      <p className="mt-1 text-xs text-night-ink-3">The pipeline runs these checks on every answer; an assessment usually takes 10–60 s.</p>
      <ol className="mt-2 grid grid-cols-1 gap-0.5 text-xs text-night-ink-3 sm:grid-cols-2">
        {PIPELINE.map((s, i) => <li key={s}>{i + 1}. {s}</li>)}
      </ol>
    </div>
  );
}

function EmptySheet({ pending }: { pending: boolean }) {
  const parts = ["Requirements: stated facts and unknowns", "Clarification questions", "Recommended methods with page citations", "Measurement concept and spectral range", "Risks and uncertainty", "First feasibility experiment"];
  return (
    <div className="mx-auto max-w-2xl pt-10">
      <div className="h-1 w-12 bg-accent" />
      <h2 className="mt-6 text-[2rem] font-light leading-tight">{pending ? "Writing the first assessment…" : "The assessment report appears here"}</h2>
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
