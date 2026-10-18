# Submission checklist (deadline Sun 18 Oct 2026 23:59)

Checked 20:30 CEST against the organisers' requirements `[BRIEF]`. ✅ verified now · ⚠ action advised · ❓ not stated

| Requirement | Status | Evidence |
|---|---|---|
| Repository public and accessible | ✅ | GitHub API and raw files answer without login (`private: false`) |
| Source code of a working prototype | ✅ | fresh clone: 150+ offline tests pass; production build passes (12 routes) |
| README: reproducible setup and run, dependencies, model/tool configuration | ✅ | Windows + macOS steps; only `GROQ_API_KEY` required; models and tools table |
| README: instructions for loading the supplied AFS materials | ✅ | "Loading the AFS materials": file names + one ingestion command; knowledge base committed |
| Short architecture description + how the assistant uses the AFS knowledge base | ✅ | README "How it works" + "How the assistant uses the AFS knowledge base" |
| Assistant answers for H01–H06 | ✅ | `answers/H01.md` … `H06.md` + index (exported unchanged from the live pipeline outputs) |
| No secrets in the repo or its history | ✅ | full `git log -p` scan: 0 Groq / OpenAI / LangSmith / Google / Logfire keys |
| All work committed and pushed | ✅ | after this commit |
| Licence | ⚠ | no LICENSE file; third-party attributions are in the README. Team decision (e.g. MIT) |
| Hosted demo URL / video / slides | ❓ | not required by the stated rules; record a backup screen video anyway |
