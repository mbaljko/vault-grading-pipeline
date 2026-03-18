
// Stage 0 — Validation join (Excel/Power Query)
// Purpose:
// - Map each LMS export row to the grading worksheet’s stable identifier (`Identifier` like "Participant 7835077")
// - Emit an explicit canonical `submission_id` (digits-only) while preserving the original `GW.Identifier`
// - Emit `__join_status` that gates grading eligibility (grade only `matched_unique`)
//
// Role of the grading worksheet (GW):
// - GW is the authoritative reference list of participants for grading.
// - Each LMS export row is matched to GW by normalized name, resolving ambiguities and ensuring stable identity.
// - GW provides the canonical identifier (`GW.Identifier`) and full name for each participant.
// - Only rows that match uniquely to GW are considered eligible for grading (`matched_unique`).
// - GW enables robust join logic, disambiguating duplicate names and supporting internal submission tracking.
//
// Note: Students listed in GW who do not have a matching submission in the LMS export will not appear in the output. The current script does not flag or report missing submissions from GW.

let
    Raw = Excel.CurrentWorkbook(){[Name="Table_raw"]}[Content],
    GW  = Excel.CurrentWorkbook(){[Name="grading_worksheet"]}[Content],

    // Collapse multiple spaces deterministically (bounded passes are sufficient for typical names)
    CollapseSpaces = (s as nullable text) as nullable text =>
        let
            s0 = if s = null then null else s,
            s1 = if s0 = null then null else List.Accumulate({1..10}, s0, (state, _) => Text.Replace(state, "  ", " "))
        in
            s1,

    // Strip leading non-alphanumeric noise (e.g., leading "." seen in some exports)
    StripLeadingJunk = (s as nullable text) as nullable text =>
        let
            s0 = if s = null then null else Text.Trim(s),
            chars = if s0 = null then null else Text.ToList(s0),
            allowed = List.Combine({{"a".."z"}, {"0".."9"}}),
            lowered = if chars = null then null else List.Transform(chars, each Text.Lower(_)),
            flags = if lowered = null then null else List.Transform(lowered, each List.Contains(allowed, _)),
            pos = if flags = null then -1 else List.PositionOf(flags, true),
            kept = if chars = null then null else if pos = -1 then {} else List.Skip(chars, pos),
            out = if kept = null then null else Text.Combine(kept)
        in
            out,

    // Extract the trailing digits from a string (robust to prefix changes like "Participant", "User", etc.)
    ExtractTrailingDigits = (s as nullable text) as nullable text =>
        let
            s0 = if s = null then null else Text.Trim(s),
            chars = if s0 = null then null else Text.ToList(s0),
            reversed = if chars = null then null else List.Reverse(chars),
            digits = {"0".."9"},
            takeWhileDigits =
                if reversed = null then
                    null
                else
                    List.FirstN(
                        reversed,
                        (c) => List.Contains(digits, c)
                    ),
            out =
                if takeWhileDigits = null then
                    null
                else
                    Text.Combine(List.Reverse(takeWhileDigits))
        in
            out,

    // Normalise join key derived from display name
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

    // Canonical internal submission_id: digits-only version of GW.Identifier
    WithSubmissionId =
        Table.AddColumn(
            ExpandedResolved,
            "submission_id",
            each ExtractTrailingDigits([GW.Identifier]),
            type text
        ),

    // Join status gates grading:
    // - matched_unique: safe to grade
    // - excluded_ambiguous: name collision in grading worksheet (duplicate name)
    // - no_match: not found in grading worksheet
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

    Output =
        Table.SelectColumns(
            JoinStatus,
            {
                "User",
                "Username",
                "__key_name",
                "GW.Full name",
                "GW.Identifier",
                "submission_id",
                "__join_status",
                "__gw_name_count"
            }
        )
in
    Output