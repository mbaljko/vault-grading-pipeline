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
