## Pipeline1A_manifest_schema.md  
### Schema Definition for Pipeline 1A Processing Manifest  
### Rubric-Agnostic Canonicalisation of Grading Targets  
## 1. Purpose  
This document defines the **authoritative schema** for the Pipeline 1A processing manifest.
The Pipeline 1A manifest records:
- input identity  
- transformation lineage  
- scope counts  
- canonical identity guarantees  
- reproducibility contract  
It is a structured metadata artefact, not narrative documentation.
Each Pipeline 1A run must instantiate this schema.
## 2. Scope  
Pipeline 1A produces a rubric-agnostic canonical dataset of grading targets defined as:
```
submission_id × component_id
```
The manifest captures the state of that dataset at the moment Pipeline 1A completes.
Pipeline 1A does NOT include rubric expansion.  
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
- `logic_version_static` — version-controlled logic reference; frozen  
- `derived_from_snapshot` — computed from frozen canonical dataset  
- `derived_from_freeze_event` — reflects the freeze moment  
All fields must be static (no formulas) after freeze.
### 4.1 Stage Identity

| field | type | freeze rule | notes |
|-------|------|------------|-------|
| `stage` | string | static_literal | Must equal `0A` |
| `course` | string | metadata_static | Course identifier |
| `assessment` | string | metadata_static | Assessment identifier |
| `workbook_filename` | string | derived_from_freeze_event | Paste as value at freeze |
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
### 4.3 Query Lineage and Logic Version
Pipeline 1A must record the exact version of transformation logic used to produce the frozen snapshot.

| field | type | freeze rule | notes |
|-------|------|------------|-------|
| `pipeline_repo` | string | metadata_static | Repository name |
| `pipeline_commit` | string | logic_version_static | Git commit hash of logic used |
| `pq_query_validation_name` | string | metadata_static | Power Query name used |
| `pq_query_cleaned_entries_name` | string | metadata_static | Power Query name used |
| `pq_query_validation_file` | string | metadata_static | File name under version control |
| `pq_query_cleaned_entries_file` | string | metadata_static | File name under version control |
Sampling queries must NOT be listed in Pipeline 1A.
The `pipeline_commit` value must correspond to a committed state (working tree clean).
### 4.4 Canonical Identity Definition

| field                             | type   | freeze rule     | notes                                                        |
| --------------------------------- | ------ | --------------- | ------------------------------------------------------------ |
| `canonical_snapshot_worksheet`    | string | metadata_static | Exact worksheet name containing the frozen Pipeline 1A snapshot |
| `canonical_dataset`               | string | static_literal  | Must equal `cleaned_entries`                                 |
| `canonical_unit`                  | string | static_literal  | `submission_id × component_id`                               |
| `primary_key`                     | string | static_literal  | `(submission_id, component_id)`                              |
| `sort_order`                      | string | metadata_static | Must match snapshot ordering                                 |
| `identifier_source_submission_id` | string | metadata_static | Documented identifier origin                                 |
| `component_id_source`             | string | metadata_static | Documented component derivation                              |
### 4.5 Row Counts and Scope Validation
All fields below MUST be derived from the frozen canonical dataset snapshot.

| field | type | freeze rule | notes |
|-------|------|------------|-------|
| `count_raw_export_rows` | integer | metadata_static | Row count of raw LMS export |
| `count_validation_rows` | integer | metadata_static | Row count of validation sheet at freeze |
| `count_matched_unique` | integer | metadata_static | Matched rows at freeze |
| `count_no_match` | integer | metadata_static | Excluded rows at freeze |
| `count_cleaned_entries_rows` | integer | derived_from_snapshot | Row count of frozen canonical dataset |
| `count_unique_submission_ids` | integer | derived_from_snapshot | Distinct submission_id count |
| `count_unique_components` | integer | derived_from_snapshot | Distinct component_id count |
Coverage validation:

| field | type | freeze rule | notes |
|-------|------|------------|-------|
| `eligible_submissions` | integer | derived_from_snapshot | Distinct submission_id in canonical snapshot |
| `components` | integer | derived_from_snapshot | Distinct component_id in canonical snapshot |
| `expected_rows_formula` | string | metadata_static | Text representation only |
| `expected_rows_value` | integer | derived_from_snapshot | eligible_submissions × components |
| `coverage_check_pass` | boolean | derived_from_snapshot | Must equal TRUE |
### 4.6 Reproducibility Contract

| field | type | freeze rule | notes |
|-------|------|------------|-------|
| `re_run_rule` | string | static_literal | Deterministic equality condition |
Required value:
```
If inputs unchanged and pipeline_commit unchanged, counts must match exactly; otherwise Pipeline 1A is considered changed.
```
## 5. Invariants
At completion of Pipeline 1A:
1. All required fields exist.  
2. No field names are duplicated.  
3. All values are static (no formulas remain).  
4. All `derived_from_snapshot` fields reflect the frozen canonical dataset.  
5. `coverage_check_pass = TRUE`.  
6. `eligible_submissions = count_unique_submission_ids`.  
7. `pipeline_commit` corresponds to a committed repository state.  
If any invariant fails, Pipeline 1A is incomplete.
## 6. Snapshot Derivation and Freeze Enforcement
The Pipeline 1A manifest must be derived from a **frozen canonical dataset snapshot**.
Operational requirements:
1. Refresh all Power Query outputs.
2. Commit any query logic changes.
3. Record `pipeline_commit` using `git rev-parse HEAD`.
4. Create a static snapshot of `cleaned_entries` (copy → paste values or export CSV).
5. Compute all `derived_from_snapshot` fields from that snapshot.
6. Convert all formula-derived fields to static values.
7. Save workbook and record freeze timestamp.
After freeze, refreshing Power Query must not alter any manifest value.
If any manifest value changes after refresh, Pipeline 1A has not been properly frozen.
The manifest describes a **snapshot state**, not a live workbook state.


## 6. Snapshot Derivation and Freeze Enforcement
The Pipeline 1A manifest must be derived from a **frozen canonical dataset snapshot**.
Operational requirements:
1. Refresh all Power Query outputs.
2. Commit any query logic changes.
3. Record `pipeline_commit` using `git rev-parse HEAD`.
4. Create a static snapshot of `cleaned_entries` (copy → paste values)  **The snapshot is implemented as a dedicated worksheet with name: `stage0A_snapshot_<YYYY_MM_DD>`.**
5. Compute all `derived_from_snapshot` fields from that snapshot.
6. Convert all formula-derived fields to static values.
7. Save workbook and record freeze timestamp.
After freeze, refreshing Power Query must not alter any manifest value.
If any manifest value changes after refresh, Pipeline 1A has not been properly frozen.
The manifest describes a **snapshot state**, not a live workbook state.

## 8. Storage Location
Schema definition (pipeline repository):
## 7. Deterministic Behaviour Definition
Pipeline 1A is deterministic if:
- Input files are identical  
- `pipeline_commit` is identical  
- Snapshot-derived counts match exactly  
If any of these differ, the run must be considered distinct.
## 8. Storage Location
Schema definition (pipeline repository):
```
docs/01_design/Stage0A_manifest_schema.md
```
Course run instances:  ==belong in COURSE-SPECIFIC VAULT==

```
<course-vault>/
  06_grading/
    <ASSESSMENT>/
      03_runs/
        <YYYY-MM-DD>/
          cleaned_entries_snapshot.csv (OPTIONAL)
          <assessment>_stage0A.xlsx
```
The manifest must remain paired with its corresponding canonical dataset snapshot.

**Optional export (not required):** **If you also export a disk snapshot for portability, store it alongside the frozen workbook as `cleaned_entries_snapshot_<YYYY-MM-DD>.csv`.**
The manifest must remain paired with its corresponding canonical dataset snapshot.
## 9. Relationship to Stage 0B
Pipeline 1A manifest does NOT include:
- dimension identifiers  
- rubric version  
- dimension counts  
These belong exclusively to Stage 0B.
Pipeline 1A guarantees only:
```
submission_id × component_id
```
Stage 0B expands to:
```
submission_id × component_id × dimension_id
```
## 10. Summary
The Pipeline 1A manifest is a reproducibility contract tied to a frozen canonical dataset snapshot and a specific logic revision.
It guarantees that:
- grading targets are canonical  
- joins are validated  
- scope is complete  
- identity is stable  
- processing is deterministic  
Without a compliant Pipeline 1A manifest derived from a frozen snapshot and pinned to a specific `pipeline_commit`, reproducibility cannot be asserted.
