let
    COMPONENT = "SectionAResponse",

    Source = Excel.CurrentWorkbook(){[Name="_03_sampling"]}[Content],

    FilteredComponent =
        Table.SelectRows(
            Source,
            each [component_id] = COMPONENT
        ),

    FilteredSampled =
        Table.SelectRows(
            FilteredComponent,
            each [sample_flag] = "F"
        ),

    Output =
        Table.RemoveColumns(
            FilteredSampled,
            {"sample_flag", "response_presence"}
        )

in
    Output