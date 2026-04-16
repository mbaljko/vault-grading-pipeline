# PPS1 CSV Importer

This workflow converts the exported PPS1 LMS CSV into one JSON file per student for PPS2 booklet generation.

## Files

- Script: `/Users/mb/Documents/vault-grading-pipeline/01_units/pipelines/PPS2_assembly/python/import_pps1_csv_to_json.py`
- Schema/config: `/Users/mb/Documents/vault-grading-pipeline/01_units/pipelines/PPS2_assembly/python/pps1_import_schema.json`

## What it does

- Reads the PPS1 LMS export CSV.
- Maps LMS columns into the JSON fields used by the PPS2 workflow.
- Derives `*-devt` fields from the `*_shift`, `*_cont`, and `*_intro` columns.
- Derives `*-status` fields from the `E2_*_GridResponse` columns.
- Populates the `Sec1_*`, `Sec2_*`, `Sec3Sec4_*`, and `CLM_*` fields heuristically from the available dimension data.
- Writes one JSON per row into `student_data_all`.
- Copies a random sample into `student_data`.
- Augments that sample with three coverage cases: one random `_DOT` family-name file, the file with the longest family name, and the file with the longest given-name string.

## Configuration

Default importer inputs are centralized in `pps1_import_schema.json` under `importDefaults`:

- `csvPath`
- `participantsCsvPath`
- `allOutputDir`
- `sampleOutputDir`
- `sampleSize`

The same schema file also defines:

- field order and default values for output JSON
- direct CSV-to-JSON field mapping
- dimension mappings like `B-1 -> B.2.1`
- section slot mappings for Section 1, Section 2, and Section 3/4 tension fields

CLI arguments still work as overrides when needed.

## Name Join Logic

`GIVEN_NAME` and `FAMILY_NAME` are resolved using the participants export CSV first.

Primary join key:

- `Email address`

Secondary fallback join key:

- LMS `Username` matched against the email local-part from the participants CSV

If no participant match is found, the importer falls back to parsing the LMS `User` field heuristically.

This matters because the LMS `User` field is not always a reliable given-name/family-name split, while the participants CSV usually is.

Special handling:

- If the authoritative participant last name is `.`, the JSON `FAMILY_NAME` is kept as `.`.
- Filenames are built as `FAMILY_NAME` first, then `GIVEN_NAME`, with the family-name portion uppercased.
- For filenames only, a family name of `.` is rendered as `_DOT` so the generated filename remains explicit and filesystem-safe.

## Typical Run

```bash
/opt/homebrew/bin/python3 /Users/mb/Documents/vault-grading-pipeline/01_units/pipelines/PPS2_assembly/python/import_pps1_csv_to_json.py --sample-seed 3000
```

## Notes

- The importer preserves LMS HTML content as-is in mapped response fields.
- Section-selection logic is heuristic. If the PPS2 booklet structure changes, update the schema first and only change Python when selection logic itself must change.
- The sampled set can therefore be larger than `sampleSize`, because the three coverage cases are added on top of the random sample when they are not already included.