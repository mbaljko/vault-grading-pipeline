### Steps to calibrate one dimension at a time (revised workflow)
#### 1) Generate Dimension Header
##### Freeze the target dimension and its unit of analysis
- Write the dimension name exactly as it appears in your rubric.
- Define what you are scoring in one sentence (e.g., “quality of boundary-marking around where responsibility stops / is handed off”).
- Define the unit you will score: one cell = one score for this dimension, regardless of what else is in the response.
Deliverable: a 3–5 line “dimension header” kept visible while scoring.  
`CAL_PPP_SectionA_Step01_dimensiovaultn_header_v01`
#### 2) Translate the dimension into observable indicators
Convert abstract rubric language into things you can point to in text.
- Phrase indicators as “does the response do X”, not “shows understanding of Y”.
- Keep indicators dimension-specific; do not import other rubric dimensions.
- Aim for 3–6 indicators total.
Deliverable: a short checklist usable at speed.  
`CAL_PPP_SectionA_Step02_indicators_checklist_v01`
#### 3) Define the score scale as boundary rules
Define scoring in terms of thresholds and failure modes, not descriptions.
For each score level:
- Minimum conditions required to earn that level.
- What knocks it down (missing element or common failure).
- Explicitly specify the hardest boundary (typically 2 vs 3).
Deliverable: explicit if/then boundary rules.  
`CAL_PPP_SectionA_Step03_boundary_rules_v01`
#### 4) Build a calibration set using interior sampling
Construct a fixed calibration set that stresses boundary decisions.
- Order all responses for this dimension by length (shortest → longest).
- Discard the single shortest and single longest responses.
- From the remaining set, sample uniformly across interior quantiles.
- Target 25–40 cells total.
- If fewer than 30 valid cells exist, include all.
Purpose:
- Concentrate on ambiguous, mid-spectrum responses.
- Avoid trivial failures and obvious exemplars.
- Ensure even coverage of the decision surface.
Deliverable: a fixed list of cell or row IDs.  
`CAL_PPP_SectionA_Step04_calibration_set_v01`
#### 5) Provisional scoring via constrained prompt
Instead of manual first-pass scoring, use a tightly bounded prompt to assign provisional scores.
- Prompt scores **only this dimension**.
- Prompt applies the defined boundary rules.
- Prompt produces provisional scores (optionally with minimal justification).
Use this step diagnostically, not as authority.
Deliverable: provisional scoring output for the calibration set.  
`CAL_PPP_SectionA_Step05_provisional_scores_v01`
#### 6) Inspect for drift and boundary instability
Review the provisional results to identify patterns, not correctness.
Look for:
- Score bands with frequent ambiguity or inconsistency.
- Boundaries where decisions cluster or oscillate.
- Fluent-but-empty responses being over-scored.
- Brief-but-valid responses being under-scored.
- Systematic bias related to length, tone, or form.
Then revise:
- Add one disqualifier (what does *not* count).
- Add one positive anchor condition (what *does* count, even if brief).
- Tighten the hardest boundary rule.
Deliverable: revised boundary rules.  
`CAL_PPP_SectionA_Step06_boundary_rules_v02`
#### 7) Create anchor examples
From the calibration set, select exemplars.
- Minimum of two per score level:
  - one clean,
  - one borderline.
For each anchor:
- State why it earns that score (linked to indicators).
- State what would move it up or down.
Deliverable: anchor bank for this dimension.  
`CAL_PPP_SectionA_Step07_anchor_bank_v01`
#### 8) Second-pass stability check
Re-score the same calibration set using the revised rules.
- Human-only pass.
- Faster than initial calibration.
- Focus on whether decisions feel stable and repeatable.
Deliverable: short stability note (what improved, what remains hard).  
`CAL_PPP_SectionA_Step08_stability_check_v01`
#### 9) Set the production scoring protocol
Before scoring all responses, lock the operating rules.
Decide:
- Default scoring pace (single read, no rumination).
- Explicit triggers for `needs_review`.
- Recalibration threshold (e.g., if 10 of the last 30 are low-confidence).
Deliverable: one-paragraph production policy.  
`CAL_PPP_SectionA_Step09_production_protocol_v01`
### Materials to keep visible while scoring
- Dimension header
- Indicator checklist
- Boundary rules (especially the mention hardest boundary)
- Anchor bank
- `needs_review` triggers
