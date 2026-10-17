// Reference data for the spectral-band view.
// Methods: AFS_Examples_and_Reference.docx §5 (nominal ranges) + S01 Table 1 (p.6).
// Fibers: S02 p.6 (figure), transcribed in the docx §5 — "check the figure before relying on an exact number".
// Ranges are in µm. `null` = no fixed nominal range in the sources (depends on target / setup).

export type MethodId = "NIR" | "MIR_ATR" | "RAMAN" | "FLUO" | "UVVIS";

export interface MethodRef {
  id: MethodId;
  label: string;
  rangeUm: [number, number] | null;
  rangeLabel: string;
  samples: string;
  limitations: string;
  read: string;
}

export const methods: MethodRef[] = [
  {
    id: "UVVIS",
    label: "UV-Vis",
    rangeUm: null,
    rangeLabel: "Depends on target and setup",
    samples: "A defined absorption; biomass-related optical signal in cell suspensions.",
    limitations: "Overlapping signals in mixtures; optical density is not a viable cell count.",
    read: "S01 p.5–6, 16",
  },
  {
    id: "FLUO",
    label: "Fluorescence",
    rangeUm: null,
    rangeLabel: "Depends on the fluorescent species",
    samples: "Only a defined fluorescent species or a justified indicator.",
    limitations: "High sensitivity, low selectivity; not a direct measurement of every analyte.",
    read: "S01 p.5, 6, 16; S04",
  },
  {
    id: "RAMAN",
    label: "Raman",
    rangeUm: null,
    rangeLabel: "Raman shift (cm⁻¹) and laser excitation (nm) stated separately",
    samples: "Powders and liquids: pharmaceutical blends, bioprocess metabolites.",
    limitations: "Weak signal, fluorescence background; calibration specific to the matrix.",
    read: "S01 p.11–12, 14–16",
  },
  {
    id: "NIR",
    label: "NIR",
    rangeUm: [0.78, 2.5],
    rangeLabel: "780–2500 nm",
    samples:
      "Powders, dairy. Diffuse reflection for scattering samples; transmission or transflection for clear liquids.",
    limitations: "Overlapping bands, physical variation; calibration specific to the matrix.",
    read: "S01 p.5, 10, 14–15, 17–18",
  },
  {
    id: "MIR_ATR",
    label: "MIR (ATR)",
    rangeUm: [2.5, 25],
    rangeLabel: "4000–400 cm⁻¹ (2.5–25 µm)",
    samples:
      "Liquids, pastes and soft solids in contact with the ATR crystal. Leads: water in petroleum, API in polymer extrusion.",
    limitations: "Usable range limited by fiber and crystal; contact, fouling, compatibility.",
    read: "S01 p.6, 9–10; S02 p.6, 13–14",
  },
];

export interface FiberRef {
  id: string;
  label: string;
  short: string;
  rangeUm: [number, number];
}

export const fibers: FiberRef[] = [
  { id: "SIL_UV", label: "UV-Vis silica (std, Al/Cu-coated)", short: "UV-Vis silica", rangeUm: [0.19, 1.2] },
  { id: "SIL_NIR", label: "Vis-NIR silica (std, Al/Cu-coated)", short: "Vis-NIR silica", rangeUm: [0.35, 2.4] },
  { id: "ZRF", label: "Zirconium fluoride", short: "ZrF₄", rangeUm: [0.3, 4.5] },
  { id: "INF", label: "Indium fluoride", short: "InF₃", rangeUm: [0.3, 5.5] },
  { id: "CIR", label: "Chalcogenide As-S IR (CIR)", short: "CIR", rangeUm: [1.1, 6.5] },
  { id: "HWG", label: "Hollow glass waveguide (HWG)", short: "HWG", rangeUm: [2, 18] },
  { id: "PIR", label: "Polycrystalline IR (PIR)", short: "PIR", rangeUm: [3, 17] },
];

export const FIBER_SOURCE = "S02 p.6";

export type Coverage = "full" | "partial" | "none";

/** How much of a method's nominal range a fiber window transmits. Nominal ≠ usable range of a real system. */
export function coverage(method: [number, number], fiber: [number, number]): { kind: Coverage; share: number } {
  const lo = Math.max(method[0], fiber[0]);
  const hi = Math.min(method[1], fiber[1]);
  if (hi <= lo) return { kind: "none", share: 0 };
  const share = (Math.log(hi) - Math.log(lo)) / (Math.log(method[1]) - Math.log(method[0]));
  return { kind: share >= 0.999 ? "full" : "partial", share };
}

// S01 Table 1 (p.6), from AFS_method_comparison_table.xlsx
export interface TableRow {
  method: string;
  technique: string;
  phenomenon: string;
  sample: string;
  depth: string;
  sensitivity: string;
  selectivity: string;
  cost: string;
}

export const table1: TableRow[] = [
  ["IR spectroscopy", "ATR platform", "absorption", "liquid, paste, soft", "1-6 µm", "average", "high", "high"],
  ["IR spectroscopy", "ATR probe*", "absorption", "liquid, paste, soft", "1-6 µm", "average", "high", "high"],
  ["IR spectroscopy", "cuvette", "absorption", "liquid", "10-100 µm", "high", "high", "average"],
  ["IR spectroscopy", "sample layer", "absorption", "solid film", "5-50 µm", "high", "high", "average"],
  ["IR spectroscopy", "sample surface", "diffuse reflection", "solid", "10 µm", "average", "high", "average"],
  ["NIR spectroscopy", "cuvette", "transmission", "liquid", "1-5 mm", "average", "average", "average"],
  ["NIR spectroscopy", "transmission or transflection probe", "transmission", "liquid, colloidal", "1-10 mm", "average", "average", "average"],
  ["NIR spectroscopy", "diffuse reflection probe", "diffuse reflection", "scattering media, powder", "0.5-1 mm", "average", "average", "average"],
  ["NIR spectroscopy", "integrating sphere", "diffuse reflection", "solid, powder", "5-10 mm", "average", "average", "average"],
  ["NIR spectroscopy", "surface at a distance", "diffuse reflection", "solid, powder", "2-5 mm", "average", "average", "average"],
  ["Raman spectroscopy", "cuvette 90 deg", "Raman scattering (emission)", "liquid", "2-5 mm", "average", "high", "high"],
  ["Raman spectroscopy", "Raman probe", "Raman scattering (emission)", "liquid, powder, solid", "2-5 mm", "average", "high", "high"],
  ["UV/Visible spectroscopy", "cuvette", "absorption", "liquid", "1-5 mm", "high", "low", "low"],
  ["UV/Visible spectroscopy", "ATR probe", "absorption", "liquid", "0.1-1 µm", "low", "low", "average"],
  ["UV/Visible spectroscopy", "diffuse reflection probe", "diffuse reflection", "solid, pill", "1-5 mm", "low", "low", "low"],
  ["UV/Visible spectroscopy", "transmission or transflection probe", "transmission", "liquid", "1-10 mm", "low", "low", "low"],
  ["UV/Visible spectroscopy", "probe, lens", "emission of an external source", "radiating sample", "any", "high", "low", "low"],
  ["Fluorimetry", "cuvette 90 deg", "fluorescence (emission)", "liquid", "10 mm", "high", "low", "low"],
  ["Fluorimetry", "fluorimetric probe", "fluorescence (emission)", "liquid, solid", "1-5 mm", "high", "low", "low"],
].map(([method, technique, phenomenon, sample, depth, sensitivity, selectivity, cost]) => ({
  method, technique, phenomenon, sample, depth, sensitivity, selectivity, cost,
}));
