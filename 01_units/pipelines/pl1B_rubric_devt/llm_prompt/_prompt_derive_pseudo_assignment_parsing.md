receive and wait
-give the materials

```md
WRAPPER PROMPT - SEGMENTATION
From this assignment, we are expecting student submissions to be structured according to the section specifications, which is a set of three analytic claims, each one following the specified template.

You will receive a set of student submissions.

Your task is to parse each submission into 3 columns, one analytic claim per column.

### Task definition (strict)

This is an **extraction and segmentation task only**.

- Do **not** summarise  
- Do **not** rewrite  
- Do **not** paraphrase  
- Do **not** normalise spacing or grammar  
- Do **not** clean or interpret the text  

You must **only segment and copy** the original text.

### Extraction rules

1. Each output cell must be an **exact verbatim substring** of the input submission.
2. Preserve the **exact original character sequence**, including spacing, punctuation, and formatting.
3. Do not add or remove words.
4. Do not fix formatting issues (e.g., missing spaces like `thissystem` must remain unchanged).
5. You may remove only the **outermost wrapping quotation marks** if present.

### Segmentation rules

1. Extract exactly **three claim spans per submission**.
2. Use explicit markers where present:
   - `Claim 1`, `Claim 2`, `Claim 3`
   - `Claim statement`, `First claim`, etc.
   - Numbered forms: `1.`, `2.`, `3.`
3. If explicit markers are absent:
   - Segment using the **first three occurrences of `In this system` (or equivalent variants such as `In thissystem`)**
4. Each claim span should:
   - begin at its claim start marker (or `In this system`)
   - end immediately before the next claim start
5. If boundaries are ambiguous:
   - prefer **longer verbatim spans**
   - do not discard or rewrite any text

### Validation constraint

For each row:

- Concatenating the three extracted spans in order should reconstruct the original submission text (aside from removed outer quotes).
- If exact reconstruction is not possible, **do not rewrite** — instead include ambiguous text in the nearest span.

### Output requirements

- The number of output rows must equal the number of input submissions.
- Each row corresponds to exactly one submission.
- Each row contains exactly three columns.
- Columns are delimited by: ` ∞ `
- Emit output as **fenced Markdown only**
- Do not include any commentary, headers, or explanations.

=== 
```
