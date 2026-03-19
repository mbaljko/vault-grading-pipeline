### Objective
Rapidly review ~38 Indicator Triage (ITP) reports to:
- detect **threshold failures** (false positives / false negatives)
- identify **indicator boundary problems**
- decide **targeted rubric revisions**
Do not re-evaluate full responses. Focus only on **threshold integrity**.
### Operating constraints
- time-bounded: ~2–4 minutes per indicator
- no deep reading of all rows
- prioritise **Panel B and Panel C only**
- treat Panel A as a quick sanity check
### Review sequence (per ITP report)
#### Step 1 — Anchor the indicator (15–20 seconds)
Read only:
- indicator_definition
- assessment_guidance
Ask:
```
What must be explicitly present for this to count as 1?
```
Do not read evaluation_notes in full unless needed.
#### Step 2 — Scan Panel C first (highest yield)
Focus:
```
Panel C = likely false positives / false negatives
```
For each row (quick skim):
- Was this incorrectly marked as evidence? → **false positive**
- Was this incorrectly marked as little_to_no_evidence? → **false negative**
Log mentally:
- FP pattern?
- FN pattern?
Do not read every word—look for **structural cues**.
#### Step 3 — Scan Panel B (threshold boundary)
Focus:
```
Panel B = threshold ambiguity
```
Ask:
- Are these cases consistently ambiguous?
- Would different graders disagree?
Key signal:
```
unclear threshold definition
```
#### Step 4 — Spot patterns (not individual errors)
Do not catalogue rows.
Instead identify:
##### A. False positive pattern
Examples:
- vague mention triggers indicator
- keyword-only activation
- missing structural requirement
##### B. False negative pattern
Examples:
- valid structure not recognised
- alternate phrasing missed
- overly strict guidance
##### C. Boundary ambiguity pattern
Examples:
- mechanism vs stage confusion
- demand vs artefact confusion
- redistribution vs pressure confusion
#### Step 5 — Quick Panel A sanity check (optional, 20–30 sec)
Only check:
- do these clearly meet threshold?
- any obvious false positives hiding here?
If clean, move on.
### Decision output (per indicator)
Write **only this minimal structure**:
```
## <indicator_id>
### Issue type
- FP inflation / FN suppression / boundary ambiguity / no issue
### Pattern observed
- <one sentence describing the recurring issue>
### Cause
- threshold too loose / too strict / definition unclear / guidance ambiguous
### Action
- tighten threshold / relax threshold / clarify definition / add exclusion rule
```
### Pattern → action mapping
Use this mapping directly:

|**observed pattern**|**action**|
|---|---|
|vague mentions counted as present|tighten threshold (require structure)|
|keyword triggers|add exclusion rule|
|valid cases missed|relax threshold OR expand guidance|
|graders would disagree|clarify definition|
|two indicators firing together incorrectly|check overlap / refine boundary|
|mechanism vs stage confusion|add contrast rule|
|demand vs artefact confusion|add negative examples|
### Hard constraints during review
Do not:
- rewrite full indicators
- attempt full re-specification
- fix everything at once
- interpret student intent
- reward “almost correct”
Always enforce:
```
explicit, structurally recognisable evidence only
```
### Time allocation strategy
For 38 indicators:
```
~3 minutes each = ~2 hours total
```
Per indicator:
- 30 sec → read definition
- 60–90 sec → Panel C
- 60 sec → Panel B
- 30 sec → decision note
Move on immediately after logging.
### Batch-level pass (after all 38)
Do a second pass across your notes only.
Identify:
- repeated failure types across indicators
- systematic confusions (e.g., redistribution vs pressure)
- over-triggering clusters
Then apply:
```
global fixes > local fixes
```
### Red flags to prioritise
Stop and act immediately if you see:
- widespread false positives → indicator too loose
- widespread false negatives → indicator too strict
- many Panel B cases → threshold unclear
- same confusion across multiple indicators → system-level issue
### Success condition
You are done when:
- each indicator has a **clear threshold decision**
- each has **one dominant issue (or none)**
- each has a **single actionable revision direction**
Not when every edge case is resolved.
### Working principle
```
You are tuning detection thresholds, not grading quality.
```
If useful, I can convert this into a one-page checklist you can keep open while reviewing.
