let
    // -----------------------------------------
    // Source (long format): one row per submission_id × component_id
    // -----------------------------------------
    Source0 = Excel.CurrentWorkbook(){[Name="cleaned_entries"]}[Content],
    Source = Table.Buffer(Source0),

    // -----------------------------------------
    // Required columns check
    // -----------------------------------------
    RequiredCols = {"submission_id", "component_id", "response_wc"},
    MissingCols = List.Difference(RequiredCols, Table.ColumnNames(Source)),
    _assert =
        if List.Count(MissingCols) = 0 then
            true
        else
            error "Expected columns missing in 'cleaned_entries': " & Text.Combine(MissingCols, ", "),

    // -----------------------------------------
    // Type normalisation
    // -----------------------------------------
    Typed =
        Table.TransformColumnTypes(
            Source,
            {
                {"submission_id", type text},
                {"component_id", type text},
                {"response_wc", Int64.Type}
            }
        ),

    // -----------------------------------------
    // Composite key for long-format unit identity
    // -----------------------------------------
    WithUnitKey =
        Table.AddColumn(
            Typed,
            "__unit_key",
            each Text.From([submission_id]) & "::" & Text.From([component_id]),
            type text
        ),

    // -----------------------------------------
    // Helper: sample m keys by interior-uniform spacing over wc-ranked rows
    // (expects a single component_id group table)
    // -----------------------------------------
    SampleInteriorUniformKeys = (t as table, wcCol as text, keyCol as text, m as number) as list =>
        let
            // Keep rows where wc is a number (0 is allowed)
            t0 =
                Table.SelectRows(
                    Table.SelectColumns(t, {keyCol, wcCol}),
                    each Record.Field(_, wcCol) <> null and Value.Is(Record.Field(_, wcCol), type number)
                ),

            t1 = Table.Sort(t0, {{wcCol, Order.Ascending}}),
            n = Table.RowCount(t1),

            // Drop shortest and longest
            interior =
                if n <= 2 then
                    #table({keyCol, wcCol}, {})
                else
                    Table.FirstN(Table.Skip(t1, 1), n - 2),

            nInt = Table.RowCount(interior),

            idxToKeep =
                if nInt = 0 then
                    {}
                else if nInt <= m then
                    {0..nInt - 1}
                else
                    List.Transform({0..m - 1}, each Number.IntegerDivide(_ * (nInt - 1), (m - 1))),

            withIdx = Table.AddIndexColumn(interior, "__i", 0, 1, Int64.Type),
            picked = Table.SelectRows(withIdx, each List.Contains(idxToKeep, [__i])),
            keys = Table.Column(picked, keyCol)
        in
            keys,

    // -----------------------------------------
    // Compute sampled keys per component_id
    // -----------------------------------------
    Grouped =
        Table.Group(
            WithUnitKey,
            {"component_id"},
            {
                {
                    "__sample_keys",
                    (g as table) => SampleInteriorUniformKeys(g, "response_wc", "__unit_key", 30),
                    type list
                }
            }
        ),

    SampleKeyList = List.Combine(Grouped[__sample_keys]),

    // -----------------------------------------
    // Convert sampled keys to a table and join (faster than List.Contains)
    // -----------------------------------------
    SampleKeyTable =
        Table.Distinct(
            Table.FromList(
                SampleKeyList,
                Splitter.SplitByNothing(),
                {"__unit_key"}
            )
        ),

    SampleKeyTableBuffered = Table.Buffer(SampleKeyTable),

    Joined =
        Table.NestedJoin(
            WithUnitKey,
            {"__unit_key"},
            SampleKeyTableBuffered,
            {"__unit_key"},
            "__hit",
            JoinKind.LeftOuter
        ),

    WithFlag =
        Table.AddColumn(
            Joined,
            "sample_flag",
            each if Table.RowCount([__hit]) > 0 then "F" else null,
            type text
        ),

    Output =
        Table.RemoveColumns(WithFlag, {"__unit_key", "__hit"})
in
    Output