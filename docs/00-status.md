# SpectraSense — status (Sun 18 Oct 2026, 03:35 CEST)

Evaluated with the hackathon-copilot process. Every "verified" item below was checked in this session; scores are rough team estimates for prioritising, not measurements.

## Scoreboard

```
Phase:                 8–10 (stress-test, pitch, submission)
Time remaining:        ~20 h to the 23:59 deadline; ~6.5 h to the 10:00 feature freeze
MVP completion:        ~85 %  (demo-path steps verified working / total, see below)
Critical blockers:     1. 108 files uncommitted + 3 commits not pushed (loss risk; teammates cannot see the work)
                       2. One LLM provider org, 200K tokens/day: a full eval batch or a long jury session can exhaust it
                       3. Published eval results are stale/mixed (Evals page: 17 Oct gpt-4o run; batch: 10/14 on the small model)
                       4. No deployed demo URL (whether one is required is unknown: the brief is not on disk)
Judge score estimate:  36.5 / 45  (docs/01-judge-matrix.md)
Next highest-value task: commit and push now; after 10:00 add the second-org Groq key and run the full batch on the large model
```

## Retrieval fix (measured, no LLM tokens)

Recall of the organisers' "useful sources" (D01–D08) reaching the composer: **0.35 → 0.90**
(keyword search + TinyBERT rerank → source-guide routing + stop-word BM25 + one chunk per page, 8 pages).
Guarded by `backend/tests/test_retrieval.py`.
Local semantic search added (BGE-base via fastembed, CPU, no key): on enquiries worded without routing keywords recall **0.64 → 0.93**,
development set unchanged at 0.90 (`backend/tests/test_semantic_retrieval.py`). Compared BGE-small / BGE-base / mxbai-large (equal recall;
BGE-base chosen for size/latency), arctic-m (0.43) and nomic (too heavy for CPU). Remaining miss: "malignant vs benign during an operation" does not reach S03 p.1. FlashRank rerank is now opt-in (`RERANK=flashrank`): it measured no gain.
Answers have not been re-run with the new retrieval yet (needs tokens): see docs/11-next-run-plan.md step 2.

## Demo path — verified now

| Step | Evidence (this session) | Status |
|---|---|---|
| Enquiry → cited first assessment, live | `POST /api/assess` D01: 5.5 s, *provisional*, NIR primary, 4/5 quotes found on the cited page, unsupported sentence and numbers moved/replaced by the validators | ✅ |
| Answers → revised report, no repeated questions | 106 backend tests incl. scripted multi-turn acceptance tests; live 2-turn batch on 10 cases: 0 repeated questions | ✅ |
| "Final report" → no question block, open points to confirm | acceptance test `test_powder_conversation…` + gate-flag test | ✅ |
| Citation popover readable, on top | real click via Chrome DevTools on *How it works* | ✅ |
| Evals page with scores | renders; data is the 17 Oct run | ⚠ stale data |
| Production build | `next build` passes (12 routes) | ✅ |
| Copy as text / PDF export after the redesign | not clicked this session | ❓ |

## Fallbacks that exist

- **No backend / LLM down:** the frontend serves cached batch outputs for the unedited example enquiries (`frontend/outputs/<ID>.json`, labelled "Batch run"), never an invented answer [code: `src/app/api/assess/route.ts`].
- **LLM gate down:** deterministic rule gate.
- **Rate limit:** the gateway waits for the provider's retry time once, then falls back to the second key (`GROQ_FALLBACK_API_KEY`, currently empty) and the small model.

## Plan (in order)

1. **Now (10 min):** commit and push today's work to `main`.
2. **10:00:** put the second-account Groq key in `GROQ_FALLBACK_API_KEY`; run `python -m scripts.run_batch` (all 14 cases, large model) → refreshes `frontend/outputs/*.json`, `evals/results/batch-latest.md`. Then one judge eval run from the Evals page (or `python -m evals.run_evals`) so the Evals page shows today's model. Rebuild the frontend afterwards (home-page numbers are prerendered).
3. **Decide hosting** (see open questions). If a URL is needed: frontend on Vercel, backend on a small container host; test with an unseen enquiry.
4. **Submission pack:** README (problem, screenshots, setup, stack, team, limitations), licence/attribution, architecture diagram matching the code (Groq + rule/LLM gate, no NeMo), docs/10-submission-checklist.md.
5. **Pitch:** 3-minute script along the demo path (H04 is the strongest live moment: the premise check stops an impossible silica link), judge Q&A answers, backup screen recording.

## Open questions (blocking)

- What exactly does the brief require for submission: repo only, hosted URL, video, slides? Where are the evaluation criteria and their weights?
- Will the jury run its own enquiry on our machine (local) or on a hosted URL? (Q&A: "The jury may ask you to run a shot on your own inquiry.")
- Is an emergency fallback to OpenAI acceptable on demo day only, if both Groq keys hit their daily limit? (Currently disabled by choice.)
