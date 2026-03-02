## Nomenclature Standard — Grading Ontology and Calibration Alignment
### Purpose
This document establishes the authoritative terminology used throughout the `vault-grading-pipeline`.
Its purpose is to:
- eliminate ambiguity between **submission**, **component**, **dimension**, and **facet**,
- align Stage 0A, Stage 0B, calibration, and production scoring,
- define how cross-component grading criteria are represented structurally.
This nomenclature is normative. All future artefacts must conform to it.
## 1. Structural Ontology (Authoritative)
The grading ontology has three structural levels.
### 1.1 Submission
A single student’s full assignment submission.
Symbolically:
```
submission_id
```
A submission contains one or more components.
### 1.2 Component
A component is a structurally defined grading surface within a submission.
Examples:
- `SectionAResponse`
- `SectionBResponse`
- `SectionCResponse`
Symbolically:
```
component_id
```
Stage 0A canonical unit:
```
submission_id × component_id
```
A component may correspond to:
- a student-authored section, or
- a synthetic grading surface defined by the rubric (see Section 3).
### 1.3 Dimension (Atomic Grading Unit)
A dimension is the smallest independently scorable rubric criterion applied to a component.
Symbolically:
```
dimension_id
```
Stage 0B canonical grading unit:
```
submission_id × component_id × dimension_id
```
This is the atomic scoring unit.
All calibration and scoring must operate at this level.
### 1.4 Section A Correction (Option A Adopted)
Previously, calibration materials used “dimension” to refer to what was structurally a component.
Under this standard:
- `SectionAResponse` is a **component**.
- Accountability framing, role boundary, and professional obligations are **dimensions** within that component.
Example:

| component_id        | dimension_id | dimension_label                |
|---------------------|--------------|--------------------------------|
| SectionAResponse    | A1           | Accountability framing         |
| SectionAResponse    | A2           | Role boundary and hand-off     |
| SectionAResponse    | A3           | Professional obligations       |
These must appear in `rubric_definition`.
Calibration must operate on `A1`, `A2`, `A3` separately.
## 2. Cross-Component Evaluation (Synthetic Components)
Some grading criteria span multiple student-authored components (e.g., cohesion, integration, conceptual consistency).
These must be modelled as **synthetic components**, not as structure-breaking exceptions.
### 2.1 Definition
A synthetic component is:
- structurally equivalent to any other component,
- not tied to a single student-authored section,
- defined explicitly in `rubric_definition`.
Example:

| component_id | dimension_id | dimension_label              |
|--------------|--------------|------------------------------|
| Global       | G1           | Cross-component cohesion     |
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
- Structural keys remain unchanged.
Inter-component scope is epistemic, not structural.
## 3. Facets (Reserved Meaning)
The term **facet** is reserved exclusively for:
> Sub-criteria used to evaluate a single dimension.

Facets:
- do not appear in Stage 0B datasets,
- are not structural entities,
- are interpretive tools used during calibration.
Example:
For dimension `A1 Accountability framing`, possible facets may include:
- locus named,
- position taken,
- distribution acknowledged.
Facets must never be used to refer to dimensions.
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

| Term         | Structural | Appears in Stage 0B | Meaning |
|--------------|------------|---------------------|--------|
| Submission   | Yes        | Yes                 | Entire student assignment |
| Component    | Yes        | Yes                 | Grading surface (authored or synthetic) |
| Dimension    | Yes        | Yes                 | Atomic rubric criterion |
| Synthetic Component | Yes | Yes                 | Cross-component grading surface |
| Facet        | No         | No                  | Sub-test within a dimension |
| Indicator    | No         | No                  | Observable presence check |
| Boundary rule| No         | No                  | Score-level threshold logic |
## 7. Architectural Principle
Ontology precedes interpretation.
- Stage 0A defines canonical grading targets.
- Stage 0B defines atomic grading units.
- Calibration refines interpretation of dimensions.
- Scoring applies calibrated rules.
Cross-component evaluation must be represented structurally as synthetic components.
Structural invariants must remain stable across calibration cycles.
## 8. Normative Status
This document supersedes prior informal terminology.
All future artefacts in `vault-grading-pipeline` must adhere strictly to this nomenclature.
