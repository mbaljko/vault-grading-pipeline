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
- `value` — scalar representation  
No additional columns are permitted.
The table must not contain duplicate `field` entries.
All values must be static at freeze time.
## 4. Required Fields
All fields below are REQUIRED unless marked optional.
Each field includes a **freeze rule**, which defines how its value must behave at freeze time.
Freeze rule categories:
- `static_literal` — constant defined by specification  
- `metadata_static` — descriptive metadata; manually entered; frozen  
- `query_identity_static` — reflects query names at freeze; frozen  
- `derived_from_snapshot` — computed from frozen canonical dataset  
- `derived_from_freeze_event` — reflects the freeze moment  
All fields must be static (no formulas) after freeze.
### 4.1 Stage Identity

| field | type | freeze rule | notes |
|-------|------|------------|-------|
| `stage` | string | static_literal | Must equal `0A` |
| `course` | string | metadata_static | Course identifier |
| `assessment` | string | metadata_static | Assessment identifier |
| `workbook_filename` | string | derived_from_freeze_event | May be formula initially; paste as value |
| `workbook_saved_timestamp` | string | derived_from_freeze_event | Timestamp recorded at freeze |
### 4.2 Input Identity

| field | type | freeze rule | notes |
|-------|------|------------|-------|
| `input_raw_export_filename` | string | metadata_static | LMS export filename |
| `input_raw_export_exported_timestamp` | string | metadata_static | Timestamp embedded in export |
| `input_grade_upload_template_filename` | string | metadata_static | LMS grading worksheet filename |
| `input_grade_upload_template_exported_timestamp` | string | metadata_static | Timestamp from grading export |
| `input_database_export_filename` (optional) | string | metadata_static | Institutional export filename |
| `input_database_exported_timestamp` (optional) | string | metadata_static | Database export timestamp |
### 4.3 Query Lineage

| field | type | freeze rule | notes |
|-------|------|------------|-------|
| `pq_query_validation` | string | query_identity_static | Query name used at freeze |
| `pq_query_cleaned_entries` | string | query_identity_static | Query name used at freeze |
Sampling queries must NOT be listed in Stage 0A.
### 4.4 Canonical Identity Definition

| field                             | type   | freeze rule     | notes                           |
| --------------------------------- | ------ | --------------- | ------------------------------- |
| `canonical_dataset`               | string | static_literal  | Must equal `cleaned_entries`    |
| `canonical_unit`                  | string | static_literal  | `submission_id × component_id`  |
| `primary_key`                     | string | static_literal  | `(submission_id, component_id)` |
| `sort_order`                      | string | metadata_static | Must match snapshot ordering    |
| `identifier_source_submission_id` | string | metadata_static | Documented identifier origin    |
| `component_id_source`             | string | metadata_static | Documented component derivation |
### 4.5 Row Counts and Scope Validation
All fields below MUST be derived from the frozen canonical dataset snapshot.

| field                         | type    | freeze rule           | notes                                 |
| ----------------------------- | ------- | --------------------- | ------------------------------------- |
| `count_raw_export_rows`       | integer | derived_from_snapshot | Raw export row count used in this run |
| `count_validation_rows`       | integer | derived_from_snapshot | Validation table row count at freeze  |
| `count_matched_unique`        | integer | derived_from_snapshot | Eligible rows at freeze               |
| `count_no_match`              | integer | derived_from_snapshot | Excluded rows at freeze               |
| `count_cleaned_entries_rows`  | integer | derived_from_snapshot | Row count of frozen canonical dataset |
| `count_unique_submission_ids` | integer | derived_from_snapshot | Distinct submission_id count          |
| `count_unique_components`     | integer | derived_from_snapshot | Distinct component_id count           |
Coverage validation:

| field                   | type    | freeze rule           | notes                                                                                      |
| ----------------------- | ------- | --------------------- | ------------------------------------------------------------------------------------------ |
| `eligible_submissions`  | integer | derived_from_snapshot | Distinct `submission_id` in canonical snapshot (Stage 0A defines eligibility by inclusion) |
| `components`            | integer | derived_from_snapshot | Distinct `component_id` in canonical snapshot                                              |
| `expected_rows_formula` | string  | metadata_static       | Text representation only                                                                   |
| `expected_rows_value`   | integer | derived_from_snapshot | eligible_submissions × components                                                          |
| `coverage_check_pass`   | boolean | derived_from_snapshot | Must equal TRUE                                                                            |

### 4.6 Reproducibility Contract

| field | type | freeze rule | notes |
|-------|------|------------|-------|
| `re_run_rule` | string | static_literal | Required deterministic rule |
Required value:
```
If inputs unchanged and queries unchanged, counts must match exactly; otherwise Stage 0A is considered changed.
```
## 5. Invariants
At completion of Stage 0A:
1. All required fields exist.  
2. No field names are duplicated.  
3. All values are static (no formulas remain).  
4. All fields marked `derived_from_snapshot` reflect the frozen canonical dataset.  
5. `coverage_check_pass = TRUE`.  
6. Canonical dataset identity matches declared unit definition.  
7. `eligible_submissions` = `count_unique_submission_ids`
If any invariant fails, Stage 0A is incomplete.
## 6. Snapshot Derivation and Freeze Enforcement
The Stage 0A manifest must be derived from a **frozen canonical dataset snapshot**.
Operational requirements:
1. The canonical dataset must be copied and converted to static values (snapshot sheet or exported CSV).
2. All fields marked `derived_from_snapshot` must be computed from that snapshot.
3. Any formula-derived values must be converted to static values before declaring freeze complete.
4. After freeze, refreshing Power Query must not alter any manifest value.
5. If any manifest value changes after refresh, the freeze procedure was not properly executed.
The manifest describes a snapshot state, not the live workbook state.
## 7. Deterministic Behaviour Definition
Stage 0A is deterministic if:
- Input files are identical.  
- Power Query definitions are unchanged.  
- Snapshot-derived counts match exactly.  
If any of these differ, the run must be considered distinct.
## 8. Storage Location
Schema definition (pipeline repository):
```
docs/01_design/Stage0A_manifest_schema.md
```
Course-specific run instances:
```
<course-vault>/
  06_grading/
    <ASSESSMENT>/
      03_runs/
        <YYYY-MM-DD>/
          cleaned_entries.csv
          stage0A_manifest.xlsx
```
The manifest must remain paired with its corresponding canonical dataset snapshot.
## 9. Relationship to Stage 0B
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
## 10. Summary
The Stage 0A manifest is a reproducibility contract tied to a frozen canonical dataset snapshot.
It guarantees that:
- grading targets are canonical  
- joins are validated  
- scope is complete  
- identity is stable  
- processing is deterministic  
Without a compliant Stage 0A manifest derived from a frozen snapshot, reproducibility cannot be asserted.### 4.5 Row Counts and Scope Validation
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
| `coverage_check_pass`   | boolean | Must be TRUE                      |
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
6. Manifest reflects the actual workbook state at freeze time.  
If any invariant fails, Stage 0A is incomplete.
## 6. Snapshot Derivation Requirement
The Stage 0A manifest must be derived from a **frozen canonical dataset snapshot**.
The manifest must not reference live query outputs at the time of future refresh.
Specifically:
1. All `count_*` fields must reflect the row counts of the frozen canonical dataset.
2. `expected_rows_value` must reflect the computed value at freeze time.
3. `coverage_check_pass` must reflect the boolean state at freeze time.
4. Any formula-derived fields must be converted to static values before the manifest is considered complete.
5. After freeze, refreshing Power Query must not alter manifest values.
If manifest values change after query refresh, Stage 0A has not been properly frozen.
The manifest describes a **snapshot state**, not a live workbook state.
## 7. Deterministic Behaviour Definition
Stage 0A is deterministic if:
- input files are identical  
- Power Query definitions are unchanged  
- row counts and identity fields match  
If any of these differ, the run must be considered distinct.
## 8. Storage Location
Recommended location in pipeline repository:
```
docs/01_design/Stage0A_manifest_schema.md
```
Course run instances:
```
<course-vault>/
  06_grading/
    <ASSESSMENT>/
      03_runs/
        <YYYY-MM-DD>/
          cleaned_entries.csv
          stage0A_manifest.xlsx
```
The manifest must remain paired with its corresponding canonical dataset snapshot.
## 9. Relationship to Stage 0B
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
## 10. Summary
The Stage 0A manifest is a reproducibility contract.
It guarantees that:
- grading targets are canonical  
- joins are validated  
- scope is complete  
- identity is stable  
- processing is deterministic  
Without a compliant Stage 0A manifest derived from a frozen snapshot, reproducibility cannot be asserted.
