## Pipeline PL3 — Production Scoring Pipeline (Two-Stage Model) 
version: v2
### Generalised Specification
This document defines the **production scoring pipeline** used to evaluate canonical grading targets using a frozen rubric specification.
Pipeline PL3 operates **after** the following upstream processes have completed:
- Pipeline 1A — Canonical population preparation  
- Pipeline 1B — Rubric construction and freeze  
- Calibration pipelines (if used)
Pipeline PL3 applies the rubric to the canonical grading population in a **two-stage evaluation model**.
The pipeline produces final component scores while preserving a complete audit trail of:
- indicator detection  
- dimension evaluation  
- boundary-rule evaluation  
- final performance-level assignment
Pipeline PL3 must operate **deterministically and reproducibly**.
## 1. Inputs to Pipeline PL3
Pipeline PL3 requires the following inputs.
### 1.1 Canonical Grading Target Dataset
Produced by Pipeline 1A:
```
PPP_CanonicalGradingTargets_v01
```
This artefact contains the **canonical grading targets** used by all downstream scoring pipelines.
The canonical grading unit is defined as:
```
submission_id × component_id
```
Each row represents **one submission evaluated for one assessment component**.
Required fields include:
- `submission_id`
- `component_id`
- `cleaned_response_text`
Additional metadata fields may be present but must not affect canonical identity.
#### Workbook Structure
`PPP_CanonicalGradingTargets_v01` may be stored as an **Excel workbook** containing multiple sheets.
Example structure:
```
Sheet: canonical_targets
    submission_id
    component_id
    cleaned_response_text
    optional_metadata_fields
Sheet: manifest
    processing_timestamp
    input_sources
    row_counts
    pipeline_version
```
The **canonical_targets sheet** must contain the grading target dataset keyed by:
```
submission_id × component_id
```
Other sheets may store supporting metadata or audit information.
#### Explicit Constraint
The canonical dataset must remain **rubric-agnostic**.
Therefore it must **not contain**:
- `dimension_id`
- indicator fields
- rubric identifiers
- scoring outputs
Rubric logic is introduced only when Pipeline PL3 executes.
### 1.2 Rubric Specification
Produced by Pipeline 1B:
```
CAL_<ASSESSMENT>_<COMPONENT_ID>_Step02_RubricSpec_v01
```
The rubric specification defines:
- dimension registry
- indicator definitions
- indicator–dimension mappings
- cross-dimension indicators
- boundary rules translating evidence into performance levels
The rubric must be **frozen before Pipeline PL3 begins**.
### 1.3 Optional Calibration Artefacts
If calibration has been performed, the pipeline may also consume:
```
CAL_<ASSESSMENT>_<COMPONENT_ID>_CalibrationNotes_v01
CAL_<ASSESSMENT>_<COMPONENT_ID>_CalibrationParameters_v01
```
These artefacts guide interpretation of ambiguous cases but must not alter the rubric structure.
# 2. Overview of the Two-Stage Scoring Model
Pipeline PL3 performs scoring in two stages.
### Stage 1 — Indicator Evidence Detection
Stage 1 evaluates the **response text directly** and records which rubric indicators are present.
Stage 1 **does not determine dimension satisfaction and does not assign performance levels**.
Stage 1 produces **raw evidence about indicator presence**.
Evaluation unit:
```
submission_id × component_id × indicator_id
```
Stage 1 determines:
- whether each indicator is present
- what textual evidence supports the indicator
- confidence in the detection
Stage 1 therefore functions as an **evidence extraction stage**.
### Stage 2 — Dimension Evaluation and Boundary Rule Execution
Stage 2 interprets the evidence produced by Stage 1.
Stage 2 determines:
1. whether rubric dimensions are satisfied
2. whether cross-dimension indicators are satisfied
3. which boundary rule condition applies
4. the final performance-level label
Evaluation unit:
```
submission_id × component_id
```
Stage 2 consumes:
- Stage 1 indicator evidence
- rubric indicator–dimension mappings
- cross-dimension indicators
- rubric boundary rules
Stage 2 performs **all interpretive scoring logic**.
# 3. Stage 1 — Indicator Evidence Detection
## 3.1 Purpose
Stage 1 extracts **observable rubric evidence** from the response text.
It records whether each indicator defined in the rubric is present.
Stage 1 **does not evaluate rubric dimensions and does not apply boundary rules**.
## 3.2 Evaluation Unit
```
submission_id × component_id × indicator_id
```
Each indicator must be evaluated independently.
Indicator detection must rely only on:
- response text
- indicator definitions
## 3.3 Stage 1 Operations
For each grading target:
1. Retrieve the canonical response text.
2. Evaluate each rubric indicator independently.
3. Record whether the indicator is present.
4. Capture supporting evidence excerpts where possible.
5. Record confidence in the detection.
Stage 1 **must not evaluate dimension satisfaction**.
## 3.4 Stage 1 Output Artefact
Pipeline PL3 must produce an **indicator evidence dataset**:
```
RUN_<ASSESSMENT>_<COMPONENT_ID>_IndicatorEvidence_v01
```
Each row represents:
```
submission_id × component_id × indicator_id
```
Required fields include:
```
submission_id
component_id
indicator_id
indicator_present
evidence_excerpt
evaluation_notes
confidence
```
This dataset serves as the **coordination mechanism between Stage 1 and Stage 2**.
Stage 2 must treat these results as authoritative evidence.
# 4. Cross-Dimension Indicator Detection
Certain indicators evaluate the response **as a whole**, not a specific dimension.
Examples include:
- coherence
- internal consistency
- specificity of claims
- evidentiary grounding
These indicators may be evaluated:
- during Stage 1, or
- as a short intermediate step before Stage 2.
Evaluation unit:
```
submission_id × component_id × indicator_id
```
## 4.1 Cross-Dimension Output Artefact
```
RUN_<ASSESSMENT>_<COMPONENT_ID>_CrossDimensionIndicators_v01
```
Required fields include:
```
submission_id
component_id
indicator_id
indicator_present
supporting_evidence
confidence
```
# 5. Stage 2 — Dimension Evaluation and Boundary Rule Execution
## 5.1 Purpose
Stage 2 converts **indicator evidence into rubric judgments**.
Stage 2 performs two steps:
1. determine **dimension satisfaction**
2. apply **boundary rules** to determine the final performance level
## 5.2 Dimension Satisfaction Evaluation
Stage 2 determines whether each rubric dimension is satisfied.
Dimension satisfaction is determined using the rubric’s **indicator–dimension mappings**.
Example logic:
```
Dimension D1 satisfied if indicators I1 AND I2 are present
Dimension D2 satisfied if indicators I3 AND I4 AND I5 are present
Dimension D3 satisfied if indicator I6 is present
```
These rules are defined in the rubric specification.
## 5.3 Boundary Rule Execution
Once dimension satisfaction has been determined, Stage 2 evaluates the rubric’s **boundary rules**.
Stage 2 must:
1. retrieve Stage 1 indicator evidence
2. determine dimension satisfaction
3. retrieve cross-dimension indicator results
4. apply boundary rules
5. determine which rule condition is satisfied
6. assign the corresponding performance-level label
Boundary rule evaluation must be **deterministic**.
## 5.4 Stage 2 Output Artefact
Pipeline PL3 must produce the final scoring dataset:
```
RUN_<ASSESSMENT>_<COMPONENT_ID>_ComponentScores_v01
```
Each row represents:
```
submission_id × component_id
```
Required fields include:
```
submission_id
component_id
performance_level_label
triggered_boundary_rule
dimension_summary
cross_dimension_summary
evaluation_notes
```
# 6. Auditability Requirements
Pipeline PL3 must preserve a full audit trail of scoring decisions.
The following artefacts must be retained:
- indicator evidence dataset
- cross-dimension indicator dataset
- final component score dataset
Together these datasets must allow reconstruction of:
- which indicators were detected
- which dimensions were satisfied
- which boundary rule produced the final score
# 7. Deterministic Reproducibility
Pipeline PL3 must produce reproducible outputs.
Re-running the pipeline with identical inputs must produce identical scoring results.
Reproducibility requires:
- fixed rubric definitions
- deterministic rule ordering
- stable evaluation logic
- stable canonical input data
# 8. Architectural Principle
The production scoring pipeline follows a strict separation of concerns.
Pipeline 1A defines:
```
what evidence exists
```
Pipeline 1B defines:
```
what properties of the response must be evaluated
```
Pipeline PL3 determines:
```
which indicators are present
how indicators combine into rubric dimensions
which boundary rule determines the final performance level
```
This architecture ensures that:
- rubric semantics remain stable
- evaluation evidence is auditable
- scoring decisions are reproducible.
