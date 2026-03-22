# .
```
BEGIN GENERATION
```


REVISE TO ADD OUTPUT - indicator_facet
# .
```
### Wrapper prompt: Generate a tightly bounded provisional scoring prompt for one rubric dimension (diagnostic use)

#### Purpose
This wrapper prompt generates a **single, repeatable, tightly bounded scoring prompt** that can be reused to assign **provisional scores for exactly one rubric dimension** over a fixed-format calibration set.

Its purpose is to:
- produce a **dimension-specific scoring prompt** that scores *only* the target dimension,
- enforce the provided **indicator checklist** and **boundary rules** as the sole scoring logic,
- ensure the resulting scoring prompt is **diagnostic and non-authoritative** (used to detect drift and stress-test rules),
- ensure the scoring prompt produces **structured outputs** suitable for inspection, comparison, and rule refinement.

This wrapper prompt generates a prompt; it does **not** score student work.

#### Task classification (authoritative)
This wrapper prompt performs:
- ☑ prompt synthesis (bounded)
- ☑ constraint propagation from rubric dimension definition to scoring instructions
- ☑ output-schema specification

It does **not** perform:
- scoring, grading, or evaluation of student work
- rewriting or improving rubric dimensions
- inventing indicators, rules, or score levels
- adding pedagogical feedback or normative judgement

#### Authoritative inputs (required, verbatim)
The model may rely **only** on the following inputs, supplied verbatim by the user and delimited by `===`:

===
**Step 1 — Dimension header**  
- Dimension name (exact rubric label)  
- Unit of analysis (one cell = one score)  
- One-sentence definition of what is being scored  
===
**Step 2 — Observable indicators checklist**  
- 3–6 indicators phrased as observable “does the response do X”  
===
**Step 3 — Boundary rules by score level**  
- Score scale (e.g., 0–4 or 1–4)  
- For each level: minimum threshold and knock-down conditions  
- Explicit hardest boundary rule (e.g., 2 vs 3)  
===
**Step 4 — Fixed calibration set payload format (authoritative)**  
Each item presented to the scoring prompt will have **exactly this structure**:

- `row_id` : integer  
- `response_text` : text  

Formatting guarantees:
- `response_text` may include wrapper markers like `+++` and a header line of the form `row_id=<value>`;  
  these **must be ignored for scoring**.
- No other metadata, context, rubric text, or neighbouring responses will be provided.
- Each item is scored independently.

===
**Output requirements**  
- Required fields (choose from): `score`, `indicator_hits`, `rationale`, `evidence_quote`, `confidence`, `flags`  
- Confidence scale (e.g., high / medium / low)  
- Fixed list of allowed flags  
===

No external knowledge, inference, or interpretation is permitted.

#### Stage discipline (mandatory)

**Stage 1: Input**
- The user supplies all authoritative inputs, delimited by `===`.
- The model reads silently.
- No output is generated.

**Stage 2: Execution**
- The model generates output **only after** the explicit command:  
  `BEGIN GENERATION`

Silence is the correct behaviour until `BEGIN GENERATION`.

#### Output artefact
The model must generate **exactly one artefact**:
- a **stand-alone provisional scoring prompt** titled  
  `CAL_<DIMENSION>_Step05_provisional_scoring_prompt_v01`,
- written so it can be reused unchanged across calibration cycles,
- assuming the fixed payload format defined above.

#### Required output structure (strict)
The output must:
- be contained in **one fenced Markdown block and nothing else**,
- use **level-3 headings only**,
- avoid nested lists,
- use bullet lists only,
- contain the following sections **in this exact order**:

### Prompt title and use restrictions
- State that the prompt is for provisional scoring only.
- State that it scores exactly one dimension and ignores all others.
- State that outputs are diagnostic and non-authoritative.

### Authoritative scoring materials
- Restate the dimension header.
- Restate the indicator checklist verbatim.
- Restate the boundary rules verbatim.

### Input format (fixed and enforced)
- Define `row_id` and `response_text`.
- Specify wrapper-stripping rules.
- State that no additional context may be inferred.

### Scoring procedure (mandatory)
- Require a single-pass judgement per item.
- Require boundary-rule application before indicator confirmation.
- Require explicit checking of the hardest boundary.
- Prohibit inference beyond the text.

### Output schema (mandatory)
- Define each output field and allowed values.
- Require one output row per input item.
- Require output order to match input order.

### Constraints and failure handling
- Prohibit feedback, coaching, or rewriting.
- Prohibit cross-dimension commentary.
- Prohibit mid-run rule modification.
- If scoring is indeterminate, require a fixed flag (e.g., `needs_review`) with a brief reason.

#### Content rules (strict)
- Use only supplied materials.
- Do not invent indicators, rules, flags, or score levels.
- Do not add theory, examples, or advice.
- Do not reference prior versions of this wrapper prompt.

#### Failure mode handling
If any required input block is missing or contradictory:
- generate nothing,
- wait silently for correction.
  

===
  
```