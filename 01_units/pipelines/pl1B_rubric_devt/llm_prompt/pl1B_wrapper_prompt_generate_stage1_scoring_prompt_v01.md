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
## pl1B_wrapper_prompt_generate_stage1_scoring_prompt_v03

Wrapper prompt: Generate a tightly bounded **Stage 1 scoring prompt** for **indicator evidence detection**.

This wrapper prompt generates a prompt. It does not score student work.

---

## Required Input Artefacts (Overview)

Before this wrapper prompt can execute, the following input artefacts must be provided verbatim.

These artefacts correspond to the upstream rubric construction pipeline outputs and the canonical assignment payload specification.

All artefacts must use the authoritative grading ontology:

- `submission_id`
- `component_id`
- `dimension_id`
- `indicator_id`

All artefacts must be supplied in full and delimited using `===`.

Required artefacts:

- `<ASSESSMENT_ID>_AssignmentPayloadSpec_v01`
- `CAL_<ASSESSMENT_ID>_<COMPONENT_ID>_Step02_RubricSpec_v*`

If any artefact is missing or inconsistent, the wrapper prompt must produce no output.

---

## Purpose

Generate one reusable **Stage 1 scoring prompt** that performs **indicator evidence detection**.

The generated prompt must:

- evaluate indicator evidence using the rubric indicator definitions and assessment guidance
- assign an **evidence status** for each indicator
- record indicator-level diagnostic information

The generated prompt must **not**:

- determine dimension evidence levels
- determine dimension satisfaction
- evaluate boundary rules
- assign submission performance levels

Stage 1 functions strictly as an **indicator evidence determination stage**.

Outputs produced by the Stage 1 prompt will be consumed by Stage 2 for:

- dimension evidence evaluation
- boundary rule evaluation
- final performance level assignment

---

## Task Classification

This wrapper prompt performs:

- prompt synthesis
- rubric constraint propagation
- Stage 1 scoring prompt specification

This wrapper prompt does **not** perform:

- grading or submission scoring
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

### Input Artefact  
`<ASSESSMENT_ID>_AssignmentPayloadSpec_v01`

This artefact defines the canonical payload structure for the assessment.

The model must extract and rely on the following information:

- `assessment_id`
- canonical identifier field `submission_id`
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
submission_id × component_id
```

===

===

### Input Artefact  
`CAL_<ASSESSMENT_ID>_<COMPONENT_ID>_Step02_RubricSpec_v*`

This artefact defines the authoritative rubric specification for the component.

The model must extract the full **indicator registry**, including:

- `indicator_id`
- `indicator_definition`
- `assessment guidance`

This includes both:

- component indicators (e.g., `I1–In`)
- cross-dimension response-quality indicators (e.g., `Q1–Qn`)

Indicator detection must rely only on:

- the response text
- the indicator definition
- the indicator assessment guidance

Indicators must be interpreted strictly as **observable textual evidence checks** referencing explicit textual evidence.

Dimension evidence levels, dimension satisfaction rules, and boundary rules **must not be executed during Stage 1**.

===

---

## Output Requirements

Allowed output fields include:

- `submission_id`
- `component_id`
- `indicator_id`
- `evidence_status`
- `evaluation_notes`
- `confidence`
- `flags`

The user must specify the confidence scale and allowed flags.

### Field formatting rules (mandatory)

The generated Stage 1 scoring prompt must require that:

- `evaluation_notes` is always enclosed in double quotes (`"` ... `"`).
- If `evaluation_notes` is empty, the output must contain an empty quoted string: `""`.
- No other escaping rules are required.

The output produced by the Stage 1 scoring prompt must be machine-parseable under these minimal quoting rules.

No external knowledge or interpretation is permitted.

---
### CSV header row requirement (mandatory)

The generated Stage 1 scoring prompt must require that the CSV output always begins with a header row.

The header row must appear **exactly once**, before any indicator evaluation rows.

The header row must contain the following fields in this exact order:

```
submission_id,component_id,indicator_id,evidence_status,evaluation_notes,confidence,flags
```

The generated prompt must explicitly instruct the model to:

- emit the header row first
- then emit one CSV data row per evaluation unit

The evaluation unit is:

```
submission_id × component_id × indicator_id
```

No additional columns may appear.

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
- evaluate **all indicators defined in the rubric**, including cross-dimension indicators
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
- Evidence interpretation rules
- Output schema
- Constraints
- Content rules
- Failure mode handling

---

## Required Stage 1 Scoring Semantics

The generated scoring prompt must enforce:

- one evaluation per `(submission_id × component_id × indicator_id)`
- explicit evaluation of **all rubric indicators**
- assignment of an **evidence status** for each indicator, using the rubric’s indicator evidence status vocabulary
- deterministic results based on explicit text

The generated scoring prompt must also enforce this evaluation discipline:

- Read `response_text` exactly once.
- Then, in a single evaluation step, determine evidence status for **all** indicators (`I1–In`, `Q1–Qn`) before writing any output.
- Do not re-read or re-scan the text separately per indicator.

Stage 1 must **not**:

- determine dimension evidence levels
- interpret indicator combinations
- apply boundary rules
- assign performance levels

If indicator evidence detection is uncertain:

- assign the indicator the lowest evidence status
- include flag `needs_review`

---

## Failure Mode Handling

If any required artefact is missing, inconsistent, or contradictory:

- produce no output
- wait silently for corrected inputs
===

````