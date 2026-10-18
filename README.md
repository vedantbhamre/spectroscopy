# SpectraSense

SpectraSense helps a process engineer make an initial assessment of whether spectroscopy could measure something in a production line. It asks for missing details, suggests methods to investigate, and creates a report with source citations, risks, and a first experiment to try.

The project was built for the Art Fiber Systems (AFS) in-line spectroscopy challenge. The supplied AFS documents are the main technical reference used by the application.

## Before you start

To run the live application on your own computer, you need:

- A computer running Windows 10/11 or macOS.
- An internet connection.
- Node.js 20 or newer (npm is included with Node.js).
- Python 3.11.
- A Groq API key for the live assistant.
- About 10–15 GB of free disk space is recommended for dependencies and the local embedding model.

You do not need to install a separate database server. The knowledge files are included in the project.

> **Use free-tier quota for the demo:** For the jury demo, create and use API keys under the providers’ free-tier allowance/credits where available. Keep usage within the free quota and do not enable or rely on paid usage for this setup. Free-tier availability, limits, and eligibility can change, so check the current terms on each provider’s website. Do not share your keys or commit them to GitHub.

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

### Get a Gemini API key (required)

1. Open Google AI Studio: <https://aistudio.google.com/apikey>.
2. Sign in with a Google account.
3. Create or select an API key and copy it.

**Important:** You must provide both a Groq API key and a Gemini API key for the jury setup. For the demo, use the providers’ free-tier quota/credits where available and keep your testing within those limits. Add your Gemini key to `GEMINI_API_KEY` in the backend `.env` file, as well as your Groq key in `GROQ_API_KEY`. Check each provider’s current free-tier terms before testing; limits and availability may change.

### Key for the evaluation judge (optional)

If you want to run the **Evals → Run evals** feature, you can add a Groq key to `JUDGE_GROQ`. You may use the same key as `GROQ_API_KEY`, as requested for the demo setup. A separate key or account can help keep evaluation usage separate, but it is not required by the code.

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

Fill in `GEMINI_API_KEY=` with your Gemini API key. Both `GROQ_API_KEY` and `GEMINI_API_KEY` must be provided. If you plan to run evaluations, fill in `JUDGE_GROQ=` with the Groq key you want to use for judging. You can use the same Groq key for `GROQ_API_KEY` and `JUDGE_GROQ`. Leave other settings unchanged unless you know you need them.

Save and close Notepad. Then start the backend:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

Keep this PowerShell window open. To check that the backend started, open <http://localhost:8000/health> in your browser. It should show `spectrasense-backend` and a configured language model. If the page does not load or the `llm` value is `null`, see [Troubleshooting](#troubleshooting).

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

Fill in `GEMINI_API_KEY=` with your Gemini API key. Both `GROQ_API_KEY` and `GEMINI_API_KEY` must be provided. If you plan to run evaluations, fill in `JUDGE_GROQ=` with the Groq key you want to use for judging. You can use the same Groq key for `GROQ_API_KEY` and `JUDGE_GROQ`. Leave other settings unchanged unless you know you need them.

Save the file and close TextEdit. Then start the backend:

```bash
.venv/bin/python -m uvicorn app.main:app --reload --port 8000
```

Keep this Terminal window open. To check that the backend started, open <http://localhost:8000/health> in your browser. It should show `spectrasense-backend` and a configured language model. If the page does not load or the `llm` value is `null`, see [Troubleshooting](#troubleshooting).

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

The app includes development examples labelled D01–D08 and H01–H06. They help demonstrate the interface and assessment process. The jury can also enter a new enquiry to test the live assistant.

## 8. Common problems

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

## 9. API key safety

- Never paste a real API key into the README, source code, screenshots, or a public issue.
- Keep keys in `backend/.env`. Do not put model-provider keys in the frontend settings file.
- Do not upload or commit your `.env` file. The project is set up to ignore it.
- If a key is accidentally shared, revoke it with the provider and create a replacement.

## 10. Project folders

```text
spectroscopy/
├── backend/     Assessment API, source retrieval, validation, and evaluation tools
├── frontend/    Website and report display
└── docs/        Project notes and submission information
```

The backend uses Python and FastAPI. The website uses Next.js and npm. For the jury setup, provide both the Groq API key (`GROQ_API_KEY`) and the Gemini API key (`GEMINI_API_KEY`).

## Official key pages

- Groq API keys: <https://console.groq.com/keys>
- Gemini API keys: <https://aistudio.google.com/apikey>

