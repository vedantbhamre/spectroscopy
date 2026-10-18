"""S01 Table 1 (p.6): methods, measurement techniques, sample types and the qualitative cost rating.

Rows from the organisers' transcription (AFS_method_comparison_table.xlsx, "Transcribed from the rendered
page because PDF text extraction interleaves the columns"). Ratings are the source document's
low / average / high, not measured values. Used for the "simplest, cheapest sufficient method" rule and
for the geometry-vs-optics check.
"""

from app.schemas import Citation

# (method id, technique, physical phenomenon, sample type, cost)
ROWS: list[tuple[str, str, str, str, str]] = [
    ("MIR_ATR", "ATR probe", "absorption", "liquid, paste, soft", "high"),
    ("MIR_ATR", "cuvette", "absorption", "liquid", "average"),
    ("MIR_ATR", "sample surface", "diffuse reflection", "solid", "average"),
    ("NIR", "transmission or transflection probe", "transmission", "liquid, colloidal", "average"),
    ("NIR", "diffuse reflection probe", "diffuse reflection", "scattering media, powder", "average"),
    ("NIR", "surface at a distance", "diffuse reflection", "solid, powder", "average"),
    ("RAMAN", "Raman probe", "Raman scattering (emission)", "liquid, powder, solid", "high"),
    ("UVVIS", "ATR probe", "absorption", "liquid", "average"),
    ("UVVIS", "diffuse reflection probe", "diffuse reflection", "solid, pill", "low"),
    ("UVVIS", "transmission or transflection probe", "transmission", "liquid", "low"),
    ("FLUO", "fluorimetric probe", "fluorescence (emission)", "liquid, solid", "low"),
]
RANK = {"low": 0, "average": 1, "high": 2}
TABLE1 = Citation(source="S01", page="Table 1 (p.6)", check="unverified")


def probe_cost(method_id: str) -> str | None:
    """Cost of the method's in-line probe options (the cheapest probe row; cuvettes and surfaces are laboratory set-ups)."""
    costs = [r[4] for r in ROWS if r[0] == method_id and "probe" in r[1]]
    return min(costs, key=RANK.get) if costs else None


def for_prompt() -> str:
    """Rows as cited text; cite them as {"source": "S01", "page": "Table 1 (p.6)", "quote": "<one row>"}."""
    return "\n".join(f"{m}: {tech} ({phen}); sample: {sample}; cost: {cost}" for m, tech, phen, sample, cost in ROWS)


# Probe geometry vs the optical density of the medium (S01 p.16 and p.18; quotes verified on the pages).
CLEAR_TRANSMISSION = Citation(source="S01", page="16", check="verified", quote=(
    "For highly transparent liquids with low optical density, UV-Transmission or Transflection probes are ideal"))
OPAQUE_SATURATES = Citation(source="S01", page="16", check="verified", quote=(
    "as the media becomes more opaque, turbid, or highly concentrated, the signal in a standard transmission setup "
    "becomes saturated because the light cannot penetrate the bulk of the sample"))
HIGH_OD_ATR = Citation(source="S01", page="16", check="verified", quote="In these high-OD scenarios, a UV-ATR (Attenuated Total Reflection) probe is used.")
REFLECTION_SCATTERING = Citation(source="S01", page="18", check="verified", quote=(
    "reflection can work well in highly scattering environments but can be less representative for clear liquids"))
