import type { Metadata } from "next";
import Link from "next/link";
import { ArrowRight, Ban, CheckCircle2, CircleHelp, ShieldAlert, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { SiteFooter } from "@/components/SiteFooter";
import { SiteHeader } from "@/components/SiteHeader";
import { PipelineLottie } from "@/components/how/PipelineLottie";
import { ChatDemo } from "@/components/how/ChatDemo";
import { CitationChip } from "@/components/report/CitationChip";
import type { Citation } from "@/lib/report";
import { PLACEHOLDER_TEXT } from "@/lib/placeholder";

export const metadata: Metadata = {
  title: "How it works",
  description: "How to get a first in-line spectroscopy assessment for your own enquiry, what SpectraSense checks behind the scenes, worked examples, and how to read the report.",
  alternates: { canonical: "/how-it-works" },
};

const useSteps = [
  {
    title: "Describe the enquiry",
    text: "Paste or write what the customer needs, in their words: what to measure, the sample, where it would be measured, the conditions, equipment they already own and how success is judged.",
    tip: "Missing details are fine. Nothing you leave out is assumed.",
  },
  {
    title: "Answer the questions",
    text: "The assistant asks up to five questions that could change the method or the setup. Each has its own answer box; “Don’t know” and “Skip” are valid answers, and answered questions are never asked again.",
    tip: "Ready for the answer? Press “Final report” and open points become assumptions to confirm.",
  },
  {
    title: "Review the report",
    text: "Each reply produces a new version of the report: the recommended methods with their sources, the measurement concept, the spectral range, risks and a first feasibility experiment.",
    tip: "Copy it as text or download a PDF for the customer or a colleague.",
  },
];

// Real quotes from the AFS material; the "not found" example is deliberately invented to show the verifier.
const sample: { c: Citation; meaning: string }[] = [
  { c: { source: "S02", page: "13", quote: "Application: measurement of water content in petroleum", check: "verified" }, meaning: "The quoted passage was found on that page." },
  { c: { source: "S02", page: "6", quote: "standard and Al/Cu-coated VIS-NIR silica fibers 350–2400 nm", check: "visual_note" }, meaning: "Matched the team’s transcription of a slide image: check the figure itself." },
  { c: { source: "S01", page: "17", check: "unverified" }, meaning: "A page reference without a quote, so it could not be checked." },
  { c: { source: "S02", page: "13", quote: "Silica fibres transmit the full mid-IR range without loss", check: "failed" }, meaning: "The quote is not on that page: treat the claim as unsupported." },
  {
    c: { source: "S01", page: "15", quote: "A multispectral NIRaman fiber probe has industrial grade design", check: "verified", transfer: true, application: "pharmaceutical solids" },
    meaning: "The source shows this for a different application, so it still has to be tested for yours.",
  },
];

const statuses = [
  { label: "Provisional feasibility assessment", icon: CheckCircle2, cls: "border-accent text-accent", text: "The known facts support a method worth testing. The first experiment decides." },
  { label: "Insufficient information", icon: CircleHelp, cls: "border-warn text-warn", text: "A decisive fact is missing or a premise is contradicted. The questions say what is needed." },
  { label: "Outside the supported scope", icon: Ban, cls: "border-bad text-bad", text: "The request goes beyond what the sources support, for example a lab study used as clinical proof." },
];

const checks = [
  { icon: ShieldCheck, cls: "text-ok", label: "Pass", text: "The premise holds against the AFS material." },
  { icon: ShieldAlert, cls: "text-warn", label: "Flag", text: "Worth attention; the report explains what to confirm." },
  { icon: Ban, cls: "text-bad", label: "Fail", text: "The premise is contradicted, e.g. a fibre that cannot carry the method's range." },
];

const faq = [
  ["Is the report a final answer?", "No. It is a first technical assessment for an AFS expert to review. It never invents performance figures, prices or guarantees, and a published application is treated as a reason to test, not as proof."],
  ["Where do the sources come from?", "From the Art Fiber Systems application material: the Multispectral Lab guide, the Process Control slides, two published studies, the AFS flyer and the lab web page. Click any source in a report to read the quoted passage and the full document name."],
  ["What if I don't know the answer to a question?", "Choose “Don’t know”. The assistant does not ask again; it plans how the first experiment can establish it instead."],
  ["Why does a number say “to be agreed with the customer”?", "Every number in a report must come from the customer or from a cited page. Anything else, such as an accuracy target, is replaced so that no figure is invented."],
];

const sections = [["use", "Use it"], ["pipeline", "Behind the scenes"], ["examples", "Examples"], ["read", "Read a report"], ["faq", "Questions"]];

export default function HowItWorksPage() {
  return (
    <>
      <SiteHeader />
      <main className="px-5 sm:px-8 lg:px-10">
        <section className="mx-auto grid max-w-300 gap-8 pb-10 pt-14 lg:grid-cols-2 lg:gap-16 lg:pt-20">
          <div>
            <p className="text-sm text-ink-2">How it works</p>
            <h1 className="mt-4 text-[clamp(2.25rem,4.6vw,3.75rem)] font-light leading-[1.12] tracking-[-0.01em]">
              From your customer&apos;s enquiry to a first assessment you can trust
            </h1>
          </div>
          <p className="self-end border-l-2 border-accent pl-5 text-lg leading-relaxed text-ink-2">
            Describe what the customer needs. SpectraSense asks only what could change the method, checks every premise against the
            Art Fiber Systems material, and returns a cited assessment with a first experiment, ready for an expert to review.
          </p>
        </section>
        <nav aria-label="On this page" className="mx-auto max-w-300 border-y border-line">
          <ul className="flex flex-wrap gap-x-6 gap-y-1 py-3 text-sm">
            {sections.map(([id, label]) => (
              <li key={id}><a href={`#${id}`} className="inline-flex min-h-6 items-center text-accent hover:underline">{label}</a></li>
            ))}
          </ul>
        </nav>

        <section id="use" className="mx-auto max-w-300 scroll-mt-20 py-14" aria-labelledby="use-h">
          <h2 id="use-h" className="text-[2rem] font-light leading-tight">Use it on your own enquiry</h2>
          <ol className="mt-8 grid gap-px bg-line md:grid-cols-3">
            {useSteps.map((s, i) => (
              <li key={s.title} className="bg-panel p-6">
                <span className="font-mono text-xs text-ink-3">0{i + 1}</span>
                <h3 className="mt-3 text-lg">{s.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-ink-2">{s.text}</p>
                <p className="mt-4 border-l-2 border-accent pl-3 text-sm text-ink">{s.tip}</p>
              </li>
            ))}
          </ol>
        </section>

        <section id="pipeline" className="mx-auto max-w-300 scroll-mt-20 border-t border-line py-14" aria-labelledby="pipeline-h">
          <h2 id="pipeline-h" className="text-[2rem] font-light leading-tight">What happens behind the scenes</h2>
          <p className="mt-3 max-w-3xl text-ink-2">
            A language model reads the enquiry and drafts the answer. The decisions it must not make alone, such as whether a fibre
            carries a method&apos;s range or whether a study supports a claim, are checked against the AFS material first, and every
            quote and number is verified afterwards.
          </p>
          <div className="mt-8"><PipelineLottie /></div>
        </section>

        <section id="examples" className="mx-auto max-w-300 scroll-mt-20 border-t border-line py-14" aria-labelledby="examples-h">
          <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
            <h2 id="examples-h" className="text-[2rem] font-light leading-tight">See it handle real situations</h2>
            <p className="max-w-md text-sm leading-relaxed text-ink-2">
              Four enquiries, four behaviours: stopping an incompatible setup, asking for a missing target, declining an overstated
              claim and building a careful shortlist.
            </p>
          </div>
          <ChatDemo />
        </section>

        <section id="read" className="mx-auto max-w-300 scroll-mt-20 border-t border-line py-14" aria-labelledby="read-h">
          <h2 id="read-h" className="text-[2rem] font-light leading-tight">How to read a report</h2>
          <div className="mt-8 grid gap-10 lg:grid-cols-2">
            <div>
              <h3 className="text-lg">Decision status</h3>
              <ul className="mt-4 space-y-4">
                {statuses.map((s) => (
                  <li key={s.label}>
                    <span className={`inline-flex items-center gap-1.5 border px-2.5 py-1 text-sm ${s.cls}`}><s.icon className="h-4 w-4" aria-hidden />{s.label}</span>
                    <p className="mt-1.5 text-sm text-ink-2">{s.text}</p>
                  </li>
                ))}
              </ul>
              <h3 className="mt-10 text-lg">Premise checks</h3>
              <p className="mt-2 text-sm text-ink-2">Checks on what the enquiry assumes, run before the answer is written.</p>
              <ul className="mt-4 space-y-2.5">
                {checks.map((c) => (
                  <li key={c.label} className="flex gap-3 text-sm">
                    <c.icon className={`mt-0.5 h-4 w-4 shrink-0 ${c.cls}`} aria-hidden />
                    <span><span className="font-semibold text-ink">{c.label}.</span> <span className="text-ink-2">{c.text}</span></span>
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <h3 className="text-lg">Sources</h3>
              <p className="mt-2 text-sm text-ink-2">Every recommendation links to the page it rests on. Click a source to read the quoted passage.</p>
              <ul className="mt-4 space-y-3">
                {sample.map(({ c, meaning }) => (
                  <li key={`${c.check}-${c.page}-${c.transfer ? "t" : ""}`} className="flex flex-wrap items-baseline gap-x-3 gap-y-1 text-sm">
                    <CitationChip c={c} />
                    <span className="text-ink-2">{meaning}</span>
                  </li>
                ))}
              </ul>
              <h3 className="mt-10 text-lg">Questions, assumptions and numbers</h3>
              <ul className="mt-4 space-y-2.5 text-sm text-ink-2">
                <li><span className="text-ink">Clarification questions</span>: only the facts that could change the method or setup, most decisive first.</li>
                <li><span className="text-ink">Assumptions and points to confirm</span>: what the assessment rests on without a customer fact or a verified source.</li>
                <li><span className="text-ink">Report versions</span>: each reply adds a version (v1, v2, …) so you can see what changed.</li>
                <li><span className="font-mono text-xs text-ink">{PLACEHOLDER_TEXT}</span>: a figure that neither the customer nor a source gave.</li>
              </ul>
            </div>
          </div>
        </section>

        <section id="faq" className="mx-auto max-w-300 scroll-mt-20 border-t border-line py-14" aria-labelledby="faq-h">
          <h2 id="faq-h" className="text-[2rem] font-light leading-tight">Common questions</h2>
          <div className="mt-6 divide-y divide-line border-y border-line">
            {faq.map(([q, a]) => (
              <details key={q} className="group py-4">
                <summary className="flex min-h-6 cursor-pointer list-none items-center justify-between gap-4 text-base text-ink">
                  {q}
                  <span className="text-accent transition-transform group-open:rotate-45" aria-hidden>+</span>
                </summary>
                <p className="mt-3 max-w-3xl text-sm leading-relaxed text-ink-2">{a}</p>
              </details>
            ))}
          </div>
        </section>

        <section className="mx-auto mb-16 flex max-w-300 flex-wrap items-center justify-between gap-6 bg-accent px-6 py-10 text-white sm:px-10">
          <p className="text-[1.75rem] font-light leading-tight">Try it on a real enquiry.</p>
          <Button asChild size="lg" variant="inverse">
            <Link href="/assess">Start an assessment <ArrowRight aria-hidden /></Link>
          </Button>
        </section>
      </main>
      <SiteFooter />
    </>
  );
}
