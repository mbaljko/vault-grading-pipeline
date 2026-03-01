let
    Raw = Excel.CurrentWorkbook(){[Name="Table_raw"]}[Content],
    GW  = Excel.CurrentWorkbook(){[Name="grading_worksheet"]}[Content],

    // Strip leading non-alphanumeric noise (e.g., leading "." seen in some exports)
    StripLeadingJunk = (s as nullable text) as nullable text =>
        let
            s0 = if s = null then null else Text.Trim(s),
            chars = if s0 = null then null else Text.ToList(s0),
            allowed = List.Combine({{"a".."z"}, {"0".."9"}}),
            kept = if chars = null then null else List.SkipWhile(chars, each not List.Contains(allowed, Text.Lower(_))),
            out = if kept = null then null else Text.Combine(kept)
        in
            out,

    // Collapse multiple spaces deterministically
    CollapseSpaces = (s as nullable text) as nullable text =>
        let
            s0 = if s = null then null else s,
            s1 = if s0 = null then null else
                 List.Accumulate({1..10}, s0, (state, _) => Text.Replace(state, "  ", " "))
        in
            s1,

    NormNameKey = (t as nullable any) as nullable text =>
        let
            s0 = if t = null then null else Text.From(t),
            s1 = if s0 = null then null else Text.Replace(s0, Character.FromNumber(160), " "),
            s2 = if s1 = null then null else Text.Trim(Text.Clean(s1)),
            s3 = if s2 = null then null else CollapseSpaces(s2),
            s4 = if s3 = null then null else Text.Lower(s3),
            s5 = if s4 = null then null else StripLeadingJunk(s4)
        in
            s5,

    RawKeyed =
        Table.AddColumn(
            Raw,
            "__key_name",
            each NormNameKey(Record.FieldOrDefault(_, "User", null)),
            type text
        ),

    GWKeyed =
        Table.AddColumn(
            GW,
            "__key_name",
            each NormNameKey(Record.FieldOrDefault(_, "Full name", null)),
            type text
        ),

    GWNameCounts =
        Table.Group(
            GWKeyed,
            {"__key_name"},
            {
                {"__gw_name_count", each Table.RowCount(_), Int64.Type},
                {"__gw_rows", each _, type table}
            }
        ),

    RawWithCounts =
        Table.NestedJoin(
            RawKeyed,
            {"__key_name"},
            GWNameCounts,
            {"__key_name"},
            "GWCount",
            JoinKind.LeftOuter
        ),

    ExpandedCounts =
        Table.ExpandTableColumn(
            RawWithCounts,
            "GWCount",
            {"__gw_name_count", "__gw_rows"},
            {"__gw_name_count", "__gw_rows"}
        ),

    ResolveGW =
        Table.AddColumn(
            ExpandedCounts,
            "GWResolved",
            each
                let
                    c = [__gw_name_count],
                    t = [__gw_rows]
                in
                    if c = null then null
                    else if c = 1 then Table.FirstN(t, 1)
                    else null,
            type table
        ),

    ExpandedResolved =
        Table.ExpandTableColumn(
            ResolveGW,
            "GWResolved",
            {"Identifier", "Full name"},
            {"GW.Identifier", "GW.Full name"}
        ),

    // Make the grading-sheet Identifier the explicit stable submission_id
    WithSubmissionId =
        Table.AddColumn(
            ExpandedResolved,
            "submission_id",
            each [GW.Identifier],
            type text
        ),

    // Tighten join_status vocabulary so only matched_unique is eligible for grading
    JoinStatus =
        Table.AddColumn(
            WithSubmissionId,
            "__join_status",
            each
                if [__gw_name_count] = null then "no_match"
                else if [__gw_name_count] = 1 and [submission_id] <> null then "matched_unique"
                else "excluded_ambiguous",
            type text
        ),

    // Output only identifier + join diagnostics (now includes explicit submission_id and __key_name for audit)
    Output =
        Table.SelectColumns(
            JoinStatus,
            {
                // from database export
                "User",
                "Username",

                // normalised join key (audit)
                "__key_name",

                // from grading worksheet (only when unique match)
                "GW.Full name",
                "GW.Identifier",
                "submission_id",

                // diagnostics
                "__join_status",
                "__gw_name_count"
            }
        )
in
    Output