this document sets out a WRAPPER PROMPT - which is used to create tightly bounded prompt which can to be used to assign provisional scores.

# .
```
BEGIN GENERATION
```

# .
```
## pl2_wrapper_prompt_generate_calibration_scoring_prompt_v02

Wrapper prompt: Generate a tightly bounded provisional scoring prompt for calibration use.

This wrapper prompt generates a prompt. It does not score student work.

## Required Input Artefacts (Overview)

Before this wrapper prompt can execute, the following input artefacts must be provided verbatim.

These artefacts correspond to the upstream **rubric construction pipeline** outputs.

All artefacts must use the authoritative nomenclature:

- `component_id`
- `dimension_id`
- indicators
- boundary rules

The wrapper prompt will read these artefacts silently during Stage 1.

Required artefacts:

- `CAL_<ASSESSMENT_ID>_<DIMENSION_ID>_Step01_dimension_header_v01`
- `CAL_<ASSESSMENT_ID>_<DIMENSION_ID>_Step02_indicators_checklist_v01`
- `CAL_<ASSESSMENT_ID>_<DIMENSION_ID>_Step03_boundary_rules_v01`

Additionally, the calibration run requires the calibration dataset payload format.

Required runtime payload definition:

- `CAL_<ASSESSMENT_ID>_<DIMENSION_ID>_CalibrationPayloadFormat`

All artefacts must be supplied in full and delimited using `===`.

If any artefact is missing or inconsistent, the wrapper prompt must produce no output.

## Purpose

- Generate one reusable scoring prompt that assigns provisional scores for a single rubric dimension (`dimension_id`).
- Enforce the supplied indicators and boundary rules as the sole scoring logic.
- Produce diagnostic, non-authoritative outputs intended for calibration analysis.
- Emit structured scoring diagnostics to allow rule inspection and boundary stress-testing.

Calibration scoring prompts must strictly follow the grading ontology:

- `submission_id` identifies the submission.
- `component_id` identifies the grading surface.
- `dimension_id` identifies the atomic rubric criterion.

Facets are optional analytic constructs and are never structural identifiers.

## Task Classification

This wrapper prompt performs:

- prompt synthesis
- rubric constraint propagation
- scoring prompt specification

This wrapper prompt does not perform:

- grading or scoring
- rubric improvement
- rule invention
- indicator invention
- coaching or pedagogical advice

## Authoritative Inputs (Verbatim)

The model may rely only on the following inputs supplied verbatim and delimited by `===`.

===
Input Artefact  
`CAL_<ASSESSMENT_ID>_<DIMENSION_ID>_Step01_dimension_header_v01`

Contents must include:

- `assessment_id`
- `component_id`
- `dimension_id`
- `dimension_label`
- one-sentence definition of what is being scored
- unit of analysis statement
- evidence rule (explicit-text only; no inference)
===

===
Input Artefact  
`CAL_<ASSESSMENT_ID>_<DIMENSION_ID>_Step02_indicators_checklist_v01`

Contents must include:

- 3–6 observable indicators
- indicators phrased as presence checks
- indicators referencing observable textual evidence
- optional facet tags (if used)
===

===
Input Artefact  
`CAL_<ASSESSMENT_ID>_<DIMENSION_ID>_Step03_boundary_rules_v01`

Contents must include:

- score level labels
- minimum conditions per level
- knock-down conditions
- explicit hardest boundary rule
- any explicit quality gates
===

===
Input Artefact  
`CAL_<ASSESSMENT_ID>_<DIMENSION_ID>_CalibrationPayloadFormat`

Each calibration item will have exactly:

- `row_id`
- `response_text`

Formatting guarantees:

- wrapper markers such as `+++` may appear and must be ignored
- no other metadata will be present
- each row must be scored independently
===

===
Output Requirements

Allowed fields include:

- `score`
- `indicator_hits`
- `facet_hits`
- `boundary_checks`
- `rationale`
- `evidence_quote`
- `confidence`
- `flags`
- `feedback`

Confidence scale and flag vocabulary must be provided by the user.
===

No external knowledge or interpretation is permitted.

## Stage Discipline (Mandatory)

Stage 1 — Input

- The user provides all required artefacts delimited by `===`.
- The model reads silently.
- No output is generated.

If the message `BEGIN GENERATION` is not present, the model must produce no output.

Stage 2 — Execution

- When the user sends `BEGIN GENERATION`, the model generates the scoring prompt artefact.

## Output Artefact

The model must generate exactly one artefact:

`CAL_<ASSESSMENT_ID>_<DIMENSION_ID>_Step05_provisional_scoring_prompt_v01`

The artefact must:

- score exactly one `dimension_id`
- reference the correct `component_id`
- assume the fixed calibration payload format
- be reusable across calibration runs

## Generated Scoring Prompt Structure

The generated scoring prompt must:

- appear in a single fenced Markdown block
- use headings no deeper than level 2
- avoid nested lists
- use bullet lists only

Sections must appear in this order:

- Prompt title and restrictions
- Authoritative scoring materials
- Input format
- Scoring procedure
- Feedback generation rules
- Feedback format
- Output schema
- Constraints
- Content rules
- Failure mode handling

## Required Scoring Semantics

The generated scoring prompt must enforce:

- one score per `(row_id × dimension_id)`
- application of boundary rules before indicator confirmation
- explicit evaluation of the hardest boundary rule
- evaluation of indicator presence
- evaluation of optional facet sufficiency (if facets exist)

If scoring is indeterminate:

- assign the lowest evaluable score label
- include flag `needs_review`

## Failure Mode Handling

If any required artefact is missing, inconsistent, or contradictory:

- produce no output
- wait silently for corrected inputs



## pl3_wrapper_prompt_generate_production_scoring_prompt_v02

Wrapper prompt: Generate a production scoring prompt that evaluates all rubric dimensions for a single component in one pass.

This wrapper prompt generates a prompt. It does not score student work.

## Required Input Artefacts (Overview)

The following artefacts must be supplied.

These correspond to the frozen rubric produced by the rubric construction pipeline.

Required artefacts:

- `<ASSESSMENT_ID>_<COMPONENT_ID>_Step01_dimension_set_v01`
- `<ASSESSMENT_ID>_<COMPONENT_ID>_Step02_indicators_checklist_v01`
- `<ASSESSMENT_ID>_<COMPONENT_ID>_Step03_boundary_rules_v01`
- `<ASSESSMENT_ID>_<COMPONENT_ID>_ScoringPayloadFormat`

All artefacts must be supplied verbatim and delimited using `===`.

## Purpose

- Generate one production scoring prompt for a single `component_id`.
- Score all dimensions of that component in one pass.
- Emit per-dimension audit diagnostics.
- Enforce a frozen rubric definition.

## Task Classification

This wrapper prompt performs:

- prompt synthesis
- scoring prompt specification

It does not perform:

- rubric calibration
- rule modification
- indicator invention
- coaching or pedagogical advice

## Authoritative Inputs (Verbatim)

The model may rely only on the following artefacts.

===
Input Artefact  
`<ASSESSMENT_ID>_<COMPONENT_ID>_Step01_dimension_set_v01`

Contents must include:

- `component_id`
- list of `dimension_id`
- `dimension_label`
- one-sentence dimension definition
===

===
Input Artefact  
`<ASSESSMENT_ID>_<COMPONENT_ID>_Step02_indicators_checklist_v01`

Contents must include the full indicator checklist for the component.
===

===
Input Artefact  
`<ASSESSMENT_ID>_<COMPONENT_ID>_Step03_boundary_rules_v01`

Contents must define the boundary rules for each dimension.
===

===
Input Artefact  
`<ASSESSMENT_ID>_<COMPONENT_ID>_ScoringPayloadFormat`

Each scoring item includes:

- `row_id`
- `submission_id`
- `component_id`
- `response_text`
===

===
Output Requirements

Allowed per-dimension fields:

- `score`
- `indicator_hits`
- `boundary_checks`
- `evidence_quote`
- `confidence`
- `flags`
- `feedback`
===

## Stage Discipline

Stage 1 — Input

- The user supplies all artefacts delimited by `===`.
- The model reads silently.
- No output is produced.

If the message `BEGIN GENERATION` is not present, the model must produce no output.

Stage 2 — Execution

- After receiving `BEGIN GENERATION`, the model generates the scoring prompt artefact.

## Output Artefact

The model must generate:

`SCORE_<ASSESSMENT_ID>_<COMPONENT_ID>_component_multi_dimension_prompt_v01`

The generated scoring prompt must:

- evaluate all dimensions of the component
- emit per-dimension diagnostic bundles
- preserve atomic scoring units

## Output Structure

For each scoring item:

- return `row_id`
- return `submission_id`
- return `component_id`
- return a `dimension_results` list

Each `dimension_results` entry must include:

- `dimension_id`
- `dimension_label`
- `score`
- selected diagnostics

## Failure Mode Handling

If any required artefact is missing or contradictory:

- produce no output
- wait silently for corrected inputs
===
  
```