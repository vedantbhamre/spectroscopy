"""Application tags for source passages and for the customer's process.

The AFS material describes applications in a few domains (pharmaceutical solids, dairy and food,
bioprocess, petroleum and chemicals, medical and tissue, environment). A retrieved example carries the
tags of the text around it; when they do not include the customer's domain, using the example is a
transfer assumption, not support.
"""

import re

from app.services.citations import normalise, page_text

DOMAINS: dict[str, str] = {
    "pharmaceutical solids": r"\btablet|pharma|\bapi\b|excipient|powder blend|feed frame|granul|coating thickness|potency",
    "dairy and food": r"\bmilk|dairy|whey|yogh?urt|butter|cheese|\bfood|beverage|permeate",
    "bioprocess": r"ferment|bioreactor|cell culture|biomass|\byeast|cultivation|bioprocess|\bcells?\b.{0,20}(density|suspension)",
    "petroleum and chemicals": r"petroleum|crude oil|\bfuel|hydrocarbon|polymer|refiner|chemical (process|reaction)|solvent",
    "medical and tissue": r"tissue|tumou?r|clinical|kidney|patient|in vivo|biopsy|surg|cancer|malignan|benign|oncolog|carcinom"
                          r"|histolog|patholog|intra-?operative|operating (room|theatre)|doctors?\b|physician|hospital|medical",
    "environment": r"\bsoil|waste ?water|drinking water|environmental (monitoring|sample)|groundwater",
}


def tag(text: str) -> list[str]:
    t = (text or "").lower()
    return [d for d, pat in DOMAINS.items() if re.search(pat, t)]


def context(source: str, page: str, quote: str | None, width: int = 250) -> str:
    """The passage around a quote on its page (the whole page if the quote is not found)."""
    text = page_text(source, page)
    if not quote:
        return text
    n, q = normalise(text), normalise(quote)
    i = n.find(q[:60])
    return n if i < 0 else n[max(0, i - width): i + len(q) + width]


def of_citation(source: str, page: str, quote: str | None) -> list[str]:
    return tag(context(source, page, quote))
