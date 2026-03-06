### Assignment Rubric Design Document
### Purpose of this document
This document explains the **conceptual design of the assignment rubric**.  
It is intended for instructors, course designers, and calibration reviewers.
Its purpose is to:
- explain **what the rubric evaluates**
- document **how the dimensions were derived**
- describe **how indicators support the evaluation of dimensions**
- explain the **interpretive logic behind the scoring rules**
This document is **human-readable and explanatory**.
It is **not used directly by the scoring pipeline**.
The deterministic rubric specification used by the grading system is defined separately in the **Rubric Payload Document**.
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
AA (Layers 1–3) = submission_id × component_id
AA (Layer 4)    = submission_id
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
### Dimensions
A **dimension** represents a conceptual evaluation criterion applied to a component.
Dimensions are designed to capture distinct aspects of the student's analysis.
Examples of dimensions include:
- accountability framing
- role boundary and hand-off
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
| Level 1 |
| Level 2 |
| Level 3 |
Hierarchy:
```
Level 1 > Level 2 > Level 3
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
Submission scoring therefore reflects the student's overall professional positioning across the assignment.
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
2 derive dimensions for each component
3 discover indicators that detect dimension evidence
4 classify indicator roles
5 define evidence scales
6 construct mapping tables
7 finalise scoring rules
```
The rubric payload document is generated once these elements have been stabilised.
### Normative status
The rubric payload document constitutes the **authoritative scoring specification** for the assignment.
This document serves as the **explanatory reference** that documents the conceptual design of the rubric.
