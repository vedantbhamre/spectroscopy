import Link from "next/link";
import { Logo } from "./Logo";

// Carbon footer: the one inverted surface, a wordmark and caption-sized link columns.
const product = [
  { href: "/assess", label: "Start an assessment" },
  { href: "/how-it-works", label: "How it works" },
  { href: "/evals", label: "Evaluation results" },
];

export function SiteFooter({ compact = false }: { compact?: boolean }) {
  const year = new Date().getFullYear();
  return (
    <footer className="print-hidden border-t border-inverse-line bg-inverse text-inverse-ink-2">
      {!compact && (
        <div className="mx-auto grid max-w-6xl gap-10 px-6 py-14 sm:grid-cols-2 lg:grid-cols-4">
          <div className="lg:col-span-2">
            <Logo className="!text-inverse-ink" />
            <p className="mt-4 max-w-sm text-sm leading-relaxed">
              First technical assessments for in-line spectroscopy, cited to the Art Fiber Systems application material and reviewed by an expert before they reach a customer.
            </p>
          </div>
          <nav aria-label="Product">
            <h2 className="text-sm font-semibold text-inverse-ink">Product</h2>
            <ul className="mt-4 space-y-2.5 text-sm">
              {product.map((l) => (
                <li key={l.href}><Link href={l.href} className="hover:text-inverse-ink hover:underline">{l.label}</Link></li>
              ))}
            </ul>
          </nav>
          <div>
            <h2 className="text-sm font-semibold text-inverse-ink">About</h2>
            <p className="mt-4 text-sm leading-relaxed">
              Built for the National AI Hackathon 2026, Art Fiber Systems challenge: AI assistance for in-line spectroscopy solution design.
            </p>
          </div>
        </div>
      )}
      <div className="border-t border-inverse-line">
        <div className="mx-auto flex max-w-6xl flex-col gap-2 px-6 py-5 text-xs sm:flex-row sm:items-center sm:justify-between">
          <p>© {year} SpectraSense. All rights reserved.</p>
          <p>Assessments are first hypotheses for expert review, not guarantees of performance.</p>
        </div>
      </div>
    </footer>
  );
}
