## Rubric Construction Pipeline — Dimension-Level Specification
This document defines the upstream process for constructing and stabilising a single rubric dimension (i.e., a grading dimension within a component).
This pipeline is epistemic and iterative.  
Its output must be frozen before execution stages (Stage 0A / Stage 0B).
## 1. Dimension Definition
### 1.1 Generate Dimension Header
Purpose:
Freeze the conceptual identity of the grading dimension.
Requirements:
- Record the dimension name exactly as it will appear in the rubric.
- Define in one sentence what is being scored.
- Define the unit of analysis (e.g., one cell = one score).
- Define the evidence rule (explicit-text only; no inference).
Deliverable:
`<ASSESSMENT>_<Component>_Step01_dimension_header_v01`
## 2. Indicator Construction
### 2.1 Translate the Dimension into Observable Indicators
Purpose:
Convert abstract rubric language into observable textual moves.
Requirements:
- Phrase indicators as “does the response do X”.
- Indicators function strictly as presence checks.
- Keep indicators specific to this dimension.
- Target 3–6 indicators total.
Indicators must not:
- Encode performance levels.
- Smuggle in boundary thresholds.
- Import criteria from other dimensions.
Deliverable:
`<ASSESSMENT>_<Component>_Step02_indicators_checklist_v01`
## 3. Boundary Rule Engineering
### 3.1 Define Score Levels as Threshold Rules
Purpose:
Define score levels using minimum conditions and knock-down rules.
For each score level:
- Specify minimum conditions.
- Specify disqualifying failures.
- Explicitly define the hardest boundary (e.g., Approaching vs Meets).
- Define any performance-level quality gates.
Rules must:
- Be stated as if/then logic.
- Distinguish structural sufficiency from surface completeness.
- Prevent indicator-completeness inflation.
Deliverable:
`<ASSESSMENT>_<Component>_Step03_boundary_rules_v01`
## 4. Calibration Stress-Testing (Rubric Stability Testing)
### 4.1 Build a Calibration Set (Interior Sampling)
Purpose:
Stress-test boundary rules on ambiguous cases.
Procedure:
- Order responses by length.
- Discard extreme shortest and longest.
- Sample evenly across interior quantiles.
- Target 25–40 cases (or all if fewer exist).
Deliverable:
`<ASSESSMENT>_<Component>_Step04_calibration_set_v01`
### 4.2 Provisional Scoring (Diagnostic Pass)
Purpose:
Apply boundary rules mechanically to detect instability.
Constraints:
- Score only this dimension.
- Apply boundary rules strictly.
- Use output diagnostically, not authoritatively.
Deliverable:
`<ASSESSMENT>_<Component>_Step05_provisional_scores_v01`
### 4.3 Drift and Boundary Instability Analysis
Purpose:
Detect structural weaknesses in boundary logic.
Inspect for:
- Oscillation at specific boundaries.
- Over-scoring of fluent-but-empty responses.
- Under-scoring of brief-but-valid responses.
- Ambiguity clustering.
- Systematic bias by length or tone.
Revision Actions:
- Add one disqualifier.
- Add one positive anchor condition.
- Tighten hardest boundary rule.
Deliverable:
`<ASSESSMENT>_<Component>_Step06_boundary_rules_v02`
## 5. Anchor Bank Construction
### 5.1 Select Anchors
Purpose:
Stabilise interpretive reference points.
Requirements:
- Minimum two anchors per score level.
  - One clean.
  - One borderline.
- For each:
  - State why it earns the score (linked to boundary rules).
  - State what would move it up or down.
Deliverable:
`<ASSESSMENT>_<Component>_Step07_anchor_bank_v01`
## 6. Stability Confirmation
### 6.1 Second-Pass Human Stability Check
Purpose:
Verify repeatability after boundary tightening.
Procedure:
- Re-score the same calibration set manually.
- Focus on stability of decisions.
- Identify any remaining fragile boundaries.
Deliverable:
`<ASSESSMENT>_<Component>_Step08_stability_check_v01`
## 7. Rubric Freeze
Before execution:
- Lock boundary rules.
- Lock indicators.
- Lock dimension definition.
- Assign `rubric_version`.
No dimension counts or score-level definitions may change after freeze without incrementing `rubric_version`.
## Outputs of Rubric Construction
At completion, the following must exist:
- Dimension header
- Indicator checklist
- Boundary rules (final version)
- Anchor bank
- Stability note
- Declared rubric_version
Only after this freeze may Stage 0B expand targets using this rubric definition.
