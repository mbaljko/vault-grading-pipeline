## 02_cleaning.pq — verification notes and required corrections (v01)
## 1. What this query is doing
This query is the canonical long-dataset builder.
It:
- cleans component response text fields from the LMS export (`Table_raw`)
- gates eligibility using the `validation` query output (`__join_status = matched_unique`)
- joins LMS rows to the roster map to obtain `submission_id`
- converts wide component columns into a long format:
  - `component_id`
  - `response_text`
- emits one row per:
  \```text
  submission_id × component_id
  \```
## 2. Alignment check against Pipeline 1A requirements
The core structural intent is aligned with Pipeline 1A:
- canonical unit: `submission_id × component_id` is produced via unpivot
- deterministic gating: uses `validation` and filters to `matched_unique`
- cleaned response text: produced by `StripHtmlSafe`
- wrapper-handling: introduces wrapper artefacts (`+++`, `+++row_id=<...>`) that are explicitly ignorable downstream (consistent with your earlier wrapper rules)
The join strategy is consistent with `01_validation` (joins on `User`), but it remains a known fragility (display-name join).
## 3. Misalignments and fixes to apply now
The following items are misaligned with your current architecture and/or with the authoritative component set.
### 3.1 Component set mismatch
This query cleans and unpivots:
- `SectionAResponse`
- `SectionBResponse`
- `SectionCResponse`
- `SectionDResponse`
- `SectionEResponse`
But your earlier `PPP_Step00_AssignmentPayloadSpec_v01` component set lists:
- `SectionAResponse`
- `SectionBResponse`
- `SectionCResponse`
- `SectionDResponse`
- `SectionFResponse`
Action required:
- decide whether `PPP` includes `SectionEResponse` or `SectionFResponse`
- then update this query so the cleaned/unpivoted component column list matches the authoritative payload spec exactly
If the payload spec is authoritative, then this query should be revised to replace all `SectionEResponse` occurrences with `SectionFResponse` (and ensure that column exists in the LMS export).
### 3.2 Evidence field naming mismatch
Pipeline 1A specification currently calls the cleaned text field:
- `cleaned_response_text`
This query outputs:
- `response_text`
You can resolve this in either direction, but it must be consistent across:
- `PPP_AssignmentPayloadSpec_v01`
- `PPP_<COMPONENT_ID>_CalibrationPayloadFormat_v01`
- downstream scoring prompts
Action required (pick one and standardise):
- option A: rename this query output column from `response_text` to `cleaned_response_text`
- option B: update the Pipeline 1A spec to declare the canonical evidence field as `response_text`
Right now, your payload spec example already uses `response_text`, so option B may be the least disruptive.
### 3.3 Wrapper artefact key mismatch (`row_id` vs canonical identifiers)
This query prefixes response text with:
\```text
+++row_id=<value>
\```
This is allowed as an ignorable wrapper artefact, but note:
- earlier, you explicitly moved away from `row_id` toward stable identifiers (`participant_id` / `submission_id`) for canonical reasoning
- `__row_id` is an internal index; it is not stable across refreshes unless you enforce determinism tightly
Action required (recommended):
- either remove the `row_id` wrapper prefix entirely, or
- replace it with a stable wrapper prefix:
  \```text
  +++submission_id=<submission_id>
  \```
  (or both, if you still want a debugging aid)
If you keep `__row_id`, treat it as non-authoritative debugging metadata only.
### 3.4 Deterministic reproducibility risk: `row_id` depends on row order
`Table.AddIndexColumn` assigns `__row_id` based on the current row ordering of `Expanded`.
If the upstream ordering changes (common in Excel/PQ refresh behaviour), `__row_id` will change.
Action required (if `__row_id` is retained):
- impose an explicit deterministic sort before `Table.AddIndexColumn`, for example by:
  - `submission_id`
  - plus any stable LMS fields you rely on
- or remove `__row_id` from all downstream expectations and treat it as a transient debugging field only
### 3.5 Redundant submission_id safeguard
This block:
- checks for `submission_id` in `ValidationFiltered`
- otherwise derives it from digits in `GW.Identifier`
Given that `01_validation` already emits `submission_id`, this fallback is not wrong, but it creates a second independent derivation path.
Action required (recommended):
- treat `01_validation` as the single authoritative derivation of `submission_id`
- remove the fallback derivation here, and fail loudly (or emit a validation error) if `submission_id` is missing from `validation`
### 3.6 Join key risk: join on `User`
This query joins `Cleaned` to `ValidationMap` on `User`:
\```text
Table.NestedJoin(Cleaned, {"User"}, ValidationMap, {"User"}, ...)
\```
This inherits the same fragility as the original validation join strategy.
Action required (future improvement, not blocking if you must proceed):
- if the LMS export includes `Username` and the grading worksheet includes the same stable identifier, switch the join to that stable field
- otherwise, keep this as-is, but explicitly document it as a known limitation and gate ambiguous cases upstream (which you already do)
## 4. Confirmed outputs and intended downstream usage
The emitted dataset is long format with columns:
- `submission_id`
- `component_id`
- `response_text` (cleaned + wrapped)
- optional metadata:
  - `response_wc`
  - `__row_id`
Downstream expectations:
- any wrapper artefacts inside `response_text` must be ignored during scoring
- eligibility gating is enforced by inclusion (inner join against `matched_unique`)
## 5. Minimal edits to keep moving forward
If your goal is “good enough, proceed”, the minimal blocking corrections are:
1) Make the component list match the authoritative payload spec  
2) Decide and standardise the evidence field name (`response_text` vs `cleaned_response_text`)  
3) Remove or stabilise `row_id` usage (prefer stable identifiers or no wrapper prefix)
If you tell me whether `PPP` should include `SectionEResponse` or `SectionFResponse`, I can rewrite the exact places in this query that must change (without otherwise refactoring your logic).
