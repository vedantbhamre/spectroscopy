import type { Report } from "@/lib/report";

// Organizer worked examples D01 and D02 (AFS_Examples_and_Reference.docx §2), transcribed into the
// report contract so the UI can be built and reviewed before the pipeline is connected.
// Shown with origin "reference" — never presented as our assistant's output.
// Concept fields (probe / location / fiberLink) are split out of the organizer's prose for the sketch.

const note = "Organizer worked example (AFS_Examples_and_Reference.docx §2) — reference, not assistant output";

export const referenceAnswers: Record<string, Report> = {
  D01: {
    scenarioId: "D01",
    title: "Blend potency in a tablet press feed frame",
    origin: "reference",
    originNote: note,
    decisionStatus: "provisional",
    requirements: {
      stated: [
        "Powder blend with API and excipients",
        "API concentration is the target",
        "Measurement in the feed frame is preferred",
        "Independent laboratory checks exist",
        "The pilot should compare options before buying equipment",
      ],
      unknowns: [
        "API and excipients",
        "Concentration range",
        "Acceptance limits",
        "Required response time",
        "Reference assay uncertainty",
        "Access and cleaning conditions",
      ],
    },
    questions: [
      { text: "Which API, excipients and concentration range are involved, and which changes must be distinguished?", impact: "method" },
      { text: "Which assay, uncertainty and sampling time provide the reference concentrations?", impact: "acceptance" },
      { text: "Which formulation, particle and operating changes occur between runs?", impact: "method" },
      { text: "What response time, acceptance limits, access and cleaning conditions apply?", impact: "setup" },
    ],
    recommendations: [
      {
        method: "NIR (diffuse reflection)",
        methodIds: ["NIR"],
        role: "primary",
        reason:
          "The supplied pharmaceutical example supports NIR reflection for blend concentration in powders. A matrix-specific calibration must be built and tested.",
        citations: [
          { source: "S01", page: "14–15", check: "unverified" },
          { source: "S01", page: "10", check: "unverified" },
        ],
      },
      {
        method: "Raman",
        methodIds: ["RAMAN"],
        role: "comparison",
        reason:
          "The same application family supports Raman as a comparison candidate. Check fluorescence background and signal quality.",
        citations: [
          { source: "S01", page: "14–15", check: "unverified" },
          { source: "S01", page: "11", check: "unverified" },
        ],
      },
      {
        method: "NIR + Raman",
        methodIds: ["NIR", "RAMAN"],
        role: "combination",
        reason:
          "Consider only after each method has been assessed on its own. Whether the combination adds value for this formulation is a hypothesis to test.",
        citations: [{ source: "S01", page: "14–15", check: "unverified" }],
      },
    ],
    concept: {
      summary:
        "A powder interface for each candidate in the feed frame, for example a diffuse reflection probe for NIR and a Raman probe. A combined probe could sample the same spot, but probe type, installation and optical configuration need AFS confirmation.",
      probe: "Diffuse reflection (NIR) · Raman probe",
      location: "Tablet press feed frame",
      fiberLink: "To be confirmed with AFS",
      analyzer: "NIR and Raman spectrometers",
      citations: [{ source: "S01", page: "Table 1 (p.6)", check: "unverified" }],
    },
    spectralRange: {
      summary:
        "NIR has a nominal method range of 780–2500 nm; specify only the usable range of the selected system. For Raman, state the excitation wavelength separately from the Raman shift. Do not pick an optimal band without sample spectra.",
      citations: [{ source: "S01", page: "10", check: "unverified" }],
    },
    risks: [
      "A change of API or excipients can invalidate a calibration.",
      "Physical variation of the powder (particle size, density, flow) changes the signal.",
      "A combination of methods does not guarantee a gain for every formulation.",
      "No accuracy, update rate or equipment compatibility has been confirmed.",
    ],
    feasibility: {
      steps: [
        "Prepare representative blends across the client-agreed API range and the relevant physical variation.",
        "Record spectra from each candidate together with independent API reference assays and timing information.",
        "Build single-method models first, then a combined model; validate on held-out runs or batches.",
        "Compare prediction error, bias and the ability to follow changes against the client’s requirements.",
      ],
      decisionBasis:
        "Agree numerical acceptance criteria with the client before the test. Choose the simplest configuration that meets them on independent material.",
    },
    premiseChecks: [],
    sources: [
      { source: "S01", page: "6", check: "unverified" },
      { source: "S01", page: "10", check: "unverified" },
      { source: "S01", page: "11", check: "unverified" },
      { source: "S01", page: "14–15", check: "unverified" },
    ],
  },
  D02: {
    scenarioId: "D02",
    title: "Fat and protein monitoring in opaque dairy product",
    origin: "reference",
    originNote: note,
    decisionStatus: "provisional",
    requirements: {
      stated: [
        "Opaque concentrated milk product in a flowing line",
        "Fat and protein are the targets",
        "Temperature and texture vary",
        "Laboratory checks remain available",
      ],
      unknowns: [
        "Product types and composition ranges",
        "Required accuracy and delay",
        "Installation point",
        "Cleaning regime",
      ],
    },
    questions: [
      { text: "Which product types, composition ranges and reference assays are involved?", impact: "method" },
      { text: "How do temperature, texture, homogenisation state and air bubbles vary?", impact: "method" },
      { text: "Can an optical interface see a representative sample and be kept clean?", impact: "setup" },
      { text: "What accuracy, delay, installation and cleaning limits apply?", impact: "acceptance" },
    ],
    recommendations: [
      {
        method: "NIR (diffuse reflection)",
        methodIds: ["NIR"],
        role: "primary",
        reason:
          "The supplied dairy example supports NIR reflection for opaque or concentrated products. Consider another geometry only if the measured optical behaviour justifies it.",
        citations: [
          { source: "S01", page: "17", check: "unverified" },
          { source: "S01", page: "18", check: "unverified" },
        ],
      },
    ],
    concept: {
      summary:
        "Test a reflection interface on representative laboratory samples before specifying the process installation. Confirm contact geometry, fouling control and cleaning with AFS and the client.",
      probe: "Reflection interface",
      location: "Processing line (point not yet defined)",
      fiberLink: "To be confirmed with AFS",
      analyzer: "NIR spectrometer",
      citations: [{ source: "S01", page: "Table 1 (p.6)", check: "unverified" }],
    },
    spectralRange: {
      summary:
        "780–2500 nm is the general NIR range, not a required full coverage. Check which bands the instrument and fiber actually cover, then inspect the sample spectra.",
      citations: [{ source: "S01", page: "10", check: "unverified" }],
    },
    risks: [
      "Temperature, texture and scattering changes can mimic composition changes.",
      "Fat and protein each need their own independent reference results.",
      "A reflection spectrum is not yet a fat or protein calibration.",
      "Interface ratings, signal stability and achievable errors are unknown.",
    ],
    feasibility: {
      steps: [
        "Collect representative samples with independent fat and protein results across production variation.",
        "Compare suitable optical geometries, first under controlled and then under realistic conditions.",
        "Separate the effect of physical changes (temperature, texture) from composition.",
        "Validate on independent production runs against client-agreed error and maintenance requirements.",
      ],
      decisionBasis:
        "Composition error and bias on independent production runs, together with maintenance and response needs. The acceptance targets come from the client; none is invented here.",
    },
    premiseChecks: [],
    sources: [
      { source: "S01", page: "6", check: "unverified" },
      { source: "S01", page: "10", check: "unverified" },
      { source: "S01", page: "17", check: "unverified" },
      { source: "S01", page: "18", check: "unverified" },
    ],
  },
};
