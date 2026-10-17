"""Method ranges and fibre windows, with the passages that support them.

Mirrors frontend/src/data/optics.ts. Ranges in µm; None = no fixed nominal range in the sources.
Nominal method ranges are not the usable range of a specific instrument, fibre or probe.
"""

import math
from dataclasses import dataclass

from app.schemas import Citation


@dataclass(frozen=True)
class Method:
    id: str
    label: str
    range_um: tuple[float, float] | None
    range_label: str
    cite: Citation | None


@dataclass(frozen=True)
class Fiber:
    id: str
    label: str
    range_um: tuple[float, float]
    cite: Citation


def _c(source: str, page: str, quote: str, check: str = "verified") -> Citation:
    return Citation(source=source, page=page, quote=quote, check=check)  # type: ignore[arg-type]


METHODS: dict[str, Method] = {
    "NIR": Method("NIR", "NIR", (0.78, 2.5), "780–2500 nm", _c("S01", "10", "NIR spectra (780–2500 nm) contain predominantly overtones")),
    "MIR_ATR": Method("MIR_ATR", "MIR (ATR)", (2.5, 25.0), "4000–400 cm⁻¹ (2.5–25 µm)",
                      _c("S01", "9", "Vibrational spectroscopy in the mid-IR range (4000–400 cm-1) is one of the most informative methods of chemical analysis.")),
    "RAMAN": Method("RAMAN", "Raman", None, "Raman shift and laser excitation stated separately", None),
    "FLUO": Method("FLUO", "Fluorescence", None, "depends on the fluorescent species", None),
    "UVVIS": Method("UVVIS", "UV-Vis", None, "depends on target and setup", None),
}

# S02 p.6 is a figure; values are the team's transcription ("check figure before relying on exact numbers").
FIBERS: dict[str, Fiber] = {
    "silica_uvvis": Fiber("silica_uvvis", "UV-Vis silica fibre", (0.19, 1.2), _c("S02", "6", "standard and Al/Cu-coated UV-VIS silica fibers 190–1200 nm", "visual_note")),
    "silica_visnir": Fiber("silica_visnir", "Vis-NIR silica fibre", (0.35, 2.4), _c("S02", "6", "standard and Al/Cu-coated VIS-NIR silica fibers 350–2400 nm", "visual_note")),
    "chalcogenide": Fiber("chalcogenide", "chalcogenide (CIR) fibre", (1.1, 6.5), _c("S02", "6", "chalcogenide As-S IR fibers 1100–6500 nm", "visual_note")),
    "pir": Fiber("pir", "polycrystalline IR (PIR) fibre", (3.0, 17.0), _c("S02", "6", "polycrystalline infrared fibers 3000 nm–17 µm", "visual_note")),
    "hwg": Fiber("hwg", "hollow glass waveguide", (2.0, 18.0), _c("S02", "6", "hollow glass waveguides 2000 nm–18 µm", "visual_note")),
    "inf": Fiber("inf", "indium fluoride fibre", (0.3, 5.5), _c("S02", "6", "indium fluoride fibers 300–5500 nm", "visual_note")),
    "zrf": Fiber("zrf", "zirconium fluoride fibre", (0.3, 4.5), _c("S02", "6", "zirconium fluoride fibers 300–4500 nm", "visual_note")),
}


def coverage(method: tuple[float, float], fiber: tuple[float, float]) -> tuple[str, float]:
    """Share (log scale) of the nominal method range that the fibre window transmits."""
    lo, hi = max(method[0], fiber[0]), min(method[1], fiber[1])
    if hi <= lo:
        return "none", 0.0
    share = (math.log(hi) - math.log(lo)) / (math.log(method[1]) - math.log(method[0]))
    return ("full" if share >= 0.999 else "partial"), share
