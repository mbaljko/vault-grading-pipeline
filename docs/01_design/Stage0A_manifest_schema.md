## Stage0A_manifest_schema.md
### Schema Definition for Stage 0A Processing Manifest
### Rubric-Agnostic Canonicalisation of Grading Targets
## 1. Purpose
This document defines the **authoritative schema** for the Stage 0A processing manifest.
The Stage 0A manifest records:
- input identity
- transformation lineage
- scope counts
- canonical identity guarantees
- reproducibility contract
It is a structured metadata artefact, not narrative documentation.
Each Stage 0A run must instantiate this schema.
## 2. Scope
Stage 0A produces a rubric-agnostic canonical dataset of grading targets defined as:
```
submission_id × component_id
```
The manifest captures the state of that dataset at the moment Stage 0A completes.
Stage 0A does NOT include rubric expansion.  
Dimension identifiers belong to Stage 0B.
## 3. Structural Format
The manifest must be stored as a flat two-column table:
```
field | value
```
- `field` — unique field name (string)
- `value` — string or scalar representation
No additional columns are permitted.
The table must not contain duplicate `field` entries.
## 4. Required Fields
All fields below are REQUIRED unless marked optional.
### 4.1 Stage Identity

| field                      | type   | description                   |
| -------------------------- | ------ | ----------------------------- |
| `stage`                    | string | Must equal `0A`               |
| `course`                   | string | Course identifier             |
| `assessment`               | string | Assessment identifier         |
| `workbook_filename`        | string | Excel workbook name           |
| `workbook_saved_timestamp` | string | Timestamp when run was frozen |
### 4.2 Input Identity

| field | type | description |
|-------|------|-------------|
| `input_raw_export_filename` | string | LMS submission export filename |
| `input_raw_export_exported_timestamp` | string | Timestamp embedded in LMS export |
| `input_grade_upload_template_filename` | string | LMS grading worksheet filename |
| `input_grade_upload_template_exported_timestamp` | string | Timestamp from grading export |
Optional (if used):

| field | type | description |
|-------|------|-------------|
| `input_database_export_filename` | string | Institutional export filename |
| `input_database_exported_timestamp` | string | Timestamp of database export |
### 4.3 Query Lineage
These fields define the transformation logic.

| field | type | description |
|-------|------|-------------|
| `pq_query_validation` | string | Name or file of validation query |
| `pq_query_cleaned_entries` | string | Name or file of canonical dataset query |
Sampling queries must NOT be listed in Stage 0A.
### 4.4 Canonical Identity Definition
These fields define the structural contract of Stage 0A.

| field | type | description |
|-------|------|-------------|
| `canonical_dataset` | string | Must equal `cleaned_entries` |
| `canonical_unit` | string | Must equal `submission_id × component_id` |
| `primary_key` | string | Must equal `(submission_id, component_id)` |
| `sort_order` | string | Deterministic sort definition |
| `identifier_source_submission_id` | string | Source of submission_id |
| `component_id_source` | string | How component_id is derived |
### 4.5 Row Counts and Scope Validation
These fields validate deterministic coverage.

| field | type | description |
|-------|------|-------------|
| `count_raw_export_rows` | integer | Row count in LMS export |
| `count_validation_rows` | integer | Row count in validation sheet |
| `count_matched_unique` | integer | Rows where join_status = matched_unique |
| `count_no_match` | integer | Rows excluded |
| `count_cleaned_entries_rows` | integer | Final canonical row count |
| `count_unique_submission_ids` | integer | Distinct submission_id count |
| `count_unique_components` | integer | Distinct component_id count |
Coverage validation:

| field                   | type    | description                        |
| ----------------------- | ------- | ---------------------------------- |
| `eligible_submissions`  | integer | Count of matched submissions       |
| `components`            | integer | Count of components per submission |
| `expected_rows_formula` | string  | Textual formula representation     |
| `expected_rows_value`   | integer | Computed expected count            |
| `coverage_check_pass`   | boolean | Must be TRUE                       |
### 4.6 Reproducibility Contract

| field | type | description |
|-------|------|-------------|
| `re_run_rule` | string | Deterministic equality condition |
Required value:
```
If inputs unchanged and queries unchanged, counts must match exactly; otherwise Stage 0A is considered changed.
```
## 5. Invariants
At completion of Stage 0A:
1. All required fields exist.
2. No field names are duplicated.
3. Row counts reconcile exactly.
4. `coverage_check_pass = TRUE`.
5. Canonical dataset identity matches declared unit definition.
6. Manifest reflects the actual workbook state.
If any invariant fails, Stage 0A is incomplete.
## 6. Deterministic Behaviour Definition
Stage 0A is deterministic if:
- input files are identical
- Power Query definitions are unchanged
- row counts and identity fields match
If any of these differ, the run must be considered distinct.
## 7. Storage Location
Recommended location in pipeline repository:
```
/06_grading/<ASSESSMENT>/03_runs/<YYYY-MM-DD>/stage0A_manifest.xlsx
```
or, if exported:
```
stage0A_manifest.json
```
The manifest must remain paired with its corresponding canonical dataset snapshot.
## 8. Relationship to Stage 0B
Stage 0A manifest does NOT include:
- dimension identifiers
- rubric version
- dimension counts
These belong exclusively to Stage 0B.
Stage 0A guarantees only:
```
submission_id × component_id
```
Stage 0B expands to:
```
submission_id × component_id × dimension_id
```
## 9. Summary
The Stage 0A manifest is a reproducibility contract.
It guarantees that:
- grading targets are canonical
- joins are validated
- scope is complete
- identity is stable
- processing is deterministic
Without a compliant Stage 0A manifest, reproducibility cannot be asserted.
