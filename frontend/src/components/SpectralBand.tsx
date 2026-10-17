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

// Chart palette (team spec), from CSS variables in globals.css so the dark theme applies.
const C = {
  bg: "var(--chart-bg)",
  border: "var(--chart-border)",
  grid: "var(--chart-grid)",
  axis: "var(--chart-axis)",
  material: "var(--chart-material)",
  range: "var(--chart-range)",
  full: "var(--chart-full)",
  partial: "var(--chart-partial)",
  unavailable: "var(--chart-unavailable)",
  tooltipBg: "var(--chart-tooltip-bg)",
  tooltipText: "var(--chart-tooltip-text)",
  tableHead: "var(--chart-table-head)",
  divider: "var(--chart-divider)",
  filterBg: "var(--chart-filter-bg)",
  filterBorder: "var(--chart-filter-border)",
};

const covColor = { full: C.full, partial: C.partial, none: C.unavailable } as const;

interface Tip { text: string; left: number; top: number }

export function SpectralBand({ highlight = [], interactive = true }: { highlight?: MethodId[]; interactive?: boolean }) {
  const [selected, setSelected] = useState<MethodId[]>(highlight);
  const [tip, setTip] = useState<Tip | null>(null);
  const active = interactive ? selected : highlight;
  const placeable = methods.filter((m) => m.rangeUm);
  const unplaced = methods.filter((m) => !m.rangeUm && active.includes(m.id));
  const activeRanges = useMemo(
    () => placeable.filter((m) => active.includes(m.id)).map((m) => ({ m, r: m.rangeUm! })),
    [active, placeable],
  );
  const toggle = (id: MethodId) => setSelected((s) => (s.includes(id) ? s.filter((v) => v !== id) : [...s, id]));

  const showTip = (e: React.MouseEvent<HTMLDivElement>, text: string) => {
    const box = e.currentTarget.closest("[data-chart]")!.getBoundingClientRect();
    const bar = e.currentTarget.getBoundingClientRect();
    setTip({ text, left: bar.left - box.left + bar.width / 2, top: bar.top - box.top });
  };

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
              style={on ? { background: C.filterBg, borderColor: C.filterBorder, color: C.filterBorder } : { borderColor: C.border, color: C.axis }}
              className={`rounded-full border px-2.5 py-1 text-xs transition ${on ? "font-semibold" : "hover:bg-panel"} disabled:cursor-default`}
            >
              {m.label}
            </button>
          );
        })}
      </div>

      <div data-chart className="relative rounded-md border p-3" style={{ background: C.bg, borderColor: C.border }} onMouseLeave={() => setTip(null)}>
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
              <rect key={r.label} x={x(r.from)} y={0} width={x(r.to) - x(r.from)} height={10} fill={r.color} opacity={0.45} />
            ))}
          </svg>
          <div className="relative mt-1 h-4 text-[10px] font-medium" style={{ color: C.axis }}>
            {regions.map((r) => (
              <span key={r.label} className="absolute -translate-x-1/2" style={{ left: `${(x(r.from) + x(r.to)) / 2}%` }}>{r.label}</span>
            ))}
          </div>
        </div>

        {/* rows */}
        <div className="relative mt-2 space-y-1.5">
          {ticks.map((t) => (
            <div key={t} className="pointer-events-none absolute inset-y-0 w-px" style={{ background: C.grid, left: `calc(7rem + (100% - 7rem) * ${x(t) / 100})` }} aria-hidden />
          ))}
          {placeable.map((m) => {
            const on = active.includes(m.id);
            const [a, b] = m.rangeUm!;
            return (
              <Row key={m.id} label={m.label} sub="nominal" dim={!on}>
                <div
                  className="absolute inset-y-0 rounded-sm"
                  style={{ background: on ? C.range : C.unavailable, left: `${x(a)}%`, width: `${x(Math.min(b, MAX)) - x(a)}%` }}
                  onMouseEnter={(e) => showTip(e, `${m.label}: ${m.rangeLabel} (nominal)`)}
                />
              </Row>
            );
          })}
          <div className="my-2 border-t border-dashed" style={{ borderColor: C.divider }} />
          {fibers.map((f) => {
            const covs = activeRanges.map(({ m, r }) => ({ m, ...coverage(r, f.rangeUm) }));
            const kind = !covs.length ? null : covs.some((c) => c.kind === "full") ? "full" : covs.some((c) => c.kind === "partial") ? "partial" : "none";
            const detail = covs.length ? covs.map((c) => `${c.m.label}: ${c.kind === "partial" ? `partial ${Math.round(c.share * 100)}%` : c.kind}`).join(", ") : "select a method to check coverage";
            return (
              <Row key={f.id} label={f.short} sub={`${f.rangeUm[0]}–${f.rangeUm[1]} µm`}>
                <div
                  className="absolute inset-y-[3px] rounded-sm"
                  style={{ background: kind ? covColor[kind] : C.unavailable, left: `${x(f.rangeUm[0])}%`, width: `${x(f.rangeUm[1]) - x(f.rangeUm[0])}%` }}
                  onMouseEnter={(e) => showTip(e, `${f.label}, ${f.rangeUm[0]}–${f.rangeUm[1]} µm. ${detail}`)}
                />
              </Row>
            );
          })}
        </div>
        <div className="relative mt-1 h-4 text-[10px]" style={{ color: C.axis }} aria-hidden>
          {ticks.map((t) => (
            <span key={t} className="absolute -translate-x-1/2" style={{ left: `calc(7rem + (100% - 7rem) * ${x(t) / 100})` }}>{t}</span>
          ))}
          <span className="absolute right-0">µm</span>
        </div>

        <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-[11px]" style={{ color: C.axis }}>
          {([["Selected method range", C.range], ["Full coverage", C.full], ["Partial coverage", C.partial], ["No coverage or not selected", C.unavailable]] as const).map(([l, c]) => (
            <span key={l} className="inline-flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-sm" style={{ background: c }} />{l}</span>
          ))}
        </div>

        {tip && (
          <div role="tooltip" className="pointer-events-none absolute z-20 max-w-xs -translate-x-1/2 -translate-y-full rounded-md px-2.5 py-1.5 text-xs shadow-lg" style={{ background: C.tooltipBg, color: C.tooltipText, left: tip.left, top: tip.top - 6 }}>
            {tip.text}
          </div>
        )}
      </div>

      {activeRanges.length > 0 && (
        <div className="overflow-x-auto rounded-md border" style={{ borderColor: C.divider }}>
          <table className="w-full text-xs">
            <thead style={{ background: C.tableHead }}>
              <tr className="text-left" style={{ color: C.material }}>
                <th className="px-3 py-2 font-semibold">Fiber family ({FIBER_SOURCE})</th>
                {activeRanges.map(({ m }) => <th key={m.id} className="px-3 py-2 font-semibold">{m.label} {m.rangeLabel}</th>)}
              </tr>
            </thead>
            <tbody>
              {fibers.map((f) => (
                <tr key={f.id} className="border-t" style={{ borderColor: C.divider }}>
                  <td className="px-3 py-1.5" style={{ color: C.material }}>{f.label}</td>
                  {activeRanges.map(({ m, r }) => {
                    const c = coverage(r, f.rangeUm);
                    const col = covColor[c.kind];
                    return (
                      <td key={m.id} className="px-3 py-1.5">
                        <span className="rounded px-1.5 py-0.5 text-[11px] font-medium" style={{ color: c.kind === "none" ? C.axis : col, background: `color-mix(in srgb, ${col} 12%, transparent)`, border: `1px solid color-mix(in srgb, ${col} 40%, transparent)` }}>
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
    <div className={`flex items-center ${dim ? "opacity-70" : ""}`}>
      <div className="w-28 shrink-0 pr-2">
        <div className="truncate text-[11px] font-medium" style={{ color: C.material }}>{label}</div>
        {sub && <div className="truncate text-[9px]" style={{ color: C.axis }}>{sub}</div>}
      </div>
      <div className="relative h-4 flex-1">{children}</div>
    </div>
  );
}
