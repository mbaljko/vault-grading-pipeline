## Stage 0A (Excel/MCode) — Implementation Mapping to Specification  
### Rubric-Agnostic Canonicalisation of Grading Targets
This document maps the current Excel/MCode workflow specifically to **Stage 0A** of the grading pipeline.
Stage 0A is the rubric-agnostic phase that produces a canonical dataset of **grading targets**, defined as:
```
submission_id × component_id
```
This document shows:
- where each Stage 0A post-condition is satisfied
- which worksheets and artefacts implement it
- what clarifications or small adjustments are needed for full compliance
## 0. Excel Workbook Mental Model (Stage 0A Context)
Stage 0A is implemented as a single Excel workbook containing multiple worksheets produced from:
- LMS submission export (wide CSV → saved as `.xlsx`)
- grading upload worksheet (downloaded from LMS)
- Power Query / MCode transformations
Sampling worksheets exist but are **not part of Stage 0A**.
### Stable Worksheet Roles (Stage 0A)
Recommended canonical worksheet names:
- `raw_export`  
  LMS submissions in wide format
- `grade_upload_template`  
  Official roster and grade columns
- `validation`  
  Join diagnostics and `__join_status`
- `cleaned_entries`  
  Canonical Stage 0A dataset (grading targets)
## 1. Canonical Dataset Definition (Stage 0A)
For Stage 0A, the canonical dataset is:
```
cleaned_entries
```
Each row represents exactly one:
```
submission_id × component_id
```
This is called a **grading target**.
Rubric dimensions are intentionally NOT present at this stage.
## 2. Mapping to Stage 0A Required Post-Conditions
### 2.1 Canonical Unit Definition
#### Spec Requirement (Stage 0A)
Each row must represent exactly one:
```
submission_id × component_id
```
#### Excel/MCode Implementation
This requirement is now fully satisfied:
- Wide LMS exports are unpivoted
- `component_id` column is explicit
- Each row contains exactly one component response
#### Compliance Status
Fully satisfied.
#### Implementation Artefact
`cleaned_entries` worksheet:
- `submission_id`
- `component_id`
- `response_text`
- metadata columns
### 2.2 Primary Key Uniqueness
#### Spec Requirement
Each grading target must be uniquely identifiable by:
```
(submission_id, component_id)
```
#### Excel/MCode Implementation
- `submission_id` derived from grading worksheet Identifier
- `component_id` derived from unpivoted column names
#### Compliance Status
Satisfied, assuming no duplicate rows exist.
#### Recommended Validation
Add Power Query check for duplicates on:
```
submission_id + component_id
```
### 2.3 Dataset Completeness
#### Spec Requirement
Dataset must include full coverage of:
```
Eligible Submissions × Components
```
#### Excel/MCode Implementation
Completeness ensured through:
- LMS export containing all submissions
- roster join validation
- exclusion of `no_match` rows
#### Compliance Status
Satisfied.
#### Implementation Artefact
`validation` worksheet provides:
- join status diagnostics
- unmatched record visibility
### 2.4 Unique Identity Integrity
#### Spec Requirement
Each grading target must include stable identifiers:
- `submission_id`
- `component_id`
#### Excel/MCode Implementation
Both are now explicit structured columns in `cleaned_entries`.
#### Compliance Status
Fully satisfied.
### 2.5 Join Validation Integrity
#### Spec Requirement
Deterministic joins must produce:
```
__join_status
```
with values:
- matched
- no_match
#### Excel/MCode Implementation
Implemented in `validation` worksheet via MCode join logic.
#### Compliance Status
Fully satisfied.
#### Implementation Details
- Only `matched` records are retained in `cleaned_entries`
- Excluded records remain visible in `validation`
### 2.6 Cleaned Response Text Integrity
#### Spec Requirement
Each grading target must contain cleaned text:
- HTML removed
- encoding artefacts removed
- whitespace normalised
#### Excel/MCode Implementation
MCode cleaning pipeline performs:
- HTML stripping
- mojibake sanitisation
- whitespace normalisation
#### Compliance Status
Fully satisfied.
### 2.7 Dataset Scope Integrity
#### Spec Requirement
Dataset must include all eligible submissions and exclude dropped students.
#### Excel/MCode Implementation
Eligibility determined through:
- join with grading worksheet roster
- filtering out `no_match` rows
#### Compliance Status
Fully satisfied.
### 2.8 Structural Consistency
#### Spec Requirement
Dataset must have uniform schema:
- consistent columns
- consistent encoding
- no missing required fields
#### Excel/MCode Implementation
Enforced through:
- fixed Power Query transformations
- deterministic column ordering
#### Compliance Status
Satisfied.
### 2.9 Deterministic Reproducibility
#### Spec Requirement
Stage 0A must produce reproducible outputs.
#### Excel/MCode Implementation
Reproducibility ensured by:
- deterministic Power Query steps
- stable join logic
- consistent identifier generation
#### Compliance Status
Partially satisfied.
#### Remaining Gap
Explicit manifest recording is not yet implemented.
### 2.10 Required Output Format
#### Spec Requirement
Canonical dataset must be a flat tabular structure.
#### Excel/MCode Implementation
`cleaned_entries` is a flat table.
#### Compliance Status
Fully satisfied.
## 3. What Stage 0A Explicitly Does NOT Do
Stage 0A intentionally does NOT:
- introduce rubric dimensions
- create dimension identifiers
- perform rubric expansion
- perform calibration sampling
- apply scoring
These functions belong to Stage 0B and later stages.
## 4. Remaining Minimal Alignment Actions for Full Stage 0A Compliance
To fully satisfy Stage 0A specification:
1. Create a `stage0_manifest` worksheet recording:
   - input filenames
   - export timestamps
   - record counts
   - processing steps
2. Add duplicate-key validation:
   - ensure uniqueness of `(submission_id, component_id)`
3. Explicitly document `cleaned_entries` as:
   > The canonical Stage 0A dataset.

No further structural changes are required.
## 5. Summary
The current Excel/MCode workflow already satisfies nearly all Stage 0A requirements.
Specifically, it successfully guarantees:
- canonical grading targets
- stable identity integrity
- deterministic joins
- cleaned response text
- full submission scope coverage
- uniform dataset structure
The only remaining step for full compliance is the addition of an explicit reproducibility manifest.
Stage 0A is therefore structurally complete and ready to serve as the foundation for Stage 0B rubric expansion.
