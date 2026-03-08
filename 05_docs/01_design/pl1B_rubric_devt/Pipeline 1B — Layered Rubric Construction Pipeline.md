### Pipeline 1B — Layered Rubric Construction Pipeline
This document defines the process for constructing and stabilising a **rubric for an assessment submission** under the **four-layer scoring ontology**.
A rubric is a **layered scoring specification** whose elements are stabilised iteratively using empirical evidence from real student responses.
The rubric defines how evidence observed in responses is transformed into scores across four scoring layers.

| layer | score-bearing object (SBO) |
|---|---|
| Layer 1 | indicator SBOs |
| Layer 2 | dimension SBOs |
| Layer 3 | component SBOs |
| Layer 4 | submission SBO |
Rubric construction therefore proceeds **layer by layer**, beginning with analytic interpretation of the assignment, then moving through observable indicators, dimension construction, component performance mapping, and submission aggregation.
Calibration pipelines operate **after the rubric structure is stabilised and frozen**.
Throughout this pipeline, work occurs directly within the **Rubric Template document**. Deliverables therefore correspond to **specific sections of the Rubric Template**, which move through states such as:

| state progression |
|---|
| Draft → Under Evaluation → Stabilised → Frozen |
### 1. Upstream Inputs
Rubric construction operates on top of the **assignment payload specification architecture** produced by **Pipeline 1A**.
#### Required artefact
```
<ASSESSMENT_ID>_AssignmentPayloadSpec_v01
```
This document defines the **canonical structural contract** for the assessment payload. Rubric construction must remain fully compatible with this specification.
#### Canonical Identifier Registry

| field_name | type | description |
|---|---|---|
| `submission_id` | integer | de-identified identifier representing one student submission |
| `component_id` | string | identifier representing one assignment component |
#### Canonical Evidence Surface Registry

| field_name | type | evidentiary_status | description |
|---|---|---|---|
| `response_text` | text | evidence | participant-authored response text used during rubric evaluation |
#### Canonical Scoring Unit

| scoring_unit | description |
|---|---|
| `submission_id × component_id` | canonical unit of evidence evaluated during rubric scoring |
These definitions determine the **Assessment Artefact (AA)** evaluated during rubric scoring.

| scoring layer | assessment artefact |
|---|---|
| Layers 1–3 | `submission_id × component_id` |
| Layer 4 | `submission_id` |
#### Component-level calibration payloads
Component-level calibration datasets are **derived directly from the canonical dataset defined in the Assignment Payload Specification**.
A calibration payload for a specific component is obtained by filtering the canonical dataset:
```
component_id = <COMPONENT_ID>
```
The resulting dataset retains the canonical schema:

| field_name | type | evidentiary_status |
|---|---|---|
| `submission_id` | integer | identifier |
| `component_id` | string | identifier |
| `response_text` | text | evidence |
Example calibration dataset for Section A:
```
component_id = SectionAResponse
```
Resulting payload structure:

| field_name |
|---|
| `submission_id` |
| `component_id` |
| `response_text` |
Because the Assignment Payload Specification already defines the canonical dataset schema and evidence surfaces, **separate component-level payload specification documents are not required**.
All calibration and scoring pipelines must therefore treat:
```
<ASSESSMENT_ID>_AssignmentPayloadSpec_v01
```
as the **authoritative structural specification** for the assessment payload.
#### Compatibility requirement
Rubric construction must ensure that:
- all `component_id` values referenced by rubric SBOs exist in the **Component Registry** defined by the Assignment Payload Specification
- all evidence used during scoring is drawn exclusively from the defined **evidence surface** (`response_text`)
- all scoring units correspond to the canonical structural unit

| structural rule |
|---|
| `submission_id × component_id` |
This guarantees that rubric structures remain **fully compatible with the canonical dataset produced by Pipeline 1A**.
### 2. Rubric Scope
The rubric applies to the **entire submission**.
The final score produced by the rubric corresponds to the **Layer 4 submission Score-Bearing Object (SBO)**:
```
submission_score
```
A submission typically contains multiple **components**, each representing a structured part of the assignment.
#### Example component identifiers

| component_id |
|---|
| `SectionAResponse` |
| `SectionBResponse` |
| `SectionCResponse` |
| `SectionDResponse` |
| `SectionEResponse` |
Most rubric design and tuning work occurs at **Layer 3**, where **dimension evidence is translated into component performance levels**.
Layer 4 typically performs a relatively straightforward mapping of component scores to the final submission score.
#### Conceptual rubric hierarchy

| level | entity |
|---|---|
| submission | overall assignment |
| components | structured response sections |
| dimensions | conceptual evaluation criteria |
| indicators | observable evidence checks |
#### Layer responsibilities

| layer | responsibility |
|---|---|
| Layer 1 | detect indicator evidence within component responses |
| Layer 2 | derive conceptual dimension evidence from indicator evidence |
| Layer 3 | translate dimension evidence into component performance levels |
| Layer 4 | combine component scores into a submission score |
Because Layer 3 determines how conceptual evidence translates into performance levels, **most empirical tuning during rubric construction occurs at Layer 3**.
### 3. Stage 0 — Submission Analytic Specification
Stage 0 establishes the **analytic interpretation of the assignment** before any rubric structures are instantiated.
It produces a human-readable analytic scaffold that guides later indicator and dimension construction.
#### Stage 0.1 Submission Analytic Brief
Before constructing indicators and dimensions, the analytic goals of the **entire submission** must be clarified.
Input:
```
<ASSESSMENT_ID>_AssignmentPayloadSpec_v01
```
From this input produce a **submission analytic brief**.
The analytic brief describes:
- the analytic goals of the assignment as a whole
- the conceptual claims students are expected to make
- the intellectual structure of the submission
- the role played by each component of the submission
Example analytic brief structure:

| section | content |
|---|---|
| Overview | analytic goals and conceptual claims |
| Component: SectionAResponse | analytic purpose and expected reasoning |
| Component: SectionBResponse | analytic purpose and expected reasoning |
| Component: SectionCResponse | analytic purpose and expected reasoning |
#### Deliverables
Produce the following document:
```
<ASSESSMENT_ID>_SubmissionAnalyticBrief_v01.md
```
The document must contain the following sections.

| section                                         | required content                                                                                                                       |
| ----------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| Overview — Analytic Goals and Conceptual Claims | analytic goals of the assignment, conceptual claims students are expected to produce, and the intellectual structure of the submission |
| Components                                      | analytic interpretation of each assignment component defined in the Component Registry                                                 |
| Conceptual Structure of the Submission          |                                                                                                                                        |
Within the **Components** section, the document must contain one subsection for **each `component_id` defined in the Component Registry** of:
```
<ASSESSMENT_ID>_AssignmentPayloadSpec_v01
```
Each component subsection must contain:

| subsection content | description |
|---|---|
| Analytic purpose | the conceptual purpose of the component within the submission |
| Expected reasoning structure | the types of reasoning or positioning moves the component asks the student to perform |
Example structure:
```
1. Overview — Analytic Goals and Conceptual Claims
2. Components
   2.1 Component: <component_id_1>
       Analytic purpose
       Expected reasoning structure
   2.2 Component: <component_id_2>
       Analytic purpose
       Expected reasoning structure
   ...
   2.n Component: <component_id_n>
       Analytic purpose
       Expected reasoning structure
3. Conceptual Structure of the Submission
```
The set of component subsections must correspond exactly to the component identifiers defined in:
```
<ASSESSMENT_ID>_AssignmentPayloadSpec_v01
```
Later stages extend the same document with additional sections:
```
4. Analytic Sub-space Identification (Stage 0.2)
5. Contrastive Pattern Discovery and Candidate Indicator Sketches (Stage 0.3)
```
#### Stage 0.2 Analytic Sub-space Identification
Some components ask students to perform **multiple distinct analytic moves**.
These are treated as **analytic sub-spaces**.
An analytic sub-space is a **task-defined conceptual area within a component response**.
Analytic sub-spaces are derived from the component instructions and recorded in the **Submission Analytic Brief**.
They are **not part of the scoring ontology** and do not appear in the Rubric Payload.
#### Example analytic sub-space registry

| component | sub-space_id | analytic focus |
|---|---|---|
| `SectionAResponse` | A1 | accountability locus |
| `SectionAResponse` | A2 | role boundary and responsibility hand-off |
| `SectionAResponse` | A3 | professional obligations |
Analytic sub-spaces serve as a **design scaffold** for indicator discovery and later dimension formation.
#### Deliverables
Stage 0.2 extends the previously created document:
```
<ASSESSMENT_ID>_SubmissionAnalyticBrief_v01.md
```
by adding the following numbered section:
```
4. Analytic Sub-space Identification
```
This section must contain a **registry of analytic sub-spaces for each assignment component**.
The registry must include one row for **each analytic sub-space derived from the component instructions**.

| field | description |
|---|---|
| `component` | the `component_id` defined in `<ASSESSMENT_ID>_AssignmentPayloadSpec_v01` |
| `sub-space_id` | analytic sub-space identifier using the convention `<SECTION_LETTER><INTEGER>` |
| `analytic focus` | concise description of the conceptual task performed within that sub-space |
The analytic sub-space registry must include **all components defined in the Component Registry** of:
```
<ASSESSMENT_ID>_AssignmentPayloadSpec_v01
```
If a component contains only a single analytic task, it may be represented by a **single analytic sub-space**.
This section provides the **analytic scaffolding used during Stage 0.3 contrastive pattern discovery** and **Stage 1 indicator discovery**.
#### Stage 0.3 Contrastive Pattern Discovery Pass
Before defining indicator SBO instances, use a **small calibration sample of real student responses** to discover contrastive response patterns.
This step surfaces **observable signals actually present in student writing** rather than relying only on the assignment description.
The purpose is to produce **candidate indicators and candidate dimensions**.
These outputs remain **analytic hypotheses** at this stage.
They do not become rubric structures until they are instantiated as SBO instances and stabilised through empirical testing.
##### Calibration sample structure

| field_name |
|---|
| `submission_id` |
| `component_id` |
| `cleaned_response_text` |
Typical calibration sample size:

| recommended sample |
|---|
| 20–40 responses |
##### Contrastive signal extraction procedure
Contrastive analysis is performed **within each analytic sub-space**.

| step | operation                                                      |
| ---- | -------------------------------------------------------------- |
| 1    | identify analytic sub-spaces within the component              |
| 2    | prompt the model to identify contrastive response pairs        |
| 3    | extract textual signals distinguishing the responses           |
| 4    | group signals into candidate indicators                        |
| 5    | identify early signal clusters suggesting candidate dimensions |
Example extracted signals:

| candidate signal |
|---|
| explicit assignment of accountability |
| recognition of distributed responsibility |
| description of responsibility hand-off |
| explicit reference to regulatory oversight |
These signals become **candidate indicators**.  
Signal clusters may also suggest **candidate dimensions**.
##### Deliverables
Stage 0.3 extends the previously created document:
```
<ASSESSMENT_ID>_SubmissionAnalyticBrief_v01.md
```
by adding the following numbered section:
```
5. Contrastive Pattern Discovery and Candidate Indicator Sketches
```
This section must contain the following subsections.

| subsection                                  | required content                                                                           |
| ------------------------------------------- | ------------------------------------------------------------------------------------------ |
| 5.1 Calibration sample description          | description of the calibration dataset used for contrastive analysis                       |
| 5.2 Contrastive response observations       | examples of contrastive response pairs identified within analytic sub-spaces               |
| 5.3 Candidate indicator signals             | list of observable textual signals extracted from contrasts, grouped by analytic sub-space |
| 5.4 Candidate indicator set                 | consolidated list of candidate indicators derived from the extracted signals               |
| 4.5 Candidate dimension sketches (optional) | early clusters of related signals suggesting possible conceptual dimensions                |
The **candidate indicator signals** must be grounded in **observable language present in the calibration responses**.
At this stage:
- indicators remain **analytic hypotheses**
- no **indicator SBO identifiers** are assigned
- no **scoring rules or thresholds** are defined
Formal indicator SBO instances and evaluation specifications are created later during **Stage 1 — Indicator Discovery and Evaluation Design (Layer 1)**.
#### Exit condition for Stage 0
Stage 0 is complete when the Submission Analytic Brief contains:
- clearly defined analytic purpose for each component
- identified analytic sub-spaces
- candidate indicators grounded in contrastive evidence
- early candidate dimension groupings
#### Deliverables
```
<ASSESSMENT_ID>_SubmissionAnalyticBrief_v01
    └ component analytic sketches NAMED: "8. Stage 0.2 — Analytic Sub-space Identification"
        ├ analytic sub-spaces 
        ├ candidate indicators
        └ candidate dimensions
```
### 4. Stage 1 — Indicator Discovery and Evaluation Design (Layer 1)
Layer 1 defines how **observable textual evidence is detected within component responses**.
Layer 1 consists of two coupled structures in the Rubric Template:
```text
5.4 Layer 1 SBO Instances
6.1 Layer 1 SBO Value Derivation
```
These sections define:
```text
indicator SBO registry
indicator evaluation specification
```
Indicators correspond to **Layer 1 Score-Bearing Objects (SBOs)**.
Indicators operate on the **Layer 1 Assessment Artefact**:
```text
AA = submission_id × component_id
```
Indicator instance design and evaluation specification are developed using the candidate indicators produced in **Stage 0**.
#### Stage 1.1 — Layer 1 SBO Instance Definition
Layer 1 indicators are represented in the rubric as **Layer 1 Score-Bearing Object (SBO) instances**.
Each indicator instance corresponds to one row in:
```text
Rubric Template: 5.4 Layer 1 SBO Instances
```
This section defines the **identity and registry information** for the indicator SBOs.
Typical fields include:
```text
sbo_identifier
sbo_identifier_shortid
submission_id
component_id
indicator_id
sbo_short_description
```
At this stage the goal is to establish the **set of indicator SBO instances** that will be evaluated for each component.
Indicators are derived from:
```text
Submission Analytic Brief
analytic sub-spaces
contrastively extracted candidate signals
```
The `sbo_short_description` provides a concise statement of the analytic signal the indicator represents.
Example forms:
```text
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
```text
4–8 indicator SBO instances per component
```
The indicator registry defined in Section **5.4** establishes **which Layer 1 SBOs exist**.
##### Deliverable
```text
Rubric Template: 5.4 Layer 1 SBO Instances (Draft)
```
#### Stage 1.2 — Drafting the Indicator Evaluation Specification
Once the **Layer 1 SBO instance registry** has been defined, a **draft evaluation specification** must be created describing **how each indicator will be detected in the response text**.
This specification populates the following section of the Rubric Template:
```text
Rubric Template: 6.1 Layer 1 SBO Value Derivation (Draft)
```
This step converts the **indicator registry** into an **operational evaluation specification** that can be used by scoring prompts.
The goal of this step is to define:
```text
how indicator_score values are derived from response_text
```
for each indicator SBO instance.
##### Purpose of Section 6.1
Section **6.1 Layer 1 SBO Value Derivation** defines the procedure for deriving:
```text
indicator_score
```
from the Layer 1 Assessment Artefact:
```text
AA = submission_id × component_id
```
Indicator scores are evaluated using the **indicator evidence scale**:
```text
evidence
partial_evidence
little_to_no_evidence
```
Section 6.1 therefore provides the **evaluation instructions used by the scoring system** when examining a component response.
##### Drafting the evaluation specification
For each indicator defined in **Section 5.4**, Section **6.1** must provide an **evaluation specification block**.
Typical fields include:
```text
indicator_definition
assessment_guidance
evaluation_notes
```
These fields describe **how the evaluator should detect the analytic signal represented by the indicator**.
###### Field meanings

| field | purpose |
|---|---|
| `indicator_definition` | conceptual description of the analytic signal being detected |
| `assessment_guidance` | operational guidance describing how the signal may appear in response text |
| `evaluation_notes` | clarifications, edge cases, exclusions, or common misinterpretations |
###### Example evaluation specification block
```text
Indicator: I_PPP_SecA_I01
sbo_short_description: distributed responsibility attribution
indicator_definition
Detects statements describing responsibility as distributed across multiple actors such as individuals, teams, institutions, or tools.
assessment_guidance
Look for explicit language indicating that responsibility is shared, layered, or distributed across different actors or organisational levels.
evaluation_notes
Do not assign evidence when the response only mentions collaboration without attributing responsibility across actors.
```
Each **indicator SBO instance defined in Section 5.4** must have a corresponding **evaluation specification** in Section 6.1.
##### Deliverable
```text
Rubric Template: 6.1 Layer 1 SBO Value Derivation (Draft)
```
At this point the rubric contains both:
```text
5.4 Layer 1 SBO Instances (Draft)
6.1 Layer 1 SBO Value Derivation (Draft)
```
Together these sections define:
```text
which indicators exist
how those indicators are evaluated
```
#### Stage 1.3 — Layer 1 SBO Iterative Development
Layer 1 SBO development establishes how **indicator scores are derived from the Assessment Artefact (AA)**.
Layer 1 behaviour is defined by two sections of the Rubric Template:
```text
Rubric Template: 5.4 Layer 1 SBO Instances
Rubric Template: 6.1 Layer 1 SBO Value Derivation
```
These sections jointly define:
```text
indicator SBO registry
indicator evaluation specification
```
Layer 1 SBO development proceeds through an **iterative testing process using a calibration sample of student submissions**.
##### Initial condition
The iterative process begins once both of the following exist:
```text
Rubric Template: 5.4 Layer 1 SBO Instances (Draft)
Rubric Template: 6.1 Layer 1 SBO Value Derivation (Draft)
```
These sections together define the **initial indicator scoring behaviour**.
##### Iterative testing process
Indicator behaviour is tested using a **calibration sample** of student submissions.

Stage 1.3 should begin by testing Layer 1 SBO behaviour on the same calibration sample used in Stage 0.3, since that sample grounded candidate indicator discovery. Once the indicator registry and evaluation specification become coherent, Stage 1.3 should also test behaviour on a separate holdout calibration sample to reduce overfitting and confirm that indicator scoring generalises beyond the discovery sample.

Evaluation is performed using **LLM-generated scoring prompts**.
Operational workflow:
```text
1. wrapper prompt generates an indicator-scoring prompt
2. scoring prompt evaluates indicators for a calibration dataset
3. indicator_score values are produced
```
The wrapper prompt receives the following rubric sections as inputs:
```text
Rubric Template: 5.4 Layer 1 SBO Instances
Rubric Template: 6.1 Layer 1 SBO Value Derivation
```
This ensures the generated scoring prompt remains aligned with the rubric specification.
Example evaluation dataset structure:
```text
submission_id
component_id
I1
I2
I3
I4
I5
```
##### Evaluation questions
During calibration testing, examine whether:
- indicators detect the intended signals
- false positives or false negatives occur
- indicators are ambiguous or overlapping
- evaluation instructions are operationally clear for the scoring prompt
During this process:
- the **evaluation specification (Section 6.1)** is typically revised multiple times
- the **indicator SBO registry (Section 5.4)** may occasionally be adjusted if indicators prove redundant or ineffective
This testing loop is repeated until indicator scoring behaviour appears stable on the calibration sample.
##### Exit condition
Layer 1 SBO development is considered complete when:
- the set of **indicator SBO instances** is stable
- the **evaluation specification** consistently produces reliable `indicator_score` values on the calibration sample
- the scoring prompt generated from the rubric sections behaves predictably
At this point the following rubric sections are marked as stabilised:
```text
Rubric Template: 5.4 Layer 1 SBO Instances (Stabilised)
Rubric Template: 6.1 Layer 1 SBO Value Derivation (Stabilised)
```
### 5. Stage 2 — Dimension Formation and Evidence Mapping (Layer 2)
Layer 2 establishes how **dimension scores are derived from indicator evidence**.
Layer 2 behaviour is defined by two sections of the Rubric Template:
```text
Rubric Template: 5.3 Layer 2 SBO Instances
Rubric Template: 6.2 Layer 2 SBO Value Derivation
```
These sections jointly define:
```text
dimension SBO registry
indicator → dimension mapping rules
```
Dimension formation proceeds through an **iterative development process using the indicator scoring dataset produced during Stage 1**.
#### Stage 2.1 Layer 2 SBO Iterative Development
##### Initial condition
The process begins once **Layer 1 indicator scoring behaviour has stabilised**.
At this stage:
```text
Rubric Template: 5.3 Layer 2 SBO Instances (Draft)
```
defines the initial set of dimension SBO instances.
Each dimension instance specifies:
```text
submission_id
component_id
dimension_id
sbo_identifier
sbo_identifier_shortid
sbo_short_description
```
Candidate dimensions are derived from:
```text
Submission Analytic Brief
analytic sub-spaces
contrastively extracted candidate indicators
observed indicator evidence patterns
```
Indicators may contribute evidence to **multiple dimensions**.
The rubric must also contain a **draft specification for how dimension scores are derived from indicator evidence**, recorded in:
```text
Rubric Template: 6.2 Layer 2 SBO Value Derivation (Draft)
```
##### Iterative testing process
Dimension behaviour is evaluated using the **indicator scoring dataset produced during Stage 1**.
Operational workflow:
```text
1. apply indicator → dimension mapping tables
2. compute dimension_score values
3. examine score distributions
4. compare dimension behaviour with qualitative judgement
```
Example dataset structure:
```text
submission_id
component_id
I1
I2
I3
I4
I5
D1
D2
D3
```
Evaluation questions:
- Do dimension scores correspond to meaningful conceptual distinctions?
- Are dimensions redundant or overlapping?
- Do mapping thresholds produce stable behaviour across responses?
- Do dimension scores reflect the intended analytic properties?
Possible revisions include:
```text
adjust indicator–dimension membership
revise mapping table threshold conditions
merge or split dimensions
```
During this process:
- the **dimension SBO registry (Section 5.3)** may be adjusted
- the **mapping rules (Section 6.2)** are typically revised repeatedly
The loop continues until dimension behaviour appears **conceptually coherent and empirically stable**.
##### Exit condition
Layer 2 development is complete when:
- the set of **dimension SBO instances** is stable
- mapping tables consistently produce reliable `dimension_score` values
- dimension scores correspond to meaningful analytic distinctions
At this point the following sections are stabilised:
```text
Rubric Template: 5.3 Layer 2 SBO Instances (Stabilised)
Rubric Template: 6.2 Layer 2 SBO Value Derivation (Stabilised)
```
### 6. Stage 3 — Component Performance Model (Layer 3)
Layer 3 establishes how **dimension evidence is translated into component performance levels**.
Layer 3 behaviour is defined by:
```text
Rubric Template: 5.2 Layer 3 SBO Instances
Rubric Template: 6.3 Layer 3 SBO Value Derivation
```
These sections define:
```text
component SBO registry
dimension → component performance mapping rules
```
Most rubric tuning occurs at this stage because component scores must align with **human judgement of response quality**.
#### Stage 3.1 Layer 3 SBO Iterative Development
##### Initial condition
The process begins once **dimension scoring behaviour has stabilised**.
At this stage:
```text
Rubric Template: 5.2 Layer 3 SBO Instances (Draft)
```
defines the component SBO instances representing assignment components.
Component scores are evaluated using the **component performance scale**:
```text
exceeds_expectations
meets_expectations
approaching_expectations
below_expectations
not_demonstrated
```
The rubric must also contain a **draft specification for how component scores are derived from dimension evidence**, defined in:
```text
Rubric Template: 6.3 Layer 3 SBO Value Derivation (Draft)
```
##### Iterative testing process
The component performance model is evaluated using the **dimension scoring dataset produced during Stage 2**.
Operational workflow:
```text
1. apply dimension → component mapping tables
2. compute component_score values
3. examine distribution of component scores
4. compare results with qualitative judgement of responses
```
Example dataset structure:
```text
submission_id
component_id
D1
D2
D3
component_score
```
Evaluation questions:
- Do strong responses reliably receive `exceeds_expectations`?
- Does the majority of competent responses fall within `meets_expectations`?
- Are weaker responses clearly separated into lower performance categories?
- Do component scores correspond to holistic judgement of response quality?
Possible revisions include:
```text
adjust dimension thresholds
modify mapping table rows
introduce or revise boundary rules
```
During this process the **Layer 3 mapping rules (Section 6.3)** are typically revised repeatedly.
##### Exit condition
Layer 3 development is complete when:
- component scores behave consistently across the calibration sample
- performance categories correspond to qualitative judgement
- score distributions appear reasonable for the assignment context
At this point the following sections are stabilised:
```text
Rubric Template: 5.2 Layer 3 SBO Instances (Stabilised)
Rubric Template: 6.3 Layer 3 SBO Value Derivation (Stabilised)
```
### 7. Stage 4 — Submission Score Derivation (Layer 4)
Layer 4 derives the **overall submission score** from the set of component scores.
Layer 4 behaviour is defined by:
```text
Rubric Template: 5.1 Layer 4 SBO Instances
Rubric Template: 6.4 Layer 4 SBO Value Derivation
```
These sections define:
```text
submission SBO registry
component → submission mapping rules
```
Because the rubric applies to the **entire submission**, Layer 4 typically involves relatively simple aggregation rules.
#### Stage 4.1 Layer 4 SBO Iterative Development
##### Initial condition
The process begins once **component performance behaviour has stabilised**.
At this stage:
```text
Rubric Template: 5.1 Layer 4 SBO Instances (Draft)
Rubric Template: 6.4 Layer 4 SBO Value Derivation (Draft)
```
define the submission-level scoring structure.
Submission scores are derived from component scores using mapping rules of the form:
```text
component_score → submission_score
```
Possible strategies include:
```text
simple aggregation
weighted component aggregation
minimum threshold rules
```
##### Iterative testing process
Submission scoring behaviour is evaluated using the **component scoring dataset produced during Stage 3**.
Operational workflow:
```text
1. apply component → submission mapping rules
2. compute submission_score values
3. examine score distributions
```
Example dataset structure:
```text
submission_id
component_score_A
component_score_B
component_score_C
submission_score
```
Evaluation questions:
- Do submission scores align with overall judgement of submission quality?
- Do component-level differences meaningfully influence the final score?
- Are aggregation rules producing predictable outcomes?
Layer 4 typically requires **minimal iteration**, since most rubric tuning occurs at Layer 3.
##### Exit condition
Layer 4 development is complete when:
- submission scores behave consistently across the calibration dataset
- aggregation rules produce predictable outcomes
At this point the following sections are stabilised:
```text
Rubric Template: 5.1 Layer 4 SBO Instances (Stabilised)
Rubric Template: 6.4 Layer 4 SBO Value Derivation (Stabilised)
```
### 8. Stage 5 — Rubric Freeze
The rubric is considered **construction-complete** when all sections of the Rubric Template have been stabilised.
Frozen sections:
```text
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
```text
Rubric Design Document
```
Machine-readable rubric payload:
```text
RUBRIC_<ASSESSMENT_ID>_PROD_payload_v01
```
This payload becomes the **authoritative rubric specification** used by calibration and scoring pipelines.
### 9. Relationship to the Canonical Grading Dataset
Pipeline 1A produces the canonical grading dataset organised as:
```text
submission_id × component_id
```
Each row represents one student submission for one assignment component.
Pipeline 1B does **not modify this dataset**.
Instead, Pipeline 1B produces the rubric structures that will later be applied when evaluating these grading targets.
### 10. Architectural Principle
The layered rubric architecture separates analytic responsibilities across the scoring system.
```text
Assignment pipelines define what evidence exists.
Rubric construction defines what will be evaluated.
Calibration determines how evidence is interpreted.
Scoring applies the rubric to the grading population.
```
The layered ontology allows each level of evaluation to be stabilised empirically using real student responses before production scoring pipelines are executed.
