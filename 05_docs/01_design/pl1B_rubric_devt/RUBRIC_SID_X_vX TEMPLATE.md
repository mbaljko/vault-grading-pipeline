## RUBRIC_SID_X_vX TEMPLATE.md
### Rubric Payload Specification
### 0. Rubric Identifier
`RUBRIC_<sid>_<status>_payload_v<version>.md`

```text
submission_id: <ASSESSMENT_ID>
rubric_version: <RUBRIC_VERSION>
```
Example:
```text
submission_id: PPP
rubric_version: PPP_v1_2026W
```

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

| layer | sbo_type   | score_name       | sbo_identifier_pattern | scale_type  | scale_name                     | sbo indentifier |
| ----- | ---------- | ---------------- | ---------------------- | ----------- | ------------------------------ | --------------- |
| 1     | indicator  | indicator_score  | `[I\|P]_sid_cid_iid`   | evidence    | `indicator_evidence_scale`     | `<PLACEHOLDER>` |
| 2     | dimension  | dimension_score  | `[D\|Q]_sid_cid_did`   | evidence    | `dimension_evidence_scale`     | `<PLACEHOLDER>` |
| 3     | component  | component_score  | `C_sid_cid`            | performance | `component_performance_scale`  | `<PLACEHOLDER>` |
| 4     | submission | submission_score | `S_sid`                | performance | `submission_performance_scale` | `<PLACEHOLDER>` |
### 3. Scale registry

| scale_name                     | ordered | description                                   |
| ------------------------------ | ------- | --------------------------------------------- |
| `indicator_evidence_scale`     | true    | Evidence strength for indicator evaluation    |
| `dimension_evidence_scale`     | true    | Evidence strength for dimension evaluation    |
| `component_performance_scale`  | true    | Performance evaluation scale for a component  |
| `submission_performance_scale` | true    | Performance evaluation scale for a submission |
#### indicator_evidence_scale

| scale_value           |
| --------------------- |
| evidence              |
| partial_evidence      |
| little_to_no_evidence |
Hierarchy:
```
evidence > partial_evidence > little_to_no_evidence
```
#### dimension_evidence_scale

| scale_value                |
| -------------------------- |
| demonstrated               |
| partially_demonstrated     |
| little_to_no_demonstration |
Hierarchy:
```
demonstrated > partially_demonstrated > little_to_no_demonstration
```
#### component_performance_scale

| scale_value              |
| ------------------------ |
| exceeds_expectations     |
| meets_expectations       |
| approaching_expectations |
| below_expectations       |
| not_demonstrated         |
Hierarchy:
```
exceeds_expectations > meets_expectations > approaching_expectations > below_expectations > not_demonstrated
```

#### submission_performance_scale

| score_label |
|---|
| exceeds_expectations |
| meets_expectations |
| approaching_expectations |
| below_expectations |
| not_demonstrated |
Hierarchy:
```
exceeds_expectations > meets_expectations > approaching_expectations > below_expectations > not_demonstrated
```

### 4. Registry of Specific Score-Bearing Objects (SBOs)
#### 4.1 Layer 4 SBO

Defines the **Layer 4 Score-Bearing Object (SBO)** representing the full student submission.

| layer | sbo_type   | score_name       | sbo_identifier_pattern | scale_type  | scale_name                     | sbo indentifier   |
| ----- | ---------- | ---------------- | ---------------------- | ----------- | ------------------------------ | ----------------- |
| 4     | submission | submission_score | `S_sid`                | performance | `submission_performance_scale` | `<ASSESSMENT_ID>` |
##### Example

| layer | sbo_type   | score_name       | sbo_identifier_pattern | scale_type  | scale_name                     | sbo indentifier | sbo_short_description                     |
| ----- | ---------- | ---------------- | ---------------------- | ----------- | ------------------------------ | --------------- | ----------------------------------------- |
| 4     | submission | submission_score | `S_sid`                | performance | `submission_performance_scale` | `S_PPP`         | Pre-Practice Positioning (PPP) Assignment |

##### OLDER
```text
submission_id: <ASSESSMENT_ID>
```
Example:
```text
submission_id: PPP
```
This is the  Layer 4 SBO.
It represents the **entire submission** and receives the final submission score.
#### 4.2 Layer 3 SBO
Defines the **Layer 3 SBOs** representing components of the submission.

| layer | sbo_type  | score_name      | sbo_identifier_pattern | scale_type  | scale_name                    | sbo indentifier |
| ----- | --------- | --------------- | ---------------------- | ----------- | ----------------------------- | --------------- |
| 3     | component | component_score | `C_sid_cid`            | performance | `component_performance_scale` | `<PLACEHOLDER>` |
| 3     | component | component_score | `C_sid_cid`            | performance | `component_performance_scale` | `<PLACEHOLDER>` |
| 3     | component | component_score | `C_sid_cid`            | performance | `component_performance_scale` | `<PLACEHOLDER>` |
| 3     | component | component_score | `C_sid_cid`            | performance | `component_performance_scale` | `<PLACEHOLDER>` |
| 3     | component | component_score | `C_sid_cid`            | performance | `component_performance_scale` | `<PLACEHOLDER>` |
##### Constraints:
- component identifiers must match the canonical population structure used in the grading dataset
- each `(submission_id × component_id)` pair defines a Layer 3 Assessment Artefact



##### Example

| layer | sbo_type  | score_name      | sbo_identifier_pattern | scale_type  | scale_name                    | sbo indentifier | sbo_short_description |
| ----- | --------- | --------------- | ---------------------- | ----------- | ----------------------------- | --------------- | --------------------- |
| 3     | component | component_score | `C_sid_cid`            | performance | `component_performance_scale` | `C_PPP_SECA`    | SectionAResponse      |
| 3     | component | component_score | `C_sid_cid`            | performance | `component_performance_scale` | `C_PPP_SECB`    | SectionBResponse      |
| 3     | component | component_score | `C_sid_cid`            | performance | `component_performance_scale` | `C_PPP_SECC`    | SectionCResponse      |
| 3     | component | component_score | `C_sid_cid`            | performance | `component_performance_scale` | `C_PPP_SECD`    | SectionDResponse      |
| 3     | component | component_score | `C_sid_cid`            | performance | `component_performance_scale` | `C_PPP_SECE`    | SectionEResponse      |

##### OLDER

| component_id | component_label |
|---|---|
| SectionAResponse | |
| SectionBResponse | |
| SectionCResponse | |

#### 4.3 Layer 2 SBO
Defines the **Layer 2 SBOs** representing rubric dimensions applied to components.

| layer | sbo_type  | score_name      | sbo_identifier_pattern | scale_type | scale_name                 | sbo indentifier |
| ----- | --------- | --------------- | ---------------------- | ---------- | -------------------------- | --------------- |
| 2     | dimension | dimension_score | `[D\|Q]_sid_cid_did`   | evidence   | `dimension_evidence_scale` | `<PLACEHOLDER>` |
| 2     | dimension | dimension_score | `[D\|Q]_sid_cid_did`   | evidence   | `dimension_evidence_scale` | `<PLACEHOLDER>` |
| 2     | dimension | dimension_score | `[D\|Q]_sid_cid_did`   | evidence   | `dimension_evidence_scale` | `<PLACEHOLDER>` |
| 2     | dimension | dimension_score | `[D\|Q]_sid_cid_did`   | evidence   | `dimension_evidence_scale` | `<PLACEHOLDER>` |
| 2     | dimension | dimension_score | `[D\|Q]_sid_cid_did`   | evidence   | `dimension_evidence_scale` | `<PLACEHOLDER>` |

Constraints:
- `(component_id, dimension_id)` pairs must be unique
- dimension identifiers must remain stable across rubric versions
##### EXAMPLE

| layer | sbo_type  | score_name      | sbo_identifier_pattern | scale_type | scale_name                 | sbo indentifier | sbo_short_description      |
| ----- | --------- | --------------- | ---------------------- | ---------- | -------------------------- | --------------- | -------------------------- |
| 2     | dimension | dimension_score | `[D\|Q]_sid_cid_did`   | evidence   | `dimension_evidence_scale` | `D_PPP_SECA_D1` | Accountability framing     |
| 2     | dimension | dimension_score | `[D\|Q]_sid_cid_did`   | evidence   | `dimension_evidence_scale` | `D_PPP_SECA_D2` | Role boundary and hand-off |
| 2     | dimension | dimension_score | `[D\|Q]_sid_cid_did`   | evidence   | `dimension_evidence_scale` | `D_PPP_SECA_D3` | Professional obligations   |
| 2     | dimension | dimension_score | `[D\|Q]_sid_cid_did`   | evidence   | `dimension_evidence_scale` | `D_PPP_SECA_Q1` | Component Coherence        |
| 2     | dimension | dimension_score | `[D\|Q]_sid_cid_did`   | evidence   | `dimension_evidence_scale` | `D_PPP_SECA_Q1` | Component Specificity      |

##### OLDER

| component_id | dimension_id | dimension_label |
|---|---|---|
| SectionAResponse | D1 | |
| SectionAResponse | D2 | |
| SectionAResponse | D3 | |

#### 4.4 Layer 1 SBO
Defines the **Layer 1 SBOs** used to detect observable evidence within the Assessment Artefact.

| layer | sbo_type  | score_name      | sbo_identifier_pattern | scale_type | scale_name                 | sbo indentifier |
| ----- | --------- | --------------- | ---------------------- | ---------- | -------------------------- | --------------- |
| 1     | indicator | indicator_score | `[IP]_sid_cid_iid`     | evidence   | `indicator_evidence_scale` | `<PLACEHOLDER>` |
| 1     | indicator | indicator_score | `[I\|P]_sid_cid_iid`   | evidence   | `indicator_evidence_scale` | `<PLACEHOLDER>` |
| 1     | indicator | indicator_score | `[I\|P]_sid_cid_iid`   | evidence   | `indicator_evidence_scale` | `<PLACEHOLDER>` |
| 1     | indicator | indicator_score | `[I\|P]_sid_cid_iid`   | evidence   | `indicator_evidence_scale` | `<PLACEHOLDER>` |
Constraints:
- indicators must reference a valid `(component_id, dimension_id)`
- indicator identifiers must remain stable within a rubric version

##### EXAMPLE


| layer | sbo_type  | score_name      | sbo_identifier_pattern | scale_type | scale_name                 | sbo indentifier | sbo_short_description                                             |
| ----- | --------- | --------------- | ---------------------- | ---------- | -------------------------- | --------------- | ----------------------------------------------------------------- |
| 1     | indicator | indicator_score | `[IP]_sid_cid_iid`     | evidence   | `indicator_evidence_scale` | `I_PPP_SECA_I1` | Accountability framing is explicitly stated                       |
| 1     | indicator | indicator_score | `[I\|P]_sid_cid_iid`   | evidence   | `indicator_evidence_scale` | `I_PPP_SECA_I2` | Accountability framing is minimally supported                     |
| 1     | indicator | indicator_score | `[I\|P]_sid_cid_iid`   | evidence   | `indicator_evidence_scale` | `I_PPP_SECA_I3` | Inside-the-role content is specified                              |
| 1     | indicator | indicator_score | `[I\|P]_sid_cid_iid`   | evidence   | `indicator_evidence_scale` | `I_PPP_SECA_I4` | Outside-the-role content is specified                             |
| 1     | indicator | indicator_score | `[I\|P]_sid_cid_iid`   | evidence   | `indicator_evidence_scale` | `I_PPP_SECA_I5` | Hand-off boundary is articulated                                  |
| 1     | indicator | indicator_score | `[I\|P]_sid_cid_iid`   | evidence   | `indicator_evidence_scale` | `I_PPP_SECA_I6` | Professional obligations in a non-licensure field are articulated |
| 1     | indicator | indicator_score | `[I\|P]_sid_cid_iid`   | evidence   | `indicator_evidence_scale` | `I_PPP_SECA_P1` | Coherence                                                         |
| 1     | indicator | indicator_score | `[I\|P]_sid_cid_iid`   | evidence   | `indicator_evidence_scale` | `I_PPP_SECA_P2` | Specificity                                                       |


### 5. SBO Instructions

#### 5.1 Layer 1 SBO Value Derivation, AA → `indicator_score` 

| sbo identifier  | Nickname | indicator_definition                                              | assessment guidance                                                                                                                           |
| --------------- | -------- | ----------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| `I_PPP_SECA_I1` | `I1`     | Accountability framing is explicitly stated                       | Determine whether the response **explicitly identifies where accountability resides** in the sociotechnical situation.                        |
| `I_PPP_SECA_I2` | `I2`     | Accountability framing is minimally supported                     | Determine whether the response provides **at least one supporting reason or explanation** justifying the accountability framing.              |
| `I_PPP_SECA_I3` | `I3`     | Inside-the-role content is specified                              | Determine whether the response identifies **at least one responsibility or activity that falls within the role of a computing professional**. |
| `I_PPP_SECA_I4` | `I4`     | Outside-the-role content is specified                             | Determine whether the response identifies **at least one responsibility outside the professional role**.                                      |
| `I_PPP_SECA_I5` | `I5`     | Hand-off boundary is articulated                                  | Determine whether the response **explicitly describes the boundary where responsibility transitions to another actor**.                       |
| `I_PPP_SECA_I6` | `I6`     | Professional obligations in a non-licensure field are articulated | Determine whether the response identifies **at least one obligation or responsibility applying to computing professionals**.                  |
| `I_PPP_SECA_P1` | `P1`     | Coherence                                                         | Determine whether the response is **readable, internally consistent, and logically structured**.                                              |
| `I_PPP_SECA_P2` | `P2`     | Specificity                                                       | Determine whether the response includes **at least one concrete, checkable claim** rather than purely generic statements.                     |

#### 5.2 Layer 2 SBO Value Derivation, `indicator_score` → `dimension_score` mapping

##### Registry Summary (All Require Threshold Tables)

| sbo indentifier | sbo_short_description      |
| --------------- | -------------------------- |
| `D_PPP_SECA_D1` | Accountability framing     |
| `D_PPP_SECA_D2` | Role boundary and hand-off |
| `D_PPP_SECA_D3` | Professional obligations   |
| `D_PPP_SECA_Q1` | Component Coherence        |
| `D_PPP_SECA_Q1` | Component Specificity      |

##### Minimum Threshold Table:  `D_PPP_SECA_D1`

| sbo indentifier | sbo_short_description  |
| --------------- | ---------------------- |
| `D_PPP_SECA_D1` | Accountability framing |

| resultant scale value    | `I1`                  | `I2`                  |
| ------------------------ | --------------------- | --------------------- |
| `demonstrated`           | evidence              | evidence              |
| `demonstrated`           | evidence              | partial_evidence      |
| `partially_demonstrated` | evidence              | little_to_no_evidence |
| `partially_demonstrated` | partial_evidence      | –                     |
| `little_to_no_evidence`  | little_to_no_evidence | –                     |
###### Interpretation:
- `I1` anchors the dimension.
- Presence of `I1` typically establishes at least `partially_demonstrated`
- `I2` primarily distinguishes `demonstrated` sophistication

##### Minimum Threshold Table: `D_PPP_SECA_D2`

| sbo indentifier | sbo_short_description      |
| --------------- | -------------------------- |
| `D_PPP_SECA_D2` | Role boundary and hand-off |

| resultant scale value    | I3                    | I4                    | I5                    |
| ------------------------ | --------------------- | --------------------- | --------------------- |
| `demonstrated`           | evidence              | evidence              | evidence              |
| `demonstrated`           | evidence              | evidence              | partial_evidence      |
| `partially_demonstrated` | evidence              | partial_evidence      | –                     |
| `partially_demonstrated` | evidence              | –                     | partial_evidence      |
| `partially_demonstrated` | evidence              | little_to_no_evidence | little_to_no_evidence |
| `little_to_no_evidence`  | little_to_no_evidence | –                     | –                     |
###### Interpretation:
- `I3` anchors the dimension.
- Presence of `I3 evidence` establishes at least **Level 2**.
- `I4` and `I5` distinguish strong articulation of the boundary.

##### Minimum Threshold Table: `D_PPP_SECA_D3`

| sbo indentifier | sbo_short_description    |
| --------------- | ------------------------ |
| `D_PPP_SECA_D3` | Professional obligations |

| dimension_level          | I6                    |
| ------------------------ | --------------------- |
| `demonstrated`           | evidence              |
| `partially_demonstrated` | partial_evidence      |
| `little_to_no_evidence`  | little_to_no_evidence |
###### Interpretation:
`I6` functions as the **anchor indicator** for this dimension.

##### Minimum Threshold Table: `D_PPP_SECA_Q1`

| sbo indentifier | sbo_short_description |
| --------------- | --------------------- |
| `D_PPP_SECA_Q1` | Component Coherence   |

| dimension_level          | P1                    |
| ------------------------ | --------------------- |
| `demonstrated`           | evidence              |
| `partially_demonstrated` | partial_evidence      |
| `little_to_no_evidence`  | little_to_no_evidence |

##### Minimum Threshold Table: `D_PPP_SECA_Q2`

| sbo indentifier | sbo_short_description |
| --------------- | --------------------- |
| `D_PPP_SECA_Q1` | Component Specificity |

| dimension_level          | P2                    |
| ------------------------ | --------------------- |
| `demonstrated`           | evidence              |
| `partially_demonstrated` | partial_evidence      |
| `little_to_no_evidence`  | little_to_no_evidence |

##### Rules
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
#### 5.3. Layer 3 SBO Value Derivation, `dimension_score` → `component_score` mapping

##### Registry Summary (All Require Threshold Tables)

| sbo indentifier | sbo_short_description |
| --------------- | --------------------- |
| `C_PPP_SECA`    | SectionAResponse      |
| `C_PPP_SECB`    | SectionBResponse      |
| `C_PPP_SECC`    | SectionCResponse      |
| `C_PPP_SECD`    | SectionDResponse      |
| `C_PPP_SECE`    | SectionEResponse      |

##### Minimum Threshold Table: `C_PPP_SECA`

| sbo indentifier | sbo_short_description |
| --------------- | --------------------- |
| `C_PPP_SECA`    | SectionAResponse      |




##### OLDER
##### Minimum Threshold Table: `D_PPP_SECA_D3`

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
#### 5.4. Layer 4 SBO Value Derivation, `component_score`  →  `submission_score` mapping
Defines how **component scores determine the final submission score**.
Placeholder structure:
```text
<Component → Submission Mapping Table Placeholder>
```
Output:
```text
submission_score
```

### 6. Hard boundary rules (optional)
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
### 7. Structural invariants
The following invariants must hold:
1. Every component must define its dimensions.
2. Every `(component_id, dimension_id)` pair must be unique.
3. Every `(component_id, indicator_id)` must reference a valid dimension.
4. Mapping tables must produce exactly one score outcome.
5. Evidence evaluation must operate only within the defined AA.
### 14. Normative status
This document constitutes the **authoritative rubric payload** for the assignment.
All calibration artefacts, scoring prompts, and automated evaluation systems must reference these definitions exactly.
