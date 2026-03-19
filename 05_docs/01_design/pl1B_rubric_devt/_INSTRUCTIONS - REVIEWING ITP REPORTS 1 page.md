### Layer 1 ITP triage — compact checklist
#### Objective
- detect threshold failures (FP / FN)  
- identify boundary problems  
- decide one targeted revision  
#### Stop rules
- For each indicator, identify **the single most important failure mode** (not all probs)
- Commit to **one concrete change direction** per indicator only (not multiple)
- do not analyse all rows, just on obvious patterns/repeated structures 
- do not rewrite full indicator, only decide what needs to change
#### Per-indicator workflow (≈ 3 min)
1. Define threshold — identify what must be explicitly present for 1
2. Scan Panel C — identify FP / FN patterns
3. Scan Panel B — check for ambiguity and disagreement risk
4. Select pattern — choose one dominant issue
5. Classify cause — determine source of failure
6. Assign action — choose one fix
7. Check Panel A (optional) — confirm clear positives are valid
#### Pattern classification - Issue Types(choose one)

| Code               | Meaning                                |
| ------------------ | -------------------------------------- |
| FP inflation       | weak / vague signals marked as present |
| FN suppression     | valid signals missed                   |
| Boundary ambiguity | inconsistent threshold interpretation  |
| No issue           | threshold working as intended          |
#### Cause classification (choose one)

| Cause | Description |
|---|---|
| Threshold too loose | vague or minimal signals pass |
| Threshold too strict | valid variants excluded |
| Definition unclear | signal not well specified |
| Guidance ambiguous | instructions allow multiple interpretations |
<div class="page-break" style="page-break-before: always;"></div>

#### Action mapping (choose one)

| Pattern            | Action                                         |
| ------------------ | ---------------------------------------------- |
| FP inflation       | tighten threshold (require explicit structure) |
| FN suppression     | relax threshold (allow valid variants)         |
| Boundary ambiguity | clarify definition                             |
| Keyword-trigger FP | add exclusion rule                             |
#### Fast recognition cues

| Cue | Interpretation | Action |
|---|---|---|
| vague mention | FP | tighten |
| keyword only | FP | add exclusion |
| missed valid structure | FN | relax |
| mixed interpretations | boundary | clarify |
#### Output note template

| Field | Entry |
|---|---|
| Indicator | \<indicator_id\> |
| Issue type |  |
| Pattern |  |
| Cause |  |
| Action |  |
#### Batch scan (after all indicators)

| Signal | Action |
|---|---|
| repeated FP across indicators | global threshold tightening |
| repeated confusion type | add shared contrast rule |
#### Core rule
- Layer 1 = explicit, sufficient, structurally recognisable signal only  
- anything less = 0  
