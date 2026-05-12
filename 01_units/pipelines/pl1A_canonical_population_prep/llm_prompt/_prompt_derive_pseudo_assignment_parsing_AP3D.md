

````md
WRAPPER PROMPT — SEGMENTATION (AP3D)

From this assignment, student submissions are expected to consist of **three institutional constraint entries**, each following the AP3D Section D structure.

Each entry is expected to contain:
- a constraint statement,
- a “What it shapes” field,
- and an effect-on-action statement.

You will receive a set of student submissions. Each submission is wrapped as:

`<submission index="N" submission_id="..."> ... </submission>`

Your task is to segment each submission into exactly three verbatim constraint-entry spans.

### Task definition (strict)

This is an **extraction and segmentation task only**.

- Do **not** summarise
- Do **not** rewrite
- Do **not** paraphrase
- Do **not** normalise spacing or grammar
- Do **not** clean or interpret the text

You must **only segment and copy** the original text.

### Extraction rules

1. Each constraint-entry span must be an **exact verbatim substring** of the input submission.
2. Preserve the **exact original character sequence**, including spaces, tabs, punctuation, blank lines, and line breaks.
3. Do not add or remove words.
4. Do not fix formatting issues.
5. You may remove only the **outermost wrapping quotation marks** if present.

### Segmentation rules

1. Extract exactly **three constraint-entry spans per submission**.
2. Use explicit markers where present, including variants such as:
   - `Constraint 1`, `Constraint 2`, `Constraint 3`
   - `Institutional Constraint 1`
   - `Entry 1`, `Entry 2`, `Entry 3`
   - numbered forms such as `1.`, `2.`, `3.` or `1:`, `2:`, `3:`
   - ordinal forms such as `First constraint`, `Second constraint`, `Third constraint`
   - field labels such as:
     - `Constraint`
     - `What it shapes`
     - `Effect on action`
3. If explicit markers are absent, segment using the first three structurally distinct constraint-like entries.
4. Each constraint-entry span should begin at its entry start marker and end immediately before the next entry start.
5. If boundaries are ambiguous, prefer **longer verbatim spans** and keep ambiguous text in the nearest entry.

### Validation constraint

For each submission:

- Concatenating constraint1 + constraint2 + constraint3 in order must reconstruct the original submission text, aside from removed outer quotes.
- If exact reconstruction is difficult, do not rewrite. Include extra text in the nearest entry.
- If markers such as `Constraint 1`, `First constraint`, `What it shapes`, or `Effect on action` appear in the input and belong with the entry span, keep them inside the entry span.
- If guidance text or template scaffolding appears in the input and cannot be cleanly separated without rewriting, keep it inside the nearest entry span.

### Output format

Output **exactly one fenced Markdown block** and nothing else.

Inside that fenced block, emit one `<row>` block for each input submission, in the same order as the input submission indices.

Use the input row indices exactly. If the inputs are `1, 2, 3`, the outputs must be `1, 2, 3` in that same order, with no gaps and no duplicates.

Use this exact structure:

```md
<row index="1">
<constraint1>exact verbatim span for constraint entry 1</constraint1>
<constraint2>exact verbatim span for constraint entry 2</constraint2>
<constraint3>exact verbatim span for constraint entry 3</constraint3>
</row>
<row index="2">
<constraint1>...</constraint1>
<constraint2>...</constraint2>
<constraint3>...</constraint3>
</row>
```

### Good output example

```md
<row index="1">
<constraint1>Constraint 1:
Constraint: Documentation retention requirements
What it shapes: visibility
Effect on action: Officers must record verification steps within retained case files.</constraint1>

<constraint2>Constraint 2:
Constraint: Fixed processing timelines
What it shapes: timing
Effect on action: Applications are routed according to service-level sequencing rules.</constraint2>

<constraint3>Constraint 3:
Constraint: Formal officer authorisation
What it shapes: authority
Effect on action: Final eligibility decisions must be recorded by authorised officers.</constraint3>
</row>
```

### Bad output examples

Do **not** output any of the following:

```md
First constraint: ...
Second constraint: ...
Third constraint: ...
```

```md
constraint1 ∞ constraint2 ∞ constraint3
```

```md
Row 1
constraint1: ...
constraint2: ...
constraint3: ...
```

### Output format rules

1. The number of `<row>` blocks must equal the number of input submissions.
2. Each `<row>` must use the same `index` value as the corresponding input `<submission index="N">`.
3. Each `<row>` must contain exactly one `<constraint1>`, one `<constraint2>`, and one `<constraint3>` block.
4. Constraint-entry text may contain literal newlines and blank lines.
5. Do not add any text outside the `<constraint1>`, `<constraint2>`, `<constraint3>` tags except the required `<row>` wrappers.
6. Do not include commentary, headers, bullet lists, explanations, or alternate formats.
7. Do **not** output the legacy `∞` delimiter format.
8. Do **not** rename the tags, add attributes to the constraint tags, or omit the closing tags.
9. If segmentation is uncertain, still emit a valid `<row>` block and put ambiguous text into the nearest constraint-entry span rather than switching formats.
10. Preserve literal line breaks inside constraint tags when they exist in the source text.

===
````
