/*
===============================================================================
Stage 0 — cleaned_entries (Canonical Long Dataset Builder)

Purpose:
- Cleans LMS export text
- Joins to validation roster
- Ensures submission_id exists
- Excludes no_match students
- Converts wide LMS export → long canonical format
- Produces one row per (submission × component)

This is the canonical Stage-0 dataset for downstream grading.
===============================================================================
*/

let
    // ------------------------------------------------------------------------
    // SOURCE TABLES
    // ------------------------------------------------------------------------

    Source = Excel.CurrentWorkbook(){[Name="Table_raw"]}[Content],
    Validation = Excel.CurrentWorkbook(){[Name="validation"]}[Content],

    // ------------------------------------------------------------------------
    // TEXT CLEANING HELPERS (UNCHANGED FROM YOUR WORKFLOW)
    // ------------------------------------------------------------------------

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
            Replacements = {
                {"¬†", " "}, {"‚Äî", "—"}, {"‚Äú", "“"}, {"‚Äù", "”"},
                {"‚Äò", "‘"}, {"‚Äô", "’"}, {Character.FromNumber(160), " "}
            },
            s1 =
                if t = null then null
                else List.Accumulate(Replacements, t, (state, pair) => Text.Replace(state, pair{0}, pair{1})),
            s2 = if s1 = null then null else Text.Trim(Text.Clean(s1))
        in
            s2,

    StripTagsFallback = (t as nullable text) as nullable text =>
        let
            parts = if t = null then {} else Text.Split(t, "<"),
            kept = List.Transform(parts, (p) => if Text.Contains(p, ">") then Text.AfterDelimiter(p, ">") else p),
            combined = Text.Combine(kept, ""),
            cleaned = Text.Trim(Text.Clean(combined))
        in
            cleaned,

    StripHtmlSafe = (raw as nullable any) as nullable text =>
        let
            t0 = if raw = null then null else Text.From(raw),
            norm = NormaliseHtml(t0),
            sane0 = SanitiseMojibake(norm),
            br = if sane0 = null then null else Text.Replace(Text.Replace(Text.Replace(sane0, "<br />", "#(lf)"), "<br/>", "#(lf)"), "<br>", "#(lf)"),
            wrapped = if br = null then null else "<div>" & br & "</div>",
            parsed =
                try
                    let
                        nodes = Html.Table(wrapped, {{"t", "//text()"}}),
                        combined = Text.Combine(nodes[t], ""),
                        cleaned = Text.Trim(Text.Clean(combined))
                    in cleaned
                otherwise StripTagsFallback(br),
            sane1 = SanitiseMojibake(parsed),
            delimited = if sane1 = null then null else "+++" & "#(lf)" & sane1 & "#(lf)" & "+++"
        in
            delimited,

    WordCount = (t as nullable text) as nullable number =>
        let
            s1 = if t = null then null else Text.Replace(Text.Replace(Text.Replace(t, "+++", " "), "#(lf)", " "), "#(cr)", " "),
            s2 = if s1 = null then null else Text.Trim(Text.Clean(s1)),
            parts = if s2 = null or s2 = "" then {} else List.Select(Text.Split(s2, " "), each _ <> ""),
            n = List.Count(parts)
        in
            n,

    // ------------------------------------------------------------------------
    // CLEAN RESPONSE TEXT
    // ------------------------------------------------------------------------

    Cleaned =
        Table.TransformColumns(
            Source,
            {
                {"SectionAResponse", StripHtmlSafe, type text},
                {"SectionBResponse", StripHtmlSafe, type text},
                {"SectionCResponse", StripHtmlSafe, type text},
                {"SectionDResponse", StripHtmlSafe, type text},
                {"SectionEResponse", StripHtmlSafe, type text}
            }
        ),

    // ------------------------------------------------------------------------
    // VALIDATION PREPARATION
    // ------------------------------------------------------------------------

    ValidationFiltered =
        Table.SelectRows(Validation, each [__join_status] = "matched_unique"),

    ValidationWithSubmissionId =
        if Table.HasColumns(ValidationFiltered, {"submission_id"}) then
            ValidationFiltered
        else
            Table.AddColumn(
                ValidationFiltered,
                "submission_id",
                each
                    let
                        s = Text.From([GW.Identifier]),
                        digits = Text.Select(s, {"0".."9"})
                    in digits,
                type text
            ),

    ValidationMap =
        Table.Distinct(
            Table.SelectColumns(
                ValidationWithSubmissionId,
                {"User", "submission_id"}
            )
        ),

    // ------------------------------------------------------------------------
    // JOIN CLEANED DATA WITH ROSTER
    // ------------------------------------------------------------------------

    Joined =
        Table.NestedJoin(Cleaned, {"User"}, ValidationMap, {"User"}, "__v", JoinKind.Inner),

    Expanded =
        Table.ExpandTableColumn(Joined, "__v", {"submission_id"}),

    // ------------------------------------------------------------------------
    // ADD ROW ID
    // ------------------------------------------------------------------------

    WithRowId = Table.AddIndexColumn(Expanded, "__row_id", 1, 1, Int64.Type),

    // ------------------------------------------------------------------------
    // TAG RESPONSES WITH ROW ID
    // ------------------------------------------------------------------------

    AddPrefix = (txt as nullable text, rid as number) =>
        if txt = null then null else "+++row_id=" & Text.From(rid) & "#(lf)" & txt,

    Prefixed =
        Table.TransformRows(
            WithRowId,
            (r) =>
                Record.TransformFields(
                    r,
                    {
                        {"SectionAResponse", (x) => AddPrefix(x, r[__row_id])},
                        {"SectionBResponse", (x) => AddPrefix(x, r[__row_id])},
                        {"SectionCResponse", (x) => AddPrefix(x, r[__row_id])},
                        {"SectionDResponse", (x) => AddPrefix(x, r[__row_id])},
                        {"SectionEResponse", (x) => AddPrefix(x, r[__row_id])}
                    }
                )
        ),

    PrefixedTable = Table.FromRecords(Prefixed),

    // ------------------------------------------------------------------------
    // UNPIVOT → LONG FORMAT
    // ------------------------------------------------------------------------

    Unpivoted =
        Table.Unpivot(
            PrefixedTable,
            {
                "SectionAResponse",
                "SectionBResponse",
                "SectionCResponse",
                "SectionDResponse",
                "SectionEResponse"
            },
            "component_id",
            "response_text"
        ),

    // ------------------------------------------------------------------------
    // ADD WORD COUNT
    // ------------------------------------------------------------------------

    WithWC = Table.AddColumn(Unpivoted, "response_wc", each WordCount([response_text]), Int64.Type),

    // ------------------------------------------------------------------------
    // FINAL CANONICAL STRUCTURE
    // ------------------------------------------------------------------------

    Final =
        Table.SelectColumns(
            WithWC,
            {
                "submission_id",
                "__row_id",
                "component_id",
                "response_text",
                "response_wc"
            }
        )

in
    Final