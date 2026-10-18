# SpectraSense

**Cited first assessments for in-line spectroscopy.** SpectraSense turns a customer enquiry ("can we measure X in our process line?") into a structured first assessment: what the customer actually stated, what is still unknown, which spectroscopic method (NIR, Raman, MIR/ATR, UV-Vis, fluorescence) is worth testing, how to set it up, and a first feasibility experiment. Every recommendation is tied to a quoted passage on a specific page of the AFS (Art Fiber Systems) source material, and the system checks those quotes instead of trusting the language model.

It was built for the AFS in-line spectroscopy challenge.

| | |
| --- | --- |
| **Frontend** | Next.js 15 (App Router, TypeScript, Tailwind v4), `frontend/` |
| **Backend** | FastAPI + LangGraph assessment pipeline, `backend/` |
| **Retrieval** | BM25 + optional Qdrant vector search, fused and reranked with FlashRank |
| **LLM** | Groq (`gpt-oss-120b`) or OpenAI (`gpt-4o`), your choice via `.env` |

---

## Contents

1. [What it does](#what-it-does)
2. [Run it on your machine](#run-it-on-your-machine)
   - [Prerequisites](#prerequisites)
   - [Option A: frontend only, no API key](#option-a-frontend-only-no-api-key-2-minutes)
   - [Option B: full live pipeline](#option-b-full-live-pipeline-with-an-llm-key)
3. [What to try](#what-to-try)
4. [Architecture](#architecture)
5. [Tests and evaluations](#tests-and-evaluations)
6. [Project structure](#project-structure)
7. [Configuration reference](#configuration-reference)
8. [Troubleshooting](#troubleshooting)
9. [Limitations](#limitations)
10. [Acknowledgements](#acknowledgements)

---

## What it does

1. **Describe the enquiry** in the customer's own words.
2. **Answer up to five questions** that could change the method or setup. "Don't know" and "Skip" are valid answers, and a question that was answered is never asked again.
3. **Get a versioned report** with: stated facts vs unknowns, recommended methods with verified source citations, measurement concept (analyzer → fibre → probe → process point), spectral range, risks, a first feasibility experiment with a decision basis, and the premise checks that were run.
4. **Press "Final report"** at any time to stop the questions; open points become assumptions to confirm.

Things that make it different from a plain chatbot:

- **Facts vs unknowns.** A "stated fact" is kept only if it is quoted from the customer. Anything else stays an unknown.
- **Verified citations.** Each quote is checked against the cited page; invented quotes are marked `failed`, and a recommendation sentence without a verified citation is moved to the assumptions.
- **Premise checks (deterministic, no LLM).** For example, a customer who wants mid-IR through an existing silica fibre is told that this fibre cannot carry that range (scenario H04). Over-confident requests are held at "provisional" or "insufficient information".
- **Safety gate.** Off-topic, jailbreak and prompt-injection messages are blocked before the pipeline runs.
- **Number validator.** A number appears in the report only if it is in the conversation or on a cited page.

---

## Run it on your machine

### Prerequisites

| Tool | Version | Needed for |
| --- | --- | --- |
| Node.js + npm | 20 or newer (tested on 22) | frontend (both options) |
| Python | 3.11 | backend (option B) |
| [`uv`](https://docs.astral.sh/uv/) | any recent | recommended Python installer (a plain `venv` + `pip` also works, shown below) |
| A Groq **or** OpenAI API key | | live assessments (option B) |
| `pdftotext` (poppler) | optional | only when re-ingesting PDFs; not needed to run |

Clone the repository first:

```bash
git clone https://github.com/yashwanth-1341/spectroscopy.git
cd spectroscopy
```

### Option A: frontend only, no API key (2 minutes)

This lets you see the whole interface and the stored results for the 14 example enquiries without any key or backend.

```bash
cd frontend
npm install
npm run dev
```

Open <http://localhost:3000>, go to **Assess**, pick an example enquiry (or open <http://localhost:3000/assess?example=H04>) and send it. With no backend configured, the example is answered from the stored batch results in `frontend/outputs/` and the report is badged **Batch run**.

In this mode, writing your own enquiry or editing an example returns "No assessment service is connected" by design: the app never invents an answer. For that you need Option B.

### Option B: full live pipeline (with an LLM key)

Run the backend and the frontend in two terminals.

**1. Get a key.** Either:

- **Groq** (free tier, the default): create a key at <https://console.groq.com>.
- **OpenAI**: create a key at <https://platform.openai.com/api-keys>.

**2. Start the backend** (terminal 1, port 8000):

```bash
cd backend

# create the environment and install dependencies
uv venv --python 3.11 .venv
uv pip install --python .venv/bin/python -r requirements.txt
# no uv? use:  python3.11 -m venv .venv && .venv/bin/pip install -r requirements.txt

# configure
cp .env.example .env
```

Open `backend/.env` and set **one** provider. Everything else can stay as it is.

```ini
# Groq (default)
LLM_PROVIDER=groq
GROQ_API_KEY=your-groq-key

# or OpenAI
# LLM_PROVIDER=openai
# OPENAI_API_KEY=your-openai-key
```

Then start the server:

```bash
.venv/bin/uvicorn app.main:app --reload --port 8000
```

> **Windows:** use `.venv\Scripts\python.exe` and `.venv\Scripts\uvicorn.exe` instead of `.venv/bin/...`, and `copy .env.example .env`.

Check that it is up: <http://localhost:8000/health> should show your provider under `"llm"`, `"kb_chunks": 188` and the model route. If `"llm"` is `null`, the key was not picked up (see [Troubleshooting](#troubleshooting)).

**3. Start the frontend** (terminal 2, port 3000):

```bash
cd frontend
npm install
echo 'ASSESS_BACKEND_URL=http://localhost:8000/assess' > .env.local     # Windows PowerShell: Set-Content .env.local 'ASSESS_BACKEND_URL=http://localhost:8000/assess'
npm run dev
```

Open <http://localhost:3000/assess>. Enquiries are now answered live by the pipeline (typically 5 to 30 seconds), including enquiries you write yourself.

> The first live assessment may take a little longer: the FlashRank reranker downloads a small local model on first use. If it cannot (offline), retrieval falls back to the BM25 order and everything still works.

For a production build instead of the dev server: `npm run build && npm start`.

---

## What to try

The 14 example enquiries are built in (Assess page, or `/assess?example=<ID>`). Two good ones for a first run:

| Example | What to look for |
| --- | --- |
| **D01**: blend potency in a tablet press feed frame | A *provisional* assessment with NIR as the primary method, cited sources, up to five questions, and a feasibility plan. Answer one question, mark another "Don't know", and watch the report revise without repeating questions. |
| **H04**: reuse of a silica fibre link for petroleum MIR ATR | The premise check fails: a silica fibre cannot carry the mid-IR range. The status becomes **Insufficient information** and the report explains why. |

Other things worth a click:

- **Citation chips** open the quoted passage with document and page, and show whether it was `verified`, matched a `visual_note`, `unverified` or `failed`.
- **Final report** button: no question block, open points listed as assumptions.
- **Copy as text / PDF** export of a report.
- **Compare with organiser example** (D01, D02) next to the reference answer.
- **How it works** page: scripted walkthroughs and a legend for reading the report (these walkthroughs are scripted, not live output, and say so).
- **Evals** page: stored evaluation scores. (The *Run evals* button there calls the LLM and costs tokens; it asks for confirmation first.)
- Try an off-topic or prompt-injection message, which is stopped by the safety gate.
- Write your **own enquiry**. Missing details are fine; nothing you leave out is assumed.

| Examples | Meaning |
| --- | --- |
| D01 to D08 | Typical enquiries: tablet blending, dairy, bioprocess, fermentation, petroleum, polymer extrusion, tissue |
| H01 to H06 | Harder cases with a trap: new formulation after an NIR pilot, a requested instrument that cannot measure the target, a silica link for MIR, an undefined contaminant, a lab study requested as clinical proof |

---

## Architecture

```
POST /assess ─► safety gate ─► planner ─┬─► analyst ─► retriever ─► checker ─► responder ─► report
                (app/guardrails)        └─► conversational (answers from the last report, MemorySaver)
```

| Node | What it does | LLM? |
| --- | --- | --- |
| safety gate | blocks off-topic, jailbreak and injection messages; flags over-confident requests | LLM classifier with a rule-based fallback |
| planner | assessment turn vs follow-up question, search queries | yes |
| analyst | stated facts (kept only if quoted from the customer) vs unknowns | yes |
| retriever | BM25 + optional Qdrant vector search, fused, reranked with FlashRank | no |
| checker | deterministic premise checks: target named, fibre window vs method range, geometry vs optics, source scope, calibration transfer, certainty, owned equipment | no |
| responder | composes the report, then deterministic post-processing: verifies every quote on its page, validates numbers, lowers the decision status if a check fails | yes |

The LLM proposes; the deterministic validators decide. The full list of validation rules is in [`backend/README.md`](backend/README.md).

The frontend talks only to `POST /api/assess`, which resolves in this order: live backend (`ASSESS_BACKEND_URL`) → stored batch result for an unedited example → `503` ("not connected"). It never fabricates an answer.

---

## Tests and evaluations

**Backend tests** need no API key and take a few seconds:

```bash
cd backend
.venv/bin/python -m pytest -q          # 106 tests
```

They cover the citation verifier, premise checks on the evaluation enquiries, the safety gate, and the full graph with a scripted LLM (an invented quote is marked `failed`, an over-confident status is lowered, unquoted "facts" are dropped, follow-ups reuse memory).

**Frontend checks:**

```bash
cd frontend
npx tsc --noEmit
npm run lint
npm run build
```

**Quality evaluation (optional, uses LLM tokens):**

```bash
cd backend
.venv/bin/python -m evals.run_evals --from-cache --no-judge   # free: deterministic metrics on stored outputs
.venv/bin/python -m evals.run_evals                           # live pipeline + LLM judge on all 14 scenarios
.venv/bin/python -m scripts.run_batch H04                     # regenerate one stored example (frontend/outputs/H04.json)
```

Metrics are RAGAS-style (faithfulness, answer relevancy, context precision and recall, answer correctness) plus deterministic checks (citation validity, grounding, clarification, feasibility, expected status per scenario). Latest results are in `backend/evals/results/latest.md` and `batch-latest.md`, and are shown on the frontend **Evals** page.

---

## Project structure

```
spectroscopy/
├── backend/
│   ├── app/
│   │   ├── main.py            FastAPI app: /assess, /query, /health, /graph, /evals/*
│   │   ├── agents/            LangGraph pipeline (planner, analyst, retriever, checker, responder)
│   │   ├── guardrails/        safety gate (LLM + rule-based)
│   │   ├── services/          retrieval, citations, number and claim validators, premise checks, question ledger
│   │   ├── knowledge/         method ranges, S01 Table 1, application tags
│   │   ├── gateway/           LLM client (Groq / OpenAI, keys and model fallbacks)
│   │   └── ingestion/         PDF/DOCX/PPTX loaders and chunking
│   ├── processed_data/        pages.json, chunks.json: the knowledge base (committed, no re-ingest needed)
│   ├── data/                  example scenarios, transcriptions of slide images
│   ├── evals/                 metrics, judge, golden expectations, results
│   ├── scripts/               batch runner, multi-turn retest
│   ├── tests/                 106 tests
│   └── .env.example           configuration template
├── frontend/
│   ├── src/app/               pages (/, /assess, /how-it-works, /evals) and API routes
│   ├── src/components/        workbench, report view, citation chips, setup sketch
│   ├── src/data/              example scenarios, reference answers
│   └── outputs/               stored batch results for the 14 examples
└── docs/                      status, judge matrix, submission checklist
```

---

## Configuration reference

Backend settings live in `backend/.env` (copy of `.env.example`). Restart the backend after changing it. Only the LLM key is required.

| Variable | Default | Purpose |
| --- | --- | --- |
| `LLM_PROVIDER` | `groq` in the example file | `groq` or `openai` |
| `GROQ_API_KEY` / `OPENAI_API_KEY` | none | **Required**: the key for the chosen provider |
| `GROQ_MODEL` / `GROQ_SMALL_MODEL` | `openai/gpt-oss-120b` / `openai/gpt-oss-20b` | assessment model / fallback and gate model |
| `OPENAI_MODEL` / `OPENAI_FALLBACK_MODEL` | `gpt-4o` / `gpt-4o-mini` | same, for OpenAI |
| `*_FALLBACK_API_KEY` | none | optional second key used when the first hits a rate limit |
| `GEMINI_API_KEY` | none | optional embeddings for the vector search step; leave empty to use BM25 + reranking only |
| `QDRANT_CLUSTER_ENDPOINT`, `QDRANT_API_KEY` | none | optional Qdrant Cloud; empty means embedded local Qdrant |
| `GUARD_MODE` | unset | set to `rules` to run the safety gate without an LLM |
| `FRONTEND_ORIGIN` | `http://localhost:3000` | origin allowed by CORS; change it if the frontend runs elsewhere |
| `LOGFIRE_TOKEN`, `LANGSMITH_*`, `PORTKEY_API_KEY`, `JUDGE_*` | none | optional observability, gateway and eval-judge settings |

Frontend settings live in `frontend/.env.local` (restart `npm run dev` after changing it):

| Variable | Purpose |
| --- | --- |
| `ASSESS_BACKEND_URL` | backend assess URL, e.g. `http://localhost:8000/assess`. Unset = stored examples only. |
| `EVALS_BACKEND_URL` | optional; defaults to the same host as `ASSESS_BACKEND_URL` |
| `NEXT_PUBLIC_SITE_URL` | optional; only for a deployed site (absolute canonical and social URLs) |

Behaviour when optional pieces are missing:

| Missing | Result |
| --- | --- |
| LLM key | `/assess` returns 503; the frontend serves the stored result for unedited examples, otherwise says "not connected" |
| `GEMINI_API_KEY` | vector step skipped, BM25 only |
| Qdrant endpoint | embedded local Qdrant in `backend/.qdrant` |
| FlashRank model download | fused BM25/vector order |
| LLM for the gate | rule-based gate (shown as `engine: rules` in the trace) |

---

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| `/health` shows `"llm": null` | The key is missing or in the wrong place. It must be in `backend/.env` (not `.env.example`), with no quotes or spaces around the value. Restart the backend. |
| Assess page says "No assessment service is connected" | `ASSESS_BACKEND_URL` is not set. Create `frontend/.env.local` as shown above and restart `npm run dev`. |
| "The assessment service did not return a valid answer" | The backend is not running, or it returned an error. Check terminal 1 and <http://localhost:8000/health>. |
| Example works but your own enquiry fails | You are in Option A (no backend/key), or the key has no quota. Use Option B. |
| `503 llm_unavailable` / rate-limit errors | The provider's quota or daily token limit is used up. Add a `*_FALLBACK_API_KEY`, wait for the reset, or switch `LLM_PROVIDER`. |
| Browser shows a CORS error | Set `FRONTEND_ORIGIN` in `backend/.env` to the exact address of the frontend and restart the backend. |
| Port already in use | Change the port (`--port 8001` for the backend, then update `ASSESS_BACKEND_URL`; `npm run dev -- -p 3001` for the frontend, then update `FRONTEND_ORIGIN`). |
| `uv: command not found` | Install it (`pip install uv`) or use `python3.11 -m venv .venv && .venv/bin/pip install -r requirements.txt`. |

---

## Limitations

- SpectraSense produces a **first draft for an expert to review**, not a final engineering recommendation. Statuses are deliberately cautious ("provisional", "insufficient information").
- The knowledge base is limited to the supplied AFS material (77 pages in 188 chunks). Where the sources show a method only for a different application, the report labels it as a *transfer assumption*.
- Fibre "coverage" is computed against **nominal** method ranges only; it is not a statement about a particular instrument.
- Citation checks verify that a quote is on the cited page. They do not prove that the claim is physically correct.
- Quotes from slide images are checked against the team's own transcriptions (`visual_note`), so the figure itself should be checked.
- The vector-search step needs an embedding key and a re-indexed collection (it needs the original source files, which are not in this repository). Without it, retrieval is BM25 plus reranking, which is what the committed results use.
- The walkthroughs on the *How it works* page are scripted examples, not live output.
- Free-tier LLM quotas can slow or stop live runs. The stored examples keep working when the backend or LLM is unavailable.
- No hosted demo is provided; the project is meant to be run locally as described above.

---

## Acknowledgements

- AFS (Art Fiber Systems) source material and the challenge organisers' examples.
- Backend structure adapted from the [8hr-MARATHON](https://github.com/d-hackmt/8hr-MARATHON) template.
- UI built with [Next.js](https://nextjs.org), [Tailwind CSS](https://tailwindcss.com), [shadcn/ui](https://ui.shadcn.com) and [motion-primitives](https://motion-primitives.com) (MIT), with a Carbon-inspired design using IBM Plex type.
- Backend built on [FastAPI](https://fastapi.tiangolo.com), [LangGraph](https://langchain-ai.github.io/langgraph/), [Qdrant](https://qdrant.tech) and [FlashRank](https://github.com/PrithivirajDamodaran/FlashRank).