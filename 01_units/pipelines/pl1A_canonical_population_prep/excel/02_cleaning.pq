/*
===============================================================================
Stage 0 — cleaned_entries (Canonical Long Dataset Builder) — dynamic components

Purpose:
- Cleans LMS export text for all response fields (columns before the fixed tail)
- Joins to validation roster (matched_unique only)
- Ensures submission_id exists (from validation)
- Converts wide LMS export → long canonical format
- Produces one row per (submission_id × component_id)
===============================================================================
*/

let
    // ------------------------------------------------------------------------
    // SOURCE TABLES
    // ------------------------------------------------------------------------
    Source = Excel.CurrentWorkbook(){[Name="Table_raw"]}[Content],
    Validation = Excel.CurrentWorkbook(){[Name="validation"]}[Content],

    // ------------------------------------------------------------------------
    // RESPONSE-FIELD DISCOVERY (DYNAMIC)
    // ------------------------------------------------------------------------
    TailCols = {"Tags", "User", "Username", "Email address", "Time added", "Time modified"},
    AllCols = Table.ColumnNames(Source),

    TailPositions =
        List.RemoveNulls(
            List.Transform(
                TailCols,
                (c) =>
                    let p = List.PositionOf(AllCols, c)
                    in if p = -1 then null else p
            )
        ),

    TailStart =
        if List.Count(TailPositions) = 0
        then error "02_cleaning: None of the tail columns were found (Tags/User/Username/Email address/Time added/Time modified). Cannot infer response fields."
        else List.Min(TailPositions),

    ResponseCols =
        if TailStart = 0
        then error "02_cleaning: Tail columns begin at position 0, leaving no response columns to unpivot."
        else List.FirstN(AllCols, TailStart),

    // ------------------------------------------------------------------------
    // TEXT CLEANING HELPERS
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
    // CLEAN RESPONSE TEXT (DYNAMIC COLUMNS)
    // ------------------------------------------------------------------------
    CleanTransforms =
        List.Transform(
            ResponseCols,
            (c) => {c, StripHtmlSafe, type text}
        ),

    Cleaned =
        Table.TransformColumns(
            Source,
            CleanTransforms
        ),

    // ------------------------------------------------------------------------
    // VALIDATION PREPARATION
    // ------------------------------------------------------------------------
    ValidationFiltered =
        Table.SelectRows(Validation, each [__join_status] = "matched_unique"),

    ValidationMap =
        if not Table.HasColumns(ValidationFiltered, {"User", "submission_id"}) then
            error "02_cleaning: validation table must include columns User and submission_id."
        else
            Table.Distinct(
                Table.SelectColumns(
                    ValidationFiltered,
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
    // OPTIONAL DEBUG ROW ID
    // ------------------------------------------------------------------------
    WithRowId = Table.AddIndexColumn(Expanded, "__row_id", 1, 1, Int64.Type),

    AddPrefix = (txt as nullable text, sid as nullable text) as nullable text =>
        if txt = null then null
        else
            "+++submission_id=" & Text.From(sid) & "#(lf)" &
            "+++" & "#(lf)" &
            txt,

    Prefixed =
        Table.TransformRows(
            WithRowId,
            (r) =>
                let
                    sid = r[submission_id],
                    fields = List.Transform(
                        ResponseCols,
                        (c) => {c, (x) => AddPrefix(x, sid)}
                    )
                in
                    Record.TransformFields(r, fields)
        ),

    PrefixedTable = Table.FromRecords(Prefixed),

    // ------------------------------------------------------------------------
    // UNPIVOT → LONG FORMAT
    // ------------------------------------------------------------------------
    Unpivoted =
        Table.Unpivot(
            PrefixedTable,
            ResponseCols,
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
                "component_id",
                "response_text",
                "response_wc",
                "__row_id"
            }
        )
in
    Final