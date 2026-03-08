# .
```
BEGIN GENERATION
```


these inputs
```
===
PARAM_TARGET_COMPONENT_ID = SectionBResponse
===
<PPP_AssignmentPayloadSpec_v01 contents>
===
<Layer1_ScoringManifest_PPP_v01 contents>
===
```

# . 
````
## Wrapper Prompt — Generate Layer 1 Indicator Detection Scoring Prompt (Stage 1.3)

Wrapper prompt: Generate a tightly bounded **Layer 1 SBO scoring prompt** for **indicator evidence detection** using the **Layer1 scoring manifest** under the **Rubric Template architecture**.

This wrapper prompt **generates a scoring prompt**.  
It **does not evaluate student work**.

The generated scoring prompt performs **Layer 1 SBO scoring**, which determines `evidence_status` values for the indicator SBO instances belonging to one target component.

---

## Target Component Parameter (Required)

The wrapper prompt requires the user to specify the component whose Layer-1 indicators will be scored.

```
PARAM_TARGET_COMPONENT_ID = <COMPONENT_ID>
```

Example:

```
PARAM_TARGET_COMPONENT_ID = SectionBResponse
```

This parameter determines which rows from the **Layer1 scoring manifest** will be embedded in the generated scoring prompt.

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
Layer1_ScoringManifest_<ASSESSMENT_ID>_v<VERSION>
```

Required wrapper parameter:

```
PARAM_TARGET_COMPONENT_ID
```

If any artefact or parameter is missing, malformed, or inconsistent, the wrapper prompt must **produce no output**.

---

## Input Artefact Order (Mandatory)

Artefacts must appear **exactly in the following order**.

```
1
===
PARAM_TARGET_COMPONENT_ID = <COMPONENT_ID>
===

2
===
<ASSESSMENT_ID>_AssignmentPayloadSpec_v01
===

3
===
Layer1_ScoringManifest_<ASSESSMENT_ID>_v<VERSION>
===
```

Example invocation:

```
===
PARAM_TARGET_COMPONENT_ID = SectionBResponse
===
<PPP_AssignmentPayloadSpec_v01 contents>
===
<Layer1_ScoringManifest_PPP_v01 contents>
===
BEGIN GENERATION
```

If the artefacts appear in a different order, the wrapper prompt must **produce no output**.

---

## Purpose

Generate a reusable **Layer 1 SBO scoring prompt** that performs **indicator evidence detection**.

The generated prompt must:

- evaluate indicator evidence using the **Layer 1 scoring manifest**
- apply the **indicator evaluation specification embedded in the manifest**
- assign an `evidence_status` value for each indicator SBO instance belonging to the target component
- record indicator-level diagnostic information
- remain fully executable without requiring the rubric document at scoring runtime

The generated prompt must **not**:

- evaluate dimensions
- evaluate indicator combinations
- apply indicator→dimension mappings
- assign component performance levels
- assign submission scores
- evaluate indicators belonging to other components

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
- manifest constraint propagation
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

If the assignment payload specification defines wrapper-handling rules for `response_text`, the generated scoring prompt must embed those rules and require that wrapper artefacts be ignored during evidence evaluation.

---

### Input Artefact  
`Layer1_ScoringManifest_<ASSESSMENT_ID>_v<VERSION>`

This artefact is the authoritative **Layer 1 scoring manifest**.

The wrapper must extract the following fields:

```
component_id
sbo_identifier
indicator_id
sbo_short_description
indicator_definition
assessment_guidance
evaluation_notes
```

The manifest defines:

```
the complete registry of Layer 1 indicator SBO instances
the evaluation specification used to detect them
```

---

## Manifest Filtering Rule

Before generating the scoring prompt, the wrapper must perform the following operation:

```
filter Layer1_ScoringManifest
where component_id = PARAM_TARGET_COMPONENT_ID
```

The resulting filtered table defines:

```
the complete ordered set of indicator SBO instances
to be evaluated by the scoring prompt
```

Validation rules:

- If the filtered table is empty → **produce no output**
- If duplicate `indicator_id` values appear → **produce no output**

Only the filtered rows may be embedded in the generated scoring prompt.

No indicators may be invented, omitted, or imported from outside the filtered manifest rows.

---

## Indicator Evidence Status Scale

The generated scoring prompt must embed the following scale.

| value | meaning |
|---|---|
| `evidence` | explicit textual evidence clearly satisfies the indicator definition |
| `partial_evidence` | some explicit textual signal relevant to the indicator is present but incomplete |
| `little_to_no_evidence` | no interpretable explicit textual signal supporting the indicator is present |

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
RUN_<ASSESSMENT_ID>_<PARAM_TARGET_COMPONENT_ID>_Layer1_SBO_scoring_prompt_v01
```

The artefact must:

- reference the specified `PARAM_TARGET_COMPONENT_ID`
- embed the filtered indicator registry for that component
- embed the evaluation specification rows for that component
- assume the canonical payload structure
- be reusable across scoring runs

---

## Generated Scoring Prompt Structure

The generated scoring prompt must:

- appear in **one fenced Markdown block**
- use **four backticks as the outer fence**
- use headings no deeper than **level 2**
- use bullet lists only

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
- Apply any wrapper-handling rules from the assignment payload specification.
- Construct the ordered list of `indicator_id` values from the filtered manifest rows.
- For each indicator SBO instance:
  - internally identify whether a relevant textual fragment exists
  - evaluate the fragment using `indicator_definition` and `assessment_guidance`
  - assign `evidence_status`
  - assign `confidence`
- Emit one CSV row for that indicator.

The evaluator must **not assign `evidence` or `partial_evidence` without first identifying a supporting fragment of text internally**.

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

---

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

### Partial-Evidence Preference Rule

If the response contains any clearly relevant explicit textual signal that partially satisfies an indicator definition but does not fully satisfy the definition, assign:

```
partial_evidence
```

Do not collapse weak but relevant explicit evidence into `little_to_no_evidence`.

---

### Independence Rule

Indicators must be evaluated independently.

Do not use:

- other indicators
- indicator combinations
- dimension definitions
- mapping logic
- component-level expectations

to strengthen or weaken an indicator judgement.

---

## Confidence Assignment Rule

Confidence must be derived from the clarity of the explicit textual evidence used to determine `evidence_status`.

Do not estimate probabilities.

Assign confidence using the following interpretation:

```
high
- clear explicit language directly supports the assigned status

medium
- explicit language is present but the match is incomplete, qualified, or somewhat ambiguous

low
- weak or ambiguous explicit signal, or reviewer uncertainty remains despite a decision
```

Confidence must be assigned **after `evidence_status`**.

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

- evaluation of **all indicators defined in the filtered component manifest**

Before evaluation begins the evaluator must:

- construct the ordered list of `indicator_id` values from the manifest
- ensure each indicator is evaluated exactly once

The number of output rows must equal the number of embedded indicators.

All emitted rows must contain:

```
component_id = PARAM_TARGET_COMPONENT_ID
```

Layer 1 scoring must **not**:

- evaluate dimensions
- interpret indicator combinations
- apply mapping rules
- assign component scores
- score indicators belonging to other components

If the evaluator is uncertain and cannot identify sufficient explicit support for `evidence` or `partial_evidence`, assign:

```
evidence_status = little_to_no_evidence
flags = needs_review
```

---

## Constraints

The generated scoring prompt must require the evaluator to use only:

- the runtime input row
- the canonical `response_text`
- the embedded manifest rows for the target component
- the embedded evidence scale

The evaluator must not use:

- external knowledge
- inferred course intent beyond the embedded materials
- dimension logic
- performance-level reasoning
- assumptions about what the student probably meant if not stated explicitly

---

## Content Rules

The generated scoring prompt must require:

- one CSV data row per embedded indicator
- `component_id` in every row must equal `PARAM_TARGET_COMPONENT_ID`
- `indicator_id` values must appear in manifest order
- `evaluation_notes` must remain concise
- `evaluation_notes` must not include long quotations unless `FRAGMENT_OUTPUT_MODE = on`

---

## Failure Mode Handling

If any required artefact or parameter is missing, inconsistent, or contradictory:

- produce **no output**
- wait silently for corrected inputs

If the filtered manifest contains:

- no rows
- duplicate `indicator_id` values
- missing evaluation specification fields

the wrapper prompt must **produce no output**.
===
````