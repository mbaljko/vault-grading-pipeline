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

The goal is to identify:

- indicator pairs that frequently fire together  
- indicator pairs with **very high conditional overlap (≥ 0.85)**  
- **clusters of indicators** where all pairwise conditional overlaps are ≥ 0.85  

These diagnostics help humans detect possible:

- redundant indicators  
- partially overlapping indicators  
- tightly coupled indicator clusters  

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

Using the dataset, internally construct a table:

| submission_id | indicator_id | evidence_status |

Determine which indicators fire with:

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

---

### Step 3 — Determine active indicators per submission

For each `submission_id`:

1. Identify indicators with

```
evidence
or
partial_evidence
```

2. Record the set of **active indicators**.

If a submission contains fewer than two active indicators, it contributes **no overlap pairs**.

---

### Step 4 — Generate indicator pairs

For each submission with two or more active indicators:

Generate all **unordered indicator pairs**.

Example:

```
I17
I19
I21
```

Pairs:

```
I17 + I19
I17 + I21
I19 + I21
```

Pairs must be treated as **unordered**.

```
I17 + I19
```

and

```
I19 + I17
```

are the same pair.

Each pair contributes **one co-occurrence** for that submission.

---

### Step 5 — Aggregate pair counts

Across the dataset:

1. Count the number of submissions containing each pair.
2. Ensure each unordered pair appears **only once**.

This produces:

```
co_occurrence_count
```

for each pair.

---

### Step 6 — Compute conditional overlap ratios

For each pair:

```
A + B
```

Compute:

```
overlap_ratio_A = co_occurrence_count / activation_count(A)
overlap_ratio_B = co_occurrence_count / activation_count(B)
```

Values near **1.0** indicate the indicators almost always appear together.

---

### Step 7 — Identify high-overlap pairs

A pair qualifies as a **high-overlap pair** if:

```
overlap_ratio_A ≥ 0.85
AND
overlap_ratio_B ≥ 0.85
```

These pairs indicate extremely strong association between indicators.

---

### Step 8 — Identify high-overlap clusters

Identify **clusters of indicators** where:

```
all pairwise conditional overlaps ≥ 0.85
```

That is, for every pair within the cluster:

```
overlap_ratio_A ≥ 0.85
AND
overlap_ratio_B ≥ 0.85
```

Clusters must contain **at least three indicators**.

Clusters represent tightly coupled indicators that frequently fire together.

Indicators may appear in **only one cluster**.

---

### Step 9 — Identify strongest overlap per indicator

For each indicator:

1. Identify the indicator with which it has the **largest co_occurrence_count**.
2. Record that pair as the indicator’s strongest overlap.

---

### Step 10 — Sort pair table

Sort pairs by:

```
co_occurrence_count (descending)
```

If counts tie, sort alphabetically by pair.

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

#### High-overlap pairs (conditional overlap ≥ 0.85)

| indicator_pair | overlap_ratio_A | overlap_ratio_B |
|---|---|---|

#### High-overlap clusters (all pairwise conditional overlap ≥ 0.85)

Cluster 1:
I25  
I27  
I28  
I29  

Cluster 2:
I31  
I32  

#### Strongest overlap per indicator

| indicator_id | strongest_overlap_indicator | pair_count |
|---|---|---|
```

Output rules:

- Each pair must appear **only once**.
- Only include pairs with `co_occurrence_count ≥ 1`.
- Ratios must be decimals between **0 and 1**.
- Do not include commentary outside the tables.

---

## Behavioural constraints

- Do not modify the dataset.
- Do not reinterpret `evidence_status`.
- Do not infer rubric meaning.
- Do not propose rubric changes.
- Do not explain conceptual overlap.
- Do not add narrative explanation.

The output must contain **descriptive statistics only**.