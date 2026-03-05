let
    // ------------------------------------------------------------------------
    // SOURCE TABLES
    // ------------------------------------------------------------------------
    Source = Excel.CurrentWorkbook(){[Name="Table_raw"]}[Content],
    Validation = Excel.CurrentWorkbook(){[Name="validation"]}[Content],

    // ------------------------------------------------------------------------
    // TEXT CLEANING HELPERS (PLAIN TEXT; NO Html.Table)
    // ------------------------------------------------------------------------

    NormaliseHtmlQuotes = (t as nullable text) as nullable text =>
        let
            s0 = t,
            s1 =
                if s0 = null then
                    null
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
                if t = null then
                    null
                else
                    List.Accumulate(Replacements, t, (state, pair) => Text.Replace(state, pair{0}, pair{1})),
            s2 = if s1 = null then null else Text.Trim(Text.Clean(s1))
        in
            s2,

    StripTags = (t as nullable text) as nullable text =>
        let
            s0 = if t = null then null else t,
            parts = if s0 = null then {} else Text.Split(s0, "<"),
            kept = List.Transform(parts, (p) => if Text.Contains(p, ">") then Text.AfterDelimiter(p, ">") else p),
            combined = Text.Combine(kept, ""),
            cleaned = Text.Trim(Text.Clean(combined))
        in
            cleaned,

    StripHtmlFastPlain = (raw as nullable any) as nullable text =>
        let
            t0 = if raw = null then null else Text.From(raw),
            q0 = NormaliseHtmlQuotes(t0),
            s0 = SanitiseMojibake(q0),

            br0 =
                if s0 = null then
                    null
                else
                    Text.Replace(
                        Text.Replace(
                            Text.Replace(
                                Text.Replace(s0, "<br />", "#(lf)"),
                                "<br/>",
                                "#(lf)"
                            ),
                            "<br>",
                            "#(lf)"
                        ),
                        "</p>",
                        "#(lf)"
                    ),

            noTags = StripTags(br0),
            s1 = SanitiseMojibake(noTags)
        in
            s1,

    WordCount = (t as nullable text) as nullable number =>
        let
            s1 = if t = null then null else Text.Replace(Text.Replace(Text.Replace(t, "+++", " "), "#(lf)", " "), "#(cr)", " "),
            s2 = if s1 = null then null else Text.Trim(Text.Clean(s1)),
            parts = if s2 = null or s2 = "" then {} else List.Select(Text.Split(s2, " "), each _ <> ""),
            n = List.Count(parts)
        in
            n,

    // ------------------------------------------------------------------------
    // RESPONSE PRESENCE CLASSIFIER
    // ------------------------------------------------------------------------
    ClassifyPresence = (txt as nullable text) as text =>
        if txt = null then
            "NULL"
        else if txt = "" then
            "EMPTY"
        else if Text.Trim(txt) = "" then
            "BLANKS"
        else
            "NONEMPTY",

    // ------------------------------------------------------------------------
    // VALIDATION PREPARATION (ELIGIBILITY GATE)
    // ------------------------------------------------------------------------
    ValidationFiltered =
        Table.SelectRows(Validation, each [__join_status] = "matched_unique"),

    ValidationMap =
        Table.Distinct(
            Table.SelectColumns(
                ValidationFiltered,
                {"User", "submission_id"}
            )
        ),

    ValidationMapBuffered = Table.Buffer(ValidationMap),

    // ------------------------------------------------------------------------
    // DYNAMIC RESPONSE COLUMN DETECTION (ALL COLUMNS BEFORE "Tags")
    // ------------------------------------------------------------------------
    AllColumns = Table.ColumnNames(Source),
    TagsPos = List.PositionOf(AllColumns, "Tags"),

    ResponseColumns =
        if TagsPos = -1 then
            error "Expected column 'Tags' not found. Cannot infer response columns."
        else
            List.FirstN(AllColumns, TagsPos),

    // ------------------------------------------------------------------------
    // JOIN RAW DATA WITH VALIDATION (KEEP ONLY ELIGIBLE STUDENTS)
    // ------------------------------------------------------------------------
    Joined =
        Table.NestedJoin(Source, {"User"}, ValidationMapBuffered, {"User"}, "__v", JoinKind.Inner),

    Expanded =
        Table.ExpandTableColumn(Joined, "__v", {"submission_id"}, {"submission_id"}),

    // ------------------------------------------------------------------------
    // UNPIVOT → LONG FORMAT (submission_id × component_id)
    // ------------------------------------------------------------------------
    Unpivoted =
        Table.Unpivot(
            Expanded,
            ResponseColumns,
            "component_id",
            "response_text_raw"
        ),

    // ------------------------------------------------------------------------
    // CLEAN RESPONSE TEXT
    // ------------------------------------------------------------------------
    Cleaned =
        Table.TransformColumns(
            Unpivoted,
            {{"response_text_raw", StripHtmlFastPlain, type text}}
        ),

    Renamed =
        Table.RenameColumns(
            Cleaned,
            {{"response_text_raw", "response_text"}}
        ),

    // ------------------------------------------------------------------------
    // CLASSIFY PRESENCE (NULL / EMPTY / BLANKS / NONEMPTY)
    // ------------------------------------------------------------------------
    WithPresence =
        Table.AddColumn(
            Renamed,
            "response_presence",
            each ClassifyPresence([response_text]),
            type text
        ),

    // ------------------------------------------------------------------------
    // PREFIX WITH submission_id AND PRESERVE NULL/EMPTY/BLANKS
    // ------------------------------------------------------------------------
    AddSubmissionPrefix = (txt as nullable text, sid as nullable text) as nullable text =>
        let
            status = ClassifyPresence(txt),
            payload =
                if status = "NULL" then "<<NULL>>"
                else if status = "EMPTY" then "<<EMPTY>>"
                else if status = "BLANKS" then "<<BLANKS>>"
                else txt
        in
            "+++submission_id=" & Text.From(sid) & "#(lf)"
            & "+++" & "#(lf)"
            & payload & "#(lf)"
            & "+++",

    Prefixed =
        Table.AddColumn(
            WithPresence,
            "response_text_prefixed",
            each AddSubmissionPrefix([response_text], [submission_id]),
            type text
        ),

    // ------------------------------------------------------------------------
    // WORD COUNT
    // ------------------------------------------------------------------------
    WithWC =
        Table.AddColumn(
            Prefixed,
            "response_wc",
            each WordCount([response_text_prefixed]),
            Int64.Type
        ),

    // ------------------------------------------------------------------------
    // FINAL CANONICAL STRUCTURE
    // ------------------------------------------------------------------------
    Final =
        Table.SelectColumns(
            WithWC,
            {
                "submission_id",
                "component_id",
                "response_presence",
                "response_text_prefixed",
                "response_wc"
            }
        ),

    FinalRenamed =
        Table.RenameColumns(
            Final,
            {{"response_text_prefixed", "response_text"}}
        )
in
    FinalRenamed