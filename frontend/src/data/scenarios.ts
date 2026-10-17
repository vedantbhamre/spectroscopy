// Verbatim from AFS_Examples_and_Reference.docx §1 (D01–D08) and
// customer_scenarios_for_final_evaluation.txt (H01–H06). Do not edit the text.

export type ScenarioSet = "development" | "evaluation";

export interface Scenario {
  id: string;
  set: ScenarioSet;
  title: string;
  enquiry: string;
  factsStated?: string[];
  usefulSources?: string;
}

export const scenarios: Scenario[] = [
  {
    id: "D01",
    set: "development",
    title: "Blend potency in a tablet press feed frame",
    enquiry:
      "We manufacture tablets from a powder blend containing an active pharmaceutical ingredient and excipients. Laboratory checks tell us whether the blend is on target, but results arrive after the material has moved through the press. We want to assess whether a fiber based measurement in the feed frame could follow API concentration changes. Our first pilot should compare reasonable measurement options before we commit to production equipment.",
    factsStated: [
      "Powder blend",
      "API concentration is the requested variable",
      "Feed frame measurement is preferred",
      "Independent laboratory checks already exist",
    ],
    usefulSources: "S01 p.5, 10, 11, 14–15",
  },
  {
    id: "D02",
    set: "development",
    title: "Fat and protein monitoring in opaque dairy product",
    enquiry:
      "We produce an opaque, concentrated milk product that flows through a processing line. We currently sample it for fat and protein analysis and would like earlier information about composition changes. Product temperature and texture vary during production. We want an initial spectroscopy concept and a practical comparison experiment, while retaining our laboratory checks.",
    factsStated: [
      "Opaque concentrated dairy product",
      "Fat and protein are the requested variables",
      "Flowing process",
      "Temperature and texture vary",
      "Laboratory checks remain available",
    ],
    usefulSources: "S01 p.5, 10, 17, 18",
  },
  {
    id: "D03",
    set: "development",
    title: "A clear whey stream before concentration",
    enquiry:
      "Our dairy process includes a relatively clear whey stream before a concentration stage. We want to investigate whether spectroscopy can track protein concentration as the stream changes, with laboratory results used as the reference. The stream can become more turbid under some operating conditions. We need a first measurement concept that handles this change rather than assuming the liquid always remains clear.",
    factsStated: [
      "Whey stream",
      "Protein concentration requested",
      "Initially relatively clear",
      "Turbidity may change",
      "Laboratory reference results available",
    ],
    usefulSources: "S01 p.5, 10, 17, 18",
  },
  {
    id: "D04",
    set: "development",
    title: "Glucose and lactate trends in an aqueous bioprocess",
    enquiry:
      "We run a cell culture process in an aqueous medium. Glucose and lactate are measured from samples, and the delay makes it difficult to see changes promptly. We are exploring an in situ spectroscopy pilot that can be checked against those existing laboratory measurements. The medium and cell population change during the run; we have not yet selected a probe or a calibration strategy.",
    factsStated: [
      "Aqueous cell culture",
      "Glucose and lactate requested",
      "Medium and cells change during the run",
      "Laboratory reference measurements exist",
    ],
    usefulSources: "S01 p.5, 10, 11, 16",
  },
  {
    id: "D05",
    set: "development",
    title: "Biomass related monitoring during yeast fermentation",
    enquiry:
      "We would like an optical measurement during yeast fermentation to help us follow growth and notice changes earlier. Our team has mentioned both a biomass signal and a metabolic signal, but these have not been defined as separate targets. The broth becomes more optically dense as the run develops. We need help turning this request into an initial feasibility study with useful reference measurements.",
    factsStated: [
      "Yeast fermentation",
      "Growth and metabolic changes mentioned",
      "Optical density changes",
      "Target variables still need definition",
    ],
    usefulSources: "S01 p.5, 16",
  },
  {
    id: "D06",
    set: "development",
    title: "Water content in a petroleum stream",
    enquiry:
      "We handle a petroleum stream and currently send samples to a laboratory for water determination. We want to investigate a fiber based measurement closer to the process so that changes can be noticed sooner. The analyzer would be outside the process area. Before selecting equipment, we need to know what to clarify and what a first comparison experiment should establish.",
    factsStated: [
      "Petroleum stream",
      "Water content requested",
      "Independent laboratory water measurement exists",
      "Analyzer outside the process area",
    ],
    usefulSources: "S01 p.6, 9, 10; S02 p.6, 13",
  },
  {
    id: "D07",
    set: "development",
    title: "API concentration during hot polymer extrusion",
    enquiry:
      "We are developing a hot polymer extrusion process that incorporates an active pharmaceutical ingredient. We want to investigate whether an optical measurement can detect composition changes while the melt is being processed. We have offline assays, but the process interface is hot and may be exposed to material build up. We need an initial comparison plan and the questions required before choosing a probe.",
    factsStated: [
      "Hot polymer melt",
      "API composition changes requested",
      "Offline assays available",
      "Interface may foul",
    ],
    usefulSources: "S01 p.5, 6, 10; S02 p.14",
  },
  {
    id: "D08",
    set: "development",
    title: "Local measurements of heterogeneous model tissues",
    enquiry:
      "Our research group is evaluating a spectral measurement interface using model biological tissues such as chicken muscle, fat and liver. We want to compare MIR ATR and fluorescence information, because the material is heterogeneous and sequential measurements may not sample the same location. This is a laboratory classification study. We need a first comparison experiment and a clear statement of what its results would demonstrate.",
    factsStated: [
      "Laboratory model tissues",
      "Chicken muscle, fat and liver are examples",
      "Heterogeneous sample",
      "Compare measurements from the same local area",
      "No clinical use requested",
    ],
    usefulSources: "S01 p.5, 6, 8–10; S04 p.1, 3, 4",
  },
  {
    id: "H01",
    set: "evaluation",
    title: "A new formulation after an existing NIR pilot",
    enquiry:
      "Our existing NIR pilot follows API concentration in one powder formulation at the tablet press feed frame. We are introducing a different API and excipient blend and would like to reuse the calibration. A colleague suggests adding Raman so that the old calibration will remain valid. What should our first technical assessment and experiment be?",
  },
  {
    id: "H02",
    set: "evaluation",
    title: "Composition monitoring across two dairy streams",
    enquiry:
      "Our dairy process handles both a relatively clear whey stream and an opaque milk concentrate. We want a pilot for composition monitoring, using laboratory protein and fat results where those variables are relevant. We can compare different measurement interfaces before choosing the installation. What first measurement concepts and comparison experiment would make sense for these two streams?",
  },
  {
    id: "H03",
    set: "evaluation",
    title: "A fluorescence instrument requested for glucose and viable biomass",
    enquiry:
      "We already have a fluorescence spectrometer and would like to use it to report glucose concentration and viable biomass directly during fermentation. Our only justification is that fluorescence can be very sensitive. We have not identified a fluorescent target, marker or reference relationship. What should the assistant tell us?",
  },
  {
    id: "H04",
    set: "evaluation",
    title: "Reuse of a silica link for petroleum MIR ATR",
    enquiry:
      "We want to investigate water content in a petroleum line using MIR ATR. The analyzer would be in another building. We already have a silica fiber cable from a visible or NIR measurement setup and would like to reuse it. The link length, routing and operating conditions have not yet been supplied. Can the assistant approve this concept?",
  },
  {
    id: "H05",
    set: "evaluation",
    title: "An undefined off specification liquid",
    enquiry:
      "We have a liquid process that occasionally goes off specification. We suspect contamination, but we cannot yet name the contaminant or the affected quality variable. We would like you to recommend the best spectroscopy method and exact sensor configuration immediately. What information and first experiment should come before that decision?",
  },
  {
    id: "H06",
    set: "evaluation",
    title: "A research sensor requested for immediate surgical use",
    enquiry:
      "We read the supplied LED NIR kidney study and want to use the same concept to guide tumor boundary decisions during live surgery. Can we quote its findings as proof that the proposed sensor is ready for that use? We have no new in vivo data and no validation on our own setup. What assessment and next feasibility steps are appropriate?",
  },
];

export const scenarioById = (id: string) => scenarios.find((s) => s.id === id);
