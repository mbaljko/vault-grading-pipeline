### Assumption — Input Text Formatting

This Stage 1 indicator detection process assumes that all `response_text` inputs are already compliant with the required output formatting constraints.

Specifically, the upstream preprocessing pipeline guarantees that:

- quotation marks appearing in the text are already escaped as `\"`
- newline characters within the text are represented as `\n`
- backslashes within the text are represented as `\\`
- the text contains no unescaped characters that would violate the output quoting rules

Because this invariant is guaranteed prior to Stage 1 execution, the prompt does **not** need to perform additional escaping or sanitization of extracted excerpts.

The Stage 1 evaluation procedure may therefore:

- extract evidence excerpts directly from `response_text`
- wrap the excerpt in double quotes as required by the output schema
- assume that no additional character escaping is required

If this invariant is violated upstream, the responsibility for correction lies with the preprocessing stage rather than the Stage 1 scoring prompt.