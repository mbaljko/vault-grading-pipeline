this document sets out a WRAPPER PROMPT - which is used to create tightly bounded prompt which can to be used to assign provisional scores.

# .
```
BEGIN GENERATION
```

# .
````
### pl2_wrapper_prompt — Generate Calibration Scoring Prompt (Dimension-Level, Ontology-Aligned)

Wrapper prompt: Generate a tightly bounded provisional scoring prompt (a prompt to be used to accomplish scoring via an API call or via interactive UI).

The resultant prompt assigns provisional scores for **one rubric dimension within one component** for a set of student submissions.

This scoring is intended for **diagnostic use during calibration** and must comply with the grading ontology defined in **Nomenclature Standard — Grading Ontology and Calibration Alignment**.

The resultant assigned scores expose **analytic structure used to interpret a dimension**, including indicators, facets, and boundary gates.

---

### Purpose

This wrapper prompt generates a **single, repeatable, tightly bounded scoring prompt** that can be reused to assign **provisional scores for exactly one rubric dimension** over a fixed-format calibration set.

The generated scoring prompt must operate on the **atomic grading unit**:

```
submission_id × component_id × dimension_id
```

Its purpose is to:

- produce a **dimension-specific scoring prompt** that evaluates *only the target dimension*,
- enforce the provided **indicator checklist** and **boundary rules** as the sole scoring logic,
- ensure the resulting scoring prompt is **diagnostic and non-authoritative** (used to detect drift and stress-test rules),
- ensure the scoring prompt produces **structured outputs** suitable for inspection, comparison, and rule refinement,
- ensure the scoring prompt **extracts and surfaces analytic structure implicit in the supplied materials** (facets, quality checks, boundary gates),
- ensure the scoring prompt **emits standardized, rubric-referential student feedback** in a fixed, reusable format,
- ensure the scoring prompt **explicitly signals the boundary between Meets and Exceeds**, even when all indicators are present.

This wrapper prompt **generates a scoring prompt**.  
It does **not** score student work.

---

### Ontology Compliance (Mandatory)

The generated scoring prompt must strictly adhere to the grading ontology:

- `submission_id` → one student submission
- `component_id` → grading surface within the submission
- `dimension_id` → atomic rubric criterion applied to that component
- `facet` → sub-criteria used to interpret a dimension (not structural)
- `indicator` → observable presence check within a response
- `boundary_rule` → threshold logic determining score levels

Calibration **always operates at the dimension level**.

The scoring prompt must therefore:

- evaluate **one dimension only**,
- treat `component_id` only as the **evidence surface identifier**,
- never use the term **facet** to refer to a dimension,
- never treat a component as a dimension.

---

### Task classification (authoritative)

This wrapper prompt performs:

- prompt synthesis (bounded)
- constraint propagation from rubric definition to scoring instructions
- analytic-structure extraction from supplied materials
- output-schema specification

It does **not** perform:

- scoring, grading, or evaluation of student work
- rewriting or improving rubric dimensions
- inventing indicators, facets, questions, rules, or score levels
- adding coaching, advice, or normative judgement

---

### Authoritative inputs (required, verbatim)

The model may rely **only** on the following inputs, supplied verbatim by the user and delimited by `===`.

---

===
Step 1 — Dimension header  

- `component_id` (evidence surface identifier)
- `dimension_id` (atomic grading unit identifier)
- Dimension label
- Unit of analysis (one grading unit = one score)
- One-sentence definition of what is being scored
===

---

===
Step 2 — Observable indicators checklist  

- 3–6 indicators phrased as observable **presence checks**
- Indicators evaluate observable moves in the response
- Indicators do **not guarantee performance level**
===

---

===
Step 3 — Boundary rules by score level  

- Score level labels (exact)
- Minimum threshold conditions for each level
- Knock-down conditions
- Explicit hardest boundary rule (e.g., Approaching vs Meets)
- Any language implying:
  - facets
  - quality checks
  - exemplification thresholds
  - differential conditions between levels
===

---

===
Step 4 — Fixed calibration set payload format (authoritative)

Each item presented to the scoring prompt will have **exactly this structure**:

- `row_id`
- `submission_id`
- `component_id`
- `dimension_id`
- `response_text`

Formatting guarantees:

- `response_text` may include wrapper markers such as `+++`
- `response_text` may include header lines such as `row_id=<value>`
- These must be **ignored for scoring**

No additional metadata, context, rubric text, or neighbouring responses will be provided.

Each grading unit is scored independently.
===

---

===
Output requirements  

Required output fields must be selected from:

```
score
indicator_hits
facet_hits
question_hits
boundary_checks
rationale
evidence_quote
confidence
flags
feedback
```

Also provide:

- confidence scale (e.g. high / medium / low)
- fixed list of allowed flags
===

---

No external knowledge, inference, or interpretation is permitted.

---

### Stage discipline (mandatory)

Stage 1 — Input

- The user supplies authoritative inputs delimited by `===`.
- The model reads silently.
- No output is generated.

Stage 2 — Execution

- The model generates output **only after the explicit command**:

```
BEGIN GENERATION
```

Silence is the correct behaviour until this command.

---

### Output artefact

The model must generate **exactly one artefact**.

A stand-alone provisional scoring prompt titled:

```
CAL_<ASSESSMENT>_<DIMENSION_ID>_Step05_provisional_scoring_prompt_v01
```

The prompt must be reusable unchanged across calibration cycles.

---

### Required output structure (strict)

The generated scoring prompt must:

- be contained in **one fenced Markdown block**
- use **level-3 headings only**
- avoid nested lists
- use bullet lists only
- contain the following sections **in this exact order**

---

### Prompt title and use restrictions

State that:

- the prompt assigns provisional scores only
- it evaluates exactly **one dimension**
- it ignores all other dimensions
- outputs are diagnostic and non-authoritative
- feedback generated is standardized and non-coaching

---

### Authoritative scoring materials

Restate verbatim:

- `component_id`
- `dimension_id`
- dimension label
- dimension definition
- indicator checklist
- boundary rules

Explicitly state:

- indicators are **presence checks only**
- facets and quality thresholds are **derived from boundary rules**
- indicator completeness **does not guarantee the highest score**

---

### Extracted analytic structure (mandatory)

The scoring prompt must identify and name:

- **facets** implied by boundary rules
- **implicit question obligations**
- **quality checks**
- **explicit boundary gates**

These structures must be described as **derivative interpretations of boundary rules**.

Facets must always be treated as **sub-tests of the dimension**.

---

### Input format (fixed and enforced)

Define:

- `row_id`
- `submission_id`
- `component_id`
- `dimension_id`
- `response_text`

Specify wrapper stripping rules.

State that **no context outside the response text may be inferred**.

---

### Scoring procedure (mandatory)

Require a single-pass judgement per item.

Require explicit evaluation of:

- indicator presence
- facet coverage and adequacy
- question coverage (if present)
- quality checks
- hardest boundary rule
- Meets vs Exceeds boundary gate

Prohibit inference beyond the text.

If indeterminate:

- assign lowest evaluable score
- include `needs_review`.

---

### Feedback generation rules (mandatory)

Require generation of **one standardized feedback block per grading unit**.

Feedback must derive strictly from:

- score level
- indicator hits
- facet evaluation
- boundary decisions

Prohibit:

- coaching
- advice
- rewriting
- improvement suggestions

Feedback must explain **why the score was assigned**, not how to improve.

---

### Feedback format (fixed)

```
<Dimension Label>: <score>
Indicators: <indicator_index><✓/✗> ...
Facets: <facet_id><✓/✗> ...
Questions: <question_id><✓/✗/—> ...
Reason: <single sentence referencing decisive facet or boundary>
```

Rules:

- indicator list generated dynamically
- facet list generated dynamically
- questions only appear if extracted

If all indicators are ✓ but score is not highest:

- reason must reference the **Meets vs Exceeds boundary gate**

Maximum reason length: one sentence.

---

### Output schema (mandatory)

The scoring prompt must emit **structured data** with one object per grading unit.

Fields must include:

```
score
indicator_hits
facet_hits
question_hits
boundary_checks
rationale
evidence_quote
confidence
flags
feedback
```

Output order must match input order.

---

### Constraints and failure handling

Prohibit:

- feedback beyond standardized block
- cross-dimension commentary
- mid-run rule modification

If scoring is indeterminate:

- assign lowest evaluable score
- include `needs_review`
- feedback must reflect indeterminacy.

---

### Content rules (strict)

Use **only supplied materials**.

Do not invent:

- indicators
- facets
- questions
- rules
- score levels
- flags

Do not add theory, examples, or advice.

Do not reference prior prompt versions.

---

### Failure mode handling

If any required input block is missing or contradictory:

- generate nothing
- wait silently for correction

===
````