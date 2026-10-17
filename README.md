# SpectraSense AI — web front end

Next.js 15 (App Router, TypeScript, Tailwind v4). Front end for the AFS in-line spectroscopy assistant.

```bash
npm install
npm run dev        # http://localhost:3000
npm run build
```

## Pages

| Route | What it is |
| --- | --- |
| `/` | Landing: preloader, intro animation (52 frames in `public/frames`) beside the pitch, steps and principles |
| `/assess` | Chat workbench for a customer enquiry → report versions (`?example=H04` preloads an example enquiry) |
| `/how-it-works` | Lottie pipeline animation (`src/lib/lottie-pipeline.ts`) and scripted chat walkthroughs (`src/data/demo-conversations.ts`) |

The walkthroughs on `/how-it-works` are scripted, not pipeline output, and say so in the UI. Every quote in them was checked against the cited page of `kb/pages.json`.

## Connecting the pipeline

The UI only talks to `POST /api/assess` with `{ messages, scenarioId? }` and expects `{ reply, report, trace }` (`AssessRequest` / `AssessResponse` in `src/lib/report.ts`). The route resolves in this order:

1. **Live**: if `ASSESS_BACKEND_URL` is set, the request is forwarded there. The response is zod-validated; invalid responses fall through.
2. **Cached**: `outputs/<scenarioId>.json` written by the batch runner (D01–D08, H01–H06). Never edit these by hand.
3. **Reference**: organizer worked examples D01 and D02 (`src/data/reference-answers.ts`), badged `REFERENCE`.
4. Otherwise `503 pipeline_not_connected`. The UI shows that state instead of inventing an answer.

An edited scenario text is sent without `scenarioId`, so it never picks up a cached answer.

### Report contract (`src/lib/report.ts`)

Sections follow `AFS_Examples_and_Reference.docx` §3: `decisionStatus` (provisional / insufficient / out_of_scope), `requirements.stated` vs `requirements.unknowns`, ordered `questions` (with optional `impact`), `recommendations` (`role` + `methodIds` drive the spectral-band highlight), `concept` (analyzer / fiberLink / probe / location feed the setup sketch), `spectralRange`, `risks`, `feasibility.steps` + `decisionBasis`, `premiseChecks`, `sources`.

Every `Citation` carries `check`: `verified` | `visual_note` | `unverified` | `failed`. That is the output of the citation verifier (`verifyCitation` in the repo seed), rendered as a coloured chip. External sources (`EXT`) need `quote` and `url` (expert Q&A).

## Data provenance

- `src/data/scenarios.ts`: scenario text verbatim from the docx and `customer_scenarios_for_final_evaluation.txt`.
- `src/data/optics.ts`: method ranges (docx §5), S01 Table 1 (from the xlsx), fiber windows (S02 p.6, transcribed; check the figure).
- Fiber "coverage" is computed against **nominal** method ranges only. It is not a statement about a real instrument.
