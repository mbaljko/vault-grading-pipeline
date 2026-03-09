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
You are helping triage rubric calibration results.
For indicator I19 below:
1. group the responses into clear positives, borderline cases, and questionable cases
2. flag rows that look suspicious (possible false positives or false negatives)
3. do not change the scoring — only flag cases for human review
```
Output should look like:
```
clear positives: [sid 12, 18, 21]
borderline: [sid 5, 14]
questionable: [sid 9]
```
Now you have a **small inspection set**.
## 3. Construct indicator diagnostic panels (mechanical + LLM-assisted)
For each indicator `Ix`, construct a **4-panel diagnostic table** containing representative responses.

| panel | evidence_status | purpose |
|---|---|---|
| A | evidence | confirm true positives |
| B | partial_evidence | inspect boundary cases |
| C | little_to_no_evidence (LLM-flagged) | detect false negatives |
| D | evidence with another indicator | detect indicator overlap |
Typical panel size:
```
5–10 responses per panel
```
The panels should be assembled as follows.
### Panel A — strong detections
Filter:
```
indicator_id = Ix
evidence_status = evidence
```
Purpose:
Confirm that the indicator fires on **clear examples of the intended analytic signal**.
### Panel B — boundary cases
Filter:
```
indicator_id = Ix
evidence_status = partial_evidence
```
Purpose:
Inspect the **decision boundary** between evidence and non-evidence.
### Panel C — potential false negatives
Filter:
```
indicator_id = Ix
evidence_status = little_to_no_evidence
```
Then ask the LLM:
```
From these responses, identify any that appear to contain the signal described by the indicator_definition.
```
Purpose:
Surface **missed detections**.
### Panel D — overlap detection
Identify indicators that frequently co-occur with `Ix`.
Filter rows where:
```
indicator_id = Ix AND indicator_j ∈ {evidence, partial_evidence}
```
Purpose:
Detect **indicator overlap or redundancy**.
## 4. Human inspection pass (your role)
Inspect the panels and flagged cases.
For each inspected response ask:
**Detection check**
```
Is the intended analytic signal actually present?
```
If not → **false positive**
If present but missed → **false negative**
**Boundary check**
```
Does this belong in this indicator or a different one?
```
**Instruction clarity check**
```
Did the evaluation instructions make the correct decision ambiguous?
```
Record findings in a small log.
Example:

| indicator | submission | issue | note |
|---|---|---|---|
| I19 | 14 | borderline | participation language implied but not explicit |
| I19 | 9 | false positive | accessibility mentioned but not about participation |
## 5. Overlap detection (LLM-assisted)
Indicators that fire together frequently may overlap.
Have the LLM compute **co-occurrence**.
Example prompt:
```
Using the indicator evidence table, identify pairs of indicators that frequently co-occur with evidence or partial_evidence in the same response.
Report the pairs and counts.
```
Example result:
```
I19 + I20 : 11 co-occurrences
I21 + I23 : 8 co-occurrences
```
Now inspect those cases.
Questions you ask:
```
Are these actually distinct analytic signals?
Or are they two ways of detecting the same thing?
```
Possible outcomes:
- keep both (signals are conceptually distinct)
- narrow one indicator definition
- merge indicators
- move signal to another indicator
## 6. Instruction clarity test (LLM-assisted)
To check whether the **evaluation instructions are operationally clear**, run a simple test.
Give the LLM:
- the indicator definition  
- several borderline responses  
Ask:
```
Explain why this response should be classified as evidence, partial_evidence, or little_to_no_evidence using the indicator instructions.
```
If the LLM produces **multiple plausible interpretations**, the instructions are unclear.
Typical fixes:
- tighten `indicator_definition`
- clarify exclusions in `evaluation_notes`
- add examples to `assessment_guidance`
## 7. False-negative sweep (LLM-assisted)
Another useful LLM pass:
```
Look at responses where evidence_status = little_to_no_evidence for I19.
Identify any responses that appear to contain the signal described by the indicator_definition.
```
This catches **missed detections**.
You inspect those manually.
## 8. Revision step (human)
You now decide whether to change:
**Indicator registry (Section 5.4)**
Possible changes:
- merge indicators
- remove redundant indicators
- split ambiguous indicators
or
**Evaluation specification (Section 6.1)**
Typical edits:
- clarify wording
- add exclusions
- specify stronger evidence requirements
## 9. Re-run the scoring prompt
After revision:
```
generate new scoring prompt
run on calibration dataset
compare behaviour
```
Repeat the cycle until behaviour stabilises.
## What the LLM should and should not do
LLM should help with:
- clustering cases  
- finding suspicious rows  
- computing co-occurrence patterns  
- suggesting ambiguous interpretations  
LLM should **not** decide:
- whether an indicator is conceptually valid  
- whether signals should be merged  
- whether the rubric reflects the assignment’s analytic goals  
Those are **rubric design decisions**.
