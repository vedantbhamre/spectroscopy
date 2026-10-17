import Link from "next/link";
import { ArrowRight, FileSearch, HelpCircle, Layers, FlaskConical, ShieldCheck } from "lucide-react";
import { Hero } from "@/components/Hero";
import { Preloader } from "@/components/Preloader";
import { Reveal } from "@/components/Reveal";
import { SiteHeader } from "@/components/SiteHeader";

const steps = [
  { icon: FileSearch, title: "Read the use case", text: "Client facts are kept apart from everything the client did not say." },
  { icon: HelpCircle, title: "Find what is missing", text: "Clarification questions, ordered by whether the answer could change the method or setup." },
  { icon: Layers, title: "Recommend approaches", text: "Methods or combinations worth testing, each with its reason, conditions and page citation." },
  { icon: FlaskConical, title: "Propose a first experiment", text: "Representative samples, independent references, what is compared, and the go / no-go basis." },
  { icon: ShieldCheck, title: "Stay reviewable", text: "Premise checks and verified citations so an AFS expert can audit the answer in minutes." },
];

// Principles from the challenge expert Q&A (Hackathon_QA_Summary.pdf) and the organizers' good-practice notes.
const principles = [
  ["As simple as possible, as complicated as necessary.", "Default to the simplest method that meets the need; combine only when one is not enough."],
  ["“Insufficient information” can be the right answer.", "An honest provisional plan beats a final configuration built on missing facts."],
  ["A published application is a reason to test, not proof.", "No invented accuracies, ratings, prices or guarantees."],
];

export default function Home() {
  return (
    <main>
      <Preloader />
      <SiteHeader overlay />
      <Hero />

      <section id="how" className="grid-bg border-t border-line">
        <div className="mx-auto max-w-6xl px-6 py-24">
          <p className="font-mono text-xs uppercase tracking-[0.25em] text-cyan">How it works</p>
          <h2 className="mt-3 max-w-2xl text-3xl font-semibold tracking-tight sm:text-4xl">
            A first technical assessment, structured for expert review.
          </h2>
          <div className="mt-12 grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
            {steps.map((s, i) => (
              <Reveal key={s.title} delay={i * 0.06} className="h-full">
              <div className="h-full rounded-lg border border-line bg-panel p-5">
                <div className="flex items-center justify-between">
                  <s.icon className="h-5 w-5 text-cyan" aria-hidden />
                  <span className="font-mono text-xs text-ink-3">0{i + 1}</span>
                </div>
                <h3 className="mt-4 font-semibold">{s.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-ink-2">{s.text}</p>
              </div>
              </Reveal>
            ))}
          </div>

          <div className="mt-20 grid gap-6 lg:grid-cols-3">
            {principles.map(([h, t], i) => (
              <Reveal key={h} delay={i * 0.08}>
                <blockquote className="border-l-2 border-cyan/60 pl-5">
                  <p className="text-lg font-medium text-ink">{h}</p>
                  <p className="mt-2 text-sm text-ink-2">{t}</p>
                </blockquote>
              </Reveal>
            ))}
          </div>

          <div className="mt-20 flex flex-wrap items-center gap-4">
            <Link href="/assess" className="glow inline-flex items-center gap-2 rounded-md bg-cyan px-5 py-3 font-semibold text-bg hover:bg-white">
              Open the workbench <ArrowRight className="h-4 w-4" />
            </Link>
            <span className="text-sm text-ink-3">Development scenarios D01–D08 · Evaluation scenarios H01–H06 · Your own enquiry</span>
          </div>
        </div>
      </section>

      <footer className="border-t border-line py-8 text-center text-xs text-ink-3">
        National AI Hackathon 2026 · Art Fiber Systems challenge · Assistant output is a first hypothesis for expert review.
      </footer>
    </main>
  );
}
