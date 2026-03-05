## Pipeline1B — Rubric Construction Pipeline (Component-Level Specification)
This document defines the upstream process for constructing and stabilising a **rubric for a single component**.
A rubric defines how one **component** of a submission is evaluated.
A rubric consists of:
- one **component**
- multiple **dimensions**
- a shared set of **indicators**
- **boundary rules** that translate indicator evidence into dimension scores.
This pipeline is epistemic and iterative.
Its outputs must be **frozen before execution stages (Stage 0A / Stage 0B)**.
Calibration pipelines operate only **after the rubric is frozen**.
### 1. Rubric Scope
Each rubric applies to exactly one component.
```
component_id
```
Example:
```
SectionAResponse
```
The rubric defines how that component is evaluated.
The rubric structure is:
```
component
    dimensions
    indicators
    boundary rules
```
### 2. Dimension Definition
#### 2.1 Generate Dimension Set
Purpose:
Define the **dimensions used to evaluate the component**.
A dimension is the smallest independently scorable rubric criterion.
Requirements:
- assign a unique `dimension_id`
- define the dimension label
- define in one sentence what the dimension evaluates
- ensure dimensions are conceptually distinct
- ensure dimensions correspond to the rubric's analytic goals
Example:

| component_id | dimension_id | dimension_label |
|--------------|--------------|----------------|
| SectionAResponse | A1 | Accountability framing |
| SectionAResponse | A2 | Role boundary and hand-off |
| SectionAResponse | A3 | Professional obligations |
Deliverable:
```
<ASSESSMENT>_<COMPONENT_ID>_Step01_dimension_set_v01
```
### 3. Indicator Construction
#### 3.1 Translate Rubric Expectations into Observable Indicators
Purpose:
Define observable textual signals used to detect relevant evidence in responses.
Indicators are **presence checks**.
Indicators may contribute to one or more dimensions.
Requirements:
- phrase indicators as “does the response do X”
- ensure indicators reference observable textual evidence
- ensure indicators do not encode scoring thresholds
- target approximately **4–8 indicators**
Indicators must not:
- encode performance levels
- encode score thresholds
- reference specific score levels
Deliverable:
```
<ASSESSMENT>_<COMPONENT_ID>_Step02_indicators_checklist_v01
```
### 4. Boundary Rule Engineering
#### 4.1 Define Score Logic for Each Dimension
Purpose:
Translate observed indicator evidence into **dimension-level scores**.
Boundary rules define:
- minimum conditions for each score level
- disqualifying conditions
- hardest boundaries between levels.
Boundary rules operate at the **dimension level**.
They reference:
- indicator presence
- indicator combinations
- qualitative sufficiency tests.
Example logic:
```
IF indicator_1 AND indicator_2 present
AND no disqualifying failure
THEN Meets
```
Boundary rules must:
- prevent indicator-completeness inflation
- distinguish sufficiency from surface coverage
- specify hardest boundaries.
Deliverable:
```
<ASSESSMENT>_<COMPONENT_ID>_Step03_boundary_rules_v01
```
### 5. Rubric Freeze Condition
A rubric is considered **construction-complete** when:
- the dimension set is frozen
- the indicator checklist is stabilised
- the boundary rules are stabilised.
Once frozen:
- dimension identifiers must not change
- boundary rules must not change
- indicators must not change.
Calibration pipelines may then begin.
### 6. Relationship to Execution Pipelines
Execution pipelines operate as follows.
Stage 0A:
```
submission_id × component_id
```
Stage 0B:
```
submission_id × component_id × dimension_id
```
The rubric constructed here supplies the **dimension definitions used in Stage 0B**.
Calibration then evaluates and stabilises the scoring logic applied to those dimensions.
### 7. Architectural Principle
Rubric construction defines **what will be evaluated**.
Calibration defines **how it will be interpreted**.
Scoring applies the calibrated rubric to the canonical grading population.
