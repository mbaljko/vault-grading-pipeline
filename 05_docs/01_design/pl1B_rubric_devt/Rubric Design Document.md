## Rubric Design Document
### Purpose of this document
This document explains the **conceptual design of the assignment rubric**.  
It is intended for instructors, course designers, and calibration reviewers.
Its purpose is to:
- explain **what the rubric evaluates**
- document **how the analytic structure of the assignment was interpreted**
- describe **how indicators and dimensions were derived**
- explain the **interpretive logic behind the scoring rules**
This document is **human-readable and explanatory**.
It is **not used directly by the scoring pipeline**.
The deterministic rubric specification used by the grading system is defined separately in the **Rubric Payload Document**.
### Identifier layers used in the rubric system
The rubric system distinguishes between two layers of identifiers.
These layers correspond to different parts of the grading architecture: the **canonical dataset structure** and the **runtime scoring outputs** produced by the scoring pipeline.
#### Dataset identifiers
The canonical dataset produced by the preprocessing pipeline identifies each student artefact using the field:
```
participant_id
```
This identifier refers to **one participant’s completed assignment artefact** within the dataset.
The canonical structural unit used in the dataset is therefore:
```
participant_id × component_id
```
This unit represents one participant’s response to one assignment component.
Dataset identifiers are used by:
- canonical datasets
- calibration datasets
- rubric development workflows
- upstream preprocessing pipelines
#### Runtime scoring identifiers
During automated scoring, the grading pipeline emits results using a **standardised output schema**.
In this schema, the participant identifier is normalised to the field name:
```
submission_id
```
This standardisation allows scoring outputs from different assignments and pipelines to share a consistent column structure.
The scoring prompts therefore apply the following mapping:
```
participant_id → submission_id
```
In other words, the value originating from the dataset field participant_id is copied into the runtime output field submission_id.
#### Relationship between the two identifier layers
Conceptually, both identifiers refer to the same underlying entity:
```
a participant’s submitted assignment artefact
```
However, they appear in different contexts:

|**context**|**identifier used**|
|---|---|
|canonical datasets|participant_id|
|scoring outputs and grading prompts|submission_id|
This separation allows the dataset structure to remain stable while maintaining a consistent output schema for grading pipelines.
#### Ontological interpretation
Within the grading ontology, the **Assessment Artefact (AA)** corresponds to the participant’s assignment artefact.
Accordingly, the analytic units evaluated during scoring are:
```
AA (Layers 1–3) = participant_id × component_id
AA (Layer 4)    = participant_id
```
When results are emitted by the scoring pipeline, the identifier value associated with participant_id appears in the output column named submission_id.
### Relationship to the rubric payload document
Two artefacts define the rubric:

| document | purpose |
|---|---|
| Rubric Design Document (this document) | human explanation of the rubric |
| Rubric Payload Document | machine-readable scoring specification |
The **rubric payload document** contains only the structural information required by the scoring pipeline.
It defines:
- the component registry
- the dimension registry
- the indicator registry
- the evidence scales
- the mapping rules used to derive scores
The payload document serves as the **authoritative input for the scoring pipeline and LLM prompts**.
The present document explains **how those structures were designed and how they should be interpreted**.
### Ontological context
The rubric follows the grading ontology defined in the project documentation.
Evidence is evaluated within the **Assessment Artefact (AA)**:
```
AA (Layers 1–3) = participant_id × component_id
AA (Layer 4)    = participant_id
```
Scores are assigned to **Score-Bearing Objects (SBOs)** across four layers:
```
indicator SBOs
    ↓
dimension SBOs
    ↓
component SBO
    ↓
submission SBO
```
Indicators detect evidence in the response.  
Dimensions synthesise indicator evidence.  
Component scores summarise dimension evidence.  
The submission score aggregates component scores.
### Components of the assignment
The assignment contains several **components**.
A component corresponds to a distinct student-authored section or grading surface.
Examples:

| component_id | description |
|---|---|
| SectionAResponse | analysis of accountability framing |
| SectionBResponse | evaluation of governance mechanisms |
| SectionCResponse | discussion of residual uncertainty |
Each component is evaluated using its own set of rubric dimensions.
### Analytic sub-spaces
Before constructing the rubric, the analytic structure of each component is interpreted in terms of **analytic sub-spaces**.
An analytic sub-space represents a **conceptual task the component asks the student to perform**.
Analytic sub-spaces are derived directly from the **assignment instructions** and guide the discovery of indicators and dimensions during rubric development.
They are **not part of the scoring ontology** and do not appear in the rubric payload document.
Instead, they serve as a **design scaffold** for rubric construction.
Example structure:

| subspace_id | analytic focus | description | prompt anchor |
|---|---|---|---|
| A1 | accountability locus | how responsibility is located (individual vs distributed) | bullet 1 |
| A2 | role boundary | where the professional role stops or responsibility is handed off | bullet 2 |
| A3 | professional obligations | whether obligations exist in a non-licensure field | bullet 3 |
Analytic sub-spaces are used to guide **contrastive indicator discovery** during rubric development.
Indicators discovered within the same analytic sub-space often later cluster into **dimensions**.
### Dimensions
A **dimension** represents a conceptual evaluation criterion applied to a component.
Dimensions are designed to capture **distinct properties of the student's analysis** that can be evaluated from the response.
Examples of dimensions include:
- accountability framing  
- role boundary and responsibility hand-off  
- professional obligations  
Each dimension has a **scoring claim**.
A scoring claim specifies the conceptual judgement being evaluated.
Example structure:
```
Evaluate whether—and how clearly—the response identifies where accountability resides in the sociotechnical situation.
```
Dimensions should satisfy the following principles:
- conceptual independence  
- interpretability  
- observable evidence support  
Dimensions are instantiated in the scoring system as **Layer 2 Score-Bearing Objects (dimension SBOs)**.
### Indicators
Indicators are **observable evidence checks**.
They detect whether particular conceptual elements appear in the response.
Indicators are evaluated using the **indicator evidence scale**.
Indicators serve several roles:

| role | purpose |
|---|---|
| anchor indicators | establish the presence of the dimension |
| strengthening indicators | distinguish stronger articulation |
| boundary indicators | distinguish sophisticated reasoning |
| response safeguards | ensure the response is interpretable |
Indicators do not directly determine the final score.  
Instead they contribute evidence used to evaluate dimensions.
Indicators are instantiated in the scoring system as **Layer 1 Score-Bearing Objects (indicator SBOs)**.
### Evidence scales
Two evidence scales are used in the rubric.
#### Indicator evidence scale

| indicator_evidence_status |
|---|
| evidence |
| partial_evidence |
| little_to_no_evidence |
Hierarchy:
```
evidence > partial_evidence > little_to_no_evidence
```
This scale measures the **strength of observable textual evidence** for an indicator.
#### Dimension evidence scale

| dimension_evidence_level |
|---|
| demonstrated |
| partially_demonstrated |
| little_to_no_demonstration |
Hierarchy:
```
demonstrated > partially_demonstrated > little_to_no_demonstration
```
This scale measures the **strength of conceptual articulation for the dimension**.
### Indicator–dimension relationship
Indicators support the evaluation of dimensions.
Conceptually:
```
dimension
    indicators
```
The presence or absence of indicator evidence is used to determine the **dimension evidence level**.
Indicator evidence is combined using deterministic rules defined in the **rubric payload document**.
These rules are implemented as **mapping tables**.
### Dimension evaluation philosophy
The rubric follows an **anchor-plus-modifier logic**.
Anchor indicators establish that a dimension is present.
Additional indicators distinguish stronger or more sophisticated articulation.
Conceptually:
```
anchor indicator → establishes adequacy
strengthening indicators → distinguish sophistication
```
This structure allows the rubric to:
- reward strong articulation
- avoid over-penalising partial responses
- maintain interpretable scoring boundaries
### Component scoring
Component scores summarise the **combined evidence across dimensions**.
Dimensions are interpreted collectively.
Strong responses typically:
- articulate multiple dimensions clearly
- explain relationships between responsibilities and roles
- provide concrete reasoning or examples
The mapping from dimension evidence levels to component scores is defined in the **rubric payload document**.
### Submission scoring
The final submission score aggregates the component scores across the assignment.
Submission scoring therefore reflects the student's **overall professional positioning across the assignment**.
### Role of the rubric payload document
The **rubric payload document** is the deterministic specification used by the scoring pipeline.
It contains:
- component registry
- dimension registry
- indicator registry
- evidence scales
- indicator → dimension mapping tables
- dimension → component mapping tables
- component → submission mapping tables
The payload document contains **no narrative explanation**.
Its purpose is to function as a **structured scoring specification used by automated scoring prompts**.
### Development workflow
Rubric development typically follows an incremental process:
```
1 identify assignment components
2 interpret analytic sub-spaces in each component
3 discover indicators using contrastive analysis of calibration responses
4 derive dimensions supported by indicator evidence
5 define evidence scales
6 construct mapping tables across scoring layers
7 stabilise the rubric payload specification
```
The rubric payload document is generated once these elements have been stabilised.
### Normative status
The rubric payload document constitutes the **authoritative scoring specification** for the assignment.
This document serves as the **explanatory reference** that documents the conceptual design of the rubric.
