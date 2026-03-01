# Stage 0 (Excel/MCode) — Implementation Mapping to Specification
This document maps the current Excel/MCode workflow to the Stage 0 specification, showing 
(a) where each post-condition is satisfied, 
(b) what worksheet(s) and artefacts implement it, and 
(c) any gaps or clarifications needed to make compliance explicit.
## 0. Excel Workbook Mental Model
Stage 0 is implemented as a single Excel workbook containing multiple worksheets produced from:
- LMS submission export (wide CSV opened in Excel, then saved as `.xlsx`)
- grading upload worksheet (downloaded from LMS; added as a separate worksheet)
- Power Query / MCode transformations producing validation and cleaned datasets
- a sampling worksheet for calibration selection
### Stable worksheet names:
- `raw database export` (imported LMS submissions; wide format)
- ~~`grade_upload_template`~~ (downloaded grading sheet; roster + grade columns)
	- as named by LMS, eg `Grades-2025_LE_EECS_W_3000__3_M`
- `validation` (join diagnostics and `__join_status`)
- `cleaned_entries` (cleaned text, word counts, exclusions applied)
- `sampled_entries` (calibration sampling flags and blanks for TA workflow)
The “canonical dataset” in the Excel implementation is the `cleaned_entries` worksheet.
# Stage 0 (Excel/MCode) — Implementation Mapping to Specification
This document maps the current Excel/MCode workflow to the Stage 0 specification, showing where each post-condition is satisfied, how it is implemented in the workbook, and what clarifications are needed for full compliance.
## 0. Excel Workbook Mental Model
Stage 0 is implemented as a single Excel workbook containing multiple worksheets produced from:
- LMS submission export (wide CSV opened in Excel, then saved as `.xlsx`)
- grading upload worksheet (downloaded from LMS)
- Power Query / MCode transformations
- sampling worksheet for calibration selection
### Stable Worksheet Roles
Recommended canonical worksheet names:
- `raw_export` — LMS submissions in wide format  
- `grade_upload_template` — official roster and grade columns  
- `validation` — join diagnostics and `__join_status`  
- `cleaned_entries` — cleaned text, word counts, exclusions applied  
- `sampled_entries` — calibration sampling flags  
The canonical dataset in the Excel implementation is the `cleaned_entries` worksheet.
## 1. Mapping to Required Post-Conditions
### 3.1 Canonical Unit Definition
#### Spec Requirement
Each row must represent exactly one:
`submission × component × dimension`
#### Excel/MCode Implementation
The workbook currently operates in wide format:
- One row per submission  
- One column per component  
- Dimensions are applied later during calibration/scoring  
#### Compliance Status
Currently satisfies a **component-level canonical unit**:
`submission × component`
Full compliance requires reshaping into long format.
#### Implementation Details
- `raw_export` contains component columns
- `cleaned_entries` mirrors this structure
- To achieve full compliance:
  - Use Power Query to unpivot component columns
  - Add explicit `component_id` and `dimension_id` columns
### 3.2 Primary Key Uniqueness
#### Spec Requirement
Each row must be uniquely identifiable by:
`(submission_id, component_id, dimension_id)`
#### Excel/MCode Implementation
- Unique anonymised IDs are created using:
`+++row_id=YYY+++`
- This allows deterministic tracing back to the student.
#### Compliance Status
Partially satisfied:
- `row_id` exists but is embedded in text rather than stored as a structured field.
#### Implementation Details
Recommended explicit fields in `cleaned_entries`:
- `submission_id`
- `row_id`
- `component_id`
- `dimension_id` (if long format adopted)
Validation can be implemented using Power Query grouping or Excel duplicate detection.
### 3.3 Dataset Completeness
#### Spec Requirement
Dataset must include full coverage of:
Eligible Submissions × Components × Dimensions
#### Excel/MCode Implementation
Completeness ensured through:
- LMS export containing all submissions
- grade sheet containing full roster
- join validation identifying dropped students
#### Compliance Status
Satisfied at the component level if all matched rows are retained.
#### Implementation Details
Recommended validation metrics in `validation` worksheet:
- Raw submission count
- Eligible submission count
- Component count
- Expected row count
### 3.4 Unique Identity Integrity
#### Spec Requirement
Each row must include stable identifiers:
- submission_id  
- component_id  
- dimension_id  
#### Excel/MCode Implementation
Identifiers currently exist implicitly:
- submission_id from LMS export
- component_id represented by column names
- row_id embedded in text prefix
#### Compliance Status
Partially satisfied; identifiers should be explicit.
#### Implementation Details
Add explicit identifier columns:
- `submission_id`
- `row_id`
- `component_id`
- `dimension_id` (if long format)
### 3.5 Join Validation Integrity
#### Spec Requirement
Deterministic joins must produce:
`__join_status` with values:
- matched  
- no_match  
#### Excel/MCode Implementation
- Implemented in `validation` worksheet
- MCode generates join status field
- Dropped students flagged as `no_match`
#### Compliance Status
Fully satisfied.
#### Implementation Details
- `cleaned_entries` must be filtered to include only `matched` rows.
- Excluded records should remain visible in `validation`.
### 3.6 Cleaned Response Text Integrity
#### Spec Requirement
Each row must include cleaned response text with:
- HTML removed  
- encoding artefacts removed  
- emoji removed  
- whitespace normalised  
#### Excel/MCode Implementation
MCode performs cleaning and generates:
- cleaned text columns
- word count columns
#### Compliance Status
Fully satisfied.
#### Implementation Details
`cleaned_entries` contains:
- raw text (optional)
- cleaned text (required)
- word count metadata
All grading uses cleaned text.
### 3.7 Dataset Scope Integrity
#### Spec Requirement
Dataset must include all eligible submissions and exclude dropped students.
#### Excel/MCode Implementation
Scope determined via:
- join with grading worksheet roster
- exclusion of `no_match` rows
#### Compliance Status
Fully satisfied.
#### Implementation Details
`validation` worksheet should include summary counts:
- matched rows
- excluded rows
- total eligible submissions
### 3.8 Structural Consistency
#### Spec Requirement
Dataset must have:
- uniform schema
- consistent encoding
- no missing required fields
#### Excel/MCode Implementation
Consistency enforced through:
- fixed worksheet structure
- Power Query transformations
- stable column ordering
#### Compliance Status
Operationally satisfied; explicit validation recommended.
#### Implementation Details
Add schema checklist section in `validation` worksheet verifying:
- required columns exist
- data types consistent
- no null values in key fields
### 3.9 Deterministic Reproducibility
#### Spec Requirement
Stage 0 must produce reproducible outputs and a processing manifest.
#### Excel/MCode Implementation
Reproducibility depends on:
- stable Power Query steps
- deterministic sampling based on word count ranking
#### Compliance Status
Partially satisfied; manifest not yet explicit.
#### Implementation Details
Add `stage0_manifest` worksheet recording:
- source filenames
- export timestamps
- Power Query names
- row counts
- sampling parameters
### 3.10 Required Output Format
#### Spec Requirement
Canonical dataset must be a flat tabular structure.
#### Excel/MCode Implementation
Canonical dataset is implemented as:
`cleaned_entries` worksheet.
#### Compliance Status
Fully satisfied.
#### Implementation Details
Optional export step:
- Export `cleaned_entries` to `canonical_units.csv` for portability.
### 3.11 Summary of Normative Guarantees
#### Spec Requirement
Stage 0 must guarantee:
- atomic grading units
- unique identifiers
- full coverage
- validated joins
- cleaned text
- structural consistency
- reproducibility
#### Excel/MCode Implementation
All guarantees are met except:
- explicit dimension-level canonicalisation
- explicit manifest documentation
These can be addressed without changing the core workflow.
## 2. Recommended Minimal Alignment Actions
To achieve full spec alignment while remaining in Excel:
1. Add explicit identifier columns to `cleaned_entries`.
2. Create a `stage0_manifest` worksheet.
3. Declare `cleaned_entries` as the canonical dataset.
4. Decide whether to retain component-level units or implement unpivoting to dimension-level units.
These steps provide spec compliance without requiring workflow migration.
