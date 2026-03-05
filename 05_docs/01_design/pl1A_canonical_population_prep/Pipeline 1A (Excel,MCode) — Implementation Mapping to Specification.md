## Pipeline 1A (Excel/MCode) — Implementation Mapping to Specification  
### Rubric-Agnostic Canonicalisation of Grading Targets
This document maps the current Excel/MCode workflow specifically to **Pipeline 1A** of the grading architecture.
Pipeline 1A is the **rubric-agnostic phase** that produces a canonical dataset of **grading targets**, defined as:
```
submission_id × component_id
```
This document shows:
- where each Pipeline 1A post-condition is satisfied
- which worksheets and artefacts implement it
- which Power Query / MCode scripts implement key transformations
- what clarifications or small adjustments are needed for full compliance
Pipeline 1A establishes the **canonical evidence layer** used by downstream processes.
Subsequent pipelines operate as follows:
- **Pipeline 1B — Rubric Construction**  
  Defines dimensions, indicators, and boundary rules.
- **Pipeline PL3 — Production Scoring**  
  Evaluates canonical responses against the rubric.
Pipeline 1A itself remains **fully rubric-independent**.
## 0. Excel Workbook Mental Model (Pipeline 1A Context)
Pipeline 1A is implemented as a single Excel workbook containing multiple worksheets produced from:
- LMS submission export (wide CSV → saved as `.xlsx`)
- grading upload worksheet (downloaded from LMS)
- Power Query / MCode transformations
Sampling worksheets may exist but are **not part of Pipeline 1A**.
### Stable Worksheet Roles (Pipeline 1A)
Recommended canonical worksheet names:
- `raw_export`  
  LMS submissions in wide format (input)
- `grade_upload_template`  
  Official roster and grade columns (input)
- `validation`  
  Join diagnostics and `__join_status` (derived)
- `cleaned_entries`  
  Canonical Pipeline 1A dataset (grading targets) (derived)
### Power Query / MCode Script Roles (Pipeline 1A)
Pipeline 1A depends on two named Power Query scripts embedded in the workbook:
- `01_validation`  
  Implements join validation, eligibility filtering logic, and diagnostics feeding the `validation` worksheet.
- `02_cleaning`  
  Implements response-text cleaning and normalisation feeding the `cleaned_entries` worksheet.
These script names are normative references in this document.
## 1. Canonical Dataset Definition (Pipeline 1A)
For Pipeline 1A, the canonical dataset is:
```
cleaned_entries
```
Each row represents exactly one:
```
submission_id × component_id
```
This unit is called a **grading target**.
Rubric dimensions are intentionally **not present** at this stage.
Pipeline 1A produces the **evidence surface** for grading:
```
submission_id × component_id
```
Later pipelines create the **evaluation surface** by combining canonical evidence with rubric definitions:
```
submission_id × component_id × dimension_id
```
That expansion occurs only during **production scoring (Pipeline PL3)**.
## 2. Mapping to Pipeline 1A Required Post-Conditions
### 2.1 Canonical Unit Definition
#### Spec Requirement (Pipeline 1A)
Each row must represent exactly one:
```
submission_id × component_id
```
#### Excel/MCode Implementation
This requirement is fully satisfied:
- Wide LMS exports are unpivoted.
- `component_id` is made explicit.
- Each row contains exactly one component response.
Primary implementing script:
- `02_cleaning`
#### Compliance Status
Fully satisfied.
#### Implementation Artefact
`cleaned_entries` worksheet contains:
- `submission_id`
- `component_id`
- `response_text`
- optional metadata columns
### 2.2 Primary Key Uniqueness
#### Spec Requirement
Each grading target must be uniquely identifiable by:
```
(submission_id, component_id)
```
#### Excel/MCode Implementation
- `submission_id` derived from grading worksheet Identifier
- `component_id` derived from unpivoted component field
Primary implementing script(s):
- `01_validation` (join/eligibility gate that affects which rows exist)
- `02_cleaning` (final emission into `cleaned_entries`)
#### Compliance Status
Satisfied, assuming no duplicates exist.
#### Required Check (to implement or confirm)
Add or confirm a duplicate-key validation step that detects duplicates on:
```
submission_id + component_id
```
If duplicates exist, Pipeline 1A must halt.
### 2.3 Dataset Completeness (Component Coverage)
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
Primary implementing script:
- `01_validation`
#### Compliance Status
Satisfied, contingent on explicit expected-row-count validation.
#### Required Check (to implement or confirm)
Compute and compare:
- expected row count = eligible submissions × number of components
- actual row count in `cleaned_entries`
### 2.4 Unique Identity Integrity
#### Spec Requirement
Each canonical row must include stable identifiers:
- `submission_id`
- `component_id`
#### Excel/MCode Implementation
Both identifiers exist as explicit structured columns in `cleaned_entries`.
Primary implementing script(s):
- `01_validation` (stabilises roster identifiers / join key behaviour)
- `02_cleaning` (preserves them into the canonical output)
#### Compliance Status
Fully satisfied.
### 2.5 Join Validation Integrity
#### Spec Requirement
Deterministic joins must produce:
```
__join_status
```
with values:
- `matched`
- `no_match`
#### Excel/MCode Implementation
Implemented in `validation` worksheet via MCode join logic.
Primary implementing script:
- `01_validation`
#### Compliance Status
Fully satisfied.
#### Implementation Details
- Only `matched` records are retained in `cleaned_entries`.
- Excluded records remain visible in `validation`.
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
Primary implementing script:
- `02_cleaning`
#### Compliance Status
Fully satisfied.
### 2.7 Dataset Scope Integrity
#### Spec Requirement
Dataset must include all eligible submissions and exclude dropped students.
#### Excel/MCode Implementation
Eligibility determined through:
- join with grading worksheet roster
- filtering out `no_match` rows
Primary implementing script:
- `01_validation`
#### Compliance Status
Fully satisfied.
### 2.8 Structural Consistency
#### Spec Requirement
Dataset must have uniform schema:
- consistent column names
- consistent identifier formats
- consistent data types
- no missing required fields
#### Excel/MCode Implementation
Enforced through:
- fixed Power Query transformations
- deterministic column ordering
Primary implementing script(s):
- `02_cleaning` (output schema)
- `01_validation` (ensures eligible population integrity)
#### Compliance Status
Satisfied.
### 2.9 Deterministic Reproducibility
#### Spec Requirement
Pipeline 1A must produce reproducible outputs.
#### Excel/MCode Implementation
Reproducibility ensured by:
- deterministic Power Query steps
- stable join logic
- consistent identifier generation
Primary implementing script(s):
- `01_validation`
- `02_cleaning`
#### Compliance Status
Partially satisfied.
#### Remaining Gap
An explicit processing manifest is not yet implemented.
### 2.10 Required Output Format
#### Spec Requirement
Canonical dataset must be a flat tabular structure.
#### Excel/MCode Implementation
`cleaned_entries` is implemented as a flat Excel table.
Primary implementing script:
- `02_cleaning`
#### Compliance Status
Fully satisfied.
## 3. What Pipeline 1A Explicitly Does NOT Do
Pipeline 1A intentionally does **not**:
- define rubric dimensions
- create dimension identifiers
- evaluate indicators
- perform rubric expansion
- perform calibration sampling
- apply scoring logic
These functions belong to downstream pipelines:
- **Pipeline 1B — Rubric Construction**
- **Pipeline PL3 — Production Scoring**
Dimension expansion occurs only when the rubric specification exists and is applied during production scoring.

# TO DO
## 4. Remaining Minimal Alignment Actions for Full Pipeline 1A Compliance
To fully satisfy the Pipeline 1A specification:
1. Create a `stage1A_manifest` worksheet recording:
   - input filenames
   - export timestamps
   - record counts
   - processing steps
2. Add or confirm duplicate-key validation ensuring uniqueness of:
```
(submission_id, component_id)
```
3. Add or confirm completeness validation:
   - compute expected row counts
   - compare to `cleaned_entries` row count
   - report missing grading targets explicitly
4. Explicitly document `cleaned_entries` as:
> The canonical Pipeline 1A dataset representing grading targets.

## 5. Next Check (Planned)
The next step is to audit the actual MCode in:
- `01_validation`
- `02_cleaning`
against the post-conditions above, focusing on:
- duplicate-key detection
- expected-row-count completeness validation
- manifest production hooks (even if manual)
## Pipeline 1A Compliance Summary — Excel/MCode Implementation
The table below summarises the **compliance status of each Pipeline 1A post-condition**, the **primary implementing artefacts**, and any **remaining alignment work**.

| Section | Requirement | Primary Implementation | Compliance Status | Remaining Actions |
|--------|-------------|------------------------|------------------|------------------|
| 2.1 | Canonical unit definition (`submission_id × component_id`) | `02_cleaning` MCode → `cleaned_entries` worksheet | Fully satisfied | None |
| 2.2 | Primary key uniqueness | `01_validation` + `02_cleaning` | Satisfied (assumed) | Add explicit duplicate-key validation on `(submission_id, component_id)` |
| 2.3 | Dataset completeness (`Eligible Submissions × Components`) | `01_validation` → `validation` worksheet | Satisfied (implicit) | Add explicit expected-row-count check |
| 2.4 | Unique identity integrity | `01_validation` (roster join) + `02_cleaning` | Fully satisfied | None |
| 2.5 | Join validation integrity | `01_validation` → `validation` worksheet | Fully satisfied | None |
| 2.6 | Cleaned response text integrity | `02_cleaning` | Fully satisfied | None |
| 2.7 | Dataset scope integrity (exclude dropped / unmatched) | `01_validation` filtering | Fully satisfied | None |
| 2.8 | Structural consistency (schema stability) | `02_cleaning` output schema | Satisfied | None |
| 2.9 | Deterministic reproducibility | `01_validation` + `02_cleaning` deterministic steps | Partially satisfied | Add `stage1A_manifest` worksheet |
| 2.10 | Required output format (flat canonical dataset) | `02_cleaning` → `cleaned_entries` table | Fully satisfied | None |
## Overall Pipeline 1A Compliance Status

| Category | Status |
|--------|--------|
| Structural correctness | ✔ Complete |
| Identity integrity | ✔ Complete |
| Join validation | ✔ Complete |
| Canonical dataset construction | ✔ Complete |
| Text cleaning pipeline | ✔ Complete |
| Reproducibility documentation | ⚠ Minor gap |
| Completeness validation | ⚠ Minor gap |
## Remaining Alignment Work (Minimal)
To reach **full Pipeline 1A compliance**, implement:
1. **Duplicate-key validation**  
   Check for duplicates on:
   ```
   submission_id + component_id
   ```
2. **Dataset completeness validation**  
   Verify:
   ```
   Eligible submissions × Components
   ```
3. **Reproducibility manifest**  
   Add worksheet:
   ```
   stage1A_manifest
   ```
   recording:
   - input files
   - export timestamps
   - row counts
   - pipeline version
## Implementation Risk Assessment

| Risk Area | Status |
|-----------|--------|
| Data identity errors | Low |
| Join mismatch visibility | Low |
| Dataset completeness drift | Medium (until explicit check added) |
| Reproducibility traceability | Medium (until manifest added) |
Once the **manifest and completeness checks** are implemented, the Pipeline 1A implementation will be **fully aligned with the architectural specification**.
