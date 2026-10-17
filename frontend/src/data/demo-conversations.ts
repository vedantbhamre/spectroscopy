import type { Citation, DecisionStatus, TraceStep } from "@/lib/report";
import { scenarioById } from "./scenarios";

// Scripted walkthroughs for the "How it works" chat demo. They illustrate behaviour on the
// evaluation enquiries; every quoted passage was checked against the cited page of the
// supplied material. They are not pipeline output and are labelled as such in the UI.

export interface DemoCase {
  id: string;
  label: string;
  lesson: string;
  enquiry: string;
  trace: TraceStep[];
  status: DecisionStatus;
  statusNote: string;
  reply: { text: string; cites?: Citation[] }[];
  questions: string[];
  next: string;
}

const v = (source: Citation["source"], page: string, quote: string, check: Citation["check"] = "verified"): Citation => ({ source, page, quote, check });

export const demoCases: DemoCase[] = [
  {
    id: "H04",
    label: "Fibre that cannot carry the signal",
    lesson: "Premise check catches an incompatible fibre",
    enquiry: scenarioById("H04")!.enquiry,
    trace: [
      { step: "Separate facts and unknowns", status: "ok", detail: "link length, routing, conditions unknown" },
      { step: "Retrieve AFS pages", status: "ok", detail: "S01 p.9 · S02 p.6, 7, 13" },
      { step: "Premise: fibre window covers method range", status: "fail", detail: "silica 0.35–2.4 µm vs MIR 2.5–25 µm" },
      { step: "Compose and verify citations", status: "ok", detail: "5 of 5 quotes found" },
    ],
    status: "insufficient",
    statusNote: "Concept not approved",
    reply: [
      { text: "I can't approve this concept. MIR ATR works in the mid-IR, 4000–400 cm⁻¹ (2.5–25 µm).", cites: [v("S01", "9", "Vibrational spectroscopy in the mid-IR range (4000–400 cm-1) is one of the most informative methods of chemical analysis.")] },
      { text: "A Vis-NIR silica fibre transmits about 350–2400 nm, so the existing cable cannot carry that range. The long silica cables in the AFS material are for Vis-NIR process control.", cites: [v("S02", "6", "standard and Al/Cu-coated VIS-NIR silica fibers 350–2400 nm", "visual_note"), v("S02", "7", "Robust 100-300m cables made with Silica fibers of low OH-content")] },
      { text: "Water in petroleum is a supplied MIR ATR application, but it shows laboratory spectra only: a reason to test, not proof for a line in another building.", cites: [v("S02", "13", "Application: measurement of water content in petroleum"), v("S02", "13", "Laboratory spectra; no process installation, fiber length or analyzer distance is shown.", "visual_note")] },
    ],
    questions: [
      "What is the link length and routing between the line and the analyser building?",
      "Which temperature, pressure and hazardous-area conditions apply at the measuring point?",
      "Could the MIR analyser be placed closer to the line?",
      "Which water range and reference method define success?",
    ],
    next: "Compare an MIR ATR probe on representative oil–water samples against the laboratory water method, with an infrared fibre type chosen for the confirmed link length.",
  },
  {
    id: "H03",
    label: "Sensitive, but no target",
    lesson: "Asks for a fluorescent target before recommending",
    enquiry: scenarioById("H03")!.enquiry,
    trace: [
      { step: "Separate facts and unknowns", status: "ok", detail: "no fluorescent target or reference named" },
      { step: "Retrieve AFS pages", status: "ok", detail: "S01 p.5, 16" },
      { step: "Premise: method has a defined target", status: "warn", detail: "sensitivity is the only reason given" },
      { step: "Compose and verify citations", status: "ok", detail: "4 of 4 quotes found" },
    ],
    status: "insufficient",
    statusNote: "No method recommended yet",
    reply: [
      { text: "Sensitivity alone doesn't justify it. In the supplied bioprocess example, fluorescence is used for defined fluorescent compounds such as NADH, tryptophan and riboflavin.", cites: [v("S01", "16", "Fluorescence spectroscopy can be used for highsensitivity detection (down to the nM-µM range) of critical cofactors and amino acids like NADH, tryptophan, and riboflavin.")] },
      { text: "Glucose in the same source is tracked with NIR or Raman, not fluorescence.", cites: [v("S01", "16", "NIR spectroscopy is effective for tracking major components like glucose or glycerol in the millimolar range"), v("S01", "16", "direct detection of specific metabolites like glucose, acetate, or lactate")] },
      { text: "Fluorescence spectra are broad and overlapping, so without a named target or a reference relationship I can't recommend it for glucose or viable biomass.", cites: [v("S01", "5", "NIR, UV, and fluorescence spectra contain broad, highly overlapping signals")] },
    ],
    questions: [
      "Is there a fluorescent compound in your process that is linked to glucose or to viable cells?",
      "Which reference methods give glucose and viable biomass today, and how often?",
      "Which ranges and response times do you need for each variable?",
    ],
    next: "Record fluorescence alongside independent glucose and viable-cell references on a few runs to test whether any relationship exists, before building on it.",
  },
  {
    id: "H06",
    label: "A study is not a clinical claim",
    lesson: "Refuses to stretch a source beyond its scope",
    enquiry: scenarioById("H06")!.enquiry,
    trace: [
      { step: "Separate facts and unknowns", status: "ok", detail: "no in vivo data, no own validation" },
      { step: "Retrieve AFS pages", status: "ok", detail: "S03 p.2, 9" },
      { step: "Premise: source supports the requested use", status: "fail", detail: "in vitro study cited for live surgery" },
      { step: "Compose and verify citations", status: "ok", detail: "2 of 2 quotes found" },
    ],
    status: "out_of_scope",
    statusNote: "Clinical use outside scope",
    reply: [
      { text: "No. The kidney study tested sensor prototypes on in vitro samples, seven tumour–normal pairs, so it can't be quoted as proof that a sensor is ready for live surgery.", cites: [v("S03", "2", "seven pairs each of tumor and normal in vitro clinical samples from different patients")] },
      { text: "Its results are compared against histology. Your own setup would need the same kind of independent reference before any clinical step.", cites: [v("S03", "9", "histologically observed tumor discrimination")] },
    ],
    questions: [
      "Which tissue samples and reference diagnosis can you access for a laboratory study?",
      "What decision should the sensor support, and what error would be acceptable?",
      "Who owns the clinical validation and regulatory path?",
    ],
    next: "Reproduce the measurement on your own setup with in vitro samples and histology as the reference, then define what result would justify a clinical study.",
  },
  {
    id: "D01",
    label: "A defensible shortlist",
    lesson: "Simplest method first, combination as a hypothesis",
    enquiry: scenarioById("D01")!.enquiry,
    trace: [
      { step: "Separate facts and unknowns", status: "ok", detail: "API, range, limits, response time unknown" },
      { step: "Retrieve AFS pages", status: "ok", detail: "S01 p.14–15" },
      { step: "Premise checks", status: "ok", detail: "nothing contradicted" },
      { step: "Compose and verify citations", status: "ok", detail: "3 of 3 quotes found" },
    ],
    status: "provisional",
    statusNote: "Provisional assessment",
    reply: [
      { text: "Blend potency in the feed frame of a rotary tablet press is a supplied application.", cites: [v("S01", "14", "specifically in the feed frame of a rotary tablet press")] },
      { text: "Test NIR reflection first and Raman as the comparison candidate; both are the setups described for this task.", cites: [v("S01", "15", "NIR spectrometer and light source coupled with a NIR reflection probe")] },
      { text: "The source reports a gain from combining them, but whether that holds for your formulation is a hypothesis to test after each method on its own.", cites: [v("S01", "15", "By combining Raman and NIR, these models can predict API potency or coating thickness with higher accuracy and robustness than single-method models.")] },
    ],
    questions: [
      "Which API, excipients and concentration range are involved?",
      "Which assay and sampling time provide the reference concentrations?",
      "What response time, acceptance limits, access and cleaning conditions apply?",
    ],
    next: "Record both methods on representative blends with independent API assays, build single-method models first, then a combined one, and validate on held-out batches.",
  },
];
