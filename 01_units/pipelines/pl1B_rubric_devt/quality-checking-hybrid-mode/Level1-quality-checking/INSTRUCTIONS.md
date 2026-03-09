## INSTRUCTIONS - Section 1.3 Evaluation questions
The most efficient workflow is to treat the process as **three nested passes**:
1. mechanical scanning (LLM or tooling)  
2. targeted human inspection  
3. rubric revision decision  
The key idea is that the LLM should **help you find the interesting rows**, but **you decide what they mean**.
Below is a workflow that works well for **Layer-1 indicator calibration**.
### A compact workflow summary
```
1 run scoring prompt
2 LLM triages suspicious rows
3 construct indicator diagnostic panels
4 human inspects panels and flagged cases
5 LLM detects indicator overlap patterns
6 human decides rubric revisions
7 revise Section 5.4 or 6.1
8 re-run scoring prompt
```
## 1. Prepare the scoring dataset (mechanical)
After running the Stage 1 scoring prompt you will have a table like:

| submission_id | component_id | indicator_id | evidence_status | evaluation_notes |
|---|---|---|---|---|
Reshape it (pivot or group) so you can inspect patterns easily.
Two useful tables:
**Indicator view**

| submission_id | I17 | I18 | I19 | I20 | … |
|---|---|---|---|---|---|
**Row view**

| submission_id | indicator_id | evidence_status |
|---|---|---|
You will use the **row view** for indicator inspection.
The LLM is not needed yet.
## 2. Indicator-level triage (LLM-assisted)
For each indicator:
1. Filter rows where `indicator_id = Ix`
2. Sort by `evidence_status`
You now have three clusters:
```
evidence
partial_evidence
little_to_no_evidence
```
Ask the LLM to do **triage**, not judgement.
Example prompt to the LLM:
```
You are helping triage rubric calibration results for a rubric indicator.
Indicator specification:
<indicator_definition>
<assessment_guidance>
<evaluation_notes>
Scored rows follow.
Procedure:
1. Examine the full dataset to understand the distribution of `evidence_status` values.
2. Internally select a diagnostic inspection set consisting of:
   - up to 8 rows where `evidence_status = evidence`
   - up to 8 rows where `evidence_status = partial_evidence`
   - up to 8 rows where `evidence_status = little_to_no_evidence`
   Choose rows that appear representative or potentially ambiguous.
3. Using **only the selected inspection set**:
   - group the responses into **clear positives**, **borderline cases**, and **questionable cases**
   - flag rows that may represent **possible misclassifications** (false positives or false negatives)
Do not change the scoring.  
Do not rescore the responses.  
Only flag rows for human review.
### Output format
Emit as fenced md. Format the results for inspection using the following structure.
#### `<indicator_id> — <short_indicator_description>`
##### Selected inspection set
List the rows chosen during internal sampling.

| submission_id | evidence_status | reason_selected |
|---|---|---|
| <sid> | <status> | brief explanation (representative / ambiguous / boundary case / suspicious pattern) |
##### Triage results
##### Panel A — Clear positives
Responses where the indicator signal appears clearly present and the assigned `evidence_status` appears appropriate.

| submission_id | evidence_status | inspection_note |
|---|---|---|
| <sid> | <status> | brief explanation of why the signal clearly matches the indicator |
##### Panel B — Borderline cases
Responses where the signal appears weak, ambiguous, or near the boundary between categories.

| submission_id | evidence_status | inspection_note |
|---|---|---|
| <sid> | <status> | brief explanation of the ambiguity or boundary issue |
##### Panel C — Questionable cases
Responses that may represent **possible misclassifications**, such as potential false positives or false negatives.

| submission_id | evidence_status | inspection_note |
|---|---|---|
| <sid> | <status> | explanation of why the classification may be incorrect |
Notes:
- Only include rows from the **selected inspection set** in the panels.
- A row may appear in only **one panel**.
- Do not rewrite or reinterpret the rubric.
- Keep inspection notes concise and focused on the indicator signal.
- Do not produce narrative summaries outside the defined sections.
```
supply the indicator specification and the response text
Output should look like:
```
clear positives: [sid 12, 18, 21]
borderline: [sid 5, 14]
questionable: [sid 9]
```
Now you have a **small inspection set**.
## 3. Inspect indicator diagnostic panels (human)
For each indicator `Ix`, inspect the diagnostic panels produced by the LLM triage step.
The triage output should contain three panels.

| panel | purpose |
|---|---|
| Panel A | confirm true positives |
| Panel B | inspect boundary cases |
| Panel C | detect possible misclassifications |
These panels represent **representative diagnostic samples** drawn from the scoring dataset.
### Panel A — clear positives
Purpose:  
Confirm that the indicator fires on **clear examples of the intended analytic signal**.
Inspection questions:
```
Does the response clearly contain the analytic signal described by the indicator_definition?
```
If not → possible **false positive**.
### Panel B — boundary cases
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
These responses reveal whether the **indicator definition or guidance is ambiguous**.
### Panel C — questionable cases
Purpose:  
Surface **possible misclassifications**.
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
Record suspected misclassifications for later rubric revision.
### Inspection log
Record findings in a small diagnostic log.

| indicator | submission | issue | note |
|---|---|---|---|
| I19 | 14 | boundary | signal present but weak |
| I19 | 9 | false positive | fairness language but not participation |
| I19 | 22 | false negative | distributive signal present but missed |
## 4. Indicator overlap detection (LLM-assisted)
Some indicators may detect **very similar analytic signals**.  
When this happens they will frequently fire together in the same responses.
This step detects those patterns.
Use the **Indicator view** pivot table.

| submission_id | I17 | I18 | I19 | I20 | … |
|---|---|---|---|---|---|
Ask the LLM to compute **indicator co-occurrence patterns**.
Example prompt:
```
Using the indicator evidence table, identify pairs of indicators that frequently co-occur with evidence or partial_evidence in the same response.
Report the indicator pairs and the number of co-occurrences.
```
Example output:
```
I19 + I20 : 11
I21 + I23 : 8
```
### Panel D — overlap inspection
For any indicator pair that frequently co-occurs, construct **Panel D**.

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
- indicators detect distinct signals → keep both
- indicators partially overlap → narrow definitions
- indicators detect the same signal → merge indicators
## 5. Instruction clarity test (LLM-assisted)
To test whether the **evaluation instructions are operationally clear**, examine borderline responses.
Provide the LLM:
- the indicator definition
- the assessment guidance
- several responses from **Panel B**
Prompt example:
```
Explain why this response should be classified as evidence, partial_evidence, or little_to_no_evidence using the indicator instructions.
```
If the LLM produces **multiple plausible interpretations**, the indicator instructions may be ambiguous.
Typical fixes:
- tighten `indicator_definition`
- clarify exclusions in `evaluation_notes`
- add examples to `assessment_guidance`
## 6. Revision step (human)
Based on the inspection results, decide whether to revise:
### Indicator registry (Section 5.4)
Possible revisions:
- merge indicators
- remove redundant indicators
- split ambiguous indicators
- adjust indicator scope
### Evaluation specification (Section 6.1)
Possible revisions:
- clarify wording
- strengthen detection rules
- add exclusions
- add examples
## 7. Re-run the scoring prompt
After revising the rubric specification:
```
generate updated scoring prompt
run on calibration dataset
compare results
```
Repeat the calibration cycle until behaviour stabilises.
## What the LLM should and should not do
LLM should assist with:
- triaging interesting responses
- clustering diagnostic cases
- computing indicator co-occurrence patterns
- identifying potential ambiguities
LLM should **not decide**:
- whether an indicator is conceptually valid
- whether indicators should be merged
- whether the rubric reflects the assignment's analytic goals
Those are **rubric design decisions made by the human evaluator**.
