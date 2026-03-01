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

    // --- clean the response columns ---
    Cleaned =
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

    // --- filter validation rows: exclude no_match ---
    ValidationFiltered =
        if Table.HasColumns(Validation, {"__join_status"}) then
            Table.SelectRows(Validation, each [__join_status] <> "no_match")
        else
            Validation,

    // --- if validation doesn't have __key, create it (stable, deterministic) ---
    ValidationWithKey =
        if Table.HasColumns(ValidationFiltered, {"__key"}) then
            ValidationFiltered
        else
            Table.AddColumn(
                ValidationFiltered,
                "__key",
                each
                    let
                        u = try Text.From([User]) otherwise null,
                        u1 = if u = null then null else Text.Trim(u),
                        u2 = if u1 = null then null else Text.Combine(List.Select(Text.SplitAny(u1, " #(tab)"), each _ <> ""), " "),
                        u3 = if u2 = null then null else Text.Lower(Text.Replace(Text.Replace(u2, "#(lf)", " "), "#(cr)", " "))
                    in
                        if u3 = null or u3 = "" then null else "user:" & u3,
                type text
            ),

    // --- map for join ---
    ValidationMap =
        if Table.HasColumns(ValidationWithKey, {"User", "__key"}) then
            Table.Distinct(Table.SelectColumns(ValidationWithKey, {"User", "__key"}))
        else
            error "The 'validation' table must contain column 'User'.",

    // --- bring __key onto the cleaned table via User ---
    WithKey =
        if Table.HasColumns(Cleaned, {"User"}) then
            Table.ExpandTableColumn(
                Table.NestedJoin(Cleaned, {"User"}, ValidationMap, {"User"}, "__v", JoinKind.LeftOuter),
                "__v",
                {"__key"},
                {"__key"}
            )
        else
            error "The source table 'Table_raw' must contain a 'User' column to join to validation.",

    // --- filter: keep only rows that successfully got a key ---
    Filtered =
        Table.SelectRows(WithKey, each [__key] <> null and Text.Trim(Text.From([__key])) <> ""),

    // --- add unique numeric row id as FIRST column ---
    WithRowId =
        Table.ReorderColumns(
            Table.AddIndexColumn(Filtered, "__row_id", 1, 1, Int64.Type),
            List.Combine({{"__row_id"}, List.RemoveItems(Table.ColumnNames(Filtered), {"__row_id"})})
        ),

    // --- prepend +++row_id=value to response columns (row-wise so __row_id is in scope) ---
    WithRowTaggedResponses =
        let
            t = WithRowId,
            colOrder = Table.ColumnNames(t),
            rows = Table.ToRecords(t),
            rows2 =
                List.Transform(
                    rows,
                    (r as record) as record =>
                        let
                            rid = Text.From(Record.Field(r, "__row_id")),
                            prefix = "+++row_id=" & rid & "#(lf)",
                            r2 =
                                Record.TransformFields(
                                    r,
                                    {
                                        {"SectionAResponse", (x) => if x = null then null else prefix & Text.From(x)},
                                        {"SectionBResponse", (x) => if x = null then null else prefix & Text.From(x)},
                                        {"SectionCResponse", (x) => if x = null then null else prefix & Text.From(x)},
                                        {"SectionDResponse", (x) => if x = null then null else prefix & Text.From(x)},
                                        {"SectionEResponse", (x) => if x = null then null else prefix & Text.From(x)}
                                    }
                                )
                        in
                            r2
                ),
            out0 = Table.FromRecords(rows2, colOrder),
            out = Table.ReorderColumns(out0, colOrder)
        in
            out,

    // --- add word counts AFTER each section column ---
    WithA_WC =
        Table.AddColumn(WithRowTaggedResponses, "SectionAResponse__wc", each WordCount([SectionAResponse]), Int64.Type),
    ReorderA =
        let
            cols = Table.ColumnNames(WithA_WC),
            insertPos = List.PositionOf(cols, "SectionAResponse") + 1,
            colsNoNew = List.RemoveItems(cols, {"SectionAResponse__wc"}),
            newOrder = List.InsertRange(colsNoNew, insertPos, {"SectionAResponse__wc"})
        in
            Table.ReorderColumns(WithA_WC, newOrder),

    WithB_WC =
        Table.AddColumn(ReorderA, "SectionBResponse__wc", each WordCount([SectionBResponse]), Int64.Type),
    ReorderB =
        let
            cols = Table.ColumnNames(WithB_WC),
            insertPos = List.PositionOf(cols, "SectionBResponse") + 1,
            colsNoNew = List.RemoveItems(cols, {"SectionBResponse__wc"}),
            newOrder = List.InsertRange(colsNoNew, insertPos, {"SectionBResponse__wc"})
        in
            Table.ReorderColumns(WithB_WC, newOrder),

    WithC_WC =
        Table.AddColumn(ReorderB, "SectionCResponse__wc", each WordCount([SectionCResponse]), Int64.Type),
    ReorderC =
        let
            cols = Table.ColumnNames(WithC_WC),
            insertPos = List.PositionOf(cols, "SectionCResponse") + 1,
            colsNoNew = List.RemoveItems(cols, {"SectionCResponse__wc"}),
            newOrder = List.InsertRange(colsNoNew, insertPos, {"SectionCResponse__wc"})
        in
            Table.ReorderColumns(WithC_WC, newOrder),

    WithD_WC =
        Table.AddColumn(ReorderC, "SectionDResponse__wc", each WordCount([SectionDResponse]), Int64.Type),
    ReorderD =
        let
            cols = Table.ColumnNames(WithD_WC),
            insertPos = List.PositionOf(cols, "SectionDResponse") + 1,
            colsNoNew = List.RemoveItems(cols, {"SectionDResponse__wc"}),
            newOrder = List.InsertRange(colsNoNew, insertPos, {"SectionDResponse__wc"})
        in
            Table.ReorderColumns(WithD_WC, newOrder),

    WithE_WC =
        Table.AddColumn(ReorderD, "SectionEResponse__wc", each WordCount([SectionEResponse]), Int64.Type),
    ReorderE =
        let
            cols = Table.ColumnNames(WithE_WC),
            insertPos = List.PositionOf(cols, "SectionEResponse") + 1,
            colsNoNew = List.RemoveItems(cols, {"SectionEResponse__wc"}),
            newOrder = List.InsertRange(colsNoNew, insertPos, {"SectionEResponse__wc"})
        in
            Table.ReorderColumns(WithE_WC, newOrder)

in
    ReorderE