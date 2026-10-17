import { SiteHeader } from "@/components/SiteHeader";
import { SpectralBand } from "@/components/SpectralBand";
import { methods, table1 } from "@/data/optics";

export const metadata = { title: "Methods & fibers · SpectraSense AI" };

const level = (v: string) =>
  v === "high" ? "text-ok" : v === "low" ? "text-bad" : "text-ink-2";

export default function ReferencePage() {
  return (
    <>
      <SiteHeader />
      <main className="mx-auto max-w-6xl space-y-8 px-4 py-8 sm:px-6">
        <header>
          <p className="font-mono text-xs uppercase tracking-[0.25em] text-cyan">Reference</p>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight">Methods and fiber windows</h1>
          <p className="mt-2 max-w-3xl text-sm text-ink-2">
            Starting point compiled from the supplied sources. Not a product specification: actual spectral coverage, fiber length, component ratings, detection limits and accuracy depend on the configuration and the sample.
          </p>
        </header>

        <section className="rounded-lg border border-line bg-panel p-5">
          <h2 className="text-sm font-semibold uppercase tracking-[0.14em] text-ink-2">Fiber compatibility</h2>
          <p className="mb-4 mt-1 text-xs text-ink-3">Select methods to see which fiber families transmit their nominal range.</p>
          <SpectralBand highlight={["MIR_ATR"]} />
        </section>

        <section className="rounded-lg border border-line bg-panel p-5">
          <h2 className="text-sm font-semibold uppercase tracking-[0.14em] text-ink-2">Method overview</h2>
          <div className="mt-4 grid gap-3 md:grid-cols-2 lg:grid-cols-3">
            {methods.map((m) => (
              <div key={m.id} className="rounded-md border border-line bg-bg/40 p-4">
                <div className="flex items-baseline justify-between gap-2">
                  <h3 className="font-semibold">{m.label}</h3>
                  <span className="font-mono text-[10px] text-ink-3">{m.read}</span>
                </div>
                <p className="mt-1 font-mono text-xs text-cyan">{m.rangeLabel}</p>
                <p className="mt-2 text-sm text-ink-2">{m.samples}</p>
                <p className="mt-2 text-xs text-warn/90">{m.limitations}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="rounded-lg border border-line bg-panel p-5">
          <h2 className="text-sm font-semibold uppercase tracking-[0.14em] text-ink-2">S01 Table 1 (p.6) — measurement techniques</h2>
          <div className="mt-4 overflow-x-auto">
            <table className="w-full min-w-[760px] text-sm">
              <thead className="text-left text-xs text-ink-3">
                <tr>{["Method", "Technique", "Phenomenon", "Sample", "Optical path / depth", "Sensitivity", "Selectivity", "Cost"].map((h) => <th key={h} className="py-2 pr-3 font-medium">{h}</th>)}</tr>
              </thead>
              <tbody>
                {table1.map((r, i) => (
                  <tr key={i} className="border-t border-line/60">
                    <td className="py-1.5 pr-3 text-ink-2">{r.method}</td>
                    <td className="py-1.5 pr-3">{r.technique}</td>
                    <td className="py-1.5 pr-3 text-ink-2">{r.phenomenon}</td>
                    <td className="py-1.5 pr-3 text-ink-2">{r.sample}</td>
                    <td className="py-1.5 pr-3 font-mono text-xs">{r.depth}</td>
                    <td className={`py-1.5 pr-3 ${level(r.sensitivity)}`}>{r.sensitivity}</td>
                    <td className={`py-1.5 pr-3 ${level(r.selectivity)}`}>{r.selectivity}</td>
                    <td className={`py-1.5 pr-3 ${r.cost === "high" ? "text-bad" : r.cost === "low" ? "text-ok" : "text-ink-2"}`}>{r.cost}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="mt-2 text-[11px] text-ink-3">Source: AFS_method_comparison_table.xlsx, a machine-readable transcription of S01 Table 1 (p.6). Cost colouring: low = green, high = red.</p>
        </section>
      </main>
    </>
  );
}
