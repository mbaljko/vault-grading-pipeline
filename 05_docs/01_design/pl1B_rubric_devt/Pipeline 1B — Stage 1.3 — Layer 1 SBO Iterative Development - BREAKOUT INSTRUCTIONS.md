## Stage 1.3 — Layer 1 SBO Iterative Development (Calibration Workflow)

This workflow supports **Layer-1 indicator calibration** for a rubric.

The process separates three roles:

1. **mechanical execution** (running prompts and preparing datasets)  
2. **LLM-assisted diagnostic triage** (finding rows worth inspecting)  
3. **human rubric design decisions**

The LLM helps **locate interesting cases**.  
Humans decide **what those cases mean for the rubric**.

The workflow is organised into three analytic phases:

- dataset analysis
- indicator calibration
- rubric revision

---

## 1. Run the scoring prompt (mechanical)

### Action

Generate the Layer-1 scoring prompt and run it on the calibration dataset.

Derive:

`Layer1_ScoringManifest_$begin:math:display$ASSESSMENT\_ID$end:math:display$_v$begin:math:display$VERSION$end:math:display$`

using the wrapper prompt:

`pl1B_stage13_layer1_indicator_scoring_prompt_wrapper_v01`

located in:

`pl1B_prompt_stage13_Generate Layer 1 Indicator Detection Scoring Prompt.md`

### Output

A scored dataset with rows of the form:

| submission_id | component_id | indicator_id | evidence_status | evaluation_notes |
|---|---|---|---|---|

### Decision

None.  
This stage only produces the raw scoring dataset.

---

## 2. Prepare the scoring dataset (mechanical)

### Action

Reshape the scoring output into two inspection views.

#### Indicator view

| submission_id | I17 | I18 | I19 | I20 | … |
|---|---|---|---|---|---|

Purpose:

- reveal patterns where indicators fire together
- support overlap inspection

#### Row view

| submission_id | indicator_id | evidence_status |
|---|---|---|

Purpose:

- support indicator-by-indicator triage

### Decision

None.  
This stage prepares the dataset for inspection.

---

# DATASET ANALYSIS

Dataset analysis inspects **patterns across indicators** before analysing indicators individually.

---

## 3. Overlap screening (LLM-assisted)

### Purpose

Detect indicators that frequently fire together.

This stage performs **screening**, not interpretation.

### Action

Provide the **indicator view table** to the LLM.

Prompt:

```
Using the indicator evidence table below, identify pairs of indicators that frequently co-occur with evidence or partial_evidence in the same response.

Report the indicator pairs and the number of co-occurrences.
```

### Output

A ranked list of indicator pairs.

Example:

```
I17 + I19 : 23
I17 + I21 : 20
I19 + I21 : 19
```

### Human decision

Record pairs with **unusually high co-occurrence**.

These pairs become **candidate overlap pairs** for inspection later.

Do **not** decide whether indicators should be merged at this stage.

Possible interpretations of overlap include:

- genuine conceptual redundancy
- partial conceptual overlap
- distinct signals frequently expressed together

The purpose is **screening**, not rubric modification.

---

# INDICATOR CALIBRATION

Indicator calibration examines **how individual indicators behave**.

Each indicator is inspected independently.

---

## 4. Indicator triage (LLM-assisted)

### Purpose

Select a **small diagnostic inspection set** for one indicator.

The LLM helps identify rows worth inspecting.

### Action

Filter the dataset for a single indicator:

```
indicator_id = Ix
```

Sort rows by:

```
evidence_status
```

The rows will fall into three clusters:

```
evidence
partial_evidence
little_to_no_evidence
```

Provide the indicator specification and the scored rows to the LLM.

Prompt:

````
PROMPT: Calibration triage

You are helping triage rubric calibration results for a rubric indicator.

Indicator specification:

\<indicator_definition\>  
\<assessment_guidance\>  
\<evaluation_notes\>

Scored rows follow.

Procedure:

1. Examine the full dataset to understand the distribution of evidence_status values.

2. Internally select a diagnostic inspection set consisting of:

- up to 8 rows where evidence_status = evidence  
- up to 8 rows where evidence_status = partial_evidence  
- up to 8 rows where evidence_status = little_to_no_evidence  

3. Choose rows that appear representative or potentially ambiguous.

4. Using only the selected inspection set:

- group responses into clear positives, borderline cases, and questionable cases  
- flag rows that may represent possible misclassifications  

Do not change the scoring.  
Do not rescore the responses.  
Only flag rows for human review.
````

### Output format

Emit results as fenced Markdown.

```
#### Ix — short indicator description

##### Selected inspection set

| submission_id | evidence_status | reason_selected |
|---|---|---|

##### Triage results

##### Panel A — Clear positives

| submission_id | evidence_status | inspection_note |
|---|---|---|

##### Panel B — Borderline cases

| submission_id | evidence_status | inspection_note |
|---|---|---|

##### Panel C — Questionable cases

| submission_id | evidence_status | inspection_note |
|---|---|---|
```

### Decision

None.

The LLM only prepares diagnostic panels.

Human inspection occurs in the next step.

---

## 5. Indicator inspection (human)

### Purpose

Determine whether the indicator behaves correctly.

Inspect Panels A–C produced in the triage stage.

---

### Panel A — Clear positives

Purpose:

Confirm that the indicator fires on **clear examples of the intended analytic signal**.

Inspection question:

```
Does the response clearly contain the analytic signal described by the indicator_definition?
```

### Action

If the signal is **not actually present**, record a **false positive**.

---

### Panel B — Boundary cases

Purpose:

Inspect the **decision boundary** between evidence and non-evidence.

Boundary cases may include responses scored as:

```
evidence
partial_evidence
little_to_no_evidence
```

Inspection questions:

```
Is the analytic signal actually present?
Is the signal weak or incomplete?
Does this response belong in a different indicator?
```

### Action

Record cases revealing:

- unclear indicator definition
- unclear guidance
- indicator boundary ambiguity

---

### Panel C — Questionable cases

Purpose:

Detect **possible misclassifications**.

These may include:

```
false positives
false negatives
```

Inspection questions:

```
Was the indicator triggered incorrectly?
Was the signal present but missed?
```

### Action

Record findings in a diagnostic log.

| indicator | submission | issue | note |
|---|---|---|---|

This log informs rubric revisions later.

---

## 6. Focused overlap inspection (human)

### Purpose

Inspect indicator pairs flagged during **overlap screening**.

Determine whether indicators detect **distinct or redundant signals**.

### Action

For each flagged pair:

```
Ix
Iy
```

Filter rows where both indicators fire.

Example filter:

```
indicator_Ix ∈ {evidence, partial_evidence}
AND
indicator_Iy ∈ {evidence, partial_evidence}
```

Sample **5–10 responses**.

Inspect those responses jointly.

### Inspection questions

```
Do the two indicators detect distinct analytic signals?
Or are they detecting the same conceptual phenomenon?
```

### Possible outcomes

| outcome | action |
|---|---|
| signals clearly distinct | keep both indicators |
| signals partially overlap | narrow indicator definitions |
| signals redundant | merge indicators |

### Decision

Record overlap findings for use in the revision stage.

---

## 7. Instruction clarity test (LLM-assisted)

### Purpose

Determine whether the **indicator instructions are operationally clear**.

Ambiguous instructions often appear in **Panel B boundary cases**.

### Action

Provide the LLM:

- indicator definition  
- assessment guidance  
- evaluation notes  
- borderline responses from Panel B  

Prompt:

```
Explain why this response should be classified as evidence, partial_evidence, or little_to_no_evidence using the indicator instructions.
```

### Interpretation

If multiple plausible classifications appear, the instructions are ambiguous.

### Possible fixes

- tighten `indicator_definition`
- clarify exclusions in `evaluation_notes`
- add examples to `assessment_guidance`

Record required instruction changes.

---

# REVISION

This phase converts diagnostic findings into rubric updates.

---

## 8. Rubric revision (human)

Use findings from:

- indicator inspection
- overlap inspection
- instruction clarity test

### Revise the indicator registry (Section 5.4)

Possible changes:

- merge redundant indicators
- remove indicators that detect no unique signal
- split indicators that capture multiple signals
- narrow overly broad indicator scope

### Revise the evaluation specification (Section 6.1)

Possible changes:

- clarify wording
- add exclusion rules
- add boundary examples
- strengthen detection guidance

### Decision

Produce an updated rubric specification.

---

## 9. Re-run the scoring prompt

### Action

After revising the rubric:

1. regenerate the Layer-1 scoring prompt  
2. run it on the same calibration dataset  
3. compare indicator behaviour

### Decision

Evaluate whether indicator behaviour has stabilised.

If problems remain:

Repeat the calibration cycle beginning at **Step 3**.