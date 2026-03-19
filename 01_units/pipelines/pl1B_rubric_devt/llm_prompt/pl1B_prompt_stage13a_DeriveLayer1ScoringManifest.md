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
## Wrapper Prompt — Generate Layer 1 Scoring Manifest from Rubric Payload

### Prompt title and purpose

This wrapper prompt generates the **Layer 1 Scoring Manifest** from a fully authored rubric payload.

The generated output corresponds to:

```text
<ASSESSMENT_ID>_Layer1_ScoringManifest_v*
```

This stage performs a **bounded transformation** that:

- extracts Layer 1 indicator SBO instances and evaluation specifications
- flattens component-wise tables into a single manifest table
- preserves canonical identifiers and ordering
- emits a normalised scoring manifest used by downstream scoring prompts

This prompt does **not**:

- modify indicator definitions
- rewrite `sbo_short_description`
- reinterpret evaluation guidance
- introduce new indicators
- remove indicators
- perform scoring
- resolve inconsistencies through interpretation

---

### Task classification (authoritative)

This prompt performs:

- extraction  
- schema-bound restructuring  
- registry flattening  
- controlled normalisation  

This prompt does **not** perform:

- content invention  
- paraphrasing  
- semantic reinterpretation  
- threshold design  
- scoring or evaluation  

---

## Required input artefact

The input must be a complete rubric payload:

```text
RUBRIC_<ASSESSMENT_ID>_<STATUS>_payload_v*
```

If the input artefact is missing, malformed, or incomplete, the prompt must produce **no output**.

---

## Source sections (authoritative)

The prompt must extract content only from the following sections:

- `Section 5.4 Layer 1 SBO Instances`
- `Section 6.1 Layer 1 SBO Value Derivation`

No other sections may be used.

---

## Output structure

The output must contain the following sections in order:

### 1. Manifest metadata

### 2. Identifier context

### 3. Layer 1 Indicator Scoring Manifest

---

## Output schema

The manifest table must use the following schema:

| component_id | sbo_identifier | indicator_id | sbo_short_description | indicator_definition | assessment_guidance | evaluation_notes |
|---|---|---|---|---|---|---|

### Column rules

- column names must match **exactly**
- column order must match **exactly**
- no columns may be added
- no columns may be omitted

---

## Extraction and mapping rules

### 1. Indicator registry extraction

From `Section 5.4 Layer 1 SBO Instances`, extract for each indicator:

- `component_id`
- `sbo_identifier`
- `indicator_id`
- `sbo_short_description`

### 2. Evaluation specification extraction

From `Section 6.1 Layer 1 SBO Value Derivation`, extract:

- `indicator_definition`
- `assessment_guidance`
- `evaluation_notes`

### 3. Join rule

Each manifest row must be constructed by joining:

```text
(component_id, indicator_id)
```

across:

- the Layer 1 SBO instance registry (Section 5.4)
- the Layer 1 value-derivation tables (Section 6.1)

### 4. Verbatim carry-forward rule (critical)

The following fields must be copied **verbatim** from the rubric payload:

- `sbo_short_description`
- `indicator_definition`
- `assessment_guidance`
- `evaluation_notes`

No paraphrasing, summarisation, or rewriting is permitted.

### 5. Completeness rule

Every indicator in Section 5.4 must:

- appear exactly once in the manifest
- have a matching entry in Section 6.1

If any indicator:

- is missing from Section 6.1  
- appears more than once  
- cannot be joined deterministically  

the prompt must produce **no output**.

---

## Ordering rules

### 1. Component ordering

Components must appear in the order they are defined in Section 6.1.

### 2. Indicator ordering

Within each component:

- indicators must appear in ascending `indicator_id` order  
- ordering must match Section 5.4  

### 3. Global ordering

The manifest table must be grouped by `component_id` and ordered as:

```text
component order → indicator order
```

---

## Manifest metadata rules

The metadata section must include:

| field | value |
|---|---|
| assessment_id | copied from rubric payload |
| scoring_layer | Layer1 |
| scoring_scope | `participant_id × component_id` |
| ontology_reference | `Rubric_SpecificationGuide_v*` |
| expected_input_identifier | `participant_id` |
| runtime_output_identifier | `submission_id` |
| component_registry_count | number of unique component_id values |
| total_indicator_count | total number of indicators |

All values must be derived deterministically from the input.

---

## Identifier context section

The identifier context must include:

- explanation of the scoring unit:
  ```text
  participant_id × component_id
  ```
- explanation of:
  ```text
  submission_id ↔ participant_id
  ```
- no additional interpretation or commentary

---

## Output format

The output must be emitted as a **single fenced Markdown block**.

The outer fence must use **four backticks**.

The output must contain:

- metadata table
- identifier context section
- one manifest table

No additional commentary is permitted.

---

## Failure conditions

The prompt must produce **no output** if:

- Section 5.4 is missing
- Section 6.1 is missing
- any indicator cannot be matched across sections
- duplicate `indicator_id` values exist
- any required field is missing
- ordering cannot be determined deterministically

---

## Integrity constraints

The generated manifest must satisfy:

1. one row per indicator SBO instance  
2. exact identifier preservation  
3. verbatim field carry-forward  
4. deterministic ordering  
5. no semantic drift from source artefact  

---

## Explicit prohibition

The generator must not:

- reinterpret indicator meaning  
- generalise or specialise definitions  
- collapse or merge indicators  
- introduce new language  
- resolve inconsistencies by inference  

If inconsistencies exist, the correct behaviour is:

```text
produce no output
```

---

## Final instruction

Perform a strict, schema-preserving extraction and flattening of Layer 1 rubric content into a scoring manifest.

No interpretation. No rewriting. No deviation from source content.

```