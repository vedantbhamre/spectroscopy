// Analyzer → fiber link → probe → process point, the scheme the expert asked for (Q&A §3).
// Missing parts are drawn but labelled "not specified" so gaps stay visible.

export function SetupSketch({ analyzer, fiberLink, probe, location }: { analyzer?: string; fiberLink?: string; probe?: string; location?: string }) {
  const parts = [
    { k: "Analyzer", v: analyzer },
    { k: "Fibre link", v: fiberLink },
    { k: "Probe", v: probe },
    { k: "Process point", v: location },
  ];
  return (
    <figure className="rounded-md border border-line p-3 font-sans">
      <svg viewBox="0 0 680 130" className="w-full" role="img" aria-label="Measurement setup sketch: analyzer, fibre link, probe, process point">
        <defs>
          <linearGradient id="fiber" x1="0" x2="1">
            <stop offset="0" stopColor="#6d28d9" /><stop offset="0.35" stopColor="#2563eb" />
            <stop offset="0.65" stopColor="#059669" /><stop offset="1" stopColor="#ea580c" />
          </linearGradient>
        </defs>
        {/* analyzer */}
        <rect x="20" y="24" width="100" height="62" rx="6" style={{ fill: "var(--panel)", stroke: "var(--line-strong)" }} />
        <rect x="32" y="36" width="52" height="24" rx="2" style={{ fill: "var(--bg)", stroke: "var(--accent)" }} />
        <polyline points="34,54 42,50 48,56 56,42 62,52 70,46 82,52" fill="none" strokeWidth="1.5" style={{ stroke: "var(--accent)" }} />
        <circle cx="100" cy="44" r="4" fill="#167a4a" /><circle cx="100" cy="60" r="4" style={{ fill: "var(--line-strong)" }} />
        {/* fiber: dashed when not specified */}
        <path d="M120 64 C 200 124, 300 4, 380 60" stroke="url(#fiber)" strokeWidth="3" fill="none" strokeDasharray={fiberLink ? undefined : "6 5"} />
        {/* probe */}
        <rect x="380" y="52" width="90" height="16" rx="3" fill="#8a96a8" />
        <rect x="470" y="55" width="26" height="10" rx="2" fill="#4a5566" />
        {/* process pipe */}
        <rect x="500" y="30" width="160" height="60" rx="8" style={{ fill: "var(--panel)", stroke: "var(--line-strong)" }} />
        <path d="M512 60 h136" strokeWidth="18" style={{ stroke: "var(--line)" }} strokeLinecap="round" />
        <circle cx="500" cy="60" r="5" style={{ fill: "var(--accent)" }} />
      </svg>
      <figcaption className="mt-2 grid grid-cols-2 gap-2 sm:grid-cols-4">
        {parts.map((p) => (
          <div key={p.k} className="rounded bg-panel px-2 py-1.5">
            <div className="text-[11px] text-ink-3">{p.k}</div>
            <div className={`text-xs ${p.v ? "text-ink" : "italic text-warn"}`}>{p.v ?? "Not specified"}</div>
          </div>
        ))}
      </figcaption>
    </figure>
  );
}
