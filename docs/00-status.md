# SpectraSense: final evaluation (Sun 18 Oct 2026, 20:30 CEST)

Evaluated with the hackathon-copilot process (Phase 10 submission gate + Phase 9 pitch). Every ✅ below was checked in this
session; scores are 1–5 team estimates for prioritising, not measurements.

## Scoreboard

```
Phase:                 10 (submission gate) + 9 (pitch)
Time remaining:        ~3.5 h to 23:59  → feature freeze now; scope-cut protocol triggers at 22:00
MVP completion:        100 % of the demo path verified (see below)
Critical blockers:     1. Groq daily limit reached on the large model (both keys are in the same Groq account:
                          199,147 / 200,000 at 20:20); live runs fall back to gpt-oss-20b until the window frees up.
                          A key from a DIFFERENT Groq account in GROQ_FALLBACK_API_KEY removes this for the jury.
                       2. Evals page shows the 17 Oct scores; one "Run evals" press refreshes them (needs quota).
Judge score estimate:  26.5 / 30 on the six official criteria (docs/01-judge-matrix.md)
Next highest-value task: second-account Groq key → re-run H02–H06 + Run evals; then pitch rehearsal and backup recording
```

## Demo path: verified now

| Step | Evidence (this session) | Status |
|---|---|---|
| Enquiry → cited report, live | H01 live 20:16 on gpt-oss-120b: provisional, 14/14 quotes verified, all expectations met; new enquiry "stop the Karl Fischer titration, NIR needs no calibration?" → calibration premise flagged, answer "No…", 9/9 quotes verified | ✅ |
| Premise checks on the trap cases | H04 silica fibre fails for MIR + link-length flag; H06 lab study → "beyond what the sources support"; H03 fluorescence without a target fails; H05 undefined target | ✅ |
| Follow-up answers, no repeated questions | offline acceptance tests (182 tests); batch: 0 repeated questions | ✅ |
| Assess page scrolling | progress bar under the header, page no longer stretches (fix/assess-scroll-ui) | ✅ |
| Evals page | renders; Run evals at the top; scores from 17 Oct | ⚠ stale data |
| Production build | `next build` passes, 12 routes | ✅ |
| No-key fallback | stored live-pipeline answers for the 14 examples, badged "Batch run" | ✅ |

## Answer quality (measured, `python -m evals.coverage`, no tokens)

| | Value |
|---|---|
| Retrieval recall of the organisers' useful pages (D01–D08) | 0.97 (was 0.35 at the start) |
| Useful pages cited in the stored reports | 0.72 |
| Key points of the expected answers (D01, D02, H04, H06) | 1.00 |
| Citations found on the cited page (large model) | 100 % in every stored case |
| Golden expectations (14 cases) | 1.0 in every case |

## Stored answers

H01 was re-run tonight with every rule (20:16, large model). H02–H06 are the 15:12–15:20 large-model runs: the 20:16 batch
fell back to the small model for them (daily limit), so those weaker runs were not kept. Re-run H02–H06 when a key from
another Groq account is available: `python -m scripts.run_batch --single H02 H03 H04 H05 H06 && python -m scripts.export_answers`.

## Fallbacks that exist

- **LLM limit reached:** gateway waits once, then tries the fallback key and the small model; the frontend serves the stored
  answers for the examples. The small model is noticeably weaker (shorter reports, fewer citations).
- **No backend:** stored answers for the 14 examples; a new enquiry says "not connected", never invents an answer.
- **No embeddings:** routing + keyword search.
