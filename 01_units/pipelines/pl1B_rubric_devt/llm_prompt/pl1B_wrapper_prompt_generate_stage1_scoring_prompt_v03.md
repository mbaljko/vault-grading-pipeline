this document sets out a WRAPPER PROMPT - which is used to create tightly bounded prompt which can to be used to assign provisional scores.

inputs:
- `<ASSESSMENT_ID>_AssignmentPayloadSpec_v01`
- `CAL_<ASSESSMENT_ID>_<COMPONENT_ID>_Step02_RubricSpec_v*`

# .
```
BEGIN GENERATION
```


- `evaluation_notes` must begin with an indicator vector in this exact format: `V=[I1,I2,I3,I4,I5,I6,Q1,Q2]`, where each value is a numeric encoding of the Stage 1 `evidence_status` for that indicator: `0` = `little_to_no_evidence`, `1` = `partial_evidence`, `2` = `evidence`; if any indicator is missing from the evidence map, use `0` and include flag `needs_review`.
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

The model must extract the full **indicator registry** defined in **Section 5**, including:

- `indicator_id`
- `indicator_definition`
- `assessment guidance`

This includes both:

- component indicators (e.g., `I1–In`)
- cross-dimension response-quality indicators (e.g., `Q1–Qn`)

Indicator evidence detection must rely only on:

- the response text
- the indicator definition
- the indicator assessment guidance
- the **indicator evidence status scale** defined in **Section 5.2**

Indicators must be interpreted strictly as **observable textual evidence checks** referencing explicit textual evidence.

The generated Stage 1 scoring prompt must embed the full indicator evidence status scale from Section 5.2 of the rubric specification (the set of allowed `evidence_status` values and their interpretations) so that the Stage 1 prompt is fully executable without requiring the rubric document at runtime.

The following rubric sections must **not** be used during Stage 1:

- dimension evidence levels (Section 3.2)
- indicator → dimension mapping tables (Section 6)
- dimension → submission score rules (Section 7)
- boundary rules (Section 8)

Stage 1 determines only the **indicator evidence status** for each indicator.
No dimension-level or submission-level reasoning may occur during this stage.

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

confidence must be one of: 0.25, 0.5, 0.75, 1.0

flags must be one of: none, needs_review

The field `evidence_status` must contain exactly one of the values defined in the rubric evidence scale:
`evidence`, `partial_evidence`, or `little_to_no_evidence`.


`evaluation_notes` should begin with an indicator vector in this exact format: `V=[I1,I2,I3,I4,I5,I6,Q1,Q2]`, where each value is a numeric encoding of the Stage 1 `evidence_status` for that indicator: `0` = `little_to_no_evidence`, `1` = `partial_evidence`, `2` = `evidence`; if any indicator is missing from the evidence map, use `0` and include flag `needs_review`.

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
RUN_<ASSESSMENT_ID>_<COMPONENT_ID>_Stage1_indicator_detection_prompt_v03
```

The artefact must:

- reference the correct `component_id`
- assume the canonical payload structure defined in `<ASSESSMENT_ID>_AssignmentPayloadSpec_v01`
- evaluate **all indicators defined in the rubric**, including cross-dimension indicators
- be reusable across scoring runs

---

## Generated Scoring Prompt Structure

The generated scoring prompt must:

- appear in a single fenced Markdown block, outer fence ````
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
  
Before evaluating any indicator, the evaluator must first construct the complete ordered list of `indicator_id` values defined in the rubric indicator registry. 
Evidence status must then be assigned exactly once for **every `indicator_id` in that list**, and the number of emitted evaluation rows must equal the number of indicators in the registry. 
  
- assignment of an **indicator evidence status** for each indicator, using the evidence status scale defined in Section 5.2 of the rubric
  
- If the response contains **any clearly relevant interpretable textual fragment that partially satisfies an indicator definition but lacks the full conditions required for `evidence`, the status must be assigned `partial_evidence` rather than `little_to_no_evidence`.
  
- If the response contains explicit textual material that **clearly satisfies all conditions stated in the indicator definition**, the status may be assigned `evidence`; otherwise the status must not exceed `partial_evidence`.
  
- deterministic results based on explicit text

The generated scoring prompt must also enforce this evaluation discipline:

- Construct a single internal representation of the full `response_text` and use that representation when evaluating all indicators.
- Then, in a single evaluation step, determine evidence status for **all** indicators (`I1–In`, `Q1–Qn`) before writing any output.
- Do not re-read or re-scan the text separately per indicator.
  

After determining the evidence status for **all indicators**, the prompt must then emit one output row for each `(submission_id × component_id × indicator_id)` combination.
  
Stage 1 evaluates indicators independently.

Indicator evidence status must be determined without considering:

- other indicators
- dimension definitions
- indicator combinations
- mapping table rows

Stage 1 must **not**:

- determine dimension evidence levels
- interpret indicator combinations
- apply boundary rules
- assign performance levels

If indicator evidence detection is uncertain:

- assign the status `little_to_no_evidence`
- include flag `needs_review`

---

## Failure Mode Handling

If any required artefact is missing, inconsistent, or contradictory:

- produce no output
- wait silently for corrected inputs
===

````