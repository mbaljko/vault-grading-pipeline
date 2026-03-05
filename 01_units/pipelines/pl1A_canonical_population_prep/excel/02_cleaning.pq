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
                {"‚Äò", "‘"}, {"‚Äô", "’"}, {Character.FromNumber(160), " "}   // NBSP
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

            // Normalise common line break tags to actual line breaks BEFORE tag stripping
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

    // ------------------------------------------------------------------------
    // ROBUST "EFFECTIVELY BLANK" TEST
    // Removes common whitespace + zero-width characters before testing length.
    // ------------------------------------------------------------------------
    RemoveWhitespaceAndZeroWidth = (t as nullable text) as nullable text =>
        let
            s0 = if t = null then null else t,
            // remove typical whitespace
            s1 =
                if s0 = null then
                    null
                else
                    Text.Remove(
                        s0,
                        {
                            " ", "#(tab)", "#(lf)", "#(cr)",
                            Character.FromNumber(160),     // NBSP
                            Character.FromNumber(65279),   // BOM / zero-width no-break space
                            Character.FromNumber(8203),    // zero-width space
                            Character.FromNumber(8204),    // zero-width non-joiner
                            Character.FromNumber(8205)     // zero-width joiner
                        }
                    )
        in
            s1,

    IsEffectivelyBlank = (t as nullable text) as logical =>
        let
            s0 = if t = null then null else Text.Clean(t),
            s1 = RemoveWhitespaceAndZeroWidth(s0),
            out = (s1 = null) or (Text.Length(s1) = 0)
        in
            out,

    // ------------------------------------------------------------------------
    // PRESENCE CLASSIFIER
    // - NULL: raw cell is null (missing)
    // - EMPTY: raw cell is exactly ""
    // - BLANKS: raw cell contains only whitespace/zero-width (pre-clean)
    // - EMPTY_AFTER_CLEANING: raw had content, but cleaning stripped it to blank (e.g., HTML scaffolding only)
    // - NONEMPTY: cleaned text contains evidence-bearing characters
    // ------------------------------------------------------------------------
    ClassifyPresence = (raw as nullable any, cleaned as nullable text) as text =>
        let
            rawTxt = if raw = null then null else Text.From(raw),
            rawIsNull = (raw = null),
            rawIsEmpty = (rawTxt <> null and rawTxt = ""),
            rawIsBlanksOnly = (rawTxt <> null and (rawTxt <> "") and IsEffectivelyBlank(rawTxt)),
            cleanedIsBlank = IsEffectivelyBlank(cleaned),
            status =
                if rawIsNull then "NULL"
                else if rawIsEmpty then "EMPTY"
                else if rawIsBlanksOnly then "BLANKS"
                else if cleanedIsBlank then "EMPTY_AFTER_CLEANING"
                else "NONEMPTY"
        in
            status,

    WordCount = (t as nullable text) as nullable number =>
        let
            s1 = if t = null then null else Text.Replace(Text.Replace(Text.Replace(t, "+++", " "), "#(lf)", " "), "#(cr)", " "),
            s2 = if s1 = null then null else Text.Trim(Text.Clean(s1)),
            parts = if s2 = null or s2 = "" then {} else List.Select(Text.Split(s2, " "), each _ <> ""),
            n = List.Count(parts)
        in
            n,

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
    // Keep BOTH raw and cleaned, so presence classification can distinguish cases.
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
    WithClean =
        Table.AddColumn(
            Unpivoted,
            "response_text_clean",
            each StripHtmlFastPlain([response_text_raw]),
            type text
        ),

    // ------------------------------------------------------------------------
    // CLASSIFY PRESENCE USING RAW + CLEANED
    // ------------------------------------------------------------------------
    WithPresence =
        Table.AddColumn(
            WithClean,
            "response_presence",
            each ClassifyPresence([response_text_raw], [response_text_clean]),
            type text
        ),

    // ------------------------------------------------------------------------
    // PREFIX WITH submission_id AND PRESERVE NULL/EMPTY/BLANKS/EMPTY_AFTER_CLEANING
    // Desired:
    // +++submission_id=7835077
    // +++
    // Currently, ...
    // +++
    // ------------------------------------------------------------------------
    AddSubmissionPrefix = (cleaned as nullable text, sid as nullable text, presence as text) as nullable text =>
        let
            payload =
                if presence = "NULL" then "<<NULL>>"
                else if presence = "EMPTY" then "<<EMPTY>>"
                else if presence = "BLANKS" then "<<BLANKS>>"
                else if presence = "EMPTY_AFTER_CLEANING" then "<<EMPTY_AFTER_CLEANING>>"
                else cleaned
        in
            "+++submission_id=" & Text.From(sid) & "#(lf)"
            & "+++" & "#(lf)"
            & payload & "#(lf)"
            & "+++",

    Prefixed =
        Table.AddColumn(
            WithPresence,
            "response_text_prefixed",
            each AddSubmissionPrefix([response_text_clean], [submission_id], [response_presence]),
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