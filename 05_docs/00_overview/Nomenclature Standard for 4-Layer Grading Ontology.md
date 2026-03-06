## Nomenclature Standard for 4-Layer Ontology

version: v.4
### Purpose
This document establishes the authoritative terminology used throughout the `vault-grading-pipeline`.

There are several layers. 
What exists at each layer


|         | Name for the thing that receives a score (a score-bearing entity, grading targets) | name for the score | Way we refer to each  individual score-bearing entity        | Example         | Levels for the scoring are defined by this | scale values                                                                                                       | Applies to (grading unit, the row)      |
| ------- | ---------------------------------------------------------------------------------- | ------------------ | ------------------------------------------------------------ | --------------- | ------------------------------------------ | ------------------------------------------------------------------------------------------------------------------ | --------------------------------------- |
| Layer 1 | `indicator`                                                                        | `indicator_score`  | `I_sid_cid_iid` where `x` is the unique identifier (numeric) | `I_PPP_SecA_I1` | `indicator_evidence_scale`                 | `evidence`, `partial_evidence`, `little_to_no_evidence`                                                            | a component of the student's submission |
| Layer 2 | `dimension`                                                                        | `dimension_score`  | `D_sid_cid_did` where `x` is the identifier (numeric)        | `D_PPP_SecA_D1` | `dimension_evidence_scale`                 | `demonstrated`, `partially_demonstrated`, `little_to_no_demonstration`                                             | a component of the student's submission |
| Layer 3 | `component`                                                                        | `component_score`  | `C_sid_cid` where `id` is the identifier (short string) <br> | `C_PPP_SecA`    | `component_scoring_scale`                  | `exceeds_expectations`, `meets_expectations`, `approaching_expectations`, `below_expectations`, `not_demonstrated` | a component of the student's submission |
| Layer 4 | `submission`                                                                       | `submission_score` | `S_sid` where `sid` is the identifier (short string)         | `S_PPP`         | `submission_scoring_scale`                 | `exceeds_expectations`, `meets_expectations`, `approaching_expectations`, `below_expectations`, `not_demonstrated` | the student's entire submission         |


There are 4 layers to the grading pipeline:
- Layer 1: scoring of a set consisting of `indicator` (multiple)
- Layer 2: scoring of a set of `sc_dimension` (multiple for one `component`) 
- Layer 3: scoring of a set of `componenent` (multiple for one `submission`)
- Layer 3: scoring of a set of `submissions` (one `submission` for every student) 



## Layering

### Layer 1
All Layer 1 scores (one for each `I_sid_cid_iid`, applied to each layer 1 grading unit) are determined by evidence found in the student's submission (but looking at one component)
- some `I_sid_cid_iid` will be "dimension-tailored" (meaning they are attuned to a specific dimension of the component), whereas others will be more "holistic" (meaning that they look at the component as a whole, e.g., grammar, clarity, the presence of a concrete example)
- we don't need to formally signal their category, it will be determined by their relationship to the next level
### Layer 2
All Layer 2 scores (one for each `D_sid_cid_did`, applied to each layer 2 grading unit) are determined by mapping tables that stipulate the combination of indicators that determine the `dimension_score`
- "tailored" dimensions: most `D_sid_cid_did` will combine "dimension-tailored"  `I_sid_cid_iid` 
- "pan-component" dimensions: some `D_sid_cid_did` are "pass-through" dimensions because they will stand in a 1-to-1 mapping from a single "holistic" `I_sid_cid_iid`
	- in the past I have refered to these as "cross-dimensional", even though they are dimensions themselves. The cross-dimensionality happens at the indicator level. So, strictly speaking, this is inconsistent nomenclature

### Layer 3
All Layer 3 scores (one for each `C_sid_cid`, applied to each layer 3 grading unit) are determined by mapping tables that stipulate the combination of dimensions that determine the `component_score`
- the "tailored" and "pan-component" dimensions combine to produce a derived `component_score`

### Layer 4
All Layer 4 scores (one for each )


Its purpose is to:
- eliminate ambiguity between **submission**, **component**, **dimension**, **facet**, and **indicator**
- align Stage 0A, Stage 0B, calibration, and production scoring
- define how cross-component grading criteria are represented structurally

This nomenclature is normative. All future artefacts must conform to it.
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
