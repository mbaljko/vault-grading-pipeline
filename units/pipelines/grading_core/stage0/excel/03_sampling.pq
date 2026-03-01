// ======================================================================
// Query: sampled_entries
// Stage 0 — Calibration Sampling (Long Format)
//
// Input:  cleaned_entries  (one row per submission_id × component_id)
// Output: same rows + sample_flag
//
// Sampling rule (per component_id):
// - rank rows by response_wc (ascending)
// - drop the shortest and longest (interior only)
// - pick m rows by interior-uniform spacing over the ranked interior
// - flag picked rows with sample_flag = "F"
//
// Notes:
// - Sampling operates on the composite unit (__row_id, component_id) via __unit_key.
// - If interior count ≤ m, all interior rows are flagged.
// ======================================================================

let
    // -----------------------------------------
    // Source
    // -----------------------------------------
    Source = Excel.CurrentWorkbook(){[Name="cleaned_entries"]}[Content],

    // -----------------------------------------
    // Required columns check
    // -----------------------------------------
    RequiredCols = {"__row_id", "component_id", "response_wc"},
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
                {"__row_id", Int64.Type},
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
            each Text.From([__row_id]) & "::" & Text.From([component_id]),
            type text
        ),

    // -----------------------------------------
    // Helper: sample m keys by interior-uniform spacing over wc-ranked rows
    // (expects a single component_id group table)
    // -----------------------------------------
    SampleInteriorUniformKeys = (t as table, wcCol as text, keyCol as text, m as number) as list =>
        let
            t0 =
                if Table.HasColumns(t, {wcCol, keyCol}) then
                    Table.SelectRows(
                        Table.SelectColumns(t, {keyCol, wcCol}),
                        each Record.Field(_, wcCol) <> null and Value.Is(Record.Field(_, wcCol), type number)
                    )
                else
                    error "Missing required columns for sampling within group.",

            t1 = Table.Sort(t0, {{wcCol, Order.Ascending}}),
            n = Table.RowCount(t1),

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

            // IMPORTANT: dynamic column extraction must use Table.Column(...)
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
    // Apply flags
    // -----------------------------------------
    WithFlag =
        Table.AddColumn(
            WithUnitKey,
            "sample_flag",
            each if List.Contains(SampleKeyList, [__unit_key]) then "F" else null,
            type text
        ),

    Output = Table.RemoveColumns(WithFlag, {"__unit_key"})

in
    Output