export function Logo({ className = "", dark = false }: { className?: string; dark?: boolean }) {
  return (
    <span className={`inline-flex items-center gap-2 ${className}`}>
      <svg viewBox="0 0 32 32" className="h-7 w-7" aria-hidden>
        <path d="M6 28 C 8 16, 14 8, 24 4" style={{ stroke: dark ? "var(--accent-bright)" : "var(--accent)" }} strokeWidth="2.2" fill="none" strokeLinecap="round" />
        <path d="M10 28 C 12 18, 18 11, 28 8" style={{ stroke: "var(--amber)" }} strokeWidth="2.2" fill="none" strokeLinecap="round" />
        <path d="M14 28 C 16 21, 21 15, 30 13" stroke={dark ? "#c4a5ff" : "#7c3aed"} strokeWidth="2.2" fill="none" strokeLinecap="round" />
        <path d="M3 30 L9 22 L15 30 Z" style={{ fill: dark ? "var(--night-ink)" : "var(--ink)" }} />
      </svg>
      <span className="whitespace-nowrap leading-none">
        <span className={`block text-[15px] font-semibold tracking-tight ${dark ? "text-night-ink" : "text-ink"}`}>SpectraSense AI</span>
        <span className={`block text-[11px] ${dark ? "text-night-ink-3" : "text-ink-3"}`}>for Art Fiber Systems</span>
      </span>
    </span>
  );
}
