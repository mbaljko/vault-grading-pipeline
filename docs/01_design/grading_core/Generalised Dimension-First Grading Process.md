# Generalised Dimension-First Grading Process  
## For Multi-Component Submissions with Multi-Dimensional Rubrics
This document describes a **generalised grading workflow** applicable to any assessment where:
- A submission may contain **one or more components**
- Each component is evaluated using a **multi-dimensional rubric**
- Grading is performed **component-by-component**, not end-to-end per submission
The process is designed to maximise **consistency, calibration stability, and scalability**, especially when grading large cohorts.
## 1. Core Principle: Dimension-First Evaluation
For any component assessed using a multi-dimensional rubric, grading should be conducted:
> **One dimension at a time across all submissions**, rather than one submission at a time across all dimensions.

### Why this approach generalises well
Dimension-first evaluation:
- Reduces cognitive switching costs
- Stabilises boundary decisions across the cohort
- Supports precise calibration for each dimension independently
- Enables dimension-specific flags, disqualifiers, and review rules
- Allows targeted rubric refinement without affecting other dimensions
## 2. Conceptual Model
For an assessment:
- Let **S** = set of submissions  
- Let **C** = set of components within a submission  
- Let **Dᶜ** = set of rubric dimensions for component *c*
The grading workflow operates on:
```
For each component c ∈ C:
    For each dimension d ∈ Dᶜ:
        Perform calibration
        Perform production scoring
```
Optional cross-checks occur after all dimensions of a component are scored.
## 3. Standardised Workflow
### Stage 0 — Prepare Canonical Inputs
See [[Stage 0 — Prepare Canonical Inputs]] for most up-to-date information.  
Below is initial version.

Before grading begins:
1. Extract all responses into a canonical table:
   - One row per:  
     `submission × component × dimension`
2. Ensure each record includes:
   - submission identifier
   - component identifier
   - dimension identifier
   - raw response text
   - metadata (optional: length, timestamps, etc.)
This stage ensures uniform processing regardless of LMS export formats.
## 4. Stage 1 — Dimension-Level Calibration
Calibration is performed independently for each dimension.
### Step 1.1 — Sample Calibration Set
Select a representative subset of responses for the dimension:
- Typically 20–40 samples
- Include variation across quality levels
### Step 1.2 — Construct Calibration Anchors
For each score level:
- Identify exemplar responses
- Include:
  - borderline cases at key boundaries
  - superficially strong but incorrect responses
  - concise yet high-quality responses
### Step 1.3 — Define Dimension Rules
For each dimension, explicitly record:
- Non-negotiables (required elements)
- Disqualifiers (automatic score limits)
- Flags (conditions triggering attention)
- “Needs review” criteria
### Step 1.4 — Freeze Calibration
Once anchors and rules stabilise:
- Freeze the scoring protocol for that dimension
- Avoid modifying criteria during production scoring
## 5. Stage 2 — Production Scoring
For each dimension:
1. Apply scoring across all submissions for that component.
2. Generate structured outputs for each evaluated cell.
### Standard Output Fields
Each scored unit should record:
- score
- evidence_quote
- rationale
- confidence level
- flags
- needs_review indicator
After completion, proceed to the next dimension.
## 6. Stage 3 — Optional Cross-Dimension Consistency Check
After all dimensions of a component are scored, perform a non-rescor­ing consistency pass.
This stage does not modify scores. It only identifies anomalies.
### Example Checks
- High score on extremely short responses
- Uniform high scores with generic language
- Logical contradictions across dimensions
- Missing or malformed responses
These checks may be rule-based or automated.
## 7. Stage 4 — Review Queue Processing
Aggregate all flagged and low-confidence cases into a review queue.
Typical workflow:
- Prioritise “needs_review” cases
- Conduct targeted manual review
- Update scores only where justified
## 8. Stage 5 — Final Coherence Pass (Optional)
Perform a final holistic review across dimensions for each submission.
Purpose:
- Detect systemic inconsistencies
- Identify scoring anomalies
- Confirm overall reliability
This stage focuses on **flagging**, not rescoring.
## 9. Reliability Optimisation Guidelines
For high-volume grading:
- Maintain strict dimension-first sequencing
- Apply conservative “needs_review” thresholds
- Expect a small manual review proportion (typically 5–15%)
- Document all calibration decisions for traceability
## 10. Key Trade-Off
Dimension-first grading sacrifices immediate cross-dimension coherence during initial scoring.
This trade-off is mitigated by:
- explicit consistency checks
- structured review passes
- transparent calibration documentation
## 11. Applicability
This process applies to:
- any number of components per submission
- any rubric structure with multiple dimensions
- any cohort size where calibration consistency is critical
It is independent of subject matter, LMS platform, or grading modality.
## 12. Summary
The generalised grading workflow consists of:
1. Preparing canonical input data
2. Calibrating each dimension independently
3. Scoring dimension-by-dimension across all submissions
4. Conducting consistency checks
5. Reviewing flagged cases
6. Performing optional coherence verification
This approach provides a scalable and reliable framework for evaluating complex, multi-component assessments.
