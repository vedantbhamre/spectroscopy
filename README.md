# SpectraSense — AFS in-line spectroscopy assistant

| Folder | What it is |
| --- | --- |
| `frontend/` | Next.js web app (landing, Assess workbench, How it works). See `frontend/README.md`. |
| `backend/` | Assessment pipeline (FastAPI). The frontend calls it through `ASSESS_BACKEND_URL`. |

```bash
cd frontend && npm install && npm run dev
```
