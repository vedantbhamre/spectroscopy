import type { AssessResponse, ChatMessage } from "./report";

// Layout placeholder used only when ASSESS_DEMO=1 and no backend is connected.
// It contains no technical content: every field says it is a placeholder, and the report is badged DEMO.

export function demoResponse(messages: ChatMessage[]): AssessResponse {
  const users = messages.filter((m) => m.role === "user");
  const latest = users[users.length - 1].content;
  const sentences = latest.split(/(?<=[.!?])\s+/).map((s) => s.trim()).filter(Boolean).slice(0, 6);
  const turn = users.length;

  return {
    reply:
      "Demo mode: the assessment pipeline is not connected, so this turn only shows how the conversation and report will look. Nothing below is an assessment.",
    trace: [
      { step: "Input check", status: "skipped", detail: "Demo mode" },
      { step: "Separate facts and unknowns", status: "skipped", detail: "Demo mode" },
      { step: "Retrieve AFS pages", status: "skipped", detail: "Demo mode" },
      { step: "Compose report", status: "skipped", detail: "Demo mode" },
      { step: "Verify citations", status: "skipped", detail: "Demo mode" },
    ],
    report: {
      title: turn > 1 ? `Demo placeholder, turn ${turn}` : "Demo placeholder",
      origin: "demo",
      originNote: "Placeholder from the demo mock. Connect the FastAPI pipeline for a real assessment.",
      decisionStatus: "insufficient",
      requirements: {
        stated: sentences,
        unknowns: ["Placeholder: the pipeline lists what the client did not state."],
      },
      questions: [
        { text: "Placeholder question 1: the pipeline asks what would change the method.", impact: "method" },
        { text: "Placeholder question 2: the pipeline asks what would change the setup.", impact: "setup" },
      ],
      recommendations: [],
      concept: { summary: "Placeholder: the pipeline proposes a probe and measurement concept.", citations: [] },
      spectralRange: { summary: "Placeholder: the pipeline states the relevant range in correct units.", citations: [] },
      risks: ["Placeholder: the pipeline lists the assumptions the recommendation rests on."],
      feasibility: {
        steps: ["Placeholder: samples, reference measurements, comparison."],
        decisionBasis: "Placeholder: the go / no-go basis agreed with the client.",
      },
      premiseChecks: [],
      sources: [],
    },
  };
}
