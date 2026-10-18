# Plan for the next run (when LLM tokens are refreshed)

Everything below is ready to run; nothing needs code changes. Token figures are estimates `[ESTIMATE]`: roughly 9–10K tokens per
assessment on `openai/gpt-oss-120b` (enquiry + retrieval excerpts + composed report), more when a repair pass runs.
Groq's free tier allows **200K tokens per day per model per account (organisation)** — keys from the same account share it.

## 0. Before anything (no tokens)

```bash
cd spectroscopy && git pull                      # fast-forward, clean tree expected
cd backend && .venv/bin/python -m pytest -q      # expect 122 passed
cd ../frontend && npx tsc --noEmit && npx next lint
```

## 1. Keys (no tokens)

In `backend/.env` (never committed):

```
LLM_PROVIDER=groq
GROQ_API_KEY=<key from account A>
GROQ_FALLBACK_API_KEY=<key from account B>     # different Groq account = its own 200K/day
JUDGE_GROQ=<key from account C, if available>    # judge on its own quota
```

Check both keys have quota (one ~3K-token probe each):

```bash
cd backend && .venv/bin/python - <<'EOF'
from openai import OpenAI
from app.config import settings
for n in ("GROQ_API_KEY", "GROQ_FALLBACK_API_KEY", "JUDGE_GROQ"):
    k = getattr(settings, n)
    if not k: print(n, "not set"); continue
    try:
        OpenAI(api_key=k, base_url=settings.GROQ_BASE_URL, max_retries=0).chat.completions.create(
            model="openai/gpt-oss-120b", messages=[{"role": "user", "content": "word " * 3000 + " OK"}], max_completion_tokens=5)
        print(n, "OK")
    except Exception as e:
        print(n, "LIMITED", str(e)[:160])
EOF
```

Restart the backend after changing `.env` (`uvicorn app.main:app --reload --port 8000`).

## 2. Full batch on the large model (~250K tokens: needs keys A + B)

```bash
cd backend && .venv/bin/python -m scripts.run_batch
```

- Turn 1 for all 14 cases first (these become the cached demo outputs in `frontend/outputs/<ID>.json`), then a generic follow-up turn.
- Report: `backend/evals/results/batch-latest.md` — per case: citation pass rate, number-validator hits, repeated questions,
  missing sections, the model that composed each turn, tokens used.
- **Pass bar:** every turn composed by `gpt-oss-120b` (not the small fallback), 0 repeated questions, 0 missing sections,
  citation pass ≥ 80 %, golden expectations ≥ 0.95. Re-run single cases with `python -m scripts.run_batch H03 H04`.

## 3. Evaluation numbers for the Evals page

Cheapest first:

```bash
# free: deterministic metrics on the fresh cached outputs (no LLM)
.venv/bin/python -m evals.run_evals --from-cache --no-judge
# full: live pipeline + judge (~14 assessments + ~46 judge calls; use JUDGE_GROQ on its own account)
.venv/bin/python -m evals.run_evals
```

Or press **Run evals** on the Evals page (one run per 30 min). Afterwards rebuild the frontend if serving a production build:
the home page's evidence numbers are prerendered at build time.

## 3b. H04 review fixes, live (~10K tokens)

```bash
.venv/bin/python -m scripts.run_batch --single H04
```

Expect in `frontend/outputs/H04.json`: premise check `mir_link_length` (flag, cites Process Control slides p.7, p.9, p.13),
a feasibility step to measure transmission over the link length or move the analyzer close to the line, the silica range
written as 0.35–2.4 µm (not "[to be agreed …]"), one "Process Control slides p.6 ×6" chip instead of six, and the setup
sketch filled (probe, fibre link, analyzer, process point).

## 4. Live multi-turn retest (~4 assessments, ~40K tokens)

```bash
.venv/bin/python -m scripts.retest_feed_frame    # expects all checklist items PASS
```

## 5. Commit the refreshed results

```bash
cd spectroscopy && git add frontend/outputs backend/evals/results && git commit -m "Refresh batch outputs and eval results (gpt-oss-120b)" && git push
```

## 6. Demo-day reserve

Keep at least **~60K tokens** (6 assessments) unused on one key for the jury's own enquiries. If both keys run out during the
session, the frontend still serves the cached outputs for the example enquiries (labelled "Batch run"). An OpenAI fallback
(`LLM_FALLBACK_PROVIDER=openai`) exists but is off by choice; enable it only with the team's agreement.

## Still open (no tokens needed)

- What the brief requires for submission (repo / hosted URL / video / slides) and the official judging criteria → update
  `docs/01-judge-matrix.md` and `docs/10-submission-checklist.md`.
- README with problem, screenshots, team and limitations; LICENSE and attribution; architecture diagram matching the code.
- 3-minute pitch along the demo path (H04 premise-check moment) and a backup screen recording.
