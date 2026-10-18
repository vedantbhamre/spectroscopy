# Pitch (3 minutes) and judge Q&A

Every number below is measured in this repo (see docs/00-status.md). Rehearse with a timer; record a backup video of steps 2–4.

## Script

| Time | Say | Show |
|---|---|---|
| 0:00–0:15 | "An AFS expert gets an enquiry like: *can we reuse our silica fibre for mid-IR water measurement, the analyzer is in another building?* Today that takes reading three documents. SpectraSense drafts the first assessment in seconds, and every claim points to the page it comes from." | Home page |
| 0:15–1:00 | Live: H04. "It answers first: **No**. The silica fibre does not carry 2.5–25 µm (Process Control slides p.6). It names the fibres that do, and it flags the 100-m-plus link as not shown in the material." | Assess → H04 → Answer, premise checks, click a citation chip |
| 1:00–1:30 | H06: "A customer wants to quote a kidney study as proof for surgery. The assistant says no, and lists why: in vitro, frozen samples, seven pairs, not their sensor, *aimed at in vivo* is a goal." | H06 report, scope check |
| 1:30–2:05 | Own enquiry from the jury, or: "We want to stop our Karl Fischer titration, NIR needs no calibration, right?" → "No … the reference method stays until the in-line method is validated." | Type it live |
| 2:05–2:30 | Trust: "The model proposes, rules decide: every quote is checked on its page, numbers must come from the customer or a cited page, unstated facts become assumptions. 182 offline tests; on the large model 100 % of quotes are found on the cited page." | Evals page: rings, open one enquiry vs the organisers' useful pages |
| 2:30–2:50 | Knowledge: "Retrieval follows the organisers' own source guide: 97 % of the pages they list as useful reach the model, from 35 % with plain search." | README knowledge-base table |
| 2:50–3:00 | "It's a draft for the expert, never a final decision. Next: a hosted version and AFS's full product catalogue." | — |

## Judge questions (20-second answers)

- **Why not just ChatGPT?** ChatGPT cites nothing it can prove. Here every quote is verified on its page, numbers are traced, and 15+ deterministic premise checks (fibre range, optics vs probe, source scope, calibration) decide the status, not the model.
- **What happens when the AI is wrong?** Wrong quotes are marked failed and their sentences moved to assumptions; unsupported numbers become "to be agreed"; certainty words are rejected; a failed premise lowers the status. The expert always reviews.
- **What data did you use?** Only the supplied AFS material (77 pages, 188 chunks) plus the team's transcriptions of slide images, labelled as such.
- **What is mocked?** Nothing in the live path. Stored answers (badged "Batch run") are earlier live outputs, used only when no backend is connected. The How-it-works walkthroughs are scripted and say so.
- **What does it cost?** About 9K tokens per assessment on Groq's gpt-oss-120b (free tier: about 20 assessments per day per account).
- **How does it scale?** Stateless API + local embeddings; the knowledge base is rebuilt from new files with one command. Production adds a hosted deployment, accounts and AFS's internal documents.
- **Weakest point?** It depends on one LLM provider's quota, and some application pages are read but not cited (0.72 of the organisers' useful pages are cited).
- **Another 4 weeks?** Expert feedback loop (accept / edit per section), AFS product catalogue for concrete part numbers, hosted pilot with AFS engineers.
