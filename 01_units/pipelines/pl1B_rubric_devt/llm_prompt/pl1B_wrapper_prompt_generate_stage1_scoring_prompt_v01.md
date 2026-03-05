this document sets out a WRAPPER PROMPT - which is used to create tightly bounded prompt which can to be used to assign provisional scores.

inputs:
- `<ASSESSMENT_ID>_AssignmentPayloadSpec_v01`
- `CAL_<ASSESSMENT_ID>_<COMPONENT_ID>_Step02_RubricSpec_v01`

# .
```
BEGIN GENERATION
```

# .
````
## pl1B_wrapper_prompt_generate_stage1_scoring_prompt_v02

Wrapper prompt: Generate a tightly bounded **Stage 1 scoring prompt** for **indicator evidence detection**.

This wrapper prompt generates a prompt. It does not score student work.

---

## Required Input Artefacts (Overview)

Before this wrapper prompt can execute, the following input artefacts must be provided verbatim.

These artefacts correspond to the upstream rubric construction pipeline outputs and the canonical assignment payload specification.

All artefacts must use the authoritative grading ontology:

- `participant_id`
- `component_id`
- `dimension_id`
- `indicator_id`
- boundary rules

All artefacts must be supplied in full and delimited using `===`.

Required artefacts:

- `<ASSESSMENT_ID>_AssignmentPayloadSpec_v01`
- `CAL_<ASSESSMENT_ID>_<COMPONENT_ID>_Step02_RubricSpec_v01`

If any artefact is missing or inconsistent, the wrapper prompt must produce no output.

---

## Purpose

Generate one reusable **Stage 1 scoring prompt** that performs **indicator evidence detection**.

The generated prompt must:

- detect indicator presence
- extract supporting textual evidence
- record indicator-level diagnostic information

The generated prompt **must not**:

- determine dimension satisfaction
- evaluate boundary rules
- assign performance levels

Stage 1 functions strictly as an **evidence extraction stage**.

Outputs produced by the Stage 1 prompt will be consumed by Stage 2 for:

- dimension satisfaction evaluation
- boundary rule evaluation
- final performance level assignment.

---

## Task Classification

This wrapper prompt performs:

- prompt synthesis
- rubric constraint propagation
- Stage 1 scoring prompt specification

This wrapper prompt does **not** perform:

- grading or scoring
- dimension evaluation
- boundary rule evaluation
- rubric modification
- rule invention
- indicator invention
- coaching or pedagogical advice

---

## Authoritative Inputs (Verbatim)

The model may rely only on the following inputs supplied verbatim and delimited using `===`.

===

Input Artefact  
`<ASSESSMENT_ID>_AssignmentPayloadSpec_v01`

This artefact defines the canonical payload structure for the assessment.

The model must extract and rely on the following information:

- `assessment_id`
- canonical identifier field `participant_id`
- canonical evidence field `response_text`
- canonical dataset structure
- wrapper-handling rules
- component registry (`component_id` values)
- evidence surfaces associated with each component

Wrapper-handling rules include:

- wrapper markers such as `+++`
- optional header lines such as `row_id=<value>` or similar preprocessing artefacts
- wrapper artefacts must be ignored during evaluation

Evidence rule:

```
explicit-text only; no inference
```

Canonical scoring unit:

```
participant_id × component_id
```

Stage 1 evaluation unit:

```
participant_id × component_id × indicator_id
```

===

===

Input Artefact  
`CAL_<ASSESSMENT_ID>_<COMPONENT_ID>_Step02_RubricSpec_v01`

This artefact defines the authoritative rubric specification for the component.

The model must extract:

- `component_id`
- dimension registry
- indicator definitions
- indicator–dimension mappings
- cross-dimension response-quality indicators

Indicators must be interpreted strictly as **observable presence checks referencing explicit textual evidence**.

Indicator detection must rely only on:

- the response text
- the indicator definitions

Dimension satisfaction rules and boundary rules **must not be executed during Stage 1**.

===

===

Output Requirements

Allowed output fields include:

- `indicator_id`
- `indicator_present`
- `evidence_excerpt`
- `evaluation_notes`
- `confidence`
- `flags`

The user must specify the confidence scale and allowed flags.

===

No external knowledge or interpretation is permitted.

---

## Stage Discipline (Mandatory)

### Stage 1 — Input

- The user provides all required artefacts delimited by `===`.
- The model reads silently.
- No output is generated.

If the message `BEGIN GENERATION` is not present, the model must produce no output.

---

### Stage 2 — Execution

When the user sends `BEGIN GENERATION`, the model generates the Stage 1 scoring prompt artefact.

---

## Output Artefact

The model must generate exactly one artefact:

```
RUN_<ASSESSMENT_ID>_<COMPONENT_ID>_Stage1_indicator_detection_prompt_v01
```

The artefact must:

- reference the correct `component_id`
- assume the canonical payload structure defined in `<ASSESSMENT_ID>_AssignmentPayloadSpec_v01`
- evaluate **all indicators defined in the rubric**
- be reusable across scoring runs

---

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
- Stage 1 evaluation procedure
- Evidence extraction rules
- Output schema
- Constraints
- Content rules
- Failure mode handling

---

## Required Stage 1 Scoring Semantics

The generated scoring prompt must enforce:

- one evaluation per `(participant_id × component_id × indicator_id)`
- explicit evaluation of **all rubric indicators**
- explicit determination of **indicator presence or absence**
- extraction of supporting textual evidence

Stage 1 must **not**:

- determine dimension satisfaction
- interpret indicator combinations
- apply boundary rules
- assign performance levels

If indicator detection is uncertain:

- record the indicator as absent
- include flag `needs_review`

---

## Failure Mode Handling

If any required artefact is missing, inconsistent, or contradictory:

- produce no output
- wait silently for corrected inputs
===

````