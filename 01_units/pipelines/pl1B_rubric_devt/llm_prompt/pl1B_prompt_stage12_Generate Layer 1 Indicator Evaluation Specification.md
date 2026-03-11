---
prompt_id: pl1B_stage12_layer1_indicator_evaluation_prompt_v01
version: v01
stage: pipeline_pl1B_stage12
purpose: generate the Layer 1 Indicator Evaluation Specification describing how each indicator is detected in student responses
status: active
owner: EECS3000W26

input_contract:
  - rubric_specification_guide (Rubric_SpecificationGuide_v*)
  - submission_analytic_brief (<ASSESSMENT_ID>_SubmissionAnalyticBrief_v*)
  - layer1_sbo_instance_registry (§5.4 Layer 1 SBO Instances)
  - trigger prompt (`BEGIN GENERATION`)

input_structure:
  delimiter: "==="
  artefacts:
    - name: rubric_specification_guide
      expected_elements:
        - layer1_sbo_identifier_structure
        - indicator_identifier_format
        - sbo_instance_authoring_rules
    - name: submission_analytic_brief
      required_sections:
        - "Contrastive Pattern Discovery"
      extracted_elements:
        - analytic_sub_space_registry
        - candidate_indicator_signals
        - candidate_indicator_sets
        - component_identifiers
    - name: layer1_sbo_instance_registry
      expected_elements:
        - sbo_identifier
        - sbo_short_description
        - submission_id
        - component_id
        - indicator_id

output_contract: fenced_markdown_tables

output_structure:
  outer_fence: "````"
  heading: "#### 6.1 Layer 1 SBO Value Derivation (Draft)"
  component_section_heading: "##### Component: <component_id>"
  table_columns:
    - sbo_identifier
    - sbo_short_description
    - indicator_definition
    - assessment_guidance
    - evaluation_notes
  grouping_rule: group_tables_by_component_id
  ordering_rules:
    - indicators_must_follow_registry_order
    - indicators_sorted_by_indicator_id_within_component

schema_invariants:
  - column_names_must_match_schema_exactly
  - column_order_must_not_change
  - each_indicator_sbo_instance_must_generate_exactly_one_row
  - every_indicator_from_section_54_must_appear_once
  - no_additional_columns_allowed
  - no_columns_may_be_omitted

indicator_specification_rules:
  indicator_definition:
    description: conceptual description of the analytic signal detected by the indicator
    requirements:
      - restate_indicator_meaning
      - describe_detected_analytic_concept
      - avoid_scoring_thresholds
      - avoid_performance_level_language
      - remain_conceptual_not_procedural
  assessment_guidance:
    description: operational guidance describing how the signal appears in response text
    requirements:
      - describe_typical_language_patterns
      - describe_forms_of_expression
      - avoid_keyword_list_generation
      - remain_generalised_detection_guidance
  evaluation_notes:
    description: clarifications or interpretive boundaries for evaluation
    allowed_content:
      - distinctions_between_similar_indicators
      - edge_case_guidance
      - exclusions_where_evidence_should_not_be_assigned
      - interpretive_boundary_reminders

generation_procedure:
  - read_layer1_sbo_instance_registry
  - identify_each_indicator_sbo_instance
  - locate_corresponding_signals_in_submission_analytic_brief
  - translate_signals_into_indicator_evaluation_specification
  - generate_one_table_row_per_indicator
  - group_rows_by_component_id

constraints:
  - do_not_modify_indicator_registry
  - do_not_assign_scores
  - do_not_create_dimension_structures
  - do_not_introduce_new_indicators
  - output_must_contain_only_one_fenced_block
  - component_tables_must_follow_required_schema

notes: |
  This prompt performs Stage 1.2 of Pipeline PL1B. It converts the Layer 1
  indicator registry into an operational evaluation specification describing
  how each indicator is detected in student responses. Each indicator from
  Section 5.4 is translated into a conceptual definition, detection guidance,
  and evaluation notes. The output corresponds to rubric template section 6.1
  and preserves the indicator registry unchanged.
---
## Wrapper Prompt — Generate Layer 1 Indicator Evaluation Specification (Stage 1.2)

### Prompt title and purpose

This wrapper prompt generates the **Layer 1 Indicator Evaluation Specification** for an assessment rubric.

The generated output corresponds to:

Rubric Template: 6.1 Layer 1 SBO Value Derivation (Draft)

This stage converts the **Layer 1 indicator registry** into an **operational evaluation specification** describing how each indicator is detected in student responses.

This prompt does **not modify the indicator registry** and does **not perform scoring**.

---

## Required input artefacts

All artefacts must be supplied verbatim and delimited using:

===
\<content\>

===


Artefacts must appear in the following order:

===
Rubric_SpecificationGuide_v*

===
\<ASSESSMENT_ID\>\_SubmissionAnalyticBrief\_v*

===
Rubric_Template: 5.4 Layer 1 SBO Instances

===

If any artefact is missing, malformed, or inconsistent, the prompt must produce **no output**.

---

# Output schema (authoritative)

The evaluation specification must be produced as **structured tabular data**.

Each indicator SBO instance corresponds to **exactly one row** in the evaluation specification table.

The table schema is:

| sbo_identifier | sbo_short_description | indicator_definition | assessment_guidance | evaluation_notes |
|---|---|---|---|---|

Column meanings:

| column | purpose                                                             |
| --------------------- | ------------------------------------------------------------------- |
| sbo_identifier | canonical identifier of the indicator SBO instance                  |
| sbo_short_description | sbo_short_description must be copied **verbatim** from Section 5.4. |
| indicator_definition | conceptual definition of the analytic signal                        |
| assessment_guidance | operational guidance for detecting the signal                       |
| evaluation_notes | clarifications, exclusions, or interpretive boundaries              |

### Schema invariants

The generated tables must obey the following rules:

1. Column names must appear **exactly as specified above**.
2. Column order must **not change**.
3. Each row must correspond to **exactly one indicator SBO instance**.
4. Every indicator from **Section 5.4 must appear exactly once**.
5. No indicator may be created that does not exist in Section 5.4.
6. No additional columns may be added.
7. No columns may be omitted.

---

# Table generation rules

Evaluation specifications must be emitted as **Markdown tables**.

Component grouping must be derived from the component_id field in the Layer 1 SBO instance registry.

For each component:

1. Emit a section heading in markdown
##### Component: `\<component_id\>`

2. Immediately after the heading, emit a Markdown table with the schema defined above.

3. Populate one row for each indicator belonging to that component.

Indicators must appear in increasing `indicator_id` order as defined in the Layer 1 SBO instance registry.


---

# Indicator specification guidance

### indicator_definition

A concise conceptual description of the analytic signal.

The definition should:

- restate the meaning of the indicator
- describe the analytic concept being detected
- avoid referencing scoring thresholds
- avoid referencing performance levels

The definition must remain **conceptual rather than procedural**.

Example:

Detects statements that attribute responsibility across multiple actors such as individuals, teams, institutions, or tools.

---

### assessment_guidance

Operational guidance describing **how the signal may appear in response text**.

This section should:

- describe the kinds of language that express the signal
- reference typical phrasing patterns where helpful
- remain general rather than enumerating exhaustive keyword lists

Example:

Look for language indicating that responsibility is shared across people, teams, institutions, or systems involved in computing work.

---

### evaluation_notes

Clarifications or edge-case guidance.

These may include:

- distinctions between similar indicators
- cases where evidence should not be assigned
- reminders about interpretive boundaries

Example:

Do not assign evidence when the response mentions teamwork without describing shared responsibility.

---

# Generation procedure

The generator must perform the following steps:

1. Read the Layer 1 SBO instance registry in **Rubric Template Section 5.4: Layer 1 SBO Instances**.
2. Identify each indicator SBO instance.
3. Locate the corresponding analytic signals in the analytic brief.
4. Translate those signals into evaluation specifications.
5. Populate one row per indicator in the appropriate component table.

---

# Output format

The output must be emitted as a **single fenced Markdown block**.

The outer fence must use **four backticks**.

The first line inside the fenced block must be exactly:

```
#### 6.1 Layer 1 SBO Value Derivation (Draft)
```

followed by the component sections and their tables.

No commentary or text may appear outside the tables except the component headings.

---

# Output restrictions

The generated output must contain **only one fenced block**.

Inside that block it must contain:

- the section heading
- component headings
- Markdown tables following the defined schema

Narrative indicator blocks must **not** be used.

===