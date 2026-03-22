---
prompt_id: pl1B_stage21_layer2_sbo_registry_prompt_v01
version: v01
stage: pipeline_pl1B_stage21
purpose: generate the Layer 2 SBO Instance Registry by consolidating conceptual evaluation dimensions derived from indicator evidence patterns
status: active
owner: EECS3000W26

input_contract:
  - rubric_specification_guide (Rubric_SpecificationGuide_v*)
  - submission_analytic_brief (\<ASSESSMENT_ID\>_SubmissionAnalyticBrief_v*)
  - layer1_sbo_registry (Rubric Template 5.4 Layer 1 SBO Instances)
  - trigger prompt (`BEGIN GENERATION`)
    
input_structure:
  delimiter: "==="
  artefacts:
    - name: rubric_specification_guide
      expected_elements:
        - layer2_sbo_identifier_structure
        - dimension_identifier_format
        - sbo_short_description_rules
    - name: submission_analytic_brief
      required_sections:
        - "Analytic Sub-space Identification"
        - "Contrastive Pattern Discovery"
      extracted_elements:
        - analytic_sub_space_registry
        - candidate_dimension_sketches
        - candidate_indicator_signals
        - component_identifiers
    - name: layer1_sbo_registry
      expected_elements:
        - indicator_registry
        - component_identifier_list
        - indicator_short_descriptions

output_contract: fenced_markdown_table

output_structure:
  outer_fence: "````"
  heading: "#### 5.3 Layer 2 SBO Instances (Draft)"
  table_columns:
    - sbo_identifier
    - sbo_identifier_shortid
    - assessment_id
    - component_id
    - dimension_id
    - sbo_short_description
  grouping_rule: group_rows_by_component_id
  ordering_rules:
    - dimension_id_must_be_globally_unique
    - dimension_id_must_be_sequential
    - rows_within_component_sorted_by_dimension_id

identifier_rules:
  submission_identifier_source: assessment_identifier
  component_identifier_source: canonical_component_id_from_analytic_brief
  component_short_identifier_mapping:
    SectionAResponse: SecA
    SectionBResponse: SecB
    SectionCResponse: SecC
    SectionDResponse: SecD
    SectionEResponse: SecE
  dimension_identifier_pattern: "D00-D99"
  sbo_identifier_pattern: "D_<sid>_<cid>_<did>"
  sbo_identifier_shortid_rule: equals_dimension_id

dimension_generation_rules:
  expected_dimension_range_per_component: "2-4"
  dimension_source_priority:
    - candidate_dimension_sketches
    - analytic_sub_spaces
    - clusters_of_related_indicators
    - conceptual_patterns_observed_in_indicator_sets
  consolidation_requirements:
    - merge_redundant_dimension_concepts
    - preserve_key_conceptual_distinctions
    - minimise_dimension_overlap
  dimension_properties:
    - must_represent_conceptual_evaluation_criterion
    - must_be_supported_by_indicator_evidence
    - must_not_duplicate_indicator_signals
    - must_not_require_performance_thresholds

sbo_description_rules:
  description_type: conceptual_dimension_label
  allowed_forms:
    - noun_phrase
    - analytic_dimension_label
  disallowed_patterns:
    - full_sentence_descriptions
    - evaluative_language
    - scoring_threshold_language
    - performance_level_references
    - outcome_predictions
  examples:
    - accountability attribution clarity
    - role boundary reasoning
    - institutional constraint awareness
    - systemic impact recognition
    - ethical tension articulation

constraints:
  - dimensions_must_be_grounded_in_analytic_brief_or_indicator_patterns
  - do_not_invent_new_concepts
  - do_not_assign_scores
  - do_not_define_performance_levels
  - do_not_generate_dimension_mapping_rules
  - do_not_generate_additional_sections
  - output_must_contain_only_one_fenced_block
  - table_must_follow_required_column_order

notes: |
  This prompt performs Stage 2.1 of Pipeline PL1B. It constructs the Layer 2 SBO
  Instance Registry representing conceptual evaluation dimensions. Dimensions
  are derived from analytic sub-spaces, candidate dimension sketches, and
  observed indicator patterns from the Layer 1 registry. The output corresponds
  to rubric template section 5.3 and must strictly follow identifier conventions
  defined in Rubric_SpecificationGuide_v*.
---

## Wrapper Prompt — Generate Layer 2 SBO Instance Registry (Stage 2.1)

### Prompt title and restrictions

This wrapper prompt generates the **Layer 2 SBO Instance Registry** for an assessment rubric.

The generated output corresponds to:

```
Rubric Template: 5.3 Layer 2 SBO Instances
```

This stage defines the **set of Layer 2 Score-Bearing Object (SBO) instances** that represent **conceptual evaluation dimensions** for each component.

This prompt **does not perform scoring** and **does not define dimension value derivation rules**.

The purpose is to produce the **dimension registry** used by downstream dimension scoring logic.

The generated output must conform to the identifier and authoring conventions in:

```
Rubric_SpecificationGuide_v*
```

If the analytic brief conflicts with the specification guide, the **specification guide takes precedence** for identifier formation and description authoring.

---

### Required input artefacts

Artefacts are separated using the delimiter:

```
===
```

Artefacts must appear in the following order:

```
===
Rubric_SpecificationGuide_v*
===
\<ASSESSMENT_ID\>_SubmissionAnalyticBrief_v*
===
Layer1_SBO_Registry
===
```

If any artefact is missing, malformed, or inconsistent, the prompt must produce **no output**.

---

### Objective

Using the **analytic scaffolding and stabilised indicator registry**, construct the **Layer 2 SBO Instance Registry**.

Each Layer 2 SBO instance corresponds to **one conceptual evaluation dimension** applied to a component response.

Dimensions must be derived from:

- analytic sub-spaces
- candidate dimension sketches from Stage 0
- clusters of related indicators
- conceptual evaluation goals described in the analytic brief

Dimensions represent **conceptual evaluation criteria**, not observable textual signals.

---

### Conceptual definition of a Layer 2 SBO instance

A Layer 2 SBO instance represents a **conceptual analytic dimension used to interpret indicator evidence**.

Examples of dimension concepts:

```
accountability attribution clarity
professional role boundary reasoning
institutional constraint awareness
systemic accessibility awareness
ethical tension articulation
```

Dimensions must capture **conceptual distinctions used to evaluate reasoning quality**.

They must **not encode performance levels**.

---

### Dimension design rules

Dimension SBO instances must:

- represent conceptual evaluation criteria
- integrate related indicator signals
- remain conceptually distinct from neighbouring dimensions
- remain interpretable across responses
- avoid encoding scoring thresholds
- avoid referencing performance categories

Dimensions should organise indicators into **coherent conceptual families**.

---

### Dimension count expectations

Typical dimension counts:

```
2–4 dimension SBO instances per component
```

If more candidate dimensions exist, the generator must **consolidate them into a coherent minimal conceptual structure**.

Dimensions should:

- capture the primary analytic evaluation axes
- minimise conceptual overlap
- remain clearly distinguishable

---

### Required fields

Each Layer 2 SBO instance must define the following fields:

```
sbo_identifier
sbo_identifier_shortid
assessment_id
component_id
dimension_id
sbo_short_description
```

Field meanings:

| field | description |
|---|---|
| `sbo_identifier` | canonical Layer 2 SBO identifier |
| `sbo_identifier_shortid` | compact short reference token |
| `assessment_id` | identifier of the assessment |
| `component_id` | canonical component identifier |
| `dimension_id` | rubric primitive identifier for the dimension |
| `sbo_short_description` | concise label describing the conceptual dimension |

---

### Identifier conventions

#### Dimension identifier (`dimension_id`)

Must follow the primitive identifier format:

```
D00 – D99
```

Rules:

- must begin with `D`
- must use two-digit numeric suffix
- must be globally unique
- must increment sequentially

Examples:

```
D01
D02
D03
```

---

#### Canonical SBO identifier

Layer 2 SBO identifiers must follow this structure:

```
D_<sid>_<cid>_<did>
```

Examples:

```
D_PPP_SecA_D01
D_PPP_SecB_D03
```

---

#### SBO short identifier

For Layer 2 SBO instances:

```
sbo_identifier_shortid = dimension_id
```

---

### sbo_short_description rules

Descriptions must:

- be concise
- use noun phrases
- distinguish conceptual evaluation dimensions
- avoid evaluative adjectives
- avoid sentence form

Preferred examples:

```
accountability attribution reasoning
role boundary interpretation
institutional constraint awareness
systemic impact reasoning
ethical tension articulation
```

---

### Consolidation rules

When generating the dimension registry:

1. Begin with candidate dimension sketches from Stage 0.
2. Compare with analytic sub-spaces.
3. Examine clusters of indicators from the Layer 1 registry.
4. Merge overlapping conceptual dimensions.
5. Preserve major analytic distinctions required for evaluating responses.

---

### Output format

The output must be emitted as a single **fenced Markdown block**.

The outer fence must use four backticks.

Inside that block emit exactly:

```
#### 5.3 Layer 2 SBO Instances (Draft)
```

followed by the registry table.

The table must use these columns in this exact order:

| sbo_identifier | sbo_identifier_shortid | assessment_id | component_id | dimension_id | sbo_short_description |

Rows must be grouped by `component_id`.

Within each component group:

- rows ordered by `dimension_id`
- identifiers sequential
- descriptions concise and parallel

---

### Generation procedure

The generator must:

1. Identify components present in the analytic brief.
2. Examine analytic sub-spaces and candidate dimension sketches.
3. Analyse clusters of related indicators from the Layer 1 registry.
4. Consolidate signals into conceptual dimensions.
5. Produce approximately **2–4 dimensions per component**.
6. Assign globally unique `dimension_id` values.
7. Construct identifiers using `D_<sid>_<cid>_<did>`.
8. Generate concise conceptual dimension labels.

---

### Output restrictions

The generated output must contain **only one fenced Markdown block**.

Inside that block it must contain only:

```
#### 5.3 Layer 2 SBO Instances (Draft)
```

followed by the table.

No commentary or explanatory text may appear outside the table.