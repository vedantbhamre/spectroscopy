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
    s = s.replace("‘", "'").replace("’", "'").replace("“", '"').replace("”", '"')
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


def page_exists(source: str, page: str) -> bool:
    wanted = set(page_numbers(page))
    return any(s == source and n in wanted for s, n, _, _ in _normalised())


def verify(c: Citation) -> Citation:
    """Return a copy of the citation with `check` set by the verifier."""
    if c.source == "EXT":
        # External sources need a quote and a link (expert Q&A); we cannot check the page here.
        return c.model_copy(update={"check": "unverified"})
    if not page_exists(c.source, c.page):
        return c.model_copy(update={"check": "failed"})
    if not c.quote or len(normalise(c.quote)) < MIN_QUOTE:
        return c.model_copy(update={"check": "unverified"})
    q = normalise(c.quote)
    wanted = set(page_numbers(c.page))
    kinds = [k for s, n, k, text in _normalised() if s == c.source and n in wanted and q in text]
    if not kinds:
        return c.model_copy(update={"check": "failed"})
    return c.model_copy(update={"check": "visual_note" if kinds == ["visual_note"] else "verified"})


def find_quote(source: str, page: int, quote: str) -> bool:
    return verify(Citation(source=source, page=str(page), quote=quote)).check in ("verified", "visual_note")
