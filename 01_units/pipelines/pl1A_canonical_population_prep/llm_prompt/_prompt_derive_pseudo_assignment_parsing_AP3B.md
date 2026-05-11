```md
WRAPPER PROMPT — SEGMENTATION (AP3B)

You will receive multiple `<submission ...>...</submission>` blocks.

Task: extract exactly 3 claim spans per submission, verbatim.

This is extraction only:
- Do not summarize
- Do not rewrite
- Do not paraphrase
- Do not normalize
- Do not add commentary

Rules:
1. Keep claim text verbatim (except you may strip only outermost wrapping quotes).
2. Use explicit starts when present (`Claim 1/2/3`, `Claim statement`, `1./2./3.`).
3. If markers are absent, use first three occurrences of `In this system`.
4. Each claim spans from its start until right before the next claim start.
5. If ambiguous, keep longer verbatim spans and assign ambiguous text to nearest claim.

OUTPUT CONTRACT (STRICT):
- Return exactly one fenced markdown block.
- Inside the fence, return ONLY structured row blocks in input order.
- One row block per submission, index starts at 1 and increments by 1.
- No prose, no bullets, no headers, no extra lines outside row blocks.

Required row format:
<row index="1">
<claim1>...</claim1>
<claim2>...</claim2>
<claim3>...</claim3>
</row>

<row index="2">
<claim1>...</claim1>
<claim2>...</claim2>
<claim3>...</claim3>
</row>

Notes:
- Claims may be multiline inside tags.
- Do not escape or transform characters.
- The number of `<row ...>` blocks must equal the number of input submissions.
```
