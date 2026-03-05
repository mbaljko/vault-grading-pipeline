## Pipeline1B — Rubric Construction Pipeline (Component-Level Specification)
This document defines the process for constructing and stabilising a **rubric for a single component**.
A rubric defines how one **component** of a submission is evaluated.
A rubric consists of:
- one **component**
- multiple **dimensions**
- a shared set of **indicators**
- **boundary rules** that translate indicator evidence into dimension satisfaction and performance levels.
This pipeline is epistemic and iterative.
Its outputs must be **frozen before execution stages (Stage 0A / Stage 0B)**.
Calibration pipelines operate only **after the rubric is frozen**.
This pipeline assumes that assignment structure and response payload contracts have already been defined upstream.
### 1. Upstream Inputs
Rubric construction operates on top of the **assignment payload specification architecture**.
The following inputs are required.
```
PPP_AssignmentPayloadSpec_v01
PPP_<COMPONENT_ID>_CalibrationPayloadFormat_v01
```
`PPP_AssignmentPayloadSpec_v01` defines the canonical structure of the assignment payload and the set of valid component identifiers.
`PPP_<COMPONENT_ID>_CalibrationPayloadFormat_v01` defines the payload contract used when evaluating responses for a specific component.
This contract specifies:
- canonical identifiers (`participant_id`, `component_id`)
- the response evidence field (e.g., `response_text`)
- the canonical scoring unit
Example component payload contract:
```
PPP_SectionAResponse_CalibrationPayloadFormat_v01
```
Rubric construction must remain **compatible with the payload contract defined for the component**.
### 2. Rubric Scope
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
The rubric specification is generated through a structured rubric input document (CRIS).
### 3. Rubric Semantic Definition (CRIS)
#### 3.1 Purpose
Rubric semantics are defined using a **Component Rubric Input Schema (CRIS)** instance.
The CRIS document defines:
- rubric dimensions
- observable indicators
- mappings between indicators and dimensions
- cross-dimension indicators
- parameters used to generate boundary rules.
The CRIS document contains the **semantic definition of the rubric**.
Deliverable:
```
CAL_<ASSESSMENT>_<COMPONENT_ID>_Step01_CRIS_v01
```
Example:
```
CAL_PPP_SectionAResponse_Step01_CRIS_v01
```
#### 3.2 Dimension Definition
Dimensions represent the **conceptual criteria used to evaluate the component response**.
Requirements:
- assign a unique `dimension_id`
- define a dimension label
- define a scoring claim describing what the dimension evaluates
- ensure dimensions are conceptually distinct
- ensure dimensions correspond to the analytic goals of the component.
Example:

| component_id | dimension_id | dimension_label |
|--------------|--------------|----------------|
| SectionAResponse | D1 | Accountability framing |
| SectionAResponse | D2 | Role boundary and hand-off |
| SectionAResponse | D3 | Professional obligations |
Dimensions define **what conceptual properties of the response must be evaluated**.
#### 3.3 Indicator Definition
Indicators define **observable textual signals used to detect evidence in responses**.
Indicators function as **presence checks**.
Indicators may apply to:
- a specific dimension
- the response as a whole (cross-dimension indicators).
Requirements:
- phrase indicators as “does the response do X”
- ensure indicators reference observable textual evidence
- ensure indicators do not encode score thresholds
- ensure indicators do not encode performance levels.
Indicators must not:
- encode scoring thresholds
- encode dimension satisfaction directly
- reference performance level labels.
Indicators typically number **4–8 per component**.
Example indicator form:
```
Does the response explicitly position accountability as individual,
distributed, or mixed and identify at least one locus of accountability?
```
#### 3.4 Indicator–Dimension Mapping
Dimension satisfaction is determined through an explicit mapping between indicators and dimensions.
Example:
```
D1 requires indicators I1 and I2
D2 requires indicators I3, I4, and I5
D3 requires indicator I6
```
This mapping determines when a dimension is considered **satisfied** during evaluation.
#### 3.5 Cross-Dimension Indicators
Some indicators evaluate properties of the response as a whole.
Typical examples:
- coherence
- specificity
- evidentiary grounding.
These indicators function as **response-quality checks** used during boundary rule evaluation.
### 4. Rubric Specification Generation
The rubric specification document is generated from the CRIS definition.
The rubric specification contains:
- the **dimension registry**
- **indicator definitions**
- **dimension satisfaction rules**
- **boundary rules** translating dimension satisfaction into performance levels.
Deliverable:
```
CAL_<ASSESSMENT>_<COMPONENT_ID>_Step02_RubricSpec_v01
```
Example:
```
CAL_PPP_SectionAResponse_Step02_RubricSpec_v01
```
The RubricSpec document is a **rendered human-readable specification** used by calibration and scoring pipelines.
### 5. Rubric Freeze Condition
A rubric is considered **construction-complete** when:
- the CRIS document is frozen
- the generated RubricSpec document is frozen.
Once frozen:
- dimension identifiers must not change
- indicator identifiers must not change
- dimension–indicator mappings must not change
- boundary rule parameters must not change.
Calibration pipelines may then begin.
### 6. Relationship to Execution Pipelines
Execution pipelines operate as follows.
Stage 0A:
```
participant_id × component_id
```
Stage 0B:
```
participant_id × component_id × dimension_id
```
The rubric constructed here supplies:
- the **dimension registry**
- the **dimension satisfaction logic**
- the **boundary rules** used to evaluate responses.
Calibration pipelines then stabilise the interpretation of these rules across graders.
### 7. Architectural Principle
Rubric construction defines **what will be evaluated**.
Calibration defines **how evidence will be interpreted**.
Scoring applies the calibrated rubric to the canonical grading population.
Assignment pipelines define **what evidence exists**.
