## Pipeline 2 — Expand Canonical Grading Targets into Grading Units (Rubric-Dependent)
## Generalised Specification with Required Post-Conditions
This document defines the **necessary and sufficient post-conditions** for Pipeline 2 of the grading workflow.
Pipeline 2 transforms the rubric-agnostic canonical grading target dataset produced in Stage 0A into a **rubric-aware canonical grading unit dataset**.
Pipeline 2 is complete only when all required conditions below are satisfied.
All downstream stages — calibration, scoring, review, QA, and reporting — assume the guarantees established here.
## 1. Purpose of Pipeline 2
Pipeline 2 introduces rubric structure into the grading pipeline.
Its purpose is to convert each grading target:
```
submission × component
```
into the full set of scorable grading units:
```
submission × component × dimension
```
Pipeline 2 therefore establishes the **true atomic grading unit** required for reliable, dimension-level calibration and scoring.
## 2. Inputs to Pipeline 2
Pipeline 2 requires two authoritative inputs:
### 2.1 Canonical Grading Targets (from Stage 0A)
A dataset containing one row per:
```
submission_id × component_id
```
with cleaned response text.
### 2.2 Rubric Definition Dataset
A structured rubric specification defining:
- components
- dimensions per component
- stable dimension identifiers
- dimension ordering
Rubric definitions must be:
- authoritative
- version-controlled
- deterministic
## 3. Required Post-Conditions (Normative Requirements)
Pipeline 2 is complete **only when ALL post-conditions below are satisfied**.
These invariants define the structural, identity, and integrity guarantees of the canonical grading unit dataset.
### 3.1 Canonical Grading Unit Definition
The canonical grading dataset must be organised so that:
> **Each row represents exactly one unique grading unit defined as:**

```
submission_id × component_id × dimension_id
```
This is the smallest independently scorable element.
No row may represent multiple grading units.
### 3.2 Primary Key Uniqueness
Each grading unit must be uniquely identifiable by the composite key:
```
(submission_id, component_id, dimension_id)
```
Duplicate key combinations are strictly prohibited.
#### Implementation Requirements
- Duplicate detection must halt Pipeline 2.
- A materialised key must be constructible:
```
grading_unit_id = submission_id::component_id::dimension_id
```
This may be stored as a physical column or derived deterministically.
### 3.3 Complete Rubric Coverage
The dataset must contain full Cartesian coverage of:
```
Eligible Submissions × Components × Dimensions
```
No dimension records may be missing.
Every grading target must be expanded into all rubric dimensions defined for its component.
### 3.4 Rubric Alignment Integrity
Each grading unit must reference a valid rubric dimension.
Dimension identifiers must:
- match authoritative rubric definitions
- be stable across runs
- not depend on display labels
- be version-traceable
Rubric drift or ambiguity is not permitted.
### 3.5 Deterministic Rubric Expansion
Expansion from targets to units must be deterministic.
Given identical inputs:
- canonical targets
- rubric definitions
Pipeline 2 must produce identical grading unit datasets.
Expansion order must not affect output.
### 3.6 Text Association Integrity
Each grading unit must contain:
- the exact cleaned response text corresponding to its component
The text must be inherited directly from Stage 0A without modification.
Text duplication across dimensions is expected and correct.
### 3.7 Dataset Scope Integrity
The grading unit dataset must include:
- all eligible submissions
- all valid components
- all rubric dimensions
No excluded or ineligible submissions may appear.
### 3.8 Structural Consistency
All grading unit rows must share a uniform schema including:
- submission identifiers
- component identifiers
- dimension identifiers
- cleaned response text
- optional metadata
No missing required fields are permitted.
### 3.9 Deterministic Ordering
The dataset must be stored in deterministic sorted order:
```
submission_id → component_id → dimension_id
```
Sorting must be stable and reproducible.
### 3.10 Reproducibility and Manifest Recording
Pipeline 2 must produce a processing manifest recording:
- rubric version used
- input dataset identifiers
- expansion method
- row counts before and after expansion
- timestamp
- processing environment or script version
Re-running Pipeline 2 with identical inputs must produce identical outputs.
## 4. Required Outputs of Pipeline 2
Pipeline 2 must produce:
### 4.1 Canonical Grading Unit Dataset
A structured table containing:
- submission_id
- component_id
- dimension_id
- cleaned_response_text
- optional metadata
This dataset becomes the sole input for all downstream grading processes.
### 4.2 Rubric Coverage Validation Report
A structured record documenting:
- expected vs actual grading unit counts
- missing dimension checks
- duplicate key checks
- rubric alignment verification
### 4.3 Processing Manifest
A reproducibility record documenting:
- rubric version
- expansion timestamp
- input dataset references
- transformation steps applied
## 5. Optional Metadata Fields
The grading unit dataset may include additional metadata such as:
- word counts
- anonymised row identifiers
- sampling flags
- section identifiers
These fields must not affect identity integrity.
## 6. Explicit Non-Goals of Pipeline 2
Pipeline 2 does NOT:
- assign scores
- perform calibration
- evaluate response quality
- modify rubric definitions
Its sole function is rubric expansion and validation.
## 7. Completion Criteria Checklist
Pipeline 2 is considered complete when:
- A canonical dataset exists with one row per grading unit.
- All identifiers are stable and unique.
- All rubric dimensions are represented.
- No duplicates exist.
- Dataset size matches expected coverage.
- A rubric coverage report exists.
- A processing manifest has been generated.
## 8. Relationship to Downstream Stages
Pipeline 2 produces the canonical grading unit dataset required for:
- dimension-first calibration
- batch scoring workflows
- consistency review passes
- automated QA checks
All downstream processes assume Pipeline 2 guarantees hold.
## 9. Summary
Pipeline 2 introduces rubric structure into the grading pipeline by expanding rubric-agnostic grading targets into fully specified grading units.
Once complete, downstream workflows can assume:
- atomic grading units
- complete rubric coverage
- stable identity integrity
- deterministic reproducibility
Without Pipeline 2 guarantees, reliable dimension-level calibration and scoring cannot be conducted.
