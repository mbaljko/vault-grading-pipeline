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

    // Converts HTML-ish input to plain text, keeping line breaks from <br>, </p>
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

    // ------------------------------------------------------------------------
    // ROBUST "EFFECTIVELY BLANK" TEST (WHITESPACE + ZERO-WIDTH)
    // ------------------------------------------------------------------------
    RemoveWhitespaceAndZeroWidth = (t as nullable text) as nullable text =>
        let
            s0 = if t = null then null else t,
            s1 =
                if s0 = null then
                    null
                else
                    Text.Remove(
                        s0,
                        {
                            " ", "#(tab)", "#(lf)", "#(cr)",
                            Character.FromNumber(160),     // NBSP
                            Character.FromNumber(65279),   // BOM / ZWNBSP
                            Character.FromNumber(8203),    // ZWSP
                            Character.FromNumber(8204),    // ZWNJ
                            Character.FromNumber(8205)     // ZWJ
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
    // ------------------------------------------------------------------------
    ClassifyPresence = (raw as nullable any) as record =>
        let
            rawTxt = if raw = null then null else Text.From(raw),

            rawIsNull = (raw = null),
            rawIsEmpty = (rawTxt <> null and rawTxt = ""),
            rawIsBlanksOnly = (rawTxt <> null and (rawTxt <> "") and IsEffectivelyBlank(rawTxt)),

            cleanedPlain = StripHtmlFastPlain(raw),
            cleanedIsBlank = IsEffectivelyBlank(cleanedPlain),

            status =
                if rawIsNull then "NULL"
                else if rawIsEmpty then "EMPTY"
                else if rawIsBlanksOnly then "BLANKS"
                else if cleanedIsBlank then "EMPTY_AFTER_CLEANING"
                else "NONEMPTY"
        in
            [
                response_text_clean = cleanedPlain,
                response_presence = status
            ],

    // Word count is computed on the PAYLOAD ONLY (not on wrappers)
    WordCountPayload = (t as nullable text) as number =>
        let
            out =
                if t = null or Text.Trim(t) = "" then
                    0
                else
                    let
                        s1 = Text.Replace(Text.Replace(t, "#(lf)", " "), "#(cr)", " "),
                        s2 = Text.Trim(Text.Clean(s1)),
                        parts = if s2 = "" then {} else List.Select(Text.Split(s2, " "), each _ <> ""),
                        n = List.Count(parts)
                    in
                        n
        in
            out,

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
    // ENFORCED LONG BUILD (GUARANTEES ONE ROW PER submission_id × component_id)
    // ------------------------------------------------------------------------
    WithPairs =
        Table.AddColumn(
            Expanded,
            "__pairs",
            each
                List.Transform(
                    ResponseColumns,
                    (c) =>
                        [
                            component_id = c,
                            response_text_raw = Record.FieldOrDefault(_, c, null)
                        ]
                ),
            type list
        ),

    ExpandedPairs =
        Table.ExpandListColumn(WithPairs, "__pairs"),

    ExpandedPairRecord =
        Table.ExpandRecordColumn(
            ExpandedPairs,
            "__pairs",
            {"component_id", "response_text_raw"},
            {"component_id", "response_text_raw"}
        ),

    // ------------------------------------------------------------------------
    // CLEAN + PRESENCE (FROM RAW)
    // ------------------------------------------------------------------------
    WithPresenceRecord =
        Table.AddColumn(
            ExpandedPairRecord,
            "__presence",
            each ClassifyPresence([response_text_raw]),
            type record
        ),

    ExpandedPresence =
        Table.ExpandRecordColumn(
            WithPresenceRecord,
            "__presence",
            {"response_text_clean", "response_presence"},
            {"response_text_clean", "response_presence"}
        ),

    // ------------------------------------------------------------------------
    // PAYLOAD POLICY (PRESERVE NULL/EMPTY/BLANKS EXPLICITLY)
    // ------------------------------------------------------------------------
    WithPayload =
        Table.AddColumn(
            ExpandedPresence,
            "response_payload",
            each
                if [response_presence] = "NULL" then
                    ""          // payload must be empty string for NULL
                else if [response_presence] = "EMPTY" then
                    "<<EMPTY>>"
                else if [response_presence] = "BLANKS" then
                    "<<BLANKS>>"
                else if [response_presence] = "EMPTY_AFTER_CLEANING" then
                    "<<EMPTY_AFTER_CLEANING>>"
                else
                    Text.From([response_text_clean]),
            type text
        ),

    // ------------------------------------------------------------------------
    // WRAP WITH submission_id (ALWAYS, INCLUDING NULL)
    //
    // Exact desired wrapper:
    // +++submission_id=7835077
    // +++
    // <payload>   (may be "")
    // +++
    // (ensure line break after submission_id line AND after closing +++)
    // ------------------------------------------------------------------------
    Wrap = (payload as text, sid as nullable text) as text =>
        "+++submission_id=" & Text.From(sid) & "#(lf)"
        & "+++" & "#(lf)"
        & payload & "#(lf)"
        & "+++" & "#(lf)",

    WithResponseText =
        Table.AddColumn(
            WithPayload,
            "response_text",
            each Wrap([response_payload], [submission_id]),
            type text
        ),

    // ------------------------------------------------------------------------
    // WORDCOUNT POLICY
    // - Wordcount is computed on the payload only.
    // - For NULL (payload="") => 0
    // ------------------------------------------------------------------------
    WithWC =
        Table.AddColumn(
            WithResponseText,
            "response_wc",
            each WordCountPayload([response_payload]),
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
                "response_text",
                "response_wc"
            }
        )
in
    Final