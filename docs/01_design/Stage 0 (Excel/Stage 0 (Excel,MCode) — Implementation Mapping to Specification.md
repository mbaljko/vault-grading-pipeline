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

Stable worksheet names:
- `raw database export` (imported LMS submissions; wide format)
- ~~`grade_upload_template`~~ (downloaded grading sheet; roster + grade columns)
	- as 
- `validation` (join diagnostics and `__join_status`)
- `cleaned_entries` (cleaned text, word counts, exclusions applied)
- `sampled_entries` (calibration sampling flags and blanks for TA workflow)
The “canonical dataset” in the Excel implementation is the `cleaned_entries` worksheet.
## 1. Mapping to Required Post-Conditions
### 3.1 Canonical Unit Definition
Spec requirement:
- one row per `submission × component × dimension`
Excel/MCode implementation:
- Current workbook organisation is *component-wide* (one column per component), and does not yet represent an explicit dimension axis in the table.
- The Excel implementation therefore has two possible compliance modes:
Mode A (component-level canonicalisation; dimension applied downstream):
- Canonical unit becomes `submission × component`
- Dimension is applied during calibration/scoring as a process layer, not a data axis
Mode B (fully spec-compliant canonicalisation; dimension included in the table):
- Transform the wide component columns into long format rows, adding `dimension_id`
Post-condition status:
- Currently satisfied only if Stage 0 is reinterpreted as producing a canonical dataset at `submission × component` granularity (Mode A).
- To satisfy the spec literally (Mode B), you need an additional reshaping step in Excel/MCode that yields one row per dimension.
Instantiation and Implementation Details (Excel):
- `raw_export` contains one row per submission with X component columns.
- `cleaned_entries` currently contains one row per submission with cleaned component columns.
- To reach Mode B in Excel:
  - Use Power Query to unpivot component columns into `component_id` rows
  - If dimensions are represented in separate columns, also unpivot dimensions into `dimension_id`
  - The resulting worksheet becomes the canonical dataset.
### 3.2 Primary Key Uniqueness
Spec requirement:
- unique composite key `(submission_id, component_id, dimension_id)`
Excel/MCode implementation:
- You prepend each student component with `+++row_id=YYY+++` where `YYY` is a per-row anonymised ID.
- This provides a stable per-submission identifier (`row_id`) and traceability back to the student via a separate mapping held in the workbook.
- However, `row_id` is not yet expressed as an explicit structured key field in the dataset.
Post-condition status:
- Partially satisfied via `row_id` convention, but should be made explicit.
Instantiation and Implementation Details (Excel):
- Add explicit columns in `cleaned_entries`:
  - `submission_id` (LMS or gradebook identifier)
  - `row_id` (your anonymised ID)
- If adopting Mode B (3.1), add:
  - `component_id`
  - `dimension_id`
- Add a validation formula or PQ check that no duplicates exist for the composite key:
  - For Mode A: uniqueness of `(row_id, component_id)`
  - For Mode B: uniqueness of `(row_id, component_id, dimension_id)`
### 3.3 Dataset Completeness
Spec requirement:
- full coverage of `Eligible Submissions × Components × Dimensions`
Excel/MCode implementation:
- You export:
  - the submissions dataset (raw LMS export)
  - the grading worksheet (roster + grade upload template)
- You validate joins and exclude dropped students.
- You have word count enrichment and sampling; these do not affect completeness.
Post-condition status:
- Satisfied at the component level provided:
  - every eligible submission has all expected component columns populated (or explicitly blank if missing)
  - dropped students are excluded before counting
Instantiation and Implementation Details (Excel):
- Add explicit “expected counts” section in `validation`:
  - `n_submissions_raw`
  - `n_submissions_eligible`
  - `n_components_expected`
  - Expected row count:
    - Mode A: `n_submissions_eligible`
    - Mode B: `n_submissions_eligible × n_components × n_dimensions`
- Add a check that required components are present as columns and not missing from the schema.
### 3.4 Unique Identity Integrity
Spec requirement:
- each row includes stable identifiers: `submission_id`, `component_id`, `dimension_id`
Excel/MCode implementation:
- `submission_id` exists implicitly (row-level identity from LMS export and/or grade sheet).
- `component_id` exists implicitly as a column identity (each of X columns represents a component).
- `dimension_id` is not yet represented as an explicit axis in the dataset (unless you restructure for Mode B).
Post-condition status:
- Satisfied for `submission_id` (implicit) and `component_id` (implicit as column name).
- Not satisfied for `dimension_id` unless adopting Mode B.
Instantiation and Implementation Details (Excel):
- Make identifiers explicit as fields:
  - Include a `submission_id` column (from LMS or grade sheet key)
  - Include a `row_id` column (anonymised stable ID)
- If adopting Mode B:
  - Create explicit `component_id` and `dimension_id` columns via unpivot steps
- Standardise identifier values:
  - `component_id` as stable short code (e.g., `PPP_C1`)
  - `dimension_id` as stable rubric ID (e.g., `D1`–`D5`)
### 3.5 Join Validation Integrity
Spec requirement:
- deterministic joins
- `__join_status` with `matched` / `no_match`
- exclude `no_match` and retain audit record
Excel/MCode implementation:
- You create a `validation` worksheet that computes `__join_status`.
- You flag dropped students as `no_match` and filter them out downstream.
- You retain the worksheet for auditability.
Post-condition status:
- Satisfied, provided the filtered dataset used for grading excludes all `no_match`.
Instantiation and Implementation Details (Excel):
- `validation` worksheet must include:
  - join keys used
  - `__join_status`
  - reason code (recommended) such as `dropped`, `missing_in_gradebook`, `missing_in_export`
- `cleaned_entries` must be derived only from `__join_status = matched`.
- Persist the list of excluded records (can be a filtered view or separate worksheet):
  - recommended worksheet: `excluded_submissions`
### 3.6 Cleaned Response Text Integrity
Spec requirement:
- `cleaned_response_text` produced by cleaning HTML, encoding artefacts, emoji, whitespace
- grading uses cleaned text
Excel/MCode implementation:
- MCode performs cleaning and produces `cleaned_entries`.
- Cleaning includes:
  - stripping HTML
  - removing emojibake / encoding artefacts
  - standardising text
- Word counts are computed on cleaned text.
Post-condition status:
- Satisfied, assuming scoring uses `cleaned_entries` rather than `raw_export`.
Instantiation and Implementation Details (Excel):
- In `cleaned_entries`, retain for each component:
  - `raw_text_<component>` (optional but recommended)
  - `cleaned_text_<component>` (required)
  - `word_count_<component>` (derived from cleaned text)
- If adopting Mode B, use a single column:
  - `raw_response_text`
  - `cleaned_response_text`
  - `word_count`
### 3.7 Dataset Scope Integrity
Spec requirement:
- include all eligible submissions
- exclude dropped/withdrawn students
- verify row count matches expected coverage
Excel/MCode implementation:
- Dropped students are detected via join validation (`no_match`) and filtered out.
- Scope is therefore driven by the grading worksheet roster.
Post-condition status:
- Satisfied if `cleaned_entries` is filtered to `matched` only and counts are verified.
Instantiation and Implementation Details (Excel):
- In `validation`, add a small scope summary block:
  - count of `matched`
  - count of `no_match`
  - list of `no_match` identifiers
- Confirm `cleaned_entries` row count equals count of `matched`.
### 3.8 Structural Consistency
Spec requirement:
- uniform schema, consistent encoding, no missing required fields
Excel/MCode implementation:
- You enforce a stable worksheet structure by:
  - saving the CSV into a workbook with a single worksheet
  - adding known worksheets in a known order
  - generating derived sheets through MCode
- Schema stability is currently implicit rather than validated.
Post-condition status:
- Mostly satisfied operationally; can be strengthened by explicit checks.
Instantiation and Implementation Details (Excel):
- Add a “schema check” section in `validation` that confirms presence of:
  - required component columns
  - required derived columns (cleaned text, word count)
  - required key columns (submission_id / row_id)
- Ensure workbook is saved in UTF-8-compatible settings where applicable (Power Query typically normalises encodings during import; note this explicitly in the doc).
### 3.9 Deterministic Reproducibility
Spec requirement:
- manifest: sources, steps, timestamp, counts
- rerunning with same inputs yields same outputs
Excel/MCode implementation:
- Determinism depends on:
  - using the same exports
  - running the same Power Query steps in the same order
  - ensuring sampling uses deterministic selection rules (see sampled_entries)
- You currently implement interior-uniform sampling based on word-count ranking.
- If the sampling algorithm is deterministic given the same cleaned dataset, Stage 0 is reproducible.
Post-condition status:
- Partially satisfied; missing an explicit manifest.
Instantiation and Implementation Details (Excel):
- Add a worksheet `stage0_manifest` containing:
  - export filenames (paste as values)
  - export timestamps (paste as values)
  - workbook name/version
  - MCode query names used (list)
  - counts: raw rows, matched rows, excluded rows
  - number of components, number of dimensions (if Mode B)
- For sampling determinism:
  - record the sampling parameters and seed (if any) in `stage0_manifest`
  - record the word-count ranking method used
### 3.10 Required Output Format
Spec requirement:
- flat tabular dataset; permissible formats include CSV, Parquet, SQL table
Excel/MCode implementation:
- Canonical dataset is a worksheet inside an `.xlsx` workbook.
- This is an acceptable implementation format if the worksheet is rectangular, schema-stable, and exportable.
Post-condition status:
- Satisfied if the worksheet can be exported as CSV without loss and contains explicit identifiers.
Instantiation and Implementation Details (Excel):
- Canonical worksheet: `cleaned_entries`
- Export step (recommended):
  - export `cleaned_entries` to `canonical_units.csv` for pipeline portability
- If staying Excel-native for this term:
  - treat the workbook as the authoritative Stage 0 artefact
  - ensure the canonical worksheet is clearly marked and stable
### 3.11 Summary of Normative Guarantees
Excel/MCode implementation summary:
- Join validation (`__join_status`) is already implemented and aligns strongly with the spec.
- Cleaning and word-count enrichment aligns with the spec.
- The main ambiguity is whether the canonical unit is:
  - `submission × component` (current state), or
  - `submission × component × dimension` (spec-literal, requires unpivoting dimensions into rows).
To make the workflow spec-grade without major disruption mid-term:
- Adopt Mode A explicitly for this term and document that dimension is applied downstream, or
- Add a Power Query unpivot step to reach Mode B while staying in Excel.
## 2. Recommended Minimal “Spec-Alignment” Edits Without Migration
If you want maximal alignment while staying in Excel:
1) Make identifiers explicit in `cleaned_entries`:
   - add `submission_id` and `row_id` columns (not only embedded in text)
2) Add a `stage0_manifest` worksheet:
   - sources, timestamps, query names, counts
3) Record the canonical worksheet contract:
   - declare `cleaned_entries` as the canonical dataset
   - declare required columns and their meaning
4) Decide and document Mode A vs Mode B:
   - If Mode A: update 3.1/3.2/3.3 language to be component-level for this implementation
   - If Mode B: implement unpivot into long format rows and add `component_id` + `dimension_id`
These edits improve traceability and reproducibility without changing the core workflow.
