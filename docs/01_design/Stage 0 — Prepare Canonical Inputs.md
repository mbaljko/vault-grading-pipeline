# Stage 0 — Prepare Canonical Inputs  
## Generalised Specification with Required Post-Conditions
This document defines the **necessary and sufficient post-conditions** for Stage 0 of the grading workflow.
Stage 0 is complete only when all required conditions below are satisfied.  
All downstream stages (calibration, scoring, review) assume these guarantees.
## 1. Purpose of Stage 0
Stage 0 transforms heterogeneous source data (LMS exports, grading sheets, database extracts) into a **single canonical dataset** suitable for automated and manual grading workflows.
Its goal is to eliminate ambiguity, inconsistency, and data integrity risks before calibration and scoring begin.
## 2. Inputs to Stage 0
Stage 0 typically operates on:
- Raw LMS submission exports (text responses)
- Grading worksheet exports (roster + gradebook structure)
- Institutional database exports (if applicable)
These inputs may differ across courses, LMS platforms, or assessment formats.
## 3. Required Post-Conditions (Normative Requirements)
Stage 0 is complete **only when ALL post-conditions below are met**.  
These conditions define the **mandatory structural, identity, and integrity guarantees** of the canonical dataset used for grading.
## 3.1 Canonical Dataset Format and Unit Definition
A single **canonical grading dataset** must exist as a rectangular tabular dataset (e.g., CSV, Parquet, or relational table).
### Atomic Grading Unit
Each row must represent exactly one unique grading unit defined as:
> `submission × component × dimension`

This is the smallest scorable unit in the workflow.
### Structural Requirements
The dataset must satisfy all of the following:
#### One Row per Grading Unit
Each row corresponds to:
- one submission  
- one component within that submission  
- one rubric dimension for that component  
No row may represent multiple grading units.
#### Primary Key Constraint
Each row must be uniquely identified by the composite key:
```
(submission_id, component_id, dimension_id)
```
This key must be:
- globally unique within the dataset
- stable across all downstream processing
Duplicate key combinations are prohibited.
#### Completeness Requirement
The dataset must contain **full Cartesian coverage** of all grading targets:
```
Eligible Submissions × Components × Dimensions
```
No missing dimension records are permitted.
#### Rectangular Table Format
The dataset must:
- have a fixed column schema
- contain one record per row
- avoid nested or hierarchical structures
Permissible formats include CSV, Parquet, or SQL tables.
## 3.2 Unique Identity Integrity
Every canonical row must include the following identifier fields:
- `submission_id` — uniquely identifies the submission
- `component_id` — identifies the assessment component
- `dimension_id` — identifies the rubric dimension
These identifiers must:
- remain stable across all downstream stages
- uniquely identify each grading unit
- support deterministic joins back to source datasets
Identifier formats must be consistent across all rows.
## 3.3 Join Completeness and Validation
All source datasets must be reconciled using deterministic joins.
A join validation process must be executed before the canonical dataset is finalised.
### Required Join Status Field
Each record must include a validation field:
```
__join_status
```
Permitted values:
- `matched` — complete and valid join
- `no_match` — unmatched or excluded record
### Mandatory Post-Conditions
The final canonical dataset must satisfy:
- All rows used for grading must have `__join_status = matched`
- All `no_match` records must be excluded from the canonical dataset
- A separate audit record of excluded submissions must be retained
## 3.4 Cleaned Response Text Requirement
Each canonical row must include:
```
cleaned_response_text
```
This field must satisfy all of the following:
- HTML markup removed
- encoding artefacts removed (e.g., mojibake)
- emoji normalised or removed
- whitespace normalised
Grading must operate exclusively on the cleaned text.
Raw source text may be retained separately for audit purposes.
## 3.5 Dataset Scope Integrity
The canonical dataset must include:
- all eligible submissions for grading
- no withdrawn, dropped, or excluded students
The total number of rows must equal:
```
(number of eligible submissions)
× (number of components per submission)
× (number of dimensions per component)
```
This equality must be explicitly verified and documented.
## 3.6 Structural Consistency Requirements
All canonical rows must conform to a uniform schema.
Specifically:
- identical column names and ordering
- consistent identifier formats
- consistent character encoding
No required field may be null or missing.
## 3.7 Deterministic Reproducibility
Stage 0 must produce a reproducible canonical dataset.
This requires generating a processing manifest that records:
- source file names and versions
- transformation steps applied
- processing timestamp
- record counts before and after processing
Re-running Stage 0 with identical inputs must produce identical outputs.
## Summary of Normative Guarantees
At completion of Stage 0, the canonical dataset must guarantee:
- atomic grading units with unique identifiers
- full coverage of all grading targets
- validated joins with documented exclusions
- cleaned and standardised response text
- structural uniformity
- reproducibility of data preparation
These guarantees form the required foundation for all subsequent grading stages.
## 4. Required Outputs of Stage 0
At completion, Stage 0 must produce:
### 4.1 Canonical Dataset
A structured table containing:
- identifiers
- cleaned response text
- optional metadata
This becomes the sole input for all subsequent stages.
### 4.2 Validation Report
A structured report documenting:
- join statistics
- excluded records
- row counts before and after cleaning
- any anomalies detected
### 4.3 Processing Manifest
A record of:
- input sources
- transformation steps applied
- processing timestamp
- operator or script version
## 5. Optional Metadata Fields
The canonical dataset may include additional metadata such as:
- response length
- submission timestamps
- section identifiers
- preprocessing flags
These fields must not affect identity integrity.
## 6. Explicit Non-Goals of Stage 0
Stage 0 does NOT:
- apply rubric scoring
- evaluate content quality
- perform calibration
- modify rubric definitions
Its sole function is data normalisation and validation.
## 7. Completion Criteria Checklist
Stage 0 is considered complete when:
- A canonical dataset exists with one row per grading unit.
- All identifiers are stable and unique.
- All joins have been validated.
- All unmatched records are excluded and logged.
- All response text has been cleaned.
- Dataset size matches expected grading scope.
- A validation report and manifest have been generated.
## 8. Summary
Stage 0 establishes the foundational data guarantees required for reliable grading.
Once complete, all downstream processes can assume:
- structural integrity
- identity correctness
- reproducible input state
Without these post-conditions, calibration and scoring cannot be conducted reliably.
