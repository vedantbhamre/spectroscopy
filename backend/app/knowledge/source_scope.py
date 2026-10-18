"""What each research source actually demonstrated, dimension by dimension, with verbatim page quotes.

Used by the source-scope premise check: when an enquiry wants to use a study as proof for a clinical or process use, the
report lists every dimension in which the study differs from that use (sample state, task, instrument, sample size, stated
aim). Keyed on the source, never on an enquiry. Quotes are checked against the pages by tests/test_premises.py.
"""

from app.schemas import Citation

Dimension = tuple[str, Citation]  # (what the study shows / does not show, page quote)

SCOPE: dict[str, list[Dimension]] = {
    "S03": [
        ("Samples: resected tissue measured in vitro (frozen and thawed), not living tissue in vivo",
         Citation(source="S03", page="3", quote="spectra of frozen/thawed biopsies can differ from real-life in vivo measurements")),
        ("Size: seven tumour/normal pairs from seven patients, too few to rule out an over-fitted model",
         Citation(source="S03", page="2", quote="seven pairs each of tumor and normal in vitro clinical samples from different patients")),
        ("Task: whether a few wavelengths capture tumour-related differences between whole samples, not where a boundary lies",
         Citation(source="S03", page="2", quote="The main analytical task of this study was to establish the fundamental feasibility of the LED-based optical diagnostics")),
        ("Instrument: the authors' two LED sensor prototypes, not the customer's sensor",
         Citation(source="S03", page="1", quote="Two sensor prototypes were tested using 14 in vitro clinical samples of 7 different patients")),
        ("Outcome: in vivo use is the stated aim of further work, not a result",
         Citation(source="S03", page="14", quote="results reported here can be considered as a successful feasibility study of an LED-based NIR sensor for cancer diagnostics aimed at in vivo applications")),
    ],
}

CLINICAL_SOURCES = ["S03"]


def clinical_scope() -> list[Dimension]:
    return [d for s in CLINICAL_SOURCES for d in SCOPE[s]]
