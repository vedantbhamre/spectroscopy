"""Where each topic lives in the AFS material: the organisers' source guide (AFS_Examples_and_Reference.docx §4).

S01: methods p.2–6 (comparison table p.6), combining methods p.7–9, kits and probes p.10–12, application cases
p.13–18 (medical, pharmaceutical, bioprocess, dairy). S02: fibre types and transmission ranges p.6–10, water in
petroleum p.13, API in polymer extrusion p.14, combined probes p.15–16. S03 and S04 are research papers.

Customers describe processes, not methods, so keyword search alone rarely reaches the method pages an assessment
needs. Retrieval therefore always includes the method overview and comparison table, the application pages for the
domain the enquiry is about, the method pages that the enquiry names or that those application pages discuss, and the
fibre pages when fibres, cables or distance come up, and the combining-methods pages when methods are used together. Generic: keyed on application domain, method and topic only.
"""

import re

Page = tuple[str, int]

CORE: list[Page] = [("S01", 5), ("S01", 6)]  # method overview; S01 Table 1 (method comparison)

DOMAIN_PAGES: dict[str, list[Page]] = {
    "pharmaceutical solids": [("S01", 14), ("S01", 15), ("S02", 14)],
    "dairy and food": [("S01", 17), ("S01", 18)],
    "bioprocess": [("S01", 16)],
    "petroleum and chemicals": [("S02", 13), ("S02", 14)],
    "medical and tissue": [("S01", 13), ("S03", 1), ("S04", 1)],
}

METHOD_PAGES: dict[str, Page] = {"MIR_ATR": ("S01", 9), "NIR": ("S01", 10), "RAMAN": ("S01", 11), "FLUO": ("S01", 12), "UVVIS": ("S01", 16)}

METHOD_PATTERNS: dict[str, str] = {
    "MIR_ATR": r"\b(mir|mid[- ]?ir|atr|ftir)\b",
    "NIR": r"\bnir\b|near[- ]infrared",
    "RAMAN": r"\braman\b",
    "FLUO": r"fluoresc",
    "UVVIS": r"\buv[- ]?vis\b|\buv\b",
}

FIBRE_PAGES: list[Page] = [("S02", 6), ("S02", 7)]

# Combined probes for a pair of methods: S01 p.15 (NIR + Raman, pharmaceutical), S04 and S02 p.15 (ATR mid-IR + fluorescence,
# tissue classification). Routed when both methods of the pair come up.
PAIR_PAGES: dict[frozenset, list[Page]] = {
    frozenset({"NIR", "RAMAN"}): [("S01", 15)],
    frozenset({"MIR_ATR", "FLUO"}): [("S04", 1), ("S04", 3), ("S04", 4), ("S02", 15)],
}

# S01 §3.2 "Synergy of Combining Spectral Methods" when the enquiry is about using methods together.
COMBINATION_PAGES: list[Page] = [("S01", 7), ("S01", 8)]
COMBINATION_TOPIC = re.compile(r"combin|complementar|simultaneous|same (location|spot|point|position)|multi-?spectral|multi-?modal|together", re.I)
FIBRE_TOPIC = re.compile(r"fib(er|re)|cable|distance|remote|another building|outside the process|far from|control room", re.I)

# A method counts as discussed on an application page when it is mentioned at least this often there.
METHOD_MENTIONS = 2
