---
scaffold_id: pl1C_stage13_layer0_segmentation_prompt_scaffold
version: v01
status: stub
output_format: markdown
instantiation_mode: deterministic_token_substitution
required_tokens:
	- ASSESSMENT_ID
	- TARGET_COMPONENT_ID
	- TARGET_OPERATOR_ID
	- CANONICAL_SEGMENT_ID
	- SUBMISSION_IDENTIFIER_FIELD
	- WRAPPER_HANDLING_RULE_BULLETS
	- OPERATOR_ID
	- SBO_SHORT_DESCRIPTION
	- OPERATOR_DEFINITION
	- OPERATOR_GUIDANCE
	- FAILURE_MODE_GUIDANCE
optional_tokens:
	- EMBEDDED_DECISION_PROCEDURE_BLOCK
notes: |
	Stub scaffold placeholder for the deterministic Layer 0 segmentation path.
	Replace the body below with the canonical scaffold text when provided.
---

# Stub Layer 0 Segmentation Prompt

[[ASSESSMENT_ID]]

[[TARGET_COMPONENT_ID]]

[[TARGET_OPERATOR_ID]]

[[CANONICAL_SEGMENT_ID]]

[[SUBMISSION_IDENTIFIER_FIELD]]

[[WRAPPER_HANDLING_RULE_BULLETS]]

[[OPERATOR_ID]]

[[SBO_SHORT_DESCRIPTION]]

[[OPERATOR_DEFINITION]]

[[OPERATOR_GUIDANCE]]

[[FAILURE_MODE_GUIDANCE]]

[[EMBEDDED_DECISION_PROCEDURE_BLOCK]]


````
#### RUN_[[ASSESSMENT_ID]]_[[TARGET_COMPONENT_ID]]_[[TARGET_OPERATOR_ID]]_Layer0_segmentation_prompt_v01

#### Prompt title and restrictions

This prompt performs **Layer 0 segmentation** for target component `[[TARGET_COMPONENT_ID]]` and target operator `[[TARGET_OPERATOR_ID]]`.

It determines the extraction output for the embedded operator SBO instance belonging to this component.

This prompt does **not**:

- evaluate Layer 1 indicators
- assign evidence_status values such as `present` or `not_present`
- aggregate evidence into dimensions
- assign component performance levels
- assign submission scores
- evaluate operators belonging to other components
- execute any operator other than `[[TARGET_OPERATOR_ID]]`

Layer 0 segmentation performs only:

```text
bounded text extraction and extraction-status assignment
```

#### Authoritative segmentation materials

Assessment identifier:

```text
[[ASSESSMENT_ID]]
```

Target component:

```text
[[TARGET_COMPONENT_ID]]
```

Target operator:

```text
[[TARGET_OPERATOR_ID]]
```

Canonical segment identifier:

```text
[[CANONICAL_SEGMENT_ID]]
```

Canonical evaluation unit:

```text
submission_id × component_id × operator_id
```

Runtime row identifier rule:

- The canonical submission-level identifier field is `[[SUBMISSION_IDENTIFIER_FIELD]]`.
- In output, copy the runtime row value from `[[SUBMISSION_IDENTIFIER_FIELD]]` into the CSV field named `submission_id`.

Wrapper-handling rule for response text:

[[WRAPPER_HANDLING_RULE_BULLETS]]

Embedded operator specification:

| operator_id | sbo_short_description | operator_definition | operator_guidance | failure_mode_guidance |
|---|---|---|---|---|
| [[OPERATOR_ID]] | [[SBO_SHORT_DESCRIPTION]] | [[OPERATOR_DEFINITION]] | [[OPERATOR_GUIDANCE]] | [[FAILURE_MODE_GUIDANCE]] |

Embedded decision procedure for `[[TARGET_OPERATOR_ID]]`:

[[EMBEDDED_DECISION_PROCEDURE_BLOCK]]

Extraction status scale:

| value | meaning |
|---|---|
| `ok` | the target span was found and extracted successfully |
| `missing` | the target span or required anchor was not found |
| `ambiguous` | the response suggests the target content but boundaries or selection remain unclear |
| `malformed` | the response is present but structurally unusable for this operator |

Required output fields:

- `submission_id`
- `component_id`
- `operator_id`
- `segment_id`
- `segment_text`
- `extraction_status`
- `extraction_notes`

Canonical output identifier rule:

- For every emitted row, set `segment_id` exactly to `[[CANONICAL_SEGMENT_ID]]`.
- Do not emit numeric placeholders such as `1`.
- Do not synthesize derived identifiers such as `[[TARGET_OPERATOR_ID]]_1`.
- `segment_id` is a registry-defined semantic identifier, not a per-row sequence number.

Do not use:

- external knowledge
- downstream scoring criteria
- semantic correctness judgements
- indicator or dimension reasoning
- assumptions about intended meaning beyond the operator definition

#### Input format

Runtime input will contain a dataset with one or more runtime rows.
Each runtime row represents one submission-level evaluation unit:
[[SUBMISSION_IDENTIFIER_FIELD]] × component_id
Evaluate every runtime row whose component_id equals the target component.
Do not stop after the first runtime row.

Each runtime row must contain:

- a submission identifier field
- `component_id`
- the response text field `response_text`

For all later instructions in this prompt, the selected field must be treated as the canonical `response_text` for that runtime row.

#### Evaluation sequence

1. Construct a single internal representation of the runtime input dataset.
2. Identify the valid runtime rows whose `component_id = [[TARGET_COMPONENT_ID]]`.
3. For each valid runtime row, treat the field `response_text` as the row's canonical response text.
4. Apply wrapper-handling rules to each valid runtime row before extraction.
5. For each valid runtime row, apply the embedded operator definition, guidance, failure-mode guidance, and decision procedure exactly as written.
6. Emit one CSV data row for the target operator for each valid runtime row.

#### Output discipline

Emit the CSV header exactly once, before all data rows.
Use concise `extraction_notes`.
If no valid runtime rows exist for the target component, emit no output.
````
