# .
```
BEGIN GENERATION
```


three inputs
`<ASSESSMENT_ID>_SubmissionAnalyticBrief_v01.md`
`<ASSESSMENT_ID>_AssignmentPayloadSpec_v01`
Calibration Sample
# . 
````
## Prompt — Stage 0.3 Contrastive Signal Extraction

### Purpose

This prompt performs **contrastive signal extraction** for **Stage 0.3 of Pipeline 1B** in the rubric construction workflow.

The goal is to identify **observable textual signals in student responses** that distinguish analytically different response types within each **analytic sub-space**.

The output will populate the following section of:

```
<ASSESSMENT_ID>_SubmissionAnalyticBrief_v01.md
```

specifically the section:

```
4. Contrastive Pattern Discovery
```

and its subsections:

```
4.1 Calibration sample description
4.2 Contrastive response observations
4.3 Candidate indicator signals
4.4 Candidate indicator set
4.5 Candidate dimension sketches (optional)
```

This stage performs **analytic signal discovery only**.

All outputs remain **analytic hypotheses**.  
No rubric structures are created at this stage.

Indicator SBO instances and evaluation specifications are defined later during **Stage 1**.

---

## Input Artefact Format

All required artefacts must be provided verbatim and delimited using:

```
===
<ARTEFACT_NAME>
<content>
===
```

Artefacts must appear in the following order:

```
===
<ASSESSMENT_ID>_AssignmentPayloadSpec_v01
<document contents>
===

===
<ASSESSMENT_ID>_SubmissionAnalyticBrief_v01
<document contents>
===

===
CALIBRATION_SAMPLE_<COMPONENT_ID>
<table containing:
submission_id
component_id
cleaned_response_text>
===
```

---

## Artefact Validation Rules

Before performing any analysis:

1. Verify that the calibration dataset contains the fields:

```
submission_id
component_id
cleaned_response_text
```

2. Determine the **target component** by examining the `component_id` values in the calibration dataset.

3. Verify that the dataset contains **exactly one unique `component_id`**.

If multiple component values are detected, **produce no output**.

4. Using the detected `component_id`, locate the corresponding **analytic sub-spaces** in:

```
<ASSESSMENT_ID>_SubmissionAnalyticBrief_v01
```

5. Extract the analytic sub-space identifiers and descriptions associated with that component.

Contrastive analysis must be performed **separately for each analytic sub-space**.

---

## Required Inputs

The following materials are required for the analysis.

### Assignment Payload Specification

```
<ASSESSMENT_ID>_AssignmentPayloadSpec_v01
```

Used to confirm valid `component_id` values.

---

### Submission Analytic Brief

```
<ASSESSMENT_ID>_SubmissionAnalyticBrief_v01
```

Used to obtain:

- analytic purpose of the component
- analytic sub-space registry

---

### Calibration Sample

Dataset structure:

| field | description |
|---|---|
| `submission_id` | de-identified student identifier |
| `component_id` | assignment component identifier |
| `cleaned_response_text` | student response text |

Typical calibration sample size:

```
20–40 responses
```

Calibration samples are produced earlier in **Pipeline PL2** and represent filtered component-level datasets derived from the canonical grading dataset.

---

## Instructions

You are analysing a calibration sample of student responses to identify **contrastive analytic signals**.

Your task is to discover **observable textual signals** that distinguish different analytic approaches to the task defined by each analytic sub-space.

Focus only on **analytic content**.

Ignore:

- writing style
- grammar
- verbosity
- general writing quality

Only identify **signals tied to the analytic expectations of the component**.

Contrastive analysis must be conducted **within each analytic sub-space separately**.

---

## Output Structure

Produce output organised under the following headings.

---

### 4.1 Calibration sample description

Insert the following boilerplate text.

The calibration responses analysed in this section were produced during **Pipeline PL2**, which prepares component-level calibration datasets for rubric construction.

Calibration datasets are derived from the canonical grading dataset defined in:

```
<ASSESSMENT_ID>_AssignmentPayloadSpec_v01
```

Each dataset contains a filtered subset of responses for a specific component.

Dataset structure:

| field_name |
|---|
| `submission_id` |
| `component_id` |
| `cleaned_response_text` |

Calibration samples typically contain **20–40 responses** and are used exclusively for **analytic discovery and rubric development**.

---

### 4.2 Contrastive response observations

For each analytic sub-space:

1. Examine the responses in the calibration sample.
2. Identify **pairs of responses that approach the analytic task in clearly different ways**.

For each pair:

- briefly describe how the analytic approaches differ
- quote the response language that reveals the difference
- identify the **distinguishing signal**

Use the following structure.

```
Analytic Sub-space: <sub-space_id> — <analytic focus>

Pair <n>

Response A approach
<description>

Example language
"<quoted response text>"

Response B approach
<description>

Example language
"<quoted response text>"

Distinguishing signal
<short description of the observable signal>
```

Identify **multiple contrastive pairs** where possible.

---

### 4.3 Candidate indicator signals

From the contrastive observations, extract **candidate signals**.

Signals must correspond to **observable textual patterns**.

Examples:

```
explicit assignment of accountability
recognition of distributed responsibility
description of responsibility hand-off
explicit reference to regulatory oversight
```

Group signals by analytic sub-space.

---

### 4.4 Candidate indicator set

Consolidate similar signals into a **candidate indicator list**.

Candidate indicators should be phrased as **detectable textual properties of the response**.

Example format:

```
response explicitly assigns accountability to a specific actor
response identifies responsibility outside the professional role
response describes a responsibility hand-off
response references regulatory oversight
```

Do not assign final indicator identifiers.

These remain **candidate indicators** and will later be instantiated as **Layer 1 SBO instances** during Stage 1.

---

### 4.5 Candidate dimension sketches (optional)

If multiple signals appear to reflect a shared conceptual theme, record a **possible dimension sketch**.

Example format:

```
Candidate dimension cluster
Accountability framing

Signals
explicit assignment of accountability
recognition of distributed responsibility
description of responsibility transfer
```

These sketches are **conceptual hypotheses only** and do not define dimension structures.

---

## Constraints

- Only use evidence present in `cleaned_response_text`.
- Signals must correspond to **observable textual language**.
- Do not introduce scoring thresholds.
- Do not reference rubric performance levels.
- Do not define dimension scoring rules.

This stage performs **empirical signal discovery**, not rubric construction.

Indicator SBO instances and evaluation specifications will be created later during:

```
Stage 1 — Indicator Discovery and Evaluation Design
```
===
````
