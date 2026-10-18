"""Page metadata for citation checks: which method(s) a page covers and whether it is an application example.

Method tags come from the text of the chunk that holds the quoted passage (the page when there is no quote; pages such
as S01 p.14 end one example and start another): a method counts when the page mentions it at least twice and at least 30 % as
often as its most-mentioned method. A page is "general" (supports a claim about any method) when it covers four or more
methods, mentions none, or is a method overview / comparison / combining-methods page in the source guide.

Application tags come from the organisers' source guide (AFS_Examples_and_Reference.docx §4): only pages that describe
an application example carry one. Method descriptions are general and never make a citation a transfer assumption.
"""

import re
from functools import lru_cache

from app.knowledge import source_map as M
from app.services.citations import _pages, normalise, page_numbers

GENERAL = "general"
_MIN, _SHARE, _BROAD = 2, 0.3, 4
_OVERVIEW = {*M.CORE, *M.COMBINATION_PAGES}

# Application examples by page (source guide): S01 p.13-18 cases, S02 p.13-16 process examples, the two research papers.
APPLICATION_PAGES: dict[tuple[str, int], str] = {
    ("S01", 13): "medical and tissue",
    ("S01", 14): "pharmaceutical solids", ("S01", 15): "pharmaceutical solids",
    ("S01", 16): "bioprocess",
    ("S01", 17): "dairy and food", ("S01", 18): "dairy and food",
    ("S02", 13): "petroleum and chemicals",
    ("S02", 14): "petroleum and chemicals",  # API in polymer extrusion (a chemical process)
    ("S02", 15): "medical and tissue", ("S02", 16): "medical and tissue",
    **{("S03", p): "medical and tissue" for p in range(1, 18)},
    **{("S04", p): "medical and tissue" for p in range(1, 7)},
}


def _counts(text: str) -> dict[str, int]:
    t = normalise(text)
    return {m: len(re.findall(pat, t, re.I)) for m, pat in M.METHOD_PATTERNS.items()}


def _tags(text: str) -> frozenset[str]:
    n = _counts(text)
    top = max(n.values(), default=0)
    tags = {m for m, c in n.items() if c >= _MIN and c >= _SHARE * top}
    if not tags or len(tags) >= _BROAD:
        return frozenset({GENERAL})
    return frozenset(tags)


@lru_cache(maxsize=1)
def _chunks() -> list[tuple[str, int, str]]:
    from app.services.retrieval import chunks

    return [(c["source"], int(c["page"]), normalise(c["text"])) for c in chunks()]


def _text_for(source: str, page: int, quote: str | None) -> str:
    q = normalise(quote or "")[:80]
    if q:
        hit = next((t for s, p, t in _chunks() if s == source and p == page and q in t), None)
        if hit:
            return hit
    return " ".join(p["text"] for p in _pages() if p["source"] == source and int(p["page"]) == page)


@lru_cache(maxsize=None)
def methods_of(source: str, page: int, quote: str | None = None) -> frozenset[str]:
    """Method ids the passage's chunk (or the page) covers, or {"general"}."""
    if (source, page) in _OVERVIEW or source not in ("S01", "S02", "S03", "S04"):
        return frozenset({GENERAL})
    return _tags(_text_for(source, page, quote))


def methods_of_citation(source: str, page: str, quote: str | None = None) -> frozenset[str]:
    if source == "EXT" or "table" in page.lower():
        return frozenset({GENERAL})
    out: set[str] = set()
    for p in page_numbers(page):
        out |= methods_of(source, p, quote)
    return frozenset(out or {GENERAL})


def quote_methods(quote: str | None) -> set[str]:
    return {m for m, n in _counts(quote or "").items() if n}


def supports_method(source: str, page: str, quote: str | None, method_ids: list[str]) -> bool:
    """A citation supports a claim about these methods when its page covers one of them, the page is general, or the
    quoted passage itself names one of them."""
    if not method_ids:
        return True
    tags = methods_of_citation(source, page, quote)
    return GENERAL in tags or bool(tags & set(method_ids)) or bool(quote_methods(quote) & set(method_ids))


def application_of(source: str, page: str, quote: str | None = None) -> str | None:
    """The application a passage is an example of; None for method descriptions and other general pages. On an
    application page, the passage's own chunk decides when it names one domain (a page can end one example and start
    the next)."""
    from app.knowledge.applications import tag

    for p in page_numbers(page):
        if (source, p) in APPLICATION_PAGES:
            local = tag(_text_for(source, p, quote)) if quote else []
            return local[0] if len(local) == 1 else APPLICATION_PAGES[(source, p)]
    return None
