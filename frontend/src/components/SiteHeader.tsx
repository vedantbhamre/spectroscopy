"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Logo } from "./Logo";
import { AnimatedBackground } from "./motion-primitives/animated-background";
import { ThemeToggle } from "./ThemeToggle";

const links = [
  { href: "/assess", label: "Assess" },
  { href: "/how-it-works", label: "How it works" },
  { href: "/evals", label: "Evals" },
];

export function SiteHeader() {
  const path = usePathname();
  return (
    <header className="print-hidden sticky inset-x-0 top-0 z-40 border-b border-line bg-bg text-ink">
      <div className="flex h-14 items-center justify-between gap-2 px-4 sm:gap-4 sm:px-8 lg:px-10">
        <Link href="/" aria-label="SpectraSense home"><Logo /></Link>
        <nav aria-label="Main" className="flex min-w-0 items-center gap-0 text-sm sm:gap-2">
          <AnimatedBackground enableHover className="bg-panel" transition={{ type: "spring", bounce: 0, duration: 0.25 }}>
            {links.map((l) => {
              const on = path === l.href;
              return (
                <Link
                  key={l.href}
                  data-id={l.href}
                  href={l.href}
                  aria-current={on ? "page" : undefined}
                  className={`relative h-14 items-center whitespace-nowrap px-1.5 transition-colors sm:px-3 ${on ? "text-ink" : "text-ink-2 hover:text-ink"}`}
                >
                  <span className="flex h-full items-center">{l.label}</span>
                  <span className={`absolute inset-x-0 bottom-0 h-[2px] bg-accent ${on ? "opacity-100" : "opacity-0"}`} aria-hidden />
                </Link>
              );
            })}
          </AnimatedBackground>
          <ThemeToggle />
        </nav>
      </div>
    </header>
  );
}
