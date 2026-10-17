# SpectraSense backend

FastAPI + LangGraph assessment pipeline. Structure follows the team architecture (and the
[8hr-MARATHON](https://github.com/d-hackmt/8hr-MARATHON) template it is based on).

```
POST /assess ─► safety gate ─► planner ─┬─► analyst ─► retriever ─► checker ─► responder ─► report
                (app/guardrails)        └─► conversational (answers from the last report, MemorySaver)
```

| Node | What it does | LLM? |
| --- | --- | --- |
| planner | assessment vs conversational turn, search queries | yes (small JSON) |
| analyst | stated facts (kept only if quoted from the client) vs unknowns, flags for the checks | yes |
| retriever | Qdrant vector search + BM25, fused, reranked with FlashRank | no |
| checker | deterministic premise checks: target named, fibre window vs method range, fluorescent target, source scope, calibration transfer, combination, certainty | no |
| responder | composes the report; then deterministic post-processing: computed checks replace the model's, decision status floored by failed checks, every quote verified on its page, unknown methods dropped | yes |

## Run

```bash
cd backend
uv venv --python 3.11 .venv && uv pip install --python .venv/bin/python -r requirements.txt
cp .env.example .env               # add OPENAI_API_KEY (+ OPENAI_FALLBACK_API_KEY, GEMINI_API_KEY for vectors)
.venv/bin/uvicorn app.main:app --reload --port 8000
```

Frontend: set `ASSESS_BACKEND_URL=http://localhost:8000/assess` in `frontend/.env.local`, then `npm run dev`.

`GET /health` shows what is configured (LLM route, embeddings, Qdrant mode, KB size, guardrails).

## Knowledge base

`processed_data/pages.json` (77 pages: S01–S06 + S01 Table 1 + 11 S02 slide transcriptions) and `chunks.json` (188 page-bounded chunks) are committed, so the API works without re-ingesting. To rebuild and index into Qdrant:

```bash
.venv/bin/python -m app.ingestion.processor --materials ~/Downloads/materials --wipe
```

PDF text comes from poppler's `pdftotext` when installed (better spacing for quote matching), else pypdf. `data/visual_notes.json` holds the team's transcriptions of S02 slide images; citations to them are labelled `visual_note`. The organizer docx (scenarios and worked answers) is excluded from retrieval.

## Batch outputs

```bash
.venv/bin/python -m scripts.run_batch          # D01–D08, H01–H06 → frontend/outputs/<ID>.json
```

## Degraded modes

| Missing | Behaviour |
| --- | --- |
| LLM key | `/assess` returns 503; the frontend shows "not connected" |
| `PORTKEY_API_KEY` | direct OpenAI calls: each model with the primary key, then the fallback key; gpt-4o → gpt-4o-mini |
| `OPENAI_FALLBACK_API_KEY` | only the primary key is used |
| `GROQ_FALLBACK_API_KEY` | no last-resort provider; with it, Groq gpt-oss-120b / 20b are tried after every OpenAI attempt fails |
| `GEMINI_API_KEY` | BM25 only (vector step skipped) |
| `QDRANT_CLUSTER_ENDPOINT` | embedded Qdrant in `backend/.qdrant` |
| FlashRank model download | fused BM25/vector order |
| LLM for the gate | rule-based gate (`engine: rules` in the trace) |

## Safety gate (app/guardrails)

From `feat/safety-gate` (Vedant), adapted to the team stack. Runs on the latest client message before the graph.

| Category | Effect |
| --- | --- |
| `off_topic`, `jailbreak`, `injection` | **block**: refusal reply + `out_of_scope` report, pipeline skipped |
| `approval_demand`, `immediate_config`, `research_as_proof` | **pass with a flag**: shown in the trace and fed to the premise checks (certainty, source scope). H04/H05/H06 are scored cases and need the full assessment. |

Engine: LLM classifier on the gateway's small tier (gpt-4o-mini; the 8hr-MARATHON template likewise uses a small model for its guard), with the deterministic rule gate as runtime fallback; rules only when no LLM is configured or `GUARD_MODE=rules`. Template interface kept: `initialize_rails()`, `guard(text) -> (fired, response)`; `check(text)` returns the full `GuardResult`. The architecture diagram's NeMo box is replaced by this gate (no NeMo dependency).

## Evals (evals/)

RAGAS-style metrics implemented in `evals/metrics.py` (no extra dependency), scored by a judge LLM on its own key, plus deterministic checks that cost nothing.

```bash
.venv/bin/python -m evals.run_evals                # all scenarios: live pipeline + judge
.venv/bin/python -m evals.run_evals D01 H04        # selected scenarios
.venv/bin/python -m evals.run_evals --no-judge     # deterministic metrics only
.venv/bin/python -m evals.run_evals --from-cache   # score frontend/outputs/<ID>.json (no context metrics)
```

| Metric | Measures | Judge? |
| --- | --- | --- |
| faithfulness | report claims supported by the retrieved pages | yes |
| answer_relevancy | the report addresses the client's enquiry | yes |
| context_precision | relevant retrieved pages, rank-weighted (average precision) | yes |
| context_recall | organiser reference statements found in the retrieved pages (D01, D02) | yes |
| answer_correctness | F1 of the report against the organiser reference (D01, D02) | yes |
| citation_validity | citations whose quote was found on the cited page | no |
| grounding | recommendations backed by a verified citation | no |
| clarification | unknowns listed and questions asked | no |
| feasibility | first experiment has steps and a decision basis | no |
| expectations | expected status, premise checks and terms per scenario (`evals/golden.json`) | no |

Judge: `JUDGE_OPENAI_API_KEY` (`JUDGE_MODEL`, default gpt-4o), else `JUDGE_GROQ` (gpt-oss-120b on Groq), so grading never rate-limits the live app; without either the judge uses the app gateway. `evals/golden.json` is read by the evals only, never by the pipeline. Results: `evals/results/latest.{json,md}` and `frontend/outputs/evals-latest.json`, shown on the frontend's **Evals** page.

## Tests

```bash
.venv/bin/python -m pytest -q
```

Citation verifier, premise checks on the evaluation enquiries, the safety gate (hard blocks, no scenario blocked, LLM fallback), and the full graph with a scripted LLM (an invented quote is marked `failed`, an over-confident status is lowered, an unquoted "fact" is dropped, follow-up questions use MemorySaver).
