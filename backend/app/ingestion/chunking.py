"""Split pages into retrieval chunks that never cross a page boundary, so every chunk keeps its citation."""

import re

MAX_CHARS = 1400
OVERLAP = 200


def _clean(text: str) -> str:
    text = re.sub(r"-\s*\n\s*", "", text)  # hyphenation at line end
    return re.sub(r"[ \t]+", " ", re.sub(r"\n{3,}", "\n\n", text)).strip()


def chunk_pages(pages: list[dict]) -> list[dict]:
    chunks: list[dict] = []
    for p in pages:
        text = _clean(p["text"])
        if not text:
            continue
        start, part = 0, 0
        while start < len(text):
            end = min(len(text), start + MAX_CHARS)
            if end < len(text):
                cut = text.rfind(". ", start + MAX_CHARS // 2, end)
                end = cut + 1 if cut != -1 else end
            chunks.append({
                "id": f"{p['source']}-p{p['page']}-{p['kind']}-{part}",
                "source": p["source"],
                "page": p["page"],
                "kind": p["kind"],
                "label": p.get("label"),
                "text": text[start:end].strip(),
            })
            if end >= len(text):
                break
            start, part = max(end - OVERLAP, start + 1), part + 1
    return chunks
