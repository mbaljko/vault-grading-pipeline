let
    // =========================================
    // Source: use the already-prepared table
    // =========================================
    Source = Excel.CurrentWorkbook(){[Name="cleaned_entries"]}[Content],

    // =========================================
    // Ensure __row_id is numeric (safe cast)
    // =========================================
    WithRowIdType =
        if Table.HasColumns(Source, {"__row_id"}) then
            Table.TransformColumnTypes(Source, {{"__row_id", Int64.Type}})
        else
            error "Expected column '__row_id' in table 'cleaned_entries'.",

    // =========================================
    // Helper: sample 30 row_ids by interior-uniform spacing over wc-ranked rows
    // - sort by wc ascending
    // - drop shortest and longest (first and last)
    // - if interior count <= 30, take all interior
    // =========================================
    SampleInteriorUniform = (t as table, wcCol as text, m as number) as list =>
        let
            t0 =
                if Table.HasColumns(t, {"__row_id", wcCol}) then
                    Table.SelectRows(
                        Table.SelectColumns(t, {"__row_id", wcCol}),
                        each Record.Field(_, wcCol) <> null and Value.Is(Record.Field(_, wcCol), type number)
                    )
                else
                    error "Missing required columns for sampling.",

            t1 = Table.Sort(t0, {{wcCol, Order.Ascending}}),
            n = Table.RowCount(t1),

            interior =
                if n <= 2 then
                    #table({"__row_id", wcCol}, {})
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
            ids = picked[__row_id]
        in
            ids,

    // =========================================
    // Compute per-section sample id lists
    // =========================================
    SampleA = SampleInteriorUniform(WithRowIdType, "SectionAResponse__wc", 30),
    SampleB = SampleInteriorUniform(WithRowIdType, "SectionBResponse__wc", 30),
    SampleC = SampleInteriorUniform(WithRowIdType, "SectionCResponse__wc", 30),
    SampleD = SampleInteriorUniform(WithRowIdType, "SectionDResponse__wc", 30),
    SampleE = SampleInteriorUniform(WithRowIdType, "SectionEResponse__wc", 30),

    // =========================================
    // Add empty flag columns (one after each __wc)
    // =========================================

    // A
    WithAFlag =
        if Table.HasColumns(WithRowIdType, {"SectionAResponse__wc"}) then
            Table.AddColumn(WithRowIdType, "SectionAResponse__flag", each null, type text)
        else
            error "Expected column 'SectionAResponse__wc' in table 'cleaned_entries'.",
    ReorderAFlag =
        let
            cols = Table.ColumnNames(WithAFlag),
            insertPos = List.PositionOf(cols, "SectionAResponse__wc") + 1,
            colsNoNew = List.RemoveItems(cols, {"SectionAResponse__flag"}),
            newOrder = List.InsertRange(colsNoNew, insertPos, {"SectionAResponse__flag"})
        in
            Table.ReorderColumns(WithAFlag, newOrder),

    // B
    WithBFlag =
        if Table.HasColumns(ReorderAFlag, {"SectionBResponse__wc"}) then
            Table.AddColumn(ReorderAFlag, "SectionBResponse__flag", each null, type text)
        else
            error "Expected column 'SectionBResponse__wc' in table 'cleaned_entries'.",
    ReorderBFlag =
        let
            cols = Table.ColumnNames(WithBFlag),
            insertPos = List.PositionOf(cols, "SectionBResponse__wc") + 1,
            colsNoNew = List.RemoveItems(cols, {"SectionBResponse__flag"}),
            newOrder = List.InsertRange(colsNoNew, insertPos, {"SectionBResponse__flag"})
        in
            Table.ReorderColumns(WithBFlag, newOrder),

    // C
    WithCFlag =
        if Table.HasColumns(ReorderBFlag, {"SectionCResponse__wc"}) then
            Table.AddColumn(ReorderBFlag, "SectionCResponse__flag", each null, type text)
        else
            error "Expected column 'SectionCResponse__wc' in table 'cleaned_entries'.",
    ReorderCFlag =
        let
            cols = Table.ColumnNames(WithCFlag),
            insertPos = List.PositionOf(cols, "SectionCResponse__wc") + 1,
            colsNoNew = List.RemoveItems(cols, {"SectionCResponse__flag"}),
            newOrder = List.InsertRange(colsNoNew, insertPos, {"SectionCResponse__flag"})
        in
            Table.ReorderColumns(WithCFlag, newOrder),

    // D
    WithDFlag =
        if Table.HasColumns(ReorderCFlag, {"SectionDResponse__wc"}) then
            Table.AddColumn(ReorderCFlag, "SectionDResponse__flag", each null, type text)
        else
            error "Expected column 'SectionDResponse__wc' in table 'cleaned_entries'.",
    ReorderDFlag =
        let
            cols = Table.ColumnNames(WithDFlag),
            insertPos = List.PositionOf(cols, "SectionDResponse__wc") + 1,
            colsNoNew = List.RemoveItems(cols, {"SectionDResponse__flag"}),
            newOrder = List.InsertRange(colsNoNew, insertPos, {"SectionDResponse__flag"})
        in
            Table.ReorderColumns(WithDFlag, newOrder),

    // E
    WithEFlag =
        if Table.HasColumns(ReorderDFlag, {"SectionEResponse__wc"}) then
            Table.AddColumn(ReorderDFlag, "SectionEResponse__flag", each null, type text)
        else
            error "Expected column 'SectionEResponse__wc' in table 'cleaned_entries'.",
    ReorderEFlag =
        let
            cols = Table.ColumnNames(WithEFlag),
            insertPos = List.PositionOf(cols, "SectionEResponse__wc") + 1,
            colsNoNew = List.RemoveItems(cols, {"SectionEResponse__flag"}),
            newOrder = List.InsertRange(colsNoNew, insertPos, {"SectionEResponse__flag"})
        in
            Table.ReorderColumns(WithEFlag, newOrder),

    // =========================================
    // Helper: replace an existing flag column using row-aware logic
    // =========================================
    ReplaceFlagByRowId = (t as table, wcCol as text, flagCol as text, sampleIds as list) as table =>
        let
            t1 = Table.AddColumn(t, "__tmp_flag", each if List.Contains(sampleIds, [__row_id]) then "F" else null, type text),
            t2 = Table.RemoveColumns(t1, {flagCol}),
            t3 = Table.RenameColumns(t2, {{"__tmp_flag", flagCol}}),
            cols = Table.ColumnNames(t3),
            insertPos = List.PositionOf(cols, wcCol) + 1,
            colsNo = List.RemoveItems(cols, {flagCol}),
            newOrder = List.InsertRange(colsNo, insertPos, {flagCol}),
            t4 = Table.ReorderColumns(t3, newOrder)
        in
            t4,

    // =========================================
    // Populate flags (row-aware)
    // =========================================
    WithAFlagPop = ReplaceFlagByRowId(ReorderEFlag, "SectionAResponse__wc", "SectionAResponse__flag", SampleA),
    WithBFlagPop = ReplaceFlagByRowId(WithAFlagPop, "SectionBResponse__wc", "SectionBResponse__flag", SampleB),
    WithCFlagPop = ReplaceFlagByRowId(WithBFlagPop, "SectionCResponse__wc", "SectionCResponse__flag", SampleC),
    WithDFlagPop = ReplaceFlagByRowId(WithCFlagPop, "SectionDResponse__wc", "SectionDResponse__flag", SampleD),
    WithEFlagPop = ReplaceFlagByRowId(WithDFlagPop, "SectionEResponse__wc", "SectionEResponse__flag", SampleE)

in
    WithEFlagPop