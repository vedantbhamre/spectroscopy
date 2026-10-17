export function Logo({ className = "" }: { className?: string }) {
  return (
    <span className={`inline-flex items-center gap-2 ${className}`}>
      <svg viewBox="0 0 32 32" className="h-7 w-7" aria-hidden>
        <path d="M6 28 C 8 16, 14 8, 24 4" stroke="#2fd9f0" strokeWidth="2" fill="none" strokeLinecap="round" />
        <path d="M10 28 C 12 18, 18 11, 28 8" stroke="#fb923c" strokeWidth="2" fill="none" strokeLinecap="round" />
        <path d="M14 28 C 16 21, 21 15, 30 13" stroke="#c084fc" strokeWidth="2" fill="none" strokeLinecap="round" />
        <path d="M3 30 L9 22 L15 30 Z" fill="#3b82f6" opacity="0.85" />
      </svg>
      <span className="whitespace-nowrap leading-none">
        <span className="block text-[15px] font-semibold tracking-tight text-ink">SpectraSense AI</span>
        <span className="block text-[10px] uppercase tracking-[0.18em] text-ink-3">Art Fiber Systems</span>
      </span>
    </span>
  );
}
