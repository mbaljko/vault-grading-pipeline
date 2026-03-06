### Pipeline 1B — Layered Rubric Construction Pipeline
This document defines the process for constructing and stabilising a **rubric for an assessment submission** under the **four-layer scoring ontology**.
A rubric is a **layered scoring specification** whose elements are stabilised iteratively using empirical evidence from real student responses.
The rubric defines how evidence observed in responses is transformed into scores across four scoring layers.
```
Layer 1 → indicator SBOs
Layer 2 → dimension SBOs
Layer 3 → component SBOs
Layer 4 → submission SBO
```
Rubric construction therefore proceeds **layer by layer**, beginning with observable indicators and progressing upward through dimension construction and performance mapping.
Calibration pipelines operate **after the rubric structure is stabilised and frozen**.
Throughout this pipeline, work occurs directly within the **Rubric Template document**.  
Deliverables therefore correspond to **specific sections of the Rubric Template**, which move through states such as:
```
Draft → Under Evaluation → Stabilised → Frozen
```
### 1. Upstream Inputs
Rubric construction operates on top of the **assignment payload specification architecture** produced by Pipeline 1A.
Required artefacts:
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
A submission typically contains multiple **components**, each representing a structured part of the assignment.
Example components:
```
SectionAResponse
SectionBResponse
SectionCResponse
SectionDResponse
SectionEResponse
```
Most rubric design and tuning work occurs at **Layer 3**, where **dimension evidence is translated into component performance levels**.
Layer 4 typically performs a relatively straightforward mapping of component scores to the final submission score.
Conceptually the rubric structure is:
```
submission
    components
        dimensions
        indicators
        mapping tables
```
Layer responsibilities:
```
Layer 1 → detect indicator evidence within each component response
Layer 2 → derive conceptual dimension evidence from indicator evidence
Layer 3 → translate dimension evidence into component performance levels
Layer 4 → combine component scores into a submission score
```
Because Layer 3 determines how conceptual evidence translates into performance levels, **most empirical tuning during rubric construction occurs at Layer 3**.
### 3. Stage 0 — Submission Analytic Specification
Before constructing indicators and dimensions, the analytic goals of the **entire submission** must be clarified.
Inputs:
```
<ASSESSMENT_ID>_AssignmentPayloadSpec_v01
```
From this input produce a **submission analytic brief**.
The analytic brief describes:
- the analytic goals of the assignment as a whole
- the conceptual claims students are expected to make
- the intellectual structure of the submission
- the role played by each component of the submission
The brief contains **subsections for each component**, describing the analytic purpose of that component.
Example structure:
```
Submission Analytic Brief
Overview
    analytic goals of the assignment
    conceptual claims students must articulate
Component: SectionAResponse
    analytic purpose
    conceptual focus
    expected forms of reasoning
Component: SectionBResponse
    analytic purpose
    conceptual focus
    expected forms of reasoning
Component: SectionCResponse
    analytic purpose
    conceptual focus
    expected forms of reasoning
```
The analytic brief serves as the conceptual foundation for indicator drafting and dimension formation.
#### Deliverables
```
<ASSESSMENT_ID>_SubmissionAnalyticBrief_v01
```
### 4. Stage 1 — Indicator Discovery and Evaluation Design (Layer 1)
Layer 1 defines how **observable textual evidence is detected within component responses**.
Layer 1 consists of two coupled structures in the Rubric Template:
```
5.4 Layer 1 SBO Instances
6.1 Layer 1 SBO Value Derivation
```
These sections define:
```
indicator registry
indicator evaluation specification
```
Indicators correspond to **Layer 1 Score-Bearing Objects (SBOs)**.
Indicators operate on the **Layer 1 Assessment Artefact**:
```
AA = submission_id × component_id
```
Indicator design and evaluation specification are developed **in parallel**, because the evaluation procedure determines whether the indicator definitions are operationally usable.
#### Stage 1.1 Indicator and Evaluation Co-Design
Indicators are initially derived from the relevant component subsection of the **Submission Analytic Brief**.
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
Typical indicator count:
```
4–8 indicators per component
```
At the same time, the **evaluation procedure for each indicator** is specified in the Rubric Template.
This specification defines:
```
indicator_definition
assessment_guidance
evaluation_notes
```
These fields populate:
```
Rubric Template: 6.1 Layer 1 SBO Value Derivation
```
The indicator registry itself is defined in:
```
Rubric Template: 5.4 Layer 1 SBO Instances
```
During this phase both sections remain **Draft**.
#### Deliverables
```
Rubric Template: 5.4 Layer 1 SBO Instances (Draft)
Rubric Template: 6.1 Layer 1 SBO Value Derivation (Draft)
```
#### Stage 1.2 Indicator Evaluation Testing
Indicator behaviour is tested using a **small calibration sample** of real student submissions.
Evaluation is performed using **LLM-generated scoring prompts**.
The operational workflow is:
```
1. wrapper prompt generates an indicator-scoring prompt
2. scoring prompt evaluates indicators for a calibration dataset
3. indicator_score values are produced
```
The wrapper prompt receives as inputs:
```
Rubric Template: 5.4 Layer 1 SBO Instances
Rubric Template: 6.1 Layer 1 SBO Value Derivation
```
This ensures the generated scoring prompt remains aligned with the rubric specification.
Example evaluation dataset structure:
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
- Are the evaluation instructions operationally clear for the scoring prompt?
Indicators and their evaluation specifications are revised iteratively until indicator detection behaves reliably on the calibration sample.
#### Deliverables
```
Rubric Template: 5.4 Layer 1 SBO Instances (Stabilised)
Rubric Template: 6.1 Layer 1 SBO Value Derivation (Stabilised)
```
Both sections are stabilised together because indicator definitions and their evaluation logic are interdependent.
### 5. Stage 2 — Dimension Formation (Layer 2 Design)
Dimensions correspond to **Layer 2 Score-Bearing Objects (SBOs)**.
Dimensions represent conceptual properties of responses.
#### 5.1 Dimension Drafting
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
#### Deliverables
```
Rubric Template: 5.3 Layer 2 SBO Instances (Draft)
```
#### 5.2 Indicator → Dimension Mapping
Dimension scores are derived using mapping tables.
```
indicator_score → dimension_score
```
#### Deliverables
```
Rubric Template: 6.2 Layer 2 Mapping Tables (Draft)
```
#### 5.3 Empirical Dimension Testing
Dimension mappings are evaluated using the calibration dataset.
Procedure:
```
compute dimension scores
examine distribution
compare with qualitative judgement
```
Adjust:
- indicator–dimension membership
- threshold values in mapping tables
#### Deliverables
```
Rubric Template: 5.3 Layer 2 SBO Instances (Stabilised)
Rubric Template: 6.2 Layer 2 Mapping Tables (Stabilised)
```
### 6. Stage 3 — Component Performance Model (Layer 3 Design)
Layer 3 translates **dimension evidence into component performance levels**.
Layer 3 SBO:
```
component_score
```
Most rubric tuning occurs at this stage.
#### 6.1 Define Performance Scale
Typical scale:
```
exceeds_expectations
meets_expectations
approaching_expectations
below_expectations
not_demonstrated
```
#### Deliverables
```
Rubric Template: 5.2 Layer 3 SBO Instances (Draft)
```
#### 6.2 Construct Dimension → Performance Mapping
Mapping tables define:
```
dimension_score → component_score
```
#### Deliverables
```
Rubric Template: 6.3 Layer 3 Mapping Tables (Draft)
```
#### 6.3 Empirical Performance Testing
Apply mappings to the calibration dataset.
Evaluate:
- expected majority in `meets_expectations`
- strong responses in `exceeds_expectations`
- weak responses clearly separated
Adjust mapping thresholds as needed.
#### Deliverables
```
Rubric Template: 5.2 Layer 3 SBO Instances (Stabilised)
Rubric Template: 6.3 Layer 3 Mapping Tables (Stabilised)
```
### 7. Stage 4 — Submission Score Derivation (Layer 4 Design)
Layer 4 combines component scores into the final submission score.
Layer 4 SBO:
```
submission_score
```
Possible strategies:
```
average component scores
weighted component aggregation
minimum threshold rules
```
Mapping tables define:
```
component_score → submission_score
```
#### Deliverables
```
Rubric Template: 5.1 Layer 4 SBO Instances (Draft → Stabilised)
Rubric Template: 6.4 Layer 4 Mapping Tables (Draft → Stabilised)
```
### 8. Stage 5 — Rubric Freeze
The rubric is considered **construction-complete** when all sections of the Rubric Template have been stabilised.
Sections frozen:
```
5.4 Layer 1 SBO Instances
6.1 Layer 1 SBO Value Derivation
5.3 Layer 2 SBO Instances
6.2 Layer 2 Mapping Tables
5.2 Layer 3 SBO Instances
6.3 Layer 3 Mapping Tables
5.1 Layer 4 SBO Instances
6.4 Layer 4 Mapping Tables
```
#### Deliverables
Human-readable specification:
```
Rubric Design Document
```
Machine-readable payload:
```
RUBRIC_<ASSESSMENT_ID>_PROD_payload_v01
```
This payload becomes the **authoritative rubric specification** used by calibration and scoring pipelines.
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
