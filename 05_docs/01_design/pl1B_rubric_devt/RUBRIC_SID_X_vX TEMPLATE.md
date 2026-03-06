## RUBRIC_SID_X_vX TEMPLATE.md
### Rubric Payload Specification
`RUBRIC_<sid>_<status>_payload_v<version>.md`
### 0. Purpose
This document defines the **rubric payload** for an assignment.  
It is intended to be **self-contained** and provides all information required for automated evaluation.
The document specifies the scoring structures used by the grading pipeline, including:
- the **component registry** (assignment components being evaluated)
- the **dimension registry** (evaluation criteria applied to components)
- the **indicator registry** (observable evidence checks used to detect evidence in responses)
- the **indicator evidence scale**
- the **dimension evidence scale**
- **mapping tables** used to derive scores across scoring layers
This payload defines the **deterministic structures used by the scoring pipeline**.
Different scoring layers within the grading pipeline may consume different sections of this payload.  
Each layer may use the relevant structures to evaluate evidence and derive scores for the **Score-Bearing Objects (SBOs)** defined in the grading ontology.
The payload therefore contains the **authoritative structural definitions** required for scoring.  
All scoring behaviour must be derived only from the definitions and rules contained in this document.
The document must remain **self-contained**.  
A scoring system using this payload must not require external documents, historical context, or design commentary in order to interpret the rubric structures.
### 1. Ontological context
This rubric payload operates within a layered grading ontology.
**Assessment Artefact (AA)**: the portion of a student submission from which evidence is examined during a scoring pass.
**Score-Bearing Object (SBO)**: an analytic entity that receives a score derived from evidence found in an AA.
A **scoring layer** is a stage of evaluation that assigns scores to a particular type of SBO.
Evidence must be drawn **only from the defined Assessment Artefact**.
AA definitions:
```text
AA (Layers 1–3) = submission_id × component_id
AA (Layer 4)    = submission_id
```
Score-Bearing Objects are evaluated across four layers:
```text
Layer 1 → indicator SBOs
Layer 2 → dimension SBOs
Layer 3 → component SBOs
Layer 4 → submission SBO
```
The scoring architecture follows the invariant:
```text
AA → indicator SBO scores → dimension SBO scores → component SBO scores → submission SBO score
```
Individual scoring processes may operate on **a subset of these layers**, depending on the evaluation task.
### 2. Assignment identity
```text
assessment_id: <ASSESSMENT_ID>
rubric_version: <RUBRIC_VERSION>
```
Example:
```text
assessment_id: PPP
rubric_version: PPP_v1_2026W
```
### Component registry
Defines the **Layer 3 SBOs**.

| component_id | component_label |
|---|---|
| SectionAResponse | |
| SectionBResponse | |
| SectionCResponse | |
All component identifiers must match the **canonical population structure** used in the grading dataset.
### Dimension registry
Defines the **Layer 2 SBOs**.
Each row represents one dimension associated with a component.

| component_id | dimension_id | dimension_label |
|---|---|---|
| SectionAResponse | D1 | |
| SectionAResponse | D2 | |
| SectionAResponse | D3 | |
Constraints:
- `(component_id, dimension_id)` pairs must be unique
- dimension identifiers must remain stable across rubric versions
### Indicator registry
Defines the **Layer 1 SBOs**.
Indicators detect observable textual evidence within the AA.

| indicator_id | component_id | dimension_id | indicator_definition |
|---|---|---|---|
| I1 | SectionAResponse | D1 | |
| I2 | SectionAResponse | D1 | |
| I3 | SectionAResponse | D2 | |
Constraints:
- indicators must reference a valid `(component_id, dimension_id)`
- indicator identifiers must remain stable within a rubric version
### Indicator evidence scale

| indicator_evidence_status |
|---|
| evidence |
| partial_evidence |
| little_to_no_evidence |
Hierarchy:
```text
evidence > partial_evidence > little_to_no_evidence
```
### Dimension evidence scale

| dimension_evidence_level |
|---|
| Level 1 |
| Level 2 |
| Level 3 |
Hierarchy:
```text
Level 1 > Level 2 > Level 3
```
### Indicator → Dimension mapping
This section defines how **indicator evidence statuses determine dimension evidence levels**.
Mapping rules must satisfy:
- deterministic evaluation
- monotonic evidence hierarchy
- explicit logical conditions
Placeholder structure:
```text
<Indicator → Dimension Mapping Table Placeholder>
```
Interpretation rules:
```text
indicator conditions within a row are combined using AND
rows are evaluated top-to-bottom
the first satisfied row determines the dimension level
```
Fallback rule:
```text
if no condition is satisfied → dimension = Level 3
```
### Dimension → Component score mapping
Defines how **dimension evidence levels determine component scores**.
Placeholder structure:
```text
<Dimension → Component Mapping Table Placeholder>
```
Input:
```text
dimension evidence levels
(optional) response indicators
```
Output:
```text
component_score
```
### Component → Submission score mapping
Defines how **component scores determine the final submission score**.
Placeholder structure:
```text
<Component → Submission Mapping Table Placeholder>
```
Output:
```text
submission_score
```
### Score labels

| score_label              |
| ------------------------ |
| exceeds_expectations     |
| meets_expectations       |
| approaching_expectations |
| below_expectations       |
| not_demonstrated         |
These labels define the **Layer 3 and Layer 4 scoring outputs**.
### Hard boundary rules (optional)
Hard boundary rules may constrain score eligibility.
Example structure:
```text
<Hard Boundary Rule Placeholder>
```
Example logic:
```text
Eligibility for Meets expectations requires
two dimensions at Level 2 or higher
```
Boundary rules must operate only on **dimension or component scores**.
### Structural invariants
The following invariants must hold:
1. Every component must define its dimensions.
2. Every `(component_id, dimension_id)` pair must be unique.
3. Every `(component_id, indicator_id)` must reference a valid dimension.
4. Mapping tables must produce exactly one score outcome.
5. Evidence evaluation must operate only within the defined AA.
### Normative status
This document constitutes the **authoritative rubric payload** for the assignment.
All calibration artefacts, scoring prompts, and automated evaluation systems must reference these definitions exactly.
