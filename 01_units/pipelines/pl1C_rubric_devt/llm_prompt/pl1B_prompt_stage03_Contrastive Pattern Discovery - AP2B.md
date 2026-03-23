---
prompt_id: pl1B_stage03_contrastive_pattern_prompt_v02
version: v02
stage: pipeline_pl1B_stage03
purpose: "perform contrastive pattern discovery on calibration responses to identify conceptual analytic patterns within analytic sub-spaces that support later human-verifiable signal design"
status: active
owner: EECS3000W26

input_contract:
  - "assignment_payload_specification (<ASSESSMENT_ID>_AssignmentPayloadSpec_v*)"
  - "submission_analytic_brief (<ASSESSMENT_ID>_SubmissionAnalyticBrief_v*)"
  - "calibration_sample_dataset (lines from csv)"

input_structure:
  delimiter: "==="
  artefacts:
    - name: assignment_payload_specification
      expected_elements:
        - assessment_id
        - component_id
        - component_ids
        - component_definitions_sufficient_to_validate_component_id
    - name: submission_analytic_brief
      required_section:
        - "Analytic Sub-space Identification"
      extracted_fields:
        - sub-space_id
        - analytic_focus
    - name: calibration_sample_dataset
      expected_columns:
        - submission_id
        - component_id
        - cleaned_response_text

output_contract:
  format: fenced_markdown_section
  fencing_rule: "outer fence must use four backticks if any inner triple-backtick fences are present"

output_structure:
  root_heading_pattern: "#### 5.<cid>"
  subsections:
    - "##### 5.<cid>.1 Calibration sample description"
    - "##### 5.<cid>.2 Analytic sub-space registry"
    - "##### 5.<cid>.3 Contrastive pattern observations"
    - "##### 5.<cid>.4 Verification-relevant pattern summary"
    - "##### 5.<cid>.5 Stage 1 design implications"

constraints:
  - patterns_must_describe_conceptual_analytic_features
  - patterns_must_be_observable_textual_features
  - patterns_must_be_bounded_to_analytic_subspace
  - patterns_must_be_supported_by_quoted_response_text
  - do_not_infer_student_cognition
  - do_not_evaluate_quality_or_performance_levels
  - do_not_define_scoring_rules
  - do_not_reference_rubric_performance_levels
  - do_not_generate_dimension_structures
  - do_not_generate_candidate_indicators
  - focus_on_conceptual_entities_relationships_and_constraints_only

notes: |
  This prompt performs Stage 0.3 contrastive pattern discovery for rubric construction.
  Patterns describe observable conceptual analytic structures in student responses, including
  entities, relationships, constraints, and required analytic forms.
  The goal is to surface contrastive patterns that will support later human-verifiable
  Layer 1 signal design without defining indicators or scoring rules.
---

## Prompt — Stage 0.3 Contrastive Pattern Discovery for Human-Verification-Oriented Signal Design
WRAPPER PROMPT — STAGE 0.3 CONTRASTIVE PATTERN DISCOVERY (AP2B)

From this assignment, student submissions consist of **three analytic claim statements** (`SectionB1Response`, `SectionB2Response`, `SectionB3Response`), each instantiating the **same analytic task**: analysing interaction between institutional demands using a fixed template.

You will receive a dataset of student submissions.

Your task is to perform **contrastive pattern discovery across all claim instances**, treating them as a **single pooled evidence surface**.

---

### Task definition (strict)

This is a **contrastive pattern discovery task**.

- Do **not** summarise submissions  
- Do **not** rewrite student text  
- Do **not** evaluate correctness in normative terms  
- Do **not** propose fixes or improvements  
- Do **not** introduce external concepts  

You must:

- identify **recurring analytic patterns and contrasts** in how the task is executed,  
- distinguish **strong, partial, and weak realisations** of the analytic move,  
- ground all observations in **explicit textual evidence patterns**.

---

### Unit of analysis

- The unit of analysis is the **individual claim statement**, not the submission.  
- You must treat all claims from:
  ```
  SectionB1Response  
  SectionB2Response  
  SectionB3Response
  ```
  as belonging to a **single pooled dataset**.

- Do **not** analyse components separately.  
- Do **not** assume differences between B1, B2, B3.

---

### Analytic focus

Each claim is expected to instantiate the following analytic structure:

- two **institutional demands**  
- one **mechanism or tool**  
- one **workflow stage or role**  
- one **structural effect (verb phrase)**  
- an explicit **interaction relation** (“interacts with … through … shaping … by …”)

Your task is to identify **how this structure is realised, mis-realised, or absent** across the dataset.

---

### Required output structure

Produce the following sections:

---

#### 1. Dominant analytic pattern (target structure)

Describe the **most complete and well-formed pattern** observed.

Include:
- how institutional demands are correctly identified,
- how interaction is expressed,
- how mechanisms and workflow stages are correctly anchored,
- how structural effects are realised.

This defines the **reference pattern** for the task.

---

#### 2. Contrastive pattern set

Identify **distinct recurring contrastive patterns**.

Each pattern must include:

- `pattern_id`: short identifier  
- `pattern_label`: concise descriptive name  
- `description`: what characterises this pattern  
- `contrast_with`: what it differs from (typically the dominant pattern or another pattern)  
- `evidence_signals`: observable textual features indicating this pattern  

Constraints:

- Patterns must be **empirically grounded** in repeated features across claims  
- Patterns must be **mutually distinguishable**  
- Avoid trivial variations (focus on analytically meaningful differences)

---

#### 3. Pattern grouping by analytic dimension

Organise patterns according to **analytic dimensions**, such as:

- institutional demand identification  
- mechanism/tool identification  
- interaction articulation  
- workflow anchoring  
- structural effect expression  
- constraint adherence (e.g., drift into evaluation)

For each dimension:
- list relevant patterns,
- describe the contrast spectrum (e.g., strong → weak → absent).

---

#### 4. Indicator candidate signals

From the contrastive patterns, derive **candidate indicator signals**.

Each signal should be:

- a **checkable textual property**,
- framed in terms of **presence/absence or quality of realisation**,
- suitable for later transformation into a scoring indicator.

Do not formalise as final indicators yet — this is a **pre-indicator layer**.

---

#### 5. Sub-space implication

Based on the patterns, state whether:

- a **single dominant analytic sub-space** is confirmed, or  
- multiple sub-spaces are evidenced.

For AP2B, explicitly evaluate whether variation reflects:
- **within-task execution differences**, or  
- **distinct analytic tasks**.

---

### Validation constraints

- All patterns must be grounded in **observable textual regularities**  
- Do **not** infer student intent  
- Do **not** use external knowledge  
- Do **not** collapse distinct patterns prematurely  
- Ensure patterns are **useful for downstream rubric construction**

---

### Output requirements

- Emit as **fenced Markdown only**  
- Use clear section headings exactly as specified  
- Do not include commentary outside the defined sections

---

===