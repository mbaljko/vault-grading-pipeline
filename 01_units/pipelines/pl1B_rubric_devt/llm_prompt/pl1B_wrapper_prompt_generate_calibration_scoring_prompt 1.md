this document sets out a WRAPPER PROMPT - which is used to create tightly bounded prompt which can to be used to assign provisional scores.

# .
```
BEGIN GENERATION
```

# .
```
## pl1B_wrapper_prompt_generate_calibration_scoring_prompt_v03

Wrapper prompt: Generate a tightly bounded provisional scoring prompt for calibration use.

This wrapper prompt generates a prompt. It does not score student work.

## Required Input Artefacts (Overview)

Before this wrapper prompt can execute, the following input artefacts must be provided verbatim.

These artefacts correspond to the upstream **rubric construction pipeline** outputs and the calibration run configuration.

All artefacts must use the authoritative grading ontology:

- `submission_id`
- `component_id`
- `dimension_id`
- indicators
- boundary rules

All artefacts must be supplied in full and delimited using `===`.

Required artefacts:

- `CAL_<ASSESSMENT_ID>_<DIMENSION_ID>_Step00_CalibrationPayloadFormat`
- `CAL_<ASSESSMENT_ID>_<DIMENSION_ID>_Step01_dimension_header_v01`
- `CAL_<ASSESSMENT_ID>_<DIMENSION_ID>_Step02_indicators_checklist_v01`
- `CAL_<ASSESSMENT_ID>_<DIMENSION_ID>_Step03_boundary_rules_v01`

If any artefact is missing or inconsistent, the wrapper prompt must produce no output.

## Purpose

- Generate one reusable scoring prompt that assigns provisional scores for a single rubric dimension (`dimension_id`).
- Enforce the supplied indicators and boundary rules as the sole scoring logic.
- Produce diagnostic, non-authoritative outputs intended for calibration analysis.
- Emit structured scoring diagnostics that allow inspection of indicator hits, rule application, and decision boundaries.

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
- rubric modification
- rule invention
- indicator invention
- coaching or pedagogical advice

## Authoritative Inputs (Verbatim)

The model may rely only on the following inputs supplied verbatim and delimited by `===`.

===
Input Artefact  
`CAL_<ASSESSMENT_ID>_<DIMENSION_ID>_Step00_CalibrationPayloadFormat`

Each calibration item will contain exactly:

- `row_id`
- `response_text`

Formatting guarantees:

- `response_text` may include wrapper markers such as `+++`
- a header line of the form `row_id=<value>` may appear and must be ignored
- no additional metadata will be present
- each row must be scored independently
===

===
Input Artefact  
`CAL_<ASSESSMENT_ID>_<DIMENSION_ID>_Step01_dimension_header_v01`

Contents must include:

- `assessment_id`
- `component_id`
- `dimension_id`
- `dimension_label`
- one-sentence definition of what is being scored
- unit of analysis statement (one row = one score for this `dimension_id`)
- evidence rule (explicit-text only; no inference)
===

===
Input Artefact  
`CAL_<ASSESSMENT_ID>_<DIMENSION_ID>_Step02_indicators_checklist_v01`

Contents must include:

- 3–6 observable indicators
- indicators phrased as presence checks
- indicators referencing observable textual evidence
- optional facet tags if facets are used
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
Output Requirements

Allowed output fields include:

- `score`
- `indicator_hits`
- `facet_hits`
- `boundary_checks`
- `rationale`
- `evidence_quote`
- `confidence`
- `flags`
- `feedback`

The user must specify the confidence scale and allowed flags.
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
- explicit evaluation of indicator presence
- evaluation of optional facet sufficiency if facets are defined

If scoring is indeterminate:

- assign the lowest evaluable score label
- include flag `needs_review`

## Failure Mode Handling

If any required artefact is missing, inconsistent, or contradictory:

- produce no output
- wait silently for corrected inputs
===
  
```