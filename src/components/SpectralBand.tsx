"use client";

import { useMemo, useState } from "react";
import { coverage, fibers, FIBER_SOURCE, methods, type MethodId } from "@/data/optics";

// Log-scale wavelength axis (µm) with nominal method ranges and fiber transmission windows.
const MIN = 0.19, MAX = 25;
const x = (um: number) => ((Math.log10(um) - Math.log10(MIN)) / (Math.log10(MAX) - Math.log10(MIN))) * 100;
const regions = [
  { label: "UV", from: MIN, to: 0.38, color: "#7c3aed" },
  { label: "Vis", from: 0.38, to: 0.78, color: "url(#vis)" },
  { label: "NIR", from: 0.78, to: 2.5, color: "#ef4444" },
  { label: "MIR", from: 2.5, to: MAX, color: "#9a3412" },
];
const ticks = [0.2, 0.5, 1, 2, 5, 10, 20];

const covStyle = {
  full: "bg-ok/15 text-ok border-ok/40",
  partial: "bg-warn/15 text-warn border-warn/40",
  none: "bg-bad/10 text-bad border-bad/40",
};

export function SpectralBand({ highlight = [], interactive = true }: { highlight?: MethodId[]; interactive?: boolean }) {
  const [selected, setSelected] = useState<MethodId[]>(highlight);
  const active = interactive ? selected : highlight;
  const placeable = methods.filter((m) => m.rangeUm);
  const unplaced = methods.filter((m) => !m.rangeUm && active.includes(m.id));
  const activeRanges = useMemo(
    () => placeable.filter((m) => active.includes(m.id)).map((m) => ({ m, r: m.rangeUm! })),
    [active, placeable],
  );
  const toggle = (id: MethodId) => setSelected((s) => (s.includes(id) ? s.filter((v) => v !== id) : [...s, id]));

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-1.5">
        {methods.map((m) => {
          const on = active.includes(m.id);
          return (
            <button
              key={m.id}
              type="button"
              disabled={!interactive}
              onClick={() => toggle(m.id)}
              aria-pressed={on}
              className={`rounded-full border px-2.5 py-1 text-xs transition ${on ? "border-cyan bg-cyan/15 text-cyan" : "border-line text-ink-3 hover:border-line-strong hover:text-ink-2"} disabled:cursor-default`}
            >
              {m.label}
            </button>
          );
        })}
      </div>

      <div className="relative rounded-md border border-line bg-bg/70 p-3">
        {/* axis + regions (offset by the 7rem row-label column) */}
        <div className="ml-28">
        <svg viewBox="0 0 100 10" preserveAspectRatio="none" className="h-5 w-full" aria-hidden>
          <defs>
            <linearGradient id="vis" x1="0" x2="1">
              <stop offset="0" stopColor="#3b82f6" /><stop offset="0.35" stopColor="#22d3ee" />
              <stop offset="0.55" stopColor="#34d399" /><stop offset="0.75" stopColor="#facc15" /><stop offset="1" stopColor="#ef4444" />
            </linearGradient>
          </defs>
          {regions.map((r) => (
            <rect key={r.label} x={x(r.from)} y={0} width={x(r.to) - x(r.from)} height={10} fill={r.color} opacity={0.55} />
          ))}
        </svg>
        <div className="relative mt-1 h-4 font-mono text-[10px] text-ink-3">
          {regions.map((r) => (
            <span key={r.label} className="absolute -translate-x-1/2" style={{ left: `${(x(r.from) + x(r.to)) / 2}%` }}>{r.label}</span>
          ))}
        </div>
        </div>

        {/* rows */}
        <div className="relative mt-2 space-y-1.5">
          {ticks.map((t) => (
            <div key={t} className="pointer-events-none absolute inset-y-0 w-px bg-line/70" style={{ left: `calc(7rem + (100% - 7rem) * ${x(t) / 100})` }} aria-hidden />
          ))}
          {placeable.map((m) => {
            const on = active.includes(m.id);
            const [a, b] = m.rangeUm!;
            return (
              <Row key={m.id} label={`${m.label}`} sub="nominal" dim={!on}>
                <div
                  className={`absolute inset-y-0 rounded-sm ${on ? "bg-cyan/70 shadow-[0_0_12px_rgba(47,217,240,0.6)]" : "bg-ink-3/30"}`}
                  style={{ left: `${x(a)}%`, width: `${x(Math.min(b, MAX)) - x(a)}%` }}
                  title={`${m.label}: ${m.rangeLabel}`}
                />
              </Row>
            );
          })}
          <div className="my-2 border-t border-dashed border-line" />
          {fibers.map((f) => {
            const covs = activeRanges.map(({ m, r }) => ({ m, ...coverage(r, f.rangeUm) }));
            const anyFull = covs.some((c) => c.kind === "full");
            const anyPartial = covs.some((c) => c.kind === "partial");
            const tone = !covs.length ? "bg-violet/35" : anyFull ? "bg-ok/55" : anyPartial ? "bg-warn/55" : "bg-bad/35";
            return (
              <Row key={f.id} label={f.short} sub={`${f.rangeUm[0]}–${f.rangeUm[1]} µm`}>
                <div
                  className={`absolute inset-y-[3px] rounded-sm ${tone}`}
                  style={{ left: `${x(f.rangeUm[0])}%`, width: `${x(f.rangeUm[1]) - x(f.rangeUm[0])}%` }}
                  title={f.label}
                />
              </Row>
            );
          })}
        </div>
        <div className="relative mt-1 h-4 font-mono text-[10px] text-ink-3" aria-hidden>
          {ticks.map((t) => (
            <span key={t} className="absolute -translate-x-1/2" style={{ left: `calc(7rem + (100% - 7rem) * ${x(t) / 100})` }}>{t}</span>
          ))}
          <span className="absolute right-0">µm</span>
        </div>
      </div>

      {activeRanges.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="text-left text-ink-3">
                <th className="py-1 pr-3 font-medium">Fiber family ({FIBER_SOURCE})</th>
                {activeRanges.map(({ m }) => <th key={m.id} className="py-1 pr-3 font-medium">{m.label} {m.rangeLabel}</th>)}
              </tr>
            </thead>
            <tbody>
              {fibers.map((f) => (
                <tr key={f.id} className="border-t border-line/60">
                  <td className="py-1 pr-3 text-ink-2">{f.label}</td>
                  {activeRanges.map(({ m, r }) => {
                    const c = coverage(r, f.rangeUm);
                    return (
                      <td key={m.id} className="py-1 pr-3">
                        <span className={`rounded border px-1.5 py-0.5 font-mono text-[10px] ${covStyle[c.kind]}`}>
                          {c.kind === "partial" ? `partial ${Math.round(c.share * 100)}%` : c.kind}
                        </span>
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {unplaced.length > 0 && (
        <p className="text-xs text-ink-3">
          Not placed on the axis: {unplaced.map((m) => `${m.label} (${m.rangeLabel.toLowerCase()})`).join("; ")}.
        </p>
      )}
      <p className="text-[11px] leading-relaxed text-ink-3">
        Nominal method ranges are not the usable range of a specific instrument, fiber or probe. Fiber windows are approximate values transcribed from the {FIBER_SOURCE} figure; check the figure before relying on an exact number.
      </p>
    </div>
  );
}

function Row({ label, sub, dim, children }: { label: string; sub?: string; dim?: boolean; children: React.ReactNode }) {
  return (
    <div className={`flex items-center ${dim ? "opacity-60" : ""}`}>
      <div className="w-28 shrink-0 pr-2">
        <div className="truncate text-[11px] text-ink-2">{label}</div>
        {sub && <div className="truncate font-mono text-[9px] text-ink-3">{sub}</div>}
      </div>
      <div className="relative h-4 flex-1">{children}</div>
    </div>
  );
}
