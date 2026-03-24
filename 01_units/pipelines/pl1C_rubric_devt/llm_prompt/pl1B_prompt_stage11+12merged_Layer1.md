---
prompt_id: pl1B_stage11_layer1_sbo_registry_prompt_v01
version: v01
stage: pipeline_pl1B_stage11
purpose: generate the Layer 1 SBO Instance Registry by consolidating indicator-level analytic signals from the submission analytic brief
status: active
owner: EECS3000W26

input_contract:
  - rubric_specification_guide (Rubric_SpecificationGuide_v*)
  - submission_analytic_brief (<ASSESSMENT_ID>_SubmissionAnalyticBrief_v*)
  - trigger prompt (`BEGIN GENERATION`)
    
input_structure:
  delimiter: "==="
  artefacts:
    - name: rubric_specification_guide
      expected_elements:
        - layer1_sbo_identifier_structure
        - indicator_identifier_format
        - sbo_short_description_rules
    - name: submission_analytic_brief
      required_sections:
        - "Contrastive Pattern Discovery"
      extracted_elements:
        - analytic_sub_space_registry
        - candidate_indicator_signals
        - candidate_indicator_sets
        - component_identifiers

output_contract: fenced_markdown_table

output_structure:
  outer_fence: "````"
  heading: "#### 5.4 Layer 1 SBO Instances (Draft)"
  table_columns:
    - sbo_identifier
    - sbo_identifier_shortid
    - submission_id
    - component_id
    - indicator_id
    - sbo_short_description
  grouping_rule: group_rows_by_component_id
  ordering_rules:
    - indicator_id_must_be_globally_unique
    - indicator_id_must_be_sequential
    - rows_within_component_sorted_by_indicator_id

identifier_rules:
  submission_identifier_source: assessment_identifier
  component_identifier_source: canonical_component_id_from_analytic_brief
  component_short_identifier_mapping:
    SectionAResponse: SecA
    SectionBResponse: SecB
    SectionCResponse: SecC
    SectionDResponse: SecD
    SectionEResponse: SecE
  indicator_identifier_pattern: "I00-I99"
  sbo_identifier_pattern: "I_<sid>_<cid>_<iid>"
  sbo_identifier_shortid_rule: equals_indicator_id

indicator_generation_rules:
  expected_indicator_range_per_component: "4-8"
  indicator_source_priority:
    - candidate_indicator_set
    - candidate_indicator_signals
    - contrastive_pattern_observations
  consolidation_requirements:
    - merge_redundant_signals
    - preserve_key_analytic_distinctions
    - minimise_indicator_overlap
  indicator_properties:
    - must_be_observable_in_response_text
    - must_be_detectable_without_scoring
    - must_represent_single_signal
    - must_not_require_multiple_conditions

sbo_description_rules:
  description_type: compact_analytic_label
  allowed_forms:
    - noun_phrase
    - analytic_label
  disallowed_patterns:
    - full_sentence_descriptions
    - evaluative_language
    - scoring_threshold_language
    - performance_level_references
    - outcome_predictions
  examples:
    - distributed responsibility attribution
    - role boundary articulation
    - institutional constraint recognition
    - systemic accessibility barrier recognition
    - tension identification

constraints:
  - indicators_must_be_grounded_in_analytic_brief
  - do_not_invent_new_concepts
  - do_not_assign_scores
  - do_not_define_performance_levels
  - do_not_create_dimension_structures
  - do_not_generate_additional_sections
  - output_must_contain_only_one_fenced_block
  - table_must_follow_required_column_order

notes: |
  This prompt performs Stage 1.1 of Pipeline PL1B. It constructs the Layer 1 SBO
  Instance Registry used by downstream scoring prompts. Indicators are derived
  from the contrastive pattern discovery results in the submission analytic
  brief and represent detectable textual signals in student responses.
  The output corresponds to rubric template section 5.4 and must strictly
  follow identifier conventions defined in Rubric_SpecificationGuide_v*.
---
### Prompt title and purpose

This wrapper prompt generates the **canonical Layer 1 Indicator Registry (v01)** for an assessment rubric.

This stage merges:
- Stage 1.1 (Layer 1 SBO Instance Registry)
- Stage 1.2 (Layer 1 Indicator Evaluation Specification)

into a single unified output.

The generated registry is the **only authoritative source** for:
- Layer 1 SBO instances (Section 5.4)
- Layer 1 evaluation specification (Section 6.1)
- downstream scoring manifest
- downstream scoring prompts

This stage does **not perform scoring** and does **not assign performance levels**.

---

### Required input artefacts

Artefacts must be separated using the delimiter:

===
{content}
===

Artefacts must appear in the following order:

===
Rubric_SpecificationGuide_v*
===
{ASSESSMENT_ID}_SubmissionAnalyticBrief_v*
===

If any artefact is missing, malformed, or inconsistent, the prompt must produce **no output**.

---

### Artefact validation

The analytic brief must:

- contain Stage 0.3 contrastive pattern discovery results
- preserve distinctions between:
  - minimum plausible presence
  - extended-structure presence

If these distinctions are not present or not usable, the generator must produce **no output**.

---

### Objective

Using the analytic brief, construct a **canonical Layer 1 Indicator Registry**.

Each registry row must define:

- the indicator (SBO instance)
- its conceptual definition
- its operational detection guidance
- its evaluation boundaries

The registry must support:

- binary human verification (`present` / `not_present`)
- downstream rendering into rubric Sections 5.4 and 6.1
- downstream scoring manifest generation

---

### Conceptual definition

Each indicator represents a **detectable analytic signal in response text**.

Indicators must:

- be grounded in Stage 0.3 signals
- reflect explicit textual structure
- be independently verifiable
- avoid evaluative or performance-based language

---

### Core vs advanced indicator classes

Indicators must be divided into two classes:

#### Core analytic structure indicators (I01–I69)

- detect minimum plausible presence
- capture baseline analytic structure
- expected to saturate in competent responses

#### Advanced structural indicators (I90–I99)

- detect additional explicit structure
- must require structural additions (not better articulation)
- must remain binary verifiable

Invalid advanced indicators include:
- stronger explanation
- more detailed response
- higher-quality reasoning

---

### Layer 1 verification constraint (critical)

Each indicator must support a binary decision:

Is there clear, sufficient, explicit textual evidence that this signal is present?

Accordingly:

- vague, partial, or implied forms must be treated as `not_present`
- signals must require recognisable structure
- no reliance on interpretation of quality or strength

---

### Indicator design rules

Indicators must:

- correspond to observable textual signals
- be grounded in Stage 0.3 patterns
- avoid encoding performance or quality
- be distinguishable from neighbouring indicators
- require structural expression (not keyword presence)
- exclude ambiguous or borderline-trigger signals

#### Compoundness rule

- do not bundle unrelated signals
- advanced indicators may capture one coherent multi-part structure

---

### Indicator count expectations

Per component:

- 4–10 indicators total
- typically:
  - 3–6 core indicators
  - 2–4 advanced indicators (if supported)

---

### Required fields (registry schema)

Each indicator must include:

indicator_id  
sbo_identifier  
sbo_identifier_shortid  
assessment_id  
component_id  
sbo_short_description  
indicator_definition  
assessment_guidance  
evaluation_notes  
status  
introduced_in  
last_modified_in  
change_note  

---

### Identifier conventions

Must comply with `Rubric_SpecificationGuide_v*`.

#### indicator_id

- format: I00–I99  
- unique across rubric  
- sequential  
- ranges:
  - I01–I69 → core  
  - I90–I99 → advanced  

#### sbo_identifier

Format:

I_{sid}_{cid}_{iid}

#### sbo_identifier_shortid

- must equal `indicator_id`

---

### component_id mapping

Use canonical values from analytic brief:

| component_id | cid |
|---|---|
| SectionAResponse | SecA |
| SectionBResponse | SecB |
| SectionCResponse | SecC |
| SectionDResponse | SecD |
| SectionEResponse | SecE |

---

### field authoring rules

#### sbo_short_description

- concise noun phrase  
- no evaluative language  
- no sentence form  

#### indicator_definition

- conceptual description of the analytic signal  
- no procedural instructions  

#### assessment_guidance

- describes how signal appears in text  
- defines what counts as explicit presence  
- distinguishes from vague or implied forms  

For advanced indicators:
- must specify required additional structure  

#### evaluation_notes

- must include:
  - false positives  
  - borderline exclusions  
  - distinctions from similar indicators  

For advanced indicators:
- must specify insufficient forms  
- must clarify difference from core indicators  

---

### generation procedure

The generator must:

1. Identify all components in the analytic brief.  
2. Extract candidate signals from Stage 0.3 material.  
3. Separate signals into:
   - core (minimum plausible presence)  
   - advanced (extended structure)  
4. Consolidate overlapping signals without collapsing structural distinctions.  
5. Construct indicators satisfying all Layer 1 constraints.  
6. Assign identifiers:
   - core → I01–I69  
   - advanced → I90–I99  
7. Generate all required fields per indicator.  

---

### validation checks (must pass before output)

- all indicators support binary verification  
- no indicator encodes quality or strength  
- advanced indicators require additional structure  
- identifier ranges are respected  
- no duplication across indicators  
- both core and advanced classes are preserved where supported  

---

### output format

The output must be emitted as a single fenced Markdown block.

The outer fence must use four backticks.

Inside the block, output a single Markdown table only.

---

### table schema (authoritative)

| indicator_id | sbo_identifier | sbo_identifier_shortid | assessment_id | component_id | sbo_short_description | indicator_definition | assessment_guidance | evaluation_notes | status | introduced_in | last_modified_in | change_note |

Rules:

- column order must be exactly as above  
- all columns must be present  
- no additional columns allowed  
- one row per indicator  
- each indicator must appear exactly once  
- no empty cells  

---

### table construction rules

- rows must be grouped by `component_id`  
- within each component, rows must be ordered by `indicator_id`  
- identifiers must remain globally unique across the table  
- all identifier conventions must be respected  

---

### output restrictions

- output must contain only one fenced block  
- no commentary outside the block  
- no YAML  
- no rubric sections (5.4, 6.1)  
- no scoring manifest  
- no explanatory text  