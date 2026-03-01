let
    Raw = Excel.CurrentWorkbook(){[Name="Table_raw"]}[Content],
    GW  = Excel.CurrentWorkbook(){[Name="grading_worksheet"]}[Content],

    NormNameKey = (t as nullable any) as nullable text =>
        let
            s0 = if t = null then null else Text.From(t),
            s1 = if s0 = null then null else Text.Replace(s0, Character.FromNumber(160), " "),
            s2 = if s1 = null then null else Text.Trim(Text.Clean(s1)),
            s3 = if s2 = null then null else Text.Replace(s2, "  ", " "),
            s4 = if s3 = null then null else Text.Replace(s3, "  ", " "),
            s5 = if s4 = null then null else Text.Lower(s4)
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

    JoinStatus =
        Table.AddColumn(
            ExpandedResolved,
            "__join_status",
            each
                if [__gw_name_count] = null then "no_match"
                else if [__gw_name_count] = 1 then "matched_unique"
                else "matched_ambiguous",
            type text
        ),

    // Output only identifier + join diagnostics
    Output =
        Table.SelectColumns(
            JoinStatus,
            {
                // from database export
                "User",
                "Username",

                // from grading worksheet (only when unique match)
                "GW.Full name",
                "GW.Identifier",

                // diagnostics
                "__join_status",
                "__gw_name_count"
            }
        )
in
    Output