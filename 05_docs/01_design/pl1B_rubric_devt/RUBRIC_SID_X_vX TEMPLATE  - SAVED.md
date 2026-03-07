## RUBRIC_SID_X_vX TEMPLATE.md
### Rubric Payload Specification
### 0. Rubric Identifier
`RUBRIC_<submission_id>_<status>_payload_v<version>.md`
`<status>` is one of `CAL` for calibration or `PROD` for production
### 1. Purpose
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
### 2. Ontological context
This rubric payload operates within a layered grading ontology.
**Assessment Artefact (AA)**: the portion of a student submission from which evidence is examined during a scoring pass.
**Score-Bearing Object (SBO)**: an analytic entity that receives a score derived from evidence found in an AA.
#### 2.1 Scoring layer definition
A **scoring layer** is a stage of evaluation that assigns scores to a particular type of **Score-Bearing Object (SBO)**.
Each scoring layer evaluates evidence drawn from a defined **Assessment Artefact (AA)** and assigns scores to the SBOs associated with that layer.
#### 2.2 Evidence boundary rule
Evidence used during scoring must be drawn **only from the defined Assessment Artefact (AA)** for that scoring layer.
No evidence outside the AA may be used when assigning scores.
#### 2.3 Assessment Artefact (AA) specification by layer
The Assessment Artefact defines the portion of the submission from which evidence may be drawn.
```text
Layer 1 AA = submission_id × component_id
Layer 2 AA = submission_id × component_id
Layer 3 AA = submission_id × component_id
Layer 4 AA = submission_id
```
#### 2.4 Score-Bearing Objects by scoring layer
Each scoring layer assigns scores to a specific class of **Score-Bearing Object (SBO)**.
```text
Layer 1 → indicator SBOs
Layer 2 → dimension SBOs
Layer 3 → component SBOs
Layer 4 → submission SBO
```
#### 2.5 Score derivation invariant
Scores across layers follow a hierarchical derivation structure.
```text
AA → indicator SBO scores → dimension SBO scores → component SBO scores → submission SBO score
```
Higher-layer SBO scores may be derived from lower-layer SBO scores through mapping rules defined in this payload.
#### 2.6 Layer execution note
Not all scoring processes operate across all layers.
A scoring process may evaluate and assign scores at **one or more layers**, depending on the evaluation task and the structures consumed by that scoring stage.
### 3. Score-Bearing Object (SBO) type registry
This table defines the Score-Bearing Object (SBO) types used in the rubric payload.
Each row specifies an SBO type, its identifier structure, and the scale used to evaluate that SBO.

| layer | sbo_type   | score_name       | sbo_identifier_pattern | scale_type  | scale_name                     |

| ----- | ---------- | ---------------- | ---------------------- | ----------- | ------------------------------ |

| 1     | indicator  | indicator_score  | `[I\|P]_sid_cid_iid`   | evidence    | `indicator_evidence_scale`     |

| 2     | dimension  | dimension_score  | `[D\|Q]_sid_cid_did`   | evidence    | `dimension_evidence_scale`     |

| 3     | component  | component_score  | `C_sid_cid`            | performance | `component_performance_scale`  |

| 4     | submission | submission_score | `S_sid`                | performance | `submission_performance_scale` |
### 4. Scale registry

| scale_name                     | ordered | description                                   |

| ------------------------------ | ------- | --------------------------------------------- |

| `indicator_evidence_scale`     | true    | Evidence strength for indicator evaluation    |

| `dimension_evidence_scale`     | true    | Evidence strength for dimension evaluation    |

| `component_performance_scale`  | true    | Performance evaluation scale for a component  |

| `submission_performance_scale` | true    | Performance evaluation scale for a submission |
#### indicator_evidence_scale

| scale_value           |

| --------------------- |

| evidence              |

| partial_evidence      |

| little_to_no_evidence |
Hierarchy:
```
evidence > partial_evidence > little_to_no_evidence
```
#### dimension_evidence_scale

| scale_value                |

| -------------------------- |

| demonstrated               |

| partially_demonstrated     |

| little_to_no_demonstration |
Hierarchy:
```
demonstrated > partially_demonstrated > little_to_no_demonstration
```
#### component_performance_scale

| scale_value              |

| ------------------------ |

| exceeds_expectations     |

| meets_expectations       |

| approaching_expectations |

| below_expectations       |

| not_demonstrated         |
Hierarchy:
```
exceeds_expectations > meets_expectations > approaching_expectations > below_expectations > not_demonstrated
```
#### submission_performance_scale

| scale_value              |

| ------------------------ |

| exceeds_expectations     |

| meets_expectations       |

| approaching_expectations |

| below_expectations       |

| not_demonstrated         |
Hierarchy:
```
exceeds_expectations > meets_expectations > approaching_expectations > below_expectations > not_demonstrated
```
### 5. Registry of specific Score-Bearing Object (SBO) instances 
`sbo_identifier_shortid`: a short token used within mapping tables as a compact reference to the corresponding SBO.
#### 5.1 Layer 4 SBO Instances
Defines the **Layer 4 Score-Bearing Object (SBO)** representing the full student submission.

| `sbo_identifier` | `sbo_identifier_shortid` | `submission_id` | `sbo_short_description` |

| ---------------- | ------------------------ | --------------- | ----------------------- |

|                  |                          |                 |                         |
#### 5.2 Layer 3 SBO Instances
Defines the **Layer 3 SBOs** representing components of the submission.

| `sbo_identifier` | `sbo_identifier_shortid` | `submission_id` | `component_id` | `sbo_short_description` |

| ---------------- | ------------------------ | --------------- | -------------- | ----------------------- |

|                  |                          |                 |                |                         |

|                  |                          |                 |                |                         |

|                  |                          |                 |                |                         |

|                  |                          |                 |                |                         |

|                  |                          |                 |                |                         |
##### Constraints:
- component identifiers must match the canonical population structure used in the grading dataset
- each `(submission_id, component_id)` pair defines a Layer 3 Assessment Artefact
#### 5.3 Layer 2 SBO Instances
Defines the **Layer 2 SBOs** representing rubric dimensions applied to components.

| `sbo_identifier` | `sbo_identifier_shortid` | `submission_id` | `component_id` | `dimension_id` | `sbo_short_description` |

| ---------------- | ------------------------ | --------------- | -------------- | -------------- | ----------------------- |

|                  |                          |                 |                |                |                         |

|                  |                          |                 |                |                |                         |

|                  |                          |                 |                |                |                         |

|                  |                          |                 |                |                |                         |

|                  |                          |                 |                |                |                         |
##### Constraints:
- `(component_id, dimension_id)` pairs must be unique
- dimension identifiers must remain stable across rubric versions
#### 5.4 Layer 1 SBO Instances
Defines the **Layer 1 SBOs** used to detect observable evidence within the Assessment Artefact.

| `sbo_identifier` | `sbo_identifier_shortid` | `submission_id` | `component_id` | `indicator_id` | `sbo_short_description` |

| ---------------- | ------------------------ | --------------- | -------------- | -------------- | ----------------------- |

|                  |                          |                 |                |                |                         |

|                  |                          |                 |                |                |                         |

|                  |                          |                 |                |                |                         |

|                  |                          |                 |                |                |                         |
##### Constraints:
- indicator SBO instances are defined independently of dimensions.
- an indicator may contribute evidence to one or more dimensions through the Layer 2 mapping rules.
- indicator identifiers must remain stable within a rubric version
### 6. SBO Instructions
#### 6.1 Layer 1 SBO Value Derivation, AA → `indicator_score` 
##### Layer 1 Target SBO class
##### Layer 1 Input SBO class
##### Layer 1 Registry summary
##### Layer 1 Mapping tables
##### Layer 1 Fallback rule
##### Layer 1 Optional interpretation notes
#### 6.2 Layer 2 SBO Value Derivation, `indicator_score` → `dimension_score` mapping
##### Layer 2 Target SBO class
##### Layer 2 Input SBO class
##### Layer 2 Registry summary
##### Layer 2 Mapping tables
##### Layer 2 Fallback rule
##### Layer 2 Optional interpretation notes
#### 6.3 Layer 3 SBO Value Derivation, `dimension_score` → `component_score` mapping
##### Layer 3 Target SBO class
##### Layer 3 Input SBO class
##### Layer 3 Registry summary
##### Layer 3 Mapping tables
##### Layer 3 Fallback rule
##### Layer 3 Optional interpretation notes
#### 6.4 Layer 4 SBO Value Derivation, `component_score`  →  `submission_score` mapping
##### Layer 4 Target SBO class
##### Layer 4 Input SBO class
##### Layer 4 Registry summary
##### Layer 4 Mapping tables
##### Layer 4 Fallback rule
##### Layer 4 Optional interpretation notes
### 7. Hard boundary rules (optional)
Hard boundary rules may constrain score eligibility.
Boundary rules must operate only on **dimension or component scores**.
Example structure:
```text
<Hard Boundary Rule Placeholder>
```
Example logic:
```text
Eligibility for `meets_expectations` requires
two dimensions at `partially_demonstrated` or higher
```
### 8. Structural invariants
The following invariants must hold:
1. All mapping tables must use input values drawn from the scale associated with the input SBOs and output values drawn from the scale associated with the target SBO.
2. Every component must define its dimensions.
3. Every `(component_id, dimension_id)` pair must be unique.
4. Every `(submission_id, component_id, indicator_id)` combination must correspond to a valid Layer 1 SBO instance (more simply, Every indicator SBO instance must reference a valid `component_id`).
5. Mapping tables must produce exactly one score outcome.
6. Evidence evaluation must operate only within the defined AA.
7. indicator SBO instances may contribute evidence to multiple dimension SBOs.
   dimension membership is defined exclusively by the Layer 2 mapping tables.
### 9. Normative status
This document constitutes the **authoritative rubric payload** for the assignment.
All calibration artefacts, scoring prompts, and automated evaluation systems must reference these definitions exactly.
### 10. Mapping table specification
Mapping tables define how scores for one class of **Score-Bearing Object (SBO)** are derived from the scores of other SBOs.
A mapping table must be **deterministic**: for any combination of input values there must be exactly one resulting output value.
Mapping tables are interpreted using the rules defined in this section.
#### 10.1 General structure of mapping tables
Each mapping table has the following structure:

| resultant scale value | <input_sbo_shortid_1> | <input_sbo_shortid_2> | ... |

|----------------------|----------------------|----------------------|-----|
Columns represent **input SBOs** whose scores determine the output score.
Rows represent **threshold conditions** under which the output score is assigned.
The column `resultant scale value` specifies the score assigned to the **target SBO**.
All other columns specify **minimum threshold values** for the corresponding input SBOs.
#### 10.2 Column requirements
Each mapping table must contain:
1. **`resultant scale value`**
   - The score assigned to the **target SBO**.
   - Must be a value from the scale associated with the target SBO.
2. **One column for each input SBO**
   - Column names must match `sbo_identifier_shortid` values defined in the SBO registry.
Example:

| resultant scale value | I1 | I2 |

|----------------------|----|----|

| demonstrated | evidence | evidence |

| partially_demonstrated | evidence | little_to_no_evidence |

| little_to_no_demonstration | little_to_no_evidence | little_to_no_evidence |
#### 10.3 Cell value semantics
Cells in the input columns represent **minimum threshold values**.
A row condition is satisfied when the actual input value is **greater than or equal to** the threshold value specified in the table.
Example:
If the scale ordering is:
```
evidence > partial_evidence > little_to_no_evidence
```
and the table cell contains:
```
partial_evidence
```
then the row condition is satisfied when the input value is:
```
partial_evidence
or
evidence
```
#### 10.4 Wildcard value
The symbol `*` may be used as a **wildcard**.
A wildcard indicates that the value of that input does not affect the rule.
Example:

| resultant scale value  | I1       | I2  
| ---------------------- | -------- | --- |
| partially_demonstrated | evidence | `*` |


Interpretation:
```
IF I1 ≥ evidence
THEN dimension_score = partially_demonstrated
```
#### 10.5 Row precedence
Rows are evaluated **from top to bottom**.
Rows must be ordered from **strongest threshold condition** at the top to **weakest threshold condition** at the bottom.
For each row:
A row is satisfied when **all input SBO values meet or exceed the threshold values specified in that row**.
The **first row whose threshold condition is satisfied determines the result**.
Once a row is satisfied, later rows are ignored.
#### 10.6 Coverage requirement
Mapping tables must guarantee that every possible combination of input values yields a result.
Coverage may be achieved by:
1. explicitly enumerating all combinations, or  
2. ensuring that the **bottom row defines the weakest possible threshold condition**.
In practice, the bottom row typically uses the **lowest values of the input scales**, ensuring that all input combinations satisfy at least that row.
#### 10.7 Validity constraints
A valid mapping table must satisfy the following conditions:
1. `resultant scale value` must contain only values from the scale associated with the **target SBO**.
2. Input columns must contain only values from the scale associated with the corresponding **input SBO**, or the wildcard `–`.
3. Rows must be ordered from **strongest threshold condition to weakest threshold condition**.
4. The table must guarantee that evaluation produces **exactly one output value** for every possible combination of input values.
#### 10.8 Evaluation procedure
Evaluation of a mapping table follows this procedure:
```
for each row in the table (top to bottom):
    if all input values meet or exceed the row thresholds:
        return resultant_scale_value
```
Because rows are ordered from strongest to weakest, the returned value corresponds to the **strongest satisfied threshold condition**.
