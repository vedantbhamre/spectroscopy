import Link from "next/link";
import { SiteHeader } from "@/components/SiteHeader";
import { PipelineLottie } from "@/components/how/PipelineLottie";
import { ChatDemo } from "@/components/how/ChatDemo";

export const metadata = { title: "How it works · SpectraSense" };

// Principles from the challenge expert Q&A and the organizers' good-practice notes.
const principles = [
  ["As simple as possible, as complicated as necessary.", "Default to the simplest method that meets the need; combine only when one is not enough."],
  ["“Insufficient information” can be the right answer.", "An honest provisional plan beats a final configuration built on missing facts."],
  ["A published application is a reason to test, not proof.", "No invented accuracies, ratings, prices or guarantees."],
];

export default function HowItWorksPage() {
  return (
    <>
      <SiteHeader />
      <main className="px-5 sm:px-8 lg:px-10">
        <section className="mx-auto grid max-w-[1200px] gap-8 border-b border-line pb-14 pt-14 lg:grid-cols-2 lg:gap-16 lg:pt-20">
          <div>
            <p className="font-mono text-[11px] uppercase tracking-[0.14em] text-ink-3">How it works</p>
            <h1 className="mt-4 text-[clamp(36px,5vw,64px)] leading-[0.98] tracking-[-0.035em]" style={{ fontWeight: 450 }}>
              Five steps from an enquiry to a reviewable assessment
            </h1>
          </div>
          <p className="relative self-end border-l-2 border-ink pl-5 text-[clamp(16px,1.4vw,19px)] leading-[1.45] text-ink-2">
            The language model reads and writes. Decisions it must not make alone, such as whether a fibre can carry a method&apos;s range or whether a study supports a claim, are checked against the AFS material before the answer is composed.
          </p>
        </section>

        <section className="mx-auto max-w-[1200px] py-14">
          <PipelineLottie />
        </section>

        <section className="mx-auto max-w-[1200px] border-t border-line py-14">
          <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
            <div>
              <p className="font-mono text-[11px] uppercase tracking-[0.14em] text-ink-3">Use cases</p>
              <h2 className="mt-3 text-[clamp(28px,3.2vw,40px)] leading-tight tracking-[-0.03em]" style={{ fontWeight: 450 }}>The assistant in conversation</h2>
            </div>
            <p className="max-w-md text-sm leading-relaxed text-ink-2">Four enquiries, four behaviours: stopping an incompatible setup, asking for a missing target, refusing an overstated claim, and building a careful shortlist.</p>
          </div>
          <ChatDemo />
        </section>

        <section className="mx-auto grid max-w-[1200px] gap-10 border-t border-line py-14 lg:grid-cols-3">
          {principles.map(([h, t]) => (
            <blockquote key={h}>
              <p className="text-[22px] leading-snug tracking-[-0.02em]" style={{ fontWeight: 450 }}>{h}</p>
              <p className="mt-3 text-sm leading-relaxed text-ink-2">{t}</p>
            </blockquote>
          ))}
        </section>

        <section className="mx-auto mb-16 flex max-w-[1200px] flex-wrap items-center justify-between gap-4 rounded-xl bg-ink px-6 py-8 text-bg sm:px-10">
          <p className="text-[clamp(20px,2.2vw,28px)] tracking-[-0.02em]" style={{ fontWeight: 450 }}>Try it on a real enquiry.</p>
          <div className="flex gap-3">
            <Link href="/assess" className="rounded-full bg-bg px-5 py-2.5 text-sm text-ink hover:bg-violet hover:text-white">Start an assessment</Link>
          </div>
        </section>
      </main>
    </>
  );
}
