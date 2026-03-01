## Query: `cleaned_entries`  
### Stage 0 — Canonical Component-Level Dataset (Long Format)

### Purpose

This Power Query (MCode) query implements **Stage 0 canonicalisation** for grading.

It transforms heterogeneous LMS exports into a structurally stable, identity-safe, component-level dataset suitable for:

- calibration
- sampling
- dimension-level scoring
- audit and reproducibility

The output of this query is the **canonical Stage 0 dataset** for this assessment.

---

### Canonical Unit Definition (Current Implementation)

Each row produced by this query represents exactly one:

> `submission_id × component_id`

This is the atomic grading unit at the component level.

Dimension-level expansion may occur in a later stage.

---

### Identity Guarantees

Each canonical row contains:

- `submission_id`  
  Stable numeric identifier derived from the grading worksheet `Identifier`  
  (digits-only; authoritative identity)

- `__row_id`  
  Local anonymised row handle (stable within this workbook/run)

- `__key`  
  Deterministic join key used for validation audit

Only rows with:

```
__join_status = matched_unique
```

are included.

No unmatched or ambiguous identities are permitted to enter this dataset.

---

### Transformations Performed

1. Cleans raw HTML and encoding artefacts from LMS exports.
2. Normalises mojibake and whitespace.
3. Joins LMS export to grading worksheet via validated identity mapping.
4. Filters out all non-eligible submissions.
5. Adds per-submission anonymised `__row_id`.
6. Unpivots component columns into long format.
7. Derives explicit `component_id` from column name.
8. Computes `word_count` per component.
9. Produces a flat, uniform canonical dataset.

---

### Structural Properties of Output

The output dataset guarantees:

- Explicit identity columns (`submission_id`, `component_id`)
- No duplicate `(submission_id, component_id)` pairs
- No null `submission_id`
- Cleaned response text only (no raw HTML)
- Uniform schema across all rows
- Deterministic transformation from identical inputs

This dataset becomes the sole input for all downstream grading stages.

---

### Non-Goals of This Query

This query does **not**:

- Apply rubric scoring
- Perform calibration logic
- Modify rubric definitions
- Perform cross-dimension checks
- Alter grading scales

It performs data normalisation and canonicalisation only.

---

### Future Extension

If the grading engine migrates to full dimension-level canonical units, this dataset will be expanded to:

> `submission_id × component_id × dimension_id`

via cross-join with a rubric dimension table.

The current component-level representation is intentionally chosen as an intermediate canonical form.

---

### Operational Rule

`cleaned_entries` SHALL be treated as the canonical Stage 0 dataset for this assessment.

All downstream queries must reference this output rather than raw LMS exports.
let
    Source = Excel.CurrentWorkbook(){[Name="Table_raw"]}[Content],
    Validation = Excel.CurrentWorkbook(){[Name="validation"]}[Content],

    // --- helper functions (unchanged) ---
    NormaliseHtml = (t as nullable text) as nullable text =>
        let
            s0 = t,
            s1 =
                if s0 = null then null
                else if Text.Length(s0) >= 2 and Text.Start(s0, 1) = """" and Text.End(s0, 1) = """"
                    then Text.Middle(s0, 1, Text.Length(s0) - 2)
                    else s0,
            s2 = if s1 = null then null else Text.Replace(s1, """""", """")
        in
            s2,

    SanitiseMojibake = (t as nullable text) as nullable text =>
        let
            s0 = t,
            Replacements = {
                {"¬†", " "},
                {"‚Äî", "—"},
                {"‚Äú", "“"},
                {"‚Äù", "”"},
                {"‚Äò", "‘"},
                {"‚Äô", "’"},
                {Character.FromNumber(160), " "}
            },
            s1 =
                if s0 = null then
                    null
                else
                    List.Accumulate(
                        Replacements,
                        s0,
                        (state as text, pair as list) =>
                            Text.Replace(state, pair{0}, pair{1})
                    ),
            s2 = if s1 = null then null else Text.Trim(Text.Clean(s1))
        in
            s2,

    StripTagsFallback = (t as nullable text) as nullable text =>
        let
            s0 = t,
            parts = if s0 = null then {} else Text.Split(s0, "<"),
            kept =
                List.Transform(
                    parts,
                    (p) => if Text.Contains(p, ">") then Text.AfterDelimiter(p, ">") else p
                ),
            combined = Text.Combine(kept, ""),
            cleaned = Text.Trim(Text.Clean(combined))
        in
            cleaned,

    StripHtmlSafe = (raw as nullable any) as nullable text =>
        let
            t0 = if raw = null then null else Text.From(raw),
            norm = NormaliseHtml(t0),
            sane0 = SanitiseMojibake(norm),

            br1 = if sane0 = null then null else Text.Replace(sane0, "<br />", "#(lf)"),
            br2 = if br1 = null then null else Text.Replace(br1, "<br/>", "#(lf)"),
            br3 = if br2 = null then null else Text.Replace(br2, "<br>", "#(lf)"),

            wrapped = if br3 = null then null else "<div>" & br3 & "</div>",

            parsed =
                try
                    let
                        nodes = Html.Table(wrapped, {{"t", "//text()"}}),
                        combined = Text.Combine(nodes[t], ""),
                        cleaned = Text.Trim(Text.Clean(combined))
                    in
                        cleaned
                otherwise
                    StripTagsFallback(br3),

            sane1 = SanitiseMojibake(parsed),

            delimited =
                if sane1 = null then null
                else "+++" & "#(lf)" & sane1 & "#(lf)" & "+++"
        in
            delimited,

    // Word count helper: strips the +++ wrapper, normalises whitespace, counts tokens
    WordCount = (t as nullable text) as nullable number =>
        let
            s0 = t,
            s1 =
                if s0 = null then
                    null
                else
                    Text.Replace(
                        Text.Replace(
                            Text.Replace(s0, "+++", " "),
                            "#(lf)",
                            " "
                        ),
                        "#(cr)",
                        " "
                    ),
            s2 = if s1 = null then null else Text.Trim(Text.Clean(s1)),
            parts = if s2 = null or s2 = "" then {} else List.Select(Text.Split(s2, " "), each _ <> ""),
            n = List.Count(parts)
        in
            n,

    // --- clean the response columns (wide, before unpivot) ---
    CleanedWide =
        Table.TransformColumns(
            Source,
            {
                {"SectionAResponse", StripHtmlSafe, type text},
                {"SectionBResponse", StripHtmlSafe, type text},
                {"SectionCResponse", StripHtmlSafe, type text},
                {"SectionDResponse", StripHtmlSafe, type text},
                {"SectionEResponse", StripHtmlSafe, type text}
            },
            null,
            MissingField.Error
        ),

    // --- filter validation rows: grade only matched_unique ---
    ValidationFiltered =
        if Table.HasColumns(Validation, {"__join_status"}) then
            Table.SelectRows(Validation, each [__join_status] = "matched_unique")
        else
            Validation,

    // --- map for join (must include submission_id) ---
    ValidationMap =
        if Table.HasColumns(ValidationFiltered, {"User", "__key", "submission_id"}) then
            Table.Distinct(Table.SelectColumns(ValidationFiltered, {"User", "__key", "submission_id"}))
        else
            error "The 'validation' table must contain columns 'User', '__key', and 'submission_id'.",

    // --- bring __key and submission_id onto the cleaned table via User ---
    WithJoinFields =
        if Table.HasColumns(CleanedWide, {"User"}) then
            Table.ExpandTableColumn(
                Table.NestedJoin(CleanedWide, {"User"}, ValidationMap, {"User"}, "__v", JoinKind.LeftOuter),
                "__v",
                {"__key", "submission_id"},
                {"__key", "submission_id"}
            )
        else
            error "The source table 'Table_raw' must contain a 'User' column to join to validation.",

    // --- filter: keep only rows that successfully got a submission_id (and key) ---
    Eligible =
        Table.SelectRows(
            WithJoinFields,
            each
                [__key] <> null and Text.Trim(Text.From([__key])) <> ""
                and [submission_id] <> null and Text.Trim(Text.From([submission_id])) <> ""
        ),

    // --- add per-submission anonymised handle (stable within this workbook/run) ---
    WithRowId =
        Table.ReorderColumns(
            Table.AddIndexColumn(Eligible, "__row_id", 1, 1, Int64.Type),
            List.Combine({{"__row_id"}, List.RemoveItems(Table.ColumnNames(Eligible), {"__row_id"})})
        ),

    // --- unpivot components to long form (one row per submission × component) ---
    ResponseColumns = {"SectionAResponse", "SectionBResponse", "SectionCResponse", "SectionDResponse", "SectionEResponse"},

    Long0 =
        Table.Unpivot(
            WithRowId,
            ResponseColumns,
            "component_source_column",
            "cleaned_response_text"
        ),

    // --- derive a stable component_id from the column name ---
    WithComponentId =
        Table.AddColumn(
            Long0,
            "component_id",
            each
                let
                    col = [component_source_column],
                    // e.g., "SectionAResponse" -> "A"
                    afterSection = if col = null then null else try Text.AfterDelimiter(col, "Section") otherwise null,
                    letter = if afterSection = null then null else try Text.BeforeDelimiter(afterSection, "Response") otherwise null
                in
                    if letter = null then null else "section_" & Text.Lower(letter),
            type text
        ),

    // --- prepend +++row_id=... to the response text (optional but keeps your current prompt/tracing convention) ---
    WithRowTaggedText =
        Table.TransformColumns(
            WithComponentId,
            {
                {
                    "cleaned_response_text",
                    (x as nullable text) as nullable text =>
                        if x = null then null else ("+++row_id=" & Text.From([__row_id]) & "#(lf)" & Text.From(x)),
                    type text
                }
            }
        ),

    // --- compute word count per canonical unit (submission × component) ---
    WithWC =
        Table.AddColumn(
            WithRowTaggedText,
            "word_count",
            each WordCount([cleaned_response_text]),
            Int64.Type
        ),

    // --- final column order (canonical long dataset) ---
    Output =
        Table.SelectColumns(
            WithWC,
            {
                "__row_id",
                "submission_id",
                "__key",

                "component_id",
                "component_source_column",

                "cleaned_response_text",
                "word_count",

                // keep metadata (optional but useful)
                "User",
                "Username",
                "Email address",
                "Time added",
                "Time modified",
                "Tags"
            }
        )
in
    Output