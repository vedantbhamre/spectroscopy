# Judge score matrix (live)

Official AFS criteria `[BRIEF]` (judging slide, received 18 Oct): **technical quality, use of AFS knowledge, feasibility, uncertainty,
explainability, prototype**. Weights not published → equal. Mapping of the rows below: technical quality #5 #6; AFS knowledge #3;
feasibility #6; uncertainty #1 #4; explainability #2 #3 #10; prototype #7 #8 #9. Scores are 1–5 team estimates.
Latest per-case check: docs/08-stress-test.md (H06: 19.5/30, gap = no direct answer).

| # | Criterion (evidence) | Measurable requirement | Evidence in product | Demo moment | Target | Current |
|---|---|---|---|---|---|---|
| 1 | Facts vs unknowns `[BRIEF]` "Anything not stated is unknown: ask about it or state it as an explicit assumption, never treat it as fact." | Every stated fact quoted from the customer; unknowns listed, not guessed | Quote-checked facts tagged with their turn; invented facts dropped (trace "unquoted dropped") | Requirements panel: stated vs "Unknown, not assumed" | 5 | 4.5 |
| 2 | Clarification questions `[BRIEF]` answer structure; `[USER]` review: no repeats | 3–5 decisive questions, never re-asked, customer facts only | Question ledger, impact ranking, purchase / own-decision filter; batch: 0 repeated questions | Answer one box, choose "Don't know" on another, see the report revise | 5 | 4 |
| 3 | Cited recommendations `[BRIEF]` "For each important claim: source and page" | Each recommendation sentence backed by a verified page quote | Citation verifier (quote on page, snapping near-verbatim quotes), claim validator, readable sources with popover | Click a source chip: quote + document + page | 5 | 4 |
| 4 | Caution and honesty `[BRIEF]` "Some enquiries ask for more certainty than the facts allow. A good answer notices this and says so." / "Do not invent … performance figures" | Status floors from premise checks; no invented numbers | 12 premise checks (fibre window, geometry, qualifier, access points, source scope…); number validator; H04–H06 expectations 1.0 | H04: silica fibre cannot carry MIR → "Insufficient information" | 5 | 4.5 |
| 5 | Measurement concept and setup `[BRIEF]` Q&A "a sketch of the setup … Simple messages beat complicated ones" | Analyzer → fibre → probe → process point, gaps visible | Setup sketch with "Not specified" gaps; spectral band chart | Report: measurement concept section | 5 | 4 |
| 6 | First feasibility study `[BRIEF]` Q&A "Clear ideas and rationale are enough" | Steps + decision basis; unknowns become experiment steps | Feasibility section; unknown answers move into the plan; feasibility metric 1.0 | "First feasibility experiment" + decision basis | 5 | 4 |
| 7 | Live runs on evaluation cases and the jury's own enquiry `[BRIEF]` Q&A "The jury may ask you to run a shot on your own inquiry." | Any enquiry → report in < 60 s, reliably | Live D01 5.5 s (this session); cached outputs as fallback | Jury types its own enquiry | 5 | 3 (one provider org, daily token cap, no hosted URL) |
| 8 | Usability for an expert `[INFERENCE]` the user is an AFS expert reviewing a draft | First-time user understands without help | Carbon design, readable sources, first-time guide, How it works with a report legend, WCAG AA contrast | Open Assess, follow the checklist | 5 | 4.5 |
| 9 | Evidence that it works `[INFERENCE]` judges reward measured quality | Repeatable evaluation with honest numbers | Evals page (RAGAS-style + deterministic), 106 tests, acceptance properties, batch report | Evals page: scores with icons | 5 | 4 (results stale/mixed until the 10:00 re-run) |
| 10 | Direct answer `[INFERENCE]` from "explainability" + H06 review | The customer's literal question answered in the first lines (yes / no / not yet), cited | none yet | Report opens with the answer | 5 | 2 |
| | **Total** | | | | **50** | **38.5** |

Biggest gains still available: #7 (second key + hosting decision + rehearsal), #9 (fresh full batch on the large model), #2–#3 (large model gives 90–100 % citation pass vs 40–60 % on the small fallback).
