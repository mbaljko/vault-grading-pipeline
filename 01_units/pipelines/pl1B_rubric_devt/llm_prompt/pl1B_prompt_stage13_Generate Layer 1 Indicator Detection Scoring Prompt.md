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

Wrapper prompt: Generate a tightly bounded **Layer 1 SBO scoring prompt** for **indicator evidence detection** using the **Layer 1 scoring manifest** under the **Rubric Template architecture**.

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

## Required Input Artefacts

All required artefacts must be supplied **verbatim** and delimited using:

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

Required parameter:

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
- embed the **indicator evaluation specification contained in the manifest**
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

## Authoritative Inputs

The model may rely **only** on the following artefacts supplied verbatim.

### Input Artefact  
`<ASSESSMENT_ID>_AssignmentPayloadSpec_v01`

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

If wrapper-handling rules exist for `response_text`, they must be embedded in the generated scoring prompt.

---

### Input Artefact  
`Layer1_ScoringManifest_<ASSESSMENT_ID>_v<VERSION>`

The wrapper must extract:

```
component_id
sbo_identifier
indicator_id
sbo_short_description
indicator_definition
assessment_guidance
evaluation_notes
```

This manifest defines both:

```
the registry of Layer 1 indicators
the evaluation specification used to detect them
```

---

## Manifest Filtering Rule

Before generating the scoring prompt, the wrapper must execute:

```
filter Layer1_ScoringManifest
where component_id = PARAM_TARGET_COMPONENT_ID
```

Validation rules:

- if the filtered table is empty → **produce no output**
- if duplicate `indicator_id` values appear → **produce no output**

Only filtered rows may be embedded in the generated scoring prompt.

---

## Indicator Evidence Status Scale

The generated scoring prompt must embed this scale.

| value | meaning |
|---|---|
| `evidence` | explicit textual evidence clearly satisfies the indicator definition |
| `partial_evidence` | explicit textual signal relevant to the indicator exists but is incomplete |
| `little_to_no_evidence` | no interpretable explicit textual signal supporting the indicator is present |

Evidence must rely strictly on **explicit response language**.

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

### Field Formatting Rules

The scoring prompt must require:

- `evaluation_notes` enclosed in double quotes
- empty notes represented as `""`

---

### CSV Header Requirement

Output must begin with the header row:

```
submission_id,component_id,indicator_id,evidence_status,evaluation_notes,confidence,flags
```

The header appears **exactly once**.

Each subsequent row represents:

```
submission_id × component_id × indicator_id
```

---

## Wrapper Execution Discipline

### Phase 1 — Artefact ingestion

The wrapper reads artefacts silently.

If

```
BEGIN GENERATION
```

is absent, produce **no output**.

### Phase 2 — Prompt generation

When

```
BEGIN GENERATION
```

appears, generate the scoring prompt artefact.

---

## Output Artefact

Generate exactly one artefact:

```
RUN_<ASSESSMENT_ID>_<PARAM_TARGET_COMPONENT_ID>_Layer1_SBO_scoring_prompt_v01
```

The artefact must:

- reference `PARAM_TARGET_COMPONENT_ID`
- embed the filtered indicator rows
- embed the evaluation specification
- assume the canonical payload structure

---

## Generated Scoring Prompt Structure

The scoring prompt must appear in **one fenced Markdown block** (outer fence ````).

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

### Indicator Coverage Rule

Before writing any output rows, construct the ordered list of `indicator_id`
values embedded in the prompt.

Ensure that:

- each `indicator_id` is evaluated exactly once
- indicators are processed in the order embedded in the prompt

### Evaluation Sequence

Layer 1 SBO scoring must follow this sequence:

- Construct a single internal representation of `response_text`.
- Apply any wrapper-handling rules from the assignment payload specification.
- Construct the ordered `indicator_id` list embedded in the prompt.

### Evidence Index Rule

After constructing the internal representation of `response_text`,
scan the response once and identify any textual fragments potentially
relevant to the indicator definitions.

Store these fragments in an internal evidence index.

All indicators must then be evaluated using this evidence index rather
than rescanning the full response text.

### Analytic Signal Pass Rule

After building the internal evidence index, perform one internal analytic
signal pass over the indexed fragments.

In that pass, organise the indexed evidence into a small set of candidate
signal groupings relevant to the target component.

Then evaluate all `indicator_id` values against those internal signal
groupings rather than re-matching each indicator independently from scratch.

### Indicator Evaluation

For each `indicator_id` in prompt order:

- internally identify whether a relevant textual fragment exists
- evaluate the fragment using `indicator_definition` and `assessment_guidance`
- assign `evidence_status`
- assign `confidence`

### Evidence Gate Rule

Do **not** assign `evidence` or `partial_evidence` without internally
identifying a supporting textual fragment.

If no relevant fragment exists, the status must be:

```
little_to_no_evidence
```

### Output Row Count Rule

Before emitting CSV rows, verify that the number of rows to be written
equals the number of `indicator_id` values embedded in the prompt.

If counts differ, complete the missing evaluations before emitting output.

### Output Emission

- Emit one CSV row for each `indicator_id` in prompt order.
- Each row corresponds to exactly one  
  `submission_id × component_id × indicator_id` evaluation.

---

## Evidence Interpretation Rules

### Evidence Fragment Output Mode

Default behaviour:

- supporting fragments are identified internally
- fragments are **not printed**

Optional runtime mode:

```
FRAGMENT_OUTPUT_MODE = on
```

If enabled, `evaluation_notes` may briefly reference the supporting fragment.

---

### Partial Evidence Preference Rule

If explicit language partially satisfies an indicator definition but does not
fully satisfy it, assign:

```
partial_evidence
```

Do not collapse weak but relevant explicit evidence into `little_to_no_evidence`.

---

### Independence Rule

Indicators must be evaluated independently.

Do not use:

- other indicators
- dimension logic
- indicator combinations
- mapping rules
- component expectations

to influence the judgement.

---

## Confidence Assignment Rule

Confidence reflects **clarity of textual evidence**, not probability.

```
high
clear explicit language supports the assigned status

medium
explicit language present but incomplete or ambiguous

low
weak or uncertain textual signal
```

If

```
evidence_status = little_to_no_evidence
```

and no fragment exists, assign:

```
confidence = high
```

---

## Constraints

The evaluator must use only:

- runtime dataset row
- canonical `response_text`
- embedded indicator definitions
- embedded evidence scale

The evaluator must not use:

- external knowledge
- dimension reasoning
- performance level reasoning
- assumptions about intended meaning

---

## Content Rules

The scoring prompt must require:

- one CSV row per indicator
- `component_id = PARAM_TARGET_COMPONENT_ID` in every row
- indicators emitted in prompt order
- concise `evaluation_notes`
- no long quotations unless fragment mode is enabled

---

## Failure Mode Handling

If any artefact or parameter is missing, inconsistent, or contradictory:

- produce **no output**
- wait silently for corrected inputs

If the filtered manifest contains:

- no rows
- duplicate `indicator_id`
- missing evaluation fields

the wrapper prompt must **produce no output**.
===
````