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

This stage converts the **Layer 1 indicator registry** into an **operational evaluation specification** describing how each indicator is detected in response text.

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

| column | purpose                                                                                                               |
| --------------------- | --------------------------------------------------------------------------------------------------------------------- |
| sbo_identifier | canonical identifier of the indicator SBO instance                                                                    |
| sbo_short_description | `sbo_short_description` must be copied verbatim from the Layer 1 SBO instance registry (Rubric Template Section 5.4). |
| indicator_definition | conceptual definition of the analytic signal                                                                          |
| assessment_guidance | operational guidance for detecting the signal                                                                         |
| evaluation_notes | clarifications, exclusions, or interpretive boundaries                                                                |

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

Component grouping must be derived exclusively from the `component_id`
field in the Layer 1 SBO instance registry contained in Section 5.4.

For each component:

1. Emit a section heading in Markdown:

##### Component: `\<component_id\>`

2. Immediately after the heading, emit a Markdown table with the schema defined above.

3. Populate one row for each indicator belonging to that component.

Indicators must appear in increasing `indicator_id` order as defined in the Layer 1 SBO instance registry.


---

# Indicator specification guidance

### Binary evaluation constraint (critical)

Layer 1 operates as a **binary signal detection layer**.

Each indicator must be evaluated as:

- 1 = clear, sufficient, explicit textual evidence
- 0 = absent, insufficient, vague, or ambiguous evidence

Accordingly:
-  “partial”, “weak”, “incomplete”, or “structurally insufficient” signals must be treated as **not present**
- evaluation guidance must support **fast and consistent human verification**
- guidance must reduce interpretive ambiguity at the threshold boundary

### Indicator class interpretation (core vs advanced)

Layer 1 indicators may include two structural classes:

- **Core indicators (I01–I69)** → detect minimum plausible presence of required analytic structure  
- **Advanced indicators (I90–I99)** → detect extended analytic structure that appears only in more developed responses  

These classes differ in the **type of structure required**, not in degree or quality.

Rules:

- Both classes remain **binary** (`present` / `not_present`)
- Advanced indicators must detect **additional structural elements**, not stronger execution of the same structure
- Core indicators must not require extended elaboration beyond minimum viable analytic structure

Interpretation for evaluators:

- Core indicators:  
  → satisfied by a **single clear instance** of the required structure

- Advanced indicators:  
  → satisfied only when **additional, explicitly articulated structure** is present  
  → absence of this additional structure must be treated as `not_present`, even if the core structure is correct

Do not:

- interpret advanced indicators as “better” or “stronger” versions of core indicators  
- assign `present` based on clarity, fluency, or persuasiveness  
- collapse advanced indicators into core indicator judgements
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

assessment_guidance must:

- describe what **counts as clear, explicit presence**
- distinguish this from:
  - vague mention
  - incomplete structure
  - implied but unstated relationships
- support a **yes/no verification decision without deliberation**

Example:

Look for language indicating that responsibility is shared across people, teams, institutions, or systems involved in computing work.


Additional requirement for advanced indicators (`I9x`):

- assessment guidance must specify the **additional structural elements required** beyond minimum presence
- guidance must make clear that:
  - a single instance is insufficient if the indicator requires **multiple elements, stages, or relations**
  - the structure must be **explicitly articulated**, not inferred

Example distinction:

- Core indicator:
  - “flags guide review order” → sufficient

- Advanced indicator:
  - requires:
    - multiple workflow stages OR
    - multiple distinct structuring effects OR
    - explicit multi-step mediation chain

Do not use language such as:
- “more detailed”
- “stronger explanation”
- “well-developed”

Instead specify:
- number of elements
- types of relations
- structural configuration required

---

### evaluation_notes

Clarifications or edge-case guidance.

These may include:

- distinctions between similar indicators
- cases where evidence should not be assigned
- reminders about interpretive boundaries

evaluation_notes must explicitly include:

- common **false-positive forms** that should not be counted as present
- clarification of **borderline cases that must be treated as not present**
- distinctions between this indicator and closely related indicators

Example:

Do not assign evidence when the response mentions teamwork without describing shared responsibility.


Additional requirement for advanced indicators (`I9x`):

evaluation_notes must explicitly clarify:

- what **minimal forms are insufficient** (even if correct at core level)
- what **partial extended structures** must still be treated as `not_present`
- how this indicator differs from:
  - the corresponding core indicator(s)
  - other advanced indicators

Typical exclusions to include:

- single-instance explanations where multiple are required
- generic statements of influence without structural differentiation
- repetition of the same structure rather than addition of new structure

Example:

Do not assign when the response correctly describes one mediation relationship but does not introduce additional stages, actors, or structuring mechanisms required by this indicator.

---

# Generation procedure

The generator must perform the following steps:

1. Read the Layer 1 SBO instance registry in **Rubric Template Section 5.4: Layer 1 SBO Instances**.
2. Identify each Layer 1 indicator SBO instance listed in Section 5.4.
3. Locate the corresponding analytic signals in the analytic brief.
4. Translate those signals into evaluation specifications, ensuring:
   - core indicators (`I01–I69`) are defined using **minimum viable structural presence**
   - advanced indicators (`I90–I99`) are defined using **additional required structural elements**
   For advanced indicators:
   - identify the extended-structure patterns from Stage 0.3
   - ensure the definition reflects **distinct structural additions**, not degree of explanation
   - ensure the signal cannot be satisfied by the corresponding core structure alone
5. Populate one row per indicator in the appropriate component table.

---

# Indicator class validation (pre-output check)

Before emitting the evaluation specification, verify:

- all indicators with `indicator_id` in the `I90–I99` range:
  - require additional structural elements beyond core indicators
  - cannot be satisfied by single-instance or minimal formulations

- no indicator encodes:
  - strength
  - quality
  - clarity
  - completeness

- all indicators remain:
  - binary verifiable
  - grounded in explicit textual evidence

If these conditions are not satisfied, the output is invalid and must not be produced.

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