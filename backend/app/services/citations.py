"""Citation verifier (port of the team's repo-seed citations.ts).

A citation is "verified" only if its quote appears on the cited page after normalising
line breaks, hyphenation, ligatures, dashes and quotes. A match on a team transcription
of a slide image is "visual_note". Without a quote the citation stays "unverified":
the expert Q&A accepts "S01 p.17" for supplied material, but the UI shows it was not checked.
"""

import json
import re
import unicodedata
from functools import lru_cache

from app.config import settings
from app.schemas import Citation

MIN_QUOTE = 12


def normalise(s: str) -> str:
    s = unicodedata.normalize("NFKC", s)
    s = re.sub(r"-\s*\n\s*", "", s)  # hyphenation at line end
    s = re.sub(r"\s+-(?=\w)", "-", s)  # "fiber -optic" → "fiber-optic"
    s = re.sub(r"[‐-―−]", "-", s)
    s = re.sub(r"[‘’‚‛“”„‟\"`]", "'", s)  # models swap " and ' freely
    s = s.replace("cm⁻¹", "cm-1").replace("cm−1", "cm-1")
    return re.sub(r"\s+", " ", s).strip().lower()


@lru_cache(maxsize=1)
def _pages() -> list[dict]:
    if not settings.PAGES_FILE.exists():
        return []
    return json.loads(settings.PAGES_FILE.read_text())


@lru_cache(maxsize=1)
def _normalised() -> list[tuple[str, int, str, str]]:
    return [(p["source"], int(p["page"]), p["kind"], normalise(p["text"])) for p in _pages()]


def page_numbers(page: str) -> list[int]:
    """'14–15' → [14, 15]; 'Table 1 (p.6)' → [6]; '10' → [10]."""
    m = re.search(r"p\.?\s*(\d+)", page)
    if m:
        return [int(m.group(1))]
    nums = [int(n) for n in re.findall(r"\d+", page)]
    if len(nums) == 2 and nums[1] > nums[0] and nums[1] - nums[0] <= 3:
        return list(range(nums[0], nums[1] + 1))
    return nums[:1]


def page_text(source: str, page: str) -> str:
    """Text of the cited page(s), for checking numbers against the source."""
    wanted = set(page_numbers(page))
    return "\n".join(p["text"] for p in _pages() if p["source"] == source and int(p["page"]) in wanted)


def contains(text: str, quote: str) -> bool:
    """Both normalised; "..." elides words, so each piece must appear, in order."""
    return _contains(text, quote)


def page_exists(source: str, page: str) -> bool:
    wanted = set(page_numbers(page))
    return any(s == source and n in wanted for s, n, _, _ in _normalised())


def _contains(text: str, quote: str) -> bool:
    """The quote is on the page; "..." elides words, so each piece must appear, in order."""
    pos = 0
    for piece in (p.strip(" ,;:.!?") for p in quote.split("...")):
        if not piece:
            continue
        i = text.find(piece, pos)
        if i < 0:
            return False
        pos = i + len(piece)
    return pos > 0


def _table_rows() -> str:
    # S01 Table 1 as transcribed by the organisers (PDF text extraction interleaves its columns).
    from app.knowledge.table1 import for_prompt

    return normalise(for_prompt())


def _check(c: Citation) -> str:
    if c.source == "EXT":
        # External sources need a quote and a link (expert Q&A); we cannot check the page here.
        return "unverified"
    if not page_exists(c.source, c.page):
        return "failed"
    if not c.quote or len(normalise(c.quote)) < MIN_QUOTE:
        return "unverified"
    q = normalise(c.quote)
    if c.source == "S01" and "table" in c.page.lower() and _contains(_table_rows(), q):
        return "verified"
    wanted = set(page_numbers(c.page))
    kinds = [k for s, n, k, text in _normalised() if s == c.source and n in wanted and _contains(text, q)]
    if not kinds:
        return "failed"
    return "visual_note" if kinds == ["visual_note"] else "verified"


SNAP_MIN = 0.8  # share of the quote's words, in order, that the page passage must reproduce


def snap(c: Citation) -> Citation | None:
    """A near-verbatim quote (a word changed, "..." elisions, a trailing paraphrase) replaced by the exact
    passage of the cited page it reproduces. None if no passage is close enough."""
    import difflib

    if not c.quote or not page_exists(c.source, c.page):
        return None
    qw = [w for w in re.findall(r"[a-z0-9]+", normalise(c.quote))]
    if len(qw) < 5:
        return None
    best, best_text = 0.0, None
    for s, n, k, _ in _normalised():
        if s != c.source or n not in set(page_numbers(c.page)):
            continue
        raw = next(p["text"] for p in _pages() if p["source"] == s and int(p["page"]) == n and p["kind"] == k)
        raw = re.sub(r"-\s*\n\s*", "", raw)
        words = raw.split()
        norm = [" ".join(re.findall(r"[a-z0-9]+", normalise(w))) for w in words]
        size = len(qw)
        for i in range(0, max(len(words) - size + 1, 1)):
            for j in (size - 2, size, size + 2):
                win = norm[i:i + j]
                ratio = difflib.SequenceMatcher(None, qw, " ".join(win).split(), autojunk=False).ratio()
                if ratio > best:
                    best, best_text = ratio, " ".join(words[i:i + j])
    if best < SNAP_MIN or not best_text:
        return None
    best_text = re.sub(r"^\S{0,30}[.;:]\s+(?=[A-Z])", "", best_text.strip())  # drop the tail of the previous sentence
    fixed = c.model_copy(update={"quote": best_text.strip(" ,;")})
    return fixed if _check(fixed) in ("verified", "visual_note") else None


def verify(c: Citation, allow_snap: bool = True) -> Citation:
    """Return a copy of the citation with `check` set by the verifier. A near-verbatim quote is replaced by
    the exact page passage it reproduces (then verified); an invented one stays "failed"."""
    status = _check(c)
    if status == "failed" and allow_snap and (fixed := snap(c)) is not None:
        return fixed.model_copy(update={"check": _check(fixed)})
    return c.model_copy(update={"check": status})


def find_quote(source: str, page: int, quote: str) -> bool:
    return verify(Citation(source=source, page=str(page), quote=quote)).check in ("verified", "visual_note")
