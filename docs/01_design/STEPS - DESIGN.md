## STEPS - DESIGN.md
Given you have 405 cells per dimension, scoring dimension-by-dimension will typically be more consistent and faster to calibrate than scoring “whole submissions” end-to-end.
### Why dimension-first tends to work better
- You hold one set of criteria in working memory, so boundary decisions (e.g., 2 vs 3) stabilise.
- Anchors and disqualifiers are easier to apply consistently.
- You can tune flags and “needs review” rules per dimension (they often differ).
- If one dimension is noisy (e.g., students misunderstand it), you can fix the rubric for that dimension without perturbing the others.
### The main trade-off
You lose cross-dimension coherence checks (e.g., “they claim distributed accountability but then describe purely individual handoff”). You can recover that with a light second pass after all dimensions are scored.
### A practical workflow for your case (405 × 5)
#### Step 1: Calibrate one dimension at a time
For Dimension 1:
- Pull 25–40 cells from that dimension only.
- Build anchors for each score level.
- Write the dimension’s non-negotiables + disqualifiers + flags.
- Freeze the scoring block for that dimension.
Repeat for Dimensions 2–5.
This keeps each calibration problem small and reduces drift.
#### Step 2: Score all 405 cells for that dimension
Run the production scoring for Dimension 1 across all 405 cells.
- Output: score, evidence_quote, rationale, confidence, flags, needs_review.
Then move to Dimension 2, and so on.
#### Step 3: Add a lightweight cross-dimension consistency check (optional but useful)
After all five dimensions are scored, run a second pass that does not rescore, it only flags anomalies such as:
- High score on a dimension where the response is extremely short
- High scores across all dimensions with near-identical generic text
- Internal contradictions across dimensions (your choice of what matters)
- Missingness patterns (blank cells, malformed delimiters, mojibake that slipped through)
This second pass can be rule-based in Python and does not need a model unless you want “contradiction detection” to be more semantic.
### What I would do if I were optimising for reliability
1. Dimension-first scoring for all five dimensions
2. A strict needs_review rule that catches low-confidence cases
3. A small manual review queue per dimension (often 5–15% of cells)
4. A final coherence flag pass across the five scores per student (not rescore)
### One concrete tip for calibration
When you go dimension-first, your anchors become much more powerful if you include:
- 2 “borderline” exemplars for the hardest boundary
- 2 “vocabulary bait” exemplars (sounds right, doesn’t do the work)
- 2 “concise but strong” exemplars (to prevent penalising brevity)

If you paste your five dimensions (just the rubric text) I can help you draft the non-negotiables and boundary rules for each so you can start calibrating dimension 1 immediately.
