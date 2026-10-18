"use client";

import { CheckCircle2, Eye, CircleDashed, XCircle } from "lucide-react";
import { Popover } from "radix-ui";
import { type Citation, citeFull, citeText } from "@/lib/report";

const style = {
  verified: { icon: CheckCircle2, cls: "border-ok/40 text-ok", label: "Quote found on the cited page" },
  visual_note: { icon: Eye, cls: "border-violet/40 text-violet", label: "Matched a team transcription of a slide image" },
  unverified: { icon: CircleDashed, cls: "border-line-strong text-ink-2", label: "Not checked by the citation verifier" },
  failed: { icon: XCircle, cls: "border-bad/50 text-bad", label: "Quote not found on the cited page" },
} as const;

// Click to see the quoted passage. Radix Popover renders it in a portal above the whole page, so later
// content (question cards, animated sections) can never cover it, and it flips away from screen edges.
export function CitationChip({ c, quotes }: { c: Citation; quotes?: string[] }) {
  const passages = quotes ?? (c.quote ? [c.quote] : []);
  const s = style[c.check ?? "unverified"];
  const Icon = s.icon;
  return (
    <Popover.Root>
      <Popover.Trigger asChild>
        <button
          type="button"
          className={`inline-flex min-h-6 items-center gap-1 whitespace-nowrap border bg-bg px-1.5 align-baseline font-sans text-xs leading-5 hover:bg-panel data-[state=open]:bg-panel ${s.cls}`}
        >
          <Icon className="h-3 w-3" aria-hidden />
          {citeText(c)}
          {passages.length > 1 && <span className="text-ink-3">×{passages.length}</span>}
          {c.transfer && <span className="border border-amber px-1 text-xs font-semibold leading-4 text-amber">transfer</span>}
          <span className="sr-only">({s.label}{c.transfer ? "; transfer assumption" : ""}). Show the quoted passage.</span>
        </button>
      </Popover.Trigger>
      <Popover.Portal>
        <Popover.Content
          side="bottom"
          align="start"
          sideOffset={6}
          collisionPadding={12}
          className="z-50 w-80 max-w-[calc(100vw-24px)] bg-tooltip p-3 font-sans text-xs leading-relaxed text-white/80 shadow-lg outline-none data-[state=open]:animate-[fadeUp_150ms_ease-out]"
        >
          <span className="block font-medium text-white">{citeFull(c)}</span>
          <span className="mt-1 flex items-center gap-1 text-white/80"><Icon className="h-3.5 w-3.5" aria-hidden /> {s.label}</span>
          {passages.length ? (
            passages.map((q) => <span key={q} className="mt-1.5 block font-serif text-[13px] text-white">“{q}”</span>)
          ) : (
            <span className="mt-1.5 block">No quoted passage attached.</span>
          )}
          {c.url && <a href={c.url} target="_blank" rel="noreferrer" className="mt-1.5 block break-all text-white underline">{c.url}</a>}
          {c.transfer && <span className="mt-1.5 block text-white"><b className="font-semibold">Transfer assumption:</b> the source shows this for {c.application ?? "another application"}; it has to be tested for this one.</span>}
          <Popover.Arrow className="fill-tooltip" width={10} height={5} />
        </Popover.Content>
      </Popover.Portal>
    </Popover.Root>
  );
}

// Several quotes from the same page with the same verification result show as one chip listing all quotes.
export function Citations({ items }: { items: Citation[] }) {
  if (!items?.length) return null;
  const groups = new Map<string, { c: Citation; quotes: string[] }>();
  for (const c of items) {
    const key = `${c.source}|${c.page}|${c.check}|${c.transfer ? 1 : 0}`;
    const g = groups.get(key) ?? { c, quotes: [] };
    if (c.quote && !g.quotes.includes(c.quote)) g.quotes.push(c.quote);
    groups.set(key, g);
  }
  return (
    <span className="inline-flex flex-wrap gap-1 align-baseline">
      {[...groups.values()].map((g, i) => <CitationChip key={i} c={g.c} quotes={g.quotes} />)}
    </span>
  );
}
