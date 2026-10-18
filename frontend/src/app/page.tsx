import { Button } from "@/components/ui/button";
import { promises as fs } from "fs";
import path from "path";
import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { Hero } from "@/components/Hero";
import { NumberTicker } from "@/components/NumberTicker";
import { Reveal } from "@/components/Reveal";
import { SiteFooter } from "@/components/SiteFooter";
import { SiteHeader } from "@/components/SiteHeader";
import { SITE } from "@/lib/site";

const steps = [
  { title: "Separate facts from gaps", text: "Every stated fact is quoted from the customer. Anything they did not say is listed as unknown, never assumed." },
  { title: "Ask what decides the method", text: "Up to five questions, ranked by whether the answer could change the method or the setup. Answered questions are never asked again." },
  { title: "Recommend with citations", text: "Each candidate method comes with its reason, its limits and the page of the AFS material that supports it." },
  { title: "Check the premises", text: "Fibre windows, probe geometry, access points, qualified targets and source scope are checked against the sources before anything is written." },
  { title: "Plan the first experiment", text: "Representative samples, independent reference measurements and the basis for a go / no-go decision." },
];

// From the challenge expert Q&A and the organisers' good-practice notes.
const principles = [
  ["As simple as possible, as complicated as necessary.", "The simplest sufficient method comes first. Methods are combined only when one is shown not to be enough."],
  ["“Insufficient information” can be the right answer.", "An honest provisional plan is more useful than a final configuration built on missing facts."],
  ["A published application is a reason to test, not proof.", "No invented accuracies, ratings, prices or guarantees. Every number is traced to the customer or a cited page."],
];

type Summary = Record<string, { all: number | null }>;

// Scores from the last saved evaluation run; the strip is hidden when there is none.
async function lastRun(): Promise<{ at: string; scenarios: number; summary: Summary } | null> {
  try {
    // The file is rewritten by eval runs; a partial or older-shaped file just hides the strip.
    const r = JSON.parse(await fs.readFile(path.join(process.cwd(), "outputs", "evals-latest.json"), "utf8"));
    if (!r || !Array.isArray(r.scenarios) || typeof r.summary !== "object" || !r.run_at) return null;
    return { at: r.run_at, scenarios: r.scenarios.length, summary: r.summary };
  } catch {
    return null;
  }
}

const SHOWN = [
  ["citation_validity", "of quoted passages found on the cited page"],
  ["expectations", "of expected checks and statuses met"],
  ["faithfulness", "of report claims supported by the retrieved pages"],
] as const;

const jsonLd = {
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  name: SITE.name,
  applicationCategory: "BusinessApplication",
  operatingSystem: "Web",
  description: SITE.description,
  url: SITE.url,
};

export default async function Home() {
  const run = await lastRun();
  const stats = run ? SHOWN.filter(([k]) => typeof run.summary[k]?.all === "number") : [];
  return (
    <>
      <SiteHeader overHero />
      <main>
        <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />
        <Hero />

        <section className="mx-auto max-w-6xl px-6 py-20" aria-labelledby="steps">
          <h2 id="steps" className="max-w-2xl text-[2rem] font-light leading-tight">How an assessment is built</h2>
          <ol className="mt-10 grid border-l border-t border-line sm:grid-cols-2 lg:grid-cols-5">
            {steps.map((s, i) => (
              <li key={s.title} className="border-b border-r border-line bg-panel p-6">
                <Reveal delay={i * 0.05}>
                  <span className="font-mono text-xs text-ink-3">0{i + 1}</span>
                  <h3 className="mt-3 text-lg">{s.title}</h3>
                  <p className="mt-2 text-sm leading-relaxed text-ink-2">{s.text}</p>
                </Reveal>
              </li>
            ))}
          </ol>
        </section>

        {run && stats.length > 0 && (
          <section className="border-y border-line bg-panel" aria-labelledby="evidence">
            <div className="mx-auto max-w-6xl px-6 py-16">
              <div className="flex flex-wrap items-end justify-between gap-4">
                <h2 id="evidence" className="text-[2rem] font-light leading-tight">Measured, not claimed</h2>
                <p className="text-sm text-ink-2">
                  Last evaluation over {run.scenarios} scenarios, {new Date(run.at).toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" })}
                </p>
              </div>
              <dl className="mt-10 grid gap-px bg-line sm:grid-cols-3">
                {stats.map(([k, label]) => (
                  <div key={k} className="bg-panel p-6">
                    <dt className="text-sm text-ink-2">{label}</dt>
                    <dd className="mt-2 text-5xl font-light text-ink">
                      <NumberTicker value={Math.round((run.summary[k].all as number) * 100)} suffix="%" />
                    </dd>
                  </div>
                ))}
              </dl>
              <Button asChild variant="link" className="mt-8">
                <Link href="/evals">See every metric and scenario <ArrowRight aria-hidden /></Link>
              </Button>
            </div>
          </section>
        )}

        <section className="mx-auto max-w-6xl px-6 py-20" aria-labelledby="principles">
          <h2 id="principles" className="text-[2rem] font-light leading-tight">Principles from the AFS experts</h2>
          <div className="mt-10 grid gap-10 lg:grid-cols-3">
            {principles.map(([h, t], i) => (
              <Reveal key={h} delay={i * 0.06}>
                <blockquote className="border-l-2 border-accent pl-5">
                  <p className="font-serif text-xl leading-snug text-ink">{h}</p>
                  <p className="mt-3 text-sm leading-relaxed text-ink-2">{t}</p>
                </blockquote>
              </Reveal>
            ))}
          </div>
        </section>

        <section className="bg-accent text-white">
          <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-6 px-6 py-12">
            <p className="text-[1.75rem] font-light leading-tight">Have an enquiry from a customer?</p>
            <Button asChild size="lg" variant="inverse">
              <Link href="/assess">Start an assessment <ArrowRight aria-hidden /></Link>
            </Button>
          </div>
        </section>
      </main>
      <SiteFooter />
    </>
  );
}
