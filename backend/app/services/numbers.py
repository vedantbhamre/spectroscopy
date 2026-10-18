"""Number validator (test review, Fix C).

Every number with a unit, every decimal or percentage and every number above 10 in the assistant's
text must come from the customer's words or from a cited page (with the same unit: "15" as a page
number does not support "15 % w/w"). Anything else is a performance figure,
threshold or specification no source supports; it is replaced by a placeholder ("to be agreed with
the customer") rather than shown as a fact. Small bare counts (2 probes, 3 blends, step 1) are left alone.
"""

import re
from dataclasses import dataclass, field
from itertools import combinations

PLACEHOLDER = "[to be agreed with the customer]"

_NUM = r"\d{1,3}(?:[,   ]\d{3})+(?:\.\d+)?|\d+(?:[.,]\d+)?"
_UNIT = (r"%|‰|nm|µm|μm|um|mm|cm[-⁻−]?1|cm⁻¹|cm|ppm|ppb|°\s?C|°|K\b|ms\b|s\b|min\b|h\b|Hz|kHz|MHz|bar\b|mbar|"
         r"mg|g\b|kg|mL|ml|L\b|W\b|mW|x\b|×|w/w|v/v|tablets|rpm")
# A single value or a range ("780–2500 nm", "95 to 105 %"), optionally with a unit.
TOKEN = re.compile(rf"(?<![\w.\-/])((?:{_NUM}))(\s?(?:–|-|—|to)\s?({_NUM}))?(\s?(?:{_UNIT}))?(?![\w])", re.I)


def _value(s: str) -> float | None:
    s = re.sub(r"[   ]", "", s)
    if re.fullmatch(r"\d{1,3}(,\d{3})+(\.\d+)?", s):
        s = s.replace(",", "")
    s = s.replace(",", ".")
    try:
        return round(float(s), 6)
    except ValueError:
        return None


def _unit(u: str | None) -> str | None:
    if not u:
        return None
    u = re.sub(r"\s", "", u).lower().replace("μ", "µ")
    return {"um": "µm", "cm⁻¹": "cm-1", "cm−1": "cm-1", "cm1": "cm-1", "°c": "°", "ml": "ml"}.get(u, u)


def _tokens(text: str):
    for m in TOKEN.finditer(text or ""):
        vals = [v for g in (m.group(1), m.group(3)) if g and (v := _value(g)) is not None]
        yield m, vals, _unit(m.group(4))


def numbers_in(text: str) -> set[float]:
    return {v for _, vals, _ in _tokens(text) for v in vals}


@dataclass
class Allowed:
    customer: set[float] = field(default_factory=set)  # any unit: the customer's own numbers (and derived ones)
    with_unit: set[tuple[float, str]] = field(default_factory=set)  # source numbers with their unit
    bare: set[float] = field(default_factory=set)  # source numbers without a unit (support bare numbers only)

    def ok(self, vals: list[float], unit: str | None) -> bool:
        if all(v in self.customer for v in vals):
            return True
        if unit:
            return all((v, unit) in self.with_unit for v in vals)
        return all(v in self.bare or any(v == w for w, _ in self.with_unit) for v in vals)


def allowed_numbers(customer_text: str, source_texts: list[str], derive: bool = False) -> Allowed:
    """The customer's numbers and the cited sources' numbers (unit-aware).

    derive=True also allows products of two customer percentages (10 % × 95 % → 9.5 %); off by default, since
    every number in the output must appear in the customer transcript or on a cited page."""
    a = Allowed(customer=numbers_in(customer_text))
    for t in source_texts:
        for _, vals, unit in _tokens(t):
            if unit:
                a.with_unit |= {(v, unit) for v in vals}
            else:
                a.bare |= set(vals)
    if derive:
        pct = sorted({v for _, vals, unit in _tokens(customer_text) if unit == "%" for v in vals})[:20]
        a.customer |= {round(x * y / 100, 6) for x, y in combinations(pct, 2)}
    return a


def _needs_support(raw: str, vals: list[float], unit: str | None, is_range: bool) -> bool:
    if unit or is_range:
        return True
    return not vals or "." in raw or "," in raw or vals[0] > 10


def scrub(text: str, allowed: Allowed) -> tuple[str, int]:
    """Replace unsupported numbers (and their unit or range) with the placeholder. Returns (text, count)."""
    if not text:
        return text, 0
    count = 0

    def repl(m: re.Match) -> str:
        nonlocal count
        vals = [v for g in (m.group(1), m.group(3)) if g and (v := _value(g)) is not None]
        unit = _unit(m.group(4))
        if not _needs_support(m.group(1), vals, unit, bool(m.group(3))) or allowed.ok(vals, unit):
            return m.group(0)
        count += 1
        return PLACEHOLDER

    out = TOKEN.sub(repl, text)
    out = re.sub(rf"(\s*{re.escape(PLACEHOLDER)})(\s*(?:–|-|to)\s*{re.escape(PLACEHOLDER)})+", r"\1", out)
    return out, count
