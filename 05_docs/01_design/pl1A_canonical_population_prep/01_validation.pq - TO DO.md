## 01_validation.pq — documented behaviour and constraints (v01)
### 1. Purpose
`01_validation.pq` performs the join-validation step that connects the LMS export (`Table_raw`) to the grading worksheet roster (`grading_worksheet`) and emits canonical identifiers and join-gating fields for downstream processing.
This query is part of the rubric-agnostic canonicalisation workflow and exists to:
- produce a canonical `submission_id` derived from the grading worksheet identifier,
- preserve the original grading worksheet identifier for auditability (`GW.Identifier`),
- emit an explicit `__join_status` that gates which records are eligible for canonical grading targets.
### 2. Inputs
This query assumes the Excel workbook contains the following named tables:
- `Table_raw`
  - LMS export rows (one row per LMS export record)
  - must include a display-name field in column `User` (used only for join-key construction)
- `grading_worksheet`
  - roster / grading upload template rows
  - must include:
    - `Full name` (used only for join-key construction)
    - `Identifier` (used as the authoritative source for canonical `submission_id`)
### 3. Outputs
This query emits a table with the following columns:
- `User`
- `Username`
- `__key_name`
- `GW.Full name`
- `GW.Identifier`
- `submission_id`
- `__join_status`
- `__gw_name_count`
### 4. Canonical identifier rule
#### 4.1 `submission_id` derivation
`submission_id` is derived from `GW.Identifier` by extracting trailing digits only.
Operational definition:
- `GW.Identifier` is expected to contain a stable identifier that ends in digits (for example: `Participant 7835077`).
- `submission_id` is the digits-only suffix of `GW.Identifier`.
Constraint:
- If `GW.Identifier` does not end in digits, `submission_id` must be treated as non-derivable and the record must not be graded.
Implementation note:
- The trailing-digit extraction logic must normalise empty strings to null to prevent false positives in grading gates.
### 5. Join key construction
#### 5.1 Join-key intent
The join attempts to match LMS export rows to grading worksheet rows using a normalised display-name key.
This is a pragmatic join strategy and is less stable than joins on institutional identifiers. It is retained as the current approach because it is available in both inputs.
#### 5.2 Normalisation pipeline (`key_name`)
A normalised key is computed from:
- LMS side: `User`
- grading worksheet side: `Full name`
Normalisation steps:
- coerce to text
- replace non-breaking spaces with regular spaces
- `Text.Clean` and `Text.Trim`
- collapse repeated spaces (bounded passes)
- lowercase
- strip leading non-alphanumeric noise (e.g., leading `.`)
Output:
- `__key_name` (lowercase, trimmed, normalised join key)
### 6. Duplicate-name handling and join resolution
#### 6.1 Name-count logic
The grading worksheet is grouped by `__key_name` and a count is computed:
- `__gw_name_count` = number of grading worksheet rows that share the join key
#### 6.2 Resolution rule
- If `__gw_name_count = 1`, the unique grading worksheet row is resolved and expanded into:
  - `GW.Identifier`
  - `GW.Full name`
- If `__gw_name_count > 1`, the join is treated as ambiguous and not resolved.
- If no match exists, the record is treated as unmatched.
### 7. Join-gating field (`join_status`)
`__join_status` provides the gating classification used to determine whether a record is eligible to proceed to canonical grading targets.
Authoritative allowed values:
- `matched_unique`
  - a single unique grading worksheet match exists (`__gw_name_count = 1`)
  - `submission_id` is present and non-empty
- `excluded_ambiguous`
  - the join key matches multiple grading worksheet rows (`__gw_name_count > 1`)
  - record must not be graded until ambiguity is resolved upstream
- `no_match`
  - no grading worksheet match exists
  - record must not be graded
Downstream rule:
- only rows with `__join_status = matched_unique` are eligible to flow into canonical grading targets.
### 8. Identity handling and auditability
This query emits both:
- canonical identifier: `submission_id`
- audit fields: `GW.Identifier`, `GW.Full name`
Normative note:
- downstream canonical datasets may drop direct identifiers (e.g., full names) if required for identity-safe handling, but must retain enough auditability to reconcile mismatches when needed.
### 9. Known limitations
- Joining on display names is inherently fragile (format differences, preferred names, diacritics, LMS export variability).
- This query mitigates ambiguity by excluding duplicate-name collisions rather than guessing.
- If a shared stable identifier becomes available in both LMS export and grading worksheet (email, username, institutional ID), the join strategy should be upgraded to use that identifier as the primary key, with display-name matching used only as a fallback.
### 10. Maintenance checklist
When inputs or exports change, confirm:
- `Table_raw` still contains `User`
- `grading_worksheet` still contains `Full name` and `Identifier`
- `GW.Identifier` still ends in digits suitable for `submission_id`
- `__join_status` values remain exactly:
  - `matched_unique`
  - `excluded_ambiguous`
  - `no_match`
If any of the above assumptions fail, treat the query as incompatible until updated.
