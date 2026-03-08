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

#### Purpose

This prompt performs **contrastive signal extraction** for **Stage 0.3 of Pipeline 1B** in the rubric construction workflow.

The goal is to identify **observable textual signals in student responses** that distinguish analytically different response types within each **analytic sub-space**.

The output will populate a component-specific section of:

```text
<ASSESSMENT_ID>_SubmissionAnalyticBrief_v01.md
```

The generated output must be emitted as **fenced Markdown** and must use the following top-level section heading:

```text
#### 5.<cid>
```

Where:

- `<cid>` is determined from the calibration sample and must match a valid `component_id` in `<ASSESSMENT_ID>_AssignmentPayloadSpec_v01`
- all internal structure must use **level 5 and level 6 headings**
- subsection numbering must use the format:

```text
##### 5.<cid>.1
##### 5.<cid>.2
##### 5.<cid>.3
##### 5.<cid>.4
##### 5.<cid>.5
```

Optional analytic sub-space subdivisions within sections should use **level 6 headings**.

This stage performs **analytic signal discovery only**.

All outputs remain **analytic hypotheses**.  
No rubric structures are created at this stage.

Indicator SBO instances and evaluation specifications are defined later during **Stage 1**.

---

#### Input Artefact Format

All required artefacts must be provided verbatim and delimited using:

```text
===
<ARTEFACT_NAME>
<content>
===
```

Artefacts must appear in the following order:

```text
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

#### Artefact Validation Rules

Before performing any analysis:

1. Verify that the calibration dataset contains the fields:

```text
submission_id
component_id
cleaned_response_text
```

2. Determine the **target component** by examining the `component_id` values in the calibration dataset.

3. Verify that the dataset contains **exactly one unique `component_id`**.

If multiple component values are detected, **produce no output**.

4. Verify that the detected `component_id` exists in:

```text
<ASSESSMENT_ID>_AssignmentPayloadSpec_v01
```

5. Using the detected `component_id`, locate the corresponding **analytic sub-spaces** in:

```text
<ASSESSMENT_ID>_SubmissionAnalyticBrief_v01
```

6. Extract the analytic sub-space identifiers and descriptions associated with that component.

Contrastive analysis must be performed **separately for each analytic sub-space**.

---

#### Required Inputs

##### Assignment Payload Specification

```text
<ASSESSMENT_ID>_AssignmentPayloadSpec_v01
```

Used to confirm valid `component_id` values.

##### Submission Analytic Brief

```text
<ASSESSMENT_ID>_SubmissionAnalyticBrief_v01
```

Used to obtain:

- analytic purpose of the component
- analytic sub-space registry

##### Calibration Sample

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

---

#### Instructions

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

#### Output Requirements

The output must be emitted as a single **fenced Markdown block**.

The output must begin with:

```text
#### 5.<cid>
```

where `<cid>` is the detected component identifier.

The section must then contain the following subsections using **level 5 headings**:

```text
##### 5.<cid>.1 Calibration sample description
##### 5.<cid>.2 Contrastive response observations
##### 5.<cid>.3 Candidate indicator signals
##### 5.<cid>.4 Candidate indicator set
##### 5.<cid>.5 Candidate dimension sketches (optional)
```

Where further internal structure is required (for example analytic sub-space breakdowns), use **level 6 headings**.

Within the analytic sub-space subsections, organise the material using **tables** rather than free-form prose wherever possible.

---

#### Required Output Structure

##### 5.<cid>.1 Calibration sample description

Insert the following boilerplate text, adapted only by substituting the detected `component_id` where appropriate.

The calibration responses analysed in this section were produced during **Pipeline PL2**, which prepares component-level calibration datasets for rubric construction.

Calibration datasets are derived from the canonical grading dataset defined in:

```text
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

The detected component for this section is:

```text
<cid>
```

---

##### 5.<cid>.2 Contrastive response observations

For each analytic sub-space:

1. Examine the responses in the calibration sample.
2. Identify **pairs of responses that approach the analytic task in clearly different ways**.

Each analytic sub-space should be introduced using a **level 6 heading**.

Example:

```text
###### Analytic Sub-space: <sub-space_id> — <analytic focus>
```

For each sub-space, present the observations in a table with the following columns:

| analytic sub-space | pair | response A approach | response A example language | response B approach | response B example language | distinguishing signal |
|---|---|---|---|---|---|---|

Requirements:

- include the sub-space identifier and analytic focus in the first column
- identify **multiple contrastive pairs** where possible
- quote response language that reveals the difference
- keep quotations brief and evidentiary

---

##### 5.<cid>.3 Candidate indicator signals

From the contrastive observations, extract **candidate signals**.

Signals must correspond to **observable textual patterns**.

Examples:

```text
explicit assignment of accountability
recognition of distributed responsibility
description of responsibility hand-off
explicit reference to regulatory oversight
```

Present the signals in a table with the following columns:

| analytic sub-space | candidate signal | brief note on what is being detected |
|---|---|---|

Group rows by analytic sub-space.

---

##### 5.<cid>.4 Candidate indicator set

Consolidate similar signals into a **candidate indicator list**.

Candidate indicators should be phrased as **detectable textual properties of the response**.

Example format:

```text
response explicitly assigns accountability to a specific actor
response identifies responsibility outside the professional role
response describes a responsibility hand-off
response references regulatory oversight
```

Present the indicator set in a table with the following columns:

| candidate indicator | source sub-space(s) | basis in extracted signals |
|---|---|---|

Do not assign final indicator identifiers.

These remain **candidate indicators** and will later be instantiated as **Layer 1 SBO instances** during Stage 1.

---

##### 5.<cid>.5 Candidate dimension sketches (optional)

If multiple signals appear to reflect a shared conceptual theme, record a **possible dimension sketch**.

Present the sketches in a table with the following columns:

| candidate dimension sketch | related signals | contributing sub-space(s) | rationale |
|---|---|---|---|

These sketches are **conceptual hypotheses only** and do not define dimension structures.

---

#### Constraints

- Only use evidence present in `cleaned_response_text`.
- Signals must correspond to **observable textual language**.
- Do not introduce scoring thresholds.
- Do not reference rubric performance levels.
- Do not define dimension scoring rules.
- Ensure the generated section is valid Markdown and can be pasted directly into `<ASSESSMENT_ID>_SubmissionAnalyticBrief_v01.md`.

This stage performs **empirical signal discovery**, not rubric construction.

Indicator SBO instances and evaluation specifications will be created later during:

```text
Stage 1 — Indicator Discovery and Evaluation Design
```
===
````
