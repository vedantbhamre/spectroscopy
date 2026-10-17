// Analyzer → fiber link → probe → process point, the scheme the expert asked for (Q&A §3).
// Missing parts are drawn but labelled "not specified" so gaps stay visible.

export function SetupSketch({ analyzer, fiberLink, probe, location }: { analyzer?: string; fiberLink?: string; probe?: string; location?: string }) {
  const parts = [
    { k: "Analyzer", v: analyzer, x: 70 },
    { k: "Fiber link", v: fiberLink, x: 250 },
    { k: "Probe", v: probe, x: 430 },
    { k: "Process point", v: location, x: 590 },
  ];
  return (
    <figure className="rounded-md border border-line bg-bg/70 p-3">
      <svg viewBox="0 0 680 150" className="w-full" role="img" aria-label="Measurement setup sketch: analyzer, fiber link, probe, process point">
        <defs>
          <linearGradient id="fiber" x1="0" x2="1">
            <stop offset="0" stopColor="#7c3aed" /><stop offset="0.3" stopColor="#22d3ee" />
            <stop offset="0.6" stopColor="#34d399" /><stop offset="1" stopColor="#fb923c" />
          </linearGradient>
        </defs>
        {/* analyzer */}
        <rect x="20" y="30" width="100" height="62" rx="6" fill="#0f1a35" stroke="#2a3d6b" />
        <rect x="32" y="42" width="52" height="24" rx="2" fill="#060b1a" stroke="#1b8fa3" />
        <polyline points="34,60 42,56 48,62 56,48 62,58 70,52 82,58" fill="none" stroke="#2fd9f0" strokeWidth="1.5" />
        <circle cx="100" cy="50" r="4" fill="#3ddc97" /><circle cx="100" cy="66" r="4" fill="#2a3d6b" />
        {/* fiber */}
        <path d="M120 70 C 200 130, 300 10, 380 66" stroke="url(#fiber)" strokeWidth="3" fill="none" strokeDasharray={fiberLink ? undefined : "6 5"} />
        {/* probe */}
        <rect x="380" y="58" width="90" height="16" rx="3" fill="#a9b6d3" />
        <rect x="470" y="61" width="26" height="10" rx="2" fill="#6f7fa6" />
        <circle cx="500" cy="66" r="5" fill="#2fd9f0"><animate attributeName="opacity" values="1;0.3;1" dur="2s" repeatCount="indefinite" /></circle>
        {/* process: pipe */}
        <rect x="500" y="36" width="160" height="60" rx="8" fill="#0f1a35" stroke="#2a3d6b" />
        <path d="M512 66 h136" stroke="#1c2a4d" strokeWidth="18" strokeLinecap="round" />
        <path d="M520 66 h20 M560 66 h20 M600 66 h20" stroke="#2fd9f0" strokeWidth="2" opacity="0.5">
          <animate attributeName="stroke-dashoffset" from="0" to="-40" dur="2s" repeatCount="indefinite" />
        </path>
      </svg>
      <figcaption className="mt-2 grid grid-cols-2 gap-2 sm:grid-cols-4">
        {parts.map((p) => (
          <div key={p.k} className="rounded border border-line/70 bg-panel px-2 py-1.5">
            <div className="font-mono text-[10px] uppercase tracking-wider text-ink-3">{p.k}</div>
            <div className={`text-xs ${p.v ? "text-ink" : "italic text-warn"}`}>{p.v ?? "Not specified"}</div>
          </div>
        ))}
      </figcaption>
    </figure>
  );
}
