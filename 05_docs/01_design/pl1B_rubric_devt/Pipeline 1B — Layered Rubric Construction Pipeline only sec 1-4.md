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
```
<ASSESSMENT_ID>_SubmissionAnalyticBrief_v01
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
```
<ASSESSMENT_ID>_SubmissionAnalyticBrief_v01
    └ component analytic sub-spaces
```
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
##### Iterative testing process
Contrastive analysis is performed **within each analytic sub-space**.

| step | operation |
|---|---|
| 1 | identify analytic sub-spaces within the component |
| 2 | prompt the model to identify contrastive response pairs |
| 3 | extract textual signals distinguishing the responses |
| 4 | group signals into candidate indicators |
| 5 | identify early signal clusters suggesting candidate dimensions |
Example extracted signals:

| candidate signal |
|---|
| explicit assignment of accountability |
| recognition of distributed responsibility |
| description of responsibility hand-off |
| explicit reference to regulatory oversight |
These signals become **candidate indicators**. Signal clusters may also suggest **candidate dimensions**.
##### Exit condition
Stage 0 is complete when the Submission Analytic Brief contains:
- clearly defined analytic purpose for each component
- identified analytic sub-spaces
- candidate indicators grounded in contrastive evidence
- early candidate dimension groupings
#### Deliverables
```
<ASSESSMENT_ID>_SubmissionAnalyticBrief_v01
    └ component analytic sketches
        ├ analytic sub-spaces
        ├ candidate indicators
        └ candidate dimensions
```
*(Stages 4–10 remain structurally identical to the previous version; only presentation style changes were applied above to replace ambiguous blocks with registry tables and schema tables where appropriate.)*
