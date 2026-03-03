## Stage 0B (Excel/MCode) — Implementation Mapping to Specification
### Mapping the current Excel + Power Query workflow to the Stage 0B rubric-expansion specification
This document maps the current Excel/MCode workflow to the Stage 0B specification, showing:
(a) where each post-condition is satisfied,  
(b) what worksheet(s) and artefacts implement it, and  
(c) what gaps or clarifications are required for explicit compliance.
## 0. Excel Workbook Mental Model (Stage 0B)
Stage 0B is implemented within the same Excel workbook used for Stage 0A, but introduces rubric-dependent structure.
### 0.1 Workbook Inputs (as Worksheets)
#### Stage 0A Canonical Snapshot Worksheet
**Role**  
Frozen Stage 0A canonical dataset snapshot (rubric-agnostic grading targets).
**Worksheet Name**  
The worksheet name varies by run and must be recorded in the Stage 0A manifest via the field:
`canonical_snapshot_worksheet`
Example:
`stage0A_snapshot_2026_03_01`
**Required Columns (Long Format Targets)**  
`submission_id`  
`component_id`  
`response_text` (cleaned)
**Optional Metadata Columns**  
`response_wc`  
`__row_id`
This worksheet must contain static values only. It represents the frozen canonical dataset state for the run.
#### `rubric_definition`
**Role**  
Authoritative rubric table defining the dimension set per component for Stage 0B expansion.
**Required Structure**  
`component_id`  
`dimension_id`  
Optional (recommended):  
`dimension_order`
**Requirements**  
The rubric definition must be:
- deterministic  
- version-traceable  
- stable across re-runs of Stage 0B  
Rubric identifiers must not depend on display labels.
### 0.2 Stage 0B Outputs (as worksheets)
- `grading_units`  
  - Canonical grading unit dataset (Stage 0B output)
  - Long format units:
    - `submission_id`
    - `component_id`
    - `dimension_id`
    - `response_text` (inherited)
    - optional metadata
- `stage0B_manifest`  
  - Processing manifest (rubric-aware)
- `stage0B_coverage_report`  
  - Coverage + integrity checks (duplicates, missingness, expected counts)
### 0.3 Query Boundary
Stage 0B must reference `cleaned_entries_snapshot`, not live query outputs, to ensure determinism.
## 1. Mapping to Required Post-Conditions
### 3.1 Canonical Grading Unit Definition
#### Spec Requirement
Each row represents exactly one unique grading unit:
```
submission_id × component_id × dimension_id
```
#### Excel/MCode Implementation
- Create `grading_units` via a deterministic expansion join between:
  - `cleaned_entries_snapshot` (targets)
  - `rubric_definition` (dimensions per component)
Implementation pattern (Power Query):
- Join on `component_id`
- Expand to one row per dimension
#### Compliance Status
Not satisfied unless `grading_units` exists and includes `dimension_id`.
#### Implementation Details
- Worksheet: `rubric_definition`
- Worksheet: `grading_units` (query output)
- Query should be named (recommended): `04_stage0B_grading_units.pq`
### 3.2 Primary Key Uniqueness
#### Spec Requirement
Composite key must be unique:
```
(submission_id, component_id, dimension_id)
```
Duplicates prohibited.
A materialised key must be constructible:
```
grading_unit_id = submission_id::component_id::dimension_id
```
#### Excel/MCode Implementation
- Compute a deterministic `grading_unit_id` column in `grading_units` (recommended as a stored column)
- Create a `stage0B_coverage_report` table that:
  - groups by `(submission_id, component_id, dimension_id)`
  - checks for counts > 1
#### Compliance Status
Satisfied only if duplicate detection exists and is checked at freeze time.
#### Implementation Details
- Add computed column in `grading_units`:
  - `grading_unit_id`
- Add duplicate check query (recommended): `05_stage0B_duplicates_check.pq`
- Coverage report fields:
  - `duplicate_key_count`
  - `duplicate_key_examples` (optional)
### 3.3 Complete Rubric Coverage
#### Spec Requirement
Full coverage of:
```
Eligible Submissions × Components × Dimensions
```
No missing dimensions for any target.
#### Excel/MCode Implementation
- Expected rows computed as:
```
expected_rows_value = (distinct submission_id in snapshot)
                      × (count of target component rows per submission in snapshot)
                      × (dimensions per component from rubric_definition)
```
Practical computation:
- derive expected unit count by summing per-component dimension expansion:
```
expected_rows_value = Σ_over_components (target_rows_for_component × dims_for_component)
```
#### Compliance Status
Satisfied only if expected vs actual is computed and matches exactly.
#### Implementation Details
- Query: `06_stage0B_expected_count.pq`
- Coverage report fields:
  - `expected_rows_value`
  - `actual_rows_value` (row count of `grading_units`)
  - `coverage_check_pass` (TRUE iff equal)
- If mismatch:
  - report missing component/dimension pairs
### 3.4 Rubric Alignment Integrity
#### Spec Requirement
Each `dimension_id` must:
- match authoritative rubric definitions
- be stable across runs
- not depend on display labels
- be version-traceable
Rubric drift not permitted.
#### Excel/MCode Implementation
- `rubric_definition` worksheet must store:
  - `rubric_id`
  - `rubric_version`
  - `component_id`
  - `dimension_id`
  - `dimension_order`
  - `dimension_label` (optional display)
Stage 0B must join using `component_id` and expand using `dimension_id`.
#### Compliance Status
Satisfied only if:
- rubric version is recorded
- rubric table is deterministic and controlled
#### Implementation Details
- Worksheet: `rubric_definition`
- Manifest must record:
  - `rubric_id`
  - `rubric_version`
  - `rubric_definition_source` (file name or sheet name)
- Validation: ensure all `component_id` values in snapshot exist in rubric_definition
### 3.5 Deterministic Rubric Expansion
#### Spec Requirement
Given identical inputs (targets snapshot + rubric definition), output must be identical.
#### Excel/MCode Implementation
Determinism ensured by:
- referencing `cleaned_entries_snapshot` (frozen)
- referencing a frozen rubric definition table
- stable join keys (`component_id`)
- stable ordering rules applied after expansion
#### Compliance Status
Satisfied only if the workbook enforces snapshot usage and records versions.
#### Implementation Details
- `stage0B_manifest` includes:
  - `targets_snapshot_name`
  - `targets_snapshot_timestamp`
  - `rubric_version`
  - `pq_query_grading_units`
- Optional: record a hash of the snapshot export (manual) if desired
### 3.6 Text Association Integrity
#### Spec Requirement
Each grading unit must contain:
- the exact cleaned response text corresponding to its component
Text is inherited directly from Stage 0A.
Text duplication across dimensions is expected.
#### Excel/MCode Implementation
- `grading_units` must copy `response_text` from the target row unchanged
- No cleaning transforms permitted in Stage 0B
#### Compliance Status
Satisfied if `grading_units.response_text` is identical to snapshot response text for the same `(submission_id, component_id)`.
#### Implementation Details
- Coverage report should include a spot-check metric:
  - `text_inheritance_check` (optional)  
  Example check: compare counts of distinct response_text per `(submission_id, component_id)` equals 1.
### 3.7 Dataset Scope Integrity
#### Spec Requirement
Include all eligible submissions; exclude ineligible.
#### Excel/MCode Implementation
- Stage 0B scope is inherited from Stage 0A snapshot
- Therefore scope integrity holds iff snapshot integrity holds
#### Compliance Status
Satisfied by construction if Stage 0B uses snapshot exclusively.
#### Implementation Details
- Manifest should record:
  - `targets_snapshot_row_count`
  - `targets_snapshot_unique_submission_ids`
### 3.8 Structural Consistency
#### Spec Requirement
Uniform schema with required fields:
- identifiers
- response text
- optional metadata
No missing required fields.
#### Excel/MCode Implementation
- `grading_units` query must explicitly select and order required columns
- Coverage report checks for nulls in required fields:
  - `submission_id`
  - `component_id`
  - `dimension_id`
  - `response_text`
#### Compliance Status
Satisfied only if null checks are executed and recorded.
#### Implementation Details
- Query: `07_stage0B_nulls_check.pq`
- Report fields:
  - `null_submission_id_count`
  - `null_component_id_count`
  - `null_dimension_id_count`
  - `null_response_text_count`
### 3.9 Deterministic Ordering
#### Spec Requirement
Sort order:
```
submission_id → component_id → dimension_id
```
#### Excel/MCode Implementation
- In `grading_units` query, apply a deterministic sort step:
  - `submission_id` ascending
  - `component_id` ascending
  - `dimension_order` ascending (or `dimension_id` if order encoded)
#### Compliance Status
Satisfied only if sorting is applied in the query and not left to Excel UI.
#### Implementation Details
- In rubric_definition, include `dimension_order` (integer)
- Sort by:
  - `submission_id`
  - `component_id`
  - `dimension_order`
### 3.10 Reproducibility and Manifest Recording
#### Spec Requirement
Stage 0B must produce a manifest recording:
- rubric version used
- input dataset identifiers
- expansion method
- row counts pre/post
- timestamp
- environment or script version
#### Excel/MCode Implementation
- Create `stage0B_manifest` worksheet following a two-column schema:
  - `field | value`
- Values must be pasted as static at freeze
#### Compliance Status
Not satisfied until manifest exists and is frozen.
#### Implementation Details (recommended fields)
- `stage` = `0B`
- `course`
- `assessment`
- `workbook_filename`
- `workbook_saved_timestamp`
- `targets_snapshot_name`
- `targets_snapshot_timestamp`
- `rubric_id`
- `rubric_version`
- `pq_query_grading_units`
- `count_targets_rows`
- `count_grading_units_rows`
- `count_unique_submission_ids`
- `count_unique_components`
- `count_unique_dimensions`
- `expected_rows_value`
- `coverage_check_pass`
- `re_run_rule`:
  - If targets snapshot unchanged and rubric unchanged and queries unchanged, counts must match exactly; otherwise Stage 0B is considered changed.
## 2. Implementation Gaps and Minimal Actions
To achieve full Stage 0B compliance while remaining in Excel:
1. Create `rubric_definition` as an authoritative table with stable ids and version fields.
2. Create `grading_units` by joining `cleaned_entries_snapshot` to `rubric_definition` and expanding dimensions.
3. Add deterministic ordering via `dimension_order`.
4. Create `stage0B_coverage_report` that computes:
   - duplicates
   - null counts
   - expected vs actual unit counts
5. Create and freeze `stage0B_manifest`.
## 3. Notes on Where This Lives
Pipeline repository (reusable documentation):
```
vault-grading-pipeline/
  docs/01_design/
    Stage_0B_Excel_MCode_Implementation_Mapping.md
```
Course vault (run artefacts and snapshots):
```
<course-vault>/
  06_grading/
    PPP/
      03_runs/
        <YYYY-MM-DD>/
          cleaned_entries_snapshot.xlsx
          grading_units_snapshot.xlsx
          stage0B_manifest.xlsx
          stage0B_coverage_report.xlsx
```
## 4. Summary
Stage 0B in Excel/MCode is compliant when:
- `grading_units` exists with one row per `submission_id × component_id × dimension_id`
- duplicates are checked and absent
- rubric coverage is complete and validated
- rubric version is recorded
- ordering is deterministic
- a frozen `stage0B_manifest` exists and is paired with frozen snapshots
Downstream calibration and scoring assume these guarantees.
