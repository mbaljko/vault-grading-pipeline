### Layer 1 ITP triage — rapid review checklist
#### Objective
Rapidly review Indicator Triage (ITP) reports to:
- detect threshold failures (false positives / false negatives)  
- identify indicator boundary problems  
- decide targeted rubric revisions  
#### 1. Anchor the threshold (≤ 20 sec)
```text
What must be explicitly present for this to count as 1?
```
- require explicit, structurally recognisable evidence  
- ignore nuance, quality, or partiality  
#### 2. Panel C (priority)
```text
Look for: false positives / false negatives
```
For each row (quick skim):
- FP → triggered on vague / incomplete signal  
- FN → valid structure present but missed  
Record mentally:
```text
FP pattern?  FN pattern?
```
#### 3. Panel B (boundary check)
```text
Look for: threshold ambiguity
```
Ask:
- would two graders disagree here?  
- is “sufficient evidence” unclear?  
If yes:
```text
boundary problem
```
#### 4. Pattern detection (choose one only)
```text
[ ] FP inflation
[ ] FN suppression
[ ] boundary ambiguity
[ ] no issue
```
#### 5. Cause classification
```text
[ ] threshold too loose
[ ] threshold too strict
[ ] definition unclear
[ ] guidance ambiguous
```
<div class="page-break" style="page-break-before: always;"></div>


#### 6. Action (choose one)
```text
[ ] tighten threshold (require explicit structure)
[ ] relax threshold (allow valid variants)
[ ] clarify definition (sharpen wording)
[ ] add exclusion rule (block false positives)
```
#### 7. Optional quick sanity check (Panel A)
```text
Do these clearly meet threshold?
```
- if yes → move on  
- if not → FP issue  
### Output note template
```markdown
## \<indicator_id\>
Issue type:
- 
Pattern:
- 
Cause:
- 
Action:
- 
```
### Fast pattern recognition cues
```text
vague mention → FP → tighten
keyword-only → FP → add exclusion
missed valid structure → FN → relax
mixed interpretations → boundary → clarify
```
### Stop rules
Move on when:
- one issue identified  
- one action selected  
Do not:
- analyse every row  
- resolve all edge cases  
- rewrite the full indicator  
### Global scan (after all indicators)
```text
same issue repeating → system-level fix
```
Examples:
- multiple indicators over-triggering → global threshold tightening  
- repeated confusion types → add shared contrast rule  
### Core rule
```text
Layer 1 = explicit, sufficient, structurally recognisable signal only
```
Anything less = 0
