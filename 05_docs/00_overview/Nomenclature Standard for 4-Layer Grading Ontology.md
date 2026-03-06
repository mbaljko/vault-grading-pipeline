## Nomenclature Standard for 4-Layer Ontology
version: v.4
### Purpose
This document establishes the authoritative terminology used throughout the `vault-grading-pipeline`.

### Nomenclature

**Assessment Artefact (AA)**: the portion of a student's submission from which evidence is examined for scoring one or more SBOs.

**Score-Bearing Object (SBO)**: an analytic entity that receives a score derived from evidence drawn from a particular AA.

I am deliberatively not using the term **grading unit**, since it often can mean either "A grading unit is the specific entity that receives a score" or "the thing being graded"

### Conceptual Framework

|         | SBO          | name for the score given to the SBO | Way we refer to each SBO                                                                                                                       | Example SBO     | scale type for the SBO | Name of the scale for this SBO | Values of the SBO scale                                                                                            | Summary: AA specification per layer     |
| ------- | ------------ | ----------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- | --------------- | ---------------------- | ------------------------------ | ------------------------------------------------------------------------------------------------------------------ | --------------------------------------- |
| Layer 1 | `indicator`  | `indicator_score`                   | `[I\|P]_sid_cid_iid` where:<br>`sid` = submission identifier<br>`cid` = component identifier<br>`iid` = indicator identifier (\[I,P\]\[0-9\])  | `I_PPP_SecA_I1` | evidence               | `indicator_evidence_scale`     | `evidence`, `partial_evidence`, `little_to_no_evidence`                                                            | a component of the student's submission |
| Layer 2 | `dimension`  | `dimension_score`                   | `[D\|Q]_sid_cid_did` where:<br>`sid` = submission identifier<br>`cid` = component identifier<br>`did` = dimension identifier (\[D\|Q\]\[0-9\]) | `D_PPP_SecA_D1` | evidence               | `dimension_evidence_scale`     | `demonstrated`, `partially_demonstrated`, `little_to_no_demonstration`                                             | a component of the student's submission |
| Layer 3 | `component`  | `component_score`                   | `C_sid_cid` where:<br>`sid` = submission identifier<br>`cid` = component identifier (short string)                                             | `C_PPP_SecA`    | performance            | `component_performance_scale`  | `exceeds_expectations`, `meets_expectations`, `approaching_expectations`, `below_expectations`, `not_demonstrated` | a component of the student's submission |
| Layer 4 | `submission` | `submission_score`                  | `S_sid` where `sid` is the submission identifier (short string), determined by course's assessment architecture document                       | `S_PPP`         | performance            | `submission_performance_scale` | `exceeds_expectations`, `meets_expectations`, `approaching_expectations`, `below_expectations`, `not_demonstrated` | the student's entire submission         |


### Scoring Passes
There are 4 scoring passes to the grading pipeline:
- Layer 1: scoring of a set of multiple `indicator` 
- Layer 2: scoring of a set of multiple `dimension` (there are different 'kinds', explained below)
- Layer 3: scoring of a set of multiple `component`
- Layer 4: scoring of a set of multiple `submissions` (one `submission` for every student) 

### Layering
#### Layer 1
- AA: each `submission_id × component_id` from the canonical population
- SBOs: various `I_sid_cid_iid` (or may be denoted `P_sid_cid_iid`)
- Result: each student will have many, many `[I|P]_sid_cid_iid` scores.
##### Layer 1 scoring logic: 
- the score for each `[I|P]_sid_cid_iid` is determined by evidence found in the relevant AA
- some `[I|P]_sid_cid_iid` may be "dimension-tailored" (meaning they are attuned to a specific aspect of the component, which we will later call a `dimension`)
- some `[I|P]_sid_cid_iid` may be "holistic" (meaning that they look at the component as a whole, e.g., grammar, clarity, the presence of a concrete example)
- we don't need to formally signal their category, it will be implicitly encoded by the mapping relationship expressed in the next level
#### Layer 2
- AA: each `submission_id × component_id` from the canonical population
- SBOs: various `D_sid_cid_did`
- Result: each student will have many `D_sid_cid_did` scores, fewer than `[I|P]_sid_cid_iid` scores.
##### Layer 2 scoring logic:  
- in general, the score for each `[D|Q]_sid_cid_did` is determined from the pool of evidence represented in the set of `[I|P]_sid_cid_iid` scores
- specifically, the score for each `[D|Q]_sid_cid_did` is determined by a mapping table that expresses the combination of `indicator_score` values for certain `[I|P]_sid_cid_iid` that determine that particular `dimension_score`
	- "tailored" dimensions: most `[D|Q]_sid_cid_did` will combine two or more "dimension-tailored"  `[I|P]_sid_cid_iid`. 
		- In this case, the dimension will tend to be labelled `D_sid_cid_did` as opposed to `Q_sid_cid_did`,  The use of `D` vs `Q` is simply an information convention and will not be enforced.
		- In this case, the indicator will tend to be labelled `I_sid_cid_iid` as opposed to `P_sid_cid_iid`.  The use of `I` vs `P` is simply an information convention and will not be enforced.
	- "pan-component" dimensions: some `[D|Q]_sid_cid_did` are derived from a single "holistic" indicator `[I|P]_sid_cid_iid`
		- In this case, the dimension will tend to be labelled `Q_sid_cid_did` as opposed to `D_sid_cid_did`,  The use of `D` vs `Q` is simply an information convention and will not be enforced.
		- In this case, the indicator will tend to be labelled `P_sid_cid_iid` as opposed to `I_sid_cid_iid`.  The use of `I` vs `P` is simply an information convention and will not be enforced.
		- in the past I have referred to these as "cross-dimensional", even though they are dimensions themselves. The cross-dimensionality happens at the indicator level. So, strictly speaking, this is inconsistent nomenclature
		- It is better to refer to these dimensions as "pan-component dimensions" (rather than "cross-dimensional" dimensions).
#### Layer 3
- AA: each `submission_id × component_id` from the canonical population
- SBOs: various `C_sid_cid`, one for each component of the assignment
- Result: each student will have several `C_sid_cid` scores, fewer than `D_sid_cid_did` scores
##### Layer 3 scoring logic:
- in general, the score for each `C_sid_cid` is determined from the pool of evidence represented in the set of `D_sid_cid_did` scores
- specifically, the score for each `C_sid_cid` is determined by a mapping table that expresses the combination of `dimension_score` values that determine the `component_score`
- the "tailored" and "pan-component" dimensions combine to produce a derived `component_score`
#### Layer 4
- AA: each `submission_id` from the canonical population
- SBO: one, which is `S_sid`
- Result: each student will have one `S_sid` score
##### Layer 4 scoring logic:
- in general, the score for each `S_sid` is determined from the pool of evidence represented in the set of `C_sid_cid` scores
- specifically, the score for each `S_sid` is determined by a mapping table that expresses the combination of `component_score` values that determine the `submission_score` value

This nomenclature is normative. All future artefacts must conform to it.


### Scoring Flow Invariant

Across all layers of the grading pipeline, scores are derived according to the following invariant:

1. Evidence is examined within a defined Assessment Artefact (AA).
2. One or more Score-Bearing Objects (SBOs) associated with that AA are assigned scores.
3. Higher-layer SBO scores are derived only from lower-layer SBO scores through explicit mapping tables.

Formally:

AA → indicator SBO scores → dimension SBO scores → component SBO scores → submission SBO score

The AA defines the evidence boundary for a scoring pass, while SBOs define the analytic entities that receive scores derived from that evidence.

### Implementation Notes
- Implementation issue for Layer 3
	- Layer 3 depends on representation in the canonical population
	- moodle database export provisions for several discrete per-student elements in the export of the student submissions, this is what I am calling a component
	- if the moodle export produces one item per student, then this would result in one component.  If one wanted to break that into chunks, then there would need to be a segmentation stage
	- this stage relies on the ability to convert into "long format" 
	- Limitation:  no way to do pan-component scoring even in a multiple-component submission content with this architecture.  If this is desired, would need to introduce a placeholder component

### AA specification per layer

| **Layer** | **AA**                 |
| --------- | ---------------------- |
| 1         | submission × component |
| 2         | submission × component |
| 3         | submission × component |
| 4         | submission             |


======

## 1. Structural Ontology (Authoritative)
The grading ontology has three structural levels.
### 1.1 Full Submission
The `f_submission` is a single student’s full assignment submission.
Symbolically:
```
f_submission = submission_id
```
A submission typically contains one or more components.
This is a scoring unit.  The score is derived from a mapping from subordinate components. 
This is the canonical scoring unit at Layer 4.
### 1.2 Submission Component
The `c_submission` is a component with a structurally defined grading surface within a submission.
Examples:
- `SectionAResponse`
- `SectionBResponse`
- `SectionCResponse`
Symbolically:
```
component_id
```
The canonical unit is a `c_submission`:
```
c_submission = submission_id × component_id
```
A component may correspond to:
- a student-authored section, or
- a synthetic grading surface defined by the rubric (see Section 3).
This is a scoring unit.
### 1.3 Dimension
The `dimension` is a component with that has structurally defined grading surface:
- there can be cross-component `cc_dimension`, within  a `f_submission`
- there can be a single component `sc_dimension`, within a `c_submission`
A dimension is the smallest independently scorable rubric criterion applied to a component.
Symbolically:
```
dimension_id
```
Stage 0B canonical grading unit:
```
submission_id × component_id × dimension_id
```
This is a scoring unit.
All calibration and scoring must operate at this level.
### 1.4 Prior Practice: Correction
Previously, calibration materials used “dimension” to refer to what was structurally a component.
Under this standard:
- `SectionAResponse` is a **component**.
- Accountability framing, role boundary, and professional obligations are **dimensions** within that component.
Example:

| component_id     | dimension_id | dimension_label              |
|------------------|--------------|------------------------------|
| SectionAResponse | A1           | Accountability framing       |
| SectionAResponse | A2           | Role boundary and hand-off   |
| SectionAResponse | A3           | Professional obligations     |
These must appear in `rubric_definition`.
Calibration must operate on `A1`, `A2`, `A3` separately.
## 2. Cross-Component Evaluation (Synthetic Components)
Some grading criteria span multiple student-authored components (e.g., cohesion, integration, conceptual consistency).
These must be modelled as **synthetic components**, not as structure-breaking exceptions.
### 2.1 Definition
A synthetic component is:
- structurally equivalent to any other component
- not tied to a single student-authored section
- defined explicitly in `rubric_definition`
Example:

| component_id | dimension_id | dimension_label          |
|--------------|--------------|--------------------------|
| Global       | G1           | Cross-component cohesion |
Stage 0B expansion:
```
submission_id × Global × G1
```
This preserves structural invariants.
### 2.2 Evidence Surface for Synthetic Components
For synthetic components:
- The evidence surface may span multiple student-authored components.
- Evidence may be derived by:
  - concatenating relevant component texts, or
  - evaluating across structured references.
Structural keys remain unchanged.
Inter-component scope is epistemic, not structural.
## 3. Facets and Indicators (Interpretive Layer)
Facets and indicators are **interpretive constructs used during calibration and scoring**.  
They are **not structural entities** and do not appear in Stage 0B datasets.
They exist to support the interpretation and evaluation of a **dimension**.
### 3.1 Facet (Optional)
A facet is an optional analytic sub-criterion used to evaluate a single dimension.
Facets:
- represent conceptual aspects of the dimension being evaluated
- help organise the analytic structure of a rubric
- are primarily used during calibration
Facets do not appear in canonical grading datasets.
Example:
For dimension `A1 Accountability framing`, possible facets may include:
- locus named
- position taken
- distribution acknowledged
Facets are optional.  
A dimension may be evaluated without defining explicit facets.
### 3.2 Indicator (Optional)
An indicator is an observable presence check used to detect whether a conceptual element appears in the response.
Indicators:
- reference observable textual evidence
- function strictly as **presence checks**, not performance guarantees
- may support detection of facets or may apply directly to a dimension
Indicators do not appear in Stage 0B datasets.
### 3.3 Relationship Between Dimensions, Facets, and Indicators
Facets and indicators are optional interpretive layers.
Possible structures include:
Dimension evaluated directly via indicators:
```
dimension
    indicators
```
Dimension structured into facets and indicators:
```
dimension
    facets
        indicators
```
Dimension structured only into facets:
```
dimension
    facets
```
Indicators may be used:
- to detect the presence of facets, or
- to detect observable features of the dimension directly.
### 3.4 Boundary Rules
Boundary rules define how evidence from indicators and facets is translated into a score.
Boundary rules:
- specify score thresholds
- define knock-down conditions
- identify the hardest boundaries between score levels
Boundary rules operate at the **dimension level**.
## 4. Calibration Alignment
Calibration is conducted one **dimension** at a time.
Naming pattern:
```
CAL_<ASSESSMENT>_<DIMENSION_ID>_Step01_dimension_header_v01
```
Examples:
```
CAL_PPP_A1_Step01_dimension_header_v01
CAL_PPP_A2_Step01_dimension_header_v01
CAL_PPP_A3_Step01_dimension_header_v01
CAL_PPP_G1_Step01_dimension_header_v01
```
Calibration artefacts must reference `dimension_id`, not `component_id`.
## 5. Structural Invariants
1. Every component (including synthetic components) must define its dimensions in `rubric_definition`.
2. Every `(component_id, dimension_id)` pair must be unique.
3. Stage 0B must expand canonical targets into grading units deterministically.
4. Calibration must operate at the dimension level.
5. Production scoring must assign exactly one score per grading unit.
6. Structural keys must not change during calibration.
## 6. Summary of Terms

| Term                 | Structural | Appears in Stage 0B | Meaning |
|----------------------|------------|---------------------|--------|
| Submission           | Yes        | Yes                 | Entire student assignment |
| Component            | Yes        | Yes                 | Grading surface (authored or synthetic) |
| Dimension            | Yes        | Yes                 | Atomic rubric criterion |
| Synthetic Component  | Yes        | Yes                 | Cross-component grading surface |
| Facet                | No         | No                  | Optional analytic sub-criterion for a dimension |
| Indicator            | No         | No                  | Observable presence check used to detect evidence |
| Boundary rule        | No         | No                  | Score-level threshold logic |
## 7. Architectural Principle
Ontology precedes interpretation.
- Stage 0A defines canonical grading targets.
- Stage 0B defines atomic grading units.
- Calibration refines interpretation of dimensions.
- Scoring applies calibrated rules.
Cross-component evaluation must be represented structurally as synthetic components.
Structural invariants must remain stable across calibration cycles.
Interpretive constructs (facets, indicators, boundary rules) must not alter structural identifiers.
## 8. Normative Status
This document supersedes prior informal terminology.
All future artefacts in `vault-grading-pipeline` must adhere strictly to this nomenclature.
