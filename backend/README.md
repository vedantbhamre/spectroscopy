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
cp .env.example .env               # add GROQ_API_KEY or PORTKEY_API_KEY (+ GEMINI_API_KEY for vectors)
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
| `PORTKEY_API_KEY` | direct Groq calls, same 70B → 8B fallback |
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

Engine: LLM classifier on the gateway's small tier (Groq Llama 3.1 8B via Portkey, as in the 8hr-MARATHON template), with the deterministic rule gate as runtime fallback; rules only when no LLM is configured or `GUARD_MODE=rules`. Template interface kept: `initialize_rails()`, `guard(text) -> (fired, response)`; `check(text)` returns the full `GuardResult`. The architecture diagram's NeMo box is replaced by this gate (no NeMo dependency).

## Tests

```bash
.venv/bin/python -m pytest -q
```

Citation verifier, premise checks on the evaluation enquiries, the safety gate (hard blocks, no scenario blocked, LLM fallback), and the full graph with a scripted LLM (an invented quote is marked `failed`, an over-confident status is lowered, an unquoted "fact" is dropped, follow-up questions use MemorySaver).
