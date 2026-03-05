## Pipeline 1A — Prepare Canonical Grading Targets (Rubric-Agnostic)
## Generalised Specification with Required Post-Conditions
This document defines the **necessary and sufficient post-conditions** for Pipeline 1A of the grading workflow.
Pipeline 1A establishes a **rubric-agnostic canonical grading target dataset** that normalises and validates heterogeneous source data prior to any rubric-dependent processing.
All downstream Pipelines — including rubric instantiation (Pipeline 0B), calibration, scoring, and review — assume the guarantees established here.
## 1. Purpose of Pipeline 1A
Pipeline 1A transforms heterogeneous source data (LMS exports, grading sheets, database extracts) into a **single canonical grading target dataset** that is:
- identity-safe  
- structurally consistent  
- free of join ambiguity  
- cleaned and standardised  
- reproducible  
Its goal is to eliminate ambiguity, inconsistency, and data integrity risks before any rubric-dependent processing begins.
Pipeline 1A is explicitly **rubric-agnostic**. It does not depend on dimension definitions or rubric structure.
## 2. Inputs to Pipeline 1A
Pipeline 1A operates on:
- Raw LMS submission exports (text responses)
- Grading worksheet exports (roster + eligibility)
- Institutional database exports (if applicable)
These inputs may differ across:
- courses
- LMS platforms
- assessment formats
Pipeline 1A must normalise these into a single unified dataset.
## 3. Required Post-Conditions (Normative Requirements)
Pipeline 1A is complete **only when ALL post-conditions below are satisfied**.
These invariants define the structural, identity, and integrity guarantees of the canonical grading target dataset.
### 3.1 Canonical Unit Definition (Rubric-Agnostic)
The canonical dataset must be organised so that:
> **Each row represents exactly one unique grading target defined as:**
>
> `submission_id × component_id`

This unit corresponds to a single student’s submission for one assessment component.
This is the smallest rubric-independent grading target.
No row may represent multiple submissions or multiple components.
#### Instantiation and Implementation Details
- Dataset must be reshaped into long format.
- Each component must be explicitly represented as a row.
- Wide LMS exports must be unpivoted.
- Component identifiers must not depend on column headers alone.
### 3.2 Primary Key Uniqueness
Each row must be uniquely identifiable by the composite key:
```
(submission_id, component_id)
```
Duplicate key combinations are prohibited.
#### Instantiation and Implementation Details
- Uniqueness must be validated explicitly.
- Duplicate key detection must halt Pipeline 1A.
- A materialised key may optionally be created:
```
grading_target_id = submission_id::component_id
```
### 3.3 Dataset Completeness (Component Coverage)
The canonical dataset must include full coverage of:
```
Eligible Submissions × Components
```
No missing component records are permitted unless explicitly marked as missing.
#### Instantiation and Implementation Details
- Expected row count must be computed.
- Missing grading targets must be detected and reported.
- Coverage must be validated before proceeding.
### 3.4 Unique Identity Integrity
Each canonical row must include:
- `submission_id` — authoritative, stable identifier  
- `component_id` — stable component identifier  
Identifiers must be:
- deterministic  
- non-null  
- stable across refreshes  
- independent of row ordering  
Display labels or column headers must not serve as identifiers.
### 3.5 Join Validation Integrity
All source datasets must be reconciled through deterministic joins.
Join validation must produce:
- eligibility filtering  
- exclusion tracking  
- join diagnostics  
#### Instantiation and Implementation Details
- Only eligible submissions may enter the canonical dataset.
- Excluded submissions must be recorded in an audit log.
- Join status does not need to persist per row if fully enforced upstream, but must be auditable.
### 3.6 Cleaned Text Integrity
Each canonical row must include cleaned text:
```
cleaned_response_text
```
Cleaning must ensure:
- HTML markup removed  
- encoding artefacts removed  
- whitespace normalised  
- text stored in UTF-8  
Raw text may optionally be retained separately.
All downstream grading processes must operate only on cleaned text.
### 3.7 Dataset Scope Integrity
The canonical dataset must include:
- all eligible submissions  
- no dropped or withdrawn students  
Row counts must match:
```
Eligible submissions × Components
```
Validation must confirm this explicitly.
### 3.8 Structural Consistency
The canonical dataset must have a uniform tabular schema:
- identical column names  
- consistent identifier formats  
- consistent data types  
- no missing required fields  
A schema definition must be declared and validated.
### 3.9 Deterministic Reproducibility
Pipeline 1A must produce reproducible outputs.
Re-running Pipeline 1A with identical inputs must produce identical results.
#### Instantiation and Implementation Details
- Dataset must be sorted deterministically by:
  - `submission_id`
  - `component_id`
- A processing manifest must record:
  - input sources
  - processing timestamp
  - row counts
  - transformation steps
### 3.10 Required Output Format
The canonical dataset must be stored as a flat tabular dataset.
Permitted formats include:
- CSV  
- Parquet  
- workbook table (for Excel-based workflows)
Data must be UTF-8 encoded and column ordering explicit.
## 4. Required Outputs of Pipeline 1A
Pipeline 1A must produce the following outputs.
### 4.1 Canonical Grading Target Dataset
A structured dataset containing one row per canonical grading target:
```
submission_id × component_id
```
Required fields:
- `submission_id`
- `component_id`
- `cleaned_response_text`
Optional metadata fields may also be included.
This dataset becomes the **sole input dataset for rubric-dependent pipelines**, including:
- rubric instantiation
- calibration
- scoring
### 4.2 Join Validation Audit
A structured audit record documenting:
- excluded submissions
- join mismatches
- eligibility filtering outcomes
- join diagnostics
This audit must be sufficient to reconstruct join decisions made during Pipeline 1A.
### 4.3 Processing Manifest
A manifest recording:
- input files
- processing timestamp
- processing steps executed
- record counts before and after transformation
- validation checks performed
This manifest ensures the pipeline is **deterministically reproducible**.
### 4.4 Assignment Payload Specification
Pipeline 1A must also produce the **assignment payload specification** describing the canonical structure of assignment components.
Deliverable:
```
PPP_AssignmentPayloadSpec_v01
```
This specification defines:
- the set of valid `component_id` values
- the canonical payload schema used in downstream pipelines
- the mapping between assessment components and canonical dataset fields
This specification becomes the authoritative reference for all rubric construction pipelines.
### 4.5 Component Payload Contracts
From the assignment payload specification, Pipeline 1A must generate **component-level payload contracts**.
Each contract defines how responses for a specific component are packaged for calibration and scoring.
Deliverables (one per component):
```
PPP_<COMPONENT_ID>_CalibrationPayloadFormat_v01
```
Examples:
```
PPP_SectionAResponse_CalibrationPayloadFormat_v01
PPP_SectionBResponse_CalibrationPayloadFormat_v01
PPP_SectionCResponse_CalibrationPayloadFormat_v01
```
Each payload contract defines:
- the canonical scoring unit
- identifier fields (`submission_id`, `component_id`)
- the response evidence field (e.g., `cleaned_response_text`)
- any additional metadata included in the payload
These payload contracts serve as **inputs to the rubric construction pipeline**.
## 5. Optional Metadata Fields
The canonical dataset may include:
- response word counts
- submission timestamps
- anonymised row identifiers
- preprocessing flags
These fields must not affect identity integrity.
## 6. Explicit Non-Goals of Pipeline 1A
Pipeline 1A does NOT:
- reference rubric definitions
- include dimension identifiers
- perform rubric expansion
- apply scoring or calibration
Its sole function is **data normalisation, validation, and assignment payload specification**.
## 7. Completion Criteria Checklist
Pipeline 1A is complete when:
- A canonical dataset exists with one row per `submission × component`.
- All identifiers are stable and unique.
- All joins have been validated.
- All excluded records are documented.
- All response text has been cleaned.
- Dataset size matches expected coverage.
- A processing manifest exists.
- `PPP_AssignmentPayloadSpec_v01` has been generated.
- `PPP_<COMPONENT_ID>_CalibrationPayloadFormat_v01` files exist for every component.
## 8. Relationship to Pipeline 0B
Pipeline 1A produces:
- a rubric-agnostic canonical grading dataset
- assignment payload specifications
- component payload contracts
Pipeline 0B subsequently expands the canonical dataset using rubric definitions to create:
```
submission_id × component_id × dimension_id
```
which becomes the true grading unit.
## 9. Summary
Pipeline 1A establishes the foundational data guarantees required for reliable grading workflows.
Once complete, all downstream processes can assume:
- identity correctness  
- structural integrity  
- clean and validated grading targets  
- deterministic reproducibility  
- well-defined assignment payload contracts  
without requiring knowledge of rubric structure.
