# SpectraSense

SpectraSense helps a process engineer make an initial assessment of whether spectroscopy could measure something in a production line. It asks for missing details, suggests methods to investigate, and creates a report with source citations, risks, and a first experiment to try.

The project was built for the Art Fiber Systems (AFS) in-line spectroscopy challenge. The supplied AFS documents are the main technical reference used by the application.

### For the jury: where everything is

| You want to… | Go to |
| --- | --- |
| Read the assistant's answers to the **final evaluation scenarios H01–H06** | [`answers/`](answers/README.md): one readable file per scenario, with every cited source quote |
| Run the live application on your computer (one free Groq key) | sections [1](#1-install-nodejs-and-python) to [6](#6-try-spectrasense) below |
| Look around **without any API key** | [Without an API key](#without-an-api-key) |
| See the architecture and how the AFS knowledge base is used | [How it works](#8-how-it-works) |
| Load or rebuild the supplied AFS materials | [Loading the AFS materials](#loading-the-afs-materials) |
| Models, tools and dependencies | [Models, tools and dependencies](#9-models-tools-and-dependencies) |

## Before you start

To run the live application on your own computer, you need:

- A computer running Windows 10/11 or macOS.
- An internet connection.
- Node.js 20 or newer (npm is included with Node.js).
- Python 3.11.
- A Groq API key for the live assistant (free). No other key is needed.

You do not need to install a separate database server. The knowledge files are included in the project.

> **Use free-tier quota for the demo:** For the jury demo, create and use API keys under the providers’ free-tier allowance/credits where available. Keep usage within the free quota and do not enable or rely on paid usage for this setup. Do not share your keys or commit them to GitHub.

## 1. Install Node.js and Python

### Windows

1. Open the official Node.js website: <https://nodejs.org/en/download>.
2. Download the **LTS** installer for Windows and run it. Keep the default installation options. npm is installed with Node.js.
3. Open <https://www.python.org/downloads/release/python-3119/> and download the Windows installer for Python 3.11. During installation, tick **Add python.exe to PATH**, then complete the installation.
4. Open **PowerShell** from the Start menu.
5. Check that the tools are installed by running:

   ```powershell
   node --version
   npm --version
   py -3.11 --version
   ```

   The commands should print version numbers. If Windows cannot find `py`, try `python --version` and make sure it reports Python 3.11.

### macOS

1. Open the official Node.js website: <https://nodejs.org/en/download>.
2. Download the **LTS** installer for macOS and run it. npm is installed with Node.js.
3. Download Python 3.11 from <https://www.python.org/downloads/release/python-3119/> and run the macOS installer.
4. Open **Terminal** (Finder → Applications → Utilities → Terminal).
5. Check that the tools are installed by running:

   ```bash
   node --version
   npm --version
   python3.11 --version
   ```

   The commands should print version numbers.

If you already have Node.js 20 or newer and Python 3.11 installed, you can skip the installation steps.

## 2. Download the project

If you are using Git, open PowerShell (Windows) or Terminal (macOS) and run:

```bash
git clone https://github.com/yashwanth-1341/spectroscopy.git
cd spectroscopy
```

If you downloaded the project as a ZIP file instead, extract it first. Open a terminal in the extracted `spectroscopy` folder. The folder you open should contain the `backend` and `frontend` folders and this `README.md` file.

## 3. Get your API keys

The live assistant uses a Groq key. You must add your own key on your computer; the project does not include a shared key.

### Get a Groq API key (required)

1. Open <https://console.groq.com> and sign in or create an account.
2. Open the API Keys page: <https://console.groq.com/keys>.
3. Create a new API key and copy it. Treat it like a password.

**That is the only key you need.** Search runs on your computer with a local model, so no embedding key (such as Gemini) is required. The settings file has a few optional lines (a second Groq key for more quota, a judge key, tracing, Gemini); leave them empty.

### Key for the evaluation judge (optional)

If you want to run the **Evals → Run evals** feature, you can add a Groq key to `JUDGE_GROQ`. You may use the same key as `GROQ_API_KEY`. A key from a separate Groq account keeps evaluation usage separate and makes the judge independent of the assistant, but it is not required.

Running live evaluations sends requests to the model provider and may use your account's quota.

## 4. Set up the backend

The backend runs the assessment and connects to Groq. Keep this terminal open while using the application.

### Windows (PowerShell)

From the main `spectroscopy` project folder, run:

```powershell
cd backend
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
```

Notepad will open the backend settings file. Find this line:

```ini
GROQ_API_KEY=
```

Paste your Groq key after the equals sign, with no quotation marks. For example:

```ini
GROQ_API_KEY=paste_your_own_key_here
```

`GROQ_API_KEY` is the only required line. If you plan to run evaluations, you may also fill in `JUDGE_GROQ=` (the same Groq key works). Leave all other lines empty.

Save and close Notepad. Then start the backend:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

Keep this PowerShell window open. To check that the backend started, open <http://localhost:8000/health> in your browser. It should show `"llm": "groq"` and `"kb_chunks": 188`. If the page does not load or the `llm` value is `null`, see [Common problems](#10-common-problems).

### macOS (Terminal)

From the main `spectroscopy` project folder, run:

```bash
cd backend
python3.11 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
open -e .env
```

The settings file will open in TextEdit. Find this line:

```ini
GROQ_API_KEY=
```

Paste your Groq key after the equals sign, without quotation marks. For example:

```ini
GROQ_API_KEY=paste_your_own_key_here
```

`GROQ_API_KEY` is the only required line. If you plan to run evaluations, you may also fill in `JUDGE_GROQ=` (the same Groq key works). Leave all other lines empty.

Save the file and close TextEdit. Then start the backend:

```bash
.venv/bin/python -m uvicorn app.main:app --reload --port 8000
```

Keep this Terminal window open. To check that the backend started, open <http://localhost:8000/health> in your browser. It should show `"llm": "groq"` and `"kb_chunks": 188`. If the page does not load or the `llm` value is `null`, see [Common problems](#10-common-problems).

## 5. Start the website

Open a **second** PowerShell/Terminal window. Leave the backend running in the first one.

### Windows (PowerShell)

If you used the Git instructions, run:

```powershell
cd spectroscopy\frontend
npm install
Copy-Item .env.example .env.local
notepad .env.local
```

If you extracted a ZIP, use `cd` to enter the extracted project's `frontend` folder instead. Notepad will open the frontend settings file. It should contain:

```ini
ASSESS_BACKEND_URL=http://localhost:8000/assess
```

Save and close the file, then start the website:

```powershell
npm run dev
```

### macOS (Terminal)

If you used the Git instructions, run:

```bash
cd spectroscopy/frontend
npm install
cp .env.example .env.local
open -e .env.local
```

If you extracted a ZIP, enter the extracted project's `frontend` folder instead. The settings file should contain:

```ini
ASSESS_BACKEND_URL=http://localhost:8000/assess
```

Save and close the file, then start the website:

```bash
npm run dev
```

Open <http://localhost:3000/assess> in your browser. Both terminal windows must remain open while you use the live application.

## 6. Try SpectraSense

1. Open the **Assess** page at <http://localhost:3000/assess>.
2. Enter a process description. For example: “We want to monitor water content in a recovered solvent stream. Our current measurements are done in a laboratory, and we want faster results during production.”
3. Read the follow-up questions. Answer what you know; **Don't know** and **Skip** are valid answers.
4. Review the report. It separates customer-provided information from unknowns and assumptions, suggests spectroscopy methods, explains risks, and proposes a feasibility experiment.
5. Check the source citations. The citation chips show the AFS document and page used for the claim.
6. Use **Final report** if you want the report without answering more questions.

The first backend start may take longer because it downloads a local text-search model and prepares the source index. Keep the backend terminal open and wait for the server to finish starting.

## 7. Useful pages

- **Assess** — enter a new enquiry and generate a report.
- **How it works** — see an explanation of the assessment process. Walkthrough examples on this page are scripted demonstrations, not live assessments.
- **Evals** — view stored evaluation results. **Run evals** runs model-based evaluations and uses API quota.

The app includes the organisers' example enquiries: D01–D08 (development) and H01–H06 (final evaluation). Open one with <http://localhost:3000/assess?example=H04>. The jury can also enter a new enquiry to test the live assistant.

### Answers for the final evaluation scenarios (H01–H06)

The assistant's answers for all six final evaluation scenarios (and the eight development scenarios) are in [`answers/`](answers/README.md), one readable file per scenario: the enquiry, the answer, the premise checks, the recommended methods with page citations, the measurement concept, the feasibility experiment and every quoted source. They were generated by the live pipeline (`backend/scripts/run_batch.py`, stored in `frontend/outputs/<ID>.json`) and exported unchanged (`backend/scripts/export_answers.py`).

### Without an API key

To look around without any key or backend, start only the website (section 5, skip the `.env.local` step) and open an example such as <http://localhost:3000/assess?example=H04>. Examples are answered from the stored live-pipeline results and badged **Batch run**. A new enquiry needs the backend and a Groq key; the app never invents an answer.

## 8. How it works

```
enquiry ─► safety gate ─► planner ─► analyst ─► retriever ─► premise checks ─► responder ─► report
```

| Step | What it does | Uses the language model? |
| --- | --- | --- |
| Safety gate | blocks off-topic, jailbreak and prompt-injection messages | yes, with a rule-based fallback |
| Planner | decides between a new assessment and a follow-up question; writes search queries | yes |
| Analyst | separates what the customer stated (kept only if quoted from the customer) from unknowns | yes |
| Retriever | finds the relevant AFS pages (see below) | no |
| Premise checks | rule checks on what the enquiry assumes: target named, fibre range vs method range, optics vs probe geometry, source scope, calibration and reference method, certainty requested | no |
| Responder | writes the report; then rules verify every quote on its page, every number against the customer's words or a cited page, and lower the status if a check fails | yes (writing), no (checking) |

The language model proposes; the rule-based checks decide. The full list of rules is in [`backend/README.md`](backend/README.md).

### How the assistant uses the AFS knowledge base

The assistant answers only from the supplied AFS material; the language model receives the retrieved pages and nothing else.

| ID | Source | In the knowledge base |
| --- | --- | --- |
| S01 | AFS Multispectral Laboratory guide (+ Table 1, the method comparison table) | 19 pages + Table 1 |
| S02 | AFS Process Control slides | 20 pages + 11 team transcriptions of slide images |
| S03 | LED kidney tissue study (2017) | 17 pages |
| S04 | Combined MIR + fluorescence study (2021) | 6 pages |
| S05 | AFS flyer | 2 pages |
| S06 | AFS laboratory web page | 1 page |

1. **Prepared once:** every page is extracted with its page number and split into 188 chunks (`backend/processed_data/`), so every citation can say "S01 p.14".
2. **Retrieval for each enquiry (10 pages):** the organisers' source guide routes the enquiry to the right pages (method overview and Table 1, the application pages for its industry, the method pages, the fibre pages when distance or fibres come up). Keyword search and local semantic search fill the remaining places.
3. **Citation by passage:** each retrieved page is split into numbered passages; the model cites a passage number, so every quote is the page's own text, and each quote is checked on its page.
4. **Rules from the sources:** method ranges, fibre transmission windows and the Table 1 cost and sample-type columns are stored with their page quotes (`backend/app/knowledge/`). The premise checks use them, for example "a silica fibre cannot carry the mid-infrared range" (S02 p.6).
5. **Scope:** a page that shows a method for another industry is labelled a *transfer assumption*; a laboratory study is never presented as proof of process or clinical readiness.

### Loading the AFS materials

**Nothing to do to run the app:** the processed knowledge base (`backend/processed_data/pages.json` and `chunks.json`) is included, and the local search index is built automatically on the first backend start.

To rebuild it from the original files:

1. Put the supplied files in one folder, keeping their names (the prefix `S01_` … `S06_` sets the source ID):
   ```text
   S01_Multispectral_Laboratory.pdf        S04_Combi_MIR_Fluorescence_2021.pdf
   S02_AFS_Process_Control_Slides.pdf      S05_AFS_Flyer.pdf
   S03_LED_Kidney_Study_2017.pdf           S06_Laboratory_Link.txt
   AFS_method_comparison_table.xlsx        (becomes S01 Table 1)
   ```
   The organisers' `AFS_Examples_and_Reference.docx` and `customer_scenarios_for_final_evaluation.txt` may be in the folder; they are skipped, so the assistant never reads the expected answers.
2. From the `backend` folder, run (Windows: `.\.venv\Scripts\python.exe` instead of `.venv/bin/python`):
   ```bash
   .venv/bin/python -m app.ingestion.processor --materials /path/to/that/folder --no-index
   ```
   It prints the pages per source and the chunk count (77 pages and 188 chunks for the supplied set).
3. Restart the backend; the search index is rebuilt automatically.

## 9. Models, tools and dependencies

| Part | What is used |
| --- | --- |
| Language model | Groq `openai/gpt-oss-120b` writes the assessments; `openai/gpt-oss-20b` runs the safety gate and is the fallback |
| Search | keyword search (BM25) + local semantic search with BGE-base (`BAAI/bge-base-en-v1.5`, via fastembed, runs on the CPU, downloaded once, about 210 MB) |
| Backend | Python 3.11, FastAPI, LangGraph; packages in `backend/requirements.txt` |
| Website | Node.js 20+, Next.js 15, React 19, Tailwind CSS; packages in `frontend/package.json` |
| Settings | `backend/.env` (copy of `backend/.env.example`; only `GROQ_API_KEY` is required) and `frontend/.env.local` (copy of `frontend/.env.example`) |

Tests (no API key needed): from `backend`, run `.venv/bin/python -m pytest -q`.

## 10. Common problems

### “No LLM configured” or the report cannot be generated

- Check that `GROQ_API_KEY` is filled in inside `backend/.env` (not `.env.example`).
- Make sure the key was copied correctly and does not contain quotes or extra spaces.
- Stop and restart the backend after changing `.env`.
- Check your Groq account's key status, quota and rate limits.

### The website opens, but live assessments do not work

- Check that the backend is running in the first terminal.
- Open <http://localhost:8000/health> and confirm it responds.
- Check that `frontend/.env.local` contains `ASSESS_BACKEND_URL=http://localhost:8000/assess`.
- Restart the frontend after changing `.env.local`.

### “Address already in use” or port 3000/8000 is occupied

Another application may already be using that port. Close the other application or stop the previous SpectraSense process before restarting.

### `node`, `npm` or Python is not recognised

Close and reopen the terminal after installation. If the command still fails, reinstall the tool and ensure it was added to your system's PATH.

### Installation fails while downloading packages or the local search model

Check your internet connection and try again. The first start downloads additional files, so it can take longer than later starts.

### The Evals page cannot run an evaluation

Check that `GROQ_API_KEY` is configured. If you want a separate judge key, add it to `JUDGE_GROQ` in `backend/.env`, then restart the backend. Live evaluations use API quota and may be limited by the provider.

## 11. API key safety

- Never paste a real API key into the README, source code, screenshots, or a public issue.
- Keep keys in `backend/.env`. Do not put model-provider keys in the frontend settings file.
- Do not upload or commit your `.env` file. The project is set up to ignore it.
- If a key is accidentally shared, revoke it with the provider and create a replacement.

## 12. Project folders

```text
spectroscopy/
├── answers/     The assistant's answers for H01–H06 and D01–D08 (readable Markdown)
├── backend/     Assessment API, AFS knowledge base, retrieval, validation and evaluation tools
└── frontend/    Website and report display
```

The backend uses Python and FastAPI. The website uses Next.js and npm. Only the Groq API key (`GROQ_API_KEY`) is required.

## Official key pages

- Groq API keys (required): <https://console.groq.com/keys>
- Optional extras in `backend/.env`: Gemini <https://aistudio.google.com/apikey>, Pydantic Logfire <https://logfire.pydantic.dev>, LangSmith <https://smith.langchain.com>

