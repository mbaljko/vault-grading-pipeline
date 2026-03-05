## Pipeline PL3 — Production Scoring Pipeline (Two-Stage Model)
### Generalised Specification
This document defines the **production scoring pipeline** used to evaluate canonical grading targets using a frozen rubric specification.
Pipeline PL3 operates **after** the following upstream processes have completed:
- Pipeline 1A — Canonical population preparation  
- Pipeline 1B — Rubric construction and freeze  
- Calibration pipelines (if used)
Pipeline PL3 applies the rubric to the canonical grading population in a **two-stage evaluation model**.
The pipeline produces final component scores while preserving a complete audit trail of:
- dimension evidence
- indicator detection
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
This dataset contains one row per grading target:
```
submission_id × component_id
```
Each row includes the canonical response evidence field:
```
cleaned_response_text
```
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
## 2. Overview of the Two-Stage Scoring Model
Pipeline PL3 performs scoring in two stages.
### Stage 1 — Dimension Evidence Evaluation
Stage 1 evaluates **dimension-level evidence** by detecting indicators and determining whether each rubric dimension is satisfied.
Evaluation unit:
```
submission_id × component_id × dimension_id
```
Stage 1 does **not assign performance levels**.
Instead, it determines:
- which indicators are present
- whether dimension requirements are satisfied
- what textual evidence supports those findings
### Stage 2 — Boundary Rule Evaluation
Stage 2 evaluates the **component response as a whole**.
Evaluation unit:
```
submission_id × component_id
```
Stage 2 consumes:
- dimension satisfaction results from Stage 1
- cross-dimension indicator results
- boundary rule logic from the rubric specification
Stage 2 assigns the final **performance level label**.
Example labels:
- Exceeds expectations
- Meets expectations
- Approaching expectations
- Below expectations
- Not demonstrated
## 3. Stage 1 — Dimension Evidence Evaluation
### 3.1 Purpose
Stage 1 detects indicator evidence and determines whether each dimension’s required indicators are satisfied.
Stage 1 produces **dimension-level diagnostic results**.
### 3.2 Evaluation Unit
```
submission_id × component_id × dimension_id
```
Each dimension evaluation must reference:
- the response text
- indicator definitions
- indicator–dimension mappings
### 3.3 Stage 1 Operations
For each grading target:
1. Retrieve the canonical response evidence.
2. Evaluate all dimension indicators.
3. Record indicator presence or absence.
4. Determine dimension satisfaction using the indicator–dimension mapping defined in the rubric.
5. Capture supporting evidence excerpts where possible.
### 3.4 Stage 1 Output Artefact
Pipeline PL3 must produce a dimension evidence dataset:
```
RUN_<ASSESSMENT>_<COMPONENT_ID>_DimensionEvidence_v01
```
Each row represents:
```
submission_id × component_id × dimension_id
```
Required fields include:
- `submission_id`
- `component_id`
- `dimension_id`
- `dimension_satisfied`
- `indicator_hits`
- `evidence_excerpt`
- `evaluation_notes`
- `confidence` (optional)
This dataset serves as the **coordination mechanism between Stage 1 and Stage 2**.
Stage 2 must treat these results as authoritative.
## 4. Cross-Dimension Indicator Evaluation
Certain indicators evaluate the response **as a whole**, not a specific dimension.
Examples include:
- coherence
- internal consistency
- specificity of claims
- evidentiary grounding
Evaluation unit:
```
submission_id × component_id × indicator_id
```
Cross-dimension indicators may be evaluated either:
- during Stage 1, or
- as a short intermediate step before Stage 2.
Results must be recorded explicitly.
### 4.1 Cross-Dimension Output Artefact
```
RUN_<ASSESSMENT>_<COMPONENT_ID>_CrossDimensionIndicators_v01
```
Required fields include:
- `submission_id`
- `component_id`
- `indicator_id`
- `indicator_present`
- `supporting_evidence`
- `confidence`
## 5. Stage 2 — Boundary Rule Evaluation
### 5.1 Purpose
Stage 2 translates evidence into a **final performance level**.
Stage 2 applies the rubric’s **boundary rules**.
These rules evaluate:
- dimension satisfaction results
- cross-dimension indicator results
- rule-specific constraints defined in the rubric.
### 5.2 Evaluation Unit
```
submission_id × component_id
```
### 5.3 Boundary Rule Execution
Stage 2 must:
1. Retrieve dimension satisfaction results.
2. Retrieve cross-dimension indicator results.
3. Apply boundary rules defined in the rubric specification.
4. Determine which rule condition is satisfied.
5. Assign the corresponding performance level.
Boundary rule evaluation must be **deterministic**.
### 5.4 Stage 2 Output Artefact
Pipeline PL3 must produce the final scoring dataset:
```
RUN_<ASSESSMENT>_<COMPONENT_ID>_ComponentScores_v01
```
Each row represents:
```
submission_id × component_id
```
Required fields include:
- `submission_id`
- `component_id`
- `performance_level_label`
- `triggered_boundary_rule`
- `dimension_summary`
- `cross_dimension_summary`
- `evaluation_notes`
## 6. Auditability Requirements
Pipeline PL3 must preserve a full audit trail of scoring decisions.
The following artefacts must be retained:
- dimension evidence dataset
- cross-dimension indicator dataset
- final component score dataset
Together these datasets must allow reconstruction of:
- which indicators were detected
- which dimensions were satisfied
- which boundary rule produced the final score
## 7. Deterministic Reproducibility
Pipeline PL3 must produce reproducible outputs.
Re-running the pipeline with identical inputs must produce identical scoring results.
Reproducibility requires:
- fixed rubric definitions
- deterministic rule ordering
- stable evaluation logic
- stable canonical input data
## 8. Architectural Principle
The production scoring pipeline follows a strict separation of concerns.
Pipeline 1A defines **what evidence exists**.
Pipeline 1B defines **what properties of the response must be evaluated**.
Pipeline PL3 determines **whether those properties are present and what performance level they imply**.
This architecture ensures that:
- rubric semantics remain stable
- evaluation evidence is auditable
- scoring decisions are reproducible.
