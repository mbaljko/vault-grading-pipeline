## Stage 1.3 — Layer 1 SBO Iterative Development - BREAKOUT INSTRUCTIONS
The most efficient workflow is to treat the process as **three nested passes**:
1. mechanical scanning (LLM or tooling)  
2. targeted human inspection  
3. rubric revision decision  
The key idea is that the LLM should **help you find the interesting rows**, but **you decide what they mean**.
The workflow below is designed for **Layer-1 indicator calibration** and separates:
- **indicator behaviour inspection**
- **indicator overlap detection**
- **rubric revision decisions**
### A compact workflow summary
```
1 run scoring prompt
2 prepare scoring dataset
3 run early overlap scan
4 LLM triages indicators
5 human inspects Panels A–C
6 inspect Panel D for flagged overlap pairs
7 run instruction clarity test
8 human decides rubric revisions
9 revise Section 5.4 or 6.1
10 re-run scoring prompt
```
### 1. Prepare the scoring dataset (mechanical)
After running the Stage-1 scoring prompt you will have a table like:

| submission_id | component_id | indicator_id | evidence_status | evaluation_notes |
|---|---|---|---|---|
Reshape the dataset so it can be inspected easily.
Two useful views are recommended.
##### Indicator view

| submission_id | I17 | I18 | I19 | I20 | … |
|---|---|---|---|---|---|
This view makes it easy to inspect **indicator overlap patterns**.
##### Row view

| submission_id | indicator_id | evidence_status |
|---|---|---|
This view is used for **indicator-by-indicator inspection**.
No LLM assistance is required at this stage.
### 2. Early overlap scan (LLM-assisted)
Before inspecting indicators individually, perform a **quick overlap scan**.
Purpose:
- detect indicators that frequently fire together  
- identify potential redundancy  
- identify indicator bundles that should be inspected jointly  
Ask the LLM:
```
Using the indicator evidence table below, identify pairs of indicators that frequently co-occur with evidence or partial_evidence in the same response.
Report the indicator pairs and the number of co-occurrences.
```
Example output:
```
I17 + I19 : 23
I17 + I21 : 20
I19 + I21 : 19
```
Important:
High co-occurrence does **not automatically mean indicators should be merged**.
High overlap may indicate:
- true redundancy  
- partial conceptual overlap  
- coherent conceptual framing expressed together by students  
The purpose of this step is **screening**, not decision-making.
Record pairs that appear unusually frequent.
These pairs will later be inspected using **Panel D**.
### 3. Indicator-level triage (LLM-assisted)
Inspect indicators **one at a time**.
For each indicator:
1. Filter rows where
```
indicator_id = Ix
```
2. Sort rows by
```
evidence_status
```
You now have three clusters:
```
evidence
partial_evidence
little_to_no_evidence
```
Ask the LLM to perform **triage**, not judgement.
Example prompt:

````
PROMPT: Calibration triage
You are helping triage rubric calibration results for a rubric indicator.
Indicator specification:
<indicator_definition>
<assessment_guidance>
<evaluation_notes>


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
```
##### Output format
Emit results as fenced Markdown.
```
#### <indicator_id> — <short_indicator_description>
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
````
Notes:
- Only include rows from the **selected inspection set**
- A row may appear in only **one panel**
- Do not reinterpret the rubric
### 4. Inspect indicator diagnostic panels (human)
For each indicator, inspect the triage output.

| panel | purpose |
|---|---|
| Panel A | confirm true positives |
| Panel B | inspect decision boundary |
| Panel C | detect possible misclassifications |
##### Panel A — clear positives
Purpose:
Confirm that the indicator fires on **clear examples of the intended analytic signal**.
Inspection question:
```
Does the response clearly contain the analytic signal described by the indicator_definition?
```
If not → possible **false positive**.
##### Panel B — boundary cases
Purpose:
Inspect the **decision boundary between evidence and non-evidence**.
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
Does this belong in a different indicator?
```
These cases reveal **definition or guidance ambiguity**.
##### Panel C — questionable cases
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
Record findings in a diagnostic log.

| indicator | submission | issue | note |
|---|---|---|---|
### 5. Focused overlap inspection (Panel D)
For indicator pairs flagged during the **early overlap scan**, perform a joint inspection.
Construct **Panel D**.

| panel | purpose |
|---|---|
| Panel D | inspect potential indicator overlap |
Filter rows where both indicators fire.
Example filter:
```
indicator_Ix ∈ {evidence, partial_evidence}
AND
indicator_Iy ∈ {evidence, partial_evidence}
```
Sample 5–10 responses.
Inspection questions:
```
Are these actually distinct analytic signals?
Or are the indicators detecting the same conceptual phenomenon?
```
Possible outcomes:
- signals are distinct → keep both indicators
- signals partially overlap → narrow definitions
- signals are redundant → merge indicators
### 6. Instruction clarity test (LLM-assisted)
To test whether **evaluation instructions are operationally clear**, examine responses from **Panel B**.
Provide the LLM:
- the indicator definition  
- the assessment guidance  
- borderline responses  
Prompt example:
```
Explain why this response should be classified as evidence, partial_evidence, or little_to_no_evidence using the indicator instructions.
```
If multiple plausible interpretations appear, the instructions are likely ambiguous.
Typical fixes:
- tighten `indicator_definition`
- clarify exclusions in `evaluation_notes`
- add examples to `assessment_guidance`
### 7. Revision step (human)
Based on the inspection results, revise the rubric specification.
##### Indicator registry (Section 5.4)
Possible changes:
- merge indicators  
- remove redundant indicators  
- split ambiguous indicators  
- narrow indicator scope  
##### Evaluation specification (Section 6.1)
Possible changes:
- clarify wording  
- add exclusions  
- strengthen detection rules  
- add examples  
### 8. Re-run the scoring prompt
After revising the rubric specification:
```
generate updated scoring prompt
run on calibration dataset
compare behaviour
```
Repeat the calibration cycle until behaviour stabilises.
### What the LLM should and should not do
LLM should assist with:
- triaging diagnostic rows  
- clustering cases  
- detecting overlap patterns  
- identifying ambiguous interpretations  
LLM should **not decide**:
- whether indicators are conceptually valid  
- whether indicators should be merged  
- whether the rubric reflects the assignment's analytic goals  
These are **human rubric design decisions**.
