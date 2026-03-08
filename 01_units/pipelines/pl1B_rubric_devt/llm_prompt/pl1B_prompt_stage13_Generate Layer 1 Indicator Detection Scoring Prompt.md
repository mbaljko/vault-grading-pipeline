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

Wrapper prompt: Generate a tightly bounded **Layer 1 SBO scoring prompt** for **indicator evidence detection** under the **Rubric Template architecture**.

This wrapper prompt **generates a scoring prompt**.  
It **does not evaluate student work**.

The generated scoring prompt performs **Layer 1 SBO scoring**, which determines **indicator evidence_status values** for each indicator SBO instance.

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

Generate a reusable **Layer 1 SBO scoring prompt** that performs **indicator evidence detection**.

The generated prompt must:

- evaluate indicator evidence using the **indicator SBO registry (Section 5.4)**
- apply the **indicator evaluation specification (Section 6.1)**
- assign an **indicator evidence_status value**
- record indicator-level diagnostic information

The generated prompt must **not**:

- evaluate dimensions
- evaluate indicator combinations
- apply indicator→dimension mappings
- assign component performance levels
- assign submission scores

Layer 1 SBO scoring performs only:

```
indicator evidence detection
```

Outputs produced by the Layer 1 scoring prompt will later be consumed by:

```
Layer 2 — Dimension Evidence Derivation
Layer 3 — Component Performance Mapping
Layer 4 — Submission Score Derivation
```

---

## Task Classification

This wrapper prompt performs:

- prompt synthesis
- rubric constraint propagation
- Layer 1 scoring prompt specification

This wrapper prompt does **not** perform:

- grading
- submission scoring
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

```
assessment_id
submission_id
component_id
response_text
```

Canonical scoring unit:

```
submission_id × component_id
```

Evidence rule:

```
explicit textual evidence only
```

---

### Input Artefact  
`Rubric Template: 5.4 Layer 1 SBO Instances`

This section defines the **Layer 1 indicator SBO registry**.

The wrapper must extract:

```
sbo_identifier
component_id
indicator_id
sbo_short_description
```

These fields define the **complete ordered set of indicators** that must be evaluated.

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

The generated scoring prompt must embed these specifications so that the scoring prompt is **fully executable without the rubric document**.

---

## Indicator Evidence Status Scale

The generated scoring prompt must embed the following scale:

| value | meaning |
|---|---|
| `evidence` | explicit textual evidence clearly satisfies the indicator definition |
| `partial_evidence` | some textual signal relevant to the indicator is present but incomplete |
| `little_to_no_evidence` | no interpretable textual signal supporting the indicator is present |

Evidence must be grounded strictly in **explicit response language**.

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

---

### Field Formatting Rules

The generated scoring prompt must require:

- `evaluation_notes` enclosed in double quotes
- empty notes represented as `""`

No additional quoting or escaping rules are required.

---

### CSV Header Row Requirement

The generated scoring prompt must require that output **always begins with the header row**:

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

## Wrapper Execution Discipline

### Phase 1 — Artefact ingestion

The user supplies the required artefacts delimited by `===`.

The wrapper prompt reads the artefacts silently.

No output is produced.

If the message

```
BEGIN GENERATION
```

is not present, the wrapper prompt must produce **no output**.

---

### Phase 2 — Prompt generation

When the user sends:

```
BEGIN GENERATION
```

the wrapper prompt generates the **Layer 1 SBO scoring prompt artefact**.

---

## Output Artefact

The wrapper must generate exactly one artefact:

```
RUN_<ASSESSMENT_ID>_<COMPONENT_ID>_Layer1_SBO_scoring_prompt_v01
```

The artefact must:

- reference the correct `component_id`
- embed the full indicator registry
- embed the full evaluation specification
- assume the canonical payload structure
- be reusable across scoring runs

---

## Generated Scoring Prompt Structure

The generated scoring prompt must:

- appear in **one fenced Markdown block**
- use **four backticks as the outer fence**
- use headings no deeper than **level 2**
- use **bullet lists only**

Sections must appear in this order:

```
Prompt title and restrictions
Authoritative scoring materials
Input format
Evaluation discipline
Evidence interpretation rules
Confidence assignment rule
Output schema
Constraints
Content rules
Failure mode handling
```

---

## Evaluation Discipline

Layer 1 SBO scoring must follow this sequence:

- Construct a single internal representation of `response_text`.
- For each indicator SBO instance, internally locate any textual fragment relevant to the indicator definition.
- Evaluate the fragment using `indicator_definition` and `assessment_guidance`.
- Assign `evidence_status`.
- Assign `confidence`.

The evaluator must **not assign evidence or partial_evidence without first identifying a supporting fragment of text**.

If no relevant textual fragment exists, the status must be:

```
little_to_no_evidence
```

---

## Evidence Interpretation Rules

### Evidence Gate Rule

Before assigning `evidence_status`, the evaluator must internally identify a fragment of `response_text` that supports the decision.

Evaluation constraints:

- Evidence must be grounded in explicit response language.
- Do not assign `evidence` or `partial_evidence` based only on implication or interpretation.
- If no supporting fragment exists, assign:

```
little_to_no_evidence
```

### Evidence Fragment Output Mode

Default behaviour:

- The evaluator must internally identify the fragment supporting the decision.
- The fragment must **not appear in the output**.

Optional future mode:

If the runtime instruction

```
FRAGMENT_OUTPUT_MODE = on
```

appears, `evaluation_notes` must briefly reference the textual fragment that supported the decision.

Otherwise, `evaluation_notes` may summarise the reasoning without quoting the fragment.

---

## Confidence Assignment Rule

Confidence must be derived from the clarity of the textual evidence used to determine `evidence_status`.

Do not estimate probabilities.

Assign confidence using the following interpretation:

```
high
- clear explicit language directly satisfies the indicator definition

medium
- language plausibly related to the indicator but incomplete or indirect

low
- weak or ambiguous signal
```

Confidence must be assigned **after evidence_status**.

If:

```
evidence_status = little_to_no_evidence
```

and no relevant textual fragment exists in the response, assign:

```
confidence = high
```

---

## Required Layer 1 Scoring Semantics

The scoring prompt must enforce:

- exactly one evaluation for each

```
submission_id × component_id × indicator_id
```

- evaluation of **all indicators defined in the registry**

Before evaluation begins the evaluator must:

- construct the ordered list of `indicator_id` values from the registry
- ensure each indicator is evaluated exactly once

The number of output rows must equal the number of indicators.

Indicators must be evaluated **independently**.

Layer 1 scoring must **not**:

- evaluate dimensions
- interpret indicator combinations
- apply mapping rules
- assign component scores

If the evaluator is uncertain:

```
evidence_status = little_to_no_evidence
flags = needs_review
```

---

## Failure Mode Handling

If any required artefact is missing, inconsistent, or contradictory:

- produce **no output**
- wait silently for corrected inputs
===
````