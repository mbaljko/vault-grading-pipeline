### Assignment Rubric Specification Template (Ontology-Aligned)
### 0. Purpose
This document defines the **rubric specification for an assignment**.
The rubric specification establishes:
- the **component registry**
- the **dimension registry**
- the **indicator registry**
- the **indicator evidence status scale**
- the **dimension evidence scale**
- the **indicator → dimension mapping**
- the **dimension → component score mapping**
- the **component → submission score mapping**
The rubric specification must conform to the **AA/SBO ontology**.
Evidence is evaluated within the canonical Assessment Artefact:
```text
AA (Layers 1–3) = submission_id × component_id
AA (Layer 4)    = submission_id
```
### Part A — Rubric Development Process (Working Section)
This section supports **incremental rubric development**.  
Content here may evolve during rubric design and calibration.
Dimension design typically proceeds **one component at a time**.
### A1. Component registry
List all grading surfaces for the assignment.
These correspond to **Layer 3 SBOs**.

| component_id | component_label |
|---|---|
| SectionAResponse | |
| SectionBResponse | |
| SectionCResponse | |
Guidelines:
- each component corresponds to a **distinct student-authored section** or grading surface
- components must match the **canonical population structure**
### A2. Dimension discovery (per component)
Dimensions correspond to **Layer 2 SBOs**.
For each component, identify conceptual evaluation criteria.
Example structure:

| component_id | dimension_id | dimension_label | conceptual_scope |
|---|---|---|---|
| SectionAResponse | D1 | | |
| SectionAResponse | D2 | | |
| SectionAResponse | D3 | | |
Guidelines:
- dimensions represent **distinct evaluation criteria**
- dimensions should be **conceptually independent**
- each dimension must correspond to a **clear scoring claim**
### A3. Scoring claims
For each dimension define the **scoring claim**.
Template:
```text
Component: <component_id>
Dimension: <dimension_id>
Scoring claim
Evaluate whether—and how clearly—the response demonstrates [criterion].
```
Optional guidance:
```text
The response should indicate:
- ...
- ...
- ...
```
### A4. Indicator discovery
Indicators correspond to **Layer 1 SBOs**.
Indicators are **observable textual evidence checks**.

| indicator_id | component_id | associated_dimension | indicator_definition |
|---|---|---|---|
| I1 | SectionAResponse | D1 | |
| I2 | SectionAResponse | D1 | |
| I3 | SectionAResponse | D2 | |
Indicators must satisfy:
- observable in the response text
- minimal interpretive inference
- conceptually tied to the dimension
### A5. Indicator classification
Indicators may play different analytic roles.

| role | description |
|---|---|
| anchor_indicator | establishes presence of the dimension |
| strengthening_indicator | distinguishes stronger articulation |
| boundary_indicator | distinguishes sophisticated articulation |
| response_safeguard_indicator | ensures interpretability |
Example:

| indicator_id | role | notes |
|---|---|---|
| I1 | anchor_indicator | |
| I2 | strengthening_indicator | |
### A6. Evidence scale definition
#### Indicator evidence scale

| indicator_evidence_status |
|---|
| evidence |
| partial_evidence |
| little_to_no_evidence |
Hierarchy:
```text
evidence > partial_evidence > little_to_no_evidence
```
#### Dimension evidence scale

| dimension_evidence_level |
|---|
| Level 1 |
| Level 2 |
| Level 3 |
Hierarchy:
```text
Level 1 > Level 2 > Level 3
```
### Part B — Normative Rubric Specification
This section defines the **authoritative rubric logic** used in scoring.
### 1. Assignment identity
```text
assessment_id: <ASSESSMENT_ID>
rubric_version: <VERSION_TAG>
```
Example:
```text
assessment_id: PPP
rubric_version: PPP_v1_2026W
```
### 2. Component registry (Authoritative)

| component_id | component_label |
|---|---|
| SectionAResponse | |
| SectionBResponse | |
| SectionCResponse | |
Each component corresponds to a **Layer 3 SBO**.
### 3. Dimension registry

| component_id | dimension_id | dimension_label |
|---|---|---|
| SectionAResponse | D1 | |
| SectionAResponse | D2 | |
| SectionAResponse | D3 | |
Each dimension represents a **Layer 2 SBO**.
### 4. Dimension definitions
For each dimension:
```text
Component: <component_id>
Dimension: <dimension_id>
Scoring claim
Evaluate whether—and how clearly—the response demonstrates [criterion].
Interpretive guidance
The response should indicate:
- ...
- ...
```
### 5. Indicator registry
Indicators represent **Layer 1 SBOs**.
Indicators must rely solely on **textual evidence within the AA**.

| indicator_id | component_id | indicator_definition | assessment_guidance |
|---|---|---|---|
Example:

| indicator_id | component_id | indicator_definition | assessment_guidance |
|---|---|---|---|
| I1 | SectionAResponse | | |
| I2 | SectionAResponse | | |
### 6. Indicator evidence scale

| indicator_evidence_status | interpretation |
|---|---|
| evidence | indicator fully satisfied |
| partial_evidence | weak or incomplete articulation |
| little_to_no_evidence | indicator absent |
### 7. Indicator → Dimension Mapping
This section defines how **indicator evidence statuses determine dimension evidence levels**.
Placeholder structure:
```text
<Indicator → Dimension Mapping Table Placeholder>
```
Mapping rules must satisfy:
- deterministic evaluation
- monotonic evidence hierarchy
- explicit conditions
Logical interpretation:
```text
indicator conditions → dimension evidence level
```
Row semantics:
```text
indicator conditions within a row are combined using AND
rows evaluated top-to-bottom
first satisfied row determines the dimension level
```
Fallback rule:
```text
If no row condition is satisfied → Level 3
```
### 8. Dimension → Component Score Mapping
Defines how **dimension evidence levels determine component scores**.
Placeholder structure:
```text
<Dimension → Component Mapping Table Placeholder>
```
Typical inputs:
```text
dimension evidence levels
optional response indicators
```
Output:
```text
component_score
```
### 9. Component → Submission Score Mapping
Defines how **component scores determine the final submission score**.
Placeholder structure:
```text
<Component → Submission Mapping Table Placeholder>
```
Output:
```text
submission_score
```
### 10. Score labels

| score_label |
|---|
| exceeds_expectations |
| meets_expectations |
| approaching_expectations |
| below_expectations |
| not_demonstrated |
Interpretation of labels may include:
- level statement
- advancement statement
### 11. Hard boundary rules (optional)
Some transitions may require explicit constraints.
Example:
```text
Eligibility for Meets expectations requires
two dimensions at Level 2 or higher.
```
These rules constrain the scoring mapping.
### 12. Normative status
The components, dimensions, indicators, evidence scales, and mapping tables defined in this document constitute the **authoritative rubric specification for the assignment**.
All calibration and scoring artefacts must reference these definitions.
### Development workflow summary
Rubric development should proceed incrementally:
```text
1 identify components
2 discover dimensions per component
3 derive indicators
4 classify indicator roles
5 define evidence scales
6 construct mapping tables
7 finalize scoring rules
```
This process ensures that **mapping tables emerge from observed indicators and evaluation logic**, rather than being imposed prematurely.
