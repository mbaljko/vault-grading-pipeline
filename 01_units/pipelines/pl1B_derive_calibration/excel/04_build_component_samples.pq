// ======================================================================
// Query: 04_build_component_samples
// Purpose:
// - Provide a reusable function to return selected sample rows per component_id
// - Provide an index table of components discovered in sampled_entries
//
// Input table (worksheet): sampled_entries
// Expected columns: submission_id, component_id, response_text, response_wc, sample_flag
//
// Notes:
// - Excel requires one query load per output worksheet. This query defines the
//   function; create one thin query per component that calls it.
// ======================================================================

let
    // -----------------------------------------
    // Source
    // -----------------------------------------
    Source = Excel.CurrentWorkbook(){[Name="sampled_entries"]}[Content],

    // -----------------------------------------
    // Required columns check
    // -----------------------------------------
    RequiredCols = {"submission_id", "component_id", "sample_flag"},
    MissingCols = List.Difference(RequiredCols, Table.ColumnNames(Source)),
    _assert =
        if List.Count(MissingCols) = 0 then
            true
        else
            error "Expected columns missing in 'sampled_entries': " & Text.Combine(MissingCols, ", "),

    // -----------------------------------------
    // Type normalisation (lightweight, avoids surprises)
    // -----------------------------------------
    Typed =
        Table.TransformColumnTypes(
            Source,
            {
                {"submission_id", type text},
                {"component_id", type text},
                {"sample_flag", type text}
            }
        ),

    // -----------------------------------------
    // Keep only selected sample rows
    // -----------------------------------------
    SelectedOnly =
        Table.SelectRows(
            Typed,
            each [sample_flag] = "F"
        ),

    // Buffer to reduce repeated scans when the function is called
    SelectedBuffered = Table.Buffer(SelectedOnly),

    // -----------------------------------------
    // Function: return selected rows for a given component_id
    // -----------------------------------------
    fn_component_sample = (component as text) as table =>
        let
            Out =
                Table.SelectRows(
                    SelectedBuffered,
                    each [component_id] = component
                )
        in
            Out,

    // -----------------------------------------
    // Component index table (discovered from data)
    // -----------------------------------------
    ComponentIndex =
        let
            distinct = List.Sort(List.Distinct(SelectedBuffered[component_id])),
            tbl = Table.FromList(distinct, Splitter.SplitByNothing(), {"component_id"}, null, ExtraValues.Error)
        in
            tbl

in
    ComponentIndex