## Stage 0 — Prepare Canonical Inputs  
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
Stage 0 is complete **only when ALL post-conditions below are satisfied**.  
Each requirement below is an independent invariant that must hold before any calibration or scoring may begin.
These requirements define the structural, identity, and integrity guarantees of the canonical grading dataset.
### 3.1 Canonical Unit Definition
The canonical grading dataset must be organised so that:
> **Each row represents exactly one unique grading unit defined as:**
>
> `submission × component × dimension`.

This atomic unit is the smallest independently scorable element.
No row may represent multiple grading units.
#### Instantiation and Implementation Details
- Canonical dataset file name (recommended): `canonical_units.csv`
- Output directory (course vault): `06_grading/<ASSESSMENT>/03_runs/<YYYY-MM-DD>/`
- Flatten LMS export into long format (not wide rubric format).
- If LMS export is wide (one column per dimension), reshape into long form.
- Typical implementation: use `pandas.melt()` to convert wide rubric exports to long format.
- Assert that each `(submission_id, component_id, dimension_id)` tuple appears exactly once.
### 3.2 Primary Key Uniqueness
Each row must be uniquely identifiable by the composite key:
```
(submission_id, component_id, dimension_id)
```
Duplicate key combinations are prohibited.
#### Instantiation and Implementation Details
- Validation check in Python:
  ```python
  df.duplicated(subset=["submission_id", "component_id", "dimension_id"]).any()
  ```
  must return `False`.
- If duplicates exist:
  - Fail Stage 0 immediately.
  - Emit `duplicate_key_report.csv`.
- Optional materialised key:
  `grading_unit_id = f"{submission_id}::{component_id}::{dimension_id}"`.
### 3.3 Dataset Completeness
The canonical dataset must include full Cartesian coverage:
```
Eligible Submissions × Components × Dimensions
```
No missing grading units are permitted.
#### Instantiation and Implementation Details
- Compute expected count:
  ```python
  expected = n_submissions * n_components * n_dimensions
  ```
- Validate:
  ```python
  assert len(df) == expected
  ```
- If missing units are detected:
  - Emit `missing_units_report.csv`.
  - Halt Stage 0.
### 3.4 Unique Identity Integrity
Each canonical row must include:
- `submission_id`
- `component_id`
- `dimension_id`
Identifiers must be stable and deterministic.
#### Instantiation and Implementation Details
- `submission_id` should match LMS unique submission identifier.
- `component_id` should use stable short codes (e.g., `PPP`, `AP1`).
- `dimension_id` should use stable rubric identifiers (e.g., `D1`, `D2`).
- Do not use display labels as identifiers.
- All identifiers must be strings and must not contain null values.
### 3.5 Join Validation Integrity
All source datasets must be reconciled using deterministic joins.
Each row must include:
```
__join_status
```
Permitted values:
- `matched`
- `no_match`
#### Instantiation and Implementation Details
- Join exports using `submission_id` or LMS primary key.
- After merge:
  ```python
  df["__join_status"] = np.where(df["_merge"] == "both", "matched", "no_match")
  ```
- Exclude `no_match` rows from the canonical dataset.
- Persist audit file: `excluded_submissions.csv`.
### 3.6 Cleaned Response Text Integrity
Each canonical row must include:
```
cleaned_response_text
```
HTML and encoding artefacts must be removed.
#### Instantiation and Implementation Details
- Strip HTML using BeautifulSoup.
- Normalise encoding to UTF-8.
- Remove emoji or non-text glyphs if necessary.
- Standardise whitespace using regex.
- Persist both:
  - `raw_response_text`
  - `cleaned_response_text`
- All grading processes must use only `cleaned_response_text`.
### 3.7 Dataset Scope Integrity
The canonical dataset must include all eligible submissions and exclude dropped students.
The total row count must equal:
```
(number of eligible submissions)
× (number of components)
× (number of dimensions)
```
#### Instantiation and Implementation Details
- Eligibility determined from official grading worksheet export.
- Exclude withdrawn or dropped students prior to canonicalisation.
- Persist audit summary: `eligibility_summary.json`.
- Log counts for:
  - total submissions raw
  - total eligible submissions
  - final canonical row count.
### 3.8 Structural Consistency
The canonical dataset must have a uniform tabular schema.
All rows must contain:
- identical column names
- consistent identifier formats
- consistent character encoding
- no missing required fields.
#### Instantiation and Implementation Details
- Define explicit schema constant: `REQUIRED_COLUMNS`.
- Validate presence and dtype of each required column.
- Save schema snapshot as `canonical_schema.json`.
- Dataset must be stored in UTF-8 encoding.
### 3.9 Deterministic Reproducibility
Stage 0 must produce reproducible outputs.
#### Instantiation and Implementation Details
- Persist processing manifest: `stage0_manifest.json`.
- Manifest must include:
  - input filenames
  - file hashes
  - script version or commit hash
  - processing timestamp
  - record counts.
- Canonical dataset must be written in deterministic order sorted by:
  `submission_id`, `component_id`, `dimension_id`.
### 3.10 Required Output Format
The canonical dataset must be stored as a flat tabular dataset.
Permitted formats:
- `canonical_units.csv`
- `canonical_units.parquet`.
#### Instantiation and Implementation Details
- Preferred working format: CSV.
- For large datasets: Parquet.
- Files must be written:
  - in UTF-8 encoding
  - with explicit column ordering
  - without index columns.
### 3.11 Summary of Normative Guarantees
At completion of Stage 0, the canonical dataset guarantees:
- atomic grading units
- unique composite keys
- complete rubric coverage
- validated joins with documented exclusions
- cleaned and standardised response text
- structural uniformity
- deterministic reproducibility.
Downstream grading stages assume these conditions hold.
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
