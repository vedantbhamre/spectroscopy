"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { Menu, X } from "lucide-react";
import { Logo } from "./Logo";
import { AnimatedBackground } from "./motion-primitives/animated-background";
import { ThemeToggle } from "./ThemeToggle";

const links = [
  { href: "/assess", label: "Assess" },
  { href: "/how-it-works", label: "How it works" },
  { href: "/evals", label: "Evals" },
];

export function SiteHeader({ overHero = false }: { overHero?: boolean }) {
  const path = usePathname();
  // Small screens get a menu button instead of a squeezed link row (from the shiv branch); Escape or a link closes it.
  const [menuOpen, setMenuOpen] = useState(false);
  useEffect(() => {
    if (!menuOpen) return;
    const close = (e: KeyboardEvent) => e.key === "Escape" && setMenuOpen(false);
    window.addEventListener("keydown", close);
    return () => window.removeEventListener("keydown", close);
  }, [menuOpen]);
  useEffect(() => setMenuOpen(false), [path]);

  return (
    <header className={`print-hidden inset-x-0 top-0 z-40 border-b ${overHero ? "absolute border-white/15 bg-[#03060c]/35 text-white backdrop-blur-md" : "sticky border-line bg-bg text-ink"}`}>
      <div className="flex h-14 items-center justify-between gap-2 px-4 sm:gap-4 sm:px-8 lg:px-10">
        <Link href="/" aria-label="SpectraSense home"><Logo dark={overHero} /></Link>
        <div className="flex min-w-0 items-center gap-1 sm:gap-2">
          <nav aria-label="Main" className="hidden min-w-0 items-center gap-0 text-sm sm:gap-2 md:flex">
            <AnimatedBackground enableHover className={overHero ? "bg-white/10" : "bg-panel"} transition={{ type: "spring", bounce: 0, duration: 0.25 }}>
              {links.map((l) => {
                const on = path === l.href;
                return (
                  <Link
                    key={l.href}
                    data-id={l.href}
                    href={l.href}
                    aria-current={on ? "page" : undefined}
                    className={`relative h-14 items-center whitespace-nowrap px-1.5 transition-colors sm:px-3 ${overHero ? "text-white/85 hover:text-white" : on ? "text-ink" : "text-ink-2 hover:text-ink"}`}
                  >
                    <span className="flex h-full items-center">{l.label}</span>
                    <span className={`absolute inset-x-0 bottom-0 h-[2px] bg-accent ${on ? "opacity-100" : "opacity-0"}`} aria-hidden />
                  </Link>
                );
              })}
            </AnimatedBackground>
          </nav>
          <ThemeToggle inverse={overHero} />
          <button
            type="button"
            className={`flex h-8 w-8 items-center justify-center border md:hidden ${overHero ? "border-white/25 bg-white/5 text-white/85 hover:bg-white/15" : "border-line text-ink-2 hover:bg-panel hover:text-ink"}`}
            aria-label={menuOpen ? "Close navigation menu" : "Open navigation menu"}
            aria-expanded={menuOpen}
            aria-controls="mobile-navigation"
            onClick={() => setMenuOpen((o) => !o)}
          >
            {menuOpen ? <X className="h-4 w-4" aria-hidden /> : <Menu className="h-4 w-4" aria-hidden />}
          </button>
        </div>
      </div>
      <nav
        id="mobile-navigation"
        aria-label="Mobile"
        className={`absolute inset-x-0 top-full border-b p-2 shadow-xl md:hidden ${overHero ? "border-white/15 bg-[#03060c]/95 backdrop-blur-xl" : "border-line bg-bg"} ${menuOpen ? "block" : "hidden"}`}
      >
        {links.map((l) => {
          const on = path === l.href;
          return (
            <Link key={l.href} href={l.href} aria-current={on ? "page" : undefined} onClick={() => setMenuOpen(false)}
                  className={`block border-l-2 px-3 py-3 text-sm ${on ? "border-accent font-medium" : "border-transparent"} ${overHero ? "text-white/90 hover:bg-white/10" : "text-ink hover:bg-panel"}`}>
              {l.label}
            </Link>
          );
        })}
      </nav>
    </header>
  );
}
