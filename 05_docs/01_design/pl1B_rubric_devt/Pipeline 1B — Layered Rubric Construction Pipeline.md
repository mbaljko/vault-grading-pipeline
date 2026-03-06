### Pipeline 1B — Layered Rubric Construction Pipeline
This document defines the process for constructing and stabilising a **rubric for an assessment submission** under the **four-layer scoring ontology**.  
A rubric is a **layered scoring specification** whose elements are stabilised iteratively using empirical evidence from real student responses.  
The rubric ultimately defines how evidence observed in responses is transformed into scores across four scoring layers.  
The scoring layers are:
```
Layer 1 → indicator SBOs
Layer 2 → dimension SBOs
Layer 3 → component SBOs
Layer 4 → submission SBO
```
Rubric construction therefore proceeds **layer by layer**, beginning with observable indicators and progressing upward through dimension construction and performance mapping.
Calibration pipelines operate **after the rubric structure is stabilised**.
### 1. Upstream Inputs
Rubric construction operates on top of the **assignment payload specification architecture** produced by Pipeline 1A.
The following artefacts are required.
```
<ASSESSMENT_ID>_AssignmentPayloadSpec_v01
<ASSESSMENT_ID>_<COMPONENT_ID>_CalibrationPayloadFormat_v01
```
`AssignmentPayloadSpec` defines the canonical structure of the assignment payload and the set of valid component identifiers.
`CalibrationPayloadFormat` defines the payload contract used when evaluating responses for a specific component.
This contract specifies:
- canonical identifiers (`submission_id`, `component_id`)
- the response evidence field (for example `cleaned_response_text`)
- the canonical scoring unit
Example:
```
PPP_SectionAResponse_CalibrationPayloadFormat_v01
```
Rubric construction must remain **compatible with the payload contract defined for the component**.
### 2. Rubric Scope
The rubric applies to the **entire submission**.
The final score produced by the rubric corresponds to the **Layer 4 submission Score-Bearing Object (SBO)**:
```
submission_score
```
However, the submission is typically composed of multiple **components**, each corresponding to a student-authored portion of the assignment.
Examples of components:
```
SectionAResponse
SectionBResponse
SectionCResponse
SectionDResponse
SectionEResponse
```
Most rubric design and tuning work occurs at **Layer 3**, where **dimension evidence is translated into component performance levels**.
Layer 4 then derives the final submission score by applying a relatively straightforward mapping over the component scores.
Conceptually, the rubric structure is:
```
submission
    components
        dimensions
        indicators
        mapping tables
```
Layer responsibilities are therefore:
```
Layer 1 → detect indicator evidence within each component response
Layer 2 → derive conceptual dimension evidence from indicator evidence
Layer 3 → translate dimension evidence into component performance levels
Layer 4 → combine component scores into a submission score
```
Because the Layer 3 mappings determine the interpretation of dimension evidence within each component, **most empirical tuning during rubric construction occurs at Layer 3**.
Layer 4 mappings typically remain simple and stable once component evaluation is established.
### 3. Stage 0 — Component Analytic Specification
Before constructing indicators, the analytic goals of each component must be clarified.
Inputs:
```
AssignmentPayloadSpec
ComponentPayloadContract
```
From these inputs, produce a **component analytic brief** describing:
- the analytic goals of the component
- the conceptual claims students are expected to make
- the boundaries of the response task
Deliverable:
```
<ASSESSMENT_ID>_<COMPONENT_ID>_AnalyticBrief_v01
```
The analytic brief guides the creation of indicators and dimensions.
### 4. Stage 1 — Indicator Discovery (Layer 1 Design)
Indicators correspond to **Layer 1 Score-Bearing Objects (SBOs)**.
Indicators detect **observable textual evidence** within responses.
Indicators are evaluated within the **Layer 1 Assessment Artefact**:
```
AA = submission_id × component_id
```
#### 4.1 Indicator Drafting
Indicators are derived from the component analytic brief.
Indicators should be phrased as observable checks.
Example forms:
```
Does the response explicitly identify where accountability resides?
Does the response identify at least one responsibility outside the professional role?
Does the response describe a responsibility hand-off?
```
Indicator design rules:
Indicators must:
- detect observable textual signals
- avoid embedding scoring thresholds
- avoid referencing performance levels
- avoid directly encoding dimension satisfaction
Indicators should typically number **4–8 per component**.
Deliverable:
```
Draft Indicator Registry
```
#### 4.2 Indicator Pilot Evaluation
Indicators are tested using a **small calibration sample**.
Procedure:
```
sample 20–40 student submissions
evaluate indicator evidence
produce indicator_score outputs
```
Example dataset structure:
```
submission_id
component_id
I1
I2
I3
I4
I5
```
Evaluation questions:
- Do indicators detect the intended signals?
- Are there false positives or false negatives?
- Are indicators ambiguous or overlapping?
Indicators are revised until they reliably capture observable evidence.
Output:
```
Layer 1 Indicator Registry (stabilised)
```
### 5. Stage 2 — Dimension Formation (Layer 2 Design)
Dimensions correspond to **Layer 2 Score-Bearing Objects (SBOs)**.
Dimensions represent **conceptual properties of the response** that the rubric evaluates.
Dimension scores are derived from indicator evidence.
#### 5.1 Dimension Proposal
Indicators are grouped conceptually to form candidate dimensions.
Example:
```
D1 Accountability framing
    I1
    I2
D2 Role boundary and hand-off
    I3
    I4
    I5
D3 Professional obligations
    I6
```
Indicators may contribute to **multiple dimensions**.
Deliverable:
```
Dimension Registry
```
#### 5.2 Indicator–Dimension Mapping
Dimension scores are derived using **Layer 2 mapping tables**.
Mapping tables define:
```
indicator_score → dimension_score
```
These tables specify the threshold relationships between indicator evidence and dimension evidence levels.
Example:
```
dimension_score(D1)
    derived from indicators I1 and I2
```
#### 5.3 Empirical Dimension Testing
Dimension mappings are tested using the calibration dataset.
Procedure:
1. compute dimension scores for the sample dataset
2. inspect resulting distributions
3. compare results with qualitative evaluation of responses
Questions to evaluate:
- Do dimension levels correspond to meaningful differences between responses?
- Are dimensions conceptually distinct?
- Do indicators cluster as expected?
Adjustments may include:
- revising indicator–dimension membership
- adjusting threshold values in mapping tables
Output:
```
Layer 2 dimension mappings stabilised
```
### 6. Stage 3 — Component Performance Model (Layer 3 Design)
Layer 3 defines how **dimension evidence translates into component performance levels**.
Layer 3 SBO:
```
component_score
```
This stage is where **most rubric tuning occurs**, because it determines how conceptual evidence levels translate into performance classifications.
#### 6.1 Define Performance Scale
Typical performance scale:
```
exceeds_expectations
meets_expectations
approaching_expectations
below_expectations
not_demonstrated
```
#### 6.2 Construct Dimension → Performance Mapping
Mapping tables define:
```
dimension_score → component_score
```
Example conceptual logic:
```
strong evidence across all dimensions → exceeds_expectations
adequate evidence across most dimensions → meets_expectations
partial evidence → approaching_expectations
minimal evidence → below_expectations
```
These relationships are encoded using Layer 3 mapping tables.
#### 6.3 Empirical Testing
Apply the component mapping tables to the calibration dataset.
Inspect the resulting performance classifications.
Evaluation questions:
- Do most competent responses land in `meets_expectations`?
- Are high-quality responses rewarded with `exceeds_expectations`?
- Are weak responses clearly separated?
Adjustments may include:
- modifying threshold conditions
- adjusting dimension combinations
Output:
```
Layer 3 mapping stabilised
```
### 7. Stage 4 — Submission Score Derivation (Layer 4 Design)
Layer 4 defines how **component scores combine into a final submission score**.
Layer 4 SBO:
```
submission_score
```
Layer 4 mappings are typically simpler than Layer 3 mappings because the conceptual evaluation work has already been completed at the component level.
Possible strategies include:
```
averaging component performance
weighted component aggregation
minimum threshold rules
```
Mapping tables define:
```
component_score → submission_score
```
Empirical checks should confirm:
- the overall score distribution is reasonable
- strong submissions remain strong
- weak submissions remain clearly identified
Output:
```
Layer 4 mapping stabilised
```
### 8. Stage 5 — Rubric Freeze
The rubric is considered **construction-complete** when all scoring layers are stabilised.
The following artefacts must then be frozen:
```
indicator registry
dimension registry
mapping tables
scales
```
Two final artefacts are produced.
Human-readable specification:
```
Rubric Design Document
```
Machine-readable payload:
```
RUBRIC_<ASSESSMENT_ID>_PROD_payload_v01
```
This payload becomes the **authoritative rubric specification** used by scoring pipelines.
### 9. Relationship to the Canonical Grading Dataset
Pipeline 1A produces the canonical grading dataset organised as:
```
submission_id × component_id
```
Each row represents one student submission for one assessment component.
Pipeline 1B does **not modify this dataset**.
Instead, Pipeline 1B produces the rubric structures that will later be applied when evaluating these grading targets.
### 10. Architectural Principle
The layered rubric architecture separates analytic responsibilities across the scoring system.
```
Assignment pipelines define what evidence exists.
Rubric construction defines what will be evaluated.
Calibration determines how evidence is interpreted.
Scoring applies the rubric to the grading population.
```
The layered ontology allows each level of evaluation to be stabilised empirically using real student responses before scoring pipelines are executed.
