// Ink wordmark: a prism that splits one ray into three, with a violet registered dot.
export function Logo({ className = "", size = "md", dark = false }: { className?: string; size?: "md" | "lg"; dark?: boolean }) {
  const lg = size === "lg";
  return (
    <span className={`inline-flex items-center ${lg ? "gap-[0.32em]" : "gap-2"} ${dark ? "text-white" : "text-ink"} ${className}`}>
      <svg viewBox="0 0 40 26" className={lg ? "h-[0.76em] w-auto" : "h-[17px] w-auto"} aria-hidden fill="currentColor">
        <path d="M0 12.2h11v1.6H0Z" />
        <path d="M11 26 20 0l9 26Zm4.4-3.2h9.2L20 9.6Z" />
        <path d="m27.6 9.2 12.2-4 .4 1.5-12.2 4ZM28.2 12.2H40v1.6H28.2ZM27.6 16.8l.4-1.5 12.2 4-.4 1.5Z" />
      </svg>
      <span className={`relative whitespace-nowrap pr-[0.24em] leading-none ${lg ? "" : "text-[17px]"}`} style={{ fontWeight: 400, letterSpacing: "-0.02em" }}>
        SpectraSense
        <svg viewBox="0 0 10 10" className="absolute right-0 top-[-0.02em] h-[0.19em] w-[0.19em] text-violet" aria-hidden fill="currentColor">
          <path d="M5 0 6.25 3.75 10 5 6.25 6.25 5 10 3.75 6.25 0 5 3.75 3.75Z" />
        </svg>
      </span>
    </span>
  );
}
