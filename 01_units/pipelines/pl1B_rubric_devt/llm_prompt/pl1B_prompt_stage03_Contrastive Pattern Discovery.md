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
<ASSESSMENT_ID>_SubmissionAnalyticBrief_v*.md
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

Optional analytic sub-space subdivisions within sections must use **level 6 headings**.

This stage performs **analytic signal discovery only**.

All outputs remain **analytic hypotheses**.  
No rubric structures are created at this stage.

Indicator SBO instances and evaluation specifications are defined later during **Stage 1**.

---

## Input Artefact Format

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

## Artefact Validation Rules

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

6. Extract the analytic sub-space identifiers and analytic focus descriptions associated with that component.

Contrastive analysis must be performed **separately for each analytic sub-space**.

---

## Required Inputs

### Assignment Payload Specification

```text
<ASSESSMENT_ID>_AssignmentPayloadSpec_v01
```

Used to confirm valid `component_id` values.

### Submission Analytic Brief

```text
<ASSESSMENT_ID>_SubmissionAnalyticBrief_v01
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

## Signal Identification Rules

Signals must satisfy all of the following constraints.

### Rule 1 — Signals must be textual

Signals must correspond to **observable textual language patterns** that appear in the response text.

A valid signal must be detectable by locating specific wording or phrasing in the response.

Valid signal examples:

```text
explicit assignment of accountability to a specific actor
recognition that responsibility is distributed
description of responsibility hand-off
reference to institutional oversight
explicit reference to accessibility barriers
```

Invalid signal examples:

```text
student demonstrates sophisticated thinking
student recognises complexity
student shows ethical awareness
response reflects deeper reflection
```

Signals must describe **textual features**, not interpretations of student cognition.

---

### Rule 2 — Signals must be analytic-sub-space bounded

Each signal must be associated with **exactly one analytic sub-space**.

Signals must not be defined at the full component level unless the same signal clearly arises independently across multiple sub-spaces.

When a signal appears in multiple sub-spaces, record the signal separately for each sub-space.

---

### Rule 3 — Use contrastive response pairs

Signals must be derived from **contrastive response observations**.

Identify response pairs that approach the analytic task in **clearly different ways**, then extract signals that distinguish those approaches.

---

### Rule 4 — Limit signal proliferation

For each analytic sub-space extract between:

```text
4–10 candidate signals
```

If fewer than four signals appear in the calibration sample, include all detectable signals.

Do not produce large exhaustive signal inventories.

Focus on signals that clearly distinguish **different analytic approaches**.

---

### Rule 5 — Signals must be grounded in evidence

Each signal must be traceable to **quoted response language** in the calibration sample.

Short quotations should be used to demonstrate the observed signal.

---

## Output Requirements

The output must be emitted as a single **fenced Markdown block**.

The output must begin with:

```text
#### 5.<cid>
```

where `<cid>` is the detected component identifier.

The section must contain the following subsections using **level 5 headings**:

```text
##### 5.<cid>.1 Calibration sample description
##### 5.<cid>.2 Contrastive response observations
##### 5.<cid>.3 Candidate indicator signals
##### 5.<cid>.4 Candidate indicator set
##### 5.<cid>.5 Candidate dimension sketches (optional exploratory notes)
```

Where further internal structure is required, use **level 6 headings**.

Tables should be used instead of free-form prose wherever possible.

---

## Required Output Structure

### 5.<cid>.1 Calibration sample description

Insert the following boilerplate text with the detected component identifier substituted where required.

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

### 5.<cid>.2 Contrastive response observations

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
###### Analytic Sub-space: <sub-space_id> — <analytic focus>
```

For each sub-space, present observations using the table:

| analytic sub-space | pair | response A approach | response A example language | response B approach | response B example language | distinguishing signal |
|---|---|---|---|---|---|---|

Requirements:

- include the sub-space identifier and analytic focus in the first column
- identify multiple contrastive pairs where possible
- quote response language that reveals the difference
- keep quotations brief and evidentiary

---

### 5.<cid>.3 Candidate indicator signals

From the contrastive observations, extract **candidate signals**.

Present them in the following table:

| analytic sub-space | candidate signal | brief note on what is being detected |
|---|---|---|

Requirements:

- group rows by analytic sub-space
- signals must correspond to textual language patterns
- each signal must originate from observed response contrasts

---

### 5.<cid>.4 Candidate indicator set

Consolidate related signals into **candidate indicator statements**.

Candidate indicators must be phrased as **detectable textual properties of the response**.

Example formats:

```text
response explicitly assigns accountability to a specific actor
response recognises distributed responsibility across actors
response describes responsibility transfer or hand-off
response references institutional oversight
```

Present the consolidated indicators using:

| candidate indicator | source sub-space(s) | basis in extracted signals |
|---|---|---|

Do not assign final indicator identifiers.

These remain **candidate indicators** and will later be instantiated as **Layer 1 SBO instances during Stage 1**.

---

### 5.<cid>.5 Candidate dimension sketches (optional exploratory notes)

This section may only be produced if multiple signals clearly cluster around a shared conceptual theme.

Dimension sketches must remain **tentative analytic hypotheses**.

They must not:

- define scoring logic
- define dimension boundaries
- define evaluation thresholds
- introduce performance levels

Present sketches using:

| candidate dimension sketch | related signals | contributing sub-space(s) | rationale |
|---|---|---|---|

---

## Constraints

- Only use evidence present in `cleaned_response_text`.
- Signals must correspond to **observable textual language**.
- Do not introduce scoring thresholds.
- Do not reference rubric performance levels.
- Do not define dimension scoring rules.
- Ensure the generated section is valid Markdown and can be pasted directly into:

```text
<ASSESSMENT_ID>_SubmissionAnalyticBrief_v*.md
```

This stage performs **empirical signal discovery**, not rubric construction.

Indicator SBO instances and evaluation specifications will be created later during:

```text
Stage 1 — Indicator Discovery and Evaluation Design
```

---

## Final Validation

Before producing output, silently verify:

- every signal is grounded in quoted response language
- each signal belongs to a single analytic sub-space
- signals describe textual patterns rather than interpretations
- candidate indicators are traceable to extracted signals
- no scoring rules or performance levels have been introduced
- analytic sub-space identifiers match the Submission Analytic Brief
===
````
