"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Logo } from "./Logo";
import { ThemeToggle } from "./ThemeToggle";

const links = [
  { href: "/assess", label: "Assess" },
  { href: "/how-it-works", label: "How it works" },
  { href: "/evals", label: "Evals" },
];

export function SiteHeader() {
  const path = usePathname();
  return (
    <header className="print-hidden sticky inset-x-0 top-0 z-40 border-b border-line bg-bg/90 text-ink backdrop-blur-md">
      <div className="flex h-14 items-center justify-between gap-4 px-5 sm:px-8 lg:px-10">
        <Link href="/" aria-label="SpectraSense home"><Logo /></Link>
        <nav className="flex items-center gap-1 text-[14px] sm:gap-2">
          {links.map((l) => {
            const on = path === l.href;
            return (
              <Link
                key={l.href}
                href={l.href}
                aria-current={on ? "page" : undefined}
                className={`relative whitespace-nowrap px-2 py-1.5 tracking-[-0.01em] transition-colors sm:px-2.5 ${on ? "text-ink" : "text-ink-2 hover:text-ink"}`}
              >
                {l.label}
                <span className={`absolute inset-x-2 -bottom-[13px] h-[2px] bg-ink transition-transform sm:inset-x-2.5 ${on ? "scale-x-100" : "scale-x-0"}`} aria-hidden />
              </Link>
            );
          })}
          <ThemeToggle />
        </nav>
      </div>
    </header>
  );
}
