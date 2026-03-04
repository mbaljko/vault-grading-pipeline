
## Pipeline1B - Rubric Construction Pipeline — Dimension-Level Specification

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
