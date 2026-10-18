# Submission checklist (deadline Sun 18 Oct 2026 23:59)

Checked 03:35 CEST. ✅ verified now · ❌ missing · ❓ requirement unknown (brief not on disk)

| Item | Status | Note |
|---|---|---|
| All work committed and pushed to `main` | ❌ | 108 files uncommitted, 3 local commits unpushed |
| No secrets in the repo or its history | ✅ | scan of tracked files and full `git log -p`: 0 matches; `backend/.env` ignored |
| `.env.example` with placeholders only | ✅ | |
| Production build passes | ✅ | `next build`, 12 routes |
| Backend tests pass | ✅ | 106 passed |
| Live assessment works | ✅ | D01 in 5.5 s through the frontend |
| Fresh evaluation results (all 14 cases, large model) | ❌ | Evals page shows the 17 Oct run; batch 10/14 on the small model |
| Cached outputs regenerated for the fallback | ❌ | after the 10:00 batch |
| README: problem, screenshots, setup, stack, team, limitations | ❌ | root README is setup only |
| Licence and attribution (Carbon/IBM Plex, shadcn, motion-primitives MIT, AFS material) | ❌ | no LICENSE file |
| Architecture diagram matches the code | ❌ | diagram still shows NeMo / Groq Llama boxes |
| Hosted demo URL | ❓ | needed? |
| Video | ❓ | required? record a backup either way |
| Slides / pitch format | ❓ | |
| Pitch rehearsed (3 min) and judge Q&A prepared | ❌ | |
| `NEXT_PUBLIC_SITE_URL` set for the deployed address | ❓ | only if hosted |
