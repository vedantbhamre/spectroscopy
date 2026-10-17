import { Hero } from "@/components/Hero";
import { Preloader } from "@/components/Preloader";
import { Reveal } from "@/components/Reveal";
import { SiteHeader } from "@/components/SiteHeader";

const steps = [
  { title: "Read the use case", text: "Client facts are kept apart from everything the client did not say." },
  { title: "Find what is missing", text: "Clarification questions, ordered by whether the answer could change the method or setup." },
  { title: "Recommend approaches", text: "Methods or combinations worth testing, each with its reason, conditions and page citation." },
  { title: "Propose a first experiment", text: "Representative samples, independent references, what is compared, and the go / no-go basis." },
  { title: "Stay reviewable", text: "Premise checks and verified citations so an AFS expert can audit the answer in minutes." },
];

// Principles from the challenge expert Q&A and the organizers' good-practice notes.
const principles = [
  ["As simple as possible, as complicated as necessary.", "Default to the simplest method that meets the need; combine only when one is not enough."],
  ["“Insufficient information” can be the right answer.", "An honest provisional plan beats a final configuration built on missing facts."],
  ["A published application is a reason to test, not proof.", "No invented accuracies, ratings, prices or guarantees."],
];

export default function Home() {
  return (
    <main>
      <Preloader />
      <SiteHeader />
      <Hero />
      <div className="h-px bg-night-line" aria-hidden />

      <section className="mx-auto max-w-6xl px-6 py-20">
        <h2 className="max-w-2xl text-3xl font-semibold tracking-tight">How the assessment is built</h2>
        <ol className="mt-10 grid gap-x-8 gap-y-8 sm:grid-cols-2 lg:grid-cols-5">
          {steps.map((s, i) => (
            <li key={s.title}>
              <Reveal delay={i * 0.06} className="h-full border-t-[3px] border-accent pt-4">
                <span className="text-sm font-semibold text-accent">Step {i + 1}</span>
                <h3 className="mt-1 font-semibold">{s.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-ink-2">{s.text}</p>
              </Reveal>
            </li>
          ))}
        </ol>
      </section>

      <section className="bg-panel">
        <div className="mx-auto grid max-w-6xl gap-8 px-6 py-16 lg:grid-cols-3">
          {principles.map(([h, t], i) => (
            <Reveal key={h} delay={i * 0.08}>
              <blockquote className="border-l-[3px] border-amber pl-5">
                <p className="font-serif text-xl leading-snug text-ink">{h}</p>
                <p className="mt-2 text-sm text-ink-2">{t}</p>
              </blockquote>
            </Reveal>
          ))}
        </div>
      </section>

      <footer className="bg-night py-8 text-center text-xs text-night-ink-3">
        National AI Hackathon 2026, Art Fiber Systems challenge. Assistant output is a first hypothesis for expert review.
      </footer>
    </main>
  );
}
