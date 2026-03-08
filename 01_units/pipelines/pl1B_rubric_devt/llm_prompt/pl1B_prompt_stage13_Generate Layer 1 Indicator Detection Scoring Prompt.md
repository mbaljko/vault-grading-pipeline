# .
```
BEGIN GENERATION
```


three inputs
`<ASSESSMENT_ID>_AssignmentPayloadSpec_v01`
`Rubric Template: 5.4 Layer 1 SBO Instances`
`Rubric Template: 6.1 Layer 1 SBO Value Derivation`
# . 
````
## Wrapper Prompt — Generate Layer 1 Indicator Detection Scoring Prompt (Stage 1.3)

Generate a tightly bounded **Layer 1 scoring prompt** for **Layer 1 indicator evidence detection** under the **Rubric Template architecture**.

This wrapper prompt **generates a scoring prompt**.  
It **does not evaluate student work**.

The generated scoring prompt will evaluate **indicator evidence only** using the **Layer 1 rubric specification**.

---

## Required Input Artefacts (Overview)

Before this wrapper prompt can execute, the following artefacts must be supplied **verbatim** and delimited using:

```
===
<content>
===
```

Required artefacts:

```
<ASSESSMENT_ID>_AssignmentPayloadSpec_v01
Rubric Template: 5.4 Layer 1 SBO Instances
Rubric Template: 6.1 Layer 1 SBO Value Derivation
```

If any artefact is missing, malformed, or inconsistent, the wrapper prompt must **produce no output**.

---

## Purpose

Generate a reusable **Stage 1 scoring prompt** that performs **Layer 1 indicator evidence detection**.

The generated prompt must:

- evaluate indicator evidence using the **indicator registry (5.4)**
- apply the **indicator evaluation specification (6.1)**
- assign an **indicator evidence status**
- record indicator-level diagnostic notes

The generated prompt must **not**:

- evaluate dimension evidence
- evaluate indicator combinations
- determine dimension satisfaction
- apply mapping rules
- assign component performance levels
- assign submission scores

Stage 1 operates strictly as an **indicator evidence detection stage**.

Outputs produced by the Stage 1 prompt will later be consumed by:

```
Stage 2 — Dimension Evidence Derivation
Stage 3 — Component Performance Mapping
Stage 4 — Submission Score Derivation
```

---

## Task Classification

This wrapper prompt performs:

- prompt synthesis
- rubric constraint propagation
- Stage 1 scoring prompt specification

This wrapper prompt does **not** perform:

- grading
- scoring
- rubric modification
- indicator invention
- rule invention
- pedagogical explanation

---

## Authoritative Inputs (Verbatim)

The model may rely **only** on the following artefacts supplied verbatim.

---

### Input Artefact  
`<ASSESSMENT_ID>_AssignmentPayloadSpec_v01`

This artefact defines the canonical grading dataset.

The wrapper must extract:

- `assessment_id`
- canonical identifier field `submission_id`
- canonical identifier field `component_id`
- canonical evidence surface `response_text`
- canonical dataset structure

Canonical scoring unit:

```
submission_id × component_id
```

Evidence rule:

```
explicit textual evidence only
```

Wrapper artefacts such as preprocessing headers or markers must be ignored.

---

### Input Artefact  
`Rubric Template: 5.4 Layer 1 SBO Instances`

This section defines the **Layer 1 indicator registry**.

The wrapper must extract:

```
sbo_identifier
component_id
indicator_id
sbo_short_description
```

These fields define **the complete ordered set of indicators that must be evaluated**.

No indicators may be invented or omitted.

---

### Input Artefact  
`Rubric Template: 6.1 Layer 1 SBO Value Derivation`

This section defines the **indicator evaluation specification**.

For each indicator the wrapper must extract:

```
indicator_definition
assessment_guidance
evaluation_notes
```

These fields define **how the indicator signal appears in response text**.

The generated scoring prompt must embed these specifications so that the scoring prompt is **fully executable without access to the rubric document**.

---

## Indicator Evidence Status Scale

The generated scoring prompt must embed the following **indicator evidence scale**:

| value | meaning |
|---|---|
| `evidence` | explicit textual evidence clearly satisfies the indicator definition |
| `partial_evidence` | some textual signal relevant to the indicator is present but incomplete |
| `little_to_no_evidence` | no interpretable textual signal supporting the indicator is present |

The scoring prompt must enforce:

- explicit textual grounding
- deterministic interpretation
- no inference beyond the response text

---

## Output Requirements

Allowed output fields:

```
submission_id
component_id
indicator_id
evidence_status
evaluation_notes
confidence
flags
```

Allowed values:

```
confidence ∈ {low, medium, high}
flags ∈ {none, needs_review}
```

Evidence status must be one of:

```
evidence
partial_evidence
little_to_no_evidence
```

---

### Field Formatting Rules

The generated scoring prompt must require:

- `evaluation_notes` always enclosed in double quotes
- empty notes represented as `""`

No additional quoting or escaping rules are required.

---

### CSV Header Row Requirement

The generated scoring prompt must enforce that output **always begins with the header row**:

```
submission_id,component_id,indicator_id,evidence_status,evaluation_notes,confidence,flags
```

The header must appear **exactly once**.

Each subsequent row represents:

```
submission_id × component_id × indicator_id
```

No additional columns may appear.

---

## Stage Discipline

### Stage 1 — Input

The user provides all artefacts delimited by `===`.

The model reads the artefacts silently.

No output is produced.

If the message:

```
BEGIN GENERATION
```

is not present, the wrapper prompt must produce **no output**.

---

### Stage 2 — Execution

When the user sends:

```
BEGIN GENERATION
```

the wrapper generates the **Stage 1 scoring prompt**.

---

## Output Artefact

The wrapper must produce exactly one artefact:

```
RUN_<ASSESSMENT_ID>_<COMPONENT_ID>_Stage1_indicator_detection_prompt_v04
```

The artefact must:

- reference the correct `component_id`
- embed all indicator definitions
- embed all evaluation guidance
- assume the canonical payload structure
- be reusable across scoring runs

---

## Generated Scoring Prompt Structure

The generated scoring prompt must:

- appear in **one fenced Markdown block**
- use **four backticks as the outer fence**
- use headings **no deeper than level 2**
- use **bullet lists only**

Sections must appear in this order:

```
Prompt title and restrictions
Authoritative scoring materials
Input format
Stage 1 evaluation procedure
Evidence interpretation rules
Output schema
Constraints
Content rules
Failure mode handling
```

---

## Required Scoring Semantics

The generated scoring prompt must enforce:

- exactly **one evaluation per**

```
submission_id × component_id × indicator_id
```

- evaluation of **all indicators defined in Section 5.4**

Before evaluating indicators the evaluator must:

1. construct the ordered indicator list from the registry
2. ensure every indicator is evaluated exactly once

The number of output rows must equal the number of indicators.

---

### Evaluation Discipline

The generated scoring prompt must enforce:

- build a single internal representation of `response_text`
- evaluate **all indicators using that single representation**
- determine evidence status for all indicators **before writing output**

The scoring prompt must **not**:

- evaluate indicators sequentially by rescanning the text
- perform dimension reasoning
- interpret indicator combinations
- apply mapping rules

Stage 1 evaluates indicators **independently**.

---

### Evidence Status Assignment Rules

The generated prompt must enforce:

- assign `evidence` only when the response text **clearly satisfies the indicator definition**
- assign `partial_evidence` when **some relevant signal is present but incomplete**
- assign `little_to_no_evidence` when **no relevant signal is present**

If uncertain:

```
evidence_status = little_to_no_evidence
flags = needs_review
```

---

## Failure Mode Handling

If any required artefact is missing, inconsistent, or contradictory:

- produce **no output**
- wait silently for corrected inputs
````