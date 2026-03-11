---
prompt_id: pl1B_stage03A_engagement_signal_prompt_v01
version: v01
stage: pipeline_pl1B_stage03A
purpose: extract engagement signals from calibration responses to identify observable patterns of task engagement within analytic sub-spaces
status: active
owner: EECS3000W26

input_contract:
  - assignment_payload_specification
  - submission_analytic_brief
  - calibration_sample_dataset

input_structure:
  delimiter: "==="
  artefacts:
    - name: assignment_payload_specification
      expected_elements:
        - assessment_id
        - component_id
        - component_ids
        - response_field_name
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

output_contract: fenced_markdown_section

output_structure:
  root_heading_pattern: "#### 5.<cid>"
  subsections:
    - "##### 5.<cid>.1 Calibration sample description"
    - "##### 5.<cid>.2 Contrastive response observations"
    - "##### 5.<cid>.3 Candidate engagement signals"
    - "##### 5.<cid>.4 Candidate indicator set"

constraints:
  - signals_must_describe_engagement_patterns
  - signals_must_be_observable_textual_features
  - signals_must_be_bounded_to_analytic_subspace
  - signals_must_be_supported_by_quoted_response_text
  - do_not_infer_student_cognition
  - do_not_classify_conceptual_positions
  - do_not_define_scoring_rules
  - do_not_reference_rubric_performance_levels
  - do_not_generate_dimension_structures

notes: |
  This prompt performs Stage 0.3 engagement signal extraction for rubric construction.
  Signals describe observable ways students engage with the positioning task, not
  conceptual interpretations of the stance taken. Output is appended to the
  SubmissionAnalyticBrief under Section 5.<cid>.
---
## Prompt — Stage 0.3 Engagement Signal Extraction

#### Purpose

This prompt performs **engagement signal extraction** for **Stage 0.3 of Pipeline 1B** in the rubric construction workflow.

The goal is to identify **observable textual signals in student responses** that indicate **how students engage with the positioning task** within each **analytic sub-space**.

This stage does **not** extract signals about whether a student’s conceptual interpretation is correct, sophisticated, persuasive, or normatively desirable.

This stage is concerned with **engagement with the task-defined positioning dimensions**, not with evaluating the substance of the position taken.

The output will populate a component-specific section of:

```text
\<ASSESSMENT_ID\>_SubmissionAnalyticBrief_v\*.md
```

The generated output must be emitted as **fenced Markdown** and must use the following top-level section heading:

```text
#### 5.\<cid\>
```

Where:

- `\<cid\>` is determined from the calibration sample and must match a valid `component_id` in `\<ASSESSMENT_ID\>_AssignmentPayloadSpec_v\*`
- all internal structure must use **level 5 and level 6 headings**
- subsection numbering must use the format:

```text
##### 5.\<cid\>.1
##### 5.\<cid\>.2
##### 5.\<cid\>.3
##### 5.\<cid\>.4
```

Optional analytic sub-space subdivisions within sections must use **level 6 headings**.

This stage performs **engagement signal discovery only**.

All outputs remain **analytic hypotheses**.  
No rubric structures are created at this stage.

Indicator SBO instances and evaluation specifications are defined later during **Stage 1**.

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
\<prompt text\>
===
\<document contents of \<ASSESSMENT_ID\>_AssignmentPayloadSpec_v\*\>
===
\<document contents of \<ASSESSMENT_ID\>_SubmissionAnalyticBrief_v\*\>
===
\<table containing:
submission_id
component_id
cleaned_response_text\>
```

No additional artefacts may appear.

## Artefact Interpretation Rules

Artefacts must be interpreted **by position**.

| position | interpretation |
|---|---|
| Artefact 1 | `\<ASSESSMENT_ID\>_AssignmentPayloadSpec_v\*` |
| Artefact 2 | `\<ASSESSMENT_ID\>_SubmissionAnalyticBrief_v\*` |
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

Engagement signal extraction must then be conducted **separately for each analytic sub-space**.

## Required Inputs

### Assignment Payload Specification

```text
\<ASSESSMENT_ID\>_AssignmentPayloadSpec_v\*
```

Used to confirm valid `component_id` values.

### Submission Analytic Brief

```text
\<ASSESSMENT_ID\>_SubmissionAnalyticBrief_v\*
```

Used to obtain:

- analytic purpose of the component
- analytic sub-space registry
- any explicit framing that signals must be treated as **engagement signals**

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

You are analysing a calibration sample of student responses to identify **contrastive engagement signals**.

Your task is to discover **observable textual signals** that indicate **how students engage with the positioning task defined by each analytic sub-space**.

Focus only on **engagement with the task-defined positioning dimension**.

Ignore:

- writing style
- grammar
- verbosity
- general writing quality
- whether the student’s position is correct
- whether the student’s position is sophisticated
- whether the student’s position aligns with course views
- whether the student’s position is normatively desirable

Only identify **signals tied to degree, form, or pattern of engagement with the component task**.

Contrastive analysis must be conducted **within each analytic sub-space separately**.

## Engagement Signal Identification Rules

Signals must satisfy all of the following constraints.

### Rule 1 — Signals must be engagement signals, not conceptual-position signals

Signals must identify **how the student engages with the task**, not **which conceptual stance the student takes**.

Valid engagement signal types include:

- whether the response explicitly addresses the task-defined sub-space
- whether the response names a relevant actor, boundary, criterion, uncertainty, or hand-off point
- whether the response gives an interpretable basis for a claim
- whether the response articulates one side of a contrast without the other
- whether the response remains generic versus specifies the task dimension
- whether the response explicitly recognises uncertainty, coherence, or tension where the task asks for this
- whether the response stays in a professional and interpretive register rather than shifting into autobiography

Invalid signal types include:

- distributed responsibility interpretation
- human-centred responsibility interpretation
- anti-neutrality stance
- justice-as-distribution interpretation
- strong ethical orientation
- sophisticated sociotechnical understanding

Those are **conceptual interpretation signals**, not engagement signals.

### Rule 2 — Signals must be textual

Signals must correspond to **observable textual language patterns** that appear in the response text.

A valid signal must be detectable by locating specific wording or phrasing in the response.

Valid signal examples:

```text
response explicitly names a locus of accountability
response explicitly identifies a responsibility hand-off point
response explicitly states one or more professional obligations
response gives a concrete basis for recognising harm or exclusion
response explicitly identifies a tension across earlier sections
response explicitly states that no tension is perceived and names a coherent thread
response articulates uncertainty using task-relevant language
```

Invalid signal examples:

```text
student demonstrates sophisticated thinking
student recognises complexity
student shows ethical awareness
response reflects deeper reflection
response takes a strong justice stance
response adopts a systemic interpretation
```

Signals must describe **textual features of engagement**, not evaluations of student cognition and not summaries of conceptual position.

### Rule 3 — Signals must be analytic-sub-space bounded

Each signal must be associated with **exactly one analytic sub-space**.

Signals must not be defined at the full component level unless the same engagement signal clearly arises independently across multiple sub-spaces.

When a signal appears in multiple sub-spaces, record the signal separately for each sub-space.

### Rule 4 — Use contrastive response pairs

Signals must be derived from **contrastive response observations**.

Identify response pairs that engage the same sub-space in **clearly different ways**, then extract signals that distinguish those engagement patterns.

Useful contrasts include:

- explicit versus implicit engagement
- specific versus generic engagement
- bounded versus unbounded articulation
- direct response to the sub-space versus drift to adjacent material
- articulated uncertainty versus unqualified assertion
- identified hand-off point versus no hand-off point
- named criterion versus vague evaluative language
- explicit synthesis versus mere restatement

### Rule 5 — Limit signal proliferation

For each analytic sub-space extract between:

```text
4–10 candidate signals
```

If fewer than four signals appear in the calibration sample, include all detectable signals.

Do not produce large exhaustive signal inventories.

Focus on signals that clearly distinguish **different engagement patterns**.

### Rule 6 — Signals must be grounded in evidence

Each signal must be traceable to **quoted response language** in the calibration sample.

Short quotations should be used to demonstrate the observed signal.

### Rule 7 — Preserve the diagnostic posture

Because this assignment records **how students currently conceptualise computing practice**, engagement signals must not treat one conceptual position as intrinsically better than another.

The task is to detect whether the student has **engaged with the positioning dimension in an interpretable way**, not whether the position itself is strong, weak, correct, advanced, or course-aligned.

## Output Requirements

The output must be emitted as a single **fenced Markdown block**.

The output must begin with:

```text
#### 5.\<cid\>
```

where `\<cid\>` is the detected component identifier.

The section must contain the following subsections using **level 5 headings**:

```text
##### 5.\<cid\>.1 Calibration sample description
##### 5.\<cid\>.2 Contrastive response observations
##### 5.\<cid\>.3 Candidate engagement signals
##### 5.\<cid\>.4 Candidate indicator set
```

Where further internal structure is required, use **level 6 headings**.

Tables should be used instead of free-form prose wherever possible.

## Required Output Structure

### 5.\<cid\>.1 Calibration sample description

Insert the following boilerplate text with the detected component identifier substituted where required.

The calibration responses analysed in this section were produced during **Pipeline PL2**, which prepares component-level calibration datasets for rubric construction.

Calibration datasets are derived from the canonical grading dataset defined in:

```text
\<ASSESSMENT_ID\>_AssignmentPayloadSpec_v\*
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
\<cid\>
```

### 5.\<cid\>.2 Contrastive response observations

Before beginning analysis, restate the analytic sub-spaces for the detected component.

Use the following format.

```text
###### Analytic Sub-space Registry
```

| sub-space_id | analytic focus |
|---|---|

Populate this table using the analytic sub-space registry defined in the Submission Analytic Brief.

Then perform contrastive analysis for each analytic sub-space separately.

Each analytic sub-space must be introduced using:

```text
###### Analytic Sub-space: \<sub-space_id\> — \<analytic focus\>
```

For each sub-space, present observations using the table:

| analytic sub-space | pair | response A engagement pattern | response A example language | response B engagement pattern | response B example language | distinguishing engagement signal |
|---|---|---|---|---|---|---|

Requirements:

- include the sub-space identifier and analytic focus in the first column
- identify multiple contrastive pairs where possible
- quote response language that reveals the difference in engagement
- keep quotations brief and evidentiary
- describe contrasts in terms of **engagement pattern**, not conceptual correctness or conceptual stance quality

### 5.\<cid\>.3 Candidate engagement signals

From the contrastive observations, extract **candidate engagement signals**.

Present them in the following table:

| analytic sub-space | candidate engagement signal | brief note on what is being detected |
|---|---|---|

Requirements:

- group rows by analytic sub-space
- signals must correspond to textual language patterns
- each signal must originate from observed response contrasts
- signals must describe **engagement with the task**
- signals must not summarise substantive conceptual positions

### 5.\<cid\>.4 Candidate indicator set

Consolidate related signals into **candidate indicator statements**.

Candidate indicators must be phrased as **detectable textual properties of the response**.

Example formats:

```text
response explicitly identifies a locus of accountability
response explicitly describes where responsibility is handed off
response states one or more professional obligations
response provides a basis for recognising harm or exclusion
response explicitly identifies a tension across earlier sections
response explicitly states that earlier responses are coherent
response articulates uncertainty using task-relevant language
```

Present the consolidated indicators using:

| candidate indicator | source sub-space(s) | basis in extracted signals |
|---|---|---|

Do not assign final indicator identifiers.

These remain **candidate indicators** and will later be instantiated as **Layer 1 SBO instances during Stage 1**.

## Constraints

- Only use evidence present in `cleaned_response_text`.
- Signals must correspond to **observable textual language**.
- Signals must describe **engagement patterns**, not substantive conceptual positions.
- Do not introduce scoring thresholds.
- Do not reference rubric performance levels.
- Do not define dimension scoring rules.
- Do not infer hidden beliefs, motivations, or sophistication.
- Ensure the generated section is valid Markdown and can be pasted directly into:

```text
\<ASSESSMENT_ID\>_SubmissionAnalyticBrief_v\*.md
```

This stage performs **empirical engagement signal discovery**, not rubric construction.

Indicator SBO instances and evaluation specifications will be created later during:

```text
Stage 1 — Indicator Discovery and Evaluation Design
```

## Final Validation

Before producing output, silently verify:

- every signal is grounded in quoted response language
- each signal belongs to a single analytic sub-space
- signals describe **engagement patterns rather than conceptual interpretations**
- candidate indicators are traceable to extracted signals
- no scoring rules or performance levels have been introduced
- analytic sub-space identifiers match the Submission Analytic Brief
- Section `5.\<cid\>.5` does not appear

===