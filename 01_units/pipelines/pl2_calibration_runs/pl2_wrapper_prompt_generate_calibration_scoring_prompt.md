this document sets out a WRAPPER PROMPT - which is used to create tightly bounded prompt which can to be used to assign provisional scores.

# .
```
BEGIN GENERATION
```

# .
```
### pl2_wrapper_prompt, to generate_calibration_scoring_prompt

Wrapper prompt: Generate a tightly bounded provisional scoring prompt (a prompt to be used to accomplish scoring via an API call or via interactive UI).
The resultant prompt can be used to assign provisional scoring for a set of student submissions for one assignment component.    
This scoring is intended for diagnostic use, as part of calibration stage.
This resultant assigned scores will have extracted analytic structure.

### Purpose
This wrapper prompt generates a **single, repeatable, tightly bounded scoring prompt** that can be reused to assign **provisional scores for exactly one rubric dimension** over a fixed-format calibration set.

Its purpose is to:
- produce a **dimension-specific scoring prompt** that scores *only* the target dimension,
- enforce the provided **indicator checklist** and **boundary rules** as the sole scoring logic,
- ensure the resulting scoring prompt is **diagnostic and non-authoritative** (used to detect drift and stress-test rules),
- ensure the scoring prompt produces **structured outputs** suitable for inspection, comparison, and rule refinement,
- ensure the scoring prompt **extracts and surfaces analytic structure implicit in the supplied materials** (facets, quality checks, boundary gates),
- ensure the scoring prompt **emits standardized, rubric-referential student feedback** in a fixed, reusable format,
- ensure the scoring prompt **explicitly signals the boundary between Meets and Exceeds**, even when all indicators are present.

This wrapper prompt generates a prompt; it does **not** score student work.

### Task classification (authoritative)
This wrapper prompt performs:
- prompt synthesis (bounded),
- constraint propagation from rubric definition to scoring instructions,
- analytic-structure extraction from supplied materials,
- output-schema specification.

It does **not** perform:
- scoring, grading, or evaluation of student work,
- rewriting or improving rubric dimensions,
- inventing indicators, facets, questions, rules, or score levels,
- adding coaching, advice, or normative judgement.

### Authoritative inputs (required, verbatim)
The model may rely **only** on the following inputs, supplied verbatim by the user and delimited by `===`:

===
Step 1 — Dimension header  
- Dimension name (exact rubric label)  
- Unit of analysis (one cell = one score)  
- One-sentence definition of what is being scored  
===

===
Step 2 — Observable indicators checklist  
- 3–6 indicators phrased as observable “does the response do X”  
- Indicators function strictly as **presence checks**, not performance guarantees  
===

===
Step 3 — Boundary rules by score level  
- Score level labels (exact)  
- For each level: minimum threshold and knock-down conditions  
- Explicit hardest boundary rule (e.g., Approaching vs Meets)  
- Any language implying required facets, quality checks, exemplification, or differential thresholds  
===

===
Step 4 — Fixed calibration set payload format (authoritative)  
Each item presented to the scoring prompt will have **exactly this structure**:
- `row_id` : integer  
- `response_text` : text  

Formatting guarantees:
- `response_text` may include wrapper markers like `+++` and a header line of the form `row_id=<value>`; these **must be ignored for scoring**.
- No other metadata, context, rubric text, or neighbouring responses will be provided.
- Each item is scored independently.
===

===
Output requirements  
- Required fields (choose from):  
  `score`, `indicator_hits`, `indicator_facets`, `question_hits`, `boundary_checks`, `rationale`, `evidence_quote`, `confidence`, `flags`, `feedback`  
- Confidence scale (e.g., high / medium / low)  
- Fixed list of allowed flags  
===

No external knowledge, inference, or interpretation is permitted.

### Stage discipline (mandatory)
Stage 1: Input  
- The user supplies all authoritative inputs, delimited by `===`.
- The model reads silently.
- No output is generated.

Stage 2: Execution  
- The model generates output **only after** the explicit command:  
  `BEGIN GENERATION`

Silence is the correct behaviour until `BEGIN GENERATION`.

### Output artefact
The model must generate **exactly one artefact**:
- a **stand-alone provisional scoring prompt** titled  
  `CAL_<DIMENSION>_Step05_provisional_scoring_prompt_v01`,
- written so it can be reused unchanged across calibration cycles,
- assuming the fixed payload format defined above.

### Required output structure (strict)
The generated scoring prompt must:
- be contained in **one fenced Markdown block and nothing else**,
- use **level-3 headings only**,
- avoid nested lists,
- use bullet lists only,
- contain the following sections **in this exact order**:

### Prompt title and use restrictions
- State that the prompt assigns provisional scores only.
- State that it scores exactly one dimension and ignores all others.
- State that outputs are diagnostic and non-authoritative.
- State that the prompt generates standardized, non-coaching student feedback.

### Authoritative scoring materials
- Restate the dimension header verbatim.
- Restate the indicator checklist verbatim.
- Restate the boundary rules verbatim.
- Explicitly state:
  - indicators are **presence checks only**,
  - facets, question coverage, and quality thresholds are **extracted from the boundary rules**, not from the indicator list,
  - indicator completeness does **not** guarantee the highest score.

### Extracted analytic structure (mandatory)
- Identify and name each **required facet** implied by the boundary rules.
- Identify any **implicit question obligations** (i.e., what the response must answer or take a position on).
- Identify any **quality checks** (e.g., coherence, specificity) implied by the boundary rules.
- Identify any **explicit boundary gates** that distinguish score levels (e.g., hardest boundary; Meets vs Exceeds).
- State explicitly that this structure is **derivative**, not newly invented.

### Input format (fixed and enforced)
- Define `row_id` and `response_text`.
- Specify wrapper-stripping rules.
- State that no additional context may be inferred.

### Scoring procedure (mandatory)
- Require a single-pass judgement per item.
- Require application of boundary rules before confirming indicator presence.
- Require explicit evaluation of:
  - indicator presence,
  - facet presence and adequacy,
  - question coverage (if extracted),
  - quality checks,
  - hardest boundary rule,
  - Meets vs Exceeds boundary gate.
- Prohibit inference beyond the text.
- If indeterminate, require `needs_review`.

### Feedback generation rules (mandatory)
- Require generation of **one standardized feedback block per item**.
- Require feedback to be derived strictly from:
  - the assigned score,
  - indicator hit pattern,
  - extracted facet, question, and boundary results.
- Prohibit advice, coaching, rewriting, or improvement guidance.
- Require feedback to explain **why this score level was assigned**, not how to improve.

### Feedback format (fixed, abstract)
The scoring prompt must enforce the following **dimension-agnostic** feedback template:

<Dimension Label>: <score>  
Indicators: <indicator_index><✓/✗> … (one entry per supplied indicator, in order)  
Facets: <facet_id><✓/✗> … (one entry per extracted facet, in order)  
Questions: <question_id><✓/✗/—> … (only if question obligations were extracted)  
Reason: <single concise sentence citing the facet, question, or boundary gate that determined the score>

Rules:
- The number and labels of indicators, facets, and questions must be generated dynamically from the supplied materials.
- If all indicators are ✓ but the score is **not the highest level**, the Reason **must explicitly reference the Meets vs Exceeds boundary gate**.
- Maximum length for Reason: one sentence.

### Output schema (mandatory)
- The scoring prompt must output **structured data** with one output object per input item and the same order as input.
- The scoring prompt must include all required fields specified by the user.
- The scoring prompt must always include:
  - `score`,
  - `indicator_hits`,
  - `indicator_facets`,
  - `question_hits` (only if questions were extracted),
  - `boundary_checks`,
  - `rationale`,
  - `evidence_quote`,
  - `confidence`,
  - `flags`,
  - `feedback`.

### Constraints and failure handling
- Prohibit feedback beyond the standardized block.
- Prohibit cross-dimension commentary.
- Prohibit mid-run rule modification.
- If scoring is indeterminate:
  - assign the lowest evaluable score label,
  - include `needs_review`,
  - generate feedback reflecting indeterminacy.

### Content rules (strict)
- Use only supplied materials.
- Do not invent indicators, facets, questions, rules, flags, or score levels.
- Do not add theory, examples, or advice.
- Do not reference prior versions of this wrapper prompt.

### Failure mode handling
If any required input block is missing or contradictory:
- generate nothing,
- wait silently for correction.

===
  
```