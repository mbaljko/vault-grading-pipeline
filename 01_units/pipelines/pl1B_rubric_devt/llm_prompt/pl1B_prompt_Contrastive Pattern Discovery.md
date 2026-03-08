# .
```
BEGIN GENERATION
```

# .
````
## Prompt — Stage 0.3 Contrastive Signal Extraction
### Purpose
This prompt performs **contrastive signal extraction** for Stage 0.3 of the rubric construction pipeline.
The goal is to identify **observable textual signals in student responses** that distinguish analytically different response types within each **analytic sub-space**.
The output will populate the following section of:
```
<ASSESSMENT_ID>_SubmissionAnalyticBrief_v01.md
```
```
4. Contrastive Pattern Discovery and Candidate Indicator Sketches
```
specifically the subsections:
```
4.2 Contrastive response observations
4.3 Candidate indicator signals
4.4 Candidate indicator set
4.5 Candidate dimension sketches (optional)
```
This process **does not create rubric structures**.  
All outputs remain **analytic hypotheses**.
## Required Input Materials
The following artefacts must be provided.
### 1. Analytic Brief
```
<ASSESSMENT_ID>_SubmissionAnalyticBrief_v01.md
```
Required sections:
```
1. Overview — Analytic Goals and Conceptual Claims
2. Components
3. Analytic Sub-space Identification
```
The prompt must use:
- the analytic purpose of the component
- the analytic sub-space registry
### 2. Assignment Payload Specification
```
<ASSESSMENT_ID>_AssignmentPayloadSpec_v01
```
Used to confirm:
```
component_id values
```
### 3. Calibration Sample
Dataset structure:

| field | description |
|---|---|
| `submission_id` | de-identified student identifier |
| `component_id` | assignment component identifier |
| `cleaned_response_text` | student response text |
Typical size:
```
20–40 responses
```
Calibration dataset must be filtered for the **target component**.
Example:
```
component_id = SectionAResponse
```
### 4. Target Analytic Sub-space
The analytic sub-space description drawn from the analytic brief.
Example:
```
A1 — accountability locus (individual vs distributed responsibility)
```
## Instructions
You are analysing a calibration sample of student responses in order to identify **contrastive signals** within the following analytic sub-space.
```
<analytic_sub_space_id>
<analytic_sub_space_description>
```
Your task is to discover **observable textual signals that distinguish different analytic approaches to this sub-space**.
Follow the procedure below.
### Step 1 — Examine responses
Review all responses in the calibration sample for the specified component.
Focus only on the analytic task represented by the analytic sub-space.
Ignore:
- writing style
- grammar
- verbosity
- general writing quality
Focus only on **analytic content signals**.
### Step 2 — Identify contrastive response pairs
Identify **pairs of responses that approach the analytic task in clearly different ways**.
For each pair:
- briefly describe the difference in analytic approach
- quote the language in each response that reveals the difference
Use the following structure:
```
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
<short description of the textual signal>
```
### Step 3 — Extract candidate signals
From the contrastive pairs, derive **short textual signal descriptions**.
Signals must correspond to **observable language patterns**, not interpretations.
Examples:
```
explicit assignment of accountability
recognition of distributed responsibility
description of responsibility hand-off
explicit mention of regulatory oversight
```
Group signals under the analytic sub-space being analysed.
### Step 4 — Consolidate candidate indicators
Combine similar signals into a **candidate indicator set**.
Indicators should be phrased as **detectable textual properties of the response**.
Example format:
```
I? response explicitly assigns accountability to a specific actor
I? response identifies responsibility outside the professional role
I? response describes a responsibility hand-off
```
Do not assign final indicator identifiers.
These remain **candidate indicators**.
### Step 5 — Identify possible dimension clusters (optional)
If multiple signals appear to reflect a shared conceptual theme, note possible **candidate dimension clusters**.
Example:
```
Candidate dimension cluster
Accountability framing
Signals
explicit assignment of accountability
distributed responsibility recognition
responsibility transfer
```
These are only **conceptual hypotheses** and do not define dimensions yet.
## Output Structure
Produce output organised under the following headings.
```
4.2 Contrastive response observations
```
List contrastive response pairs and distinguishing signals.
```
4.3 Candidate indicator signals
```
List extracted signals grouped by analytic sub-space.
```
4.4 Candidate indicator set
```
List consolidated candidate indicators.
```
4.5 Candidate dimension sketches (optional)
```
List any observed clusters of signals that suggest possible conceptual dimensions.
## Constraints
- Only use evidence present in `cleaned_response_text`.
- Signals must correspond to **observable textual language**.
- Do not introduce scoring thresholds.
- Do not reference rubric performance levels.
- Do not define dimension scoring rules.
The goal is **empirical discovery of analytic signals**, not rubric construction.
Indicator SBO instances will be created later during:
```
Stage 1 — Indicator Discovery and Evaluation Design
```
````
