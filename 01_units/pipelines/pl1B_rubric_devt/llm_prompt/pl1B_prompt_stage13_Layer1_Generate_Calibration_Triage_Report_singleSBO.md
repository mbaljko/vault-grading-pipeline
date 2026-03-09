---
prompt_id: calibration_triage
version: v01
stage: calibration
purpose: triage scored indicator rows to identify cases that may require human review during rubric calibration
status: active
owner: EECS3000W26
input_contract:
  - indicator_specification
  - scored_rows_dataset
input_structure:
  delimiter: "==="
  artefacts:
    - name: indicator_specification
      fields:
        - indicator_definition
        - assessment_guidance
        - evaluation_notes
    - name: scored_rows_dataset
      expected_columns:
        - submission_id
        - component_id
        - indicator_id
        - evidence_status
        - evaluation_notes
        - confidence
        - flags
output_contract: fenced_markdown_tables
constraints:
  - do_not_rescore_responses
  - do_not_modify_scoring
  - triage_only
notes: prompt performs calibration triage by sampling scored rows and identifying potentially ambiguous or misclassified cases for human inspection
---

PROMPT: Calibration triage

You are helping triage rubric calibration results for a rubric indicator.

The prompt receives two artefacts after the prompt text.

These artefacts will be supplied using the delimiter `===` in the following structure.

===
Indicator specification:
<indicator_definition>
<assessment_guidance>
<evaluation_notes>

===
Scored rows follow.

===


Procedure:

1. Examine the full dataset to understand the distribution of `evidence_status` values.

2. Internally select a diagnostic inspection set consisting of:
   - up to 8 rows where `evidence_status = evidence`
   - up to 8 rows where `evidence_status = partial_evidence`
   - up to 8 rows where `evidence_status = little_to_no_evidence`
The inspection set therefore contains **at most 24 rows total**.  
All rows appearing anywhere in the output **must come from this inspection set**.  
No additional rows from the dataset may be introduced.  

3. Choose rows that appear representative or potentially ambiguous.

4. Using only the selected inspection set:
   - group responses into clear positives, borderline cases, and questionable cases
   - flag rows that may represent possible misclassifications

Do not change the scoring.  
Do not rescore the responses.  
Only flag rows for human review.


Panels A–C must partition the Selected inspection set.
Every row in the inspection set must appear in exactly one panel.
No new rows may appear in the panels.

Output constraint:
The rows listed in Panel A, Panel B, and Panel C must be drawn only from the Selected inspection set.
Do not include rows that are not listed in the inspection set table.
##### Output format

Emit results as fenced Markdown.

```
#### <indicator_id> — <short_indicator_description>

##### Selected inspection set

| submission_id | evidence_status | reason_selected |
|---|---|---|

##### Triage results

##### Panel A — Clear positives
*Inspection question for these:* Does the response clearly contain the analytic signal described by the indicator_definition?

| submission_id | evidence_status | inspection_note |
|---|---|---|

##### Panel B — Borderline cases
*Inspection questions for these:* 
- Is the analytic signal actually present?
- Is the signal weak or incomplete?
- Does this belong in a different indicator?

| submission_id | evidence_status | inspection_note |
|---|---|---|

##### Panel C — Questionable cases
*Inspection questions for these:* 
Was the indicator triggered incorrectly?
Was the signal present but missed?

| submission_id | evidence_status | inspection_note |
|---|---|---|
```
===