# Stress test: H06 (lab study quoted as surgical proof), live run 18 Oct 13:01

Enquiry `[BRIEF]` H06: "Can we quote its findings as proof that the proposed sensor is ready for that use? We have no new in vivo
data and no validation on our own setup. What assessment and next feasibility steps are appropriate?"
Expected answer `[USER]` (team reviewer, 18 Oct): no; seven in vitro pairs; classification of whole samples, not boundary detection;
not the customer's sensor; "aimed at in vivo applications" is a goal; an honest wording; next steps: reproduce ex vivo on own sensor
→ margin specimens mapped to histology spot by spot → validation on unseen patients (7 pairs: overfitting risk).

Scores are 1–5 team estimates against the official AFS criteria `[BRIEF]` (judging slide: "Technical quality, use of AFS knowledge,
feasibility, uncertainty, explainability, prototype"), weights unknown → equal.

| Criterion | Score | What this run did well | What it missed |
|---|---|---|---|
| Technical quality | 3 | NIR diffuse reflection, 900–1500 nm LED band, PCA/PLS-DA, histology as reference; fibre table correct | Never states that the study classified whole samples (tumour vs normal), which is a different task from finding a boundary in live tissue |
| Use of AFS knowledge | 3 | Cites kidney study p.1, p.2, p.14; quotes verified | Misses S03 p.3 "spectra of frozen/thawed biopsies can differ from real-life in vivo measurements" (the strongest scope quote) and p.1 "14 in vitro clinical samples of 7 different patients"; uses p.14 "aimed at in vivo applications" as support instead of as a goal |
| Feasibility | 3 | Ex vivo first, histology reference, cross-validation, variance check | No step "validate on patients the model has not seen"; no spot-by-spot margin mapping; step 5 jumps to "animal or pilot human study" |
| Uncertainty | 4 | Source-scope **fail** (in vitro), certainty **flag**, "Provisional" decision basis | Status label "Outside the supported scope" reads like a refusal; 7-pair sample size / overfitting not named as a risk |
| Explainability | 2.5 | Premise checks, cited chips, sources list | **No direct answer.** The customer asked a yes/no question; the report never says "No, it cannot be quoted as proof" and gives no honest wording they *can* use. Questions 1–2 (tissue scattering, instrument ports) are not decisive here; the decisive unknowns (their sensor vs the study's, reference method, boundary resolution) are listed but not asked. An unsupported ATR-MIR sentence is shown under assumptions instead of dropped |
| Prototype | 4 | Live run, full report, PDF export works | — |
| **Total** | **19.5 / 30** | | |

## Fixes, generic (no scenario-specific logic), ranked by judge value ÷ effort

1. **Direct answer first** (all enquiries; biggest gain). New `answer` field: one or two sentences that answer the customer's literal
   question (yes / no / not yet / depends on X), each claim cited, shown at the top of the report. When a premise check fails, the answer
   must state that premise and its citation. Plus optional "What you can say instead" when the customer asks to claim or quote something.
2. **Source-scope check names every dimension** that differs between the cited study and the request: sample state (in vitro,
   frozen/thawed vs in vivo), task (classify whole samples vs locate a boundary), instrument (the study's sensor vs the customer's),
   sample count. Facts come from the source pages, not from the enquiry ID.
3. **Feasibility plan rule:** when the evidence is from a small study, include validation on samples/patients not used for the model;
   never propose human or animal studies as a feasibility step.
4. **Status label:** `out_of_scope` → "Not supported by the sources" (the tool did answer; it is the customer's claim that is out of scope).
5. **Questions:** decisive-for-the-decision first (here: their sensor's wavelengths, reference method, required boundary resolution),
   setup details later. Drop assumption lines the claim validator marked "not supported by the cited page".

Needs LLM tokens to verify (one H06 run, ~10K). Re-check against the expected answer above.

## After the fixes (live H06 re-run, 18 Oct ~15:50, gpt-oss-120b, 8K tokens)

Implemented 1–4 and the question-order rule of 5 (unsupported sentences still move to the assumptions: that is an earlier
acceptance property, kept). Tests: `backend/tests/test_answer.py` (7 offline tests); suite 122 passed.

| Expected point | Now |
|---|---|
| Plain "No" | ✅ "No, the supplied LED NIR kidney study cannot be used as proof of clinical readiness because it was performed on resected tissue in vitro, not on living tissue in vivo." (Kidney study p.1, verified) |
| Seven in vitro pairs; whole samples vs boundary; not their sensor; "aimed at in vivo" = goal | ✅ all five dimensions in the source-scope check, each with its page quote (p.1, p.2, p.3, p.14) |
| What they can honestly say | ✅ "What you can say instead" (shown only when the customer wants to quote or claim something) |
| Own sensor ex vivo → histology → held-out patients | ✅ steps 1–5 incl. "Validate the model on held-out samples (different patients)"; over-fitting (14 samples) named as a risk |
| No jump to human studies | ✅ in the second run; later-stage steps are moved to points to confirm by `validate_feasibility` |
| Decisive questions first | ⚠ model-dependent: run 1 asked the reference method (5th of 5), run 2 asked a single scattering question |

Estimated after: technical quality 4, AFS knowledge 4.5, feasibility 4, uncertainty 4.5, explainability 4, prototype 4 → **25 / 30** (was 19.5).
