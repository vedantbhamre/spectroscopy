import Link from "next/link";
import { Logo } from "./Logo";

export function SiteHeader({ overlay = false }: { overlay?: boolean }) {
  return (
    <header
      className={`${overlay ? "fixed" : "sticky"} inset-x-0 top-0 z-40 border-b border-line/60 bg-bg/70 backdrop-blur-md`}
    >
      <div className="mx-auto flex h-14 max-w-[1400px] items-center justify-between px-4 sm:px-6">
        <Link href="/" aria-label="SpectraSense AI home"><Logo /></Link>
        <nav className="flex items-center gap-1 text-sm">
          <Link href="/assess" className="rounded px-3 py-1.5 text-ink-2 hover:bg-panel-2 hover:text-ink">Assess</Link>
          <Link href="/reference" className="rounded px-3 py-1.5 text-ink-2 hover:bg-panel-2 hover:text-ink"><span className="sm:hidden">Reference</span><span className="hidden sm:inline">Methods &amp; fibers</span></Link>
        </nav>
      </div>
    </header>
  );
}
