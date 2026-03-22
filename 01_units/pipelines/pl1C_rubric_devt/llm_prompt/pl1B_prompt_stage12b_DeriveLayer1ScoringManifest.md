---
prompt_id: pl1B_stage12b_layer1_scoring_manifest_wrapper_v01
version: v01
stage: pipeline_pl1B_stage12
purpose: generate a Layer 1 Scoring Manifest by extracting and flattening Layer 1 SBO instances and value-derivation specifications from a rubric payload
status: active
owner: EECS3000W26
input_contract:
  - rubric_payload (RUBRIC_<ASSESSMENT_ID>_<STATUS>_payload_v*)
input_structure:
  delimiter: ===
  artefacts:
    - name: rubric_payload
      required_sections:
        - 5.4 Layer 1 SBO Instances
        - 6.1 Layer 1 SBO Value Derivation
      section_tolerance:
        - allow_status_suffixes: true
  artefact_order:
    - rubric_payload
extraction_rules:
  indicator_registry_source:
    section: 5.4 Layer 1 SBO Instances
    fields:
      - component_id
      - sbo_identifier
      - indicator_id
      - sbo_short_description
    ignore_fields:
      - sbo_identifier_shortid
  value_derivation_source:
    section: 6.1 Layer 1 SBO Value Derivation
    fields:
      - indicator_definition
      - assessment_guidance
      - evaluation_notes
  join_rule:
    keys:
      - component_id
      - indicator_id
    constraints:
      - indicator_id_is_canonical_join_key
      - do_not_use_sbo_identifier_shortid
ordering_rules:
  component_order:
    source: section_6_1_component_block_order
    method: top_to_bottom
  indicator_order:
    within_component: ascending_indicator_id
    consistency_requirement: must_match_section_5_4
manifest_rules:
  row_definition: one_row_per_indicator
  completeness:
    - all_indicators_from_section_5_4_must_appear_once
    - all_indicators_must_have_matching_section_6_1_entry
  verbatim_fields:
    - sbo_short_description
    - indicator_definition
    - assessment_guidance
    - evaluation_notes
  prohibition:
    - no_paraphrasing
    - no_inference
    - no_semantic_modification
metadata_rules:
  assessment_id:
    source: any_layer1_sbo_instance_row
    constraint: all_rows_must_agree
  scoring_layer: Layer1
  scoring_scope: participant_id_x_component_id
  ontology_reference: Rubric_SpecificationGuide_v*
  expected_input_identifier: participant_id
  runtime_output_identifier: submission_id
  component_registry_count: count_unique_component_id
  total_indicator_count: count_all_indicators
output_contract: layer1_scoring_manifest
output_structure:
  artefact_name_pattern: <ASSESSMENT_ID>_Layer1_ScoringManifest_v*
  output_container: fenced_markdown_block
  outer_fence: "````"
  required_sections:
    - title_line
    - manifest_metadata
    - identifier_context
    - layer1_indicator_scoring_manifest_table
output_format_rules:
  title_line:
    required: true
    format: "## <ASSESSMENT_ID>_Layer1_ScoringManifest_v01"
    position: first_line_inside_fence
  metadata_section:
    format: markdown_table
  identifier_context:
    required_elements:
      - participant_id_x_component_id_expression
      - submission_id_mapping_statement
  manifest_table:
    format: markdown_table
    schema:
      - component_id
      - sbo_identifier
      - indicator_id
      - sbo_short_description
      - indicator_definition
      - assessment_guidance
      - evaluation_notes
    column_constraints:
      - exact_match_required
      - fixed_order
      - no_extra_columns
      - no_missing_columns
failure_conditions:
  - missing_rubric_payload
  - missing_section_5_4
  - missing_section_6_1
  - unmatched_indicators_between_sections
  - duplicate_indicator_id_values
  - missing_required_fields
  - non_deterministic_ordering
  - conflicting_assessment_id_values
integrity_constraints:
  - one_row_per_indicator
  - exact_identifier_preservation
  - verbatim_field_transfer
  - deterministic_ordering
  - no_semantic_drift
  - indicator_id_used_as_sole_join_key
notes: |
  This prompt performs Stage 1.2 of Pipeline PL1B. It generates a Layer 1 Scoring Manifest
  by extracting indicator definitions and evaluation specifications from a rubric payload.
  The manifest is a flattened, schema-stable artefact used as input to Layer 1 scoring prompts.
  The process is strictly non-interpretive and must preserve all source content verbatim.
---
## Wrapper Prompt — Generate Layer 1 Scoring Manifest from Rubric Payload

### Prompt title and purpose

This wrapper prompt generates the **Layer 1 Scoring Manifest** from a fully authored rubric payload.

The generated output corresponds to:

```text
\<ASSESSMENT_ID\>\_Layer1_ScoringManifest_v*
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
RUBRIC_\<ASSESSMENT_ID\>_\<STATUS\>_payload_v*
```

If the input artefact is missing, malformed, or incomplete, the prompt must produce **no output**.

---

## Source sections (authoritative)

The prompt must extract content only from the following sections:

- `5.4 Layer 1 SBO Instances` (including any status suffix such as `(Draft)`)  
- `6.1 Layer 1 SBO Value Derivation` (including any status suffix such as `(Draft)`)  

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

From Section 5.4, extract for each indicator:

- `component_id`  
- `sbo_identifier`  
- `indicator_id`  
- `sbo_short_description`  

Ignore `sbo_identifier_shortid`.

---

### 2. Evaluation specification extraction

From Section 6.1, extract:

- `indicator_definition`  
- `assessment_guidance`  
- `evaluation_notes`  

---

### 3. Join rule

Each manifest row must be constructed by joining:

```text
(component_id, indicator_id)
```

`indicator_id` is the canonical join key.  
`sbo_identifier_shortid` must not be used for joining.

---

### 4. Verbatim carry-forward rule (critical)

The following fields must be copied **verbatim** from the rubric payload:

- `sbo_short_description`  
- `indicator_definition`  
- `assessment_guidance`  
- `evaluation_notes`  

No paraphrasing, summarisation, or rewriting is permitted.

---

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

Component order must be determined by the top-to-bottom order of `##### Component:` blocks in Section 6.1.

---

### 2. Indicator ordering

Within each component:

- indicators must appear in ascending `indicator_id` order  
- ordering must match Section 5.4  

---

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
| assessment_id | extracted from any Layer 1 SBO instance row (all rows must agree) |
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

No additional interpretation or commentary is permitted.

---

## Output format

### Output title requirement

The first line inside the fenced Markdown block must be the manifest title in the following exact form:

```text
## \<ASSESSMENT_ID\>\_Layer1_ScoringManifest_v01
```

Where:

- `<ASSESSMENT_ID>` is the manifest `assessment_id` extracted from Section `5.4 Layer 1 SBO Instances`
- the version token must be emitted exactly as `v01` unless an alternative version is explicitly provided in the prompt input

This title line must appear before:

- `### 1. Manifest metadata`
- all other output content

If the title line cannot be emitted exactly in this form, produce **no output**.
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
- multiple conflicting `assessment_id` values are detected across Layer 1 SBO instances  

---

## Integrity constraints

The generated manifest must satisfy:

1. one row per indicator SBO instance  
2. exact identifier preservation  
3. verbatim field carry-forward  
4. deterministic ordering  
5. no semantic drift from source artefact  
6. consistent use of `indicator_id` as the sole join key across sections  

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