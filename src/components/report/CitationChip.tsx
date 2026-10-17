import { CheckCircle2, Eye, CircleDashed, XCircle } from "lucide-react";
import { type Citation, citeText } from "@/lib/report";

const style = {
  verified: { icon: CheckCircle2, cls: "border-ok/40 text-ok", label: "Quote verified on cited page" },
  visual_note: { icon: Eye, cls: "border-violet/40 text-violet", label: "Matched a team transcription of a slide image" },
  unverified: { icon: CircleDashed, cls: "border-line-strong text-ink-2", label: "Not yet checked by the citation verifier" },
  failed: { icon: XCircle, cls: "border-bad/50 text-bad", label: "Quote not found on cited page" },
} as const;

export function CitationChip({ c }: { c: Citation }) {
  const s = style[c.check ?? "unverified"];
  const Icon = s.icon;
  const tip = [s.label, c.quote && `“${c.quote}”`, c.url].filter(Boolean).join("\n");
  return (
    <span
      title={tip}
      className={`inline-flex items-center gap-1 whitespace-nowrap rounded border bg-bg/60 px-1.5 py-0.5 font-mono text-[11px] ${s.cls}`}
    >
      <Icon className="h-3 w-3" aria-hidden />
      {citeText(c)}
      <span className="sr-only">({s.label})</span>
    </span>
  );
}

export function Citations({ items }: { items: Citation[] }) {
  if (!items?.length) return null;
  return (
    <span className="inline-flex flex-wrap gap-1 align-middle">
      {items.map((c, i) => <CitationChip key={i} c={c} />)}
    </span>
  );
}
