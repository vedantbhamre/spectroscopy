"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Logo } from "./Logo";
import { ThemeToggle } from "./ThemeToggle";

const links = [
  { href: "/assess", label: "Assess" },
  { href: "/how-it-works", label: "How it works" },
  { href: "/reference", label: "Methods and fibres" },
];

export function SiteHeader() {
  const path = usePathname();
  return (
    <header className="print-hidden sticky inset-x-0 top-0 z-40 border-b border-line bg-bg text-ink">
      <div className="flex h-14 items-center justify-between px-4 sm:px-6">
        <Link href="/" aria-label="SpectraSense AI home"><Logo dark /></Link>
        <nav className="flex items-center gap-1 text-sm">
          {links.map((l) => {
            const on = path === l.href;
            return (
              <Link
                key={l.href}
                href={l.href}
                aria-current={on ? "page" : undefined}
                className={`rounded-md px-3 py-1.5 ${on ? "bg-accent text-white" : "text-ink-2 hover:bg-panel hover:text-ink"}`}
              >
                {l.label}
              </Link>
            );
          })}
          <ThemeToggle />
        </nav>
      </div>
    </header>
  );
}
