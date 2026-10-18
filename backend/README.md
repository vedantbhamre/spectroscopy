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
| retriever | pages routed by the organisers' source guide (domain, methods, fibre topic), then BM25 (+ Qdrant vectors when configured), one chunk per page, 8 pages; recall of the organisers' useful pages 0.90 vs 0.35 for keyword search alone (`tests/test_retrieval.py`) | no |
| checker | deterministic premise checks: target named, fibre window vs method range, fluorescent target, source scope, calibration transfer, combination, certainty | no |
| responder | composes the report; then deterministic post-processing: computed checks replace the model's, decision status floored by failed checks, every quote verified on its page, unknown methods dropped | yes |

## Conversation handling and validators

Generic rules (no scenario IDs, no case wording): they use only extracted facts and the AFS sources. The LLM proposes; these decide.

| # | Rule | Where |
| --- | --- | --- |
| 1 | **Question ledger**: statuses `open`, `answered`, `answered_unknown`, `declined`, `moved_to_experiment`; one UI input per question; a closed question is never asked again (reworded counts); an unknown answer becomes a feasibility step and stays a key unknown | `services/ledger.py`, `Workbench.tsx` |
| 2 | **Facts from the whole transcript**, quote-checked against every customer turn and tagged with the turn | `nodes/analyst.py` |
| 3 | **Final-report mode** on an explicit request or the gate's `immediate_config`: no question block; open points → points to confirm; status provisional unless a check fails | `nodes/planner.py`, `finalise()` |
| 4 | **Customer-fact questions only**: no method / equipment choice, no purchases, no assistant decisions; ≤ 5 open, ranked method > setup > acceptance | `ledger.asks_assistant_decision`, `merge_new` |
| 5 | **Number validator**: every number in the transcript or on a cited page (same unit); otherwise "[to be agreed with the customer]" | `services/numbers.py` |
| 6 | **One pipeline for technical advice**; the conversational branch only explains the existing report (numbers validated) | `nodes/planner.py`, `conversational_node` |
| 7 | **Claim validator**: each recommendation sentence must be covered by the passage of a verified citation; otherwise it moves to assumptions (a recommendation without any verified citation moves entirely) | `services/validators.py` |
| 8 | **ACCESS_POINTS**: probes ≤ free ports, else a combined probe (only if the sources show one for the customer's application), sequential measurement or an offline rig | `premises.access_check` |
| 9 | **Certainty / combination / cost**: provisional while anything decisive is open; combination only if one method is shown insufficient; cheapest sufficient method first (S01 Table 1 cost column) | `premises.py`, `knowledge/table1.py` |
| 10 | **TARGET_QUALIFIER**: a qualified target (viable, free, dissolved, …) the cited passages do not distinguish → stated limitation, risk, and a reference method for the qualified quantity | `premises.target_qualifier_check` |
| 11 | **Owned equipment** must be assessed (recommendation or feasibility plan) before purchases | `premises.owned_equipment_check` |
| 12 | **GEOMETRY_VS_OPTICS** from the full transcript: clear → transmission / transflection; opaque, turbid, high-OD, powders → ATR / reflection; clear→opaque → a single transmission path may saturate (S01 p.16, p.18) | `premises.geometry_check` |
| 13 | **Application tags** on retrieved passages and citations; another application → "transfer assumption" on the citation and in the assumptions | `knowledge/applications.py`, `validators.label_transfers` |
| 14 | **Required sections**: missing ones are rejected and repaired once | `validators.missing_sections`, `responder_node` |
| 15 | **One numbering source**: leading numbers stripped from question text | `ledger.clean`, `questionText()` |

Citations: a quote is verified only if it is on the cited page; a near-verbatim quote (≥ 80 % of its words in order) is replaced by the exact page passage; an S01 Table 1 row is checked against the organisers' transcription of the table.

Acceptance properties for any conversation: `evals/acceptance.py` (tests in `tests/test_conversation.py`). Live batch with a generic follow-up turn and per-case validation report: `.venv/bin/python -m scripts.run_batch` → `evals/results/batch-latest.md`. Live multi-turn retest: `.venv/bin/python -m scripts.retest_feed_frame`.

## Run

```bash
cd backend
uv venv --python 3.11 .venv && uv pip install --python .venv/bin/python -r requirements.txt
cp .env.example .env               # LLM_PROVIDER=groq|openai + its keys (GEMINI_API_KEY for vectors)
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
| `PORTKEY_API_KEY` | direct calls to `LLM_PROVIDER` (groq: gpt-oss-120b → 20b; openai: gpt-4o → gpt-4o-mini), each model with the primary key, then the fallback key |
| fallback key | only the primary key is used |
| `LLM_FALLBACK_PROVIDER` | the other provider is never called (no surprise spend); set it to `openai` or `groq` to try it after every attempt fails |
| `GEMINI_API_KEY` | BM25 only (vector step skipped) |
| `QDRANT_CLUSTER_ENDPOINT` | embedded Qdrant in `backend/.qdrant` |
| `RERANK=flashrank` unset (default) | no reranking: FlashRank measured no gain and dropped correct pages |
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
.venv/bin/python -m evals.run_evals                # all scenarios: live pipeline + judge (~$0.20 on OpenAI)
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

Judge on its own key, on the active provider, so grading never rate-limits the live app: `JUDGE_GROQ` (`JUDGE_GROQ_MODEL`) with Groq; `JUDGE_OPENAI_API_KEY` (`JUDGE_MODEL`, default gpt-4o-mini) with OpenAI. Without one the judge uses the app gateway.

Evals never run on their own: only this command or the **Run evals** button on the frontend's Evals page (`POST /evals/run`, progress on `GET /evals/status`). The button asks for confirmation with a cost estimate; the backend allows one run at a time and one run per `EVAL_COOLDOWN_MIN` minutes (default 30, read from the last result on disk). Tests never start a run. `evals/golden.json` is read by the evals only, never by the pipeline. Results: `evals/results/latest.{json,md}` and `frontend/outputs/evals-latest.json`, shown on the frontend's **Evals** page.

## Tests

```bash
.venv/bin/python -m pytest -q
```

Citation verifier, premise checks on the evaluation enquiries, the safety gate (hard blocks, no scenario blocked, LLM fallback), and the full graph with a scripted LLM (an invented quote is marked `failed`, an over-confident status is lowered, an unquoted "fact" is dropped, follow-up questions use MemorySaver).
