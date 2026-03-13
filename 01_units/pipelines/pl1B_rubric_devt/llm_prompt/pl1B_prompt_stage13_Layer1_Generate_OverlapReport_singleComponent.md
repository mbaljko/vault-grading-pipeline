---
prompt_id: generate_indicator_overlap_report
version: v01
stage: calibration
purpose: detect indicator co-occurrence patterns within a single component to support overlap inspection during rubric calibration
status: active
owner: EECS3000W26
input_contract:
  - scored_rows_dataset
input_structure:
  delimiter: "==="
  artefacts:
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
  - descriptive_analysis_only
notes: prompt identifies indicator pairs that frequently co-occur in the same submission where either indicator registers evidence or partial_evidence
---
## PROMPT: Indicator overlap report

You are helping analyse **indicator co-occurrence patterns** in a scored dataset produced during Layer 1 rubric calibration.

The prompt receives **one artefact** after the prompt text using the delimiter `===`.

```
===
Scored rows dataset follows.
===
```

### Purpose

This prompt produces an **Overlap Report** for a single rubric component.

The goal is to identify **indicator pairs that frequently fire together** within the same submission and provide additional descriptive statistics that help humans interpret overlap patterns.

This report helps humans detect possible:

- redundant indicators  
- partially overlapping indicators  
- conceptually distinct indicators that frequently appear together  

The prompt performs **descriptive overlap analysis only**.

This prompt **does not perform scoring**.

Do not reinterpret the rubric.  
Do not change `evidence_status` values.  
Do not rescore the responses.

Only analyse the existing scoring results.

---

### Input integrity requirements

All rows must correspond to **one `component_id` only**.

If multiple `component_id` values appear in the dataset, treat this as an input error and do not proceed.

Each row must contain a valid:

- `submission_id`
- `indicator_id`
- `evidence_status`

Valid `evidence_status` values are:

- evidence  
- partial_evidence  
- little_to_no_evidence  

Do not invent new evidence_status values.

---

## Procedure

### Step 1 — Construct indicator evidence matrix

Using the dataset, internally construct a table with the structure:

| submission_id | indicator_id | evidence_status |

From this table determine which indicators fire with:

```
evidence
or
partial_evidence
```

Indicators with `little_to_no_evidence` must be ignored for activation and overlap calculations.

---

### Step 2 — Compute indicator activation counts

For each `indicator_id`, compute:

```
activation_count
```

This is the number of unique `submission_id` values where the indicator has:

```
evidence
or
partial_evidence
```

This table provides the baseline frequency of each indicator.

---

### Step 3 — Determine active indicators per submission

For each `submission_id`:

1. Identify all indicators where `evidence_status` is:

```
evidence
or
partial_evidence
```

2. Record the set of **active indicators** for that submission.

If a submission contains fewer than two active indicators, it contributes **no overlap pairs**.

---

### Step 4 — Generate indicator pairs

For each submission that has two or more active indicators:

1. Generate all **unordered indicator pairs** from the active indicator set.

Example:

```
I17
I19
I21
```

The generated pairs are:

```
I17 + I19
I17 + I21
I19 + I21
```

Each pair contributes **one co-occurrence** for that submission.

Pairs must be treated as **unordered**.

```
I17 + I19
```

and

```
I19 + I17
```

must be treated as the **same pair**.

---

### Step 5 — Aggregate pair counts

Across the full dataset:

1. Count how many submissions contain each unordered pair.
2. Each pair must appear **only once in the final table**.
3. Duplicate pair rows must not appear.

This produces:

```
co_occurrence_count
```

for each indicator pair.

---

### Step 6 — Compute conditional overlap ratios

For each indicator pair:

```
A + B
```

Compute two ratios:

```
overlap_ratio_A = co_occurrence_count / activation_count(A)
overlap_ratio_B = co_occurrence_count / activation_count(B)
```

These ratios indicate how strongly the indicators are associated.

Values near **1.0** indicate that the indicators almost always appear together.

---

### Step 7 — Identify strongest overlap per indicator

For each indicator:

1. Identify the indicator with which it has the **largest co_occurrence_count**.
2. Record that pair as the indicator’s **strongest overlap**.

---

### Step 8 — Sort pair table

Sort indicator pairs by:

```
co_occurrence_count (descending)
```

If counts are equal, sort alphabetically by the pair.

---

## Output format

Emit the overlap report as Markdown.

```
### Overlap report — component \<component_id\>

#### Indicator activation counts

| indicator_id | activation_count |
|---|---|

#### Pair overlap table

| indicator_pair | co_occurrence_count | overlap_ratio_A | overlap_ratio_B |
|---|---|---|---|

#### Strongest overlap per indicator

| indicator_id | strongest_overlap_indicator | pair_count |
|---|---|---|
```

Output rules:

- Each indicator pair must appear **only once**.
- Only include pairs where `co_occurrence_count ≥ 1`.
- Ratios should be expressed as **decimal values between 0 and 1**.
- No explanatory commentary may appear outside the tables.

---

## Behavioural constraints

- Do not modify the dataset.
- Do not reinterpret `evidence_status`.
- Do not infer rubric meaning.
- Do not propose rubric changes.
- Do not explain conceptual overlap.
- Do not add narrative explanation.

The output must contain **descriptive statistics only**.