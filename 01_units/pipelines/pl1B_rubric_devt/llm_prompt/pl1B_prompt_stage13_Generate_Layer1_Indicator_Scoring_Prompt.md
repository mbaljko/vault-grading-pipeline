---
prompt_id: pl1B_stage13_layer1_indicator_scoring_prompt_wrapper_v01
version: v01
stage: pipeline_pl1B_stage13
purpose: generate a bounded Layer 1 SBO scoring prompt that performs indicator evidence detection for a single target component using the Layer1_ScoringManifest
status: active
owner: EECS3000W26
input_contract:
  - target_component_parameter (`PARAM_TARGET_COMPONENT_ID = <INSERT HERE>`)
  - assignment_payload_specification (<ASSESSMENT_ID>_AssignmentPayloadSpec_v*)
  - layer1_scoring_manifest (Layer1_ScoringManifest_<ASSESSMENT_ID>_v<VERSION>)
input_structure:
  delimiter: §§§
  parameter_block:
    required_format: PARAM_TARGET_COMPONENT_ID = <COMPONENT_ID>
  artefacts:
    - name: assignment_payload_specification
      expected_elements:
        - assessment_id
        - submission_id
        - component_id
        - response_text
      canonical_scoring_unit: submission_id_x_component_id
      evidence_rule: explicit_textual_evidence_only
    - name: layer1_scoring_manifest
      expected_elements:
        - component_id
        - sbo_identifier
        - indicator_id
        - sbo_short_description
        - indicator_definition
        - assessment_guidance
        - evaluation_notes
  artefact_order:
    - parameter_block
    - assignment_payload_specification
    - layer1_scoring_manifest
    - generation_trigger
manifest_processing:
  filtering_rule: filter_rows_where_component_id_equals_PARAM_TARGET_COMPONENT_ID
  validation_rules:
    - filtered_manifest_must_not_be_empty
    - indicator_id_values_must_be_unique_within_filtered_rows
output_contract: generated_scoring_prompt
output_structure:
  artefact_name_pattern: RUN_<ASSESSMENT_ID>_<PARAM_TARGET_COMPONENT_ID>_Layer1_SBO_scoring_prompt_v*
  output_container: fenced_markdown_block
  outer_fence: "````"
  required_sections:
    - Prompt title and restrictions
    - Authoritative scoring materials
    - Input format
    - Evaluation discipline
    - Evidence interpretation rules
    - Confidence assignment rule
    - Output schema
    - Constraints
    - Content rules
    - Failure mode handling
runtime_semantics:
  input_definition:
    - runtime_input_dataset_contains_one_or_more_rows
    - each_runtime_row_represents_submission_id_x_component_id
    - evaluate_rows_where_component_id_equals_target_component
    - do_not_stop_after_first_runtime_row
  batch_output_definition:
    - emit_one_csv_header_row_once
    - for_each_runtime_row_emit_one_row_per_indicator
    - group_output_rows_by_runtime_row
    - maintain_indicator_order_within_each_group
    - total_rows_equals_runtime_rows_times_indicator_count
evaluation_pipeline:
  sequence:
    - construct_internal_runtime_dataset_representation
    - identify_valid_runtime_rows_matching_target_component
    - apply_wrapper_handling_rules_per_runtime_row_if_required
    - construct_ordered_indicator_id_list_from_manifest
    - build_evidence_index_from_response_text
    - perform_single_analytic_signal_pass
    - group_candidate_fragments_by_indicator_relevance
    - evaluate_indicators_using_indexed_fragments
indicator_evidence_scale:
  values:
    - evidence
    - partial_evidence
    - little_to_no_evidence
  definitions:
    evidence: explicit_textual_evidence_clearly_satisfies_indicator_definition
    partial_evidence: explicit_signal_present_but_incomplete
    little_to_no_evidence: no_interpretable_explicit_signal_present
confidence_scale:
  values:
    - high
    - medium
    - low
  interpretation:
    high: clear_explicit_language_supports_status
    medium: explicit_language_present_but_ambiguous
    low: weak_or_uncertain_textual_signal
output_schema:
  format: csv
  header: submission_id,component_id,indicator_id,evidence_status,evaluation_notes,confidence,flags
  fields:
    - submission_id
    - component_id
    - indicator_id
    - evidence_status
    - evaluation_notes
    - confidence
    - flags
  allowed_flag_values:
    - none
    - needs_review
evaluation_rules:
  - each_indicator_evaluated_once_per_runtime_row
  - evidence_or_partial_requires_explicit_fragment
  - indicators_must_be_evaluated_independently
  - dimension_logic_must_not_be_used
  - mapping_rules_must_not_be_used
  - component_performance_logic_must_not_be_used
content_rules:
  - output_must_be_csv_only
  - header_must_appear_once
  - evaluation_notes_must_be_double_quoted
  - empty_notes_must_be_emitted_as_double_quotes
  - component_id_must_equal_target_component
  - one_output_row_per_indicator_per_runtime_row
constraints:
  - do_not_modify_scoring_manifest
  - do_not_invent_indicators
  - do_not_perform_dimension_scoring
  - do_not_assign_component_or_submission_scores
  - evaluator_must_use_only_runtime_dataset_and_embedded_manifest
failure_conditions:
  - missing_required_parameter
  - malformed_delimiter_structure
  - missing_assignment_payload_specification
  - missing_layer1_scoring_manifest
  - filtered_manifest_empty
  - duplicate_indicator_ids_detected
  - runtime_dataset_contains_no_valid_rows
  - csv_header_cannot_be_emitted_exactly
notes: |
  This prompt performs Stage 1.3 of Pipeline PL1B. It generates a reusable
  Layer 1 SBO scoring prompt that evaluates indicator evidence using the
  Layer1_ScoringManifest. The wrapper filters indicators by the target
  component and embeds their definitions and detection guidance into a
  standalone scoring prompt capable of processing runtime datasets and
  producing indicator-level evidence status outputs for downstream
  Layer 2–4 rubric evaluation stages.
---
## Wrapper Prompt — Generate Canonical Layer 1 Indicator Detection Scoring Prompt (Stage 1.3)

Wrapper prompt: Generate a deterministic and canonically formatted Layer 1 indicator evidence detection scoring prompt using the **Layer 1 scoring manifest** under the **Rubric Template architecture**.

This wrapper prompt **generates a scoring prompt**.  
This wrapper prompt does not evaluate participant responses.

The generated scoring prompt performs **Layer 1 SBO scoring**, which determines `evidence_status` values for the embedded indicator SBO instances belonging to one target component.

### Canonicalisation requirement

The generated scoring prompt must be **canonically formatted**.

For all invocations that use valid inputs, the generated scoring prompt must preserve the same:

- section order
- subsection order
- heading text
- sentence order
- table structure
- lead-in phrases
- bullet structure
- field order
- terminology
- spacing conventions

except where substitution is required by the input artefacts.

Allowed substitutions are limited to:

- `ASSESSMENT_ID`
- `PARAM_TARGET_COMPONENT_ID`
- the canonical submission-level identifier field name
- wrapper-handling rules for response_text extracted from the assignment payload specification
- filtered embedded indicator rows from the `Layer1_ScoringManifest`

No other variation is permitted.

If two invocations differ only in `PARAM_TARGET_COMPONENT_ID` or in the filtered manifest rows, the generated prompts must remain identical in structure and wording except for those required substitutions.

The wrapper must treat the generated scoring prompt as a **locked canonical template instance**.

Generation must therefore follow **template instantiation discipline** rather than free-form rewriting.

The wrapper must:

- reproduce all canonical template text **verbatim**
- substitute values **only** at explicitly permitted substitution points
- preserve punctuation, spacing, bullet grammar, and heading levels
- preserve section ordering and sentence ordering
- preserve Markdown structure and table schemas

The wrapper must **not**:

- paraphrase template text
- rewrite sentences
- compress or expand lists
- introduce explanatory prose
- alter Markdown structure
- alter table schemas
- change heading levels
- reorder sections
- modify spacing conventions

If the wrapper cannot produce a prompt that matches the canonical template exactly except for permitted substitutions, the wrapper must **produce no output**.

The wrapper must treat the canonical scoring prompt text below as the **single authoritative scaffold**.  
The scaffold must be instantiated by **direct substitution only**.

The wrapper must not synthesise section text from the abstract requirements when the canonical scaffold already provides the required wording.

The wrapper must perform only the following insertion operations on the canonical scaffold:

- replace `[[ASSESSMENT_ID]]`
- replace `[[TARGET_COMPONENT_ID]]`
- replace `[[SUBMISSION_IDENTIFIER_FIELD]]`
- replace `[[WRAPPER_HANDLING_RULE_BULLETS]]`
- replace `[[EMBEDDED_INDICATOR_TABLE_ROWS]]`

No other insertion points are permitted.

If any required insertion value cannot be determined deterministically from the supplied artefacts, the wrapper must **produce no output**.

### Target Component Parameter (Required)

The wrapper prompt requires the user to specify the component whose Layer 1 indicators will be scored.

```text
PARAM_TARGET_COMPONENT_ID = \<COMPONENT_ID\>
```

Example:

```text
PARAM_TARGET_COMPONENT_ID = SectionBResponse
```

This parameter determines which rows from the `Layer1_ScoringManifest` will be embedded in the generated scoring prompt.

### Required Input Artefacts

The wrapper expects exactly three input blocks separated using the delimiter:

```text
§§§
```

The wrapper expects the following three blocks in sequence:

1. parameter block  
   `PARAM_TARGET_COMPONENT_ID = <COMPONENT_ID>`

2. artefact block  
   `\<ASSESSMENT_ID\>_AssignmentPayloadSpec_v*`

3. artefact block  
   `Layer1_ScoringManifest_\<ASSESSMENT_ID\>_v\<VERSION\>`

The parameter block must appear in the form:

```text
§§§
PARAM_TARGET_COMPONENT_ID = \<COMPONENT_ID\>
§§§
```

The two artefact blocks must appear exactly as produced by their upstream pipelines and must not be modified.
The parameter block must appear exactly in the required syntax.

If any required artefact or parameter is missing, malformed, or inconsistent, the wrapper prompt must **produce no output**.

Angle-bracketed expressions in this wrapper, such as `<ASSESSMENT_ID>`, `<COMPONENT_ID>`, and `<VERSION>`, are specification placeholders used to describe required payload content. They are not literal payload text unless they occur inside a verbatim artefact block.

### Payload Grammar (Normative)

The payload supplied to this wrapper must match the following exact grammar:
```text
§§§
PARAM_TARGET_COMPONENT_ID = <COMPONENT_ID>
§§§
<ASSESSMENT_ID>_AssignmentPayloadSpec_v* contents
§§§
Layer1_ScoringManifest_<ASSESSMENT_ID>_v<VERSION> contents
```

The payload must contain exactly three blocks.
The first block is a parameter block.
The second and third blocks are verbatim artefact blocks.
No text may appear before the first delimiter.
No text may appear after the final manifest line.
No additional delimiter may appear after the manifest block.
If the payload violates this grammar, the wrapper must produce no output.


### Input Artefact Order (Mandatory)

Artefacts must appear **exactly in the following order**, separated by the delimiter `§§§`.

Exactly three blocks must appear, in the required order. No additional block, delimiter-only block, numbering marker, commentary line, or trailing text may appear anywhere in the payload.

```text
§§§
PARAM_TARGET_COMPONENT_ID = \<COMPONENT_ID\>
§§§
\<ASSESSMENT_ID\>_AssignmentPayloadSpec_v* contents
§§§
Layer1_ScoringManifest_\<ASSESSMENT_ID\>_v\<VERSION\> contents
```

Exactly three input blocks must be provided. No additional blocks, delimiters, markers, or trailing text are permitted after the manifest block.

### Example Invocation

```text
§§§
PARAM_TARGET_COMPONENT_ID = SectionBResponse
§§§
\<PPP_AssignmentPayloadSpec_v01 contents\>
§§§
\<Layer1_ScoringManifest_PPP_v01 contents\>
```

If the artefacts appear in a different order or if the delimiter structure is violated, the wrapper prompt must **produce no output**.

### Purpose

Generate a reusable **Layer 1 SBO scoring prompt** that performs **indicator evidence detection**.

The generated prompt must:

- evaluate indicator evidence using the `Layer1_ScoringManifest`
- embed the indicator evaluation specification contained in the manifest

For each embedded indicator, the generated scoring prompt must include:

```text
indicator_id
sbo_short_description
indicator_definition
assessment_guidance
the manifest evaluation_notes field as embedded evaluator guidance
```

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

```text
indicator evidence detection
```

Outputs produced by the Layer 1 scoring prompt will later be consumed by:

```text
Layer 2 — Dimension Evidence Derivation
Layer 3 — Component Performance Mapping
Layer 4 — Submission Score Derivation
```

### Task Classification

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

### Authoritative Inputs

The model may rely **only** on the following artefacts supplied verbatim.

#### Input Artefact  
`\<ASSESSMENT_ID\>_AssignmentPayloadSpec_v*`

The wrapper must extract:

```text
assessment_id
the canonical submission-level identifier field
component_id
response_text
```

If the assignment payload uses `participant_id` as the canonical row identifier, the generated scoring prompt must treat that field as the runtime `submission_id` field in output.

Canonical response text rule:

The canonical evidence surface for each runtime row is the field `response_text`.

For all later instructions in the generated scoring prompt, `response_text` must be treated as the canonical response text for that runtime row.

Canonical scoring unit:

```text
submission_id × component_id
```

Evidence rule:

```text
explicit textual evidence only
```

If wrapper-handling rules exist for `response_text`, they must be embedded in the generated scoring prompt.

#### Input Artefact  
`Layer1_ScoringManifest_\<ASSESSMENT_ID\>_v\<VERSION\>`

The wrapper must extract:

```text
component_id
sbo_identifier
indicator_id
sbo_short_description
indicator_definition
assessment_guidance
evaluation_notes
```

Within the generated scoring prompt, the manifest field `evaluation_notes` must be treated as embedded evaluator guidance for indicator interpretation.  
It must not be confused with the CSV output field named `evaluation_notes`.

This manifest defines both:

```text
the registry of Layer 1 indicators
the evaluation specification used to detect them
```

### Manifest Filtering Rule

Before generating the scoring prompt, the wrapper must execute:

```text
filter Layer1_ScoringManifest
where component_id = PARAM_TARGET_COMPONENT_ID
```

The generated scoring prompt must embed only indicators whose component_id equals `PARAM_TARGET_COMPONENT_ID`.  
Indicators belonging to other components must not appear in the generated prompt.

Manifest validation rules:

- if any required manifest column is missing → produce no output
- if the filtered table is empty → produce no output
- if duplicate `indicator_id` values appear in the filtered table → produce no output

Only filtered rows may be embedded in the generated scoring prompt.

The row order of the filtered manifest becomes the canonical embedded indicator order in the generated scoring prompt.

### Canonical Scaffold Insertion Mapping

The wrapper must construct the following deterministic insertion values before scaffold instantiation.

#### Insertion token `[[ASSESSMENT_ID]]`

Set equal to the extracted `assessment_id`.

#### Insertion token `[[TARGET_COMPONENT_ID]]`

Set equal to `PARAM_TARGET_COMPONENT_ID`.

#### Insertion token `[[SUBMISSION_IDENTIFIER_FIELD]]`

Set equal to the canonical submission-level identifier field extracted from the assignment payload specification.

#### Insertion token `[[WRAPPER_HANDLING_RULE_BULLETS]]`

Set equal to the wrapper-handling rules extracted from the assignment payload specification for `response_text`, but only if those rules already appear in the source artefact as Markdown bullet lines.

The insertion value must preserve the extracted bullet lines verbatim and in source order.

The inserted text must contain bullet lines only.  
No introductory sentence, paraphrase, normalisation, bullet synthesis, or prose-to-bullet conversion may occur inside the insertion value.

If wrapper-handling rules are absent, malformed, not present as bullet lines in the source artefact, or cannot be extracted verbatim as bullet lines, the wrapper must **produce no output**.

#### Insertion token `[[EMBEDDED_INDICATOR_TABLE_ROWS]]`

Set equal to the filtered manifest rows rendered as Markdown table body rows using the following exact column order:

- indicator_id
- sbo_short_description
- indicator_definition
- assessment_guidance
- embedded evaluator guidance

Each table body row must be constructed deterministically using the following formatting rules:

- each row must begin with `|`
- each column value must be surrounded by single spaces inside the pipes
- the final column must end with ` |`
- the row must contain exactly five columns
- columns must appear in the required column order
- column values must preserve the exact text from the source manifest fields
- leading and trailing whitespace from manifest field values must be trimmed before insertion
- newline characters inside manifest field values must be replaced with a single space
- pipe characters inside manifest field values must be escaped as `\|`
- empty field values must be rendered as an empty cell between pipes

Example row format:

```text
| indicator_id | sbo_short_description | indicator_definition | assessment_guidance | embedded evaluator guidance |
```

Each table body row must preserve the filtered manifest row order exactly.

The wrapper must insert only the filtered rows whose `component_id = PARAM_TARGET_COMPONENT_ID`.

No header row may appear inside this insertion value.  
No prose may appear before or after the inserted rows.

If any manifest field required to construct a table row is missing, malformed, or cannot be rendered deterministically according to these rules, the wrapper must **produce no output**.

### Canonical Template Validation

Before emitting the scoring prompt, the wrapper must perform a **canonical scaffold validation check**.

The wrapper must confirm that the emitted scoring prompt is an exact structural instantiation of the canonical scaffold.

The following conditions must all hold:

- all required sections appear exactly once
- section headings match the canonical scaffold text exactly
- section ordering is identical to the canonical scaffold
- bullet lists match the canonical scaffold exactly
- table schemas match the canonical scaffold exactly
- lead-in phrases match the canonical scaffold exactly
- no additional sentences appear anywhere in the scaffold
- no scaffold sentences are missing
- no scaffold sentences are rewritten or paraphrased
- permitted substitutions were applied only at the defined insertion tokens
- no insertion tokens remain unresolved in the emitted prompt

The wrapper must treat the canonical scaffold as immutable text except at the explicitly permitted insertion tokens.

If any validation rule fails, the wrapper must **produce no output**.

### Wrapper Behaviour
#### Indicator Evidence Status Scale

The generated scoring prompt must embed this scale.

| value | meaning |
|---|---|
| `evidence` | explicit textual evidence clearly satisfies the indicator definition |
| `partial_evidence` | explicit textual signal relevant to the indicator exists but is incomplete |
| `little_to_no_evidence` | no interpretable explicit textual signal supporting the indicator is present |

Evidence must rely strictly on **explicit response language**.

#### Output Requirements

Allowed output fields:

```text
submission_id
component_id
indicator_id
evidence_status
evaluation_notes
confidence
flags
```

Allowed values:

```text
confidence ∈ {low, medium, high}
flags ∈ {none, needs_review}
```

##### Field Formatting Rules

The scoring prompt must require:

- `evaluation_notes` enclosed in double quotes
- empty notes represented as `""`

##### CSV Header Requirement

Output must begin with the header row:

```text
submission_id,component_id,indicator_id,evidence_status,evaluation_notes,confidence,flags
```

The header appears **exactly once**.

#### Wrapper Execution Discipline

##### Phase 1 — Artefact ingestion

The wrapper reads the three input blocks silently.

If the input-block contract is violated, produce **no output**.

##### Phase 2 — Validation and extraction

The wrapper validates block count, block order, artefact consistency, and required fields.

If validation fails, produce **no output**.

##### Phase 3 — Canonical scaffold instantiation

When valid input blocks are present, the wrapper must instantiate the canonical scaffold exactly once.

Instantiation sequence:

1. Construct all insertion values.
2. Copy the canonical scaffold text exactly as written.
3. Replace insertion tokens directly.
4. Run canonical template validation.
5. Emit the instantiated scaffold if and only if validation succeeds.

### Output Artefact

Generate exactly one artefact:

```text
RUN_\<ASSESSMENT_ID\>_\<PARAM_TARGET_COMPONENT_ID\>_Layer1_SBO_scoring_prompt_v*
```

The artefact must:

- reference `PARAM_TARGET_COMPONENT_ID`
- embed the filtered indicator rows
- embed the evaluation specification
- assume the canonical payload structure

### Prompt Template Lock Requirement

The generated scoring prompt must follow a **fixed canonical template**.

The wrapper must **not paraphrase, compress, rename, reorder, restyle, or structurally reformat** any of the required semantic instructions listed below.

The generated scoring prompt must preserve the exact wording, ordering, subsection structure, and formatting grammar of the canonical template, except where input-driven substitution is explicitly required.

The generated scoring prompt must use the exact section order specified in this wrapper.

The generated scoring prompt must use **batch-safe runtime language** and must never use any of the following phrases:

```text
one runtime row
evaluate only the supplied runtime row
one evaluation unit
then emit exactly 8 data rows
```

The generated scoring prompt must instead describe runtime input using the exact concepts:

```text
runtime input dataset
runtime rows
for each runtime row
for each runtime row, evaluate all embedded indicators
```

Within the section titled `Authoritative scoring materials`, embedded indicators must be presented in **one Markdown table**, not as repeated per-indicator subsections or narrative blocks.

That table must appear after the assessment-level scoring metadata and must use this exact column order:

```text
indicator_id
sbo_short_description
indicator_definition
assessment_guidance
embedded evaluator guidance
```

The embedded indicator table must contain **only** rows from the filtered `Layer1_ScoringManifest` where:

```text
component_id = PARAM_TARGET_COMPONENT_ID
```

The row order of that table must match the row order of the filtered manifest exactly.

Per-indicator subsection formats such as:

```text
#### Indicator: I01
```

must **not** be generated.

The generated scoring prompt must use the following fixed lead-ins exactly as written:

```text
Assessment identifier:
Target component:
Canonical scoring unit:
Runtime row identifier rule:
Evidence rule:
Wrapper-handling rule for response text:
Embedded indicators for `[[TARGET_COMPONENT_ID]]` appear in the canonical order defined by the filtered `Layer1_ScoringManifest`:
Indicator evidence status scale:
Field rules:
Use only:
Do not use:
Require all of the following:
Produce no output if:
```

Where the target component appears inside a lead-in, only the component value may vary.

If a generated prompt would differ from the canonical template in wording or structure beyond permitted substitutions, the wrapper prompt must **produce no output**.

### Generated Scoring Prompt Structure

The scoring prompt must appear in **one fenced Markdown block** using an outer fence of four backticks.

Sections must appear in this exact order:

```text
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

### Wrapper Output Contract

The wrapper must emit exactly one output artefact.

That artefact must consist solely of the instantiated canonical scoring prompt scaffold.

The output must therefore contain:

- one fenced Markdown block
- using an outer fence of four backticks
- containing the instantiated canonical scaffold

The wrapper must not emit:

- explanatory text
- commentary
- diagnostic notes
- prefaces or summaries
- additional Markdown blocks
- any text before or after the fenced scaffold block

If the wrapper cannot produce a fully instantiated canonical scaffold that passes the canonical template validation rules, the wrapper must produce **no output**.

### Canonical Output Scaffold

The wrapper must instantiate the following scaffold **verbatim**.

No text may be added, removed, reordered, or rewritten outside the permitted insertion operations.

````text
#### RUN_[[ASSESSMENT_ID]]_[[TARGET_COMPONENT_ID]]_Layer1_SBO_scoring_prompt_v01

### Prompt title and restrictions

This prompt performs **Layer 1 SBO scoring** for target component `[[TARGET_COMPONENT_ID]]`.

It determines `evidence_status` values for the embedded indicator SBO instances belonging to this component.

This prompt does **not**:

- evaluate dimensions
- evaluate indicator combinations
- apply indicator→dimension mappings
- assign component performance levels
- assign submission scores
- evaluate indicators belonging to other components

Layer 1 SBO scoring performs only:

```text
indicator evidence detection
```

### Authoritative scoring materials

Assessment identifier:

```text
[[ASSESSMENT_ID]]
```

Target component:

```text
[[TARGET_COMPONENT_ID]]
```

Canonical scoring unit:

```text
submission_id × component_id
```

Runtime row identifier rule:

- The canonical submission-level identifier field is `[[SUBMISSION_IDENTIFIER_FIELD]]`.
- In output, copy the runtime row value from `[[SUBMISSION_IDENTIFIER_FIELD]]` into the CSV field named `submission_id`.

Evidence rule:

```text
explicit textual evidence only
```

Wrapper-handling rule for response text:

[[WRAPPER_HANDLING_RULE_BULLETS]]

Embedded indicators for `[[TARGET_COMPONENT_ID]]` appear in the canonical order defined by the filtered `Layer1_ScoringManifest`:

| indicator_id | sbo_short_description | indicator_definition | assessment_guidance | embedded evaluator guidance |
|---|---|---|---|---|
[[EMBEDDED_INDICATOR_TABLE_ROWS]]

Indicator evidence status scale:

| value | meaning |
|---|---|
| `evidence` | explicit textual evidence clearly satisfies the indicator definition |
| `partial_evidence` | explicit textual signal relevant to the indicator exists but is incomplete |
| `little_to_no_evidence` | no interpretable explicit textual signal supporting the indicator is present |

Field rules:

- `evaluation_notes` enclosed in double quotes
- empty notes represented as `""`

Use only:

- the runtime dataset rows
- canonical `response_text`
- the embedded indicator definitions
- the embedded assessment guidance
- the embedded evaluator guidance derived from the manifest `evaluation_notes` field
- the embedded evidence scale

Do not use:

- external knowledge
- dimension reasoning
- performance-level reasoning
- assumptions about intended meaning

Require all of the following:

- one CSV row per embedded indicator **for each valid runtime row**
- complete coverage of all valid runtime rows in the runtime dataset
- `component_id = [[TARGET_COMPONENT_ID]]` in every emitted row
- concise `evaluation_notes`
- no long quotations unless fragment mode is enabled

Produce no output if:

- the runtime dataset contains no valid runtime rows for the target component
- the CSV header cannot be emitted exactly as specified
- complete row coverage cannot be achieved for all valid runtime rows
- any contradiction prevents deterministic evaluation

### Input format

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

Wrapper handling is applied per runtime row.

### Evaluation discipline

For each runtime row, evaluate all embedded indicator_id values exactly once.  
For each runtime row, emit one CSV data row per embedded indicator_id.  
Emit rows grouped by runtime row.  
Within each runtime row group, emit indicator_id values in embedded prompt order.  
Embedded indicator order must follow the order of rows in the filtered Layer1_ScoringManifest.  
Emit the CSV header exactly once, before all data rows.

```text
total data row count = number of valid runtime rows × number of embedded indicators
```

#### Indicator Coverage Rule

Before writing any output rows, construct the ordered list of embedded `indicator_id` values.

Ensure that:

- each embedded `indicator_id` is evaluated exactly once per runtime row
- indicators are processed in embedded prompt order
- every valid runtime row receives a complete indicator evaluation set

#### Runtime Row Coverage Rule

Before writing any output rows, construct the ordered list of valid runtime rows from the runtime dataset.

A valid runtime row is a row whose:

- submission identifier field is present
- `component_id` is present
- the response text field `response_text` is present
- `component_id` equals `[[TARGET_COMPONENT_ID]]`

Do not stop after the first valid runtime row.  
Do not emit output for only a prefix of the runtime dataset.

#### Evaluation Sequence

Layer 1 SBO scoring must follow this exact sequence:

1. Construct a single internal representation of the runtime input dataset.
2. Identify the valid runtime rows whose `component_id = [[TARGET_COMPONENT_ID]]`.
3. For each valid runtime row, treat the field `response_text` as the row’s canonical response text.
4. Apply wrapper-handling rules to each valid runtime row before evaluation.
5. Construct the ordered `indicator_id` list embedded in the prompt.
6. For each valid runtime row:
   - construct a single internal representation of that row’s canonical `response_text`
   - scan the response once and identify potentially relevant textual fragments
   - store those fragments in an internal evidence index
   - perform one internal analytic signal pass over the indexed fragments
   - organise the indexed evidence into candidate signal groupings relevant to the target component
   - evaluate all embedded `indicator_id` values using the evidence index and signal groupings rather than rescanning the full response text

#### Indicator Evaluation

For each valid runtime row and for each embedded `indicator_id` in prompt order:

- internally identify whether a relevant textual fragment exists
- evaluate the fragment using the embedded `indicator_definition`
- evaluate the fragment using the embedded `assessment_guidance`
- use the embedded evaluator guidance derived from the manifest `evaluation_notes` field
- assign `evidence_status`
- assign `confidence`
- assign `flags`

#### Evidence Gate Rule

Do **not** assign `evidence` or `partial_evidence` without internally identifying a supporting textual fragment.

If no relevant fragment exists, assign:

```text
little_to_no_evidence
```

#### Output Row Count Rule

Before emitting CSV rows, verify that:

```text
number of data rows to be written
=
number of valid runtime rows × number of embedded indicators
```

If counts differ, complete the missing evaluations before emitting output.  
Do not emit partial output.

#### Output Emission Rule

Emit output in this exact structure:

- one CSV header row
- then, for runtime row 1, one data row per embedded `indicator_id` in prompt order
- then, for runtime row 2, one data row per embedded `indicator_id` in prompt order
- continue until all valid runtime rows are exhausted

### Evidence interpretation rules

#### Evidence Fragment Output Mode

Default behaviour:

- supporting fragments are identified internally
- fragments are **not printed**
- `evaluation_notes` should normally be empty and emitted as `""`

Optional runtime mode:

```text
FRAGMENT_OUTPUT_MODE = on
```

If enabled, `evaluation_notes` may briefly reference the supporting fragment used to assign the evidence status.

#### Partial Evidence Preference Rule

If explicit language partially satisfies an indicator definition but does not fully satisfy it, assign:

```text
partial_evidence
```

Do not collapse weak but relevant explicit evidence into `little_to_no_evidence`.

#### Independence Rule

Indicators must be evaluated independently.

Do not use:

- other indicators
- dimension logic
- indicator combinations
- mapping rules
- component expectations

to influence the judgement.

### Confidence assignment rule

Confidence reflects clarity of textual evidence, not probability.

```text
high
clear explicit language supports the assigned status

medium
explicit language present but incomplete or ambiguous

low
weak or uncertain textual signal
```

```text
If evidence_status = little_to_no_evidence and no fragment exists, assign confidence = high.
If you are uncertain and cannot identify sufficient explicit support for evidence or partial_evidence, assign evidence_status = little_to_no_evidence and flags = needs_review.
```

### Output schema

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
- `indicator_id` values must appear in embedded prompt order within each runtime row group
- `evaluation_notes` must always be enclosed in double quotes
- if `evaluation_notes` is empty, emit `""`
- `confidence` must be one of: `low`, `medium`, `high`
- `flags` must be one of: `none`, `needs_review`
- no additional columns may appear
- no explanatory text may appear before or after the CSV

### Constraints

Use only:

- the runtime dataset rows
- canonical `response_text`
- the embedded indicator definitions
- the embedded assessment guidance
- the embedded evaluator guidance derived from the manifest `evaluation_notes` field
- the embedded evidence scale

Do not use:

- external knowledge
- dimension reasoning
- performance-level reasoning
- assumptions about intended meaning

### Content rules

Require all of the following:

- one CSV row per embedded indicator **for each valid runtime row**
- complete coverage of all valid runtime rows in the runtime dataset
- `component_id = [[TARGET_COMPONENT_ID]]` in every emitted row
- concise `evaluation_notes`
- no long quotations unless fragment mode is enabled

### Failure mode handling

If any artefact or parameter is missing, inconsistent, or contradictory:

- produce **no output**
- wait silently for corrected inputs

If the filtered manifest contains:

- no rows
- duplicate `indicator_id`
- missing evaluation fields

the wrapper prompt must **produce no output**.

Produce no output if:

- the runtime dataset contains no valid runtime rows for the target component
- the CSV header cannot be emitted exactly as specified
- complete row coverage cannot be achieved for all valid runtime rows
- any contradiction prevents deterministic evaluation
````
