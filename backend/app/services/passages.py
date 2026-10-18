"""Numbered passages for citation by reference.

The composer used to copy quotes by hand; a quote that drifted from the page failed verification, the repair pass then
fell back to citing Table 1 rows, and the application pages an assessment rests on went uncited. Now every retrieved
excerpt is split into short numbered passages ("S01.14.3"), the composer cites the number, and the quote is the page's
own text by construction.
"""

import re

from app.schemas import Citation

MAX_WORDS = 40
MIN_WORDS = 6
_SENT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9(\"“])")


def _pieces(text: str) -> list[str]:
    text = re.sub(r"-\s*\n\s*", "", text)  # hyphenation at line end
    text = re.sub(r"\s+", " ", text).strip()
    out: list[str] = []
    for s in _SENT.split(text):
        words = s.split()
        while len(words) > MAX_WORDS:  # long PDF runs: cut at a comma or semicolon near the limit, else hard
            cut = next((i + 1 for i in range(MAX_WORDS - 1, MIN_WORDS, -1) if words[i].endswith((",", ";", ":"))), MAX_WORDS)
            out.append(" ".join(words[:cut]))
            words = words[cut:]
        if words:
            out.append(" ".join(words))
    merged: list[str] = []
    carry = ""
    for p in out:  # fragments too short to quote join the passage before them (or after, at the start)
        p = f"{carry} {p}".strip() if carry else p
        carry = ""
        if len(p.split()) < MIN_WORDS:
            if merged and len(merged[-1].split()) + len(p.split()) <= MAX_WORDS + MIN_WORDS:
                merged[-1] += " " + p
            else:
                carry = p
            continue
        merged.append(p)
    if carry:
        merged.append(carry)
    return merged


def number(docs: list[dict]) -> tuple[str, dict[str, Citation]]:
    """Excerpts with numbered passages for the prompt, and the reference → citation map."""
    refs: dict[str, Citation] = {}
    blocks = []
    counters: dict[tuple[str, str], int] = {}
    for d in docs:
        src, page = d["source"], str(d["page"])
        label = d.get("label") or f"p.{page}"
        kind = " (team transcription of a slide image)" if d.get("kind") == "visual_note" else ""
        app = f" · application: {', '.join(d['applications'])}" if d.get("applications") else ""
        lines = [f"[{src} {label}{kind}{app}]"]
        if d.get("kind") == "table":  # Table 1 rows are cited as rows (see the Table 1 note), not by number
            blocks.append("\n".join([*lines, d["text"]]))
            continue
        for piece in _pieces(d["text"]):
            n = counters[(src, page)] = counters.get((src, page), 0) + 1
            ref = f"{src}.{page}.{n}"
            refs[ref] = Citation(source=src, page=page, quote=piece)
            lines.append(f"  {ref} {piece}")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks), refs


def resolve(c: dict, refs: dict[str, Citation]) -> dict | None:
    """A citation given by reference becomes source, page and the passage itself; an unknown reference is dropped."""
    ref = str(c.get("ref") or "").strip().strip("[]")
    if not ref:
        return c
    hit = refs.get(ref)
    return hit.model_dump(include={"source", "page", "quote"}) if hit else None


# Reference markers the model sometimes writes into prose: 【ref":"S04.4.2"】, {"ref": "S01.14.3"}, (S01.14.3), [S01.14.3]
_INLINE = re.compile(r"\s*(【[^】]*】|\{\s*\"?ref\"?\s*:\s*\"?S\d{2}\.\d+\.\d+\"?\s*\}|[\[(]\s*(ref:?\s*)?S\d{2}\.\d+\.\d+(\s*[,;]\s*S\d{2}\.\d+\.\d+)*\s*[\])]"
                     r"|\bref\"?\s*:\s*\"?S\d{2}\.\d+\.\d+\"?|\bS\d{2}\.\d+\.\d+\b)")


def strip_refs(text: str | None) -> str | None:
    if not text:
        return text
    return re.sub(r"\s+([.,;:])", r"\1", _INLINE.sub("", text)).strip()
