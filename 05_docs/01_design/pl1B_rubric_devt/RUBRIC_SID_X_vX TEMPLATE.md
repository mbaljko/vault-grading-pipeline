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
These structures define the **deterministic scoring rules** used by the evaluation system.
Different scoring layers within the grading pipeline may consume different sections of this payload.  
Each layer evaluates evidence drawn from the relevant **Assessment Artefact (AA)** and assigns scores to the appropriate **Score-Bearing Objects (SBOs)** defined in the grading ontology.
This document therefore contains the **authoritative structural definitions required for scoring**.  
All scoring behaviour must be derived solely from the definitions and rules contained in this document.
The payload must remain **self-contained**.  
A scoring system using this payload must not require external documents, historical context, or design commentary in order to interpret the rubric structures.
### 1. Ontological context
This rubric payload operates within a layered grading ontology.
**Assessment Artefact (AA)**: the portion of a student submission from which evidence is examined during a scoring pass.
**Score-Bearing Object (SBO)**: an analytic entity that receives a score derived from evidence found in an AA.
#### 1.1 Scoring layer definition
A **scoring layer** is a stage of evaluation that assigns scores to a particular type of **Score-Bearing Object (SBO)**.
Each scoring layer evaluates evidence drawn from a defined **Assessment Artefact (AA)** and assigns scores to the SBOs associated with that layer.
#### 1.2 Evidence boundary rule
Evidence used during scoring must be drawn **only from the defined Assessment Artefact (AA)** for that scoring layer.
No evidence outside the AA may be used when assigning scores.
#### 1.3 Assessment Artefact (AA) specification by layer
The Assessment Artefact defines the portion of the submission from which evidence may be drawn.
```text
Layer 1 AA = submission_id × component_id
Layer 2 AA = submission_id × component_id
Layer 3 AA = submission_id × component_id
Layer 4 AA = submission_id
```
#### 1.4 Score-Bearing Objects by scoring layer
Each scoring layer assigns scores to a specific class of **Score-Bearing Object (SBO)**.
```text
Layer 1 → indicator SBOs
Layer 2 → dimension SBOs
Layer 3 → component SBOs
Layer 4 → submission SBO
```
#### 1.5 Score derivation invariant
Scores across layers follow a hierarchical derivation structure.
```text
AA → indicator SBO scores → dimension SBO scores → component SBO scores → submission SBO score
```
Higher-layer SBO scores may be derived from lower-layer SBO scores through mapping rules defined in this payload.
#### 1.6 Layer execution note
Not all scoring processes operate across all layers.
A scoring process may evaluate and assign scores at **one or more layers**, depending on the evaluation task and the structures consumed by that scoring stage.
### 2. Score-Bearing Object (SBO) registry
This table defines the Score-Bearing Objects used in the rubric payload.
Each row specifies an SBO type, its identifier structure, and the scale used to evaluate that SBO.

| layer | sbo_type   | score_name       | sbo_identifier_pattern | scale_type  | scale_name                    | sbo indentifier |
| ----- | ---------- | ---------------- | ---------------------- | ----------- | ----------------------------- | --------------- |
| 1     | indicator  | indicator_score  | `[I\|P]_sid_cid_iid`   | evidence    | `indicator_evidence_scale`    |                 |
| 2     | dimension  | dimension_score  | `[D\|Q]_sid_cid_did`   | evidence    | `dimension_evidence_scale`    |                 |
| 3     | component  | component_score  | `C_sid_cid`            | performance | `component_performance_scale` |                 |
| 4     | submission | submission_score | `S_sid`                | performance | submission_performance_scale  |                 |
### 2. Registries
#### 2.1 The Layer 4 registry — submission SBO
Defines the **Layer 4 Score-Bearing Object (SBO)** representing the full student submission.
```text
submission_id: <ASSESSMENT_ID>
rubric_version: <RUBRIC_VERSION>
```
Example:
```text
submission_id: PPP
rubric_version: PPP_v1_2026W
```
The Layer 4 SBO represents the **entire submission** and receives the final submission score.
#### 2.2 The Layer 3 registry — component SBOs
Defines the **Layer 3 SBOs** representing components of the submission.

| component_id | component_label |
|---|---|
| SectionAResponse | |
| SectionBResponse | |
| SectionCResponse | |
Constraints:
- component identifiers must match the canonical population structure used in the grading dataset
- each `(submission_id × component_id)` pair defines a Layer 3 Assessment Artefact
#### 2.3 The Layer 2 registry
#### 2.3.1 Layer 2 SBOs
Defines the **Layer 2 SBOs** representing rubric dimensions applied to components.

| component_id | dimension_id | dimension_label |
|---|---|---|
| SectionAResponse | D1 | |
| SectionAResponse | D2 | |
| SectionAResponse | D3 | |
Constraints:
- `(component_id, dimension_id)` pairs must be unique
- dimension identifiers must remain stable across rubric versions
#### 2.3.2 The Layer 2 dimension evidence scale

| dimension_evidence_level |
|---|
| Level 1 |
| Level 2 |
| Level 3 |
Hierarchy:
```text
Level 1 > Level 2 > Level 3
```
#### 2.4. The Layer 1 registry
#### 2.4.1 Layer 1 SBOs
Defines the **Layer 1 SBOs** used to detect observable evidence within the Assessment Artefact.

| indicator_id | component_id | dimension_id | indicator_definition |
|---|---|---|---|
| I1 | SectionAResponse | D1 | |
| I2 | SectionAResponse | D1 | |
| I3 | SectionAResponse | D2 | |
Constraints:
- indicators must reference a valid `(component_id, dimension_id)`
- indicator identifiers must remain stable within a rubric version
#### 2.4.1 Layer 1 indicator evidence scale for SBOs

| indicator_evidence_status |
|---|
| evidence |
| partial_evidence |
| little_to_no_evidence |
Hierarchy:
```text
evidence > partial_evidence > little_to_no_evidence
```
### 6. Indicator evidence scale

| indicator_evidence_status |
|---|
| evidence |
| partial_evidence |
| little_to_no_evidence |
Hierarchy:
```text
evidence > partial_evidence > little_to_no_evidence
```
### 7. Dimension evidence scale

| dimension_evidence_level |
|---|
| Level 1 |
| Level 2 |
| Level 3 |
Hierarchy:
```text
Level 1 > Level 2 > Level 3
```
### 8. Indicator → Dimension mapping
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
### 9. Dimension → Component score mapping
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
### 10. Component → Submission score mapping
Defines how **component scores determine the final submission score**.
Placeholder structure:
```text
<Component → Submission Mapping Table Placeholder>
```
Output:
```text
submission_score
```
### 11. Score labels

| score_label |
|---|
| exceeds_expectations |
| meets_expectations |
| approaching_expectations |
| below_expectations |
| not_demonstrated |
These labels define the **Layer 3 and Layer 4 scoring outputs**.
### 12. Hard boundary rules (optional)
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
### 13. Structural invariants
The following invariants must hold:
1. Every component must define its dimensions.
2. Every `(component_id, dimension_id)` pair must be unique.
3. Every `(component_id, indicator_id)` must reference a valid dimension.
4. Mapping tables must produce exactly one score outcome.
5. Evidence evaluation must operate only within the defined AA.
### 14. Normative status
This document constitutes the **authoritative rubric payload** for the assignment.
All calibration artefacts, scoring prompts, and automated evaluation systems must reference these definitions exactly.
