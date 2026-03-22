---
prompt_id: pl1B_stage22_layer2_value_derivation_prompt_v01
version: v01
stage: pipeline_pl1B_stage22
purpose: generate the Layer 2 SBO Value Derivation specification describing how dimension scores are derived from indicator evidence
status: active
owner: EECS3000W26

input_contract:
  - rubric_specification_guide (Rubric_SpecificationGuide_v*)
  - layer1_sbo_registry (Rubric Template 5.4 Layer 1 SBO Instances)
  - layer2_sbo_registry (Rubric Template 5.3 Layer 2 SBO Instances)
  - submission_analytic_brief (\<ASSESSMENT_ID\>_SubmissionAnalyticBrief_v*)
  - trigger prompt (`BEGIN GENERATION`)
    
input_structure:
  delimiter: "==="
  artefacts:
    - name: rubric_specification_guide
      expected_elements:
        - layer2_value_derivation_structure
        - dimension_score_scale
        - mapping_rule_patterns
    - name: layer1_sbo_registry
      expected_elements:
        - indicator_registry
        - indicator_short_descriptions
        - component_identifier_list
    - name: layer2_sbo_registry
      expected_elements:
        - dimension_registry
        - dimension_short_descriptions
        - component_identifier_list
    - name: submission_analytic_brief
      extracted_elements:
        - analytic_sub_space_registry
        - candidate_dimension_sketches
        - candidate_indicator_signals

output_contract: fenced_markdown_blocks

output_structure:
  outer_fence: "`````"
  heading: "#### 6.2 Layer 2 SBO Value Derivation (Draft)"
  block_structure:
    - dimension_identifier
    - dimension_description
    - contributing_indicators
    - derivation_logic
    - interpretation_notes
  grouping_rule: group_blocks_by_component_id
  ordering_rules:
    - dimensions_follow_registry_order
    - indicators_listed_by_indicator_id

mapping_rules:
  dimension_score_scale:
    - evidence
    - partial_evidence
    - little_to_no_evidence
  permitted_rule_types:
    - indicator_presence
    - indicator_combination
    - indicator_threshold
  prohibited_rule_types:
    - performance_level_rules
    - component_score_references
    - outcome_predictions

derivation_logic_guidelines:
  design_principles:
    - dimensions_integrate_multiple_indicators
    - avoid_single_indicator_dimensions_when_possible
    - allow_indicator_membership_in_multiple_dimensions
  rule_patterns:
    evidence_condition:
      description: multiple indicators expressing the conceptual dimension are present
    partial_evidence_condition:
      description: limited or incomplete indicator evidence for the dimension
    little_to_no_evidence_condition:
      description: indicators supporting the dimension are absent

constraints:
  - must_reference_existing_indicators_only
  - must_reference_existing_dimensions_only
  - do_not_create_new_identifiers
  - do_not_assign_component_scores
  - do_not_define_performance_levels
  - do_not_generate_additional_sections
  - output_must_contain_only_one_fenced_block
  - blocks_must_follow_registry_dimension_order

notes: |
  This prompt performs Stage 2.2 of Pipeline PL1B. It constructs the Layer 2
  SBO Value Derivation specification that maps Layer 1 indicator evidence to
  Layer 2 dimension scores. The output corresponds to rubric template section
  6.2 and must strictly reference identifiers defined in sections 5.4 and 5.3.
---

## Wrapper Prompt — Generate Layer 2 Value Derivation Specification (Stage 2.2)

### Prompt title and restrictions

This wrapper prompt generates the **Layer 2 SBO Value Derivation specification** for an assessment rubric.

The generated output corresponds to:

```
Rubric Template: 6.2 Layer 2 SBO Value Derivation
```

This stage defines **how dimension scores are derived from Layer 1 indicator evidence**.

This prompt **does not modify the dimension registry** and **does not perform scoring**.

The purpose is to specify the **indicator → dimension evidence mapping rules** used by downstream scoring prompts.

The generated output must conform to identifier and authoring conventions defined in:

```
Rubric_SpecificationGuide_v*
```

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
Layer1_SBO_Registry
===
Layer2_SBO_Registry
===
\<ASSESSMENT_ID\>_SubmissionAnalyticBrief_v*
===
```

If any artefact is missing, malformed, or inconsistent, the prompt must produce **no output**.

---

### Objective

Using the **dimension registry (5.3)** and the **indicator registry (5.4)**, construct the **Layer 2 SBO Value Derivation specification**.

This specification defines:

```
dimension_score = f(indicator_evidence)
```

for each dimension.

Dimension scores are derived from indicator evidence patterns within the assessment artefact:

```
AA = submission_id × component_id
```

---

### Conceptual definition of Layer 2 value derivation

Layer 2 value derivation determines **how conceptual dimension evidence is inferred from indicator evidence**.

Indicators represent **observable textual signals**.

Dimensions represent **conceptual evaluation criteria**.

The derivation logic therefore maps **indicator patterns → conceptual dimension evidence**.

---

### Dimension scoring scale

Dimensions use the same evidence scale as indicators:

```
evidence
partial_evidence
little_to_no_evidence
```

Meaning:

| value | interpretation |
|---|---|
| evidence | strong conceptual support for the dimension |
| partial_evidence | limited or incomplete conceptual support |
| little_to_no_evidence | dimension not supported by indicator evidence |

---

### Derivation design rules

Derivation logic must:

- reference indicators from the Layer 1 registry
- reflect conceptual relationships described in the analytic brief
- remain interpretable and operationally simple
- avoid overly complex multi-condition rules

Indicators may contribute to **multiple dimensions**.

Dimensions should normally integrate **multiple indicators**.

Avoid dimensions defined by a single indicator unless analytically necessary.

---

### Typical derivation pattern

A dimension derivation block typically follows this structure:

```
Dimension: <dimension_id>
Conceptual dimension: <dimension description>

Indicators contributing to this dimension:
I01
I03
I05

Derivation logic:

evidence
Assign when multiple contributing indicators appear in the response.

partial_evidence
Assign when at least one contributing indicator appears but conceptual support remains limited.

little_to_no_evidence
Assign when none of the contributing indicators appear.
```

---

### Output format

The output must be emitted as a **single fenced Markdown block**.

The outer fence must use **five backticks**.

Inside the block emit exactly:

```
#### 6.2 Layer 2 SBO Value Derivation (Draft)
```

followed by one derivation block per dimension.

Each block must contain:

| element | description |
|---|---|
| Dimension identifier | `dimension_id` |
| Dimension description | `sbo_short_description` |
| Contributing indicators | list of relevant `indicator_id` values |
| Derivation logic | mapping from indicator evidence patterns to dimension_score |
| Interpretation notes | clarification of edge cases |

Dimensions must appear **in the same order as the Layer 2 registry (5.3)**.

Indicators must be referenced **exactly using their `indicator_id` values**.

---

### Generation procedure

The generator must:

1. Read the Layer 2 SBO registry.
2. Identify indicators conceptually related to each dimension.
3. Assign contributing indicators to each dimension.
4. Construct simple derivation logic mapping indicator evidence patterns to dimension evidence.
5. Ensure dimensions integrate related indicators coherently.
6. Ensure no new identifiers are introduced.

---

### Output restrictions

The generated output must contain **only one fenced Markdown block**.

Inside that block it must contain only:

```
#### 6.2 Layer 2 SBO Value Derivation (Draft)
```

followed by the derivation blocks.

No commentary or explanatory text may appear outside the fenced block.