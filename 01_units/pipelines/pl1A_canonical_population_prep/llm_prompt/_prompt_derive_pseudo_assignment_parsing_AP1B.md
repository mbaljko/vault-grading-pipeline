receive and wait
-give the materials

````md
WRAPPER PROMPT — SEGMENTATION (AP1B)

From this assignment, student submissions are expected to consist of **three analytic claim statements**, each following the AP2B Section B template.

You will receive a set of student submissions. Each submission is wrapped as:

`<submission index="N" submission_id="..."> ... </submission>`

Your task is to segment each submission into exactly three verbatim claim spans.

### Task definition (strict)

This is an **extraction and segmentation task only**.

- Do **not** summarise
- Do **not** rewrite
- Do **not** paraphrase
- Do **not** normalise spacing or grammar
- Do **not** clean or interpret the text

You must **only segment and copy** the original text.

### Extraction rules

1. Each claim span must be an **exact verbatim substring** of the input submission.
2. Preserve the **exact original character sequence**, including spaces, tabs, punctuation, blank lines, and line breaks.
3. Do not add or remove words.
4. Do not fix formatting issues.
5. You may remove only the **outermost wrapping quotation marks** if present.

### Segmentation rules

1. Extract exactly **three claim statement spans per submission**.
2. Use explicit markers where present, including variants such as:
   - `Claim 1`, `Claim 2`, `Claim 3`
   - `Constraint 1`, `Constraint 2`, `Constraint 3`
   - `Case 1`, `Case 2`, `Case 3`
   - `Claim statement`
   - numbered forms such as `1.`, `2.`, `3.` or `1:`, `2:`, `3:`
   - ordinal forms such as `First claim`, `Second claim`, `Third claim`, `Final claim`, `First Analytic Claim`
3. If explicit markers are absent, segment using the first three claim-like starts such as `In this system` or `In the system` when they clearly expose three claim spans.
4. Each claim span should begin at its claim start marker and end immediately before the next claim start.
5. If boundaries are ambiguous, prefer **longer verbatim spans** and keep ambiguous text in the nearest claim.

### Validation constraint

For each submission:

- Concatenating claim1 + claim2 + claim3 in order must reconstruct the original submission text, aside from removed outer quotes.
- If exact reconstruction is difficult, do not rewrite. Include extra text in the nearest claim.
- If a marker such as `Claim 1`, `First claim`, `Case 3`, or `Constraint 2` appears in the input and belongs with the claim span, keep it inside the claim span.
- If guidance text or template scaffolding appears in the input and cannot be cleanly separated without rewriting, keep it inside the nearest claim span.

### Output format

Output **exactly one fenced Markdown block** and nothing else.

Inside that fenced block, emit one `<row>` block for each input submission, in the same order as the input submission indices.

Use the input row indices exactly. If the inputs are `1, 2, 3`, the outputs must be `1, 2, 3` in that same order, with no gaps and no duplicates.

Use this exact structure:

```md
<row index="1">
<claim1>exact verbatim span for claim 1</claim1>
<claim2>exact verbatim span for claim 2</claim2>
<claim3>exact verbatim span for claim 3</claim3>
</row>
<row index="2">
<claim1>...</claim1>
<claim2>...</claim2>
<claim3>...</claim3>
</row>
```

### Good output example

```md
<row index="1">
<claim1>Claim 1:
In this system, ...</claim1>
<claim2>Claim 2:
In this system, ...</claim2>
<claim3>Case 3:
In this system, ...</claim3>
</row>
```

### Bad output examples

Do **not** output any of the following:

```md
First claim: ...
Second claim: ...
Third claim: ...
```

```md
claim1 ∞ claim2 ∞ claim3
```

```md
Row 1
claim1: ...
claim2: ...
claim3: ...
```

### Output format rules

1. The number of `<row>` blocks must equal the number of input submissions.
2. Each `<row>` must use the same `index` value as the corresponding input `<submission index="N">`.
3. Each `<row>` must contain exactly one `<claim1>`, one `<claim2>`, and one `<claim3>` block.
4. Claim text may contain literal newlines and blank lines.
5. Do not add any text outside the `<claim1>`, `<claim2>`, `<claim3>` tags except the required `<row>` wrappers.
6. Do not include commentary, headers, bullet lists, explanations, or alternate formats.
7. Do **not** output the legacy `∞` delimiter format.
8. Do **not** rename the tags, add attributes to the claim tags, or omit the closing tags.
9. If segmentation is uncertain, still emit a valid `<row>` block and put ambiguous text into the nearest claim span rather than switching formats.
10. Preserve literal line breaks inside claim tags when they exist in the source text.

===
````
