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
#### Stage 1.1 Layer 1 SBO Instance Definition
Layer 1 indicators are represented in the rubric as **Layer 1 Score-Bearing Object (SBO) instances**.
Each indicator instance corresponds to one row in:
```
Rubric Template: 5.4 Layer 1 SBO Instances
```
This section defines the **identity and registry information** for the indicator SBOs.
Typical fields include:
```
sbo_identifier
sbo_identifier_shortid
submission_id
component_id
indicator_id
sbo_short_description
```
At this stage the goal is to establish the **set of indicator SBO instances** that will be evaluated for each component.
Indicators are derived from the relevant component subsection of the **Submission Analytic Brief**.
The `sbo_short_description` provides a concise statement of the analytic signal the indicator represents.
Example forms:
```
response identifies where accountability resides
response identifies a responsibility outside the professional role
response describes a responsibility hand-off
```
Indicator instance design rules:
Indicator SBO instances must:
- correspond to observable textual signals in the response
- avoid embedding scoring thresholds
- avoid referencing performance levels
- avoid directly encoding dimension satisfaction
Typical indicator count:
```
4–8 indicator SBO instances per component
```
The indicator registry defined in Section **5.4** establishes **which Layer 1 SBOs exist**.
#### Deliverables
```
Rubric Template: 5.4 Layer 1 SBO Instances (Draft)
```
#### Stage 1.2 Layer 1 SBO Evaluation Specification
Once indicator SBO instances are defined, the rubric must specify **how the value of each indicator SBO is derived from the Assessment Artefact**.
This logic is defined in:
```
Rubric Template: 6.1 Layer 1 SBO Value Derivation
```
This section specifies how the scoring system derives the value of:
```
indicator_score
```
from the Layer 1 Assessment Artefact:
```
AA = submission_id × component_id
```
For each indicator SBO instance, the evaluation specification provides the **evaluation surface and interpretation guidance** used during indicator scoring.
Typical fields include:
```
indicator_definition
assessment_guidance
evaluation_notes
```
These fields are used by the **wrapper prompt that generates the indicator-scoring prompt**.
Indicator evaluation specifications are typically **iteratively refined** during testing on calibration samples, while the **indicator SBO instance registry (Section 5.4)** usually remains stable.
#### Deliverables
```
Rubric Template: 6.1 Layer 1 SBO Value Derivation (Draft)
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
#### Stage 1.1 Indicator Initial Definition
Indicators represent **observable analytic signals** that may appear in a response.
Indicators are initially derived from the relevant component subsection of the **Submission Analytic Brief**.
An indicator defines **what conceptual feature of the response should be detectable**, but does not define how the feature is evaluated.
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
Indicators are registered in:
```
Rubric Template: 5.4 Layer 1 SBO Instances
```
At this stage the indicator registry establishes:
```
indicator identifiers
indicator short descriptions
component association
```
#### Deliverables
```
Rubric Template: 5.4 Layer 1 SBO Instances (Draft)
```
#### Stage 1.2 Indicator Evaluation Testing (Iterative Testing)
Once indicators are defined, the **procedure used to evaluate indicator evidence** must be specified.
We begin with a basic technique
This specification defines **how the scoring system determines the indicator_score** for each indicator.
Indicator evaluation behaviour is defined in:
```
Rubric Template: 6.1 Layer 1 SBO Value Derivation
```
The evaluation specification typically includes:
```
indicator_definition
assessment_guidance
evaluation_notes
```
These fields provide operational instructions used by the **wrapper prompt that generates the indicator-scoring prompt**.
The evaluation specification may be revised multiple times as indicator behaviour is tested on calibration data.
The **indicator registry (Section 5.4)** usually remains stable while the **evaluation specification (Section 6.1)** is iteratively refined.
#### Deliverables
```
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
### 5. Stage 2 — Dimension Formation and Evidence Mapping (Layer 2)
Dimensions correspond to **Layer 2 Score-Bearing Objects (SBOs)**.
Dimensions represent conceptual properties of responses that are inferred from patterns of **indicator evidence**.
Layer 2 consists of two coupled structures in the Rubric Template:
```
5.3 Layer 2 SBO Instances
6.2 Layer 2 SBO Value Derivation
```
These sections define:
```
dimension registry
indicator → dimension mapping rules
```
Dimension construction and mapping design are developed **iteratively**, because indicator evidence patterns often reveal whether a proposed dimension structure is conceptually meaningful and operationally stable.
#### Stage 2.1 Dimension Drafting
Candidate dimensions are derived from the **Submission Analytic Brief** and from patterns observed in indicator evidence.
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
Dimension design rules:
Dimensions must:
- represent conceptually distinct response properties
- correspond to the analytic goals of the assignment component
- remain interpretable based on observable indicator evidence
- avoid embedding performance thresholds directly
#### Deliverables
```
Rubric Template: 5.3 Layer 2 SBO Instances (Draft)
```
#### Stage 2.2 Indicator → Dimension Mapping Design
Dimension scores are derived using **mapping tables** that translate indicator evidence into dimension evidence levels.
Mapping form:
```
indicator_score → dimension_score
```
These mapping tables define the operational logic by which patterns of indicator evidence determine dimension evidence levels.
Mapping rules must follow the **mapping table specification defined in the Rubric Template**.
Mapping tables are defined in:
```
Rubric Template: 6.2 Layer 2 SBO Value Derivation
```
#### Deliverables
```
Rubric Template: 6.2 Layer 2 SBO Value Derivation (Draft)
```
#### Stage 2.3 Empirical Dimension Testing
Candidate dimension structures and mapping rules are evaluated using the **indicator scoring dataset** produced during Stage 1.
Procedure:
```
apply indicator → dimension mappings
compute dimension_score values
examine score distributions
compare with qualitative judgement of responses
```
Evaluation questions:
- Do dimension scores correspond to meaningful conceptual distinctions?
- Are dimensions redundant or overlapping?
- Do mapping thresholds produce stable behaviour across responses?
Possible revisions:
- adjust indicator–dimension membership
- revise mapping table threshold conditions
- merge or split dimensions if necessary
Iteration continues until dimension behaviour appears **conceptually coherent and empirically stable**.
#### Deliverables
```
Rubric Template: 5.3 Layer 2 SBO Instances (Stabilised)
Rubric Template: 6.2 Layer 2 SBO Value Derivation (Stabilised)
```
### 6. Stage 3 — Component Performance Model (Layer 3 Design)
Layer 3 translates **dimension evidence levels into component performance levels**.
Layer 3 consists of two structures in the Rubric Template:
```
5.2 Layer 3 SBO Instances
6.3 Layer 3 SBO Value Derivation
```
These sections define:
```
component registry
dimension → component performance mapping rules
```
Most rubric tuning typically occurs at this stage because component scores must align with **human judgement of response quality**.
#### Stage 3.1 Component Performance Scale Definition
The component performance scale defines the set of possible **Layer 3 performance outcomes**.
Typical scale:
```
exceeds_expectations
meets_expectations
approaching_expectations
below_expectations
not_demonstrated
```
These values correspond to the **component_performance_scale** defined in the Rubric Template.
#### Deliverables
```
Rubric Template: 5.2 Layer 3 SBO Instances (Draft)
```
#### Stage 3.2 Dimension → Component Mapping Design
Component scores are derived using mapping tables that translate **dimension evidence levels** into **component performance levels**.
Mapping form:
```
dimension_score → component_score
```
Mapping tables define the performance model for the component.
These tables are defined in:
```
Rubric Template: 6.3 Layer 3 SBO Value Derivation
```
#### Deliverables
```
Rubric Template: 6.3 Layer 3 SBO Value Derivation (Draft)
```
#### Stage 3.3 Empirical Performance Testing
The component performance model is evaluated using the **calibration dataset**.
Procedure:
```
apply dimension → component mappings
compute component_score values
examine score distribution
compare outcomes with qualitative judgement
```
Evaluation questions:
- Do strong responses reliably receive `exceeds_expectations`?
- Does the majority of competent responses fall within `meets_expectations`?
- Are weaker responses clearly separated into lower performance categories?
Mapping thresholds are revised iteratively until the performance model behaves as expected.
#### Deliverables
```
Rubric Template: 5.2 Layer 3 SBO Instances (Stabilised)
Rubric Template: 6.3 Layer 3 SBO Value Derivation (Stabilised)
```
### 7. Stage 4 — Submission Score Derivation (Layer 4 Design)
Layer 4 derives the **overall submission score** from the set of component scores.
Layer 4 consists of two structures in the Rubric Template:
```
5.1 Layer 4 SBO Instances
6.4 Layer 4 SBO Value Derivation
```
These sections define:
```
submission registry
component → submission mapping rules
```
Because the rubric applies to the **entire submission**, Layer 4 typically involves **straightforward aggregation rules** applied to component scores.
#### Stage 4.1 Submission Aggregation Design
Submission scores are derived using mapping tables that translate **component scores** into a **submission performance level**.
Mapping form:
```
component_score → submission_score
```
Possible strategies include:
```
average component scores
weighted component aggregation
minimum threshold conditions
```
Mapping rules are defined in:
```
Rubric Template: 6.4 Layer 4 SBO Value Derivation
```
#### Deliverables
```
Rubric Template: 5.1 Layer 4 SBO Instances (Draft)
Rubric Template: 6.4 Layer 4 SBO Value Derivation (Draft)
```
#### Stage 4.2 Submission Model Confirmation
Submission aggregation rules are tested using the calibration dataset.
Procedure:
```
apply component → submission mappings
compute submission_score values
verify overall distribution and alignment with judgement
```
Because submission scoring is derived from component scores, relatively little tuning is usually required at this stage.
#### Deliverables
```
Rubric Template: 5.1 Layer 4 SBO Instances (Stabilised)
Rubric Template: 6.4 Layer 4 SBO Value Derivation (Stabilised)
```
### 8. Stage 5 — Rubric Freeze
The rubric is considered **construction-complete** when all sections of the Rubric Template have been stabilised.
Frozen sections:
```
5.4 Layer 1 SBO Instances
6.1 Layer 1 SBO Value Derivation
5.3 Layer 2 SBO Instances
6.2 Layer 2 SBO Value Derivation
5.2 Layer 3 SBO Instances
6.3 Layer 3 SBO Value Derivation
5.1 Layer 4 SBO Instances
6.4 Layer 4 SBO Value Derivation
```
Once frozen:
- SBO identifiers must not change
- mapping tables must not change
- scale definitions must not change
#### Deliverables
Human-readable documentation:
```
Rubric Design Document
```
Machine-readable rubric payload:
```
RUBRIC_<ASSESSMENT_ID>_PROD_payload_v01
```
This payload becomes the **authoritative rubric specification** used by calibration and scoring pipelines.
### 9. Relationship to the Canonical Grading Dataset
Pipeline 1A produces the canonical grading dataset organised as:
```
submission_id × component_id
```
Each row represents one student submission for one assignment component.
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
The layered ontology allows each level of evaluation to be stabilised empirically using real student responses before production scoring pipelines are executed.
