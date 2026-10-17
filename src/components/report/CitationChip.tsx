"use client";

import { useState } from "react";
import { CheckCircle2, Eye, CircleDashed, XCircle } from "lucide-react";
import { type Citation, citeText } from "@/lib/report";

const style = {
  verified: { icon: CheckCircle2, cls: "border-ok/40 text-ok", label: "Quote found on the cited page" },
  visual_note: { icon: Eye, cls: "border-violet/40 text-violet", label: "Matched a team transcription of a slide image" },
  unverified: { icon: CircleDashed, cls: "border-line-strong text-ink-2", label: "Not checked by the citation verifier" },
  failed: { icon: XCircle, cls: "border-bad/50 text-bad", label: "Quote not found on the cited page" },
} as const;

export function CitationChip({ c }: { c: Citation }) {
  const [open, setOpen] = useState(false);
  const s = style[c.check ?? "unverified"];
  const Icon = s.icon;
  return (
    <span className="relative inline-block align-baseline font-sans">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        onBlur={() => setOpen(false)}
        aria-expanded={open}
        className={`inline-flex items-center gap-1 whitespace-nowrap rounded border bg-bg px-1.5 py-px text-[12px] leading-5 hover:bg-panel ${s.cls}`}
      >
        <Icon className="h-3 w-3" aria-hidden />
        {citeText(c)}
        <span className="sr-only">({s.label})</span>
      </button>
      {open && (
        <span role="tooltip" className="absolute left-0 top-full z-30 mt-1 block w-72 rounded-md bg-tooltip p-3 text-left text-xs leading-relaxed text-white/80 shadow-lg">
          <span className="flex items-center gap-1 font-medium text-white"><Icon className="h-3.5 w-3.5" aria-hidden /> {s.label}</span>
          {c.quote ? <span className="mt-1.5 block font-serif text-[13px] text-white">“{c.quote}”</span> : <span className="mt-1.5 block">No quoted passage attached.</span>}
          {c.url && <span className="mt-1.5 block break-all text-[#9ccbe0]">{c.url}</span>}
        </span>
      )}
    </span>
  );
}

export function Citations({ items }: { items: Citation[] }) {
  if (!items?.length) return null;
  return (
    <span className="inline-flex flex-wrap gap-1 align-baseline">
      {items.map((c, i) => <CitationChip key={i} c={c} />)}
    </span>
  );
}
