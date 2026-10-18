"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { ArrowRight, ArrowUp, Check, Circle, RotateCcw, TriangleAlert, X } from "lucide-react";
import { demoCases, type DemoCase } from "@/data/demo-conversations";
import { statusLabel } from "@/lib/report";
import { Citations } from "../report/CitationChip";
import { readableSources } from "@/lib/sources";

// Plays a scripted conversation step by step: enquiry, pipeline trace, reply, questions.
type Stage = { trace: number; reply: number; words: number; questions: boolean; done: boolean };
const START: Stage = { trace: 0, reply: 0, words: 0, questions: false, done: false };
const FULL = (c: DemoCase): Stage => ({ trace: c.trace.length, reply: c.reply.length, words: 0, questions: true, done: true });

const traceIcon = {
  ok: <Check className="h-3.5 w-3.5 text-ok" />,
  warn: <TriangleAlert className="h-3.5 w-3.5 text-warn" />,
  fail: <X className="h-3.5 w-3.5 text-bad" />,
  skipped: <Circle className="h-3 w-3 text-ink-3" />,
};
const statusTone = { provisional: "border-ink text-ink", insufficient: "border-warn text-warn", out_of_scope: "border-bad text-bad" };

export function ChatDemo() {
  const [idx, setIdx] = useState(0);
  const [stage, setStage] = useState<Stage>(START);
  const [run, setRun] = useState(0);
  const [inView, setInView] = useState(false);
  const wrap = useRef<HTMLDivElement>(null);
  const thread = useRef<HTMLDivElement>(null);
  const c = demoCases[idx];

  useEffect(() => {
    const io = new IntersectionObserver(([e]) => e.isIntersecting && setInView(true), { threshold: 0.35 });
    if (wrap.current) io.observe(wrap.current);
    return () => io.disconnect();
  }, []);

  // Script timeline.
  useEffect(() => {
    if (!inView) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) { setStage(FULL(c)); return; }
    setStage(START);
    const timers: ReturnType<typeof setTimeout>[] = [];
    let t = 900;
    const at = (ms: number, fn: () => void) => timers.push(setTimeout(fn, (t += ms)));
    c.trace.forEach((_, i) => at(i ? 520 : 0, () => setStage((s) => ({ ...s, trace: i + 1 }))));
    c.reply.forEach((p, i) => {
      at(i ? 380 : 600, () => setStage((s) => ({ ...s, reply: i + 1, words: 0 })));
      const n = p.text.split(" ").length;
      for (let w = 1; w <= n; w++) at(28, () => setStage((s) => ({ ...s, words: w })));
    });
    at(450, () => setStage((s) => ({ ...s, questions: true })));
    at(300, () => setStage((s) => ({ ...s, done: true })));
    return () => timers.forEach(clearTimeout);
  }, [idx, run, inView, c]);

  useEffect(() => { thread.current?.scrollTo({ top: thread.current.scrollHeight, behavior: "smooth" }); }, [stage]);

  const replying = stage.trace === c.trace.length && !stage.done;

  return (
    <div ref={wrap} className="grid gap-6 lg:grid-cols-[320px_1fr]">
      {/* Use cases */}
      <div role="tablist" aria-label="Use cases" className="flex gap-2 overflow-x-auto lg:flex-col lg:overflow-visible">
        {demoCases.map((d, i) => {
          const on = i === idx;
          return (
            <button
              key={d.id}
              role="tab"
              aria-selected={on}
              onClick={() => { setIdx(i); setRun((r) => r + 1); }}
              className={`min-w-[220px] rounded-lg border px-4 py-3.5 text-left transition-colors lg:min-w-0 ${on ? "border-ink bg-night-2" : "border-line hover:border-line-strong"}`}
            >
              <div className="flex items-center gap-2 text-base text-ink">
                {on && <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-accent" aria-hidden />}
                {d.label}
              </div>
              <div className="mt-0.5 text-sm text-ink-2">{d.lesson}</div>
            </button>
          );
        })}
        <p className="hidden px-1 pt-2 text-xs leading-relaxed text-ink-3 lg:block">
          These are prepared examples that show how the assistant behaves; every quote in them was checked on the cited page. Pick one, watch it play, then try the same enquiry yourself.
        </p>
      </div>

      {/* Chat window */}
      <div className="flex h-[620px] flex-col overflow-hidden rounded-xl border border-line bg-night-2">
        <div className="flex h-12 items-center justify-between border-b border-line px-4">
          <div className="flex items-center gap-2 text-sm">
            <span className="h-2 w-2 rounded-full bg-violet" />
            <span style={{ fontWeight: 500 }}>SpectraSense</span>
            <span className="text-ink-3">· Example: {c.label}</span>
          </div>
          <button onClick={() => setRun((r) => r + 1)} className="inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-xs text-ink-2 hover:bg-panel hover:text-ink">
            <RotateCcw className="h-3.5 w-3.5" /> Replay
          </button>
        </div>

        <div ref={thread} className="min-h-0 flex-1 space-y-5 overflow-y-auto px-4 py-6 sm:px-6" aria-live="polite">
          {inView && (
            <div className="ml-auto max-w-[85%] animate-[fadeUp_.4s_ease_both] rounded-2xl rounded-br-md bg-ink px-4 py-3 text-[14.5px] leading-relaxed text-bg">
              <div className="mb-1 text-xs uppercase tracking-[0.12em] opacity-70">Customer</div>
              {c.enquiry}
            </div>
          )}

          {stage.trace > 0 && (
            <ul className="space-y-1.5 border-l border-line pl-4">
              {c.trace.slice(0, stage.trace).map((s) => (
                <li key={s.step} className="flex animate-[fadeUp_.35s_ease_both] items-start gap-2 text-[13px]">
                  <span className="mt-0.5">{traceIcon[s.status]}</span>
                  <span className="text-ink-2">{s.step}<span className="text-ink-3"> · {readableSources(s.detail ?? "")}</span></span>
                </li>
              ))}
            </ul>
          )}

          {stage.reply > 0 && (
            <div className="max-w-[92%] animate-[fadeUp_.4s_ease_both]">
              <div className="mb-2 flex flex-wrap items-center gap-2">
                <span className={`rounded-full border px-2.5 py-0.5 text-[12px] ${statusTone[c.status]}`}>{statusLabel[c.status]}</span>
                <span className="text-[12px] text-ink-3">{c.statusNote}</span>
              </div>
              <div className="space-y-2.5 font-serif text-[15.5px] leading-relaxed text-ink">
                {c.reply.slice(0, stage.reply).map((p, i) => {
                  const typing = i === stage.reply - 1 && !stage.questions && !stage.done;
                  const words = p.text.split(" ");
                  const shown = typing ? words.slice(0, stage.words).join(" ") : p.text;
                  const complete = !typing || stage.words >= words.length;
                  return (
                    <p key={i}>
                      {shown}
                      {typing && !complete && <span className="ml-0.5 inline-block h-[1em] w-[2px] translate-y-[2px] animate-pulse bg-violet" />}
                      {complete && p.cites && <> <Citations items={p.cites} /></>}
                    </p>
                  );
                })}
              </div>
            </div>
          )}

          {stage.questions && (
            <div className="max-w-[92%] animate-[fadeUp_.4s_ease_both] rounded-xl border border-line bg-bg p-4">
              <div className="text-xs uppercase tracking-[0.12em] text-violet">Ask the customer next</div>
              <ol className="mt-2 list-decimal space-y-1 pl-5 text-[14px] text-ink">
                {c.questions.map((q) => <li key={q}>{q}</li>)}
              </ol>
              <div className="mt-3 border-t border-line pt-3 text-[13.5px] leading-relaxed text-ink-2">
                <span className="text-ink" style={{ fontWeight: 500 }}>First step. </span>{c.next}
              </div>
            </div>
          )}

          {stage.done && (
            <Link href={`/assess?example=${c.id}`} className="inline-flex animate-[fadeUp_.4s_ease_both] items-center gap-1.5 text-sm text-ink underline decoration-line-strong underline-offset-4 hover:decoration-violet">
              Try this enquiry yourself <ArrowRight className="h-3.5 w-3.5" aria-hidden />
            </Link>
          )}
        </div>

        {/* Composer (illustrative) */}
        <div className="border-t border-line p-3">
          <div className="flex items-center gap-2 rounded-lg border border-line bg-bg px-3 py-2.5 text-sm text-ink-3">
            <span className="flex-1 truncate">{replying ? "SpectraSense is writing…" : "Answer the questions or add details…"}</span>
            <span className="flex h-7 w-7 items-center justify-center rounded-md bg-ink text-bg"><ArrowUp className="h-4 w-4" /></span>
          </div>
        </div>
      </div>
    </div>
  );
}
