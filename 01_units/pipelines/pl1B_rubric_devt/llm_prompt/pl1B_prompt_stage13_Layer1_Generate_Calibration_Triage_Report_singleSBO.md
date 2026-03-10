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
## PROMPT: Calibration triage
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

### Purpose
This prompt performs **calibration triage** for a single rubric indicator by selecting a small diagnostic inspection set and grouping those rows into triage panels for human review.
This prompt **does not perform scoring**.
Do not reinterpret the rubric.
Do not change evidence_status values.
Do not rescore the responses.
Only identify rows that may require human inspection.

### Input integrity requirements
All rows in the dataset must correspond to **one indicator_id only**.
If multiple indicator_id values appear in the dataset, treat this as an input error and do not proceed.
Each row must contain a valid `submission_id` and `evidence_status`.

Valid evidence_status values are:
- evidence  
- partial_evidence  
- little_to_no_evidence

Do not invent new evidence_status values.

### Procedure

#### Step 1 — Partition the dataset
Partition the full dataset into three groups using the recorded `evidence_status` values:
- evidence  
- partial_evidence  
- little_to_no_evidence  

Do not reinterpret or modify these labels.

#### Step 2 — Construct the diagnostic inspection set
From each partition, select diagnostic rows as follows:

- up to **8 rows** where `evidence_status = evidence`
- up to **8 rows** where `evidence_status = partial_evidence`
- up to **8 rows** where `evidence_status = little_to_no_evidence`

**Enforcement rule for row limits:**

If a partition contains more than 8 rows:
- Use the dataset order exactly as provided.
- Keep only the first 8 rows in that partition.
- Ignore all remaining rows in that partition.
- Do not inspect, analyse, or reference rows beyond these first 8.

The inspection set therefore contains **at most 24 rows total**.

The limit of 8 rows applies **independently to each evidence_status category**.

If a category contains fewer than 8 rows, include all available rows.

When selecting rows, include a mix of:
- clearly representative examples
- potentially ambiguous examples

Do not select only ambiguous rows.

#### Step 3 — Declare the inspection set
The **Selected inspection set table must list every sampled row**.
This table is the **registry of rows** used for the remainder of the task.

All rows appearing anywhere later in the output must come from this registry.
No additional rows from the dataset may be introduced.

#### Step 4 — Perform triage grouping
Using **only the rows listed in the Selected inspection set**, group them into the following diagnostic panels:

- Panel A — Clear positives  
- Panel B — Borderline cases  
- Panel C — Questionable cases  

These panels are **diagnostic groupings only**.  
They do **not** modify the recorded evidence_status values.

Panels must reflect triage interpretation only.

#### Structural integrity rules
Panels A–C must form a **strict partition of the Selected inspection set**.

The following conditions must hold:

1. Every row listed in the Selected inspection set must appear in **exactly one panel**.
2. No row may appear in more than one panel.
3. No new rows may appear in any panel.
4. The union of rows appearing in Panels A–C must exactly match the rows listed in the Selected inspection set.
5. Each row must include the **exact submission_id from the dataset**. Do not alter identifiers.

Do not report excluded rows, omitted rows, duplicate rows, or partition violations inside any panel.
If a row is excluded, it must not appear anywhere in the panel tables.
If a row has already been assigned to a panel, do not mention it again.
### Notes for inspection reasoning
Inspection notes should briefly explain **why the row appears in that panel**.

Do not restate the rubric definition.
Do not provide general rubric commentary.

Inspection notes should describe the diagnostic reason the row may be:
- clearly aligned with the indicator
- weak or incomplete
- potentially misclassified

### Output format

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

### Behavioural constraints
- Do not modify the dataset.
- Do not add or remove rows beyond the inspection set selection.
- Do not reinterpret or override evidence_status.
- Do not rescore responses.
- Only flag rows for human review through panel placement and inspection notes.

===