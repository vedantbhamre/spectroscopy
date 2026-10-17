# SpectraSense — AFS in-line spectroscopy assistant

| Folder | What it is |
| --- | --- |
| `frontend/` | Next.js web app (landing, Assess workbench, How it works). See `frontend/README.md`. |
| `backend/` | Assessment pipeline (FastAPI + LangGraph). See `backend/README.md`. The frontend calls it through `ASSESS_BACKEND_URL`. |

```bash
# backend (port 8000)
cd backend && uv venv --python 3.11 .venv && uv pip install --python .venv/bin/python -r requirements.txt
cp .env.example .env && .venv/bin/uvicorn app.main:app --port 8000

# frontend (port 3000)
cd frontend && npm install
echo 'ASSESS_BACKEND_URL=http://localhost:8000/assess' > .env.local && npm run dev
```
