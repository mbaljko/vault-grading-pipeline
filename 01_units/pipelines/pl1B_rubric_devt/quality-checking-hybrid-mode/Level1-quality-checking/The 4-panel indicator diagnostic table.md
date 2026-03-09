### The 4-panel indicator diagnostic table
This is a simple inspection structure that lets you assess almost all of the Stage 1.3 evaluation questions very quickly. You build it **for one indicator at a time**.
For indicator Ix, construct four small panels containing representative responses.

|**panel**|**evidence_status**|**purpose**|
|---|---|---|
|A|evidence|confirm true positives|
|B|partial_evidence|inspect borderline cases|
|C|little_to_no_evidence (LLM-flagged possible misses)|detect false negatives|
|D|evidence (co-occurring with another indicator)|detect overlap|
Each panel typically contains **5–10 responses**.
This lets you visually inspect whether the indicator behaves coherently.
### How to construct the panels
#### Panel A — clear detections
Filter:
```
indicator_id = Ix
evidence_status = evidence
```
Sort by:
```
response_wc DESC
```
Select ~5–10 responses.
Purpose:
Check whether the indicator is firing on **genuinely strong signals**.
Questions you ask:
```
Do these clearly express the analytic signal?
Are they consistent with the indicator_definition?
```
If many look weak → the indicator is **too permissive**.
#### Panel B — boundary cases
Filter:
```
indicator_id = Ix
evidence_status = partial_evidence
```
Purpose:
Understand the **decision boundary**.
Questions:
```
Do these really belong in partial_evidence?
Should some actually be evidence?
Should some be little_to_no_evidence?
```
If the boundary is unclear → revise **assessment_guidance**.
#### Panel C — potential false negatives
Filter:
```
indicator_id = Ix
evidence_status = little_to_no_evidence
```
Ask the LLM:
```
From these responses, identify any that appear to contain the signal described by the indicator_definition.
```
Inspect those rows.
Purpose:
Find **missed detections**.
Questions:
```
Is the signal actually present?
If yes, why did the prompt miss it?
```
Typical fixes:
- broaden assessment_guidance
- add explicit examples
- clarify signal wording
#### Panel D — overlap detection
First compute indicator co-occurrence.
Example table:

|**indicator pair**|**co-occurrence count**|
|---|---|
|I19 + I20|11|
|I21 + I23|8|
For indicator Ix, filter:
```
indicator_id = Ix
evidence_status ∈ {evidence, partial_evidence}
AND indicator_j ∈ {evidence, partial_evidence}
```
Inspect ~5 rows.
Purpose:
Detect **indicator overlap**.
Questions:
```
Are both signals truly present?
Or are both indicators detecting the same signal?
```
Possible outcomes:

|**outcome**|**action**|
|---|---|
|signals distinct|keep both indicators|
|signals redundant|merge indicators|
|signals partially overlapping|narrow indicator_definition|
### Visual example layout
You literally arrange the panels like this during inspection.

|**Panel A**|**Panel B**|
|---|---|
|strong positives|borderline|

|**Panel C**|**Panel D**|
|---|---|
|missed detections|overlap|
This layout helps your brain see patterns very quickly.
### What each panel answers
Your Stage 1.3 evaluation questions map cleanly to the panels.

|**evaluation question**|**panel**|
|---|---|
|indicators detect intended signals|A|
|false positives|A|
|boundary clarity|B|
|false negatives|C|
|indicator overlap|D|
|instruction clarity|B + C|
### How the LLM fits into the workflow
LLM assists in constructing the panels.
Good LLM tasks:
```
identify possible false negatives
identify borderline cases
identify indicator co-occurrence
cluster responses with similar signals
```
But the judgement remains yours.
### Typical time per indicator
Once the panels are built:

|**step**|**time**|
|---|---|
|Panel inspection|~3 minutes|
|Notes|~1 minute|
|Decision|~1 minute|
So you can review **8 indicators in ~40 minutes**.
### Optional improvement: an “indicator confusion map”
After doing the panels for all indicators, compute:

|**indicator_i**|**indicator_j**|**co-occurrence rate**|
|---|---|---|
This reveals hidden structural overlap between indicators.
It often reveals things like:
```
accessibility participation vs accommodation indicators firing together
systemic harm vs non-neutral system indicators firing together
```
Those are exactly the places where rubric refinements usually occur.
If you’d like, I can also show you **one additional diagnostic table that is even more powerful than the 4-panel method** for large indicator sets. It lets you see **the entire Layer 1 behaviour at once**.
