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

#### Purpose
This prompt performs **contrastive pattern discovery** for **Stage 0.3 of Pipeline 1B** in the rubric construction workflow.

The goal is to identify **contrastive response patterns within each analytic sub-space** that will later support **human-verifiable Layer 1 SBO value derivation**.

This stage is now **load-bearing** because later Layer 1 SBO values are expected to support **fast human verification**, likely using a **binary presence / not-present decision surface**, with a later decision still to be made about whether a **triary full / partial / none surface** is necessary for some signal families.

Accordingly, this stage must do more than list candidate signals. It must surface:

- **clear positive patterns** that would likely count as sufficient explicit evidence
- **borderline or partial patterns** that may appear relevant but may not be sufficient for a binary verification decision
- **insufficient or misaligned patterns** that should not be treated as presence of the target signal
- **contrastive distinctions** that later help define verification thresholds

The output will populate a component-specific section of:

```text
<ASSESSMENT_ID>_SubmissionAnalyticBrief_v*.md
```

The generated output must be emitted as **fenced Markdown** and must use the following top-level section heading:

```text
#### 5.<cid>
```

Where:
- `<cid>` is determined from the calibration sample and must match a valid `component_id` in `<ASSESSMENT_ID>_AssignmentPayloadSpec_v*`
- all internal structure must use **level 5 and level 6 headings**
- subsection numbering must use the format:

```text
##### 5.<cid>.1
##### 5.<cid>.2
##### 5.<cid>.3
##### 5.<cid>.4
##### 5.<cid>.5
```

Optional analytic sub-space subdivisions within sections must use **level 6 headings**.

This stage performs **empirical contrastive pattern discovery only**.  
All outputs remain **analytic hypotheses**.  
No rubric structures are created at this stage.  
**Do not create candidate indicators, indicator SBO instances, score labels, thresholds, or evaluation specifications.**  
Those are defined later during **Stage 1**.

## Input Artefact Format
All required artefacts are provided in a **single sequence** separated by the delimiter:

```text
===
```

The delimiter separates artefacts.  
It does **not** wrap them.

Exactly **three artefacts** must appear, separated by this delimiter.

The structure must therefore be:

```text
<prompt text>
===
<document contents of <ASSESSMENT_ID>_AssignmentPayloadSpec_v*>
===
<document contents of <ASSESSMENT_ID>_SubmissionAnalyticBrief_v*>
===
<table containing:
submission_id
component_id
cleaned_response_text>
```

No additional artefacts may appear.

## Artefact Interpretation Rules
Artefacts must be interpreted **by position**.

| position | interpretation |
|---|---|
| Artefact 1 | `<ASSESSMENT_ID>_AssignmentPayloadSpec_v*` |
| Artefact 2 | `<ASSESSMENT_ID>_SubmissionAnalyticBrief_v*` |
| Artefact 3 | calibration sample dataset |

The delimiter `===` must therefore appear **exactly three times** in the payload.

## Artefact Validation Rules
Before performing any analysis:

### Validation 1 — Artefact count
Confirm that the input contains **exactly three artefacts** separated by the delimiter:

```text
===
```

If more or fewer artefacts are detected, **produce no output**.

### Validation 2 — Assignment payload specification
Verify that **Artefact 1** contains structural features consistent with an Assignment Payload Specification.

Expected elements include references to:

```text
assessment_id
component_id
component_ids
```

If the first artefact does not resemble an Assignment Payload Specification, **produce no output**.

### Validation 3 — Submission analytic brief
Verify that **Artefact 2** contains the Submission Analytic Brief and includes the section:

```text
Analytic Sub-space Identification
```

If the analytic sub-space registry cannot be located, **produce no output**.

### Validation 4 — Calibration dataset structure
Verify that **Artefact 3** is a dataset containing the fields:

```text
submission_id
component_id
cleaned_response_text
```

If any required field is missing, **produce no output**.

### Validation 5 — Target component detection
Determine the **target component** by examining the `component_id` values in the calibration dataset.

The dataset must contain **exactly one unique `component_id`**.

If multiple component identifiers are detected, **produce no output**.

### Validation 6 — Component registry verification
Verify that the detected `component_id` exists in the Assignment Payload Specification.

If the component does not exist in the registry, **produce no output**.

### Validation 7 — Analytic sub-space lookup
Using the detected `component_id`, locate the corresponding analytic sub-spaces in the Submission Analytic Brief.

Extract the following fields from the analytic sub-space registry:

```text
sub-space_id
analytic focus
```

Contrastive pattern discovery must then be conducted **separately for each analytic sub-space**.

## Required Inputs

### Assignment Payload Specification

```text
<ASSESSMENT_ID>_AssignmentPayloadSpec_v*
```

Used to confirm valid `component_id` values.

### Submission Analytic Brief

```text
<ASSESSMENT_ID>_SubmissionAnalyticBrief_v*
```

Used to obtain:
- analytic purpose of the component
- analytic sub-space registry

### Calibration Sample

Dataset structure:

| field | description |
|---|---|
| `submission_id` | de-identified student identifier |
| `component_id` | assignment component identifier |
| `cleaned_response_text` | student response text |

Typical calibration sample size:

```text
20–40 responses
```

Calibration samples are produced earlier in **Pipeline PL2** and represent filtered component-level datasets derived from the canonical grading dataset.

## Instructions
You are analysing a calibration sample of student responses to identify **contrastive response patterns** that will later support **human verification of Layer 1 analytic signals**.

Your task is to discover **observable textual patterns** that distinguish different ways students perform, partially perform, or fail to perform the task defined by each analytic sub-space.

Focus only on **analytic content**.

Ignore:
- writing style
- grammar
- verbosity
- fluency
- general writing quality

Only identify **patterns tied to the analytic expectations of the component**.

Contrastive analysis must be conducted **within each analytic sub-space separately**.

## Pattern Discovery Rules

### Rule 1 — Patterns must be textual
Patterns must correspond to **observable textual language patterns** that appear in the response text.

A valid pattern must be detectable by locating specific wording, phrasing, or explicit conceptual structure (entities, relationships, constraints)

Valid examples:

```text
explicit naming of two institutional demands
explicit statement that responsibility cannot be located in one role
description of one output produced by a tool
explicit boundary statement naming what cannot be determined
```

Invalid examples:

```text
student demonstrates sophisticated thinking
student seems aware of complexity
student probably understands the workflow
response reflects strong insight
```

Patterns must describe **response text**, not interpretations of student cognition.

### Rule 2 — Patterns must be analytic-sub-space bounded
Each discovered pattern must be associated with **exactly one analytic sub-space**.

Patterns must not be defined at the full component level unless the same pattern clearly arises independently across multiple sub-spaces.

When a similar pattern appears in multiple sub-spaces, record it separately for each sub-space.

### Rule 3 — Use contrastive response groupings
Patterns must be derived from **contrastive response observations**.

Within each analytic sub-space, identify differences among responses such as:

- clear and explicit execution
- partial, incomplete, or weakly grounded execution
- misaligned execution
- absent execution
- structurally compliant but analytically thin execution
- superficially similar but substantively different execution

### Rule 4 — Discover threshold-relevant contrasts
Because later Layer 1 design is being shifted toward **human verification**, this stage must explicitly surface contrasts relevant to later threshold-setting.

For each analytic sub-space, discover patterns that help distinguish:

- **likely sufficient explicit evidence**
- **borderline / partial evidence**
- **insufficient, vague, or misaligned evidence**

Do **not** convert these into score labels or final thresholds.  
Simply document the contrastive patterns.

### Rule 4A — Decompose patterns for later human verification

Because later Layer 1 design may use a binary human-verification surface, Stage 0.3 must surface distinctions at a finer level than broad pattern labels.

For each analytic sub-space:

- decompose broad response patterns into **atomic observable textual features** where possible
- distinguish **different borderline subtypes** if they would behave differently under later binary verification
- identify the **minimum textual configuration** that could plausibly count as presence of the pattern
- identify **false-positive or superficially compliant forms** that may look relevant but should not be treated as sufficient evidence

Atomic observable textual features may include:
- explicit naming of a required entity
- explicit naming of an institutional setting
- explicit naming of an operational process
- explicit in-scope / out-of-scope contrast markers
- explicit omitted-case-content statements
- explicit non-evaluative boundary markers

Do not turn these into formal indicators or scoring rules.
They remain empirical analytic observations used to support later Stage 1 design.
### Rule 5 — Limit proliferation
For each analytic sub-space, extract a manageable set of patterns.

Target range:

```text
3–8 contrastive patterns per analytic sub-space
```

If fewer than three meaningful patterns appear in the calibration sample, include all detectable patterns.

Do not produce exhaustive inventories.

### Rule 6 — Ground every pattern in quoted evidence
Every pattern must be traceable to **quoted response language** in the calibration sample.

Use short quotations only.

### Rule 7 — No indicator leakage
Do not convert patterns into formal indicator statements.

Do not write:
- “response explicitly does X” as a final candidate indicator set
- “detects Y”
- “should receive present / absent”
- “counts as full / partial / none”

This stage stops at **pattern discovery and verification-relevant analytic observation**.


## Conceptual Signal Constraint (Critical)

This stage must identify **conceptual analytic patterns**, not engagement or performance-quality signals.

### Definition — Conceptual signals

Conceptual signals refer to whether the response text:

- correctly identifies required analytic entities (e.g., institutional demands, mechanisms, workflow stages)
- correctly structures relationships among those entities (e.g., interaction, redistribution, constraint)
- correctly adheres to task-specific analytic constraints (e.g., non-evaluative stance, internal system focus)
- correctly instantiates required analytic forms (e.g., claim structure, demand pairing, boundary statements)

### Disallowed signal types (must not appear)

Do not produce patterns based on:

- writing quality (clarity, coherence, fluency)
- level of detail or completeness
- strength or persuasiveness of explanation
- perceived effort or engagement
- generic reasoning quality (e.g., “good analysis”, “strong thinking”)
- surface compliance without conceptual correctness

Invalid examples:

- “response is detailed”
- “response clearly explains”
- “response demonstrates strong reasoning”
- “response is well-structured”

### Required orientation

All patterns must instead be grounded in:

- what conceptual elements are present or missing
- how those elements are structurally related
- whether required analytic constraints are respected or violated

If a pattern cannot be tied to a **specific conceptual requirement of the task**, it must be excluded.
## Output Requirements
The output must be emitted as a single **fenced Markdown block**.

Fencing constraint (mandatory):

If the output contains any inner fenced code blocks using triple backticks (```),
the entire output must be wrapped in an outer fence using four backticks (````).

The outer fence must:

- open with: ````markdown
- close with: ````

All inner fences must remain triple backticks.

Failure to follow this rule invalidates the output.

The output must begin with:

```text
#### 5.<cid>
```

where `<cid>` is the detected component identifier.

The section must contain the following subsections using **level 5 headings**:

```text
##### 5.<cid>.1 Calibration sample description
##### 5.<cid>.2 Analytic sub-space registry
##### 5.<cid>.3 Contrastive pattern observations
##### 5.<cid>.4 Verification-relevant pattern summary
##### 5.<cid>.5 Stage 1 design implications
```

Where further internal structure is required, use **level 6 headings**.

Tables should be used instead of free-form prose wherever possible.

## Required Output Structure

### 5.`<cid>`.1 Calibration sample description
Insert the following boilerplate text with the detected component identifier substituted where required.

The calibration responses analysed in this section were produced during **Pipeline PL2**, which prepares component-level calibration datasets for rubric construction. Calibration datasets are derived from the canonical grading dataset defined in:

```text
<ASSESSMENT_ID>_AssignmentPayloadSpec_v*
```

Each dataset contains a filtered subset of responses for a specific component.

Dataset structure:

| field_name |
|---|
| `submission_id` |
| `component_id` |
| `cleaned_response_text` |

Calibration samples typically contain **20–40 responses** and are used exclusively for **analytic discovery and rubric development**.

The detected component for this section is:

```text
<cid>
```

### 5.`<cid>`.2 Analytic sub-space registry
Restate the analytic sub-spaces for the detected component.

Use the heading:

```text
###### Analytic Sub-space Registry
```

Then use the table:

| sub-space_id | analytic focus |
|---|---|

Populate this table using the analytic sub-space registry defined in the Submission Analytic Brief.

### 5.`<cid>`.3 Contrastive pattern observations

Perform contrastive analysis for each analytic sub-space separately.

Each analytic sub-space must be introduced using:

```text
###### Analytic Sub-space: <sub-space_id> — <analytic focus>
```

For each analytic sub-space, use the following three-part structure.

#### Part A — Contrastive observation table

Use the table:

| analytic sub-space | contrast group | response pattern description | example language | contrastive counterpart | counterpart example language | analytic difference observed |
|---|---|---|---|---|---|---|

Requirements:
- include multiple contrastive observations where possible
- keep quotations brief and evidentiary
- include patterns that help differentiate clear, borderline, and insufficient execution where the sample permits
- remain descriptive and empirical
- do not collapse distinct borderline forms into one row if they differ analytically

#### Part B — Atomic feature decomposition

After the contrastive observation table, insert the heading:

```text
###### Atomic feature decomposition: <sub-space_id> — <analytic focus>
```

Then use the table:

| broad pattern | atomic observable feature | example language | verification relevance |
|---|---|---|---|

Requirements:
- decompose broad patterns into smaller observable textual features where possible
- features must remain textual and directly observable
- features may include required entities, relationships, constraints, boundary markers, or structural forms
- do not convert features into formal indicators

#### Part C — Threshold-relevant edge forms

After the atomic feature table, insert the heading:

```text
###### Threshold-relevant edge forms: <sub-space_id> — <analytic focus>
```

Then use the table:

| edge-form class | description | example language | why this matters later |
|---|---|---|---|

Allowed values for `edge-form class`:
- `minimum plausible presence`
- `borderline subtype`
- `false-positive risk`

Requirements:
- `minimum plausible presence` identifies the smallest textual form that could plausibly be treated as presence
- `borderline subtype` distinguishes different partial forms that may behave differently under binary verification
- `false-positive risk` identifies superficially compliant or misleading forms that should not automatically count as presence
- remain descriptive only
- do not define scoring rules, thresholds, or evaluation decisions
### 5.`<cid>`.4 Verification-relevant pattern summary
For each analytic sub-space, summarise the discovered patterns in a way that will later support human verification design.

Use one subsection per analytic sub-space with the heading:

```text
###### Verification-relevant summary: <sub-space_id> — <analytic focus>
```

Then use the table:

| pattern class | discovered textual pattern | why it matters for later human verification |
|---|---|---|

Allowed values for `pattern class`:
- `likely sufficient explicit evidence`
- `borderline / partial evidence`
- `insufficient or misaligned evidence`

Requirements:
- do not assign scoring labels
- do not define thresholds
- do not define evaluation rules
- do identify the distinctions that later Stage 1 must preserve or resolve

### 5.`<cid>`.5 Stage 1 design implications
This section records only the implications of the discovered contrasts for later indicator and verification design.

Use the table:

| analytic sub-space | implication for Stage 1 |
|---|---|

Implications may include observations such as:
- later Layer 1 design will need to distinguish explicit structural naming from vague mention
- borderline responses cluster around incomplete linkage between mechanism and workflow stage
- later Stage 1 should decide whether partial forms are collapsed into absence or retained through multi-signal reconstruction
- human verification will require examples clarifying what counts as sufficient explicit evidence

Do **not**:
- define final indicators
- define binary or triary scoring rules
- define score thresholds
- define performance levels

## Constraints
- Only use evidence present in `cleaned_response_text`.
- Patterns must correspond to **observable textual language**.
- Do not introduce scoring thresholds.
- Do not reference rubric performance levels.
- Do not define dimension scoring rules.
- Do not create candidate indicators.
- Ensure the generated section is valid Markdown and can be pasted directly into:

```text
<ASSESSMENT_ID>_SubmissionAnalyticBrief_v*.md
```

This stage performs **empirical contrastive pattern discovery**, not rubric construction.

Formal indicator design and evaluation specification will be created later during:

```text
Stage 1 — Indicator Discovery and Evaluation Design
```

## Final Validation
Before producing output, silently verify:
- every discovered pattern is grounded in quoted response language
- each pattern belongs to a single analytic sub-space
- patterns describe textual features rather than interpretations of student cognition
- clear, borderline, and insufficient contrasts are surfaced where the sample supports them
- no scoring rules or performance levels have been introduced
- no candidate indicators have been created
- analytic sub-space identifiers match the Submission Analytic Brief
- outer fencing uses four backticks if any inner triple-backtick blocks are present
- broad patterns have been decomposed into smaller observable textual features where the sample supports this
- borderline patterns have been subdivided where different partial forms are visible
- minimum plausible presence forms have been surfaced where identifiable
- false-positive or superficially compliant forms have been surfaced where identifiable

===

  
