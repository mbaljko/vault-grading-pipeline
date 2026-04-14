---
scaffold_id: pl1C_stage13_layer1_indicator_scoring_prompt_scaffold
version: v01
status: stub
output_format: markdown
instantiation_mode: deterministic_token_substitution
required_tokens:
  - ASSESSMENT_ID
  - TARGET_COMPONENT_ID
  - TARGET_INDICATOR_ID
  - SUBMISSION_IDENTIFIER_FIELD
  - EVIDENCE_FIELD_NAME
  - WRAPPER_HANDLING_RULE_BULLETS
  - INDICATOR_ID
  - SBO_SHORT_DESCRIPTION
  - INDICATOR_DEFINITION
  - ASSESSMENT_GUIDANCE
  - EMBEDDED_EVALUATOR_GUIDANCE
optional_tokens:
  - EMBEDDED_DECISION_PROCEDURE_BLOCK
notes: |
  Stub scaffold placeholder for the deterministic Python instantiation path.
  Replace the body below with the canonical scaffold text when provided.
---

# Stub Layer 1 Indicator Scoring Prompt

[[ASSESSMENT_ID]]

[[TARGET_COMPONENT_ID]]

[[TARGET_INDICATOR_ID]]

[[SUBMISSION_IDENTIFIER_FIELD]]

[[EVIDENCE_FIELD_NAME]]

[[WRAPPER_HANDLING_RULE_BULLETS]]

[[INDICATOR_ID]]

[[SBO_SHORT_DESCRIPTION]]

[[INDICATOR_DEFINITION]]

[[ASSESSMENT_GUIDANCE]]

[[EMBEDDED_EVALUATOR_GUIDANCE]]

[[EMBEDDED_DECISION_PROCEDURE_BLOCK]]


````
#### RUN_[[ASSESSMENT_ID]]_[[TARGET_COMPONENT_ID]]_[[TARGET_INDICATOR_ID]]_Layer1_SBO_scoring_prompt_v01

#### Prompt title and restrictions

This prompt performs **Layer 1 SBO scoring** for target component `[[TARGET_COMPONENT_ID]]` and target indicator `[[TARGET_INDICATOR_ID]]`.

It determines the `evidence_status` value for the embedded indicator SBO instance belonging to this component.

This prompt does **not**:

- evaluate dimensions
- evaluate indicator combinations
- apply indicator→dimension mappings
- assign component performance levels
- assign submission scores
- evaluate indicators belonging to other components
- evaluate any indicator other than `[[TARGET_INDICATOR_ID]]`

Layer 1 SBO scoring performs only:

```text
binary indicator presence detection
```

#### Authoritative scoring materials

Assessment identifier:

```text
[[ASSESSMENT_ID]]
```

Target component:

```text
[[TARGET_COMPONENT_ID]]
```

Target indicator:

```text
[[TARGET_INDICATOR_ID]]
```

Canonical scoring unit:

```text
submission_id × component_id × indicator_id
```

Runtime row identifier rule:

- The canonical submission-level identifier field is `[[SUBMISSION_IDENTIFIER_FIELD]]`.
- In output, copy the runtime row value from `[[SUBMISSION_IDENTIFIER_FIELD]]` into the CSV field named `submission_id`.

Canonical evidence field:

```text
[[EVIDENCE_FIELD_NAME]]
```

Evidence rule:

```text
explicit textual evidence only
```

Wrapper-handling rule for the canonical evidence field:

[[WRAPPER_HANDLING_RULE_BULLETS]]

Embedded indicator specification:

| indicator_id | sbo_short_description | indicator_definition | assessment_guidance | embedded evaluator guidance |
|---|---|---|---|---|
| [[INDICATOR_ID]] | [[SBO_SHORT_DESCRIPTION]] | [[INDICATOR_DEFINITION]] | [[ASSESSMENT_GUIDANCE]] | [[EMBEDDED_EVALUATOR_GUIDANCE]] |

Embedded decision procedure for `[[TARGET_INDICATOR_ID]]`:

[[EMBEDDED_DECISION_PROCEDURE_BLOCK]]

Indicator evidence status scale:

| value | meaning |
|---|---|
| `present` | clear, sufficient, explicit textual evidence fully satisfies the indicator definition |
| `not_present` | the indicator is absent or supported only by partial, weak, implicit, incomplete, vague, or ambiguous evidence |

Field rules:

- `evaluation_notes` enclosed in double quotes
- empty notes represented as `""`

Use only:

- the runtime dataset rows
- canonical `[[EVIDENCE_FIELD_NAME]]`
- the embedded indicator definition
- the embedded assessment guidance
- the embedded evaluator guidance derived from the manifest `evaluation_notes` field
- the embedded decision procedure, if present
- the embedded evidence scale

Do not use:

- external knowledge
- dimension reasoning
- performance-level reasoning
- assumptions about intended meaning
- other indicators
- indicator combinations

Require all of the following:

- one CSV row for the embedded indicator **for each valid runtime row**
- complete coverage of all valid runtime rows in the runtime dataset
- `component_id = [[TARGET_COMPONENT_ID]]` in every emitted row
- `indicator_id = [[TARGET_INDICATOR_ID]]` in every emitted row
- concise `evaluation_notes`
- no long quotations unless fragment mode is enabled

Produce no output if:

- the runtime dataset contains no valid runtime rows for the target component
- the CSV header cannot be emitted exactly as specified
- complete row coverage cannot be achieved for all valid runtime rows
- any contradiction prevents deterministic evaluation

#### Input format

Runtime input will contain a dataset with one or more runtime rows.  
Each runtime row represents one submission-level evaluation unit:
[[SUBMISSION_IDENTIFIER_FIELD]] × component_id
Evaluate every runtime row whose component_id equals the target component.  
Do not stop after the first runtime row.

Each runtime row must contain:

- a submission identifier field
- `component_id`
- the canonical evidence field `[[EVIDENCE_FIELD_NAME]]`

For all later instructions in this prompt, the selected field must be treated as the canonical evidence field for that runtime row.

Wrapper handling is applied per runtime row.

#### Evaluation discipline

For each runtime row, evaluate the embedded indicator exactly once.  
For each runtime row, emit one CSV data row.  
Emit rows grouped by runtime row order.  
Emit the CSV header exactly once, before all data rows.

```text
total data row count = number of valid runtime rows
```

##### Runtime Row Coverage Rule

Before writing any output rows, construct the ordered list of valid runtime rows from the runtime dataset.

A valid runtime row is a row whose:

- submission identifier field is present
- `component_id` is present
- the canonical evidence field `[[EVIDENCE_FIELD_NAME]]` is present
- `component_id` equals `[[TARGET_COMPONENT_ID]]`

Do not stop after the first valid runtime row.  
Do not emit output for only a prefix of the runtime dataset.

##### Evaluation Sequence

Layer 1 SBO scoring must follow this exact sequence:

1. Construct a single internal representation of the runtime input dataset.
2. Identify the valid runtime rows whose `component_id = [[TARGET_COMPONENT_ID]]`.
3. For each valid runtime row, treat the field `[[EVIDENCE_FIELD_NAME]]` as the row’s canonical evidence text.
4. Apply wrapper-handling rules to each valid runtime row before evaluation.
5. For each valid runtime row:
  - construct a single internal representation of that row’s canonical evidence text
   - identify candidate supporting fragments for the embedded indicator without inferring unstated meaning
   - if an embedded decision procedure is present, apply it exactly as written
   - evaluate the indicator against the explicit threshold stated in the embedded indicator specification
   - treat partial, weak, implicit, incomplete, vague, or ambiguous matches as `not_present`
   - evaluate using explicit fragment comparison rather than holistic interpretation

##### Indicator Evaluation

For each valid runtime row:

- internally identify whether a supporting textual fragment exists
- evaluate the fragment using the embedded `indicator_definition`
- evaluate the fragment using the embedded `assessment_guidance`
- use the embedded evaluator guidance derived from the manifest `evaluation_notes` field
- if present, apply the embedded decision procedure exactly as written
- assign `evidence_status`
- assign `confidence`
- assign `flags`

##### Evidence Gate Rule

Do **not** assign `present` unless a supporting textual fragment is explicitly present and fully satisfies the embedded indicator threshold.

If no such fragment exists, assign:

```text
not_present
```

If the response contains only partial, weak, implicit, incomplete, vague, or ambiguous evidence, assign:

```text
not_present
```

##### Output Row Count Rule

Before emitting CSV rows, verify that:

```text
number of data rows to be written
=
number of valid runtime rows
```

If counts differ, complete the missing evaluations before emitting output.  
Do not emit partial output.

##### Output Emission Rule

Emit output in this exact structure:

- one CSV header row
- then, for runtime row 1, one data row
- then, for runtime row 2, one data row
- continue until all valid runtime rows are exhausted

#### Evidence interpretation rules

##### Evidence Fragment Output Mode

Default behaviour:

- supporting fragments are identified internally
- fragments are **not printed**
- `evaluation_notes` should normally be empty and emitted as `""`

Optional runtime mode:

```text
FRAGMENT_OUTPUT_MODE = on
```

If enabled, `evaluation_notes` may briefly reference the supporting fragment used to assign the evidence status.

##### Binary Threshold Rule

Presence requires a complete, explicit textual match to the embedded indicator specification.

Do not assign `present` for:

- partial matches
- implied structure
- incomplete structure
- vague mention
- keyword mention without required analytic structure

All such cases must be assigned:

```text
not_present
```

##### Independence Rule

This indicator must be evaluated independently.

Do not use:

- other indicators
- dimension logic
- indicator combinations
- mapping rules
- component expectations

to influence the judgement.

#### Confidence assignment rule

Confidence reflects clarity of the basis for the binary decision, not degree of evidence.

```text
high
the assigned status is clearly supported by explicit textual evidence or by a clear absence of qualifying evidence

medium
the assigned status is determinable, but the boundary is close and should be flagged for review if needed

low
use only when a binary decision is still required but the evidence surface is unusually difficult to parse because of malformed or highly unclear text
```

```text
If evidence_status = not_present because no qualifying fragment exists, assign confidence = high.
If a decision is boundary-close, assign flags = needs_review.
Do not use confidence to introduce partial credit or graded evidence.
```

#### Output schema

Output must be CSV.  
Emit the header row exactly once:

```text
submission_id,component_id,indicator_id,evidence_status,evaluation_notes,confidence,flags
```

In output, `evaluation_notes` refers only to the CSV output field.  
It does not rename or reproduce the manifest `evaluation_notes` field, which serves as embedded evaluator guidance inside the scoring prompt.

Field rules:

- `submission_id` must be copied from the runtime row
- `component_id` must equal `[[TARGET_COMPONENT_ID]]` in every emitted row
- `indicator_id` must equal `[[TARGET_INDICATOR_ID]]` in every emitted row
- `evaluation_notes` must always be enclosed in double quotes
- if `evaluation_notes` is empty, emit `""`
- `confidence` must be one of: `low`, `medium`, `high`
- `flags` must be one of: `none`, `needs_review`
- no additional columns may appear
- no explanatory text may appear before or after the CSV

#### Constraints

Use only:

- the runtime dataset rows
- canonical `response_text`
- the embedded indicator definition
- the embedded assessment guidance
- the embedded evaluator guidance derived from the manifest `evaluation_notes` field
- the embedded decision procedure, if present
- the embedded evidence scale

Do not use:

- external knowledge
- dimension reasoning
- performance-level reasoning
- assumptions about intended meaning
- inferential reconstruction of missing structure

#### Content rules

Require all of the following:

- one CSV row for the embedded indicator **for each valid runtime row**
- complete coverage of all valid runtime rows in the runtime dataset
- `component_id = [[TARGET_COMPONENT_ID]]` in every emitted row
- `indicator_id = [[TARGET_INDICATOR_ID]]` in every emitted row
- concise `evaluation_notes`
- no long quotations unless fragment mode is enabled

#### Failure mode handling

If any artefact or parameter is missing, inconsistent, or contradictory:

- produce **no output**
- wait silently for corrected inputs

If the selected manifest row is:

- missing
- duplicated
- missing evaluation fields

the wrapper prompt must **produce no output**.

Produce no output if:

- the runtime dataset contains no valid runtime rows for the target component
- the CSV header cannot be emitted exactly as specified
- complete row coverage cannot be achieved for all valid runtime rows
- any contradiction prevents deterministic evaluation
````